# univ3 — Hướng dẫn

Bộ rule v3 cho vibe coder dùng **Claude CLI + Codex CLI**. Triết lý: siêu gọn, self-contained, harness-agnostic. Nền tảng: luật luôn-nạp giữ cực mỏng (SPINE), phần chuyên biệt lazy-load (skill), thứ "phải luôn đúng" ép bằng hook + git pre-commit.

## Cài vào 1 project

**SSOT repo:** `git@github.com:thanhnt1021/univ3.git` (PRIVATE, tài khoản `thanhnt1021`).

**Cách A — bootstrap từ repo (khuyến nghị, project mới):**
```bash
cd <project>
bash <(curl -fsSL https://raw.githubusercontent.com/thanhnt1021/univ3/main/bootstrap.sh) || \
  bash docs/univ3/bootstrap.sh    # nếu đã có sẵn bootstrap.sh
```
`bootstrap.sh` tự: clone repo vào `docs/univ3/` (SSH→HTTPS fallback) → chạy `install.py --harness all`.

**Cách B — clone tay:**
```bash
cd <project>
gh repo clone thanhnt1021/univ3 docs/univ3         # hoặc: git clone git@github.com:thanhnt1021/univ3.git docs/univ3
rm -rf docs/univ3/.git                               # gỡ .git để nhúng vào project (cache, không nested repo)
python3 docs/univ3/install.py --harness all
```

**Sau khi có `docs/univ3/`** → tạo file rule gốc ở root project:
- `AGENTS.md`: copy từ `docs/univ3/AGENTS.md` (Codex đọc natively) + thêm mục project-specific.
- `CLAUDE.md`: dòng đầu `@AGENTS.md` + vài dòng Claude-only. (`install.py` đã sinh AGENTS.md sẵn.)

`install.py`:
- `--harness claude` → hook `~/.claude/universal-hooks/` + settings.json (đã backup `.bak`) + skill `~/.claude/skills/`.
- `--harness codex` → skill `~/.agents/skills/` + hook `~/.agents/univ3-hooks/` (tùy chọn) + nhắc copy AGENTS.md.
- `--harness all` → cả hai.
- Luôn: sinh `AGENTS.md` + `MANIFEST.txt` + cài git pre-commit (nếu project là git repo).

## Cách hệ vận hành (5 tầng thực thi)
1. **Cưỡng chế**: git `pre-commit` (mọi harness lẫn người) + Claude hook (SessionStart nạp SPINE, PreToolUse chặn thiếu dấu/gate GOAL, Stop chống báo-xong-dối). Codex: AGENTS.md tự nạp + pre-commit.
2. **Skill lazy-load**: chỉ description nằm trong context; body đọc khi trúng tình huống.
3. **Nested memory**: `docs/GOAL.md` + `docs/PROJECT_SUMMARY.md` + `docs/CHANGELOG.md` — harness-agnostic.
4. **Index mỏng**: `SPINE.md` (canonical) → `AGENTS.md` (sinh ra). Sửa SPINE → chạy `scripts/gen_agents_md.py`.
5. **Kỹ thuật prompt**: When/When-NOT, GOOD/BAD, IMPORTANT ít mà đúng chỗ.

## Spine riêng cho project
Muốn luật luôn-nạp riêng: tạo `docs/SESSION_SPINE.md` (NGOÀI `univ3/`). `session_context` ưu tiên file đó; không bị ghi đè khi `sync uni`.

## Cập nhật từ SSOT (pull)
Drift-check nhanh (trong `docs/univ3/`):
```bash
shasum -a 256 -c MANIFEST.txt --quiet && echo "✓ khớp $(cat VERSION)" || echo "⚠️ DRIFT — cần sync"
```
Pull bản mới nhất (lệnh `sync uni` — chi tiết `rules/WORKFLOWS.md` §sync-uni):
```bash
# 1. Clone SSOT vào thư mục tạm
gh repo clone thanhnt1021/univ3 /tmp/univ3-ssot     # cần gh auth tài khoản thanhnt1021
# 2. So manifest — khớp thì thôi
diff docs/univ3/MANIFEST.txt /tmp/univ3-ssot/MANIFEST.txt && echo "đã mới nhất" || echo "có thay đổi"
# 3. Copy về (giữ file project-specific: KHÔNG overwrite CLAUDE.md/AGENTS.md project/GOAL/CHANGELOG;
#    giữ file khai trong docs/univ3/LOCAL_ONLY.txt), rồi cài lại hook/skill:
rsync -a --delete /tmp/univ3-ssot/ docs/univ3/ && python3 docs/univ3/install.py --harness all
rm -rf /tmp/univ3-ssot
```
> Chi tiết chiều PULL (giữ LOCAL_ONLY, không overwrite file project) + chiều PUSH (đẩy rule mới ngược về SSOT): `rules/WORKFLOWS.md` §sync-uni.

**Push rule mới ngược về SSOT** (khi sửa rule ở project): clone `~/PycharmProjects/univ3-ssot` → copy file đã sửa → bump `VERSION` + `bash scripts/gen_manifest.sh` (+ `gen_agents_md.py` nếu sửa SPINE) → commit + push (`gh auth switch --user thanhnt1021`).

## Khác biệt với v2 (`docs/universal_rules/`)
v2 giữ nguyên làm bản đối chiếu. v3 = viết lại gọn: 30 rule → 6 + SPINE; 3 bug hook đã sửa; AGENTS.md canonical (chạy Codex); 3 skill mới + skill self-contained; 1 installer thay 5 bề mặt; đã gỡ dữ liệu cá nhân/project khỏi bộ universal. So sánh đầy đủ: `_meta/ROADMAP.md` + `docs/UNIV3_BLUEPRINT.md`.
