#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w88_ca_thu.py — ĐƯỜNG TIÊU SỐ THỨ BA: `worker_board.dong_bo_so` cấp số cho tệp mốc MỒ CÔI.

CA THẬT 14/09/2026 (sổ `~/.claude/worker-counter/EtsyFulfillChichub.map`): trong ba giây
19:52:47→19:52:49 sổ đẻ 17 dòng W66→W82, slug đúng bằng TÊN TỆP mốc (`w08-va-he-thong-worker`,
`w47-cong-duyet-chi-vai-seller`…) của những thợ đã chết từ 13:07–16:49, mô tả là chính slug
viết rời ra (dấu vết của `ten_sach(mo_ta rỗng)`) — tức không agent nào còn sống để khai tên.
Founder: *"sao đang 48 49 lại 65??"*.

BA CA (chạy trong hộp cát, KHÔNG đụng sổ thật):
  A · tệp mốc mồ côi (không agent nào) -> bộ đếm KHÔNG được nhảy.
  B · thợ THẬT đang sống, chưa có số -> vẫn PHẢI được cấp số (chống vá quá tay).
  C · chạy bảng hai lượt liên tiếp -> số không nhảy thêm lượt nào (lũy đẳng).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time

HOOKS = os.path.dirname(os.path.abspath(__file__))
HOP = "/tmp/w88-hop-cat"
CWD = os.path.join(HOP, "du-an-gia")
SCOPE = "DuAnW88"
_loi = [0]


def ghi(ten, dat, chi_tiet=""):
    print(("  ✅ " if dat else "  ❌ ") + ten + (" — " + chi_tiet if chi_tiet else ""))
    if not dat:
        _loi[0] += 1


def moi_truong():
    return dict(os.environ,
                UNIV3_PROGRESS_ROOT=os.path.join(HOP, "progress"),
                UNIV3_PROJECTS_ROOT=os.path.join(HOP, "projects"),
                UNIV3_WQUEUE_ROOT=os.path.join(HOP, "worker-queue"),
                WSEQ_ROOT=os.path.join(HOP, "worker-counter"),
                UNIV3_SCOPE=SCOPE,
                CLAUDE_PROJECT_DIR=CWD)


def dung_hop():
    shutil.rmtree(HOP, ignore_errors=True)
    for d in ("progress/" + SCOPE, "projects", "worker-counter", "worker-queue", "du-an-gia"):
        os.makedirs(os.path.join(HOP, d), exist_ok=True)


def wseq(*tham_so):
    r = subprocess.run(["bash", os.path.join(HOOKS, "wseq.sh")] + list(tham_so),
                       env=dict(moi_truong(), WSEQ_PROJECT=SCOPE),
                       capture_output=True, text=True)
    return r.stdout.strip()


def bo_dem():
    """Số cuối cùng bộ đếm đã cấp (dòng 2 của tệp `.seq`). 0 khi chưa cấp số nào."""
    try:
        with open(os.path.join(HOP, "worker-counter", SCOPE + ".seq"), encoding="utf-8") as fh:
            return int(fh.read().splitlines()[1])
    except (OSError, IndexError, ValueError):
        return 0


def so_dong_so():
    try:
        with open(os.path.join(HOP, "worker-counter", SCOPE + ".map"), encoding="utf-8") as fh:
            return [l.rstrip("\n").split("\x1f")[:2] for l in fh if l.strip()]
    except OSError:
        return []


def tep_moc(slug, noi_dung, tuoi_phut):
    p = os.path.join(HOP, "progress", SCOPE, slug + ".progress")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(noi_dung + "\n")
    t = time.time() - tuoi_phut * 60
    os.utime(p, (t, t))
    return p


def agent_song(session_id, agent_id, mo_ta):
    """Agent CÒN SỐNG: transcript cha không có `<task-notification>`, transcript con chưa
    `end_turn` (bản ghi cuối là một lượt gọi công cụ) -> `quet_agent` xếp vào nhóm sống."""
    slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(CWD))
    goc = os.path.join(HOP, "projects", slug)
    os.makedirs(os.path.join(goc, session_id, "subagents"), exist_ok=True)
    with open(os.path.join(goc, session_id + ".jsonl"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "assistant", "message": {
            "role": "assistant", "content": [{"type": "text", "text": "đang điều phối"}]}}) + "\n")
    jl = os.path.join(goc, session_id, "subagents", "agent-%s.jsonl" % agent_id)
    with open(jl, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "assistant", "message": {
            "role": "assistant", "stop_reason": "tool_use",
            "content": [{"type": "tool_use", "name": "Bash", "id": "t1",
                         "input": {"command": "grep -rn x ."}}]}}, ensure_ascii=False) + "\n")
    with open(jl[:-len(".jsonl")] + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump({"description": mo_ta}, fh, ensure_ascii=False)
    return jl


def chay_bang():
    r = subprocess.run([sys.executable, os.path.join(HOOKS, "worker_board.py"), "--day-du"],
                       env=moi_truong(), cwd=CWD, capture_output=True, text=True)
    return r.stdout + r.stderr


def ca_d():
    """CA D — cỗ máy bơm tệp mồ côi: `worker_state.dong_bo_moc` kéo ngược bản bền về.

    ĐO THẬT 14/09/2026 trên máy founder: thư mục sống còn 2 tệp, chạy MỘT lượt bảng ra lại
    25 — `don_dep` dời tệp sang `done/` bên `/tmp`, bản gốc bên `~/.claude/bg-progress` vẫn
    nằm đó nên lượt sau chép ngược về. Không bịt chỗ này thì dòng mồ côi tái sinh vô hạn và
    đường tiêu số luôn có mồi.
    """
    dung_hop()
    ben = os.path.join(HOP, "ben")
    tam = os.path.join(HOP, "progress", SCOPE)
    os.makedirs(os.path.join(ben, SCOPE), exist_ok=True)
    os.makedirs(os.path.join(tam, "done"), exist_ok=True)
    os.environ["UNIV3_PROGRESS_ROOT"] = os.path.join(HOP, "progress")
    os.environ["UNIV3_PROGRESS_BEN"] = ben
    for m in [x for x in list(sys.modules) if x.startswith("worker_state")]:
        del sys.modules[m]
    sys.path.insert(0, HOOKS)
    import worker_state as WS
    WS.PROGRESS_ROOT = os.path.join(HOP, "progress")

    # D1 — việc ĐÃ ĐÓNG (có tệp trong done/): bản bền KHÔNG được kéo về.
    with open(os.path.join(ben, SCOPE, "w08-viec-da-xong.progress"), "w", encoding="utf-8") as fh:
        fh.write("100|xong từ chiều\n")
    with open(os.path.join(tam, "done", "2026-09-14-1323__w08-viec-da-xong__xong.progress"),
              "w", encoding="utf-8") as fh:
        fh.write("100|xong từ chiều\n")
    WS.dong_bo_moc(SCOPE)
    ghi("ca D1 — việc đã đóng KHÔNG bị kéo ngược về thư mục sống",
        not os.path.exists(os.path.join(tam, "w08-viec-da-xong.progress")),
        "còn: %s" % sorted(x for x in os.listdir(tam) if x.endswith(".progress")))

    # D2 (ĐỐI CHỨNG) — việc CHƯA đóng: mốc vẫn phải được kéo về sau lần tắt máy.
    with open(os.path.join(ben, SCOPE, "w09-viec-dang-do.progress"), "w", encoding="utf-8") as fh:
        fh.write("60|đang dở\n")
    WS.dong_bo_moc(SCOPE)
    ghi("ca D2 — việc chưa đóng VẪN được kéo về (không vá quá tay)",
        os.path.exists(os.path.join(tam, "w09-viec-dang-do.progress")),
        "còn: %s" % sorted(x for x in os.listdir(tam) if x.endswith(".progress")))
    os.environ.pop("UNIV3_PROGRESS_BEN", None)


def main():
    print("=" * 90)
    print("W88 — ba ca thử đường tiêu số thứ ba (hộp cát %s)" % HOP)
    print("=" * 90)

    # ── CA A ───────────────────────────────────────────────────────────────────
    dung_hop()
    wseq("next", "viec-that-dang-chay", "W01 việc thật đang chạy")
    truoc = bo_dem()
    # Mồ côi = thợ đã chết, KHÔNG còn agent nào; tệp mới ghi 5 phút trước nên `don_dep`
    # còn bị CỔNG 1 (MOI_GHI_PHUT=20) cấm dọn — đúng khe mà bản cũ tiêu số.
    for s, nn in (("w08-va-he-thong-worker", "100|Xong việc cũ"),
                  ("w21-ha-khong-thay-the", "70|đang dở"),
                  ("w47-cong-duyet-chi-vai-seller", "40|đang dở")):
        tep_moc(s, nn, 5)
    ra_a = chay_bang()
    sau = bo_dem()
    print("  · CA A bộ đếm: trước W%02d → sau W%02d" % (truoc, sau))
    print("  · sổ sau ca A: %s" % so_dong_so())
    ghi("ca A — tệp mốc mồ côi KHÔNG làm bộ đếm nhảy", sau == truoc,
        "trước W%02d sau W%02d" % (truoc, sau))
    ghi("ca A — sổ không đẻ dòng mang tên tệp mốc",
        not [x for x in so_dong_so() if re.match(r"^w\d+-", x[1])],
        str([x[1] for x in so_dong_so()]))

    # ── CA B ───────────────────────────────────────────────────────────────────
    dung_hop()
    wseq("next", "viec-that-dang-chay", "W01 việc thật đang chạy")
    truoc_b = bo_dem()
    agent_song("phien-1", "aaa111bbb222", "Việc sống chưa có số")
    tep_moc("viec-song-chua-co-so", "30|đang cày", 1)
    ra_b = chay_bang()
    sau_b = bo_dem()
    print("  · CA B bộ đếm: trước W%02d → sau W%02d" % (truoc_b, sau_b))
    print("  · sổ sau ca B: %s" % so_dong_so())
    ghi("ca B — thợ SỐNG chưa có số vẫn được cấp số", sau_b == truoc_b + 1,
        "trước W%02d sau W%02d" % (truoc_b, sau_b))

    # ── CA C ───────────────────────────────────────────────────────────────────
    lan1 = bo_dem()
    chay_bang()
    lan2 = bo_dem()
    chay_bang()
    lan3 = bo_dem()
    print("  · CA C bộ đếm ba lượt: W%02d → W%02d → W%02d" % (lan1, lan2, lan3))
    ghi("ca C — chạy lại bảng không tiêu thêm số", lan1 == lan2 == lan3,
        "W%02d/W%02d/W%02d" % (lan1, lan2, lan3))

    ca_d()

    print("-" * 90)
    print("KẾT: %s" % ("ĐẠT HẾT" if not _loi[0] else "%d ca HỎNG" % _loi[0]))
    shutil.rmtree(HOP, ignore_errors=True)
    return 1 if _loi[0] else 0


if __name__ == "__main__":
    sys.exit(main())
