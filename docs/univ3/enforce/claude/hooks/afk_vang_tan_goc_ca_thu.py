#!/usr/bin/env python3
"""afk_vang_tan_goc_ca_thu.py — ca thử phiếu P005 (C-HX, 18/10/2026): «AFK thì KHÔNG BAO GIỜ hỏi trong CLI».

Ca gốc 18/10/2026: founder /afk 17/10 (cờ hết hạn 17:20), suốt đêm chỉ nhắn Telegram (tin #343-#347 lúc
06:18-06:20), không gõ CLI. 06:51 cổng Stop `ve_cho_founder` ra lệnh «gom thành tối đa 4 câu AskUserQuestion»,
`afk_hoi_inbox_gate` thấy cờ hết hạn (và đã tự xoá cờ) → hộp hỏi bật trong CLI. Founder: «tao đã afk thì mày
phải biết mà gửi vào tele chứ???? fix tận gốc».

Mỗi ca chạy trong HOME GIẢ (thư mục tạm) — không đụng cờ thật `~/.claude/afk/trang-thai.json`, không mạng.
Chạy: python3 afk_vang_tan_goc_ca_thu.py   → in «N/N ca đúng», mã thoát 0 khi đạt hết.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

GOC = os.path.dirname(os.path.abspath(__file__))
CONG = os.path.join(GOC, "afk_hoi_inbox_gate.py")
MODE = os.path.join(GOC, "afk_mode.py")
TT = os.path.join(GOC, "afk_trang_thai.py")
VDS = os.path.join(GOC, "ve_de_sau_gate.py")
KENH_CHX = ("python3 scripts/sep-viec/sep_viec.py gui --ma <mã việc> --tieu-de \"Câu hỏi chờ anh quyết\" "
            "--hoi \"1. … 1A (đề xuất) · 1B\" --html --thu   # rồi bỏ --thu để gửi thật\n")

KQ = {"tong": 0, "sai": 0}


def ca(ten, dung, them=""):
    KQ["tong"] += 1
    KQ["sai"] += 0 if dung else 1
    print("%s %s%s" % ("PASS" if dung else "FAIL", ten, ("  — " + them) if (them and not dung) else ""))


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(t))


def go_cli(t, chu="làm tiếp đi"):
    return {"type": "user", "timestamp": iso(t), "origin": {"kind": "human"}, "turnOrigin": "human",
            "promptSource": "typed", "message": {"role": "user", "content": chu}}


def nen_ngu_canh(t):
    # Dòng tóm tắt nén ngữ cảnh — đo thật 18/10 06:51:30: isCompactSummary=True, turnOrigin=human, KHÔNG có origin.
    return {"type": "user", "timestamp": iso(t), "isCompactSummary": True, "isVisibleInTranscriptOnly": True,
            "turnOrigin": "human",
            "message": {"role": "user", "content": "This session is being continued from a previous conversation…"}}


def thong_bao_nen(t):
    return {"type": "user", "timestamp": iso(t), "promptSource": "system", "turnOrigin": "task_notification",
            "origin": {"kind": "task-notification"},
            "message": {"role": "user", "content": "<task-notification>\n<task-id>b1</task-id>\n<status>completed"
                        "</status>\n<summary>🔔 CÓ VIỆC SẾP MỚI: 2 tin (id 343,347)</summary>\n</task-notification>"}}


def tin_lien_phien(t):
    return {"type": "user", "timestamp": iso(t), "promptSource": "system", "turnOrigin": "peer",
            "origin": {"kind": "peer", "name": "nhatrangdream-39"},
            "message": {"role": "user", "content": "<cross-session-message from=\"x\">tao về rồi</cross-session-message>"}}


def tro_ly(t, chu="Xong phần này."):
    return {"type": "assistant", "timestamp": iso(t),
            "message": {"role": "assistant", "content": [{"type": "text", "text": chu}]}}


class Hop:
    """Một HOME giả: cờ AFK, sổ lệnh, mốc Telegram, hàng chờ vé — tất cả nằm trong thư mục tạm."""

    def __init__(self):
        self.goc = tempfile.mkdtemp(prefix="afk-tan-goc-")
        self.home = os.path.join(self.goc, "home")
        self.afk = os.path.join(self.home, ".claude", "afk")
        os.makedirs(self.afk)
        self.chx = os.path.join(self.goc, "C-HX")
        os.makedirs(os.path.join(self.chx, ".claude"))
        # Giống máy thật: .claude/ của C-HX bị .gitignore → sep_viec.py tự khai kênh ở ~/.claude/afk/inbox-C-HX.txt
        with open(os.path.join(self.afk, "inbox-C-HX.txt"), "w", encoding="utf-8") as f:
            f.write(KENH_CHX)
        self.tu_khai = os.path.join(self.goc, "du-an-tu-khai")
        os.makedirs(os.path.join(self.tu_khai, ".claude", "con"))
        with open(os.path.join(self.tu_khai, ".claude", "afk-inbox.txt"), "w", encoding="utf-8") as f:
            f.write("node tools/hoi-founder.mjs --thu")
        self.khong_tg = os.path.join(self.goc, "du-an-khong-tg")
        os.makedirs(self.khong_tg)
        self.tr = os.path.join(self.goc, "phien.jsonl")
        open(self.tr, "w").close()

    def env(self, cwd):
        e = dict(os.environ, HOME=self.home, CLAUDE_PROJECT_DIR=cwd)
        for k in ("UNIV3_AFK_DIR", "UNIV3_SO_LENH_ROOT", "UNIV3_MOC_TELEGRAM_ANH", "UNIV3_VANG_TELEGRAM_TAT",
                  "UNIV3_WQUEUE_ROOT", "WSEQ_ROOT", "UNIV3_CUA_THOAT_DIR", "UNIV3_LOG_DIR"):
            e.pop(k, None)
        e["UNIV3_QUEUE_RECONCILE"] = "0"
        return e

    def co(self, bat_luc, het_han):
        with open(os.path.join(self.afk, "trang-thai.json"), "w") as f:
            json.dump({"bat_luc": int(bat_luc), "het_han": int(het_han), "trich": "/afk"}, f)

    def bo_co(self):
        try:
            os.remove(os.path.join(self.afk, "trang-thai.json"))
        except FileNotFoundError:
            pass

    def co_ton_tai(self):
        return os.path.exists(os.path.join(self.afk, "trang-thai.json"))

    def moc_tg(self, du_an, moc, tho=None):
        p = os.path.join(self.afk, "moc-telegram-%s.json" % du_an)
        with open(p, "w") as f:
            f.write(tho if tho is not None else json.dumps({"moc": moc, "nguon": "ca-thu"}))
        return p

    def bo_moc_tg(self):
        for t in os.listdir(self.afk):
            if t.startswith("moc-telegram"):
                p = os.path.join(self.afk, t)
                if os.path.isdir(p):
                    os.rmdir(p)
                else:
                    os.remove(p)

    def phien(self, dong):
        with open(self.tr, "w", encoding="utf-8") as f:
            for j in dong:
                f.write(json.dumps(j, ensure_ascii=False) + "\n")

    def cong(self, cwd):
        vao = json.dumps({"tool_name": "AskUserQuestion", "cwd": cwd, "transcript_path": self.tr,
                          "session_id": "ca-thu", "hook_event_name": "PreToolUse",
                          "tool_input": {"questions": [{"question": "Xoá hay giữ?", "options": [{"label": "A"}]}]}})
        t0 = time.time()
        r = subprocess.run([sys.executable, CONG], input=vao, capture_output=True, text=True,
                           env=self.env(cwd), timeout=30)
        return ("chan" if '"deny"' in r.stdout else "qua"), r.stdout, r.stderr, time.time() - t0

    def mode(self, cwd, prompt):
        vao = json.dumps({"prompt": prompt, "cwd": cwd, "transcript_path": self.tr, "session_id": "ca-thu",
                          "hook_event_name": "UserPromptSubmit"})
        return subprocess.run([sys.executable, MODE], input=vao, capture_output=True, text=True,
                              env=self.env(cwd), timeout=30)

    def py(self, cwd, ma):
        """Chạy một đoạn Python trong HOME giả (nhập module hook ở GOC)."""
        return subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, %r)\n" % GOC + ma],
                              capture_output=True, text=True, env=self.env(cwd), timeout=60)

    def don(self):
        shutil.rmtree(self.goc, ignore_errors=True)


def main():
    h = Hop()
    now = time.time()
    bat = now - 13 * 3600
    het = now - 5 * 3600
    try:
        # ── AC1 — cờ hết hạn + Telegram C-HX mới hơn lượt CLI cuối → CHẶN, chỉ đường sep_viec.py gui
        h.co(bat, het)
        h.phien([go_cli(bat + 5, "/afk"), thong_bao_nen(now - 600)])
        h.moc_tg("C-HX", now - 600)
        kq, out, err, _ = h.cong(h.chx)
        ca("AC1. cờ hết hạn 5 tiếng, lượt CLI cuối = /afk, Telegram C-HX 10 phút trước → CHẶN",
           kq == "chan" and "sep_viec.py gui" in out and not err.strip(), "kq=%s err=%s" % (kq, err[-200:]))
        ca("AC1b. cổng KHÔNG xoá cờ hết hạn (còn dấu bat_luc cho lần sau)", h.co_ton_tai())

        # ── O1.7 — founder đã GÕ CLI sau khi bật /afk rồi lại đi, nhắn Telegram mới hơn → CHẶN (chỉ H3 cứu)
        h.phien([go_cli(bat + 5, "/afk"), go_cli(now - 3600, "sửa nav"), thong_bao_nen(now - 600)])
        kq, out, err, _ = h.cong(h.chx)
        ca("AC1c. cờ hết hạn, gõ CLI 1 tiếng trước, Telegram C-HX 10 phút trước (mới hơn) → CHẶN",
           kq == "chan" and "sep_viec.py gui" in out, "kq=%s" % kq)

        # ── AC2 — cờ hết hạn + KHÔNG lượt gõ CLI thật nào sau bat_luc, dự án không Telegram → CHẶN
        h.bo_moc_tg()
        h.phien([go_cli(bat + 5, "/afk"), thong_bao_nen(now - 7200)])
        kq, out, err, _ = h.cong(h.khong_tg)
        ca("AC2. cờ hết hạn, chưa gõ CLI từ lúc bật, dự án không Telegram → CHẶN, chỉ cau-hoi-<dự án>.md",
           kq == "chan" and "cau-hoi-du-an-khong-tg.md" in out and not err.strip(), "kq=%s err=%s" % (kq, err[-200:]))
        h.phien([])
        kq, out, err, _ = h.cong(h.khong_tg)
        ca("AC2b. cờ hết hạn, bản ghi phiên rỗng (phiên mới mở lúc vắng) → CHẶN", kq == "chan", kq)

        # ── AC9 / R2 — tin máy sau bat_luc KHÔNG được tính là founder gõ CLI
        h.phien([go_cli(bat + 5, "/afk"), nen_ngu_canh(now - 300)])
        kq, *_ = h.cong(h.khong_tg)
        ca("AC9a. dòng nén ngữ cảnh (isCompactSummary, turnOrigin=human) sau bat_luc → vẫn CHẶN", kq == "chan", kq)
        h.phien([go_cli(bat + 5, "/afk"), thong_bao_nen(now - 400), tin_lien_phien(now - 300)])
        kq, *_ = h.cong(h.khong_tg)
        ca("AC9b. thông báo nền + tin liên phiên «tao về rồi» sau bat_luc → vẫn CHẶN", kq == "chan", kq)
        r = h.mode(h.khong_tg, "<task-notification>\n<summary>tao về rồi</summary>\n</task-notification>")
        ca("AC9c. thông báo nền chứa «tao về rồi» đi qua afk_mode → cờ KHÔNG tắt", h.co_ton_tai(), r.stderr[-200:])
        r = h.py(h.khong_tg, "import afk_trang_thai as T\n"
                 "print(T.dang_vang(%r, %r, nhanh=True, prompt='<task-notification>x</task-notification>')[0])"
                 % (h.khong_tg, h.tr))
        ca("AC9d. lượt UserPromptSubmit là thông báo nền → dang_vang xét đủ (không coi là vừa gõ CLI) → vắng",
           r.stdout.strip() == "True", r.stdout + r.stderr[-200:])
        # sổ lệnh: mục là tin kênh Telegram không tính là gõ tay
        so = os.path.join(h.home, ".claude", "so-lenh", "DuAn", time.strftime("%Y-%m-%d"))
        os.makedirs(so, exist_ok=True)
        trk = os.path.join(h.goc, "phien-kenh.jsonl")
        with open(trk, "w", encoding="utf-8") as f:
            f.write(json.dumps({"type": "user", "timestamp": iso(now - 200), "message": {
                "role": "user", "content": '<channel source="plugin:telegram:telegram" chat_id="1">1A</channel>'}}) + "\n")
        with open(os.path.join(so, ".so.json"), "w") as f:
            json.dump({"muc": {"L01": {"luc": str(now - 200), "transcript": trk, "offset": "0"}}}, f)
        h.phien([go_cli(bat + 5, "/afk")])
        kq, *_ = h.cong(h.khong_tg)
        ca("AC9e. mục sổ lệnh là tin kênh Telegram (không phải gõ tay) → vẫn CHẶN", kq == "chan", kq)
        shutil.rmtree(os.path.join(h.home, ".claude", "so-lenh"))

        # ── AC5 — founder gõ CLI thật mới hơn Telegram cuối → CÓ MẶT, cho qua
        h.moc_tg("C-HX", now - 1800)
        h.phien([go_cli(bat + 5, "/afk"), thong_bao_nen(now - 1800), go_cli(now - 5, "sửa giúp tao cái nav")])
        kq, out, err, _ = h.cong(h.chx)
        ca("AC5. cờ hết hạn, Telegram 30 phút trước, gõ CLI «sửa giúp tao cái nav» vừa xong → CHO QUA", kq == "qua", kq)
        h.bo_moc_tg()
        h.phien([go_cli(bat + 5, "/afk"), go_cli(now - 5, "làm tiếp")])
        kq, *_ = h.cong(h.khong_tg)
        ca("AC5b. dự án không Telegram, cờ hết hạn, đã gõ CLI sau bat_luc → CHO QUA (không chặn nhầm)", kq == "qua", kq)
        h.phien([go_cli(bat + 30, "làm tiếp")])
        kq, *_ = h.cong(h.khong_tg)
        ca("O1.9. lượt gõ trong biên 120 giây sau bat_luc (chính lượt /afk) không tính là đã về → CHẶN", kq == "chan", kq)

        # ── AC6 — cờ CÒN hạn → chặn như cũ, kể cả vừa gõ CLI
        h.co(now - 600, now + 7 * 3600)
        h.moc_tg("C-HX", now - 60)
        h.phien([go_cli(now - 5, "sửa nav")])
        kq, out, *_ = h.cong(h.chx)
        ca("AC6. cờ còn hạn, vừa gõ CLI, có Telegram → CHẶN (luật 11/10 giữ nguyên)",
           kq == "chan" and "sep_viec.py gui" in out, kq)

        # ── AC4 — founder nói đã về → hỏi CLI được (4 câu)
        for cau in ("tao về rồi", "ngồi máy rồi", "tắt afk", "tao ve roi"):
            h.co(now - 600, now + 7 * 3600)
            h.moc_tg("C-HX", now - 60)
            r = h.mode(h.chx, cau)
            h.phien([go_cli(now - 60, "/afk"), go_cli(now - 1, cau)])
            kq, *_ = h.cong(h.chx)
            ca("AC4. «%s» → cờ tắt + AskUserQuestion CHO QUA" % cau, (not h.co_ton_tai()) and kq == "qua",
               "co=%s kq=%s err=%s" % (h.co_ton_tai(), kq, r.stderr[-200:]))
        r = h.mode(h.chx, "tao không ngồi máy rồi")
        ca("AC4b. «tao không ngồi máy rồi» (phủ định) → BẬT cờ, không tắt", h.co_ton_tai(), r.stderr[-200:])

        # ── AC3 — ve_cho_founder (khối Stop của ve_de_sau_gate) lúc vắng không đòi AskUserQuestion, không lặp
        ma_vcf = ("import ve_cho_founder as V, json, os, time\n"
                  "V.phan_tich = lambda cwd: ([[{'ma':'x1','so':'W09','luc':time.time()-3600,"
                  "'description':'Việc W09 để lại: chờ founder quyết xoá hay giữ bản thử'}]], [], [], 1)\n"
                  "p = os.path.join(%r, 'nhac.json')\n"
                  "V._so_nhac = lambda cwd: p\n"
                  "print(json.dumps([V.khoi_nhac(%%r, transcript=%r), V.khoi_nhac(%%r, transcript=%r)]))\n"
                  % (h.goc, h.tr, h.tr))
        h.co(bat, het)
        h.moc_tg("C-HX", now - 600)
        h.phien([go_cli(bat + 5, "/afk"), thong_bao_nen(now - 600)])
        try:
            os.remove(os.path.join(h.goc, "nhac.json"))
        except FileNotFoundError:
            pass
        r = h.py(h.chx, ma_vcf % (h.chx, h.chx))
        try:
            lan1, lan2 = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            lan1, lan2 = "", "LỖI " + r.stderr[-300:]
        dong_auq = [d for d in lan1.splitlines() if "AskUserQuestion" in d]
        ca("AC3a. vắng: khối nhắc vé chờ founder KHÔNG ra lệnh AskUserQuestion (chỉ nằm trong câu CẤM), CÓ sep_viec.py gui",
           bool(lan1) and all("CẤM" in d for d in dong_auq) and "sep_viec.py gui" in lan1,
           "lan1=%r" % lan1[:400])
        ca("AC3b. vắng: lần Stop thứ hai (đã chỉ đường inbox) → im, cho kết lượt", lan2 == "", "lan2=%r" % lan2[:200])
        # founder về → hỏi trong CLI lại như cũ
        h.bo_co()
        h.bo_moc_tg()
        h.phien([go_cli(now - 1, "tao về rồi")])
        r = h.py(h.chx, "import ve_cho_founder as V, json, os, time\n"
                 "V.phan_tich = lambda cwd: ([[{'ma':'x1','so':'W09','luc':time.time()-3600,"
                 "'description':'Việc W09 để lại: chờ founder quyết xoá hay giữ bản thử'}]], [], [], 1)\n"
                 "V._so_nhac = lambda cwd: os.path.join(%r, 'nhac.json')\n"
                 "print(json.dumps(V.khoi_nhac(%r, transcript=%r)))\n" % (h.goc, h.chx, h.tr))
        try:
            lan3 = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:
            lan3 = "LỖI " + r.stderr[-300:]
        ca("AC4c. founder về ngay sau lần nhắc lúc vắng → nhắc NGAY (không đợi 20 phút), đòi AskUserQuestion như cũ",
           "NGAY LƯỢT NÀY" in lan3 and "AskUserQuestion" in lan3, "lan3=%r" % lan3[:300])

        # ── AC3 đầu-cuối: hook Stop ve_de_sau_gate thật, hàng chờ vé trong HOME giả
        h.co(bat, het)
        h.moc_tg("C-HX", now - 600)
        r = h.py(h.chx, "import worker_queue as W; print(W.thu_muc(%r))" % h.chx)
        tm = (r.stdout.strip().splitlines() or [""])[-1]
        if tm and os.path.isdir(tm):
            for t in os.listdir(tm):
                if t.startswith(".nhac"):
                    os.remove(os.path.join(tm, t))
            with open(os.path.join(tm, "ve-ca-thu.json"), "w", encoding="utf-8") as f:
                json.dump({"ma": "cathu00001", "so": "W09", "slug": "xoa-hay-giu", "luc": now - 3600, "cwd": h.chx,
                           "cho_founder": True, "nguon": "W09",
                           "description": "Việc W09 để lại: chờ founder quyết xoá hay giữ bản thử trên trang quản trị",
                           "muc": ["xoá hay giữ bản thử"]}, f, ensure_ascii=False)
        h.phien([go_cli(bat + 5, "/afk"), thong_bao_nen(now - 600), tro_ly(now - 2, "Đã đẩy xong lô 6.")])
        vao = json.dumps({"transcript_path": h.tr, "cwd": h.chx, "session_id": "ca-thu-stop",
                          "hook_event_name": "Stop", "stop_hook_active": False})
        r1 = subprocess.run([sys.executable, VDS], input=vao, capture_output=True, text=True, env=h.env(h.chx), timeout=60)
        r2 = subprocess.run([sys.executable, VDS], input=vao, capture_output=True, text=True, env=h.env(h.chx), timeout=60)
        try:
            ly1 = json.loads(r1.stdout or "{}").get("reason", "")
        except Exception:
            ly1 = r1.stdout
        auq1 = [d for d in ly1.splitlines() if "AskUserQuestion" in d]
        ca("AC3c. hook Stop ve_de_sau_gate thật, lúc vắng: lý do chặn có sep_viec.py gui, AskUserQuestion chỉ trong câu CẤM",
           "sep_viec.py gui" in ly1 and all("CẤM" in d for d in auq1) and "Traceback" not in r1.stderr,
           "out=%r err=%r" % (r1.stdout[:300], r1.stderr[-300:]))
        ca("AC3d. hook Stop lần 2 → không chặn nữa (không lặp vô hạn)",
           '"block"' not in (r2.stdout or "") or "CHỜ FOUNDER QUYẾT" not in (r2.stdout or ""),
           "out2=%r" % (r2.stdout[:300]))

        # ── AC7 — dự án không Telegram: mọi hook thoát sạch
        h.bo_co()
        h.bo_moc_tg()
        h.phien([go_cli(now - 60, "làm tiếp")])
        kq, out, err, _ = h.cong(h.khong_tg)
        r = h.mode(h.khong_tg, "làm tiếp đi")
        r3 = subprocess.run([sys.executable, VDS], input=json.dumps({"transcript_path": h.tr, "cwd": h.khong_tg,
                            "session_id": "ca-thu-7"}), capture_output=True, text=True, env=h.env(h.khong_tg), timeout=60)
        ca("AC7. dự án không Telegram, không cờ: cổng CHO QUA, afk_mode + ve_de_sau_gate không traceback",
           kq == "qua" and "Traceback" not in (err + r.stderr + r3.stderr), (err + r.stderr + r3.stderr)[-300:])

        # ── AC8 — tệp mốc Telegram hỏng / là thư mục / thiếu → không vỡ, ≤ 1 giây, rơi về H2
        h.co(bat, het)
        h.phien([go_cli(bat + 5, "/afk")])
        for ten, tho in (("hỏng JSON", "{không phải json"), ("moc là chữ", '{"moc": "abc"}'), ("rỗng", "")):
            h.bo_moc_tg()
            h.moc_tg("C-HX", 0, tho=tho)
            kq, out, err, giay = h.cong(h.chx)
            ca("AC8. tệp mốc Telegram %s → vẫn CHẶN theo H2, %.2f giây, không traceback" % (ten, giay),
               kq == "chan" and giay <= 1.0 and "Traceback" not in err, "kq=%s giay=%.2f err=%s" % (kq, giay, err[-200:]))
        h.bo_moc_tg()
        os.makedirs(os.path.join(h.afk, "moc-telegram-C-HX.json"))
        kq, out, err, giay = h.cong(h.chx)
        ca("AC8. tệp mốc Telegram là THƯ MỤC → vẫn CHẶN, %.2f giây, không traceback" % giay,
           kq == "chan" and giay <= 1.0 and "Traceback" not in err, err[-200:])
        h.bo_moc_tg()

        # ── loi_khi_vang dùng chung cho các cổng ra lệnh hỏi (O1.6)
        r = h.py(h.chx, "import afk_trang_thai as T\nprint(repr(T.loi_khi_vang(%r, %r)))" % (h.chx, h.tr))
        ca("O1.6a. loi_khi_vang lúc vắng: có chữ CẤM + đường sep_viec.py gui", "CẤM" in r.stdout and "sep_viec.py gui" in r.stdout,
           r.stdout[-300:] + r.stderr[-200:])
        h.bo_co()
        h.phien([go_cli(now - 5, "làm tiếp")])
        r = h.py(h.chx, "import afk_trang_thai as T\nprint(repr(T.loi_khi_vang(%r, %r)))" % (h.chx, h.tr))
        ca("O1.6b. loi_khi_vang lúc có mặt → chuỗi rỗng", r.stdout.strip() == "''", r.stdout + r.stderr[-200:])
        # ── O1.5 — kênh inbox: dự án khai ở <dự án>/.claude/afk-inbox.txt (đứng ở thư mục con) / không khai
        r = h.py(h.tu_khai, "import afk_trang_thai as T\nprint(T.kenh_inbox(%r))" % os.path.join(h.tu_khai, ".claude", "con"))
        ca("O1.5a. dự án tự khai .claude/afk-inbox.txt (cwd thư mục con) → kenh_inbox in đúng lệnh dự án",
           "node tools/hoi-founder.mjs" in r.stdout and "sep_viec" not in r.stdout, r.stdout[-300:] + r.stderr[-200:])
        r = h.py(h.khong_tg, "import afk_trang_thai as T\nprint(T.kenh_inbox(%r))" % h.khong_tg)
        ca("O1.5b. dự án không khai kênh → chỉ ~/.claude/afk/cau-hoi-du-an-khong-tg.md",
           "cau-hoi-du-an-khong-tg.md" in r.stdout and "sep_viec" not in r.stdout, r.stdout[-300:] + r.stderr[-200:])
    finally:
        h.don()

    # ── AC11 — bộ ca cũ vẫn xanh
    for ten, lenh, dau in (("afk_vang_ca_thu", [os.path.join(GOC, "afk_vang_ca_thu.py")], "11/11"),
                           ("afk_trang_thai --ca-thu", [TT, "--ca-thu"], "6/6"),
                           ("ve_de_sau_gate --tu-kiem-luat", [VDS, "--tu-kiem-luat"], None),
                           ("ve_cho_founder --tu-kiem", [os.path.join(GOC, "ve_cho_founder.py"), "--tu-kiem"], None)):
        r = subprocess.run([sys.executable] + lenh, capture_output=True, text=True, timeout=300)
        dong = (r.stdout.strip().splitlines() or [""])[-1]
        ca("AC11. %s xanh (%s)" % (ten, dong[:60]), r.returncode == 0 and (dau is None or dau in r.stdout), r.stdout[-300:])

    print("\n%d/%d ca đúng" % (KQ["tong"] - KQ["sai"], KQ["tong"]))
    return 1 if KQ["sai"] else 0


if __name__ == "__main__":
    sys.exit(main())
