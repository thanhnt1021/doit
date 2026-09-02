#!/usr/bin/env bash
# delegate_subagent_reminder.sh — UserPromptSubmit hook (Rule AGENTS-ORCH "1 main, subagent cày").
# Rule ở markdown = xác suất (model hay tự cày trong main). Chèn nhắc MỖI lượt cho tất định hơn.
# Chỉ echo text -> Claude Code gắn vào context lượt đó. Fail-open (không bao giờ exit != 0).
INPUT="$(cat 2>/dev/null || true)"   # JSON của harness; đọc trước vì heredoc bên dưới không dùng stdin
# Đường dẫn TUYỆT ĐỐI của thư mục hook, chốt TRƯỚC mọi `cd` — nếu để dạng tương đối
# ("."), sau khi cd sang project sẽ trỏ nhầm và không tìm ra bg-progress.sh.
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cat <<'EOF'
⛔ LỆNH ĐIỀU PHỐI CỨNG — ÁP DỤNG MỌI LƯỢT, KHÔNG NGOẠI LỆ

CƠ CHẾ: Agent(run_in_background:true) + kết thúc lượt NGAY = main trống.
Không có "tool thứ 2". Không có "để đó nối sau". Main trống là HỆ QUẢ của việc DỪNG,
không phải lệnh riêng. Gọi Agent nền → echo 1-2 dòng → STOP — không làm gì thêm.

NHẬN BẤT KỲ TASK NÀO (build / fix / deploy / điều tra / verify / nhiều bước):
→ main CHỈ được làm 3 việc rồi DỪNG NGAY trong cùng lượt:
  1. Spawn subagent(s) với run_in_background:true và brief ĐẦY ĐỦ (tự-chứa, worker không cần hỏi lại).
  2. Echo 1-2 dòng trạng thái ("Đã spawn X worker, chờ kết quả.").
  3. STOP — để main TRỐNG cho founder gửi lệnh tiếp.

CẤM TUYỆT ĐỐI ở main (nhét hết vào brief của worker):
  - Đọc nhiều file / grep / điều tra sâu
  - Build / test / lint / tsc
  - Commit / push / deploy demo / deploy prod
  - Regen artifact (MANIFEST, schema, codegen…)
  - Verify "lời khai" worker bằng cách tự chạy lệnh

BRIEF WORKER phải tự-chứa:
  - Bước thi công cụ thể (file, hàm, logic)
  - Bước verify (build pass / test pass / shasum…)
  - Bước commit local
  - Bước deploy demo + prod (founder muốn LUÔN cả hai)
  - Bước báo bằng chứng (output thật, file:dòng)

NHIỀU MẢNG ĐỘC LẬP → 1 message nhiều Agent call SONG SONG, tất cả run_in_background:true.
VERIFY LỜI KHAI WORKER → giao worker khác, đừng tự chạy ở main.

BRIEF WORKER BẮT BUỘC KÈM: "Ghi echo 'NN|<nhãn>' > /tmp/claude-bg-progress/<project>/<slug>.progress sau mỗi bước chính — mốc là SỐ NGUYÊN 0-100 (bộ gợi ý: 10 nhận việc · 20 điều tra · 35 ra nguyên nhân · 50 đang sửa · 65 tự kiểm · 72 build · 78 build xanh+commit · 82 CHỜ KHOÁ deploy · 86 deploy demo · 90 smoke demo · 93 deploy prod · 95 verify prod · 98 dọn+viết báo cáo · 100 xong) — chặng deploy PHẢI tách mốc, đừng nằm lì một số; nhãn 1 dòng ≤60 ký tự, tiếng Việt viết ĐỦ DẤU (hook progress_format_enforce.py chặn nếu sai), <project> = basename CLAUDE_PROJECT_DIR (vd EtsyFulfillChichub). Báo % = chạy ~/.claude/universal-hooks/bg-progress.sh (tự lấy scope, chỉ đọc file project hiện tại), cấm ước lượng."

LUẬT SỐ 1 — Worker đang chạy = bất khả xâm phạm (chỉ kill khi: founder bảo / treo-chết / làm sai / đụng file). Đổi chủ đề KHÔNG kill luồng khác — giữ mọi mảng độc lập chạy song song.

Main trống = founder gõ lệnh là có phản hồi tức thì. Đây là ưu tiên số 1.
EOF

# --- BẢNG W## — in MỌI LƯỢT, không chỉ khi gõ "%" -------------------------
# WHY: danh sách agent nền của giao diện chỉ hiện `◯ general-purpose  Verifying…  2h 25m`
# -> founder không biết con nào là việc gì, ngày nào cũng phải hỏi lại:
#     *"tao còn muốn tên worker là cái mã đấy cơ"*
# Cột chữ đó do harness tự sinh (thao tác đang chạy), điều phối viên KHÔNG đặt được ->
# phải đưa thông tin qua đường khác: chèn bảng vào ngữ cảnh + bắt in nguyên văn.
# KHÔNG có worker nào đang chạy -> KHÔNG in gì, để hội thoại thường sạch sẽ.
ASK_CWD="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("cwd") or "")
except Exception: pass' 2>/dev/null)"

# Lượt founder MỚI -> quên chuyện "đã in bảng" của lượt cũ (dấu do stop_viet_lai.py đặt).
printf '%s' "$INPUT" | python3 -c 'import json,os,sys
sys.path.insert(0, os.path.expanduser("~/.claude/universal-hooks"))
try:
    sid = json.load(sys.stdin).get("session_id") or ""
    import stop_viet_lai as S
    S.xoa_dau(sid)
except Exception:
    pass' 2>/dev/null
[ -d "$ASK_CWD" ] || ASK_CWD="$PWD"

# Prompt CHỈ hỏi tiến độ ("%", "tiến độ"…) -> bảng ĐẦY ĐỦ; còn lại -> bảng GỌN.
IS_PROGRESS_ASK="$(printf '%s' "$INPUT" | python3 -c '
import json, re, sys
try:
    p = (json.load(sys.stdin).get("prompt") or "").strip().lower()
except Exception:
    sys.exit(0)
ok = bool(re.fullmatch(r"[%\s?]*%[%\s?]*", p)) or bool(
    re.fullmatch(r"(tiến độ|tien do|tiendo|progress|bar)[\s?%]*", p))
print("1" if ok else "")
' 2>/dev/null)"

BOARD_SH="$HOOK_DIR/worker_board.py"
if [ -f "$BOARD_SH" ]; then
  if [ "$IS_PROGRESS_ASK" = "1" ]; then
    BAR="$(cd "$ASK_CWD" && python3 "$BOARD_SH" --day-du 2>/dev/null)"
  else
    BAR="$(cd "$ASK_CWD" && python3 "$BOARD_SH" 2>/dev/null)"
  fi
else
  BAR="$(cd "$ASK_CWD" && bash "$HOOK_DIR/bg-progress.sh" 2>/dev/null)"
fi

if [ -n "$BAR" ]; then
  printf '\n📊 BẢNG WORKER — đã chạy sẵn, KHÔNG chạy lại lệnh nào để lấy lại:\n%s\n' "$BAR"
  if [ "$IS_PROGRESS_ASK" = "1" ]; then
    cat <<'EOF2'

⛔ TRẢ LỜI: in NGUYÊN VĂN khối trên, giữ nguyên từng dòng.
CẤM chế lại thành bảng markdown. CẤM thêm đoạn văn giải thích. CẤM liệt kê lại từng luồng.
Tối đa 1 dòng tình trạng kèm theo, không hơn.
EOF2
  else
    cat <<'EOF3'

⛔ MỞ ĐẦU CÂU TRẢ LỜI bằng ĐÚNG khối trên, nguyên văn, trong một khối mã, TRƯỚC mọi thứ khác
— rồi mới trả lời việc founder hỏi. Đây là cách DUY NHẤT founder nhìn ra con nào đang làm gì
(danh sách agent của giao diện không hiện được tên việc). In đúng MỘT lần, KHÔNG bình luận
thêm về bảng, KHÔNG chạy lại lệnh để lấy số khác.

⛔ MỘT LẦN LÀ MỘT LƯỢT, KHÔNG PHẢI MỘT TIN. Bị cổng `Stop` chặn phải viết lại → chỉ viết lại
ĐÚNG câu bị bắt, TUYỆT ĐỐI KHÔNG in bảng lần hai (đo 29/08: một lần chặn «con đầu tiên» làm
founder đọc lại nguyên tin 2.390 ký tự kèm bảng — hai lần liền).
EOF3
  fi
fi

exit 0
