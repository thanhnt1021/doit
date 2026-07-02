#!/usr/bin/env bash
# Universal Workflow Bootstrap Script
# https://github.com/thanhnt1021/universal-workflow
#
# Usage (from project root):
#   curl -fsSL https://raw.githubusercontent.com/thanhnt1021/universal-workflow/main/bootstrap.sh | bash
#   or: bash bootstrap.sh
#   or: BOOTSTRAP_SSH_KEY=~/.ssh/my_key bash bootstrap.sh

set -e

SSH_KEY="${BOOTSTRAP_SSH_KEY:-$HOME/.ssh/id_rsa}"

echo ""
echo "=== Universal Workflow Bootstrap ==="
echo ""

# Step 1: Clone and copy rules
echo "[1/5] Copying universal rules to docs/universal_rules/..."
mkdir -p docs/universal_rules

CLONE_DIR="/tmp/_uw_$$"

if GIT_SSH_COMMAND="ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
   git clone --quiet git@github.com:thanhnt1021/universal-workflow.git "$CLONE_DIR" 2>/dev/null; then
  echo "✅ Cloned (via SSH)"
else
  echo "   SSH failed, trying HTTPS..."
  if git clone --quiet https://github.com/thanhnt1021/universal-workflow.git "$CLONE_DIR" 2>/dev/null; then
    echo "✅ Cloned (via HTTPS)"
  else
    echo "❌ Clone failed. Check network / SSH key."
    echo "   SSH key used: $SSH_KEY"
    echo "   Override: BOOTSTRAP_SSH_KEY=/path/to/key bash bootstrap.sh"
    exit 1
  fi
fi

# Copy rules (*.md + bootstrap.sh + subdirectories)
cp "$CLONE_DIR"/*.md docs/universal_rules/
cp "$CLONE_DIR"/bootstrap.sh docs/universal_rules/
# VERSION + MANIFEST.txt: dấu vân tay SSOT để check drift (xem WORKFLOWS.md sync uni)
cp "$CLONE_DIR"/VERSION "$CLONE_DIR"/MANIFEST.txt docs/universal_rules/ 2>/dev/null || true
for sub in rules templates skills hooks scripts _meta; do
  [ -d "$CLONE_DIR/$sub" ] && cp -r "$CLONE_DIR/$sub" docs/universal_rules/
done

# Remove uni repo's own README/CLAUDE.md from project's universal_rules (not rule files)
rm -f docs/universal_rules/README.md docs/universal_rules/CLAUDE.md

echo "✅ Rules copied to docs/universal_rules/"

# Step 2: CLAUDE.md
echo "[2/5] Checking CLAUDE.md..."
if [ ! -f CLAUDE.md ]; then
  cat > CLAUDE.md << 'CLAUDEEOF'
# [Tên Project]

## ⚠️ CRITICAL WORKFLOW RULES

1. **`feature: [tên]` workflow bắt buộc:** Tạo branch `feature/tên` NGAY → đọc context → Q&A → chờ user confirm → rồi mới code. KHÔNG nhảy thẳng vào code.
2. **KHÔNG tự ý** `git commit`, `git push`, `git merge`, hay deploy production — chỉ khi user ra lệnh rõ ràng (`full update`, `commit`, `merge main`).
3. **Sau `quick deploy`** → báo cáo kết quả → **DỪNG**, không làm gì thêm. Chờ user feedback.

> Đọc docs/universal_rules/INDEX.md để áp dụng universal workflow rules.

## Overview
[Mô tả ngắn về project]

## Tech Stack
[Liệt kê tech stack]

## What's DONE ✓
- [x] Project scaffolding

## What's TODO
- [ ] ...
CLAUDEEOF
  echo "✅ Created CLAUDE.md (điền thông tin project vào)"
else
  if ! grep -q "docs/universal_rules/INDEX" CLAUDE.md; then
    echo "" >> CLAUDE.md
    echo '> Đọc docs/universal_rules/INDEX.md để áp dụng universal workflow rules.' >> CLAUDE.md
    echo "✅ Added reference line to CLAUDE.md"
  else
    echo "✅ CLAUDE.md already has reference line"
  fi
fi

# Step 3: README.md (project-specific, từ template)
echo "[3/5] Checking README.md..."
if [ ! -f README.md ]; then
  if [ -f docs/universal_rules/templates/README_TEMPLATE.md ]; then
    cp docs/universal_rules/templates/README_TEMPLATE.md README.md
    echo "✅ Created README.md from template (điền thông tin project vào)"
  else
    cat > README.md << 'READMEEOF'
# [Tên Project]

[Mô tả ngắn về project]

## Tech Stack
[Liệt kê tech stack]

## Cài Đặt & Chạy
[Hướng dẫn setup]
READMEEOF
    echo "✅ Created README.md (điền thông tin project vào)"
  fi
else
  echo "✅ README.md already exists"
fi

# Step 4: docs/GOAL.md (project-specific, từ GOAL_TEMPLATE.md)
echo "[4/5] Checking docs/GOAL.md..."
mkdir -p docs
if [ ! -f docs/GOAL.md ]; then
  if [ -f docs/universal_rules/templates/GOAL_TEMPLATE.md ]; then
    cp docs/universal_rules/templates/GOAL_TEMPLATE.md docs/GOAL.md
    echo "✅ Created docs/GOAL.md from template (điền mục tiêu project vào)"
  else
    cat > docs/GOAL.md << 'GOALEOF'
# GOAL

## Mục tiêu cuối cùng
[Viết 1-2 câu rõ ràng]

## Thành công trông như thế nào
- [Tiêu chí 1]

## KHÔNG phải mục tiêu
- [Thứ để sau]

## Milestones
- [ ] Milestone 1

## Hiện tại đang ở đâu
[Trạng thái hiện tại]
GOALEOF
    echo "✅ Created docs/GOAL.md (điền mục tiêu project vào)"
  fi
else
  echo "✅ docs/GOAL.md already exists"
fi

# Step 5: Cleanup
echo "[5/5] Cleanup..."
CLEANED=0
if [ -f "BOOTSTRAP.md" ] && [ -f "docs/universal_rules/BOOTSTRAP.md" ]; then
  rm -f BOOTSTRAP.md
  echo "✅ Removed BOOTSTRAP.md from project root"
  CLEANED=1
fi
if [ -f "GOAL_TEMPLATE.md" ]; then
  rm -f GOAL_TEMPLATE.md
  echo "✅ Removed GOAL_TEMPLATE.md from project root"
  CLEANED=1
fi
if [ -f "README_TEMPLATE.md" ]; then
  rm -f README_TEMPLATE.md
  echo "✅ Removed README_TEMPLATE.md from project root"
  CLEANED=1
fi
[ $CLEANED -eq 0 ] && echo "✅ No cleanup needed"

rm -rf "$CLONE_DIR"

echo ""
echo "=== Bootstrap complete! ==="
echo ""
echo "Files created/updated:"
echo "  docs/universal_rules/  — workflow rules"
echo "  CLAUDE.md              — project config for Claude Code"
echo "  README.md              — project README"
echo "  docs/GOAL.md           — project goals & milestones"
echo ""
echo "Next: open Claude Code in this project and run:"
echo "  check requirements"
echo ""
