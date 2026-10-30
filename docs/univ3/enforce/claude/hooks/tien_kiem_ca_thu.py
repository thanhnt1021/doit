#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tien_kiem_ca_thu.py — chín ca thử cho lệnh tiền kiểm brief + cổng bắt buộc chạy nó.

CA THẬT 19/09/2026 (lý do có bộ này): bốn lượt thả thợ bị cổng chặn ngay lúc bấm vì brief
thiếu điều kiện; founder chỉ thấy bốn dòng «0 tool uses ⎿ Done». Bộ ca dưới đây khoá đúng
những chỗ dễ trượt của cách chữa: báo THIẾU đúng chỗ, dấu phải bám nội dung brief, dấu phải
hết hạn, và cổng phải có lối ra (cửa thoát + fail-open) chứ không được làm kẹt phiên.

TẤT CẢ chạy trong hộp cát /tmp — KHÔNG đụng hàng chờ, sổ số, nhật ký hay dấu tiền kiểm thật.

    python3 ~/.claude/universal-hooks/tien_kiem_ca_thu.py
"""
import json
import os
import shutil
import subprocess
import sys
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
HOP = "/tmp/tien-kiem-ca-thu"
CWD = os.path.join(HOP, "du-an-gia")
_loi = [0]

BRIEF_DU = """W99 — THI CÔNG: thử cổng tiền kiểm brief.

GHI: %s/src/thu.ts
ĐỌC: %s/src
TÀI NGUYÊN: không

## GHI MỐC TIẾN ĐỘ — lệnh Bash RIÊNG
```
echo 'NN|<nhãn tiếng Việt có dấu>' > /tmp/claude-bg-progress/du-an-gia/w99-thu-cong-tien-kiem.progress
```
Làm: sửa `src/thu.ts` cho hết lỗi, chạy lại bài kiểm, báo cáo có số.
""" % (CWD, CWD)

BRIEF_THIEU_MOC = """W98 — THI CÔNG: rà code mail cảnh báo.

GHI: %s/src/mail.ts
ĐỌC: %s/src
TÀI NGUYÊN: không

Đọc mã rồi sửa chỗ gửi mail cảnh báo bị lặp.
""" % (CWD, CWD)


def ghi(ten, dat, chi_tiet=""):
    print(("  ✅ " if dat else "  ❌ ") + ten + (" — " + chi_tiet if chi_tiet else ""))
    if not dat:
        _loi[0] += 1


def moi_truong(**them):
    env = dict(os.environ,
               UNIV3_TIEN_KIEM_ROOT=os.path.join(HOP, "dau"),
               UNIV3_TIEN_KIEM_DEM_DIR=os.path.join(HOP, "dem"),
               UNIV3_TIEN_KIEM_LOG=os.path.join(HOP, "tien-kiem.log"),
               UNIV3_WQUEUE_ROOT=os.path.join(HOP, "worker-queue"),
               WSEQ_ROOT=os.path.join(HOP, "worker-counter"),
               UNIV3_DOD_ROOT=os.path.join(HOP, "dod"),
               UNIV3_NGHIEM_THU_ROOT=os.path.join(HOP, "nghiem-thu"),
               UNIV3_SO_LENH_ROOT=os.path.join(HOP, "so-lenh"),
               UNIV3_DEPLOY_QUEUE_ROOT=os.path.join(HOP, "deploy-queue"),
               UNIV3_CUA_THOAT_DIR=os.path.join(HOP, "cua-thoat"),
               UNIV3_LOG_DIR=os.path.join(HOP, "logs"),
               UNIV3_PROJECTS_ROOT=os.path.join(HOP, "projects"),
               UNIV3_PROGRESS_ROOT=os.path.join(HOP, "progress"),
               CLAUDE_CODE_SESSION_ID="ca-thu-w08",
               CLAUDE_PROJECT_DIR=CWD)
    env.update(them)
    return env


def dung_hop():
    shutil.rmtree(HOP, ignore_errors=True)
    for d in ("du-an-gia/src", "dau", "dem", "projects", "progress", "worker-queue",
              "worker-counter", "dod", "nghiem-thu", "so-lenh", "deploy-queue",
              "cua-thoat", "logs"):
        os.makedirs(os.path.join(HOP, d), exist_ok=True)
    # Transcript mang dấu «phiên đang chạy bảng worker» — cổng chỉ bật trong chế độ đó.
    p = os.path.join(HOP, "transcript.jsonl")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "id": "t1", "input": {
                "command": "echo '05|nhận việc' > /tmp/claude-bg-progress/du-an-gia/w01-a.progress"}}]}},
            ensure_ascii=False) + "\n")
    return p


def chay_tien_kiem(brief: str, mo_ta: str, env=None):
    p = os.path.join(HOP, "brief.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(brief)
    r = subprocess.run([sys.executable, os.path.join(HOOKS, "tien_kiem_brief.py"),
                        "--brief", p, "--mo-ta", mo_ta, "--cwd", CWD, "--transcript", ""],
                       capture_output=True, text=True, env=env or moi_truong(), cwd=CWD)
    return r.returncode, r.stdout + r.stderr


def chay_cong(brief: str, mo_ta: str, transcript: str, env=None, thu_muc_hook=HOOKS):
    payload = {"session_id": "ca-thu-w08", "transcript_path": transcript, "cwd": CWD,
               "hook_event_name": "PreToolUse", "tool_name": "Agent",
               "tool_input": {"description": mo_ta, "prompt": brief,
                              "subagent_type": "tho-fulfill"}}
    r = subprocess.run([sys.executable, os.path.join(thu_muc_hook, "tien_kiem_gate.py")],
                       input=json.dumps(payload, ensure_ascii=False),
                       capture_output=True, text=True, env=env or moi_truong(), cwd=HOP)
    ra = (r.stdout or "").strip()
    if not ra:
        return "allow", "", r.returncode
    try:
        hs = (json.loads(ra) or {}).get("hookSpecificOutput") or {}
    except Exception:
        return "allow", ra, r.returncode
    return (str(hs.get("permissionDecision") or "allow"),
            str(hs.get("permissionDecisionReason") or ""), r.returncode)


def main():
    print("=" * 92)
    print("TIỀN KIỂM BRIEF — 9 ca thử (hộp cát %s)" % HOP)
    print("=" * 92)

    # ── CA 1: brief thiếu câu ghi mốc -> THIẾU + mã thoát khác 0 ────────────────
    tr = dung_hop()
    ma, ra = chay_tien_kiem(BRIEF_THIEU_MOC, "W98 rà code mail cảnh báo")
    ghi("ca 1 — brief thiếu câu ghi mốc: tiền kiểm báo THIẾU, mã thoát khác 0",
        ma != 0 and "THIẾU câu ghi mốc tiến độ" in ra, "mã thoát %d" % ma)
    ghi("ca 1b — chỉ đích danh cổng nào chặn",
        "subagent_background_enforce.py" in ra and "⛔ THIẾU" in ra)

    # ── CA 2: brief đủ -> ĐẠT + mã thoát 0 + có dấu ────────────────────────────
    ma2, ra2 = chay_tien_kiem(BRIEF_DU, "W99 thử cổng tiền kiểm")
    dau = []
    for goc, _, tep in os.walk(os.path.join(HOP, "dau")):
        dau += [os.path.join(goc, t) for t in tep]
    ghi("ca 2 — brief đủ: tiền kiểm báo ĐẠT, mã thoát 0",
        ma2 == 0 and "QUA HẾT" in ra2, "mã thoát %d" % ma2)
    ghi("ca 2b — đã để lại dấu tiền kiểm", len(dau) == 1, "%d tệp dấu" % len(dau))

    # ── CA 3: đã tiền kiểm đạt -> cổng thả CHO QUA ────────────────────────────
    qd, ly, _ = chay_cong(BRIEF_DU, "W99 thử cổng tiền kiểm", tr)
    ghi("ca 3 — brief đã tiền kiểm đạt: cổng thả cho qua", qd == "allow", "quyết định %s" % qd)

    # ── CA 4: chưa tiền kiểm -> cổng thả CHẶN + in đúng lệnh cần chạy ─────────
    qd4, ly4, _ = chay_cong(BRIEF_THIEU_MOC, "W98 rà code mail cảnh báo", tr)
    ghi("ca 4 — brief chưa tiền kiểm: cổng thả CHẶN", qd4 == "deny", "quyết định %s" % qd4)
    ghi("ca 4b — thông điệp chặn có đúng lệnh phải gõ",
        "tien_kiem_brief.py --brief" in ly4)
    ghi("ca 4c — việc bị chặn vào hàng chờ giữ nguyên brief (thả lại chạy y việc cũ)",
        "VÀO HÀNG CHỜ" in ly4, ly4[-200:].replace("\n", " ")[:120])

    # ── CA 5: tiền kiểm brief A rồi thả brief B -> CHẶN (vân tay không khớp) ──
    khac = BRIEF_DU.replace("sửa `src/thu.ts` cho hết lỗi", "xoá `src/thu.ts` đi")
    qd5, _, _ = chay_cong(khac, "W99 thử cổng tiền kiểm", tr)
    ghi("ca 5 — kiểm brief A rồi thả brief B: CHẶN", qd5 == "deny", "quyết định %s" % qd5)

    # ── CA 6: dấu quá hạn -> CHẶN ────────────────────────────────────────────
    with open(dau[0], encoding="utf-8") as fh:
        ban = json.load(fh)
    ban["luc"] = time.time() - 999 * 60
    with open(dau[0], "w", encoding="utf-8") as fh:
        json.dump(ban, fh, ensure_ascii=False)
    qd6, ly6, _ = chay_cong(BRIEF_DU, "W99 thử cổng tiền kiểm", tr)
    ghi("ca 6 — dấu tiền kiểm quá hạn: CHẶN", qd6 == "deny", "quyết định %s" % qd6)
    ghi("ca 6b — nói rõ là quá hạn chứ không phải chưa kiểm", "QUÁ HẠN" in ly6)

    # ── CA 7: cửa thoát có chủ ý -> cho qua, có ghi vết ──────────────────────
    qd7, _, _ = chay_cong(
        BRIEF_THIEU_MOC + "\ntien-kiem-bo-qua: máy đo hỏng, founder đã chốt miệng thả ngay\n",
        "W98 rà code mail cảnh báo", tr)
    try:
        nk = open(os.path.join(HOP, "tien-kiem.log"), encoding="utf-8").read()
    except OSError:
        nk = ""
    ghi("ca 7 — có dòng vượt có chủ ý: cho qua", qd7 == "allow", "quyết định %s" % qd7)
    ghi("ca 7b — lần vượt cổng ĐƯỢC GHI VẾT", "VƯỢT CỔNG" in nk,
        nk.strip().splitlines()[-1][:110] if nk.strip() else "(nhật ký rỗng)")

    # ── CA 8: hook hỏng (thiếu tệp lệnh tiền kiểm) -> CHO QUA, không vỡ phiên ─
    hong = os.path.join(HOP, "hook-hong")
    os.makedirs(hong, exist_ok=True)
    shutil.copy(os.path.join(HOOKS, "tien_kiem_gate.py"), hong)
    qd8, ly8, rc8 = chay_cong(BRIEF_THIEU_MOC, "W98 rà code mail cảnh báo", tr,
                              thu_muc_hook=hong)
    ghi("ca 8 — thiếu tệp `tien_kiem_brief.py`: cổng cho qua, mã thoát 0",
        qd8 == "allow" and rc8 == 0, "quyết định %s · mã thoát %d" % (qd8, rc8))

    # ── CA 9: CHU TRÌNH CỨU — chặn -> vào hàng chờ -> tiền kiểm -> thả lại chạy được ──
    # Đây là phép thử «cổng đòi việc phải có lối ra»: chặn mà không đi tiếp được thì cổng
    # chỉ là chỗ chết việc.
    brief9 = BRIEF_DU.replace("W99", "W97").replace("w99-thu-cong-tien-kiem",
                                                    "w97-thu-cong-tien-kiem")
    qd9a, ly9a, _ = chay_cong(brief9, "W97 chu trình cứu", tr)
    ve9 = [f for f in os.listdir(os.path.join(HOP, "worker-queue",
                                              "".join(c if c.isalnum() else "-" for c in CWD)))
           if f.endswith(".json")] if os.path.isdir(
        os.path.join(HOP, "worker-queue", "".join(c if c.isalnum() else "-" for c in CWD))) else []
    ma9, ra9 = chay_tien_kiem(brief9, "W97 chu trình cứu")
    qd9b, _, _ = chay_cong(brief9, "W97 chu trình cứu", tr)
    ghi("ca 9 — lượt đầu bị CHẶN và việc vào hàng chờ",
        qd9a == "deny" and "VÀO HÀNG CHỜ" in ly9a and ve9, "%d vé trong sổ" % len(ve9))
    ghi("ca 9b — chạy tiền kiểm xong thì thả lại ĐÚNG brief cũ là qua",
        ma9 == 0 and qd9b == "allow", "tiền kiểm mã %d · cổng %s" % (ma9, qd9b))

    # ── Lưới cuối: tiền kiểm KHÔNG được đụng kho thật ────────────────────────
    ghi("lưới cuối — không sót hộp cát nào trong /tmp",
        not [d for d in os.listdir("/tmp") if d.startswith("tien-kiem-hop-cat-")],
        str([d for d in os.listdir("/tmp") if d.startswith("tien-kiem-hop-cat-")]))

    print("-" * 92)
    tong = 15
    print("KẾT: %d/%d ca ĐẠT" % (tong - _loi[0], tong))
    shutil.rmtree(HOP, ignore_errors=True)
    return 1 if _loi[0] else 0


if __name__ == "__main__":
    sys.exit(main())
