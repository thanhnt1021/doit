#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tien_kiem_brief.py — CHẠY TRƯỚC MỌI LƯỢT THẢ THỢ: brief này có qua nổi các cổng không.

CA THẬT 19/09/2026: điều phối thả bốn thợ W01·W02·W03·W04, cả bốn bị cổng chặn ngay lúc
bấm (`dod.cong_dor` ba lượt vì sổ lệnh chưa có bản dịch, `subagent_background_enforce` hai
lượt vì brief thiếu câu ghi mốc). Trên màn hình founder chỉ thấy bốn dòng «0 tool uses ⎿
Done» — trông y như bốn thợ chạy xong mà không làm gì. Founder: *"tại sao nó cứ thả worker
ra và done như này mà không đáp ứng đủ điều kiện trước khi thả"*.

Gốc bệnh đo được: điều kiện DoR có lệnh tự kiểm (`dod.py san-sang`), còn các cổng còn lại
(khai vùng `GHI:`, câu ghi mốc, trùng vùng, trần worker, lượt founder HỎI) CHỈ sống như cổng
chặn lúc bấm thả — không có đường nào chạy TRƯỚC. Lệnh này mở đúng đường đó.

CÁCH DÙNG (một dòng, chép dán được):

    python3 ~/.claude/universal-hooks/tien_kiem_brief.py --brief /tmp/claude-brief/<dự-án>/w05.md --mo-ta "W05 vá cổng mail"
    cat /tmp/claude-brief/<dự-án>/w05.md | python3 ~/.claude/universal-hooks/tien_kiem_brief.py --mo-ta "W05 vá cổng mail"

Mã thoát 0 = qua hết · 1 = còn thiếu (bảng in ra chỉ đích danh chỗ thiếu) · 2 = lỗi tham số.

KHÔNG CHÉP LẠI LUẬT CỦA CỔNG NÀO. Lệnh dựng đúng khuôn JSON mà hook chờ ở đầu vào chuẩn rồi
gọi CHÍNH hook đó; chữ in ra là chữ của hook trả về. Chép lại logic = hai bản luật lệch nhau,
đúng bệnh đang trị.

KHÔNG SỬA BRIEF. Chỉ báo — người viết brief tự vá.

HỘP CÁT: mấy cổng này có tác dụng phụ thật (đẻ vé hàng chờ, cấp số worker, đốt cờ cửa thoát,
ghi nhật ký). Lệnh nhân bản trạng thái sang thư mục tạm rồi trỏ biến môi trường vào đó, nên
chạy tiền kiểm mười lần cũng không đẻ một cái vé ma nào.

TỰ KIỂM: python3 tien_kiem_ca_thu.py
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
DAU_ROOT = os.path.expanduser(os.environ.get("UNIV3_TIEN_KIEM_ROOT", "~/.claude/tien-kiem"))
HAN_PHUT = float(os.environ.get("UNIV3_TIEN_KIEM_HAN_PHUT", "45"))
TIMEOUT_CONG = float(os.environ.get("UNIV3_TIEN_KIEM_TIMEOUT", "120"))
NHAT_KY = os.path.expanduser(os.environ.get("UNIV3_TIEN_KIEM_LOG")
                             or "~/.claude/logs/tien-kiem-brief.log")
CUA_THOAT = "tien-kiem-bo-qua"

# Cổng SOI NỘI DUNG BRIEF — chạy thật trong hộp cát.
#   ten tệp · việc nó gác · kiểu transcript cần bơm.
# `bang-gia`: cổng chỉ bật khi phiên cha đang chạy bảng worker (nó dò dấu `> /tmp/claude-bg-
# progress/` trong transcript cha — subagent_background_enforce.py:57). Tiền kiểm phải bơm
# transcript CÓ dấu đó, nếu không cổng im và lệnh này báo ĐẠT oan cho brief thiếu câu ghi mốc.
#   `that`: cổng đo bằng chứng trong transcript thật của phiên -> đưa tệp thật.
CONG_SOI_BRIEF = (
    ("subagent_background_enforce.py", "câu ghi mốc tiến độ + khuôn tên tệp mốc", "bang-gia"),
    ("worker_cap_enforce.py", "khai vùng `GHI:` · GHI khớp phiếu · đủ điều kiện giao việc (DoR) · trùng vùng · trần thợ", "that"),
    ("founder_lenh_gate.py", "lượt founder HỎI/GÓP Ý thì không được thả thợ", "that"),
)

# Cổng CÙNG GÁC lượt `Agent` nhưng KHÔNG soi nội dung brief -> cố ý không chạy (chạy chỉ tốn
# thời gian và tiêu van an toàn của chúng). Vẫn in ra bảng để bảng là bản kiểm kê ĐỦ.
CONG_KHONG_SOI_BRIEF = (
    ("mo_phien_gate.py", "chuỗi mở phiên đã chạy chưa — soi TRẠNG THÁI PHIÊN, không soi brief"),
    ("worker-watchdog.sh ensure", "dựng watchdog nền — không có nhánh chặn nào"),
    ("disk_guard_enforce.py", "cảnh báo đĩa đầy — chỉ in nhắc, không có nhánh chặn nào"),
)

# Thư mục trạng thái GHI ĐƯỢC -> nhân bản sang hộp cát qua biến môi trường tương ứng.
# Nhân bản chứ không bỏ trống: cổng phải thấy ĐÚNG dữ liệu thật (vé cũ, cờ cửa thoát đang mở,
# sổ lệnh hôm nay) mới ra đúng kết luận như lúc thả thật.
KHO_TRANG_THAI = (
    ("UNIV3_WQUEUE_ROOT", "~/.claude/worker-queue"),
    ("WSEQ_ROOT", "~/.claude/worker-counter"),
    ("UNIV3_DOD_ROOT", "~/.claude/dod"),
    ("UNIV3_NGHIEM_THU_ROOT", "~/.claude/nghiem-thu"),
    ("UNIV3_SO_LENH_ROOT", "~/.claude/so-lenh"),
    ("UNIV3_DEPLOY_QUEUE_ROOT", "~/.claude/deploy-queue"),
    ("UNIV3_CUA_THOAT_DIR", "~/.claude/cua-thoat"),
    ("UNIV3_LOG_DIR", "~/.claude/logs"),
)


# ── vân tay ────────────────────────────────────────────────────────────────────
def chuan_hoa(s) -> str:
    """Bỏ khác biệt vô nghĩa (xuống dòng kiểu Windows, khoảng trắng cuối dòng) — sửa NỘI DUNG
    brief thì vân tay phải đổi, còn dán lại y brief cũ thì phải khớp."""
    t = str(s or "").replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(d.rstrip() for d in t.split("\n")).strip()


def van_tay(prompt) -> str:
    return hashlib.sha256(chuan_hoa(prompt).encode("utf-8")).hexdigest()


def scope(cwd: str) -> str:
    return os.path.basename(str(cwd or "").rstrip("/")) or "khong-ro"


def duong_dau(cwd: str, vt: str) -> str:
    return os.path.join(DAU_ROOT, scope(cwd), vt[:16] + ".json")


def ghi_dau(cwd: str, prompt: str, mo_ta: str, ket: list) -> str:
    """Dấu ĐẠT — cổng `tien_kiem_gate.py` đọc chỗ này. Trả đường dẫn dấu ('' nếu ghi hỏng)."""
    vt = van_tay(prompt)
    p = duong_dau(cwd, vt)
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump({"van_tay": vt, "luc": time.time(),
                       "luc_doc": time.strftime("%Y-%m-%d %H:%M:%S"),
                       "mo_ta": mo_ta, "cwd": cwd, "ky_tu": len(chuan_hoa(prompt)),
                       "cong_da_qua": [c[0] for c in ket if c[1] == "ĐẠT"],
                       "ai": os.environ.get("CLAUDE_AGENT_ID") or "main"},
                      fh, ensure_ascii=False)
        return p
    except OSError:
        return ""


def doc_dau(cwd: str, prompt: str):
    """(còn hiệu lực, bản ghi). Hết hạn hoặc không có -> (False, {})."""
    try:
        with open(duong_dau(cwd, van_tay(prompt)), encoding="utf-8") as fh:
            ban = json.load(fh)
    except Exception:
        return False, {}
    tuoi = (time.time() - float(ban.get("luc") or 0)) / 60.0
    ban["tuoi_phut"] = tuoi
    return (tuoi <= HAN_PHUT), ban


def ghi_nhat_ky(dong: str) -> None:
    for p in (NHAT_KY, "/tmp/claude_hooks/tien-kiem-brief.log"):
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a", encoding="utf-8") as fh:
                fh.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dong))
        except OSError:
            pass


# ── hộp cát ────────────────────────────────────────────────────────────────────
def dung_hop_cat(goc: str) -> dict:
    """Nhân bản trạng thái thật sang `goc`, trả biến môi trường trỏ vào bản sao."""
    env = dict(os.environ)
    os.makedirs(goc, exist_ok=True)
    for bien, that in KHO_TRANG_THAI:
        nguon = os.path.expanduser(os.environ.get(bien) or that)
        dich = os.path.join(goc, os.path.basename(that.rstrip("/")))
        try:
            if os.path.isdir(nguon):
                # `-c` = nhân bản kiểu APFS: 20 MB sổ lệnh sao trong mili-giây, không tốn đĩa.
                r = subprocess.run(["cp", "-Rc", nguon, dich], capture_output=True)
                if r.returncode != 0:
                    subprocess.run(["cp", "-R", nguon, dich], capture_output=True)
            else:
                os.makedirs(dich, exist_ok=True)
        except Exception:
            os.makedirs(dich, exist_ok=True)
        env[bien] = dich
    return env


def transcript_that(cwd: str) -> str:
    """Transcript phiên mới nhất của dự án — nguồn để cổng đo bằng chứng đã tra."""
    slug = "".join(c if c.isalnum() else "-" for c in os.path.abspath(cwd))
    d = os.path.join(os.path.expanduser(os.environ.get("UNIV3_PROJECTS_ROOT")
                                        or "~/.claude/projects"), slug)
    try:
        ts = [(os.path.getmtime(os.path.join(d, f)), os.path.join(d, f))
              for f in os.listdir(d) if f.endswith(".jsonl")]
    except OSError:
        return ""
    return max(ts)[1] if ts else ""


def transcript_bang_gia(goc: str) -> str:
    """Transcript tối thiểu mang dấu «phiên đang chạy bảng worker»."""
    p = os.path.join(goc, "transcript-bang.jsonl")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "id": "t1", "input": {
                "command": "echo '05|nhận việc' > /tmp/claude-bg-progress/%s/w00-mau.progress"
                           % scope(os.getcwd())}}]}}, ensure_ascii=False) + "\n")
    return p


# ── chạy một cổng ──────────────────────────────────────────────────────────────
def chay_cong(ten_hook: str, payload: dict, env: dict, cwd: str):
    """(trạng thái, lời của cổng). Trạng thái: ĐẠT · THIẾU · NHẮC · KHÔNG ĐO ĐƯỢC.

    `NHẮC` (W28, 21/09/2026) = cổng KHÔNG chặn nhưng có chữ gửi người thả (vd: việc có
    giao diện mà brief không bắt chụp ảnh). Không tính vào mã thoát — nhưng phải HIỆN,
    vì đây là lúc duy nhất còn sửa brief được trước khi thợ chạy."""
    duong = os.path.join(HOOKS, ten_hook)
    if not os.path.isfile(duong):
        return "KHÔNG ĐO ĐƯỢC", "không thấy tệp hook %s" % duong
    try:
        r = subprocess.run([sys.executable, duong], input=json.dumps(payload, ensure_ascii=False),
                           capture_output=True, text=True, env=env, cwd=cwd,
                           timeout=TIMEOUT_CONG)
    except subprocess.TimeoutExpired:
        return "KHÔNG ĐO ĐƯỢC", "cổng chạy quá %.0f giây" % TIMEOUT_CONG
    except Exception as e:
        return "KHÔNG ĐO ĐƯỢC", "không gọi được cổng: %s" % e
    ra = (r.stdout or "").strip()
    if not ra:
        return "ĐẠT", ""
    try:
        hs = (json.loads(ra) or {}).get("hookSpecificOutput") or {}
    except Exception:
        return "ĐẠT", ""          # cổng chỉ in nhắc, không ra quyết định
    if str(hs.get("permissionDecision") or "") == "deny":
        return "THIẾU", str(hs.get("permissionDecisionReason") or "").strip()
    try:
        goi = json.loads(ra)
    except Exception:
        goi = {}
    chu = str(hs.get("additionalContext") or goi.get("systemMessage") or "").strip()
    if chu:
        return "NHẮC", chu
    return "ĐẠT", ""


def kiem(prompt: str, mo_ta: str, cwd: str, transcript: str = "", ai_goi: str = ""):
    """(mọi cổng đều qua?, danh sách (tên cổng, trạng thái, lời)). Không ghi dấu, không sửa gì."""
    goc = os.path.join("/tmp", "tien-kiem-hop-cat-%d-%d" % (os.getpid(), int(time.time() * 1000) % 100000))
    ket = []
    try:
        env = dung_hop_cat(goc)
        tr_that = transcript or transcript_that(cwd)
        tr_bang = transcript_bang_gia(goc)
        for ten, viec, kieu in CONG_SOI_BRIEF:
            payload = {
                "session_id": os.environ.get("CLAUDE_CODE_SESSION_ID") or "tien-kiem",
                "transcript_path": tr_bang if kieu == "bang-gia" else tr_that,
                "cwd": cwd,
                "hook_event_name": "PreToolUse",
                "tool_name": "Agent",
                "tool_input": {"description": mo_ta, "prompt": prompt,
                               "subagent_type": "tho-fulfill"},
            }
            # `agent_id` cố ý BỎ TRỐNG: lượt thả của điều phối không có trường này, có nó vào
            # là hai cổng tự thoát sớm (worker đẻ cháu / lời gọi phát từ worker) -> đo lỏng.
            if ai_goi:
                payload["agent_id"] = ai_goi
            tt, loi = chay_cong(ten, payload, env, cwd)
            ket.append((ten, tt, viec, loi))
    finally:
        shutil.rmtree(goc, ignore_errors=True)
    return (not [k for k in ket if k[1] == "THIẾU"]), ket


def in_bang(ket, prompt: str, mo_ta: str, cwd: str) -> None:
    print("=" * 92)
    print("TIỀN KIỂM BRIEF — «%s» · %d ký tự · dự án %s"
          % (mo_ta or "(không đặt mô tả)", len(chuan_hoa(prompt)), scope(cwd)))
    print("=" * 92)
    for ten, tt, viec, loi in ket:
        dau = {"ĐẠT": "✅ ĐẠT  ", "THIẾU": "⛔ THIẾU", "NHẮC": "⚠️  NHẮC ",
               "KHÔNG ĐO ĐƯỢC": "➖ KHÔNG ĐO ĐƯỢC"}[tt]
        print("%s  %-34s %s" % (dau, ten, viec))
        if loi:
            for d in loi.splitlines():
                print("          │ " + d)
    for ten, viec in CONG_KHONG_SOI_BRIEF:
        print("➖ BỎ QUA  %-34s %s" % (ten, viec))
    print("-" * 92)


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True, description="Tiền kiểm brief trước khi thả thợ")
    ap.add_argument("--brief", help="tệp chứa brief; bỏ trống thì đọc từ ống dẫn")
    ap.add_argument("--mo-ta", default="", help="description sẽ đặt cho Agent (vài cổng soi cả nó)")
    ap.add_argument("--cwd", default=os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    ap.add_argument("--transcript", default="", help="ép transcript phiên (mặc định: tự dò)")
    a = ap.parse_args()

    if a.brief:
        try:
            with open(a.brief, encoding="utf-8") as fh:
                prompt = fh.read()
        except OSError as e:
            print("⛔ Không đọc được tệp brief: %s" % e)
            return 2
    elif not sys.stdin.isatty():
        prompt = sys.stdin.read()
    else:
        print("⛔ Chưa đưa brief. Dùng `--brief <tệp>` hoặc dẫn qua ống: `cat brief.md | ...`")
        return 2
    if not chuan_hoa(prompt):
        print("⛔ Brief rỗng — không có gì để kiểm.")
        return 2

    cwd = os.path.abspath(a.cwd)
    qua, ket = kiem(prompt, a.mo_ta, cwd, a.transcript)
    in_bang(ket, prompt, a.mo_ta, cwd)

    if not qua:
        ghi_nhat_ky("THIẾU · %s · %s · %s" % (scope(cwd), (a.mo_ta or "?")[:60],
                                              ", ".join(k[0] for k in ket if k[1] == "THIẾU")))
        print("⛔ CHƯA QUA — vá đúng chỗ cổng nêu ở trên rồi CHẠY LẠI lệnh này. "
              "Chưa có dấu tiền kiểm thì `tien_kiem_gate.py` sẽ chặn lượt thả.")
        print("   (Lệnh này KHÔNG sửa brief hộ — sửa xong phải kiểm lại vì vân tay tính "
              "trên chính nội dung brief.)")
        return 1

    # Dấu lưu THEO DỰ ÁN (`scope(cwd)`), mà cổng thả đọc dấu theo `cwd` của lượt thả. Chạy
    # tiền kiểm từ /tmp rồi thả thợ cho dự án thật = hai scope khác nhau = dấu vô dụng.
    if not os.path.isdir(os.path.join(cwd, ".git")):
        print("⚠️  Thư mục đang đứng (%s) không phải gốc kho mã — dấu sẽ lưu theo tên «%s». "
              "Thả thợ cho dự án khác thì chạy lại kèm `--cwd <gốc dự án>`." % (cwd, scope(cwd)))

    if [k for k in ket if k[1] == "NHẮC"]:
        print("⚠️  CÓ LỜI NHẮC ở trên — KHÔNG chặn, vẫn thả được. Nhưng vá brief bây giờ "
              "rẻ hơn nhiều so với đi chụp bù sau khi thợ đóng (ảnh không chụp bù được).")
    p = ghi_dau(cwd, prompt, a.mo_ta, [(k[0], k[1]) for k in ket])
    ghi_nhat_ky("ĐẠT · %s · %s · vân tay %s" % (scope(cwd), (a.mo_ta or "?")[:60],
                                                van_tay(prompt)[:16]))
    print("✅ QUA HẾT — đã ghi dấu tiền kiểm (hạn %.0f phút): %s" % (HAN_PHUT, p or "(ghi hỏng)"))
    print("   Thả thợ NGAY BÂY GIỜ với ĐÚNG brief này (sửa một ký tự là dấu mất hiệu lực).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
