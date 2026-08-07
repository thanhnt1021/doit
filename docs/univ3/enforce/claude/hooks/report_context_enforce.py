#!/usr/bin/env python3
"""
report_context_enforce.py — UserPromptSubmit hook.

Biến rule mềm thành nhắc CỨNG chèn vào context, không phụ thuộc model tự nhớ:

  (A) prompt có "report context" → nhắc chạy git remote/status/log + đọc TODO.
  (B) prompt có ý KIỂM CHỨNG ("check", "đúng không", "kiểm tra", "verify", "thật chưa"...)
      → nhắc RÀ HẾT công cụ verify sẵn có (lệnh local, DB dev/demo/prod qua tunnel, SSH VPS,
      log PM2) TRƯỚC khi kết luận. CẤM nói "không kiểm được" khi chưa thử hết.

Không match → im, exit 0.
"""
import json
import os
import re
import sys

# ── Nhắc theo TỪNG PROJECT (project-aware) ────────────────────────────────────
# Chọn theo `cwd` của session. Mỗi project khai báo report/verify riêng vì hạ
# tầng khác nhau (chichub = VPS + Postgres tunnel; iloveus = Cloudflare Pages +
# D1 + phiếu univ3). Project lạ → dùng DEFAULT (không hardcode file/infra ai cả).

CHICHUB_REPORT = """\
⚠️ LỆNH "report context" — BẮT BUỘC làm TRƯỚC khi trả lời (chạy lệnh, đọc output THẬT, CẤM đoán):
  1) git remote -v && git status -sb && git log --oneline -6
  2) Đọc docs/TODO.md (mục trên cùng) + docs/PROGRESS.md điểm dừng mới nhất.
  3) Nêu rõ: nhánh · track remote nào · commit nào CHƯA push · origin=PROD (lamquynh94/chichub)
     vs staging=DEMO (thanhnt1021/chichub-staging).
"""

CHICHUB_VERIFY = """\
⚠️ CÂU HỎI KIỂM CHỨNG — CẤM kết luận / CẤM nói "không kiểm được" khi CHƯA rà hết công cụ verify:
  - Lệnh local / git.
  - DB dev qua tunnel (localhost:5432 → chichub_dev).
  - DB DEMO/PROD qua tunnel: đổi dbname connection (chichub_demo / chichub) + driver pg.
  - SSH VPS: ssh -p 9494 root@170.205.38.233 (key đã cài) → đọc /root/chichub-demo|.env, log PM2.
  - Log PM2: /root/.pm2/logs/chichub-demo-*.log.
DÙNG công cụ phù hợp → CHẠY → đọc output THẬT → rồi mới trả lời. Đây là rule, không phải tùy chọn.
"""

ILOVEUS_REPORT = """\
⚠️ LỆNH "report context" — BẮT BUỘC làm TRƯỚC khi trả lời (chạy lệnh, đọc output THẬT, CẤM đoán):
  1) git remote -v && git status -sb && git log --oneline -6
  2) Xem PHIẾU đang dở trong docs/ticket/P###.md (trạng thái draft→…→done, phần Discoveries + AC còn treo);
     đối chiếu docs/GOAL.md + docs/CHANGELOG.md. (univ3 KHÔNG dùng TODO.md/PROGRESS.md.)
  3) Nêu rõ: nhánh · track remote nào · commit nào CHƯA push · origin = thanhnt1021/iloveus (auto-deploy Cloudflare Pages).
"""

ILOVEUS_VERIFY = """\
⚠️ CÂU HỎI KIỂM CHỨNG — CẤM kết luận / CẤM nói "không kiểm được" khi CHƯA rà hết công cụ verify:
  - Lệnh local / git.
  - D1 remote: wrangler d1 execute iloveus-db --remote --command "..." (binding DB, id trong wrangler.toml).
  - Live production: curl / Chrome DevTools trên https://iloveus.jst4.fun (nhớ chờ Cloudflare rollout ~1-3 phút).
  - Quyền: npx wrangler whoami · gh auth status (thanhnt1021) trước khi bảo "không có quyền".
DÙNG công cụ phù hợp → CHẠY → đọc output THẬT → rồi mới trả lời. Đây là rule, không phải tùy chọn.
"""

DEFAULT_REPORT = """\
⚠️ LỆNH "report context" — BẮT BUỘC làm TRƯỚC khi trả lời (chạy lệnh, đọc output THẬT, CẤM đoán):
  1) git remote -v && git status -sb && git log --oneline -6
  2) Đọc tài liệu định vị của project (docs/GOAL.md, docs/PROJECT_SUMMARY.md, docs/ticket/*, hoặc TODO/PROGRESS nếu project có).
  3) Nêu rõ: nhánh · track remote nào · commit nào CHƯA push · đâu là PROD vs staging.
  4) Hạ tầng/remote riêng của project → đọc docs/SESSION_SPINE.md (nếu có) thay vì đoán.
"""

DEFAULT_VERIFY = """\
⚠️ CÂU HỎI KIỂM CHỨNG — CẤM kết luận / CẤM nói "không kiểm được" khi CHƯA rà hết công cụ verify sẵn có:
  - Lệnh local / git · DB · SSH · log · endpoint live của project.
  - Lệnh/infra verify RIÊNG của project (DB tunnel, SSH VPS, D1, log): đọc docs/SESSION_SPINE.md nếu có — đó là nguồn, KHÔNG hardcode vào hook chung.
DÙNG công cụ phù hợp → CHẠY → đọc output THẬT → rồi mới trả lời. Đây là rule, không phải tùy chọn.
"""

# (substring khớp trong cwd, report, verify) — xét theo thứ tự, khớp đầu tiên thắng.
PROJECTS = [
    ("iloveus", ILOVEUS_REPORT, ILOVEUS_VERIFY),
    ("chichub", CHICHUB_REPORT, CHICHUB_VERIFY),
]


def pick(cwd: str):
    low = (cwd or "").lower()
    for key, report, verify in PROJECTS:
        if key in low:
            return report, verify
    return DEFAULT_REPORT, DEFAULT_VERIFY


RE_REPORT = re.compile(r"report\s*context|b[aá]o\s*c[aá]o\s*context", re.IGNORECASE)
RE_VERIFY = re.compile(
    r"\bcheck\b|\bverify\b|ki[eể]m\s*tra|ki[eể]m\s*ch[uứ]ng|đúng\s*kh[oô]ng|"
    r"th[aậ]t\s*ch[uư]a|ch[aắ]c\s*ch[uư]a|có\s*ph[aả]i|ph[aả]i\s*kh[oô]ng",
    re.IGNORECASE,
)


def emit(text: str) -> None:
    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}},
            ensure_ascii=False,
        )
    )


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    prompt = str(data.get("prompt", ""))
    cwd = str(data.get("cwd") or os.getcwd())
    report, verify = pick(cwd)
    if RE_REPORT.search(prompt):
        emit(report)
    elif RE_VERIFY.search(prompt):
        emit(verify)
    return 0


if __name__ == "__main__":
    sys.exit(main())
