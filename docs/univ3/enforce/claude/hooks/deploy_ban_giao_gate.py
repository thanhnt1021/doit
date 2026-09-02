#!/usr/bin/env python3
"""deploy_ban_giao_gate.py — CỔNG BÀN GIAO CHẶNG ĐẨY (tách deploy khỏi worker thi công).

VÌ SAO CÓ FILE NÀY (đêm 29/08/2026, ba ca thật):
  · W144 dừng 92% — nhãn cuối «Smoke demo + prod, chụp ảnh» -> phần soát sau khi lên web
    KHÔNG AI LÀM -> 4 màn giao diện vỡ lọt tới tay founder.
  · W165 dừng 84% — nhãn cuối «Đăng ký lô deploy, chuẩn bị đẩy» -> 4 việc dữ liệu làm
    xong mà chưa lên web, phải thả con khác đẩy nốt.
  · W175 dừng 92%.
  Cả ba đều chết Ở CHẶNG ĐẨY, không con nào chết giữa lúc thi công.

CÁCH TÁCH (founder: "miễn là đủ việc, đéo thiếu gì của tao"):
  HAI CUỐN SỔ RIÊNG, mỗi cuốn đóng độc lập.
    Sổ 1 — công thi công: `/tmp/claude-bg-progress/<project>/<slug>.progress`.
           Worker thi công dừng ở "build xanh + đã lưu mã + ĐÃ ĐĂNG KÝ VÉ ĐẨY" và ghi
           `100|...` cho CHÍNH PHẦN THI CÔNG. Nó KHÔNG chờ lô deploy chạy xong.
    Sổ 2 — chặng đẩy: `~/.claude/deploy-queue/<project>/pending/*.json` (vé `register`
           của `scripts/deploy-batch.sh`), đóng khi lô chạy xong (vé chuyển sang `done/`
           và `last-green-build` nhảy sha).
  Chết ở chặng đẩy -> vé còn nguyên trong `pending/`, công thi công đã commit vẫn còn.
  Thả lại chỉ cần `bash scripts/deploy-batch.sh run --wait` — KHÔNG làm lại từ đầu.

LỖ DUY NHẤT CÒN LẠI SAU KHI TÁCH — và đó là việc của cổng này:
  worker commit xong rồi CHẾT TRƯỚC KHI `register` (đúng ca W165 ở 84%). Lúc đó
  sổ 1 đóng/đứng, sổ 2 TRỐNG -> mã nằm trong git mà KHÔNG AI BIẾT nó chưa lên web.
  Cổng quét: `git log <last-green-build>..HEAD` có commit đụng file deploy được, mà
  `pending/` rỗng và không có lô nào đang chạy -> RÓT CẢNH BÁO vào ngữ cảnh main.

  · `SubagentStop` -> `additionalContext`: nổi NGAY lượt worker kết thúc.
  · `Stop`         -> `decision: block` khi main sắp nói "đã lên demo/prod/xong" mà mã
                      vẫn mồ côi. Chặn tối đa 2 lần/lượt rồi thả (fail-open).

KHÔNG KÊU OAN (đo bằng chính dữ liệu dự án):
  · commit toàn `docs/` + `*.md` + `reference/` -> không cần đẩy -> im.
  · `pending/` còn vé -> việc đẩy ĐANG trong sổ, có người/lô lo -> im.
  · `ps` thấy `deploy-batch.sh run` -> lô đang chạy -> im.
  · cùng một HEAD đã kêu trong `LAP_LAI_GIAY` giây gần đây -> im (chống lải nhải).

Fail-open tuyệt đối: thiếu git / thiếu `last-green-build` / lỗi bất kỳ -> exit 0.
Tự kiểm: `python3 deploy_ban_giao_gate.py --tu-kiem` (dựng repo giả, chạy cổng thật).
Chạy tay: `python3 deploy_ban_giao_gate.py --kiem` trong thư mục project.
"""
import json
import os
import re
import subprocess
import sys
import time

CLAUDE_HOME = os.environ.get("CLAUDE_HOME", os.path.expanduser("~/.claude"))
DEPLOY_ROOT = os.environ.get("UNIV3_DEPLOY_QUEUE_ROOT",
                             os.path.join(CLAUDE_HOME, "deploy-queue"))
SO_DIR = os.environ.get("UNIV3_BAN_GIAO_SO", os.path.join(CLAUDE_HOME, "worker-cache"))

# Kêu lại cùng một HEAD sau ngần này giây. 1800 = 30 phút: dài hơn MỘT lượt lô đầy đủ
# (đo thật trong chain.log dự án: 5-24 phút) nên không chồng lên lô đang chạy, mà vẫn
# đủ ngắn để mã mồ côi không nằm im cả buổi.
LAP_LAI_GIAY = 1800
MAX_BLOCKS = 2                 # chặn 2 lần/lượt rồi thả, không treo founder
GIOI_HAN_COMMIT = 40           # trần số commit đọc ra, khỏi in cả trang

# Đuôi/thư mục KHÔNG đi lên web -> commit chỉ đụng những chỗ này thì không cần đẩy.
KHONG_CAN_DAY = re.compile(
    r"^(docs/|reference/|e2e/|\.claude/|\.github/|[^/]*\.md$|[^/]*\.txt$)")
RX_MA_W = re.compile(r"\bW\d{1,4}\b")
RX_KHAI_LEN_WEB = re.compile(
    r"(đã\s+lên\s+(demo|prod|web)|đã\s+deploy|deploy\s+xong|đã\s+đẩy\s+lên|"
    r"live\s+trên\s+(demo|prod)|đã\s+lên\s+bản\s+thật)", re.IGNORECASE)


def _chay(args, cwd, timeout=6):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def _goc_repo(cwd):
    out = _chay(["git", "rev-parse", "--show-toplevel"], cwd).strip()
    return out or ""


def _lo_dang_chay():
    """`ps` thấy lô deploy đang chạy -> chặng đẩy có người lo, đừng kêu."""
    out = _chay(["ps", "-eo", "args"], "/", timeout=5)
    for d in out.splitlines():
        if "deploy-batch" in d and (" run" in d or d.rstrip().endswith("run")):
            return True
    return False


def quet(cwd):
    """Trả về dict mô tả mã chờ đẩy, hoặc None nếu LÀNH (không có gì để kêu)."""
    repo = _goc_repo(cwd)
    if not repo:
        return None
    proj = os.path.basename(repo)
    qroot = os.path.join(DEPLOY_ROOT, proj)
    # W194 29/08/2026 — ĐỌC ĐÚNG CUỐN SỔ.
    # BỆNH THẬT: cổng kêu "9 bản lưu chưa lên web" trong khi chúng đã lên từ 08:03, main
    # báo sai với founder. Nguyên nhân: `last-green-build` do `deploy-batch.sh` ghi NGAY
    # SAU KHI BUILD XANH (dòng 394/419) — đó là sổ "khỏi build lại", KHÔNG phải sổ "đã lên
    # web". Đẩy thẳng bằng `deploy-remote.sh promote|<app>` thì sổ đó đứng yên -> kêu oan.
    # Nay `scripts/deploy-remote.sh` ghi `last-deployed` SAU khi đẩy xong và đã đọc lại sha
    # thật trên app (cả ba đường đẩy đều qua relay đó). Ưu tiên sổ mới, thiếu thì lùi về sổ
    # cũ để dự án chưa cập nhật script vẫn chạy y như trước.
    base = ""
    for ten in ("last-deployed", "last-green-build"):
        f = os.path.join(qroot, ten)
        if not os.path.exists(f):
            continue
        try:
            base = open(f, encoding="utf-8").read().strip()
        except OSError:
            base = ""
        if base:
            break
    if not base:
        return None                                   # không có sổ nào -> im
    head = _chay(["git", "rev-parse", "HEAD"], repo).strip()
    if not head or head == base:
        return None
    # base phải là commit CÓ THẬT trong repo, không thì dải vô nghĩa.
    if not _chay(["git", "cat-file", "-t", base], repo).strip() == "commit":
        return None

    raw = _chay(["git", "log", "--format=%h%x09%s", "-n", str(GIOI_HAN_COMMIT),
                 "%s..HEAD" % base], repo)
    commits = [d.split("\t", 1) for d in raw.splitlines() if "\t" in d]
    if not commits:
        return None

    files = [d for d in _chay(["git", "diff", "--name-only", "%s..HEAD" % base],
                              repo).splitlines() if d.strip()]
    if files and all(KHONG_CAN_DAY.match(f) for f in files):
        return None                                   # toàn tài liệu -> không cần đẩy

    pend = []
    pdir = os.path.join(qroot, "pending")
    if os.path.isdir(pdir):
        pend = [f for f in os.listdir(pdir) if f.endswith(".json")]
    if pend:
        return None                                   # vé đang nằm trong sổ -> im
    if _lo_dang_chay():
        return None                                   # lô đang chạy -> im

    ma = []
    for _, subj in commits:
        for m in RX_MA_W.findall(subj):
            if m not in ma:
                ma.append(m)
    return {"repo": repo, "proj": proj, "base": base[:8], "head": head,
            "commits": commits, "ma": ma,
            "files": [f for f in files if not KHONG_CAN_DAY.match(f)]}


def khoi_canh_bao(d):
    dong = ["  · %s  %s" % (h, s) for h, s in d["commits"][:8]]
    if len(d["commits"]) > 8:
        dong.append("  · … và %d commit nữa" % (len(d["commits"]) - 8))
    ai = (" · ".join(d["ma"])) if d["ma"] else "(commit không ghi mã W)"
    return (
        "⛔ CÓ MÃ ĐÃ LƯU MÀ CHƯA LÊN WEB — KHÔNG VÉ NÀO CHỜ ĐẨY\n"
        "   (cổng deploy_ban_giao_gate — hai cuốn sổ: sổ thi công `.progress` ĐÃ đóng, "
        "sổ đẩy `deploy-queue/%s/pending` TRỐNG)\n"
        "  %d commit sau bản đã lên web `%s`, đụng %d tệp chạy thật:\n%s\n"
        "  Của: %s\n\n"
        "CA GỐC 29/08/2026: W165 dừng ở 84%% — nhãn cuối «Đăng ký lô deploy, chuẩn bị đẩy». "
        "Nó chết ĐÚNG khe giữa commit và đăng ký vé, nên 4 việc dữ liệu làm xong mà "
        "không lên web, không ai biết.\n\n"
        "PHẢI làm 1 trong 2, ĐỪNG báo founder là xong:\n"
        "  1. Mở chặng đẩy (công thi công đã có sẵn, KHÔNG phải làm lại):\n"
        "     bash scripts/deploy-batch.sh register --owner=<slug> --smoke=/<route>\n"
        "     bash scripts/deploy-batch.sh run --wait\n"
        "  2. Nếu dải này CỐ Ý không lên web (thử nghiệm, tài liệu) -> nói thẳng lý do "
        "trong báo cáo, đừng im lặng bỏ qua."
        % (d["proj"], len(d["commits"]), d["base"], len(d["files"]),
           "\n".join(dong), ai)
    )


# ----------------------------- sổ chống lải nhải -----------------------------
def _so_p(proj):
    os.makedirs(SO_DIR, exist_ok=True)
    return os.path.join(SO_DIR, "ban-giao-day-%s.json" % proj)


def _doc_so(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}


def _ghi_so(p, d):
    try:
        json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    except OSError:
        pass


def _hook_subagent_stop(cwd):
    d = quet(cwd)
    if not d:
        return 0
    p = _so_p(d["proj"])
    so = _doc_so(p)
    bay_gio = time.time()
    cu = float(so.get(d["head"]) or 0)
    so = {d["head"]: bay_gio}              # chỉ giữ HEAD hiện tại, sổ không phình
    _ghi_so(p, so)
    if cu and (bay_gio - cu) < LAP_LAI_GIAY:
        return 0                           # vừa kêu xong -> im, chống lặp mỗi lượt
    json.dump({"hookSpecificOutput": {"hookEventName": "SubagentStop",
                                      "additionalContext": khoi_canh_bao(d)}},
              sys.stdout, ensure_ascii=False)
    return 0


def _cau_cuoi_cua_main(tp):
    """Lời main vừa viết ở lượt này (đọc ngược transcript tới lượt user gần nhất)."""
    try:
        dong = open(tp, encoding="utf-8").read().splitlines()
    except OSError:
        return ""
    gom = []
    for d in reversed(dong[-400:]):
        try:
            o = json.loads(d)
        except Exception:
            continue
        if o.get("type") == "user":
            break
        if o.get("type") != "assistant":
            continue
        for c in (o.get("message") or {}).get("content") or []:
            if isinstance(c, dict) and c.get("type") == "text":
                gom.append(c.get("text") or "")
    return "\n".join(reversed(gom))


def _hook_stop(data, cwd):
    tp = data.get("transcript_path") or ""
    if not tp or not os.path.exists(tp):
        return 0
    d = quet(cwd)
    if not d:
        return 0
    if not RX_KHAI_LEN_WEB.search(_cau_cuoi_cua_main(tp)):
        return 0                           # main không khai đã lên web -> không chặn
    dem_f = os.path.join(SO_DIR, "ban-giao-day-%s.block" % d["proj"])
    try:
        n = int(open(dem_f, encoding="utf-8").read().strip()) + 1
    except Exception:
        n = 1
    try:
        open(dem_f, "w", encoding="utf-8").write(str(n))
    except OSError:
        pass
    if n > MAX_BLOCKS:
        try:
            os.remove(dem_f)
        except OSError:
            pass
        return 0
    ly_do = ("⛔ ĐANG BÁO 'ĐÃ LÊN WEB' TRONG KHI MÃ VẪN CHƯA ĐẨY.\n\n"
             + khoi_canh_bao(d)
             + "\n\nSỬA: hoặc chạy chặng đẩy cho xong rồi hãy nói, hoặc viết lại câu đó "
               "nói rõ mã đang NẰM CHỜ ĐẨY và ai sẽ đẩy.")
    print(json.dumps({"decision": "block", "reason": ly_do, "suppressOutput": True},
                     ensure_ascii=False))
    return 0


def main():
    if "--tu-kiem" in sys.argv:
        return _tu_kiem()
    if "--kiem" in sys.argv:
        d = quet(os.getcwd())
        print(khoi_canh_bao(d) if d else
              "(sạch) không có mã nào chờ đẩy mà thiếu vé.")
        return 0
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    ev = str(data.get("hook_event_name") or "")
    cwd = str(data.get("cwd") or os.getcwd())
    if ev == "SubagentStop":
        return _hook_subagent_stop(cwd)
    if ev == "Stop":
        return _hook_stop(data, cwd)
    return 0


# ------------------------------- tự kiểm -------------------------------
def _tu_kiem():
    """Dựng repo git thật trong /tmp, diễn lại ĐÚNG ca W165 + ca đẩy trót lọt."""
    import shutil
    import tempfile

    goc = tempfile.mkdtemp(prefix="w187-tu-kiem-")
    repo = os.path.join(goc, "DuAnThu")
    os.makedirs(os.path.join(repo, "src"))
    qroot = os.path.join(goc, "deploy-queue", "DuAnThu")
    os.makedirs(os.path.join(qroot, "pending"))
    moi = dict(os.environ, UNIV3_DEPLOY_QUEUE_ROOT=os.path.join(goc, "deploy-queue"),
               UNIV3_BAN_GIAO_SO=os.path.join(goc, "so"))

    def g(*a):
        subprocess.run(["git"] + list(a), cwd=repo, capture_output=True, text=True)

    g("init", "-q", "-b", "main")
    g("config", "user.email", "thu@vidu.test")
    g("config", "user.name", "Thu W187")
    g("config", "commit.gpgsign", "false")
    open(os.path.join(repo, "src", "a.ts"), "w").write("export const a = 1\n")
    g("add", "src/a.ts")
    g("commit", "-q", "--no-verify", "-m", "nen: ban da len web")
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True,
                          text=True).stdout.strip()
    open(os.path.join(qroot, "last-green-build"), "w").write(base + "\n")

    # (a) worker thi công xong BỐN việc, build xanh, đã lưu mã
    for i in range(1, 5):
        open(os.path.join(repo, "src", "viec%d.ts" % i), "w").write("export const v%d=1\n" % i)
        g("add", "src/viec%d.ts" % i)
        g("commit", "-q", "--no-verify", "-m",
          "feat(W165): viec du lieu Pipeline so %d" % i)

    def goi(ev, extra=None):
        vao = {"hook_event_name": ev, "cwd": repo}
        if extra:
            vao.update(extra)
        r = subprocess.run([sys.executable, os.path.abspath(__file__)],
                           input=json.dumps(vao), capture_output=True, text=True, env=moi)
        return r.stdout.strip()

    print("── CA W165: 4 việc xong, build xanh, ĐÃ LƯU MÃ, chết TRƯỚC khi đăng ký vé ──")
    ra = goi("SubagentStop")
    if ra:
        try:
            print(json.loads(ra)["hookSpecificOutput"]["additionalContext"])
        except Exception:
            print(ra)
    else:
        print("✗ SAI: cổng IM — mã mồ côi lọt lưới")
    con = subprocess.run(["git", "log", "--oneline", "%s..HEAD" % base], cwd=repo,
                         capture_output=True, text=True).stdout.strip()
    print("\n  CÔNG THI CÔNG CÒN NGUYÊN? git log %s..HEAD ->" % base[:8])
    for d in con.splitlines():
        print("    " + d)
    print("  -> %d commit vẫn nằm trong git, KHÔNG mất gì. Thả lại chỉ cần đăng ký vé "
          "+ chạy lô." % len(con.splitlines()))

    print("\n── CA THẢ LẠI: con sau đăng ký vé (chặng đẩy mở) ──")
    json.dump({"owner": "w165", "sha": subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True,
        text=True).stdout.strip(), "smoke": "/pipeline", "ts": int(time.time())},
        open(os.path.join(qroot, "pending", "20260829-090000-w165.json"), "w"))
    ra = goi("SubagentStop")
    print("stdout=%r -> %s" % (ra, "IM, đúng (việc đẩy đã nằm trong sổ)" if not ra
                               else "✗ SAI: kêu oan"))

    print("\n── CA ĐẨY TRÓT LỌT: lô chạy xong, vé sang done, last-green nhảy sha ──")
    os.remove(os.path.join(qroot, "pending", "20260829-090000-w165.json"))
    open(os.path.join(qroot, "last-green-build"), "w").write(
        subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True,
                       text=True).stdout.strip() + "\n")
    ra = goi("SubagentStop")
    print("stdout=%r -> %s" % (ra, "IM, đúng (không cảnh báo thừa)" if not ra
                               else "✗ SAI: kêu oan sau khi đã đẩy"))

    print("\n── CA CHỈ SỬA TÀI LIỆU: commit toàn docs/ -> không cần đẩy ──")
    os.makedirs(os.path.join(repo, "docs"), exist_ok=True)
    open(os.path.join(repo, "docs", "ghi-chu.md"), "w").write("# ghi chú\n")
    g("add", "docs/ghi-chu.md")
    g("commit", "-q", "--no-verify", "-m", "docs(W187): them ghi chu")
    ra = goi("SubagentStop")
    print("stdout=%r -> %s" % (ra, "IM, đúng (tài liệu không lên web)" if not ra
                               else "✗ SAI: kêu oan vì tài liệu"))

    shutil.rmtree(goc, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
