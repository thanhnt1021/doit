# ============================================================
# TMUX AUTO MENU + ALIASES
# Sourced from ~/.bashrc
# ============================================================

# Auto tmux menu on SSH login
if [ -n "$SSH_CONNECTION" ] && [ -z "$TMUX" ] && command -v tmux &>/dev/null; then
  echo ""
  echo "╔═══════════════════════════════════════╗"
  echo "║          TMUX SESSION MENU            ║"
  echo "║  Gõ lệnh rồi bấm Enter để thực hiện  ║"
  echo "╠═══════════════════════════════════════╣"
  sessions=$(tmux ls 2>/dev/null)
  if [ -n "$sessions" ]; then
    echo "║ Sessions đang chạy:                  ║"
    echo "$sessions" | while IFS= read -r line; do
      printf "║   %-35s ║\n" "$line"
    done
  else
    echo "║   (chưa có session nào)              ║"
  fi
  echo "╠═══════════════════════════════════════╣"
  echo "║ n + Enter = Tạo session mới          ║"
  echo "║ a + Enter = Vào lại session cũ        ║"
  echo "║ k + Enter = Kill 1 session            ║"
  echo "║ K + Enter = Kill TẤT CẢ sessions     ║"
  echo "║ s + Enter = Bỏ qua, vào shell thường ║"
  echo "║ ? + Enter = Xem hướng dẫn đầy đủ     ║"
  echo "║                                       ║"
  echo "║ Hoặc gõ thẳng tên session + Enter     ║"
  echo "║ để vào luôn (VD: claude-main)         ║"
  echo "╚═══════════════════════════════════════╝"
  echo ""
  read -p "Nhập lệnh > " choice
  case "$choice" in
    n)
      read -p "Đặt tên session: " sname
      tmux new -s "${sname:-default}" || true
      ;;
    a)
      read -p "Nhập tên/số session muốn vào: " sid
      tmux attach -t "$sid" || true
      ;;
    k)
      read -p "Nhập tên/số session muốn kill: " kid
      if tmux has-session -t "$kid" 2>/dev/null; then
        tmux send-keys -t "$kid" "/exit" Enter 2>/dev/null
        sleep 2
        tmux send-keys -t "$kid" "exit" Enter 2>/dev/null
        sleep 1
        tmux kill-session -t "$kid" 2>/dev/null
        echo "✅ Đã exit Claude + kill session: $kid"
      else
        echo "❌ Không tìm thấy session: $kid"
      fi
      ;;
    K)
      read -p "Kill TẤT CẢ sessions? Gõ y + Enter để xác nhận: " confirm
      if [ "$confirm" = "y" ]; then
        for sess in $(tmux ls -F '#{session_name}' 2>/dev/null); do
          tmux send-keys -t "$sess" "/exit" Enter 2>/dev/null
        done
        sleep 3
        tmux kill-server 2>/dev/null
        echo "✅ Đã exit Claude + kill tất cả sessions"
      else
        echo "Đã huỷ."
      fi
      ;;
    s) ;;
    "?")
      echo ""
      echo "══════════ HƯỚNG DẪN TMUX ══════════"
      echo ""
      echo "KHI ĐANG Ở TRONG TMUX SESSION:"
      echo "  Thoát tạm (session vẫn chạy ngầm):"
      echo "    Cách 1: Gõ tmux detach + Enter"
      echo "    Cách 2: Ctrl+B rồi D (Mac/PC)"
      echo "    Trong Claude Code: !tmux detach"
      echo ""
      echo "  Tạo thêm window trong session:"
      echo "    Cách 1: Gõ tmux new-window + Enter"
      echo "    Cách 2: Ctrl+B rồi C (Mac/PC)"
      echo ""
      echo "  Chuyển window:"
      echo "    tmux select-window -t 0 + Enter"
      echo "    Hoặc Ctrl+B rồi 0/1/2 (Mac/PC)"
      echo ""
      echo "  Đổi tên session:"
      echo "    tmux rename-session <tên mới> + Enter"
      echo ""
      echo "  Đóng window hiện tại:"
      echo "    Gõ exit + Enter"
      echo "    (hết window = session tự kill)"
      echo ""
      echo "KHI Ở NGOÀI TMUX (shell thường):"
      echo "  tmux ls              = Xem sessions"
      echo "  tmux new -s <tên>    = Tạo session"
      echo "  tmux attach -t <tên> = Vào lại session"
      echo "  tmux kill-session -t <tên> = Kill"
      echo "  tmux kill-server     = Kill tất cả"
      echo ""
      echo "LƯU Ý VỀ TÀI NGUYÊN:"
      echo "  - Tmux rất nhẹ, chỉ tốn vài MB RAM"
      echo "  - Claude Code idle ~200-500MB RAM"
      echo "  - Kill session (k/K) tự /exit Claude"
      echo "  - Không cần kill nếu muốn resume sau"
      echo ""
      echo "Bấm Enter để quay lại menu..."
      read
      exec bash --login
      ;;
    *)
      tmux attach -t "$choice" 2>/dev/null || tmux new -s "$choice" || true
      ;;
  esac
fi

# Quick tmux aliases
alias t="tmux ls 2>/dev/null || echo \"Không có session nào\"; echo \"─────────────────\"; echo \"Gõ: a <tên> = attach | n <tên> = tạo mới | k <tên> = kill\""
alias a="tmux attach -t"
alias k="tmux kill-session -t"
alias d="tmux detach"

# Menu tmux đầy đủ (gõ m trong shell)
m() {
  echo ""
  echo "╔═══════════════════════════════════════╗"
  echo "║          TMUX SESSION MENU            ║"
  echo "║  Gõ lệnh rồi bấm Enter để thực hiện  ║"
  echo "╠═══════════════════════════════════════╣"
  sessions=$(tmux ls 2>/dev/null)
  if [ -n "$sessions" ]; then
    echo "║ Sessions đang chạy:                  ║"
    echo "$sessions" | while IFS= read -r line; do
      printf "║   %-35s ║\n" "$line"
    done
  else
    echo "║   (chưa có session nào)              ║"
  fi
  echo "╠═══════════════════════════════════════╣"
  echo "║ n + Enter = Tạo session mới          ║"
  echo "║ a + Enter = Vào lại session cũ        ║"
  echo "║ k + Enter = Kill 1 session            ║"
  echo "║ K + Enter = Kill TẤT CẢ sessions     ║"
  echo "║ s + Enter = Bỏ qua                   ║"
  echo "║                                       ║"
  echo "║ Hoặc gõ thẳng tên session + Enter     ║"
  echo "╚═══════════════════════════════════════╝"
  echo ""
  read -p "Nhập lệnh > " choice
  case "$choice" in
    n)
      read -p "Đặt tên session: " sname
      tmux new -s "${sname:-default}" || true
      ;;
    a)
      read -p "Nhập tên/số session: " sid
      tmux attach -t "$sid" || true
      ;;
    k)
      read -p "Nhập tên/số session muốn kill: " kid
      if tmux has-session -t "$kid" 2>/dev/null; then
        tmux send-keys -t "$kid" "/exit" Enter 2>/dev/null
        sleep 2
        tmux send-keys -t "$kid" "exit" Enter 2>/dev/null
        sleep 1
        tmux kill-session -t "$kid" 2>/dev/null
        echo "✅ Đã kill session: $kid"
      else
        echo "❌ Không tìm thấy session: $kid"
      fi
      ;;
    K)
      read -p "Kill TẤT CẢ? y + Enter xác nhận: " confirm
      if [ "$confirm" = "y" ]; then
        for sess in $(tmux ls -F '#{session_name}' 2>/dev/null); do
          tmux send-keys -t "$sess" "/exit" Enter 2>/dev/null
        done
        sleep 3
        tmux kill-server 2>/dev/null
        echo "✅ Đã kill tất cả sessions"
      else
        echo "Đã huỷ."
      fi
      ;;
    s) ;;
    *)
      tmux attach -t "$choice" 2>/dev/null || tmux new -s "$choice" || true
      ;;
  esac
}

# Tạo session mới (có hỏi tên)
n() {
  if [ -z "$1" ]; then
    read -p "Đặt tên session: " sname
    tmux new -s "${sname:-default}" || true
  else
    tmux new -s "$1" || true
  fi
}
