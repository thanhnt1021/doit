#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""worker_cap_enforce.py — TRẦN SỐ WORKER ĐỒNG THỜI + ép gửi việc vào worker đang chạy.

BÀI HỌC THẬT (2026-08-25, máy founder — 10 nhân, 16 GB): điều phối thả **11 worker song
song** trên cùng một dự án. Đo được:
  - load average 228–566, có lúc chỉ còn ~63 MB RAM trống, founder không làm việc được;
  - 8 shell nền, trong đó **6 shell là vòng `until ps aux | grep ftp_push; sleep N`** —
    mỗi worker tự dựng một vòng canh riêng cho CÙNG một tài nguyên;
  - 4 `http.server` mồ côi (8484, 8877, 8899, 8911), 264 tiến trình CoreSimulator;
  - hai worker ghi đè CSS của nhau: một con xoá nhầm 1250 dòng rồi khôi phục từ backup,
    cuốn mất thay đổi của con kia; cache-bust lệch nhau -> giao diện vỡ không đồng nhất;
  - hai worker đẩy FTP cùng lúc -> 9 tệp lệch.

Nguyên văn founder: *"mày phải có quy định là như nào tối đa thôi để máy tính của tao còn
làm được việc. lag quá. chưa kịp thì cho hàng chờ. cái nào cùng worker đang xử lý thì mới
add vào worker chứ???"*

WHY hook chứ không thêm dòng markdown: luật "song song hoá" nằm sẵn trong
`rules/AGENTS-ORCH.md` mà vẫn thả 11 con, vì **không ai NHÌN được tổng số worker đang
chạy tại khoảnh khắc bấm spawn** — mỗi lần gọi `Agent` là một quyết định cục bộ. Chỉ hook
`PreToolUse` mới đọc được trạng thái toàn máy đúng lúc đó.

CÁCH ĐẾM (đo thực nghiệm, không đoán):
  Mỗi subagent có một transcript riêng `~/.claude/projects/<project>/<session>/subagents/
  agent-<id>.jsonl`, được GHI THÊM sau mỗi lượt nó làm việc -> mtime của tệp này là nhịp
  tim. Đã kiểm 3 cách khác và loại:
    - `*.meta.json` KHÔNG có trường trạng thái (chỉ agentType/description/toolUseId);
    - đếm số lần `toolUseId` xuất hiện trong transcript cha: KHÔNG phân biệt được
      (con đang chạy 6 lần, con xong từ hôm qua cũng 2–6 lần);
    - tìm `tool_use_id` trong khối kết quả: worker NGẦM trả kết quả "đã thả nền" NGAY lúc
      spawn -> con đang chạy cũng bị coi là xong.
  `session_id` trong payload hook KHÔNG phải id phiên cha khi hook chạy trong subagent
  (đã kiểm bằng các tệp cờ do hook khác để lại) -> phải suy ra dự án từ `cwd`.

NHÁNH THỨ HAI — cấm mỗi worker tự dựng một VÒNG CANH riêng: lệnh Bash dạng
`until/while ... ps|pgrep ... sleep` bị hỏi lại và chỉ sang khoá dùng chung
`wlock.sh`. Chính sáu vòng canh kiểu này đã ngốn 6 shell nền cùng lúc,
lại canh theo TÊN SCRIPT nên worker dùng script tên khác vẫn lọt qua.

LOẠI XÁC TREO RA KHỎI SỐ ĐẾM (thêm 2026-08-25, sau khi founder nổi giận):
  Worker **đã trả báo cáo cuối** vẫn hiện `running` trên khung điều phối và transcript của
  nó vẫn được ghi thêm mỗi khi một thông báo nền chạm vào (nó trả lời "việc đã xong" rồi
  ngủ tiếp) -> nằm gọn trong cửa sổ 15 phút -> **chiếm chỗ trong trần dù không làm gì**.
  Hôm đó `a31808898ec601ae9` ("Sửa giỏ hàng") hiện 1h38m, gửi lại đúng bản báo cáo cũ 4
  lần; `a5f3e7d9d3deb1f7c` 3 lần. Worker mới bị chặn oan.

  DẤU HIỆU TẤT ĐỊNH — `message.stop_reason` (SỬA 28/08/2026, xem "BẢN CŨ SAI" bên dưới):
  harness ghi transcript agent theo TỪNG KHỐI nội dung, mỗi khối một dòng JSONL; chỉ khối
  CUỐI CÙNG của một lượt model mới mang `stop_reason` khác `null`. Đó chính là tuyên bố
  "lượt này đã kết thúc", và với subagent, hết lượt = **đã trả kết quả về cha**. Nên: đọc
  ngược từ đuôi transcript, bỏ nhiễu (`type=="attachment"`, bản ghi user `isMeta` — tức
  SYSTEM NOTIFICATION / Stop hook feedback), rồi xét bản ghi thật đầu tiên gặp:
    - assistant `stop_reason` ∈ {end_turn, stop_sequence} -> ĐÃ TRẢ BÁO CÁO CUỐI (xác treo)
    - user text MỞ ĐẦU bằng "[Request interrupted by user]" -> ĐÃ BỊ DỪNG        (xác treo)
    - còn lại — kể cả assistant `stop_reason == null` — -> ĐANG CHẠY
  Fail-safe: không đọc/không hiểu được -> coi là ĐANG CHẠY (thà đếm dư còn hơn kill oan).

  BẢN CŨ SAI THẾ NÀO (2 lần kill oan trong ngày 28/08/2026): luật cũ là "assistant có khối
  `text` mà không kèm `tool_use` -> đã xong". Nhưng worker VỪA NÓI VỪA LÀM: nó in một câu
  tường thuật (một bản ghi `text`, `stop_reason: null`) rồi mới gọi tool ở bản ghi kế tiếp.
  Hook chụp đúng khe đó -> phán "đã xong" -> điều phối `TaskStop` thật. Hai nạn nhân đo
  được: một con đang cập nhật phiếu, dừng ở câu *"Cuối cùng: cập nhật §7 các bước và §9 thứ
  tự thi công, §11 cửa duyệt."*; một con đang viết tài liệu, dừng ở *"Now the markdown guide
  — rewritten around the MỚI/CŨ split…"*. Cả hai lúc đó im 0–1 phút.

  ĐO TRÊN DỮ LIỆU THẬT (728 transcript agent của dự án EtsyFulfillChichub):
    - phân bố `(khối, stop_reason)`: `(text, end_turn)` 28 · `(text, null)` 158 ·
      `(tool_use, tool_use)` 877 · `(tool_use, null)` 191 · `(thinking, null)` 565
      -> `text` KHÔNG kèm tool xảy ra 158/186 lần GIỮA CHỪNG, chỉ 28 lần là kết lượt thật;
    - replay từng khoảnh khắc (phán "đã xong" mà transcript CÒN bản ghi sau = sai tất định):
      hàm CŨ sai **12.137** khoảnh khắc, hàm MỚI **392** — và 392 ca đó không phải sai:
      377 ca `end_turn` rồi Stop-hook feedback đánh thức worker (đúng định nghĩa xác treo),
      18 ca `stop_sequence` tương tự, 2 ca là brief TRÍCH NGUYÊN VĂN chuỗi "[Request
      interrupted by user]" (đã bịt bằng `startswith`), 1 ca cha gửi việc mới.

  KHÔNG dùng mốc "im ≥ N phút" làm cách nhận diện, kể cả làm lưới phụ: đo 11.536 khe giữa
  một bản ghi `text/null` và bản ghi kế tiếp của CÙNG worker -> p50 1,9 s · p99 98 s, nhưng
  **51 khe > 3 phút, 4 khe > 5 phút, khe dài nhất 15,5 phút** mà worker vẫn chạy tiếp. Mọi
  ngưỡng dưới 15 phút đều giết oan, còn ngưỡng 15 phút thì trùng `ACTIVE_MIN` -> vô nghĩa.
  Khoảng trống duy nhất (worker xong thật mà harness không đóng dấu `stop_reason`) đã có
  nguồn khác bịt: `<task-notification><status>` của harness về tới transcript cha sau
  **0,1–0,2 giây** (đo 5 ca trong phiên 28/8) và `running_workers` đã hỏi nó qua
  `worker_relapse.ids_ket_thuc`.

  Ba hướng khác đã cân nhắc và LOẠI:
    - tệp `.output` của tác vụ: **không tồn tại** (`find ~/.claude/projects -name '*.output*'`
      ra rỗng); `.meta.json` vẫn không có trường trạng thái nào;
    - so mtime transcript với mốc `100|...` trong `/tmp/claude-bg-progress/<dự án>/*.progress`:
      **không có cách nối** slug tệp progress với `agent-<id>` — worker tự đặt tên slug;
    - hạ cửa sổ 15 phút xuống ngắn hơn: sai bản chất — worker build/deploy dài im lặng 20
      phút vẫn đang chạy, mà xác treo lại bị thông báo nền đánh thức nên luôn "mới".

KHÔNG tự kill: xem §"vì sao không tự dọn" trong rules/AGENTS-ORCH.md §LUẬT SỐ 1. Tóm tắt:
  cả phiên chỉ có MỘT tiến trình `claude` (đã đếm `pgrep`: 42 subagent / 1 tiến trình) nên
  hook không có cách giết riêng một worker mà không giết cả phiên; việc kill để coordinator
  làm bằng `TaskStop` ngay trong lượt nhận báo cáo. Hook chỉ ĐẾM ĐÚNG và NHẮC.

CHẶN (deny) khi: số worker ĐANG THỰC SỰ CHẠY của DỰ ÁN NÀY >= trần (mặc định 3).
HỎI (ask) khi: còn chỗ trống nhưng việc mới TRÙNG MẢNG với một worker đang chạy —
  luật founder: trùng mảng thì `SendMessage` vào chính worker đó, không đẻ con mới.
CHO QUA: dưới trần và không trùng mảng · gọi tool khác · có cửa thoát `worker-cap-ok`.

Fail-open tuyệt đối: lỗi bất kỳ -> exit 0.
"""
import glob
import json
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import worker_queue as WQ          # hàng chờ có lưu bền (worker_queue.py)
except Exception:                       # fail-open: thiếu module thì hook vẫn chạy
    WQ = None
try:
    import worker_relapse as WR        # worker bị dừng giữa chừng -> tự quay lại hàng chờ
except Exception:
    WR = None
try:
    import worker_de_lai as WD         # worker XONG mà tự khai để lại việc -> tự đẻ vé
except Exception:
    WD = None

AGENT_TOOLS = {"Agent", "Task"}

# vòng canh tài nguyên tự chế: phải có ĐỦ 3 mảnh mới tính (while/until + ps/pgrep + sleep)
VONG_CANH = (re.compile(r"(?<![\w-])(while|until)(?![\w-])"),
             re.compile(r"(?<![\w-])(ps|pgrep|pidof)(?![\w-])"),
             re.compile(r"(?<![\w-])sleep(?![\w-])"))

# 26/08/2026: worker `import-pod-folder` ĐƯỢC CẤP khoá ngay lần đầu, nhưng nó tự bọc
# `acquire` trong `until … sleep 60` rồi DÒ CHỮ tiếng Anh (`acquired|ok|granted`) trong
# output — mà wlock in tiếng Việt "ĐÃ CẤP" -> tưởng trượt -> ngủ 60s -> xin lại ->
# XẾP HÀNG SAU CHÍNH MÌNH, kẹt 15 phút và chặn worker khác. Có `wlock wait` rồi thì
# tự viết vòng lặp quanh wlock là SAI, và dò chữ trong output là CẤM.
VONG_WLOCK = (re.compile(r"(?<![\w-])(while|until)(?![\w-])"),
              re.compile(r"wlock"),
              re.compile(r"(?<![\w-])sleep(?![\w-])"))
RX_DO_CHU = re.compile(r"(grep|=~|case\s)[^\n]{0,80}"
                       r"(acquired|granted|ĐÃ CẤP|DA CAP|đã cấp)", re.I)

# Trần mặc định 3: máy founder 10 nhân / 16 GB, mà mỗi worker còn đẻ thêm build,
# iOS Simulator, http.server... 11 con đã đẩy load lên 566.
MAX_WORKERS = int(os.environ.get("UNIV3_WORKER_MAX", "5"))  # founder chốt 25/8: "tối đa 4-5 — ưu tiên xong nhanh"
# Coi là ĐANG CHẠY nếu transcript được ghi thêm trong bấy nhiêu phút.
# 15 phút = trùng dải "im lặng vẫn còn bình thường" của worker-watchdog.sh (mốc nhắc đầu
# tiên là 20 phút), đủ để worker đang chạy build/deploy dài không bị coi là đã chết.
ACTIVE_MIN = float(os.environ.get("UNIV3_WORKER_ACTIVE_MIN", "15"))
PROJECTS_ROOT = os.environ.get("UNIV3_PROJECTS_ROOT",
                               os.path.expanduser("~/.claude/projects"))
ESCAPE = "worker-cap-ok"

# từ quá phổ thông, không dùng để đo trùng mảng
STOP = {"fix", "sua", "lam", "cho", "tren", "trong", "voi", "cua", "va", "the", "cai",
        "lai", "them", "bo", "ra", "vao", "moi", "cu", "hai", "lan", "mot", "hai",
        "worker", "rule", "task", "check", "test", "verify", "kiem", "tra", "soat",
        "trang", "web", "app", "code", "file", "tep", "nhom", "toan", "dien", "not"}


def khong_dau(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def tokens(s: str):
    return {t for t in re.split(r"[^a-z0-9]+", khong_dau(s)) if len(t) >= 3 and t not in STOP}


def project_dir(cwd: str):
    """Thư mục ~/.claude/projects/<ma-hoa-duong-dan> ứng với cwd (đi ngược lên cha)."""
    p = os.path.abspath(cwd or os.getcwd())
    while True:
        cand = os.path.join(PROJECTS_ROOT, p.replace("/", "-"))
        if os.path.isdir(cand):
            return cand
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent


# đọc ngược từ đuôi transcript: đủ để thấy lượt cuối, không nuốt cả tệp 30 MB
TAIL_BYTES = 256 * 1024
TAIL_CAP = 8 * 1024 * 1024
NGAT = "[Request interrupted by user]"

# `stop_reason` mà harness đóng dấu khi MODEL KẾT LƯỢT (đã trả kết quả về cha).
# Cố ý CHỈ liệt kê hai giá trị QUAN SÁT ĐƯỢC trên 728 transcript thật. Giá trị lạ
# (`max_tokens`, `refusal`…) rơi vào nhánh mặc định = ĐANG CHẠY — lệch về phía an toàn:
# đếm dư một xác treo trong ≤15 phút rẻ hơn nhiều so với kill oan worker đang làm.
KET_LUOT = {"end_turn", "stop_sequence"}

# NGƯỠNG "CÒN NHÚC NHÍCH" — bao lâu không gọi lệnh nào thì mới được KHUYÊN tắt.
#
# CA THẬT 29/08/2026 (W11 bị tắt oan): worker đang gửi ảnh cho founder, 02:17:02 nó viết
# một tin TRUNG GIAN ("curl bị chặn đọc file local trong sandbox. Chuyển sang Node fetch."),
# 02:17:32 gọi tiếp `Bash`, 02:17:50 bị `TaskStop`. Cách lệnh cuối đúng 18 GIÂY — không hề
# treo. Máy nhìn tin trung gian tưởng là báo cáo cuối.
#
# ĐO ĐỂ CHỌN SỐ (776 agent của dự án này, 49.344 khoảng nghỉ giữa hai lệnh liên tiếp):
#   p50 = 6 giây · p90 = 25 giây · p95 = 45 giây · p99 = 3,9 phút · p99,5 = 6,2 phút.
#   Số khoảng nghỉ > 5 phút: 362/49.344 = 0,73%.
# -> 5 phút bao 99,27% nhịp làm việc thật. Im QUÁ 5 phút mà không gọi lệnh nào thì gần như
# chắc chắn đã dừng hẳn -> VẪN PHẢI khuyên tắt (xác để lại sẽ gửi lặp báo cáo cũ, 25/8 lặp
# 4 lần một con). Cố ý KHÔNG lấy p99,9 (10 phút): nới gấp đôi chỉ mua thêm 0,5% nhịp thật
# mà xác nằm lại lâu gấp đôi. Cùng số 5 phút `worker_board.NGHI_PHUT` đang dùng để vẽ 💤.
NGUONG_NHUC_NHICH_PHUT = 5.0


def phut_tu_lenh_cuoi(path: str):
    """Số PHÚT kể từ `tool_use` cuối cùng trong transcript worker. None = không thấy lệnh nào.

    Đo cùng nguồn với cột `⚙ <lệnh> Np` của bảng worker: bản ghi assistant có khối
    `tool_use`. CỐ Ý không đòi lệnh phải còn dở (chưa có `tool_result`) — worker vừa chạy
    xong một lệnh và đang nghĩ lệnh kế tiếp vẫn là ĐANG LÀM VIỆC.
    """
    import datetime as _dt
    moc = None
    try:
        for r in _tail_records(path):
            c = (r.get("message") or {}).get("content")
            if not isinstance(c, list):
                continue
            if not any(isinstance(k, dict) and k.get("type") == "tool_use" for k in c):
                continue
            try:
                moc = _dt.datetime.fromisoformat(
                    str(r.get("timestamp") or "").replace("Z", "+00:00")).timestamp()
            except Exception:
                pass
    except Exception:
        return None
    return None if moc is None else max((time.time() - moc) / 60.0, 0.0)


def _tail_records(path: str):
    """Các bản ghi JSONL cuối tệp; nới dần cho tới khi thấy ít nhất một bản ghi assistant."""
    size = os.path.getsize(path)
    chunk = TAIL_BYTES
    while True:
        start = max(0, size - chunk)
        with open(path, "rb") as fh:
            fh.seek(start)
            raw = fh.read()
        lines = raw.split(b"\n")
        if start > 0:
            lines = lines[1:]          # dòng đầu bị cắt giữa chừng
        recs = []
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            try:
                recs.append(json.loads(ln))
            except Exception:
                pass
        if start == 0 or chunk >= TAIL_CAP or any(r.get("type") == "assistant" for r in recs):
            return recs
        chunk *= 4


def da_tra_bao_cao(path: str) -> bool:
    """True = worker ĐÃ TRẢ BÁO CÁO CUỐI (hoặc đã bị dừng) -> xác treo, không tính vào trần.

    Đọc ngược, bỏ nhiễu (attachment · user isMeta = SYSTEM NOTIFICATION / Stop hook feedback),
    xét bản ghi thật đầu tiên và HỎI ĐÚNG MỘT TRƯỜNG: `message.stop_reason`.

    Vì sao là trường này chứ không phải "text mà không gọi tool" (luật cũ, đã kill oan 2
    worker ngày 28/08/2026) — xem khối "DẤU HIỆU TẤT ĐỊNH" ở docstring đầu tệp. Tóm tắt:
    một lượt model được ghi thành NHIỀU bản ghi (thinking · text · tool_use), chỉ bản ghi
    CUỐI của lượt mới có `stop_reason` khác `null`. Worker vừa nói vừa làm sinh ra bản ghi
    `text` với `stop_reason: null` ở GIỮA CHỪNG — luật cũ đọc trúng khe đó là phán nhầm.

    Mọi bất trắc -> False (coi như đang chạy).
    """
    try:
        for r in reversed(_tail_records(path)):
            if r.get("type") == "attachment":
                continue
            if r.get("type") == "user" and r.get("isMeta"):
                continue
            msg = r.get("message") or {}
            content = msg.get("content")
            texts = []
            if isinstance(content, list):
                for b in content:
                    if isinstance(b, dict) and b.get("type") == "text":
                        texts.append(str(b.get("text") or ""))
            elif isinstance(content, str):
                texts.append(content)
            if r.get("type") == "user":
                # Cha vừa gửi việc mới -> đang chạy. Chỉ bản ghi NGẮT thật mới tính, mà bản
                # ghi ngắt luôn MỞ ĐẦU bằng chuỗi đó (đo: 66/67 bản ghi ngắt thật). Ca thứ
                # 67 là một brief TRÍCH chuỗi ấy để dặn dò -> `in` sẽ khai tử worker ngay
                # bản ghi đầu tiên của nó, nên phải so bằng `startswith`.
                return any(t.strip().startswith(NGAT) for t in texts)
            if r.get("type") == "assistant":
                return msg.get("stop_reason") in KET_LUOT
        return False
    except Exception:
        return False


# ===================== VÙNG TỆP (chống hai worker cùng ghi một vùng) ==========
# Ngày 26/08/2026: cổng "trùng mảng" cũ so bằng TỪ KHOÁ trong mô tả nên worker "A35 chia
# tab" và worker "fix lỗi đẩy đơn" không trùng chữ nào -> lọt; hai con cùng ghi
# src/lib/fulfill/ -> `git add` của con này cuốn phần dang dở của con kia -> main không
# biên dịch được, lô deploy gãy. Nên phải so bằng VÙNG TỆP THẬT, không so chữ.
VUNG_GOC = ("src", "scripts", "e2e", "workers", "packages", "app", "lib", "docs")
RX_DUONG = re.compile(r"(?:^|[\s\"'`(=,])\.?/?((?:%s)/[\w./@\-\[\]]+)"
                      % "|".join(VUNG_GOC))
VUNG_TAIL = 3 * 1024 * 1024   # đọc 3 MB cuối transcript là đủ thấy tệp đã chạm

# 26/08/2026 chiều — CẮT VÙNG QUÁ THÔ, chặn oan 21 phút: một việc sửa nhánh
# `src/lib/drive` bị chặn vì "trùng vùng" với worker đang sửa `src/lib/pipeline`
# (đường dẫn thư mục 3 đoạn `src/lib/drive/` bị luật cũ cắt mất đoạn cuối -> cả hai
# đều thành `src/lib`). Nên: đoạn đường dẫn chỉ là HỘP CHỨA (src, lib, app, api,
# components…) thì phải đi sâu thêm một tầng nữa mới ra vùng thật.
CHUA = {"src", "app", "lib", "api", "components", "component", "ui", "utils", "util",
        "helpers", "helper", "common", "shared", "core", "modules", "module",
        "services", "service", "routes", "route", "pages", "hooks", "types", "type",
        "styles", "style", "server", "client", "packages", "workers", "scripts",
        "e2e", "public", "assets", "config", "features", "domain", "test", "tests"}
# Tệp nằm THẲNG trong hộp chứa (src/lib/db.ts, src/lib/datetime.ts, src/types/*.ts,
# src/app/globals.css, packages/*/…) = tài sản dùng chung: ai đụng cũng chặn nhau.
CHUNG = "dung-chung"
# Công cụ điều phối trong ~/.claude — KHÔNG BAO GIỜ trùng vùng với kho mã dự án.
TOOL = "tools/univ3"
MAX_TANG = 4
RX_TEP = re.compile(r"\.[A-Za-z0-9]{1,6}$")
RX_HE_THONG = re.compile(r"^(private/)?(tmp|var|etc|usr|opt|dev|Applications)(/|$)")


def chuan_vung(duong: str) -> str:
    """Đường dẫn -> VÙNG. Cắt tới tầng mà hai worker thật sự đụng file của nhau:
      src/lib/drive/folders.ts   -> src/lib/drive
      src/lib/pipeline/board.ts  -> src/lib/pipeline   (KHÁC vùng trên)
      src/app/api/orders/route.ts-> src/app/api/orders
      src/lib/db.ts              -> dung-chung          (tệp dùng chung tầng trên)
      ~/.claude/universal-hooks/ -> tools/univ3         (không dính kho mã)
    """
    p = (duong or "").strip().strip("\"'`,)").replace("\\", "/")
    if not p:
        return ""
    if "universal-hooks" in p or "/.claude/" in p or p.startswith("~/.claude"):
        return TOOL
    if RX_HE_THONG.match(p.lstrip("~").lstrip("/")):
        return ""                            # /tmp, /var… không phải vùng mã
    ph = [x for x in p.split("/") if x and x != "."]
    if not ph:
        return ""
    if p.startswith("/") or p.startswith("~"):
        # đường dẫn tuyệt đối -> cắt từ thư mục gốc mã đầu tiên nhận ra được
        idx = next((i for i, x in enumerate(ph) if x in VUNG_GOC), -1)
        if idx < 0:
            return ""
        ph = ph[idx:]
    if ph[0] == "docs":
        return "docs"                        # tài liệu: cả docs coi là một vùng
    thu_muc = ph[:-1] if RX_TEP.search(ph[-1]) else ph
    if not thu_muc:
        return ""                            # tệp ở gốc kho -> regex không bắt tới
    phan, het_hop = [], True
    for seg in thu_muc[:MAX_TANG]:
        phan.append(seg)
        # nhóm route Next.js `(dashboard)`, đoạn động `[id]`, `_private`, `@slot`
        # cũng chỉ là hộp chứa -> đi tiếp một tầng nữa
        hop = seg in CHUA or seg[:1] in ("(", "[", "_", "@")
        if len(phan) >= 2 and not hop:
            het_hop = False
            break
    if len(phan) == 1:
        return phan[0]                       # 'scripts', 'e2e'… rộng -> vung_hep loại
    return CHUNG if het_hop else "/".join(phan)


def vung_tu_text(text: str):
    return {v for v in (chuan_vung(m.group(1)) for m in RX_DUONG.finditer(text or "")) if v}


def vung_hep(vs):
    """Chỉ vùng ĐỦ HẸP mới đem so trùng: bỏ `docs` (ai cũng ghi tài liệu riêng, không gãy
    build) và bỏ vùng một tầng (`src`, `app`…) vì rộng tới mức worker nào cũng dính.
    GIỮ `dung-chung` (tệp dùng chung tầng trên — đúng chỗ đáng chặn)."""
    return {v for v in (vs or set())
            if v and (v == CHUNG or ("/" in v and not v.startswith("docs")))}


# --- suy VÙNG của việc MỚI: ưu tiên KHAI BÁO, cấm đoán bừa từ chữ trong brief ---
RX_KHAI = re.compile(r"^[ \t>*\-]*(?:V[ÙU]NG(?:\s+GHI)?|ZONE|WRITE[- ]?ZONE)\s*[:=]\s*(.+)$",
                     re.I | re.M)
RX_KHONG_DUNG = re.compile(
    r"(kh[ôo]ng\s+[đd][uụ]ng|kh[ôo]ng\s+s[ửu]a|kh[ôo]ng\s+ghi|c[ấa]m\s+s[ửu]a|"
    r"ch[ỉi]\s+[đd][ọo]c|read[- ]only)", re.I)
RX_VI_DU = re.compile(
    r"(v[íi]\s*d[ụu]|\bvd\b|\be\.g\b|minh\s*ho[ạa]|tham\s*kh[ảa]o|xem\s+th[êe]m|"
    r"[đd][ọo]c\s+(file|t[ệe]p))", re.I)
RX_TOOL_TEXT = re.compile(r"(universal-hooks|~/\.claude|\$HOME/\.claude)", re.I)


# W188 29/08/2026 — CÂU CẤM KHÔNG PHẢI LỜI KHAI VÙNG GHI.
# CA THẬT founder chỉ mặt: brief W190 («điều tra thẻ hiện hai chip A14», CHỈ ĐỌC) và W191
# («đẩy 8 bản lưu lên demo/prod», vùng `scripts/deploy-batch.sh`) đều có dòng ràng buộc
# «KHÔNG đụng ~/.claude/universal-hooks/ (W187, W188 đang giữ)». Cổng đọc thấy tên thư mục
# đó rồi CHẶN cả hai với lý do «ghi vào VÙNG worker khác ĐANG GIỮ: tools/univ3».
# Nguyên văn founder: «toàn đẩy chờ nhưng khi có task liên quan đéo tự động phân tích để
# gộp. tốn nguồn lực và thời gian vãi lồn.»
# Càng viết ràng buộc cẩn thận thì càng bị chặn — ngược hoàn toàn ý đồ.
# Hai lỗ đã bịt ở đây:
#   (1) nhánh cũ `co_tool and RX_KHONG_DUNG -> {TOOL}, "khai"` HIỂU NGƯỢC: nó đọc câu
#       "KHÔNG đụng universal-hooks" thành "chỉ sửa universal-hooks". Bỏ hẳn nhánh đó.
#   (2) dòng khai `VÙNG:` bị nuốt cả mệnh đề cấm nằm trong ngoặc cùng dòng -> `chuan_vung`
#       thấy chữ "universal-hooks" là trả TOOL. Nay cắt mệnh đề cấm TRƯỚC khi bóc vùng.
RX_CAM_RONG = re.compile(
    r"(kh[ôo]ng\s+[đd][uụ]ng|kh[ôo]ng\s+s[ửu]a|kh[ôo]ng\s+ghi|kh[ôo]ng\s+ch[ạa]m|"
    r"c[ấa]m\s+[đd][uụ]ng|c[ấa]m\s+s[ửu]a|c[ấa]m\s+ghi|tr[áa]nh\s+[đd][uụ]ng|"
    r"n[ée]\s+v[ùu]ng|[đd]ang\s+gi[ữu]|worker\s+kh[áa]c\s+gi[ữu]|"
    r"ch[ỉi]\s+[đd][ọo]c|read[- ]only)", re.I)


def _bo_menh_de_cam(text: str) -> str:
    """Bỏ MỆNH ĐỀ CẤM khỏi brief trước khi suy vùng ghi.

    Cắt hai lớp, đúng thứ tự:
      · cụm nằm trong ngoặc đơn có chữ cấm  -> xoá cả cụm  «(KHÔNG đụng ~/.claude/…)»
      · phần còn lại từ chữ cấm tới hết dòng -> xoá        «… , không ghi tệp mã nguồn»
    Thà bỏ sót một vùng còn hơn chặn oan: vùng suy sai thì brief khai thẳng `VÙNG:` là xong,
    còn chặn oan thì việc nằm chết trong hàng chờ và founder không biết.
    """
    ra = []
    for dong in (text or "").splitlines():
        d = re.sub(r"\([^()]*\)", lambda m: " " if RX_CAM_RONG.search(m.group(0)) else m.group(0), dong)
        m = RX_CAM_RONG.search(d)
        if m:
            d = d[:m.start()]
        ra.append(d)
    return "\n".join(ra)


# Dấu tách giữa nhiều đường dẫn trên MỘT dòng khai: dấu câu, chữ "và", và KHOẢNG TRẮNG.
# W46 29/08/2026 — vì sao thêm khoảng trắng: brief khai «VÙNG: src/app/pipeline
# src/components/card» thì bản cũ nuốt cả cụm thành MỘT vùng tên «src/app/pipeline src»
# -> hai vùng khai ra biến mất sạch, mọi phép so trùng vùng sau đó trượt. Điều phối khai
# càng đầy đủ thì cổng càng mù.
RX_KHAI_TACH = re.compile(r"[,;|+]|\s+v[àa]\s+|\s+")
# Token nào MỚI là đường dẫn: chỉ chữ/số ASCII và `. - _ @ [ ] ( ) / ~`. Dòng khai thật
# hay lẫn văn xuôi tiếng Việt («VÙNG: enforce/claude/hooks/ — các tệp hệ vé») và gạch dài;
# không lọc thì `chuan_vung("các")` đẻ ra vùng ma, in lên lời chặn founder đọc không hiểu.
RX_TOKEN_DUONG = re.compile(r"^[~./]*[A-Za-z0-9_@.\-\[\]()]+(?:/[A-Za-z0-9_@.\-\[\]()]*)*/?$")


def _bo_ngoac(s: str) -> str:
    """Bỏ cụm trong ngoặc đơn khỏi dòng khai — chú thích, không phải đường dẫn."""
    return re.sub(r"\([^()]*\)", " ", s or "")


def _vung_khai(dong: str):
    """Bóc TẤT CẢ đường dẫn trong phần sau dấu `:` của một dòng `VÙNG:`."""
    ra = set()
    for tok in RX_KHAI_TACH.split(_bo_ngoac(dong)):
        tok = tok.strip().strip("\"'`,;.").strip()
        if not tok or not RX_TOKEN_DUONG.match(tok):
            continue
        if "/" not in tok and tok.strip("~./") not in VUNG_GOC:
            continue                      # một chữ trơ trọi ("univ3", "sửa") — không phải vùng
        v = chuan_vung(tok)
        if v:
            ra.add(v)
    return ra


def vung_viec_moi(text: str):
    """(tập vùng, nguồn) — nguồn: 'khai' (brief tự khai, tin tuyệt đối) ·
    'khai-rong' (CÓ dòng khai nhưng không bóc ra đường dẫn nào -> cho qua, cảnh báo) ·
    'suy' (rút từ đường dẫn trong brief, đã bỏ dòng ví dụ/dặn-không-đụng) ·
    'khong' (không suy được -> CHO QUA kèm cảnh báo, không chặn oan).

    CÓ DÒNG KHAI THÌ KHÔNG BAO GIỜ SUY NỮA — kể cả khi dòng khai bóc ra rỗng. Đó là ý
    founder (W46): *"khi có khai báo thì DÙNG khai báo, KHÔNG suy từ các đường dẫn khác
    trong brief"*; brief nào cũng nhắc dăm đường dẫn để ĐỌC, suy tiếp là chặn oan.
    """
    text = _bo_menh_de_cam(text or "")
    co_dong_khai = False
    khai = set()
    for m in RX_KHAI.finditer(text):
        co_dong_khai = True
        khai |= _vung_khai(m.group(1))
    if co_dong_khai:
        return khai, ("khai" if khai else "khai-rong")
    ra = set()
    for dong in text.splitlines():
        if RX_VI_DU.search(dong) or RX_KHONG_DUNG.search(dong):
            continue                          # dòng nêu ví dụ / dặn không đụng: bỏ
        ra |= vung_tu_text(dong)
    if RX_TOOL_TEXT.search(text):
        ra.add(TOOL)                          # còn nhắc tool ở câu KHẲNG ĐỊNH -> tính
    return ra, ("suy" if ra else "khong")


def vung_worker(jl: str):
    """Vùng mà worker ĐANG CHẠY đã ghi vào: mọi file_path của Edit/Write + đường dẫn trong
    lệnh Bash của nó. Quét thô trên raw transcript (nhanh, không parse hết JSON)."""
    try:
        size = os.path.getsize(jl)
        with open(jl, "rb") as fh:
            fh.seek(max(0, size - VUNG_TAIL))
            raw = fh.read().decode("utf-8", "replace")
    except Exception:
        return set()
    ra = set()
    # CHỈ tính vùng worker thật sự GHI: file_path của Edit/Write/MultiEdit và `git add <tệp>`.
    # (Trước đó quét cả transcript -> bắt luôn mọi đường dẫn nêu trong văn bản, kể cả ví dụ
    #  minh hoạ như "src/lib/abc/xyz.ts" -> chặn oan.)
    for m in re.finditer(r'"file_path"\s*:\s*"([^"]+)"', raw):
        ra.add(chuan_vung(m.group(1)))
    # Lớp ký tự loại: nháy · & | ; · DẤU GẠCH NGƯỢC (chặn ở escape `\n` của JSONL) · xuống dòng thật.
    # Bản cũ viết `\\n` -> lớp ký tự nuốt luôn CHỮ "n": `git add src/app/pipeline` ra vùng
    # `src/app/pipeli`. Cụt như nhau ở mọi worker nên cổng vẫn so trùng được, nhưng tên vùng in ra
    # sai và cổng nào so theo TÊN VÙNG (worker_de_trung_vung_gate) thì trượt.
    for m in re.finditer(r"git add ([^\"'&|;\\\n]+)", raw):
        for d in m.group(1).split():
            if not d.startswith("-"):
                ra.add(chuan_vung(d))
    return {v for v in ra if v}


def running_workers(cwd: str):
    """(dang_chay, xac_treo) — mỗi phần tử là (tuoi_phut, agent_id, mo_ta).

    Cả hai đều nằm trong cửa sổ ACTIVE_MIN; khác nhau ở chỗ xác treo ĐÃ trả báo cáo cuối
    nên KHÔNG được tính vào trần (xem docstring đầu tệp).
    """
    root = project_dir(cwd)
    if not root:
        return [], []
    now = time.time()
    song, xac = [], []
    _chet = {}      # {phiên: {agent_id: trạng thái}} — harness đã báo kết thúc
    # Gom theo agent id: phiên cha nối tiếp thì harness đặt SYMLINK sang transcript thật ở
    # phiên cũ, glob khớp cả hai -> MỘT worker chiếm HAI chỗ trong trần (28/8: trần đếm 5
    # khi chỉ có 4 con sống, con thứ 5 bị chặn oan). Tệp thật đứng đầu, các đường dẫn còn
    # lại chỉ để biết agent thuộc phiên cha nào mà hỏi notification kết thúc.
    _gom = {}
    for _jl in sorted(glob.glob(os.path.join(root, "*", "subagents", "agent-*.jsonl"))):
        _aid = os.path.basename(_jl)[len("agent-"):-len(".jsonl")]
        _ds = _gom.setdefault(_aid, [])
        (_ds.insert(0, _jl) if not os.path.islink(_jl) else _ds.append(_jl))
    for aid, ds in _gom.items():
        jl = ds[0]
        try:
            age = (now - os.path.getmtime(jl)) / 60.0
        except OSError:
            continue
        if age > ACTIVE_MIN:
            continue
        desc = ""
        try:
            with open(jl[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as fh:
                desc = str(json.load(fh).get("description") or "")
        except Exception:
            pass
        # Worker BỊ GIẾT mà lượt cuối đang gọi tool thì `da_tra_bao_cao` trả False ->
        # bản cũ đếm nó là ĐANG CHẠY, chiếm chỗ trong trần dù đã chết (27/8: 2 con chết
        # vẫn giữ chỗ). Hỏi thẳng harness qua `worker_relapse.ids_ket_thuc`.
        # Hỏi MỌI phiên cha của agent: notification chỉ nằm ở phiên đã thả nó, mà qua
        # symlink agent còn xuất hiện ở phiên nối tiếp (phiên đó không có notification).
        ket = False
        if WR is not None:
            for _d in ds:
                phien = os.path.dirname(os.path.dirname(_d)) + ".jsonl"
                if phien not in _chet:
                    try:
                        _chet[phien] = WR.ids_ket_thuc(phien) or {}
                    except Exception:
                        _chet[phien] = {}
                if aid in _chet[phien]:
                    ket = True
                    break
        # Phần tử thứ 5 = số phút từ `tool_use` cuối. Harness đã báo kết thúc (`ket`) thì
        # ghi -1: `TaskStop` lúc đó là lệnh rỗng, không có gì để tắt oan.
        _pl = -1.0 if ket else phut_tu_lenh_cuoi(jl)
        (xac if (ket or da_tra_bao_cao(jl)) else song).append(
            (age, aid, desc, vung_worker(jl), _pl))
    song.sort()
    xac.sort()
    return song, xac


def so_worker(w, cwd: str) -> str:
    """Worker đang giữ vùng -> SỐ W## founder đọc được, không phải id agent.

    WHY: vé xếp hàng ghi "chờ ab8f76152c371c1da nhả src/lib" thì founder nhìn bảng không
    biết đó là con nào — đúng thứ dãy số W## sinh ra để dẹp. Lấy số theo hai đường: số gõ
    sẵn đầu `description`, hoặc tra sổ `wseq` theo slug. Cả hai trượt thì trả TÊN VIỆC,
    id agent chỉ là nước cuối.
    """
    desc = w[2] or ""
    m = re.match(r"\s*(W\d+)\b", desc, re.I)
    if m:
        return m.group(1).upper()
    t = re.sub(r"^\s*W\d+\b", "", desc, flags=re.I).replace("worker-cap-ok", " ")
    slug = re.sub(r"[^a-z0-9]+", "-", khong_dau(t)).strip("-")
    if slug:
        try:
            duong = os.path.expanduser("~/.claude/worker-counter/%s.map"
                                       % os.path.basename(os.path.abspath(cwd or ".").rstrip("/")))
            with open(duong, encoding="utf-8") as fh:
                for d in fh:
                    c = d.rstrip("\n").split("\037")
                    if len(c) >= 2 and c[1] == slug:
                        return c[0]
        except Exception:
            pass
    return (desc.strip()[:28] or w[1])


def _im_lenh(w):
    """Phút từ lệnh cuối của worker `w`. None = không đo được (tuple cũ 4 phần tử)."""
    return w[4] if len(w) > 4 else None


def bang(ws) -> str:
    return "\n".join("    - %-17s %-38s (im %.0f phút)" % (w[1], w[2] or "(không rõ)", w[0])
                     for w in ws)


HOW_TO = """LUẬT ĐIỀU PHỐI (rules/AGENTS-ORCH.md §Trần-worker):
  1. **Trần {cap} worker đồng thời / dự án.** Vượt trần thì XẾP HÀNG CHỜ — xong một mới
     thả một. Không có "thả trước rồi tính sau".
  2. **Việc mới trùng mảng với worker đang chạy -> `SendMessage` vào chính worker đó**,
     CẤM đẻ worker mới. Nó đã có sẵn ngữ cảnh, lại không tranh tệp với chính mình.
  3. **Một tệp/vùng chỉ MỘT worker được ghi tại một thời điểm** (nhất là CSS/JS/template
     dùng chung). Muốn sửa vùng người khác đang giữ -> chờ, hoặc nhờ chính worker đó làm.
  4. Worker phải **tự dọn tài nguyên nền** của mình khi xong (`http.server`, iOS Simulator,
     tiến trình nền). Lưới an toàn: `stale-server-reaper.sh`.
  5. **Worker đã trả báo cáo cuối VÀ im quá 5 phút không gọi lệnh nào = XONG, kill NGAY**
     (`TaskStop`), dù khung điều phối vẫn hiện `running`. Trạng thái đó là RÁC — để đấy thì
     mỗi thông báo nền lại đánh thức nó gửi lại đúng bản báo cáo cũ (25/8: 4 lần một con).
     **CẤM tắt con vừa gọi lệnh trong 5 phút gần đây**, dù nó có trả ra thứ trông như báo
     cáo: worker vừa nói vừa làm (29/8: W11 bị tắt lúc cách lệnh cuối 18 giây, đang gửi ảnh
     cho founder). Hook tự tách hai nhóm và chỉ khuyên tắt nhóm đã im — cứ đọc lời hook.
  6. **Cấm mỗi worker tự dựng một vòng `until ... sleep` canh cùng một tài nguyên, và CẤM
     dò chữ trong output khoá** — chờ khoá bằng ĐÚNG MỘT DÒNG:
     `bash ~/.claude/universal-hooks/wlock.sh wait deploy --owner=<slug> --pid=$$ || exit 75`
     (lệnh tự nằm chờ tới lượt; chỉ xét MÃ THOÁT 0/75, không đọc chữ. Khoá theo TÀI NGUYÊN
     nên script tên gì cũng bị chặn, không như `grep` theo tên script).

ĐI TIẾP NGAY BÂY GIỜ (chọn 1):
  a. Gửi việc vào một worker ở bảng trên: `SendMessage` kèm id/tên của nó.
  b. Xếp hàng: chờ một worker xong (notification sẽ báo) rồi mới thả con này.
  c. Việc thật sự độc lập và founder ĐÃ đồng ý chạy thêm -> thêm chuỗi `worker-cap-ok`
     vào `description`/`prompt`, hoặc chạy với `UNIV3_WORKER_MAX=<n>`."""


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    ev = str(data.get("hook_event_name") or "")
    cwd0 = str(data.get("cwd") or os.getcwd())

    # Một worker vừa trả báo cáo -> có thể đã nhả vùng/nhả chỗ. Đây là thời điểm DUY NHẤT
    # chắc chắn có việc rời hàng, nên ép điều phối đọc hàng chờ ngay tại đây.
    if ev in ("SubagentStop", "UserPromptSubmit"):
        try:
            if WQ is None:
                return 0
            # BƯỚC 0 (thêm 27/8): worker bị `TaskStop`/kill/chết giữa chừng TỰ QUAY LẠI
            # hàng chờ. Trước đó hàng chờ chỉ nhận việc ở CỔNG VÀO (bị chặn lúc thả), nên
            # worker đã chạy rồi bị giết là rơi mất sạch — điều phối phải tự nhớ, và đã
            # quên 2 lần trong một buổi sáng (ca HGT nằm chết 2 tiếng).
            hoi_sinh = []
            if WR is not None:
                try:
                    hoi_sinh = WR.quet(cwd0)
                except Exception:
                    hoi_sinh = []
            # BƯỚC 0b (thêm 29/8): worker XONG VIỆC nhưng trong báo cáo cuối tự khai
            # "để lại / ngoài vùng ghi" -> đẻ vé. Đo 28/8: 31/56 worker có việc để lại mà
            # sổ hàng chờ nhận ĐÚNG 0 vé loại này (vé chỉ sinh lúc THẢ bị chặn) — ca P070
            # mục S5 nằm chết trong một tệp 52 KB tới sáng hôm sau founder mới thấy.
            de_lai = []
            if WD is not None:
                try:
                    de_lai = WD.quet(cwd0)
                except Exception:
                    de_lai = []
            ves = WQ.doc(cwd0)
            if not ves:
                return 0
            ws, _ = running_workers(cwd0)
            dang = set()
            for w in ws:
                dang |= vung_hep(w[3])
            # Vé chờ founder quyết KHÔNG bao giờ nằm trong tập "thả được ngay": nó
            # không vướng vùng nên bản cũ luôn cho lọt (ca W156·W160·W161 đêm 29/08).
            # WHY (W192, 29/08): vé còn ghi ĐIỀU KIỆN CHỜ MỘT WORKER cụ thể (`cho_worker`)
            # mà worker đó CÒN SỐNG thì KHÔNG phải "thả được ngay" — dù vùng tệp trống.
            # Ca thật: vé W200 «chạy sync-uni.sh pull KHI MỌI WORKER ĐÃ DỪNG» ghi chờ W197;
            # W197 còn chạy ở mốc 68% mà cổng vẫn giục thả 4 lượt liền. Pull cài đè lại
            # toàn bộ hook vào ~/.claude giữa lúc worker khác đang thi công = gãy cổng.
            try:
                so_song = {a["so"] for a in (WQ.agent_song(cwd0) or []) if a.get("so")}
            except Exception:
                so_song = set()

            def _cho_nguoi_khac(v):
                ai = WQ._so_chuan(str(v.get("cho_worker") or ""))
                return bool(ai) and ai in so_song

            san = [v for v in ves if not (vung_tu_text(v.get("vung") or "") & dang)
                   and not ((v.get("vung") or "") in dang)
                   and not WQ.cho_founder(v)
                   and not _cho_nguoi_khac(v)]
            if len(ws) >= MAX_WORKERS:
                san = []
            ma_san = {v.get("ma") for v in san}
            lau = max((time.time() - v.get("luc", 0)) / 60.0 for v in ves)
            dau = "⏳ HÀNG CHỜ WORKER"
            if san and lau >= 15:
                # Nhắc phải TO DẦN: bản cũ nhắc đúng một giọng mỗi lượt, điều phối lướt
                # qua -> việc nằm 2 tiếng. Chờ càng lâu mà vùng đã trống thì càng gắt.
                dau = ("⛔ ĐANG BỎ RƠI VIỆC — vé nằm chờ %.0f phút mà VÙNG ĐÃ TRỐNG, "
                       "THẢ NGAY LƯỢT NÀY" % lau)
            txt = ("%s — %d việc đang nằm chờ (đã lưu đủ brief, KHÔNG mất):\n%s"
                   % (dau, len(ves), WQ.bang(ves, chi_tiet=True, san=ma_san)))
            if hoi_sinh:
                txt += ("\n\n🔁 VỪA TỰ DỰNG LẠI %d vé từ worker BỊ DỪNG GIỮA CHỪNG: %s\n"
                        "   (brief nguyên văn + mốc %% + việc đang dở đã nằm trong vé — "
                        "thả lại là chạy tiếp được, không phải làm lại từ đầu.)"
                        % (len(hoi_sinh),
                           ", ".join("%s «%s» dừng ở %s%%" % (r[0], r[1][:32], r[2])
                                     for r in hoi_sinh)))
            # W71 30/08/2026 — TÁCH tầng A (đã đẻ vé thật) khỏi tầng B (chỉ cảnh báo, xem
            # WHY tại worker_de_lai.py chỗ `if tang == "B"`): worker TỪ CHỐI việc rồi viết
            # kiểu "nằm ngoài phạm vi của tôi" từng bị tầng B hiểu nhầm là bàn giao, đẻ vé
            # rác đêm 29-30/08. Từ nay tầng B không tạo vé nữa, chỉ in cảnh báo cho main đọc.
            ve_that = [r for r in de_lai if r[3] != "B"]
            canh_bao = [r for r in de_lai if r[3] == "B"]
            if ve_that:
                txt += ("\n\n\U0001F4CC VỪA ĐẺ %d vé từ VIỆC WORKER TỰ ĐỂ LẠI (báo cáo cuối "
                        "khai «để lại / ngoài vùng ghi»): %s\n"
                        "   Vé nào có vùng thì tự lật sang ✅ THẢ ĐƯỢC NGAY khi vùng trống; "
                        "vé không vùng là việc CHỜ FOUNDER quyết — gom lúc chốt ngày."
                        % (len(ve_that),
                           ", ".join("%s «%s»%s" % (r[0], str(r[1])[:32],
                                                    (" [vùng %s]" % r[2]) if r[2] else "")
                                     for r in ve_that)))
            if canh_bao:
                txt += ("\n\n⚠️ NGHI CÓ %d VIỆC ĐỂ LẠI (lưới vớt văn xuôi tầng B, "
                        "CHƯA đẻ vé — main tự đọc và quyết có mở vé hay không): %s"
                        % (len(canh_bao),
                           ", ".join("«%s»%s" % (str(r[1])[:40],
                                                 (" [vùng %s]" % r[2]) if r[2] else "")
                                     for r in canh_bao)))
            if san:
                v = san[0]
                txt += ("\n\n➜ THẢ ĐƯỢC NGAY: %s «%s» (đang chạy %d/%d worker, vùng đã trống).\n"
                        "   Gọi `Agent` với brief NGUYÊN VĂN trong tệp vé: %s\n"
                        "   `description` PHẢI bắt đầu bằng \"%s \" — số này cấp từ lúc xếp "
                        "hàng, đổi số là founder mất dấu việc đang theo.\n"
                        "   Thả xong vé tự gỡ khỏi hàng chờ (hook nhận ra cùng brief)."
                        % (v.get("so") or "W??", WQ.ten_ve(v), len(ws), MAX_WORKERS,
                           v.get("_path"), v.get("so") or "W??"))
            else:
                txt += "\n\n(chưa thả được: %s)" % (
                    "đủ trần %d worker" % MAX_WORKERS if len(ws) >= MAX_WORKERS
                    else "vùng vẫn bị worker đang chạy giữ")
            key = "SubagentStop" if ev == "SubagentStop" else "UserPromptSubmit"
            json.dump({"hookSpecificOutput": {"hookEventName": key,
                                              "additionalContext": txt}},
                      sys.stdout, ensure_ascii=False)
        except Exception:
            return 0
        return 0

    if ev != "PreToolUse":
        return 0
    tool = str(data.get("tool_name") or "")

    if tool == "Bash":
        try:
            cmd = str((data.get("tool_input") or {}).get("command") or "")
            if ESCAPE in cmd:
                return 0
            la_wlock = all(rx.search(cmd) for rx in VONG_WLOCK)
            la_do_chu = ("wlock" in cmd) and bool(RX_DO_CHU.search(cmd))
            if la_wlock or la_do_chu:
                reason = (
                    "SAI CÁCH DÙNG KHOÁ — lệnh này tự bọc vòng lặp quanh `wlock` "
                    "và/hoặc DÒ CHỮ trong output của nó.\n\n"
                    "Ngày 2026-08-26 đúng kiểu này: worker được cấp khoá NGAY lần đầu "
                    "(wlock in `ĐÃ CẤP khoá 'deploy'…`) nhưng vòng lặp dò chữ tiếng Anh "
                    "`acquired|ok|granted` -> không khớp -> tưởng trượt -> `sleep 60` -> xin lại "
                    "-> **xếp hàng sau chính mình**, kẹt 15 phút và chặn 2 worker phía sau.\n\n"
                    "CÁCH ĐÚNG — MỘT DÒNG, tự nằm chờ tới lượt, KHÔNG dò chữ:\n"
                    "    W=~/.claude/universal-hooks/wlock.sh; ME=<slug worker>\n"
                    "    bash $W wait deploy --owner=$ME --pid=$$ --timeout=900 || exit 75\n"
                    "    trap 'bash '\"$W\"' release deploy --owner='\"$ME\"' >/dev/null' EXIT INT TERM\n"
                    "  hoặc gọn hơn, tự nhả kể cả khi lệnh lỗi:\n"
                    "    bash $W run deploy --owner=$ME -- ./day_len_prod.sh\n\n"
                    "MÃ THOÁT là thứ duy nhất được xét: 0 = đã cầm khoá · 75 = hết giờ chờ · "
                    "2 = sai cú pháp. Xin/chờ khoá mà CHÍNH MÌNH đang giữ -> wlock trả 0 ngay, "
                    "không xếp hàng sau chính mình.")
                json.dump({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse", "permissionDecision": "allow",
                    "permissionDecisionReason": reason,
                    "additionalContext": reason}}, sys.stdout, ensure_ascii=False)
                return 0
            if not all(rx.search(cmd) for rx in VONG_CANH):
                return 0
            reason = (
                "HỎI TRƯỚC — lệnh này là một VÒNG CANH tài nguyên tự chế "
                "(`while/until` + `ps/pgrep` + `sleep`).\n\n"
                "Ngày 2026-08-25 mỗi worker tự dựng một vòng như vậy -> **6 shell nền cùng canh "
                "một thứ**; lại canh theo TÊN SCRIPT nên một worker dùng script tên khác vẫn lọt "
                "-> hai worker đẩy FTP cùng lúc, 9 tệp lệch.\n\n"
                "CÁCH ĐÚNG — xin khoá dùng chung theo TÀI NGUYÊN (rules/AGENTS-ORCH.md §Trần worker):\n"
                "    W=~/.claude/universal-hooks/wlock.sh; ME=<slug worker>\n"
                "    bash $W wait deploy --timeout=900 --owner=$ME --pid=$$ || exit 75\n"
                "    trap 'bash '\"$W\"' release deploy --owner='\"$ME\"' >/dev/null' EXIT INT TERM\n"
                "  hoặc gọn 1 dòng, tự nhả kể cả khi lệnh lỗi:\n"
                "    bash $W run deploy --owner=$ME -- ./day_len_prod.sh\n\n"
                "Duyệt CHỈ khi vòng lặp này canh thứ KHÁC hẳn (không phải deploy/tài nguyên dùng "
                "chung). Thật sự cần -> thêm `worker-cap-ok` vào lệnh."
            )
        except Exception:
            return 0
        # 2026-08-26: allow thay vi ask — hook hoi = ket ca phien khi founder di vang.
        # Nhac van toi agent qua additionalContext, khong chan.
        json.dump({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "allow",
            "permissionDecisionReason": reason,
            "additionalContext": reason}}, sys.stdout, ensure_ascii=False)
        return 0

    if tool not in AGENT_TOOLS:
        return 0
    try:
        ti = data.get("tool_input") or {}
        if not isinstance(ti, dict):
            return 0
        desc = str(ti.get("description") or "")
        prompt = str(ti.get("prompt") or "")
        cwd = str(data.get("cwd") or "")
        co_ok = (ESCAPE in desc) or (ESCAPE in prompt)

        ws, xac = running_workers(cwd)
        cap = MAX_WORKERS

        # ---- CỔNG 1: TRÙNG VÙNG TỆP — chặn KỂ CẢ khi có `worker-cap-ok` ----
        # Vượt trần chỉ làm nặng máy; trùng vùng làm GÃY BUILD (26/8: deeddc1). Nên cửa
        # thoát `worker-cap-ok` (founder cho phép chạy thêm) KHÔNG được mở cổng này.
        vung_raw, nguon_vung = vung_viec_moi(desc + "\n" + prompt)
        vung_moi = vung_hep(vung_raw)
        if vung_moi:
            for w in ws:
                chung = vung_moi & vung_hep(w[3])
                if not chung:
                    continue
                cv = ", ".join(sorted(chung))
                ve = ""
                if WQ is not None:
                    # `them` trả rỗng = việc này ĐANG có agent sống làm -> không đẻ vé
                    # thứ hai (nếu không bảng lại vẽ nó hai lần, đúng bệnh đang trị).
                    p = WQ.them(cwd, ti, "trùng vùng %s" % cv, cho_ai=so_worker(w, cwd), vung=cv)
                    _v = (WQ.tim(cwd, ti) or {}) if p else {}
                    ve = "" if not p else ("\n\n✅ ĐÃ CHO VÀO HÀNG CHỜ với số **%s** — việc này KHÔNG mất, và "
                          "ĐÃ CÓ TÊN + SỐ ngay từ lúc xếp hàng (hiện trên bảng worker). Vé lưu "
                          "đủ brief để chạy lại y nguyên:\n    %s\n%s"
                          % (_v.get("so") or "W??", p, WQ.bang(WQ.doc(cwd))))
                # W188 29/08/2026 — CHẶN XONG PHẢI TỰ PHÂN TÍCH CÓ GỘP ĐƯỢC KHÔNG.
                # Nguyên văn founder: «toàn đẩy chờ nhưng khi có task liên quan đéo tự động
                # phân tích để gộp. ngu vãi lồn. tốn nguồn lực và thời gian vãi lồn.»
                # Cổng BIẾT THỪA worker nào đang giữ vùng (nó in tên ngay dưới) mà chỉ nhét
                # việc vào hàng chờ rồi thôi. Nay: cùng vùng + CÙNG LOẠI VIỆC -> in thẳng
                # lệnh chuyển việc kèm mã worker đích, main dán một phát là xong; khác loại
                # -> nói rõ chờ AI và con đó đã chạy bao lâu.
                gop = ""
                try:
                    import ve_cho_founder as VCF
                    if VCF.cung_loai_viec(desc + " " + prompt[:600], str(w[2] or "")):
                        gop = ("\n\n🔗 GỘP ĐƯỢC — %s đang làm ĐÚNG loại việc này trong cùng "
                               "vùng %s. Đừng xếp hàng, chuyển thẳng:\n"
                               "    SendMessage -> to: \"%s\" · message: «%s»\n"
                               "   (đo bằng cùng thước gộp vé của `ve_cho_founder.cung_viec`)"
                               % (so_worker(w, cwd) or w[1], cv,
                                  so_worker(w, cwd) or w[1], (desc or "")[:120]))
                    else:
                        gop = ("\n\n⏳ KHÔNG gộp được (khác loại việc). Chờ %s — con đó đã "
                               "chạy %.0f phút: «%s»."
                               % (so_worker(w, cwd) or w[1], w[0], str(w[2] or "")[:70]))
                except Exception:
                    gop = ""
                nguon_cau = {
                    "khai": "brief TỰ KHAI dòng `VÙNG:` (cổng tin theo khai báo)",
                    "khai-rong": "brief có dòng `VÙNG:` nhưng không bóc ra đường dẫn nào",
                    "suy": "SUY từ đường dẫn nêu trong brief",
                    "khong": "không suy được",
                }.get(nguon_vung, nguon_vung)
                chan_do = (
                    "\n\n📍 AI NÓI THẾ (dán nguyên khối này khi báo lỗi cổng):\n"
                    "   · vùng bị giữ   : %s\n"
                    "   · worker đang giữ: %s  (id %s)\n"
                    "   · NGUỒN         : transcript worker ĐANG SỐNG — "
                    "`worker_cap_enforce.running_workers()` -> `vung_worker()`, tức tệp "
                    "worker đã Edit/Write/`git add` thật. Bảng worker và hàng chờ hỏi "
                    "CÙNG nguồn này qua `worker_queue.vung_dang_giu()`.\n"
                    "   · vùng việc mới : %s  (nguồn: %s)\n"
                    "   · CHỈ ĐỌC VẪN BỊ TÍNH: cổng chưa phân biệt đọc/ghi ở phía việc "
                    "mới — brief chỉ ĐỌC `~/.claude/...` vẫn ra vùng `tools/univ3`. "
                    "Cách khai đúng: một dòng `VÙNG: <đường dẫn SẼ GHI>` (nhiều đường dẫn "
                    "cách nhau bằng khoảng trắng); việc thuần đọc thì khai vùng thật sự "
                    "sẽ ghi, hoặc không khai đường dẫn nào."
                ) % (cv, so_worker(w, cwd) or "(không rõ số)", w[1],
                     ", ".join(sorted(vung_moi)) or "(rỗng)", nguon_cau)
                reason = (
                    "CHẶN — việc mới «%s» ghi vào VÙNG mà worker khác ĐANG GIỮ: %s\n%s%s\n\n"
                    "Ngày 26/08/2026 đúng tình huống này: hai worker cùng ghi "
                    "`src/lib/fulfill/` -> `git add` của con này cuốn phần đang viết dở của "
                    "con kia vào commit deeddc1 (gọi `probeSupplierOrderWithRetry` khi hàm đó "
                    "chưa được export) -> nhánh main không biên dịch được, lô deploy gãy.\n\n"
                    "LÀM NGAY (chọn 1):\n"
                    "  a. `SendMessage` việc này vào chính worker %s — nó đang giữ vùng đó.\n"
                    "  b. Để nguyên trong hàng chờ; khi %s xong, hook sẽ nhắc thả.\n\n"
                    "Lưu ý: `worker-cap-ok` KHÔNG mở được cổng này — vượt trần chỉ nặng máy, "
                    "còn trùng vùng thì gãy build.%s%s%s"
                ) % (desc or "(không tên)", cv, bang([w]), chan_do, w[1], w[1],
                     ("\n\n(`dung-chung` = tệp dùng chung nằm thẳng trong hộp chứa — "
                      "src/lib/*.ts, src/types/*, src/app/globals.css, layout gốc. "
                      "Đây là chỗ hai worker chắc chắn ghi đè nhau.)" if CHUNG in chung else ""),
                     ("\n\n(Vùng việc mới được SUY từ đường dẫn nêu trong brief. Suy sai thì "
                      "khai thẳng một dòng `VÙNG: <đường dẫn sẽ ghi>` trong brief — cổng tin "
                      "theo khai báo, không đoán nữa.)" if nguon_vung == "suy" else ""),
                     gop + ve)
                json.dump({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse", "permissionDecision": "deny",
                    "permissionDecisionReason": reason}}, sys.stdout, ensure_ascii=False)
                return 0

        if co_ok:
            # GỠ VÉ TRƯỚC, rồi mới thoát. Bản cũ `return 0` NGAY ở đây nên không bao giờ
            # chạm tới `WQ.tha()` bên dưới — mà vé bị chặn vì VƯỢT TRẦN chỉ thả được khi
            # điều phối thêm `worker-cap-ok`, tức ĐÚNG những vé được thả thì không bao giờ
            # được gỡ. Hậu quả đo được 27/8: W130 đang chạy 84% vẫn hiện "đang xếp hàng",
            # bảng vẽ việc đó hai lần; trước đó W114 và W125 y hệt, lần nào main cũng phải
            # xoá vé bằng tay. (Lưới thứ hai: `worker_queue.doc()` tự đối soát mỗi lần đọc.)
            nhac_ve = ""
            if WQ is not None:
                _t = WQ.tha(cwd, ti)
                if _t:
                    nhac_ve = ("\n✅ Đã GỠ vé %s khỏi hàng chờ — việc này giờ đang chạy, "
                               "bảng sẽ không vẽ nó hai lần nữa." % (_t.get("so") or "W??"))
            # Founder cho phép vượt trần -> cho qua NHƯNG phải nhìn thấy là đang ép chạy.
            canh = nhac_ve
            if len(ws) >= cap:
                canh = ("⚠️  ĐANG ÉP CHẠY VƯỢT TRẦN bằng `worker-cap-ok`: %d worker đang "
                        "chạy / trần %d.\n%s\n(Đã qua cổng trùng vùng nên không gãy build, "
                        "nhưng máy founder sẽ nặng thêm.)%s"
                        % (len(ws), cap, bang(ws), nhac_ve))
            if canh.strip():
                json.dump({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": canh.strip()}}, sys.stdout, ensure_ascii=False)
            return 0

        # Điều phối đang thả đúng việc nằm trong hàng chờ -> gỡ vé.
        nhac_q = ""
        if nguon_vung == "khai-rong":
            # CÓ dòng `VÙNG:` nhưng bóc ra RỖNG -> cổng cho qua mà không ai biết là khai
            # hỏng. Im lặng ở đây là mở toang cổng trùng vùng bằng một dòng viết sai.
            nhac_q = ("\n\n⚠️  DÒNG `VÙNG:` TRONG BRIEF KHÔNG BÓC RA ĐƯỜNG DẪN NÀO -> cổng "
                      "trùng vùng ĐÃ BỊ TẮT cho lần thả này. Viết lại đúng dạng: "
                      "`VÙNG: src/app/pipeline src/components/card` (đường dẫn thật, cách "
                      "nhau bằng khoảng trắng; chữ mô tả và ngoặc đơn bị bỏ qua).")
        if WQ is not None:
            _tha = WQ.tha(cwd, ti)
            if _tha:
                nhac_q = ("\n\n(đã gỡ việc này khỏi hàng chờ — nó mang số %s từ lúc xếp hàng; "
                          "giữ nguyên số đó trên bảng, đừng cấp số mới)" % (_tha.get("so") or "W??"))
            con = WQ.doc(cwd)
            if con:
                nhac_q += ("\n\n⏳ Hàng chờ còn %d việc:\n%s" % (len(con), WQ.bang(con)))
        # CẤM KHUYÊN TẮT CON CÒN ĐANG GỌI LỆNH (ca W11, 29/08 — xem NGUONG_NHUC_NHICH_PHUT).
        # "Trông như đã trả báo cáo" KHÔNG đủ để kết luận đã xong: worker vừa nói vừa làm.
        xac_tat = [w for w in xac
                   if _im_lenh(w) is None or _im_lenh(w) < 0
                   or _im_lenh(w) >= NGUONG_NHUC_NHICH_PHUT]
        xac_dong = [w for w in xac if w not in xac_tat]
        nhac_xac = ""
        if xac_tat:
            nhac_xac = (
                "\n\nDỌN NGAY — {m} worker ĐÃ TRẢ BÁO CÁO CUỐI và im quá {ng:.0f} phút không gọi "
                "lệnh nào (khung điều phối vẫn hiện `running`, KHÔNG tính vào trần, nhưng phải "
                "kill):\n{tx}\n"
                "    -> `TaskStop` từng con ngay bây giờ. Để đấy thì mỗi thông báo nền lại đánh "
                "thức nó gửi lại đúng bản báo cáo cũ (25/8: 4 lần liên tiếp một con)."
            ).format(m=len(xac_tat), ng=NGUONG_NHUC_NHICH_PHUT, tx=bang(xac_tat))
        if xac_dong:
            nhac_xac += (
                "\n\n⛔ CẤM `TaskStop` {m} con dưới đây — trông như đã trả báo cáo NHƯNG VỪA GỌI "
                "LỆNH, nó đang làm dở:\n{tx}\n"
                "    -> để yên. Tắt bây giờ là cắt giữa chừng (ca W11 29/08: tắt lúc nó cách lệnh "
                "cuối 18 GIÂY, đang gửi ảnh cho founder). Im quá {ng:.0f} phút mới được khuyên tắt."
            ).format(m=len(xac_dong), ng=NGUONG_NHUC_NHICH_PHUT,
                     tx="\n".join("    - %-17s %-38s (lệnh cuối cách %.1f phút)"
                                  % (w[1], w[2] or "(không rõ)", _im_lenh(w)) for w in xac_dong))

        if len(ws) >= cap:
            ve = ""
            if WQ is not None:
                p = WQ.them(cwd, ti, "vượt trần %d worker" % cap)
                _v = (WQ.tim(cwd, ti) or {}) if p else {}
                ve = "" if not p else ("\n\n✅ ĐÃ CHO VÀO HÀNG CHỜ với số **%s** — việc này KHÔNG mất, đã có "
                      "TÊN + SỐ ngay từ lúc xếp hàng, vé lưu đủ brief:\n"
                      "    %s\n%s\nKhi một worker xong, hook `SubagentStop` sẽ nhắc thả "
                      "đúng việc này." % (_v.get("so") or "W??", p, WQ.bang(WQ.doc(cwd))))
            reason = (
                "CHẶN — dự án này đang có {n} worker THỰC SỰ ĐANG CHẠY, trần là {cap}:\n{tb}\n\n"
                "Ngày 2026-08-25 thả 11 worker cùng lúc đã đẩy load average lên 566, "
                "còn ~63 MB RAM trống, 4 http.server mồ côi, worker ghi đè CSS của nhau."
                "{nx}\n\n{how}"
            ).format(n=len(ws), cap=cap, tb=bang(ws), nx=nhac_xac,
                     how=HOW_TO.format(cap=cap)) + ve
            decision = "deny"
        else:
            # Brief đã KHAI vùng và không đè vùng ai -> khỏi đoán tiếp bằng từ khoá
            # (đoán chữ chính là thứ đẻ ra cảnh báo oan: brief nhắc tên thư mục làm ví dụ).
            if nguon_vung == "khai" and vung_moi:
                phu = (nhac_xac or "") + (nhac_q or "")
                if phu.strip():
                    json.dump({"hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "additionalContext": phu.strip()}},
                        sys.stdout, ensure_ascii=False)
                return 0
            moi = tokens(desc + " " + prompt[:400])
            trung = [(w, moi & tokens(w[2])) for w in ws if w[2]]
            trung = [(w, k) for w, k in trung if len(k) >= 2]
            if not trung:
                phu = (nhac_xac or "") + (nhac_q or "")
                if phu.strip():
                    json.dump({"hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "additionalContext": phu.strip()}},
                        sys.stdout, ensure_ascii=False)
                return 0
            w, k = max(trung, key=lambda x: len(x[1]))
            reason = (
                "HỎI TRƯỚC — việc mới «{d}» TRÙNG MẢNG với worker đang chạy:\n{tb}\n"
                "    (từ khoá trùng: {k})\n\n"
                "Luật founder: *\"cái nào cùng worker đang xử lý thì mới add vào worker chứ\"* — "
                "trùng mảng thì `SendMessage` vào chính worker đó, đừng đẻ con mới: nó đã có "
                "ngữ cảnh, và hai con cùng sửa một vùng tệp sẽ ghi đè nhau (đã mất 1250 dòng CSS "
                "vì đúng lỗi này).{nx}\n\nDuyệt CHỈ khi việc này thật sự đụng tệp KHÁC hẳn.\n\n{how}"
            ).format(d=desc or "(không tên)", tb=bang([w]), k=", ".join(sorted(k)),
                     nx=nhac_xac, how=HOW_TO.format(cap=cap)) + (nhac_q or "")
            # 2026-08-26: "allow" thay "ask" — chi nhac, khong chan de hoi (ket phien).
            # Tran worker (nhanh tren) van DENY nhu cu: deny khong hoi user.
            decision = "allow"
    except Exception:
        return 0

    out = {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }
    if decision == "allow":
        out["additionalContext"] = reason  # allow -> agent van phai DOC loi nhac
    json.dump({"hookSpecificOutput": out}, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
