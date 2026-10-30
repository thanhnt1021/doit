#!/usr/bin/env python3
"""Cổng chung: chặn BÍ MẬT + CHỮ KHÁCH THẬT trước khi lưu (commit) và trước khi đẩy (push).

WHY (univ3, Task-28102026-02): 28/10/2026 một lần lưu ChicHub chép nguyên tên khách từ
personalization vào chú thích + ca thử; thợ sau phải thay bằng tên giả, nhưng bản có tên
khách đã nằm trong lịch sử và lên máy chủ deploy. Anh Thành: «đéo có cơ chế tách ra để auto
đẩy à lần lồn nào cũng hỏi». Cổng này là cơ chế đó: quét tất định -> sạch thì máy TỰ đẩy đủ
mọi remote, không hỏi chủ nhà; bẩn thì chặn, chỉ đúng tệp:dòng, KHÔNG in chữ khách.

Dự án KHÔNG khai cấu hình -> cổng chỉ quét bí mật (token, khoá riêng, chuỗi kết nối có
mật khẩu). Dự án khai `.pii-gate.json` (hoặc --cau-hinh <tệp>) -> quét thêm chữ khách:
    {
      "cache": "scripts/kiem-ten-khach/.cache-ten.txt",   # dấu băm chữ khách (gitignore)
      "lam_moi": "node scripts/kiem-ten-khach/lam-moi.mjs", # lệnh làm mới cache
      "lam_moi_sau_gio": 24,                                # cache cũ hơn -> chạy lam_moi
      "remotes": ["origin", "staging"],                     # --day đẩy đủ các remote này
      "nhanh": "main",
      "bo_qua": ["pnpm-lock.yaml"]                          # glob tệp không quét chữ khách
    }
Khuôn cache (do lệnh lam_moi của dự án sinh): dòng `#muoi=<hex>`, rồi mỗi dòng
`P <băm>` (cụm: họ tên, email `email:<thư>`, dòng địa chỉ) hoặc `T <băm>` (từ lẻ hiếm).
băm = sha256(muoi + "\\0" + chữ đã chuẩn hoá)[:20]; chuẩn hoá = NFKD, bỏ dấu, chữ thường,
bỏ dấu nháy, tách [a-z0-9]+ — lệnh lam_moi PHẢI chuẩn hoá y hệt.

Dùng:
    pii_commit_gate.py [--cau-hinh F]                 # pre-commit: quét phần THÊM của bản sắp lưu
    pii_commit_gate.py --khoang A..B [--cau-hinh F]   # quét từng lần lưu trong đoạn (lịch sử)
    pii_commit_gate.py --day [--cau-hinh F]           # quét đoạn chưa đẩy -> sạch thì đẩy đủ remote
Mã thoát: 0 sạch · 1 chặn · 2 cấu hình/lệnh git lỗi.
Trúng oan (chữ chung, không phải chữ khách): thêm chữ đó vào danh sách cho qua của dự án
(ChicHub: scripts/kiem-ten-khach/cho-qua.txt) rồi chạy lại lệnh lam_moi. CẤM --no-verify.
Cổng HỎNG thì CHẶN (fail-closed): lọt chữ khách/bí mật ra kho là việc không đảo ngược được.
"""
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

MAX_BYTES = 2_000_000

SECRET_PATTERNS = [
    ("token bot Telegram", re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b")),
    ("khoá riêng (PRIVATE KEY)", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "chuỗi kết nối có mật khẩu",
        re.compile(
            r"\b(postgres|postgresql|mysql|mongodb\+srv|mongodb|redis|amqp)://"
            r"[^\s:/@]+:[^\s@/]{3,}@",
            re.IGNORECASE,
        ),
    ),
    ("khoá truy cập AWS", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("khoá API Google", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("token GitHub", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("khoá API Anthropic/OpenAI", re.compile(r"\bsk-(ant|proj|live)?-?[A-Za-z0-9_-]{40,}\b")),
    ("khoá bí mật Slack", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
]
PLACEHOLDER = re.compile(
    r"(your[_-]|example|sample|placeholder|dummy|redacted|<[^>]*>|"
    r"xxxx|aaaa{4,}|changeme|fake|test[_-]?token|\.\.\.|"
    r":(pass|passwd|password|mat[_-]?khau|secret|123456)@)",
    re.IGNORECASE,
)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LOAI = {"P": "họ tên / email / địa chỉ khách", "T": "từ hiếm lấy từ tên hoặc personalization khách"}


def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def git(*args):
    r = sh(["git", *args])
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()[:300]}")
    return r.stdout


def tach_tu(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.category(c).startswith("M"))
    s = re.sub(r"['’`]", "", s.lower())
    return re.findall(r"[a-z0-9]+", s)


def che(x):
    """In ra dạng che: chữ cái đầu + số ký tự — đủ để người lưu tìm ra, không lộ tên."""
    return f"{x[:1]}…({len(x)} ký tự)"


class ChuKhach:
    def __init__(self, root, cfg):
        self.ok = False
        self.ghi_chu = ""
        if not cfg:
            return
        self.bo_qua = cfg.get("bo_qua", [])
        root = cfg.get("_goc", root)
        cache = os.path.join(root, cfg.get("cache", ""))
        han = float(cfg.get("lam_moi_sau_gio", 24)) * 3600
        cu = (not os.path.exists(cache)) or (time.time() - os.path.getmtime(cache) > han)
        if cu and cfg.get("lam_moi"):
            try:
                r = subprocess.run(cfg["lam_moi"], shell=True, cwd=root, capture_output=True,
                                   text=True, timeout=45)
                if r.returncode != 0:
                    self.ghi_chu = "không làm mới được danh sách chữ khách (cầu DB tắt?) — dùng bản cũ"
            except subprocess.TimeoutExpired:
                self.ghi_chu = "làm mới danh sách chữ khách quá 45 giây — dùng bản cũ"
        if not os.path.exists(cache):
            # Máy chưa từng có cache (máy mới, chưa có cầu DB): không có gì để so -> báo, cho qua.
            self.ghi_chu = "CHƯA có danh sách chữ khách trên máy này — chỉ quét bí mật"
            return
        self.muoi = None
        self.P, self.T = set(), set()
        with open(cache, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("#muoi="):
                    self.muoi = line[6:]
                elif line[:2] == "P ":
                    self.P.add(line[2:])
                elif line[:2] == "T ":
                    self.T.add(line[2:])
        if not self.muoi:
            raise RuntimeError(f"cache {cache} thiếu dòng #muoi=")
        self.ok = True

    def bam(self, x):
        return hashlib.sha256((self.muoi + "\0" + x).encode("utf-8")).hexdigest()[:20]

    def bo_qua_tep(self, path):
        return any(fnmatch.fnmatch(path, g) for g in self.bo_qua)

    def soi_dong(self, line):
        """Trả về [(loại, chữ)] trúng trong một dòng."""
        if not self.ok:
            return []
        hits = []
        for m in EMAIL.finditer(line):
            e = m.group().lower()
            if self.bam("email:" + e) in self.P:
                hits.append(("P", e))
        tu = tach_tu(line)
        for i in range(len(tu)):
            for n in range(6, 1, -1):  # cụm dài trước: họ tên + địa chỉ
                if i + n <= len(tu):
                    g = " ".join(tu[i:i + n])
                    if self.bam(g) in self.P:
                        hits.append(("P", g))
                        break
        for w in set(tu):
            if len(w) >= 4 and self.bam(w) in self.T:
                hits.append(("T", w))
        return hits


def soi_bi_mat(text):
    out = []
    for label, pat in SECRET_PATTERNS:
        for m in pat.finditer(text):
            if PLACEHOLDER.search(m.group()):
                continue
            out.append((text[: m.start()].count("\n") + 1, label))
            break
    return out


def doc_cau_hinh(root, path):
    path = path or os.environ.get("PII_GATE_CONFIG") or ".pii-gate.json"
    full = path if os.path.isabs(path) else os.path.join(root, path)
    if not os.path.exists(full):
        return None
    with open(full, encoding="utf-8") as fh:
        cfg = json.load(fh)
    # Đường dẫn trong cấu hình tính từ gốc kho CHỨA tệp cấu hình — để quét được cả bản sao
    # không có cây làm việc (công cụ viết lại lịch sử chạy cổng trong bản sao ở /tmp).
    r = sh(["git", "-C", os.path.dirname(full), "rev-parse", "--show-toplevel"])
    cfg["_goc"] = r.stdout.strip() if r.returncode == 0 else root
    return cfg


def them_tu_diff(diff_text):
    """Duyệt diff -U0 -> (tệp, số dòng mới, nội dung dòng thêm)."""
    path, lineno = None, 0
    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            p = raw[4:]
            path = None if p == "/dev/null" else (p[2:] if p.startswith("b/") else p)
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            lineno = int(m.group(1)) if m else 0
        elif raw.startswith("+") and path:
            yield path, lineno, raw[1:]
            lineno += 1
        elif raw.startswith("Binary files"):
            continue


def quet_diff(ck, diff_text):
    hits = []
    for path, ln, line in them_tu_diff(diff_text):
        if ck.ok and not ck.bo_qua_tep(path):
            for loai, x in ck.soi_dong(line):
                hits.append(f"{path}:{ln}  — {LOAI[loai]} «{che(x)}»")
    return hits


def che_do_commit(root, ck):
    hits = []
    files = [f for f in git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines() if f]
    for f in files:
        r = subprocess.run(["git", "show", f":{f}"], capture_output=True)
        raw = r.stdout[:MAX_BYTES]
        if r.returncode != 0 or b"\0" in raw[:8000]:
            continue
        for ln, label in soi_bi_mat(raw.decode("utf-8", errors="replace")):
            hits.append(f"{f}:{ln}  — {label} (giá trị KHÔNG in ra đây)")
    if ck.ok:
        hits += quet_diff(ck, git("diff", "--cached", "-U0", "--no-color", "--no-ext-diff",
                                  "--diff-filter=ACMR"))
    return hits


def quet_khoang(ck, rev_args):
    """Quét từng lần lưu -> {sha: [hit]}."""
    out = {}
    for sha in git("rev-list", "--reverse", *rev_args).split():
        d = git("show", "--format=", "-U0", "--no-color", "--no-ext-diff", "--diff-filter=ACMR", sha)
        hits = quet_diff(ck, d)
        for path, ln, line in them_tu_diff(d):
            for l2, label in soi_bi_mat(line):
                hits.append(f"{path}:{ln}  — {label}")
        if hits:
            out[sha] = hits
    return out


def in_khoang(res):
    for sha, hits in res.items():
        tieu_de = git("log", "-1", "--format=%h %s", sha).strip()[:110]
        print(f"  ✗ {tieu_de}", file=sys.stderr)
        for h in hits[:15]:
            print("      " + h, file=sys.stderr)
        if len(hits) > 15:
            print(f"      … thêm {len(hits) - 15} chỗ", file=sys.stderr)


def che_do_day(ck, cfg):
    remotes = (cfg or {}).get("remotes") or [r for r in git("remote").split() if r]
    nhanh = (cfg or {}).get("nhanh") or "main"
    for r in remotes:
        sh(["git", "fetch", "-q", r, nhanh])
    have = [f"{r}/{nhanh}" for r in remotes if sh(["git", "rev-parse", "-q", "--verify", f"{r}/{nhanh}"]).returncode == 0]
    res = quet_khoang(ck, ["HEAD", "--not", *have])
    if res:
        print("❌ KHÔNG ĐẨY — đoạn chưa đẩy có chữ khách/bí mật:", file=sys.stderr)
        in_khoang(res)
        print("\nXoá khỏi lịch sử chưa đẩy rồi đẩy lại (kho có công cụ viết lại lịch sử thì dùng nó,"
              "\nmặc định: bash ~/.claude/universal-hooks/viet_lai_lich_su.sh --thay <tệp luật>).", file=sys.stderr)
        return 1
    loi = 0
    for r in remotes:
        p = sh(["git", "push", r, f"HEAD:refs/heads/{nhanh}"])
        if p.returncode != 0:
            print(f"❌ đẩy {r} lỗi: {p.stderr.strip()[-400:]}", file=sys.stderr)
            loi = 1
            continue
        sh(["git", "fetch", "-q", r, nhanh])
        lr = git("rev-list", "--left-right", "--count", f"{r}/{nhanh}...HEAD").split()
        print(f"✓ {r}/{nhanh}: lệch {lr[0]} {lr[1]}")
        if lr != ["0", "0"]:
            loi = 1
    return loi


def main(argv):
    cfg_path, khoang, day = None, None, False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--cau-hinh":
            cfg_path = argv[i + 1]; i += 1
        elif a == "--khoang":
            khoang = argv[i + 1]; i += 1
        elif a == "--day":
            day = True
        else:
            print(f"tham số lạ: {a}", file=sys.stderr)
            return 2
        i += 1
    root = git("rev-parse", "--show-toplevel").strip()
    os.chdir(root)
    cfg = doc_cau_hinh(root, cfg_path)
    ck = ChuKhach(root, cfg)
    if ck.ghi_chu:
        print(f"⚠ cổng chữ khách: {ck.ghi_chu}", file=sys.stderr)

    if day:
        return che_do_day(ck, cfg)
    if khoang:
        res = quet_khoang(ck, [khoang])
        if res:
            print(f"❌ {len(res)} lần lưu trong {khoang} có chữ khách/bí mật:", file=sys.stderr)
            in_khoang(res)
            return 1
        print(f"✓ {khoang}: sạch")
        return 0

    hits = che_do_commit(root, ck)
    if hits:
        print("❌ CHẶN COMMIT — phần sắp lưu có bí mật hoặc chữ khách thật:", file=sys.stderr)
        for h in hits[:30]:
            print("    " + h, file=sys.stderr)
        print("\nThay chữ khách bằng tên giả (vd «ROGER'S», «Max»), gỡ bí mật, rồi lưu lại."
              "\nTừ trúng oan (địa danh, chữ kỹ thuật) -> thêm vào tệp cho-qua của dự án rồi chạy lại"
              "\nlệnh lam_moi trong cấu hình. Cấm --no-verify (luật univ3 rules/GIT.md).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:  # hỏng thì CHẶN
        print(f"❌ Cổng chữ khách/bí mật lỗi: {e} — chặn cho an toàn.", file=sys.stderr)
        sys.exit(2)
