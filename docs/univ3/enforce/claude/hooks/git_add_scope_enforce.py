#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""git_add_scope_enforce.py — CẤM `git add` VƠ VÉT khi nhiều worker dùng chung một cây mã.

SỰ VIỆC THẬT (2026-08-26, dự án EtsyFulfillChichub — 5 worker song song trên CÙNG một
thư mục làm việc):
  · 16:38 worker "A35 chia tab" chạy `git add` vơ vét rồi commit `deeddc1`. Lệnh đó CUỐN
    THEO phần đang viết dở của worker khác trong `src/lib/fulfill/supplier-actions.ts`:
    dòng 44/46 đã `import { probeSupplierOrderWithRetry } from './push-verify'` và dòng
    1000/1010 đã gọi hàm đó, trong khi `push-verify.ts` tại chính commit ấy CHƯA hề export
    hàm này (chỉ có classifyPushError / supplierCanLookupByCode / probeSupplierOrderByCode).
  · Hệ quả: nhánh `main` KHÔNG biên dịch được, lô deploy gãy ở bước build (exit 1, không
    phải OOM). Demo và prod thoát nạn chỉ vì `deploy-batch.sh` build ở thư mục trung lập
    rồi mới swap — build gãy nên không có gì được swap.
  · 16:43 phải vá vội bằng `cafcb38` ("bù probeSupplierOrderWithRetry để main biên dịch
    lại được") — tức đẩy code CHƯA XONG của người khác lên chỉ để cứu build.

VÌ SAO PHẢI LÀ HOOK CHỨ KHÔNG PHẢI DÒNG NHẮC TRONG TÀI LIỆU: luật
`rules/AGENTS-ORCH.md` §Trần-worker điều 3 ("một tệp/vùng chỉ MỘT worker được ghi tại một
thời điểm") ĐÃ tồn tại từ 25/8 và vẫn xảy ra đúng lỗi ấy sau đó một ngày. Markdown là xác
suất; `git add -A` thì tất định cuốn sạch cây làm việc. Chỉ cổng tất định mới chặn được.

SỰ VIỆC THẬT THỨ HAI (2026-08-27, cùng dự án): worker chạy `git commit --amend` trong cây
dùng chung -> commit 12f7522 CUỐN THEO `docs/NGHIEN-CUU-GMAIL-TU-DONG.md` mà worker khác
đang để trong index. `--amend` gói TOÀN BỘ index vào commit cũ, y hệt `-a`, lại còn viết
lại sha nên vé deploy đã đăng ký theo sha cũ thành vé trỏ vào hư không.

CHẶN (deny):  `git add -A` · `git add --all` · `git add .` · `git add -u` (không pathspec)
              `git commit -a` · `git commit -am`  (-a = tự động stage MỌI file đã theo dõi)
              `git commit --amend` KHI INDEX ĐANG CÓ FILE STAGE (không biết của ai)
              — sửa mỗi lời nhắn thì dùng `git commit --amend --only -m "..."`, cờ `--only`
              không kèm đường dẫn = KHÔNG hót index.
NHẮC (allow + additionalContext): `git add <thư mục>` mà trong thư mục đó đang có ≥2 tệp
              thay đổi — liệt kê ra để worker tự soi tệp nào không phải của mình.
CHO QUA:      lệnh git khác · có cửa thoát `git-scope-ok` (chỉ tắt TẦNG 1 dưới đây).

SỰ VIỆC THẬT THỨ BA (2026-09-18) — LỖ CỦA CHÍNH CÁI DÒNG "CHO QUA" Ở TRÊN: W07 khai
`GHI: src/lib/fulfill` nhưng gõ `git add src/app/pipeline/_components/card-dialog.tsx`
(ĐÍCH DANH, không vơ vét) -> cổng cho qua -> commit `f13253dc` nuốt 288 dòng việc đang dở
của W09, `main` gãy build. Hai lần trước chỉ vá đúng CÚ PHÁP vừa gây hoạ nên lần này lọt
qua cú pháp khác. Nay thêm TẦNG 2 canh VÙNG chứ không canh cú pháp:

TẦNG 2 — CHẶN (deny): mọi đường dẫn trong `git add <đường dẫn>` / `git commit … -- <đường
              dẫn>` mà nằm NGOÀI vùng dòng `GHI:` của brief chính worker đó; brief khai
              `GHI: -` (thuần đọc) mà vẫn `git add` -> chặn. `git-scope-ok` KHÔNG mở được
              tầng này; cửa thoát riêng là cờ dùng-một-lần `git-ngoai-vung`.
              KHÔNG áp cho main/manager (payload không có `agent_id`) và cho brief cũ
              thiếu hẳn dòng `GHI:` (tương thích ngược).

Fail-open tuyệt đối: lỗi bất kỳ -> exit 0 (không bao giờ chặn oan vì hook tự vỡ).
"""
import json
import os
import re
import time
import shlex
import subprocess
import sys

ESCAPE = "git-scope-ok"

# `git add` vơ vét: cờ -A/--all/-u, hoặc pathspec là "." / "./" / ":/"
CO_VO_VET = {"-A", "--all", "--no-ignore-removal", "-u", "--update"}
PATH_VO_VET = {".", "./", ":/", "*", "'*'"}


def chay(args, cwd):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                              timeout=8).stdout
    except Exception:
        return ""


# THÂN heredoc và mã nhúng là DỮ LIỆU ĐANG ĐƯỢC GHI, không phải lệnh đang chạy. Đo ngay
# trong lượt vá này (18/09/2026): tệp vá được soạn bằng `python3 - <<PYEOF … PYEOF`, trong
# thân có chuỗi `git commit -q -F -` của ca thử -> cổng tầng 3 vừa dựng xong đã CHẶN OAN
# chính lệnh soạn tệp. Cùng bệnh với `RX_HEREDOC` mà `worker_cap_enforce` phải thêm ngày
# 04/09 vì nguyên văn commit message bị đọc thành lệnh.
# GIỮ dòng mở heredoc (`git commit -q -F - <<'EOF'` vẫn còn nguyên phần trước `<<`), chỉ bỏ
# phần thân — nên lệnh THẬT vẫn bị soi, chỉ dữ liệu là được tha.
RX_THAN_HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\r?\n.*?\r?\n\s*\1\b", re.S)
RX_MA_NHUNG = re.compile(r"(?:python3?|node|perl|ruby)\s+-(?:c|e)\s+(['\"])(?:\\.|(?!\1).)*\1", re.S)


def bo_du_lieu(cmd: str) -> str:
    """Bỏ phần DỮ LIỆU (thân heredoc, mã nhúng `-c`) khỏi chuỗi lệnh trước khi soi."""
    try:
        return RX_MA_NHUNG.sub(" ", RX_THAN_HEREDOC.sub(" ", cmd or ""))
    except Exception:
        return cmd or ""


def tach_lenh(cmd: str):
    """Cắt chuỗi Bash thành từng lệnh con (theo ; && || | và xuống dòng)."""
    phan = re.split(r"(?:&&|\|\||[;\n|])", cmd)
    ra = []
    for p in phan:
        p = p.strip()
        if not p:
            continue
        try:
            ra.append(shlex.split(p))
        except Exception:
            ra.append(p.split())
    return ra


def la_git(tok, *sub):
    """tok bắt đầu bằng `git ... <sub>` (bỏ qua các cờ toàn cục như -C <đường dẫn>)."""
    if not tok or os.path.basename(tok[0]) != "git":
        return None
    i = 1
    while i < len(tok):
        t = tok[i]
        if t in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
            i += 2
            continue
        if t.startswith("-"):
            i += 1
            continue
        break
    if i < len(tok) and tok[i] in sub:
        return tok[i + 1:]
    return None


def file_dang_doi(cwd):
    """Danh sách đường dẫn đang thay đổi (đã theo dõi hoặc chưa) theo git status."""
    ra = []
    for ln in chay(["git", "status", "--porcelain", "-z"], cwd).split("\0"):
        # KHÔNG strip() trước khi cắt: mã trạng thái là 2 ký tự + 1 dấu cách
        # (" M src/a.ts"), strip xoá dấu cách đầu -> cắt [3:] ăn mất chữ cái đầu tên tệp.
        if len(ln) > 3:
            ra.append(ln[3:].strip().strip('"'))
    return ra


LOI_KHUYEN = """CÁCH ĐÚNG — liệt kê ĐÍCH DANH tệp của chính bạn:
    git add src/lib/abc/xyz.ts src/app/def/page.tsx
    git commit -m "..."          # KHÔNG dùng -a, KHÔNG --amend

Lỡ commit thiếu tệp -> tạo commit MỚI (`git add <tệp> && git commit -m "..."`), đừng
`--amend`. Chỉ muốn sửa lời nhắn thì: `git commit --amend --only -m "..."`.

Muốn biết tệp nào là của mình: `git status --short` rồi chỉ nhặt tệp bạn thật sự vừa sửa
trong lượt này. Tệp bạn không đụng tới = của worker khác, để nguyên cho họ commit.

Nếu bạn CHẮC CHẮN cây làm việc chỉ có một mình bạn (không có worker nào khác đang chạy
trên dự án này) -> thêm chuỗi `git-scope-ok` vào lệnh."""


def chuan_hoa(p):
    return os.path.normpath((p or "").strip().strip('"').lstrip("./"))


def da_bao_phu(duong_add, tep):
    """`git add` trong CÙNG lệnh có phủ `tep` không (khớp thẳng hoặc là thư mục cha)."""
    t = chuan_hoa(tep)
    for d in duong_add:
        d = chuan_hoa(d)
        if not d or d == ".":
            return True
        if t == d or t.startswith(d.rstrip("/") + "/"):
            return True
    return False


LOI_KHUYEN_COMMIT = """CÁCH ĐÚNG — nêu ĐÍCH DANH đường dẫn ngay trong lệnh commit:
    git commit -m "..." -- src/lib/abc/xyz.ts src/app/def/page.tsx

`git commit` trần lấy TOÀN BỘ index. Trong cây dùng chung, index là của chung — người
khác `git add` xong chưa kịp commit thì tệp của họ nằm sẵn ở đó và đi theo commit của bạn."""



# ══════════════════════════════════════════════════════════════════════════════════════
# TẦNG 2 — `git add` ĐÍCH DANH VẪN PHẢI NẰM TRONG VÙNG `GHI:` CỦA CHÍNH WORKER (W13, 18/09/2026)
# ══════════════════════════════════════════════════════════════════════════════════════
# CA THẬT HÔM NAY, đo bằng `git show --stat f13253dc` (8 tệp):
#   Thợ W07 (việc Printbelle) khai `GHI: src/lib/fulfill`. Commit của nó cuốn thêm
#   `src/app/pipeline/_components/card-dialog.tsx` (**288 dòng** — TOÀN BỘ việc đang dở của
#   W09: auto-save ô mô tả thẻ) và `src/app/orders/[id]/_components/supplier-dispatch-card.tsx`.
#   Nửa việc W09 đi theo commit, nửa kia (`easymde-editor.tsx` khai prop `onBlur`) ở lại chỉ
#   mục -> `main` GÃY BUILD, cả lô deploy kẹt, phải vá vội bằng `3a76c7b4` rồi `092b64cd`.
#
# VÌ SAO TẦNG 1 KHÔNG BẮT ĐƯỢC: toàn bộ phần trên chỉ hỏi «lệnh này có VƠ VÉT không?»
# (`-A` · `--all` · `.` · `-u` · `commit -a` · `--amend`). W07 gõ
# `git add src/app/pipeline/_components/card-dialog.tsx` — ĐÍCH DANH, không vơ vét — nên
# dòng 35 của chính tệp này ghi rõ «CHO QUA». Cổng hỏi SAI CÂU HỎI.
#
# ĐÂY LÀ LẦN THỨ BA cùng một loại hoạ, mỗi lần lọt qua một CÚ PHÁP khác:
#   26/08 `git add` vơ vét (deeddc1) · 27/08 `--amend` (12f7522) · 18/09 `git add` đích danh.
# Hai lần trước đều chỉ vá đúng cú pháp vừa gây hoạ. Nên tầng này KHÔNG canh cú pháp nữa:
# canh VÙNG — brief khai `GHI:` gì thì chỉ được `git add` trong đó, bất kể gõ kiểu gì.
# Founder chốt nguyên văn: *"nó KHÔNG ĐƯỢC PHÉP CUỐN NHƯ THẾ NO MATTER WHAT"*.
#
# KHÔNG ĐẺ BỘ MÁY MỚI: vùng bóc bằng ĐÚNG hàm mà cổng trùng vùng đang dùng
# (`worker_cap_enforce.vung_viec_moi` / `chuan_vung` / `running_workers`) — một nguồn đếm
# duy nhất, mọi bản vá chặn-oan tích luỹ ở đó tự động có hiệu lực tại đây.
#
# KHÔNG CHẶN OAN MAIN: manager ở luồng chính điều phối CẢ CÂY, không có vùng nào cả ->
# payload không có `agent_id` thì tầng này không chạy một dòng nào.
TEN_CONG_VUNG = "git-ngoai-vung"
NHAT_KY_VUNG = ("~/.claude/logs/cong-git-vung.log", "/tmp/claude_hooks/cong-git-vung.log")


def _ghi_log_vung(dong: str):
    for p in NHAT_KY_VUNG:
        try:
            p = os.path.expanduser(p)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as fh:
                fh.write("%s\t%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
        except OSError:
            pass


def _nap(ten: str):
    """Import module hook nằm CẠNH tệp này. Không nạp được -> None (fail-open)."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        return __import__(ten)
    except Exception:
        return None


def duong_transcript_worker(data) -> str:
    """Đường dẫn `agent-<id>.jsonl` của CHÍNH worker đang gõ lệnh; "" nếu là main.

    ĐO THẬT 18/09/2026 (bằng cách cho hook ghi nguyên payload ra tệp rồi chạy một lệnh
    `git status` trong phiên worker): `transcript_path` mà harness gửi cho PreToolUse là
    transcript PHIÊN CHA (`<projects>/<session>.jsonl`), KHÔNG phải transcript agent.
    Danh tính worker nằm ở trường RIÊNG `agent_id` (kèm `agent_type`). Vì thế hàm
    `so_worker_cua_luot` ngay dưới — đòi chuỗi "agent-" trong tên tệp — CHƯA BAO GIỜ khớp
    trong phiên worker; đó chính là lý do nhật ký `.thieu-trailer.log` đầy dòng "không suy
    được W##" và 11/12 commit gần nhất không có trailer `Worker=`.
    """
    aid = str(data.get("agent_id") or "").strip()
    if not aid:
        return ""                      # lượt của MAIN (manager) -> tầng vùng không áp
    t = str(data.get("transcript_path") or "")
    ung = []
    if t.endswith(".jsonl"):
        ung.append(os.path.join(t[:-len(".jsonl")], "subagents", "agent-%s.jsonl" % aid))
        ung.append(os.path.join(os.path.dirname(t), str(data.get("session_id") or ""),
                                "subagents", "agent-%s.jsonl" % aid))
    for p in ung:
        if os.path.isfile(p):
            return p
    return ""


def brief_worker(duong: str) -> str:
    """Brief (lời giao việc) của worker = bản ghi `user` ĐẦU TIÊN trong transcript agent."""
    try:
        with open(duong, encoding="utf-8") as fh:
            for _ in range(60):
                dong = fh.readline()
                if not dong:
                    break
                try:
                    o = json.loads(dong)
                except Exception:
                    continue
                if o.get("type") != "user":
                    continue
                c = ((o.get("message") or {}) if isinstance(o.get("message"), dict) else {}).get("content")
                if isinstance(c, str):
                    van = c
                elif isinstance(c, list):
                    van = "\n".join(str(b.get("text") or "") for b in c
                                     if isinstance(b, dict) and b.get("type") == "text")
                else:
                    continue
                if van.strip():
                    return van
    except Exception:
        pass
    return ""


def tien_to_khai(brief: str, WCE):
    """Đường dẫn THÔ trong dòng `GHI:` (chưa qua `chuan_vung`).

    WHY cần bản thô bên cạnh bản vùng: `chuan_vung` cắt tới tầng vùng nên khai
    `GHI: src` ra vùng `src` còn tệp `src/lib/fulfill/x.ts` ra `src/lib/fulfill` — so tập
    thô sẽ CHẶN OAN. So thêm bằng tiền tố thư mục thật thì quan hệ cha-con giữ nguyên.
    """
    ra = []
    try:
        van = WCE._bo_menh_de_cam(brief or "")
        for m in WCE.RX_KHAI.finditer(van):
            for tok in WCE.RX_KHAI_TACH.split(WCE._bo_ngoac(m.group(1))):
                tok = WCE.bo_dau_token(tok)     # W45: giữ dấu chấm đầu (`.claude/…`)
                if not tok or not WCE.RX_TOKEN_DUONG.match(tok):
                    continue
                if "/" not in tok and tok.strip("~./") not in WCE.VUNG_GOC and \
                        not WCE.la_thu_muc_goc(tok):
                    continue              # W39: chữ trơn là thư mục thật ở gốc kho thì nhận
                ra.append(tok)
    except Exception:
        pass
    return ra


def goc_lam_viec(cac_lenh, cwd: str):
    """Mọi thư mục mà đường dẫn tương đối trong lệnh CÓ THỂ được tính từ đó.

    CA THẬT 18/09/2026, chính lượt vá này bị chặn oan: brief W13 khai
    `GHI: … /Users/buddhy/PycharmProjects/univ3-ssot`, lệnh gõ
    `cd /Users/buddhy/PycharmProjects/univ3-ssot && git add enforce/claude/hooks/x.py`.
    Hook chỉ biết `cwd` của PHIÊN (kho Fulfill) nên ghép ra
    `<Fulfill>/enforce/claude/hooks/x.py` -> không khớp tiền tố khai -> chặn oan đúng
    người đang sửa nó. Nay gom thêm thư mục của `cd …` và `git -C …` ngay trong lệnh;
    khớp theo BẤT KỲ gốc nào là cho qua (lệch về phía fail-open, đúng luật của cổng này).
    """
    goc = [cwd]
    # W15: đường dẫn trong BẢN VÁ luôn tính từ GỐC KHO ("a/src/..."), nên gõ lệnh ở thư mục
    # con thì ghép với cwd sẽ trật. `--show-toplevel` là lệnh ĐỌC, không đụng chỗ chờ.
    tl = chay(["git", "rev-parse", "--show-toplevel"], cwd).strip()
    if tl:
        goc.append(tl)
    for tok in cac_lenh:
        if not tok:
            continue
        if tok[0] == "cd" and len(tok) > 1 and not tok[1].startswith("-"):
            goc.append(tok[1])
        if os.path.basename(tok[0]) == "git":
            for i, t in enumerate(tok[:-1]):
                if t == "-C":
                    goc.append(tok[i + 1])
    ra = []
    for g in goc:
        try:
            g = os.path.abspath(os.path.join(cwd, os.path.expanduser(g)))
        except Exception:
            continue
        if g not in ra:
            ra.append(g)
    return ra


def _duoi_tien_to(duong: str, tien_to, cac_goc) -> bool:
    for cwd in cac_goc:
        try:
            a = os.path.abspath(os.path.join(cwd, os.path.expanduser(duong)))
        except Exception:
            continue
        for p in tien_to:
            try:
                b = os.path.abspath(os.path.join(cwd, os.path.expanduser(p)))
            except Exception:
                continue
            if a == b or a.startswith(b.rstrip("/") + "/"):
                return True
    return False


# Token phải TRÔNG NHƯ đường dẫn. Đo ngay trong lượt vá (18/09/2026): lệnh
# `git commit -F /tmp/msg.txt -- docs/... 2>&1 | tail -4` -> `2>&1` lọt vào danh sách
# pathspec và lời chặn in ra "· 2>&1 -> vùng `2>&1`". Cùng họ lỗi với `RX_TEP_HOP_LE`
# mà `worker_cap_enforce` phải thêm: mảnh cú pháp shell không phải tệp.
RX_LA_DUONG_DAN = re.compile(r"^[~./A-Za-z0-9_@][A-Za-z0-9_@.\-/\[\]()]*$")


def pathspec_cua_lenh(cac_lenh):
    """(đường dẫn được stage, có cờ/pathspec vơ vét không).

    Gom cả hai đường vào chỉ mục: `git add <đường dẫn>` và `git commit … -- <đường dẫn>`.
    """
    duong, vo_vet = [], False
    for tok in cac_lenh:
        sau = la_git(tok, "add", "stage")
        if sau is not None:
            for t in sau:
                if t.startswith("-"):
                    if t in CO_VO_VET:
                        vo_vet = True
                    continue
                if t in PATH_VO_VET:
                    vo_vet = True
                    continue
                if t != "--" and RX_LA_DUONG_DAN.match(t):
                    duong.append(t)
            continue
        sau = la_git(tok, "commit")
        if sau is not None and "--" in sau:
            for t in sau[sau.index("--") + 1:]:
                if not t.startswith("-") and RX_LA_DUONG_DAN.match(t):
                    duong.append(t)
    return duong, vo_vet


# ══════════════════════════════════════════════════════════════════════════════════════
# W15 (18/09/2026) — CHỖ CHỜ DÙNG CHUNG CÓ NHIỀU CỬA, `git add` CHỈ LÀ MỘT
# ══════════════════════════════════════════════════════════════════════════════════════
# LỖ THẬT, chính W13 khai khi bàn giao và dòng thời gian của `f13253dc` xác nhận:
#   03:43:47 (UTC) W10 chạy `git apply --cached /tmp/w10-cd-mine.patch` -> `card-dialog.tsx`
#   NẰM SẴN trong chỗ chờ dùng chung mà KHÔNG hề đi qua `git add`. 04:11:45 thợ Printbelle
#   commit trần và cuốn theo -> nhánh chính gãy build.
# Tầng 2 cũ chỉ đọc pathspec của `git add` / `git commit --trailer "Worker=W15" … --` nên hai tầng W13 dựng đều
# không soi tới đường này.
#
# ĐO THẬT trong repo hộp cát (18/09/2026, script `do_ho_lenh.py` + `do_dot2.py`, xem bảng
# trong báo cáo W15) — cột "ghi vào đâu" là kết quả `git diff --cached --name-only` và
# `git diff --name-only` NGAY SAU lệnh:
#   apply --cached      -> CHỖ CHỜ (+ cây)      apply --index -> CHỖ CHỜ
#   apply (không cờ)    -> cây làm việc          apply --cached - < tệp -> CHỖ CHỜ
#   update-index --add  -> CHỖ CHỜ               read-tree HEAD -> thay CẢ chỗ chờ
#   mv / rm / rm --cached -> CHỖ CHỜ             checkout <rev> -- tệp -> CHỖ CHỜ + cây
#   restore --staged -- tệp -> CHỖ CHỜ           restore -- tệp -> VỨT sửa trong cây
#   reset (trần) / reset -- tệp -> gỡ khỏi chỗ chờ phần người khác vừa đặt vào
#   stash pop / apply --index -> mang việc người khác trở lại cây (và chỗ chờ)
#   cherry-pick -n -> CHỖ CHỜ                    merge / đổi nhánh -> ĐỔI NỘI DUNG cả cây
# KHÔNG ghi gì (đo được index lẫn cây đều trống) -> KHÔNG chặn, tránh chặn oan:
#   apply --check · --stat · --numstat · --summary · git worktree add/list/prune ·
#   mọi lệnh đọc (diff/log/show/status/ls-files).
RX_VA_GIT = re.compile(r"^diff --git a/(.+?) b/(.+?)\s*$", re.M)
RX_VA_MOI = re.compile(r"^\+\+\+ (?:b/)?(.+?)(?:\t.*)?\s*$", re.M)
RX_VA_CU = re.compile(r"^--- (?:a/)?(.+?)(?:\t.*)?\s*$", re.M)


def tep_trong_ban_va(noi_dung: str):
    """Tệp mà một bản vá (unified diff / mbox) sẽ đụng — bóc bằng regex, KHÔNG gọi git.

    Đo 18/09/2026: `git apply --numstat` cũng ra đúng danh sách này và không ghi gì, nhưng
    bóc tại chỗ thì không phụ thuộc lệnh ngoài, không có rủi ro gọi nhầm lệnh ghi.
    """
    ra = []
    for rx in (RX_VA_GIT, RX_VA_MOI, RX_VA_CU):
        for m in rx.finditer(noi_dung or ""):
            for g in m.groups():
                g = (g or "").strip().strip('"')
                if not g or g == "/dev/null" or g.startswith("-"):
                    continue
                if g not in ra:
                    ra.append(g)
    return ra


CO_VA_DOC_THUAN = {"--check", "--stat", "--numstat", "--summary"}
CO_THOAT_TRANG_THAI = {"--abort", "--quit", "--skip", "--continue"}


def lenh_ap_ban_va(cac_lenh):
    """[(nhãn lệnh, tên lệnh con)] các lệnh THẬT SỰ áp bản vá; bỏ dạng chỉ đọc."""
    ra = []
    for tok in cac_lenh:
        for ten in ("apply", "am"):
            sau = la_git(tok, ten)
            if sau is None:
                continue
            co = set(t for t in sau if t.startswith("-"))
            if ten == "apply" and (co & CO_VA_DOC_THUAN):
                break                       # đọc thuần -> không đụng chỗ chờ lẫn cây
            if co & CO_THOAT_TRANG_THAI:
                break                       # `--abort/--continue…` là đường THOÁT, chặn thì kẹt cứng
            ra.append((" ".join(tok), ten))
            break
    return ra


def _noi_dung_ban_va(cac_lenh, cmd_goc: str, cac_goc):
    """Mọi nguồn bản vá đọc được TRƯỚC khi lệnh chạy: tệp trên dòng lệnh (kể cả `< tệp`
    và `cat tệp |`), và thân heredoc trong chính lệnh."""
    noi = []
    try:
        for m in RX_THAN_HEREDOC.finditer(cmd_goc or ""):
            noi.append(m.group(0))
    except Exception:
        pass
    da_doc = set()
    for tok in cac_lenh:
        for t in tok:
            if not t or t.startswith("-") or not RX_LA_DUONG_DAN.match(t):
                continue
            for g in cac_goc:
                try:
                    p = os.path.abspath(os.path.join(g, os.path.expanduser(t)))
                except Exception:
                    continue
                if p in da_doc or not os.path.isfile(p):
                    continue
                da_doc.add(p)
                try:
                    if os.path.getsize(p) > 4_000_000:
                        break
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        noi.append(fh.read())
                except OSError:
                    pass
                break
    return noi


def duong_tu_ban_va(cac_lenh, cmd_goc: str, cac_goc):
    """(đường dẫn bản vá sẽ đụng, [(nhãn, lệnh con)] không bóc được nguồn vá).

    Không đọc nổi bản vá (đến từ tiến trình khác, process substitution…) -> KHÔNG đoán:
    trả về ở vế thứ hai để tầng 3 xử như lệnh "không nêu đích danh".
    """
    ap = lenh_ap_ban_va(cac_lenh)
    if not ap:
        return [], []
    duong = []
    for noi in _noi_dung_ban_va(cac_lenh, cmd_goc, cac_goc):
        for d in tep_trong_ban_va(noi):
            if d not in duong:
                duong.append(d)
    return (duong, [] if duong else ap)


# Rev (HEAD, HEAD~1, sha, @) KHÔNG phải đường dẫn — nếu không lọc thì `git checkout HEAD --
# tệp` sẽ báo "HEAD ngoài vùng".
RX_LA_REV = re.compile(r"^(?:HEAD|ORIG_HEAD|FETCH_HEAD|MERGE_HEAD|@|[0-9a-f]{7,40})"
                       r"(?:[~^@][^\s]*)?$")
# Cờ NUỐT giá trị đứng sau -> giá trị đó không phải đường dẫn cần soi vùng.
CO_NUOT_GIA_TRI = {"-s", "--source", "-m", "--message", "-F", "--file", "-c", "-C",
                   "--pathspec-from-file", "--chmod", "-p", "--directory", "--exclude",
                   "--include", "-U", "--unsafe-paths"}


def _co_ve_duong_dan(t: str) -> bool:
    if not t or t.startswith("-") or not RX_LA_DUONG_DAN.match(t):
        return False
    if RX_LA_REV.match(t):
        return False
    return ("/" in t) or bool(re.search(r"\.[A-Za-z0-9]{1,8}$", t))


def _duong_sau_co(sau):
    """Đường dẫn trong phần đuôi một lệnh git: hết thảy sau `--`, hoặc token trông như
    đường dẫn (bỏ giá trị của cờ nuốt giá trị)."""
    ra = []
    if "--" in sau:
        for t in sau[sau.index("--") + 1:]:
            if not t.startswith("-") and RX_LA_DUONG_DAN.match(t or ""):
                ra.append(t)
        return ra
    bo_ke = False
    for t in sau:
        if bo_ke:
            bo_ke = False
            continue
        if t.startswith("-"):
            if t in CO_NUOT_GIA_TRI:
                bo_ke = True
            continue
        if _co_ve_duong_dan(t):
            ra.append(t)
    return ra


LENH_GHI_CO_DUONG = ("rm", "mv", "restore", "update-index", "checkout", "switch", "reset")


def duong_ghi_lenh_khac(cac_lenh):
    """Đường dẫn bị GHI/GỠ bởi họ lệnh ngoài `git add` — bảng đo ở đầu khối này."""
    duong = []
    for tok in cac_lenh:
        for ten in LENH_GHI_CO_DUONG:
            sau = la_git(tok, ten)
            if sau is None:
                continue
            if set(t for t in sau if t.startswith("-")) & CO_THOAT_TRANG_THAI:
                break
            for d in _duong_sau_co(sau):
                if ten == "update-index" and d.count(",") >= 2:
                    d = d.rsplit(",", 1)[-1]     # `--cacheinfo <mode>,<sha>,<đường dẫn>`
                if d and d not in duong:
                    duong.append(d)
            break
        else:
            sau = la_git(tok, "stash")
            if sau is not None:
                con = next((t for t in sau if not t.startswith("-")), "")
                if con in ("push", "save"):
                    for d in _duong_sau_co(sau[1:] if sau and sau[0] == con else sau):
                        if d not in duong:
                            duong.append(d)
    return duong


def ai_giu_vung(cwd: str, vung: str, aid_minh: str, WCE):
    """Tên W## của worker KHÁC đang giữ vùng ấy ("" nếu không ai / không đo được)."""
    try:
        song, xac = WCE.running_workers(cwd)
        ten = []
        for w in list(song) + list(xac):
            if str(w[1]) == aid_minh:
                continue
            if vung and vung in (w[3] or set()):
                t = WCE.so_worker(w, cwd)
                if t and t not in ten:
                    ten.append(t)
        return " · ".join(ten)
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════════════════════
# TẦNG 3 — LỆNH GÓI/HUỶ CẢ CÂY PHẢI NÊU ĐÍCH DANH ĐƯỜNG DẪN (W13, 18/09/2026)
# ══════════════════════════════════════════════════════════════════════════════════════
# DÒNG THỜI GIAN THẬT CỦA CA `f13253dc`, đọc từ transcript agent (giờ UTC, +7 = giờ VN):
#   03:43:47  W10 `git apply --cached …` -> `card-dialog.tsx` NẰM SẴN trong index.
#   04:10:24  W07 `git add` 6 tệp của nó.
#   04:10:52  W07 `git commit -q -F - <<EOF` (TRẦN) -> cổng commit-trần CHẶN ĐÚNG, liệt kê
#             7 tệp index. Cổng 27/08 vẫn chạy tốt — KHÔNG phải nó hỏng.
#   04:11:45  W07 gõ LẠI: tự `git diff --cached --name-only`, so với danh sách MONG của
#             mình, thấy khớp rồi TỰ CẤP chuỗi `git-scope-ok` ngay trong lệnh và commit
#             TRẦN lần nữa. `ESCAPE in cmd` ở đầu `main()` -> hook tắt sạch, không kiểm gì.
#   04:12:41  lệnh mới THẬT SỰ chạy xong — chậm 56 GIÂY vì `lint-staged` ("Backing up
#             original state… Running tasks for staged files"). Trong 56 giây đó
#             `card-dialog.tsx` (W09/W10) vào index -> commit nuốt 288 dòng của W09.
#
# BÀI HỌC: kiểm index TẠI PreToolUse không bao giờ đủ — nó đo TRƯỚC, lệnh chạy SAU, và
# khoảng cách đo được ở đây là 56 giây. Đường duy nhất miễn nhiễm khe đua là bắt lệnh
# NÊU ĐÍCH DANH đường dẫn: `git commit -m "…" -- <paths>` chỉ lấy đúng các đường dẫn ấy,
# index có gì thêm cũng không theo vào.
#
# VÌ SAO CHẶN CẢ KHI INDEX ĐANG SẠCH: sạch lúc kiểm ≠ sạch lúc chạy (đúng 56 giây trên).
# VÌ SAO CHỈ ÁP CHO PHIÊN WORKER: main/manager điều phối cả cây, commit gom là việc của nó.
# VÌ SAO CHỈ KHI CÓ ≥1 WORKER KHÁC SỐNG: một mình trong cây thì không cuốn của ai — chặn
# lúc đó là chặn oan, mà "cổng chặn oan là cổng bị lách" (đúng cách W07 đã lách hôm nay).
# CẤM VÁ THEO CÚ PHÁP: nhóm lệnh dưới đây liệt kê theo HÀNH VI (gói cả index / huỷ cả cây),
# không theo cú pháp vừa gây hoạ — ba lần 26/08 · 27/08 · 18/09 đều vì vá theo cú pháp.
def _worker_khac_dang_song(cwd: str, aid: str, WCE):
    """(số worker KHÁC đang sống, tên W##). Không đo được -> (None, [])."""
    try:
        if WCE.project_dir(cwd) is None:
            return None, []
        song, xac = WCE.running_workers(cwd)
    except Exception:
        return None, []
    ten = []
    # `xac` gồm con đã trả báo cáo (không còn gõ lệnh) LẪN con "không rõ" (mất nguồn tất
    # định, phần tử thứ 6) — con không rõ vẫn có thể đang `git add`, nên vẫn tính.
    for w in list(song) + [w for w in xac if len(w) > 5 and w[5]]:
        if str(w[1]) == aid:
            continue
        t = WCE.so_worker(w, cwd)
        if t and t not in ten:
            ten.append(t)
    return len(ten), ten


def _co_pathspec(sau):
    """Lệnh có nêu đường dẫn sau `--` không."""
    return "--" in sau and any(not t.startswith("-") for t in sau[sau.index("--") + 1:])


PATHSPEC_VO_VET_ROI = {".", "./", ":/", "*", "'*'", "-A", "--all"}


def _co_duong_dan(sau):
    """Lệnh có nêu đường dẫn không — sau `--` hoặc token trông như đường dẫn.

    W15: `_co_pathspec` cũ chỉ nhìn sau `--`, nên `git reset src/lib/x.ts` (hợp lệ, có nêu
    đích danh) vẫn bị xếp vào nhóm "vơ vét cả cây" -> chặn oan.
    """
    return _co_pathspec(sau) or bool(_duong_sau_co(sau))


def lenh_gom_ca_cay(cac_lenh, va_mu=()):
    """[(nhãn lệnh, vì sao nguy hiểm)] — lệnh gói/huỷ CẢ CÂY mà không nêu đích danh.

    `va_mu` = các lệnh áp bản vá mà cổng KHÔNG đọc nổi nguồn vá (W15) -> coi như không nêu
    đích danh: bản vá có thể đụng tệp bất kỳ của bất kỳ ai.
    """
    ra = []
    for nhan, ten_con in va_mu:
        ra.append((nhan, "`git %s` áp một bản vá mà cổng KHÔNG đọc được nguồn (đến từ tiến "
                         "trình khác / stdin không bắt được) — không biết nó đụng tệp của ai. "
                         "Ghi bản vá ra TỆP rồi áp lại thì cổng đọc được và cho qua"
                   % ten_con))
    for tok in cac_lenh:
        nhan = " ".join(tok)
        sau = la_git(tok, "commit")
        if sau is not None:
            if _co_pathspec(sau):
                continue                                   # đã nêu đích danh -> an toàn
            if "--amend" in sau and ({"--only", "-o"} & set(sau)):
                continue                                   # chỉ sửa lời nhắn -> an toàn
            ra.append((nhan, "`git commit` không nêu đường dẫn sau `--` thì gói TOÀN BỘ "
                             "index tại thời điểm nó CHẠY, không phải lúc bạn vừa kiểm"))
            continue
        sau = la_git(tok, "stash")
        if sau is not None:
            con = next((t for t in sau if not t.startswith("-")), "")
            if con in ("", "push", "save", "clear") and not _co_duong_dan(sau):
                ra.append((nhan, "`git stash` không kèm đường dẫn CẤT SẠCH thay đổi của "
                                 "mọi worker trong cây — họ đang sửa dở thì mất trắng"))
            # W15 — đo 18/09/2026: `stash pop` mang tệp trong ngăn cất TRỞ LẠI cây của người
            # gõ (ngăn cất là của CHUNG, mục trên cùng có thể do worker khác cất); `stash
            # apply --index` còn đặt thẳng vào chỗ chờ. git KHÔNG nhận đường dẫn cho pop/apply
            # nên không có cách nêu đích danh -> luôn xếp vào nhóm này.
            elif con in ("pop", "apply", "drop", "branch"):
                ra.append((nhan, "`git stash %s` lấy/huỷ mục trong ngăn cất DÙNG CHUNG — mục "
                                 "trên cùng có thể là việc dang dở worker khác vừa cất; "
                                 "git không nhận đường dẫn cho lệnh này" % con))
            continue
        sau = la_git(tok, "reset")
        if sau is not None:
            if not _co_duong_dan(sau):
                ra.append((nhan, "`git reset` không nêu đường dẫn đụng CẢ chỗ chờ dùng chung: "
                                 "`--hard` ném bỏ thay đổi của cả cây, bản thường gỡ khỏi chỗ "
                                 "chờ đúng phần worker khác vừa đặt vào"))
            continue
        # W15 — `git read-tree` thay TOÀN BỘ chỗ chờ bằng nội dung một cây; git không nhận
        # đường dẫn cho nó (đo: sau `read-tree HEAD` phần vừa `git add` biến sạch).
        sau = la_git(tok, "read-tree")
        if sau is not None:
            ra.append((nhan, "`git read-tree` GHI ĐÈ toàn bộ chỗ chờ dùng chung bằng nội dung "
                             "một cây — phần worker khác vừa đặt vào biến mất"))
            continue
        sau = la_git(tok, "update-index")
        if sau is not None:
            if not _co_duong_dan(sau):
                ra.append((nhan, "`git update-index` không nêu đường dẫn (vd `--index-info` đọc "
                                 "từ stdin) ghi thẳng vào chỗ chờ dùng chung"))
            continue
        # W15 — đo 18/09/2026: các lệnh này ghi vào chỗ chờ / đổi nội dung CẢ CÂY, không có
        # đường nêu đích danh tệp. `merge nhanh2` khi cây đang bẩn đã đổi nội dung
        # `src/lib/fulfill/a.ts` ngay dưới tay người đang mở nó.
        for ten_con in ("cherry-pick", "revert", "merge", "rebase", "am"):
            sau = la_git(tok, ten_con)
            if sau is None:
                continue
            if set(t for t in sau if t.startswith("-")) & CO_THOAT_TRANG_THAI:
                break              # `--abort/--continue/--skip/--quit` là đường THOÁT
            ra.append((nhan, "`git %s` ghi vào chỗ chờ và đổi nội dung cây làm việc dùng "
                             "chung; không có cách nêu đích danh tệp" % ten_con))
            break
        else:
            # W15 — đo 18/09/2026: đổi nhánh khi cây đang bẩn thì việc dang dở của worker
            # khác ĐI THEO sang nhánh mới (chỗ chờ mang nguyên `b.tsx`) và tệp họ đang mở
            # (`a.ts`) đổi nội dung theo nhánh đích.
            for ten_con in ("checkout", "switch"):
                sau = la_git(tok, ten_con)
                if sau is None:
                    continue
                duong = [t for t in sau if not t.startswith("-")]
                if any(d in PATHSPEC_VO_VET_ROI for d in duong) or any(
                        c in PATHSPEC_VO_VET_ROI for c in sau if c.startswith("-")):
                    ra.append((nhan, "`git %s` với pathspec vơ vét khôi phục ĐÈ lên tệp worker "
                                     "khác đang sửa" % ten_con))
                elif not _co_duong_dan(sau):
                    ra.append((nhan, "`git %s` đổi nhánh cho CẢ cây dùng chung: việc dang dở "
                                     "của worker khác đi theo sang nhánh mới, tệp họ đang mở "
                                     "đổi nội dung ngay dưới tay" % ten_con))
                break
            else:
                sau = la_git(tok, "restore")
                if sau is not None:
                    duong = [t for t in sau if not t.startswith("-")]
                    if any(d in PATHSPEC_VO_VET_ROI for d in duong) or any(
                            c in PATHSPEC_VO_VET_ROI for c in sau if c.startswith("-")):
                        ra.append((nhan, "`git restore` với pathspec vơ vét khôi phục ĐÈ lên "
                                         "tệp worker khác đang sửa"))
                    continue
        sau = la_git(tok, "clean")
        if sau is not None:
            if any(c.startswith("-") and "f" in c for c in sau):
                ra.append((nhan, "`git clean -f` XOÁ tệp chưa theo dõi của mọi worker "
                                 "(ảnh nghiệm thu, tệp mới chưa add…)"))
            continue
        # W15 — `git worktree add/list/prune` KHÔNG rò việc của ai (đo: cây phụ có chỗ chờ
        # RIÊNG, commit trần trong cây phụ không cuốn tệp đang stage ở cây chính) -> cho qua.
        # Riêng `remove --force` xoá được cây phụ ĐANG BẨN: bản không `--force` đã từ chối
        # ("contains modified files"), `--force` xoá trắng việc dang dở của người đang dùng nó.
        sau = la_git(tok, "worktree")
        if sau is not None:
            con = next((t for t in sau if not t.startswith("-")), "")
            if con == "remove" and any(c in ("-f", "--force") for c in sau):
                ra.append((nhan, "`git worktree remove --force` xoá cây phụ KỂ CẢ khi trong đó "
                                 "còn việc chưa commit — bản không `--force` đã từ chối đúng vì "
                                 "lẽ đó"))
    return ra


def kiem_gom_ca_cay(data, cac_lenh, cwd: str, cmd_goc: str = ""):
    """(quyết định, lời) — 'deny' / 'nhac' / '' (không áp). Fail-open mọi chỗ mù."""
    try:
        va_mu = duong_tu_ban_va(cac_lenh, cmd_goc, goc_lam_viec(cac_lenh, cwd))[1]
    except Exception:
        va_mu = []
    pham = lenh_gom_ca_cay(cac_lenh, va_mu)
    if not pham:
        return "", ""
    jl = duong_transcript_worker(data)
    if not jl:
        return "", ""                                  # main/manager -> không áp
    WCE = _nap("worker_cap_enforce")
    if WCE is None:
        return "", ""
    aid = str(data.get("agent_id") or "")
    n, ten = _worker_khac_dang_song(cwd, aid, WCE)
    so_minh = so_worker_cua_luot(data)
    cach_dung = (
        "CÁCH ĐÚNG — nêu ĐÍCH DANH đường dẫn, git chỉ lấy đúng những cái đó:\n"
        "    git commit -m \"…\" -- src/lib/abc/xyz.ts src/app/def/page.tsx\n"
        "    git commit -F /tmp/msg.txt -- <đường dẫn>          # lời nhắn dài để ở tệp\n"
        "    git stash push -- <đường dẫn>                      # cất RIÊNG phần của mình\n"
        "    git restore --staged -- <đường dẫn>                # gỡ RIÊNG tệp của mình")
    bang = "\n".join("    · %s\n        %s" % (l, v) for l, v in pham)
    if n is None:
        return "nhac", ("NHẮC — không đo được có bao nhiêu worker khác đang chạy, nên cổng "
                        "KHÔNG chặn. Nhưng lệnh này gói/huỷ cả cây:\n%s\n\n%s"
                        % (bang, cach_dung))
    if n == 0:
        return "nhac", ("NHẮC — cây lúc này chỉ có mình bạn nên cổng cho qua. Lệnh này gói/huỷ "
                        "cả cây:\n%s\n\nCó worker thứ hai vào là hỏng, nên quen tay kiểu này "
                        "vẫn hơn:\n%s" % (bang, cach_dung))
    CT = _nap("cua_thoat")
    if CT is not None:
        try:
            _khoa = "%s|gom|%s" % (so_minh or aid, "|".join(sorted(l for l, _ in pham)))
            if CT.lay(TEN_CONG_VUNG, ai=(so_minh or aid), cwd=cwd, khoa=_khoa):
                _ghi_log_vung("CỬA THOÁT (gom cả cây)\t%s\t%s"
                              % (so_minh or aid, "; ".join(l for l, _ in pham)[:300]))
                return "", ""
        except Exception:
            pass
    _ghi_log_vung("CHẶN (gom cả cây)\t%s\tcùng cây: %s\t%s"
                  % (so_minh or aid, ", ".join(ten), "; ".join(l for l, _ in pham)[:300]))
    return "deny", (
        "CHẶN — lệnh gói/huỷ CẢ CÂY trong lúc còn %d worker khác đang làm (%s).\n\n%s\n\n"
        "VÌ SAO CHẶN DÙ BẠN VỪA KIỂM INDEX THẤY SẠCH: cổng đo TRƯỚC khi lệnh chạy, không "
        "phải lúc nó chạy. Đo thật ca hôm nay 18/09/2026: W07 tự đối chiếu `git diff "
        "--cached --name-only` lúc 11:11:45 thấy đúng 7 tệp của mình, tự cấp `git-scope-ok` "
        "rồi commit trần; lệnh mất 56 GIÂY mới chạy xong (lint-staged), và trong 56 giây đó "
        "`card-dialog.tsx` của worker khác vào index -> commit `f13253dc` nuốt 288 dòng việc "
        "đang dở của W09, `main` gãy build. Kiểm kỹ hơn KHÔNG cứu được khe này — chỉ có nêu "
        "đích danh đường dẫn mới miễn nhiễm.\n\n%s\n\n"
        "Lời nhắn dài thì `cat > /tmp/msg.txt <<'EOF' … EOF` rồi `git commit -F /tmp/msg.txt "
        "-- <đường dẫn>`.\n"
        "Chuỗi `git-scope-ok` KHÔNG mở được cổng này (đó đúng là đường W07 đã lách hôm nay). "
        "Manager đã chốt thì mở cửa thoát dùng-một-lần, có ghi nhật ký (P138: CHỈ đúng thợ "
        "có tên sau `--cho` lấy được, cờ vô chủ không ai lấy được):\n"
        "    python3 ~/.claude/universal-hooks/cua_thoat.py mo %s \"<lý do >= 15 ký tự>\" --cho %s"
    ) % (n, ", ".join(ten) or "không tra được tên", bang, cach_dung, TEN_CONG_VUNG,
         so_minh or aid or "<W##>")


def _so_minh_cua(jl: str) -> str:
    try:
        with open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
            mo_ta = str((json.load(fh) or {}).get("description") or "")
        m = re.match(r"\s*W(\d+)\b", mo_ta, re.I)
        return "W%02d" % int(m.group(1)) if m else ""
    except Exception:
        return ""


def _pham_ngoai_vung(data, duong, vo_vet, cwd: str, cac_goc, bo_khong_vung: bool = False):
    """LÕI SO VÙNG dùng chung cho nhánh git (tầng 2) và nhánh Edit/Write (P138 bước 2).

    Trả None = cho qua; ngược lại (pham, vung_khai, jl). Điều kiện chặn giữ NGUYÊN của
    `kiem_ngoai_vung` cũ — chỉ tách ra để nhánh Edit/Write ăn đúng một luật.
    `bo_khong_vung` (chỉ nhánh Edit): đường dẫn `chuan_vung` rỗng (`/tmp`, scratchpad,
    kho ngoài) luôn qua, kể cả brief thuần đọc — thợ `GHI: -` vẫn phải viết được tệp nháp.
    """
    jl = duong_transcript_worker(data)
    if not jl:
        return None                        # main / không tra ra transcript agent -> qua
    brief = brief_worker(jl)
    if not brief:
        return None
    WCE = _nap("worker_cap_enforce")
    if WCE is None:
        return None
    try:
        WCE._GOC_KHO = list(cac_goc or []) or cwd     # W39: xem `la_thu_muc_goc`
    except Exception:
        pass
    vung_khai, nguon = WCE.vung_viec_moi(brief)
    if nguon == "thieu-khai":
        # Brief cũ không có dòng `GHI:` -> tương thích ngược, y hệt cổng trùng vùng.
        # Cổng thả worker đã chặn brief thiếu khai ngay từ đầu vào, không chặn lần hai ở đây.
        return None
    # `vung_viec_moi` trả 'khai-rong' cho HAI ca KHÁC HẲN NHAU, gộp lại là chặn oan nặng
    # (đo được 18/09/2026 ngay trong lượt vá): (a) brief khai `GHI: -` — thuần đọc, đúng là
    # phải chặn mọi `git add`; (b) brief khai đường dẫn THẬT nhưng nằm ngoài cây mã nên
    # `chuan_vung` trả rỗng (`/tmp/...`, kho luật `~/PycharmProjects/univ3-ssot`). Ca (b)
    # mà chặn sạch thì worker sửa kho ngoài không commit nổi gì. Phân biệt bằng TIỀN TỐ
    # THÔ của dòng khai, không bằng nhãn nguồn.
    tt = tien_to_khai(brief, WCE)
    thuan_doc = not tt and not vung_khai
    pham = []                              # [(đường dẫn, vùng)]
    for d in duong:
        if bo_khong_vung and not WCE.chuan_vung(d) and not _duoi_tien_to(d, tt, cac_goc):
            continue
        if thuan_doc:                      # brief khai `GHI: -`
            pham.append((d, WCE.chuan_vung(d)))
            continue
        if _duoi_tien_to(d, tt, cac_goc):
            continue
        v = WCE.chuan_vung(d)
        if not v:
            continue                       # không đo được vùng -> KHÔNG đoán, cho qua
        if v in vung_khai or any(v == k or v.startswith(k.rstrip("/") + "/")
                                 for k in vung_khai):
            continue
        pham.append((d, v))
    if vo_vet:
        pham.append(("(cả cây làm việc — cờ/pathspec vơ vét)", ""))
    if not pham:
        return None
    return pham, vung_khai, jl


def _loi_chan_vung(data, pham, vung_khai, jl, cwd: str, kieu: str = "git") -> str:
    """Cửa thoát + lời chặn. "" = cửa thoát đang mở cho đúng thợ này -> qua."""
    aid = str(data.get("agent_id") or "")
    so_minh = _so_minh_cua(jl)

    CT = _nap("cua_thoat")
    if CT is not None:
        try:
            # W39: `khoa` = đúng tập tệp ngoài vùng + mã thợ -> commit hỏng rồi chạy lại y
            # nguyên thì không phải mở cờ lần hai (cua_thoat.HAN_DUNG_LAI_PHUT).
            _khoa = "%s|%s" % (so_minh or aid, "|".join(sorted(d for d, _ in pham)))
            if CT.lay(TEN_CONG_VUNG, ai=(so_minh or aid), cwd=cwd, khoa=_khoa):
                _ghi_log_vung("CỬA THOÁT%s\t%s\t%s"
                              % ("" if kieu == "git" else " (%s)" % kieu, so_minh or aid,
                                 ", ".join(d for d, _ in pham)[:300]))
                return ""
        except Exception:
            pass

    WCE = _nap("worker_cap_enforce")
    dong = []
    for d, v in pham:
        giu = ai_giu_vung(cwd, v, aid, WCE) if (v and WCE is not None) else ""
        dong.append("    · %s   -> vùng `%s`%s"
                    % (d, v or "(ngoài cây mã)",
                       ("   ⚠️ %s ĐANG GIỮ vùng này" % giu) if giu else ""))
    khai = ", ".join("`%s`" % x for x in sorted(vung_khai)) or "`-` (brief khai KHÔNG ghi gì)"
    _ghi_log_vung("CHẶN%s\t%s\tkhai=%s\tngoài=%s"
                  % ("" if kieu == "git" else " (%s)" % kieu, so_minh or aid, khai,
                     ", ".join(d for d, _ in pham)[:300]))
    ten = so_minh or "worker này"
    vung_cho = " ".join(sorted({v for _, v in pham if v})) or "<vùng>"
    if kieu == "git":
        mo_dau = ("CHẶN — lệnh này đụng tệp NGOÀI vùng `GHI:` mà brief của %s đã khai.\n\n"
                  "Ngoài vùng:\n%s\n\nVùng khai của bạn: %s\n\n"
                  "Vì sao chặn dù bạn đã gõ ĐÍCH DANH từng tệp: hôm nay 18/09/2026 thợ W07 khai "
                  "`GHI: src/lib/fulfill` rồi `git add src/app/pipeline/_components/card-dialog.tsx` — "
                  "đích danh, không vơ vét, nên cổng cũ CHO QUA. Commit `f13253dc` nuốt 288 dòng việc "
                  "đang dở của W09; nửa còn lại kẹt ở chỉ mục -> `main` gãy build, cả lô deploy kẹt.\n\n"
                  % (ten, "\n".join(dong), khai))
    else:
        mo_dau = ("CHẶN — `%s` ghi tệp NGOÀI vùng `GHI:` mà brief của %s đã khai (P138).\n\n"
                  "Ngoài vùng:\n%s\n\nVùng khai của bạn: %s\n\n"
                  "Vì sao chặn NGAY lần sửa đầu: ca P137 11/10/2026 thợ viết mã ngoài vùng suốt "
                  "30 phút (tsc xanh, 92 ca thử xanh) rồi mới bị cổng commit chặn — đứng 35%% sau "
                  "44 phút, điều phối không hay biết. Viết thêm cũng không commit được.\n\n"
                  % (str(data.get("tool_name") or "Edit"), ten, "\n".join(dong), khai))
    return mo_dau + (
        "ĐI TIẾP THẾ NÀO — LÀM ĐÚNG THỨ TỰ, KHÔNG viết thêm tệp ngoài vùng:\n"
        "  1. Commit phần đã làm TRONG vùng (nêu đích danh từng tệp: "
        "`git commit -F <tệp lời> -- <tệp trong vùng>`).\n"
        "  2. Gửi điều phối MỘT dòng: `SendMessage` tới `main`, nội dung "
        "`KẸT VÙNG: %s · %s` — main đang rảnh thì tin thành lượt mới của main trong vài giây "
        "(đo 11/10: 91/100 tin).\n"
        "  3. KẾT THÚC LƯỢT NGAY. Báo cáo cuối ghi dòng `CHỜ VÙNG: %s` — kết thúc lượt là "
        "đường chắc chắn nhất để điều phối biết khi anh vắng; máy đẻ vé thả lại mang theo "
        "dòng đó.\n"
        "  · Tệp đó là của worker khác -> `git restore --staged <tệp>` / để nguyên, commit "
        "phần của mình rồi báo cáo là đã đụng nhầm.\n"
        "  · Chỉ khi manager đã CHỐT thì mở cửa thoát (dùng một lần, có ghi nhật ký, CHỈ "
        "đúng thợ có tên sau `--cho` lấy được) — phải mở ở MỘT LỆNH RIÊNG chạy TRƯỚC, gộp "
        "chung lệnh git là vô tác dụng (cổng đọc cờ trước khi lệnh của bạn kịp chạy):\n"
        "      python3 ~/.claude/universal-hooks/cua_thoat.py mo %s \"<lý do >= 15 ký tự>\" "
        "--cho %s\n\n"
        "Lưu ý: chuỗi `git-scope-ok` KHÔNG mở được tầng này — nó chỉ tắt tầng chống vơ vét. "
        "Vùng là giao kèo giữa các worker, không phải thứ tự cho mình miễn."
    ) % (ten, vung_cho, vung_cho, TEN_CONG_VUNG, so_minh or aid or "<W##>")


def kiem_ngoai_vung(data, cac_lenh, cwd: str, cmd_goc: str = "") -> str:
    """Lời CHẶN nếu lệnh đụng ngoài vùng `GHI:` của worker; "" = cho qua.

    Fail-open từng bước: mù chỗ nào thì cho qua chỗ đó, KHÔNG đoán.

    W15 18/09/2026: gom ĐỦ HỌ LỆNH ghi vào chỗ chờ / cây, không riêng `git add` —
    `git apply --cached` (đúng đường W10 đã đưa `card-dialog.tsx` vào chỗ chờ lúc 03:43:47),
    `git am`, `update-index`, `rm`, `mv`, `restore`, `checkout <rev> -- tệp`, `reset -- tệp`,
    `stash push -- tệp`. Vá theo CÚ PHÁP vừa nổ là sai lầm đã lặp ba lần (26/08 · 27/08 ·
    18/09) nên lần này liệt theo HÀNH VI, đo từng lệnh trong repo hộp cát trước khi đưa vào.
    """
    cac_goc = goc_lam_viec(cac_lenh, cwd)
    duong, vo_vet = pathspec_cua_lenh(cac_lenh)
    them = list(duong_ghi_lenh_khac(cac_lenh))
    them += duong_tu_ban_va(cac_lenh, cmd_goc, cac_goc)[0]
    for d in them:
        if d not in duong:
            duong.append(d)
    if not duong and not vo_vet:
        return ""
    kq = _pham_ngoai_vung(data, duong, vo_vet, cwd, cac_goc)
    if not kq:
        return ""
    pham, vung_khai, jl = kq
    return _loi_chan_vung(data, pham, vung_khai, jl, cwd, "git")


# ── P138 bước 2 — Edit/Write/MultiEdit/NotebookEdit RA NGOÀI VÙNG BỊ CHẶN NGAY LẦN ĐẦU ──
# Cổng commit (tầng 2) chỉ soi `Bash`; sửa tệp bằng Edit/Write không cổng nào chặn, nên thợ
# P137 viết mã ngoài vùng 30 phút rồi mới vấp lúc commit. Chặn ở đây = lỗi `GHI:` lộ ra ở
# lượt sửa đầu tiên, thợ kết thúc lượt trong vài phút, điều phối biết liền.
GHI_TOOL = ("Edit", "Write", "MultiEdit", "NotebookEdit")
RX_CAY_PHU = re.compile(r"/\.claude/worktrees/[^/]+/(.+)$")


def _duong_tuong_doi(p: str, cac_goc) -> str:
    """Đường tuyệt đối trong gốc kho / cây phụ -> tương đối. `chuan_vung` xếp mọi đường có
    `/.claude/` thành `tools/univ3`, nên tệp `src/…` trong cây phụ `.claude/worktrees/x/`
    sẽ bị chặn oan nếu không gọt gốc trước."""
    m = RX_CAY_PHU.search(p)
    if m:
        return m.group(1)
    for g in sorted(cac_goc or [], key=len, reverse=True):
        g = g.rstrip("/")
        if g and p.startswith(g + "/"):
            return p[len(g) + 1:]
    return p


def kiem_sua_tep(data, cwd: str) -> str:
    """Lời CHẶN nếu Edit/Write ghi ra ngoài vùng `GHI:`; "" = qua. Fail-open."""
    ti = data.get("tool_input") or {}
    if not isinstance(ti, dict):
        return ""
    p = str(ti.get("file_path") or ti.get("notebook_path") or "").strip()
    if not p:
        return ""
    cac_goc = goc_lam_viec([], cwd)
    if os.path.isabs(p):
        p = _duong_tuong_doi(os.path.normpath(p), cac_goc)
    kq = _pham_ngoai_vung(data, [p], False, cwd, cac_goc, bo_khong_vung=True)
    if not kq:
        return ""
    pham, vung_khai, jl = kq
    return _loi_chan_vung(data, pham, vung_khai, jl, cwd, str(data.get("tool_name") or "Edit"))

# ── P085 §6.1 — DANH TÍNH DO HỆ THỐNG CHÈN, KHÔNG DO WORKER NHỚ ──────────────────────
# Đo thật 09/09/2026: **0/40** commit gần nhất có trailer `Worker:`, dù
# `docs/DEPLOY-THEO-NHOM.md:244` bắt buộc từ lâu — vì bắt buộc bằng VĂN BẢN là xác suất.
# Hệ quả: muốn biết commit nào của worker nào phải map `sha`->vé, tra ngược hay đứt.
#
# WHY CHÈN chứ không CHẶN: chặn commit là chặn đúng lúc worker vừa làm xong, dễ làm nó
# loay hoay rồi manager mở cửa thoát -> cổng thành đồ trang trí (bài học `P080:328`
# "cổng chặn oan là cổng bị lách"). Sửa hộ thì worker không cần biết luật này tồn tại.
RX_COMMIT = re.compile(r"(?<![\w-])git(\s+-[^\s]+\s+[^\s]+)*\s+commit(?![\w-])")
NHAT_KY_TRAILER = os.path.expanduser("~/.claude/dod/%s/.thieu-trailer.log")


def so_worker_cua_luot(data_hoac_transcript) -> str:
    """`W##` của chính agent đang chạy lệnh — đọc `description` trong `agent-*.meta.json`.

    W13 18/09/2026 — SỬA MỘT LỖI ĐO ĐƯỢC: bản cũ nhận CHUỖI `transcript_path` rồi đòi tên
    tệp chứa "agent-". Payload thật của PreToolUse (đo bằng cách cho hook ghi nguyên gói ra
    tệp rồi chạy `git status` trong phiên worker, 18/09/2026 11:38) có
    `transcript_path` = transcript PHIÊN CHA `<projects>/<session>.jsonl`; danh tính worker
    nằm ở trường RIÊNG `agent_id`. Nên nhánh cũ CHƯA BAO GIỜ khớp trong phiên worker —
    khớp với nhật ký `.thieu-trailer.log` (đầy dòng "không suy được W##") và với việc
    11/12 commit gần nhất không có trailer `Worker=`.

    Nhận CẢ gói `data` (đường mới) lẫn chuỗi transcript (đường cũ, giữ cho ca thử cũ).
    Không suy ra được -> "" và TUYỆT ĐỐI không đoán số.
    """
    try:
        if isinstance(data_hoac_transcript, dict):
            jl = duong_transcript_worker(data_hoac_transcript)
        else:
            t = str(data_hoac_transcript or "")
            jl = t if (t.endswith(".jsonl") and "agent-" in os.path.basename(t)) else ""
        if not jl:
            return ""
        with open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as f:
            mo_ta = str((json.load(f) or {}).get("description") or "")
        m = re.match(r"\s*W(\d+)\b", mo_ta, re.I)
        return "W%02d" % int(m.group(1)) if m else ""
    except Exception:
        return ""


def _vung_du_lieu(cmd: str):
    """[(đầu, cuối)] các đoạn là DỮ LIỆU trong chuỗi lệnh (thân heredoc, mã nhúng `-c`)."""
    ra = []
    for rx in (RX_THAN_HEREDOC, RX_MA_NHUNG):
        try:
            for m in rx.finditer(cmd or ""):
                ra.append((m.start(), m.end()))
        except Exception:
            pass
    return ra


def viec_cua_luot(data) -> str:
    """Số hiệu việc (`20261001-L05.1`) khai ở brief của thợ đang chạy lệnh — "" nếu không có.
    W39 (P114 hướng A): để commit mang trailer `Viec=` nối được về sổ lệnh."""
    try:
        jl = duong_transcript_worker(data)
        if not jl:
            return ""
        SL = _nap("so_lenh")
        loai, gt = SL.boc_viec(brief_worker(jl)) if SL is not None else ("", "")
        return gt if loai == "so" else ""
    except Exception:
        return ""


def chen_trailer(cmd: str, so: str, viec: str = "") -> str:
    """Thêm `--trailer Worker=W##` vào ĐÚNG một lệnh `git commit` đầu tiên; "" = không đụng.

    W15 18/09/2026 — LỖI ĐO ĐƯỢC NGAY TRONG LƯỢT NÀY: bản cũ tìm `git commit` trên chuỗi
    lệnh THÔ nên chèn trailer vào THÂN HEREDOC. Lệnh thật là `python3 - <<PY … PY` có dòng
    dữ liệu `("git commit -m x", "nhãn")`; hook chèn vào giữa chuỗi Python ->
    `SyntaxError: invalid syntax`, lệnh chết mà worker không hiểu vì sao. Cùng họ bệnh với
    `RX_THAN_HEREDOC` mà chính tệp này đã phải thêm cho hai tầng chặn: dữ liệu không phải lệnh.
    """
    du_lieu = _vung_du_lieu(cmd or "")
    m = None
    for ung in RX_COMMIT.finditer(cmd or ""):
        if any(d <= ung.start() < c for d, c in du_lieu):
            continue
        m = ung
        break
    if not m:
        return ""
    if "--trailer" in cmd and "Worker=" in cmd:
        return ""
    if re.search(r"(?mi)^\s*Worker:\s*W\d+", cmd or "") or "Worker: %s" % so in cmd:
        return ""
    if "--amend" in cmd:            # `--amend` viết lại commit cũ -> không phải chỗ khai danh tính
        return ""
    them = ' --trailer "Worker=%s"' % so
    if viec and "Viec=" not in cmd:
        them += ' --trailer "Viec=%s"' % viec
    return cmd[:m.end()] + them + cmd[m.end():]


def ghi_thieu_trailer(cwd: str, cmd: str):
    try:
        p = NHAT_KY_TRAILER % os.path.basename(os.path.abspath(cwd or ".").rstrip("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write("%s  không suy được W## -> KHÔNG đụng lệnh: %s\n"
                    % (time.strftime("%Y-%m-%d %H:%M:%S"), (cmd or "")[:160]))
    except OSError:
        pass


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    if str(data.get("hook_event_name") or "") != "PreToolUse":
        return 0
    if str(data.get("tool_name") or "") in GHI_TOOL:
        try:
            ly = kiem_sua_tep(data, str(data.get("cwd") or os.getcwd()))
        except Exception:
            ly = ""
        if ly:
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": ly}}, sys.stdout, ensure_ascii=False)
        return 0
    if str(data.get("tool_name") or "") != "Bash":
        return 0
    try:
        cmd = str((data.get("tool_input") or {}).get("command") or "")
        if not cmd:
            return 0
        if "git" not in cmd:
            return 0
        cwd = str(data.get("cwd") or os.getcwd())
        # W13 18/09/2026 — chuỗi `git-scope-ok` CHỈ tắt tầng 1 (chống vơ vét), KHÔNG tắt
        # tầng VÙNG. WHY: tầng 1 nói về "cây này có mình tôi không" — worker tự biết được.
        # Tầng vùng nói về GIAO KÈO giữa các worker: một mình worker không có quyền tự
        # tuyên bố vùng của người khác là của mình. Muốn qua thì mở cửa thoát dùng-một-lần
        # `git-ngoai-vung` (có ghi nhật ký 2 nơi), để manager còn soi lại được.
        thoat_inline = ESCAPE in cmd
        cac_lenh = tach_lenh(bo_du_lieu(cmd))

        # ── TẦNG 2 (chạy TRƯỚC): vùng `GHI:`. Đặt trước tầng 1 vì hai nhánh của tầng 1
        # (`NHẮC git add <thư mục>` trả allow, và `git-scope-ok`) đều KẾT THÚC lượt sớm —
        # để sau thì đúng ca hôm nay `git add <thư mục ngoài vùng>` lại lọt lần nữa.
        ly_do_vung = kiem_ngoai_vung(data, cac_lenh, cwd, cmd)
        if ly_do_vung:
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": ly_do_vung}}, sys.stdout, ensure_ascii=False)
            return 0
        qd_gom, loi_gom = kiem_gom_ca_cay(data, cac_lenh, cwd, cmd)
        if qd_gom == "deny":
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": loi_gom}}, sys.stdout, ensure_ascii=False)
            return 0
        if qd_gom == "nhac":
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": loi_gom,
                "additionalContext": loi_gom}}, sys.stdout, ensure_ascii=False)
            return 0
        if thoat_inline:
            return 0

        vi_pham = None      # (nhãn lệnh, giải thích)
        canh_bao = None     # (thư mục, [tệp])
        commit_tran = None  # (nhãn lệnh, [tệp lạ trong index])

        # Đường dẫn được `git add` NGAY TRONG lệnh Bash này -> phần chắc chắn của người gõ.
        duong_add = []
        for tok in cac_lenh:
            s2 = la_git(tok, "add", "stage")
            if s2:
                duong_add += [t for t in s2 if not t.startswith("-")]

        for tok in cac_lenh:
            sau = la_git(tok, "add", "stage")
            if sau is not None:
                co = [t for t in sau if t.startswith("-")]
                duong = [t for t in sau if not t.startswith("-")]
                if any(c in CO_VO_VET for c in co) or any(d in PATH_VO_VET for d in duong):
                    vi_pham = (" ".join(tok),
                               "cờ/pathspec này stage MỌI thay đổi trong cây làm việc, "
                               "kể cả phần worker khác đang viết dở")
                    break
                # pathspec là thư mục -> chỉ NHẮC, kèm danh sách tệp bên trong
                for d in duong:
                    p = os.path.join(cwd, d)
                    if os.path.isdir(p):
                        pre = d.rstrip("/") + "/"
                        trong = [f for f in file_dang_doi(cwd) if f.startswith(pre)]
                        if len(trong) >= 2:
                            canh_bao = (d, trong)
                continue
            sau = la_git(tok, "commit")
            if sau is not None:
                for t in sau:
                    if t in ("-a", "--all") or (
                            re.fullmatch(r"-[a-zA-Z]+", t or "") and "a" in t[1:]):
                        vi_pham = (" ".join(tok),
                                   "`-a` tự động stage MỌI tệp đã theo dõi bị sửa, "
                                   "kể cả của worker khác")
                        break
                if vi_pham:
                    break
                # `--amend` gói TOÀN BỘ index vào commit cũ. Có `--only` (không kèm
                # đường dẫn) thì chỉ sửa lời nhắn -> an toàn, cho qua.
                if "--amend" in sau and not ({"--only", "-o"} & set(sau)):
                    dang_stage = [f for f in chay(
                        ["git", "diff", "--cached", "--name-only"], cwd).split("\n") if f.strip()]
                    if dang_stage:
                        vi_pham = (" ".join(tok),
                                   "`--amend` gói CẢ INDEX vào commit cũ. Index lúc này có "
                                   "%d tệp đang stage (%s) — trong cây dùng chung KHÔNG có "
                                   "cách nào biết tệp nào của bạn. `--amend` còn viết lại "
                                   "sha nên vé deploy đăng ký theo sha cũ thành vé chết"
                                   % (len(dang_stage), ", ".join(dang_stage[:5])))
                        break
                # `git commit` TRẦN (không pathspec sau `--`) commit CẢ index dùng chung.
                # 27/08/2026 commit 50187a6 của worker email đã cuốn theo
                # `scripts/check-prod-demo-parity.sh` mà worker hạ tầng vừa `git add`.
                if "--amend" not in sau and "--" not in sau:
                    la_index = [f for f in chay(
                        ["git", "diff", "--cached", "--name-only"], cwd).split("\n")
                        if f.strip() and not da_bao_phu(duong_add, f)]
                    if la_index:
                        commit_tran = (" ".join(tok), la_index)
                        break

        if vi_pham:
            lenh, vi_sao = vi_pham
            dang_doi = file_dang_doi(cwd)
            bang = "\n".join("    · " + f for f in dang_doi[:25]) or "    (không đọc được)"
            them = "" if len(dang_doi) <= 25 else "\n    … và %d tệp nữa" % (len(dang_doi) - 25)
            reason = (
                "CHẶN — `%s` vơ vét cả cây làm việc.\n\n"
                "Vì sao: %s.\n\n"
                "Dự án này chạy NHIỀU WORKER trên CÙNG một thư mục. Đúng lệnh kiểu này ngày "
                "26/08/2026 đã cuốn phần dang dở của worker khác vào commit deeddc1 "
                "(supplier-actions.ts gọi `probeSupplierOrderWithRetry` mà push-verify.ts "
                "chưa export) -> nhánh main không biên dịch được, lô deploy gãy.\n\n"
                "ĐANG THAY ĐỔI trong cây lúc này (%d tệp — KHÔNG phải tất cả đều của bạn):\n%s%s\n\n%s"
            ) % (lenh, vi_sao, len(dang_doi), bang, them, LOI_KHUYEN)
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason}}, sys.stdout, ensure_ascii=False)
            return 0

        if commit_tran:
            lenh, la = commit_tran
            reason = (
                "CHẶN — `%s` sẽ commit CẢ index dùng chung.\n\n"
                "Index đang có %d tệp mà chính lệnh này KHÔNG `git add`:\n%s%s\n\n"
                "Trong cây nhiều worker, index là của chung. Ngày 27/08/2026 commit 50187a6 "
                "của worker email đã cuốn theo `scripts/check-prod-demo-parity.sh` mà worker "
                "hạ tầng vừa stage — cùng ngày `--amend` cũng cuốn "
                "`docs/NGHIEN-CUU-GMAIL-TU-DONG.md` vào commit 12f7522.\n\n%s\n\n"
                "Chắc chắn cây chỉ có mình bạn -> thêm `git-scope-ok` vào lệnh."
            ) % (lenh, len(la), "\n".join("    · " + f for f in la[:25]),
                 "" if len(la) <= 25 else "\n    … và %d tệp nữa" % (len(la) - 25),
                 LOI_KHUYEN_COMMIT)
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason}}, sys.stdout, ensure_ascii=False)
            return 0

        if canh_bao:
            d, trong = canh_bao
            reason = (
                "NHẮC — `git add %s` sẽ stage %d tệp đang thay đổi trong thư mục đó:\n%s\n\n"
                "Nhiều worker dùng chung cây mã này. Soi lại: tệp nào KHÔNG phải bạn vừa sửa "
                "thì bỏ ra, add đích danh từng tệp của mình."
            ) % (d, len(trong), "\n".join("    · " + f for f in trong[:25]))
            json.dump({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": reason,
                "additionalContext": reason}}, sys.stdout, ensure_ascii=False)
            return 0
        # Không vi phạm gì -> tới lượt việc CHÈN TRAILER (không chặn, không hỏi).
        if RX_COMMIT.search(cmd):
            so = so_worker_cua_luot(data)
            if not so:
                ghi_thieu_trailer(cwd, cmd)
            else:
                viec = viec_cua_luot(data)
                moi = chen_trailer(cmd, so, viec)
                if moi and moi != cmd:
                    json.dump({"hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "updatedInput": dict((data.get("tool_input") or {}), command=moi),
                        "additionalContext": ("hệ thống đã chèn `--trailer \"Worker=%s\"`%s vào "
                                              "lệnh commit — không cần bạn nhớ"
                                              % (so, (" + `Viec=%s`" % viec) if viec else "")),
                    }}, sys.stdout, ensure_ascii=False)
                    return 0
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
