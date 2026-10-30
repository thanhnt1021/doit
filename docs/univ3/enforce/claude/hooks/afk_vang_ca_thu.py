#!/usr/bin/env python3
"""afk_vang_ca_thu.py — ca thử «anh vắng khỏi CLI» cho cổng hộp hỏi (thẻ Task-12102026-21).

Ca gốc: 16/10/2026 06:10–06:24 anh Thành Reply 1A trên Telegram, con canh đẩy vào phiên ChicHub; không cờ
/afk, đường hầm DB tắt (psql «timeout expired») → mốc Telegram từ DB = None → afk_hoi_inbox_gate cho hộp
AskUserQuestion qua. Nay cổng đọc thêm bản ghi phiên (`transcript_path`).
Chạy: python3 afk_vang_ca_thu.py   (hoặc bash chay-het-ca-thu.sh afk_vang). Tự dựng hộp cát, tự xoá.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

GOC = os.path.dirname(os.path.abspath(__file__))
CONG = os.path.join(GOC, "afk_hoi_inbox_gate.py")
TT = os.path.join(GOC, "afk_trang_thai.py")

CANH_ANH = ("🔔 CÓ CẬP NHẬT VIỆC GIAO DEV MỚI — xử lý theo .claude/commands/check-dev-task-update.md\n"
            "1 cập nhật Việc giao Dev chưa xử lý (cũ → mới):\n"
            "#8468 · Task-16102026-02 · cột \"Xong\" · 16/10 06:10 giờ VN · anh Thành [anh Thành] · Bình luận\n"
            "   Thẻ: toàn bộ các task hôm nay xong chưa???\n"
            "   │ Nathan Goo trả lời (Reply) tin của việc trên Telegram:\n"
            "   │ 06:10 — 1A\n")
CANH_NGUOI_KHAC = ("🔔 CÓ CẬP NHẬT VIỆC GIAO DEV MỚI — xử lý theo .claude/commands/check-dev-task-update.md\n"
                   "#8500 · Task-16102026-05 · cột \"Đang làm\" · 16/10 06:12 giờ VN · Phương [Phương] · Bình luận\n"
                   "   │ Phương ghi trên web: đơn này sai màu\n")


def gio(hm):
    return "2026-10-16T%s:00.000Z" % hm      # giờ UTC cho gọn; chỉ so thứ tự


def go_cli(hm, chu="làm tiếp đi"):
    return {"type": "user", "timestamp": gio(hm), "origin": {"kind": "human"}, "turnOrigin": "human",
            "message": {"role": "user", "content": chu}}


def go_chen(hm, chu="a"):
    return {"type": "attachment", "timestamp": gio(hm),
            "attachment": {"type": "queued_command", "prompt": chu, "origin": {"kind": "human"}, "humanTurn": True}}


def lich(hm):
    return {"type": "user", "timestamp": gio(hm), "isMeta": True, "promptSource": "system", "turnOrigin": "scheduled",
            "message": {"role": "user", "content": "Theo dõi thẻ Task-12102026-31 …"}}


def canh(hm, tep):
    return {"type": "user", "timestamp": gio(hm), "promptSource": "system", "turnOrigin": "task_notification",
            "origin": {"kind": "task-notification"},
            "message": {"role": "user", "content": "<task-notification>\n<task-id>b7</task-id>\n<output-file>%s"
                        "</output-file>\n<status>completed</status>\n</task-notification>" % tep}}


def kenh_tg(hm):
    return {"type": "user", "timestamp": gio(hm),
            "message": {"role": "user", "content": '<channel source="plugin:telegram:telegram" chat_id="x">1A</channel>'}}


def ket_qua_cong(hop, ban_ghi, co_afk=False):
    afk = os.path.join(hop, "afk")
    os.makedirs(afk, exist_ok=True)
    tep_co = os.path.join(afk, "trang-thai.json")
    if co_afk:
        with open(tep_co, "w") as f:
            json.dump({"bat_luc": 1, "het_han": 9999999999}, f)
    elif os.path.exists(tep_co):
        os.remove(tep_co)
    so = os.path.join(hop, "so-lenh-trong")
    os.makedirs(so, exist_ok=True)
    env = dict(os.environ, UNIV3_AFK_DIR=afk, UNIV3_SO_LENH_ROOT=so, UNIV3_MOC_TELEGRAM_ANH="0")
    env.pop("UNIV3_VANG_TELEGRAM_TAT", None)
    tr = os.path.join(hop, "phien.jsonl")
    with open(tr, "w", encoding="utf-8") as f:
        for j in ban_ghi:
            f.write(json.dumps(j, ensure_ascii=False) + "\n")
    vao = json.dumps({"tool_name": "AskUserQuestion", "cwd": hop, "transcript_path": tr,
                      "tool_input": {"questions": [{"question": "Sửa ở đâu?", "options": [{"label": "A"}]}]}})
    r = subprocess.run([sys.executable, CONG], input=vao, capture_output=True, text=True, env=env, timeout=20)
    return "chan" if '"deny"' in r.stdout else "qua"


def main():
    hop = tempfile.mkdtemp(prefix="afk-vang-ca-thu-")
    tong = sai = 0
    try:
        t_anh = os.path.join(hop, "canh-anh.output")
        t_khac = os.path.join(hop, "canh-khac.output")
        open(t_anh, "w", encoding="utf-8").write(CANH_ANH)
        open(t_khac, "w", encoding="utf-8").write(CANH_NGUOI_KHAC)
        ca = [
            ("1. CA GỐC: không cờ /afk, DB không với tới, gõ CLI 18:11 → anh Reply Telegram 23:10 → CHẶN",
             [go_cli("18:11"), canh("23:10", t_anh)], False, "chan"),
            ("2. Reply Telegram 23:10 → anh gõ CLI 23:15 → CHO QUA", [canh("23:10", t_anh), go_cli("23:15")], False, "qua"),
            ("3. chỉ gõ CLI, không có lời Telegram → CHO QUA", [go_cli("18:11")], False, "qua"),
            ("4. lời nhắc theo lịch sau lời Telegram không tính là gõ CLI → CHẶN",
             [go_cli("18:11"), canh("23:10", t_anh), lich("23:20")], False, "chan"),
            ("5. canh chỉ có cập nhật của người khác (không phải anh, không Telegram) → CHO QUA",
             [go_cli("18:11"), canh("23:10", t_khac)], False, "qua"),
            ("6. anh gõ chen (queued) sau lời Telegram → CHO QUA",
             [canh("23:10", t_anh), go_chen("23:12")], False, "qua"),
            ("7. kênh Telegram của Claude Code (<channel source=…telegram>) là lời cuối → CHẶN",
             [go_cli("18:11"), kenh_tg("23:10")], False, "chan"),
            ("8. cờ /afk bật, lời cuối gõ CLI → vẫn CHẶN (hành vi cũ)", [go_cli("23:15")], True, "chan"),
            ("9. tệp đầu ra con canh đã bị xoá → không suy ra Telegram → CHO QUA",
             [go_cli("18:11"), canh("23:10", os.path.join(hop, "khong-co.output"))], False, "qua"),
        ]
        for ten, bg, afk, mong in ca:
            tong += 1
            kq = ket_qua_cong(hop, bg, afk)
            dung = kq == mong
            sai += 0 if dung else 1
            print("%s %s (được: %s)" % ("PASS" if dung else "FAIL", ten, kq))
        # Sổ lệnh: mục là lời nhắc theo lịch bị bỏ qua khi tìm lượt gõ CLI cuối
        sys.path.insert(0, GOC)
        import afk_trang_thai as T
        tr = os.path.join(hop, "phien-so.jsonl")
        bg = [go_cli("18:11"), lich("23:20")]
        with open(tr, "w", encoding="utf-8") as f:
            for j in bg:
                f.write(json.dumps(j, ensure_ascii=False) + "\n")
        e = lambda hm: T._epoch_iso(gio(hm))
        d = os.path.join(hop, "so", "DuAn", "2026-10-16")
        os.makedirs(d)
        with open(os.path.join(d, ".so.json"), "w") as f:
            json.dump({"muc": {"L01": {"luc": str(e("18:11")), "transcript": tr, "offset": "0"},
                               "L02": {"luc": str(e("23:20")), "transcript": tr, "offset": "0"}}}, f)
        cu, T.GOC_SO_LENH = T.GOC_SO_LENH, os.path.join(hop, "so")
        try:
            tong += 1
            dung = T.luot_go_cli_cuoi() == e("18:11")
            sai += 0 if dung else 1
            print("%s 10. sổ lệnh: bỏ mục lời nhắc theo lịch 23:20, lượt gõ tay cuối = 18:11" % ("PASS" if dung else "FAIL"))
        finally:
            T.GOC_SO_LENH = cu
        # Bộ ca cũ của afk_trang_thai
        r = subprocess.run([sys.executable, TT, "--ca-thu"], capture_output=True, text=True, timeout=30)
        tong += 1
        dung = r.returncode == 0
        sai += 0 if dung else 1
        print("%s 11. bộ ca cũ afk_trang_thai --ca-thu (%s)" % ("PASS" if dung else "FAIL",
                                                              (r.stdout.strip().splitlines() or ["?"])[-1]))
    finally:
        shutil.rmtree(hop, ignore_errors=True)
    print("\n%d/%d ca đúng" % (tong - sai, tong))
    return 1 if sai else 0


if __name__ == "__main__":
    sys.exit(main())
