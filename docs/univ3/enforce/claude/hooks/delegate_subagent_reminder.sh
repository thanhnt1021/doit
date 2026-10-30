#!/usr/bin/env bash
# delegate_subagent_reminder.sh — UserPromptSubmit hook (Rule AGENTS-ORCH "1 main, subagent cày").
# Rule ở markdown = xác suất (model hay tự cày trong main). Chèn nhắc MỖI lượt cho tất định hơn.
# Chỉ echo text -> Claude Code gắn vào context lượt đó. Fail-open (không bao giờ exit != 0).
INPUT="$(cat 2>/dev/null || true)"   # JSON của harness; đọc trước vì heredoc bên dưới không dùng stdin
# Đường dẫn TUYỆT ĐỐI của thư mục hook, chốt TRƯỚC mọi `cd` — nếu để dạng tương đối
# ("."), sau khi cd sang project sẽ trỏ nhầm và không tìm ra bg-progress.sh.
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- DẤU DỰ ÁN cho khuôn brief tạm (P104/W55) — tính TRƯỚC heredoc vì heredoc dưới
# dùng quote 'EOF' (KHÔNG expand $VAR) nên phải in path thật ở NGOÀI heredoc.
# Thang: (1) UNIV3_SCOPE ép sẵn -> (2) CLAUDE_PROJECT_DIR nếu là thư mục có thật ->
# (3) đi ngược từ cwd lên `/`, dừng ở thư mục đầu tiên có CLAUDE.md/AGENTS.md ->
# (4) không ra được -> "_khong-ro" (KHÔNG dùng basename($PWD) thô — P101 O2.5 đã đo
# "$PWD" sinh ra tên rác kiểu "scratchpad"/"wA"/"wB" khi CLAUDE_PROJECT_DIR rỗng).
P104_SCOPE="${UNIV3_SCOPE:-}"
if [ -z "$P104_SCOPE" ] && [ -n "$CLAUDE_PROJECT_DIR" ] && [ -d "$CLAUDE_PROJECT_DIR" ]; then
  P104_SCOPE="$(basename "$CLAUDE_PROJECT_DIR")"
fi
if [ -z "$P104_SCOPE" ]; then
  P104_CWD="$(printf '%s' "$INPUT" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("cwd") or "")
except Exception: pass' 2>/dev/null)"
  [ -n "$P104_CWD" ] || P104_CWD="$PWD"
  P104_D="$P104_CWD"
  while [ -n "$P104_D" ] && [ "$P104_D" != "/" ]; do
    if [ -f "$P104_D/CLAUDE.md" ] || [ -f "$P104_D/AGENTS.md" ]; then
      P104_SCOPE="$(basename "$P104_D")"
      break
    fi
    P104_D="$(dirname "$P104_D")"
  done
fi
[ -n "$P104_SCOPE" ] || P104_SCOPE="_khong-ro"
P104_SCOPE="$(printf '%s' "$P104_SCOPE" | tr -c 'A-Za-z0-9._-' '-')"

# W140 09/10/2026 (Etsy Task-09102026-39): khối luật điều phối dưới đây là chữ TĨNH ~4.400 ký tự,
# bản cũ in NGUYÊN mỗi lượt. Nay gom vào biến rồi qua `nhac_gon.py`: in đủ lần đầu mỗi phiên, khi
# chữ đổi, sau nén ngữ cảnh (session_context.py xoá sổ ở SessionStart) và mỗi 40 lượt; các lượt khác
# MỘT dòng nhắc đúng các ý cốt lõi. Cửa tắt: UNIV3_NHAC_GON=0.
DIEU_PHOI_DU="$(
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

BRIEF WORKER BẮT BUỘC MỞ ĐẦU BẰNG BA DÒNG KHAI VÙNG (khuôn cố định, máy đọc — cổng
`worker_cap_enforce` CHẶN brief thiếu dòng `GHI:` và KHÔNG còn đoán vùng từ văn xuôi nữa):

  GHI: src/lib/fulfill src/app/api/orders     <- MỌI chỗ worker SẼ GHI, cách nhau bằng khoảng trắng
  ĐỌC: docs/FULFILL_WORKFLOW.md               <- chỗ chỉ đọc; cổng KHÔNG tính là tranh chấp
  TÀI NGUYÊN: db-dev                          <- db-dev · db-that · dev-3000 · prisma · build

Việc thuần đọc / chỉ viết báo cáo ra `/tmp` -> `GHI: -`. Không giành tài nguyên -> `TÀI NGUYÊN: -`.
Khai SAI thì bị chặn oan, khai THIẾU thì không thả được — nhưng KHÔNG khai gì mới là thứ
đã bắt cổng phải vá bốn lần trong một buổi 07/09/2026.

BRIEF WORKER phải tự-chứa:
  - Bước thi công cụ thể (file, hàm, logic)
  - Bước verify (build pass / test pass / shasum…)
  - Bước commit local
  - Bước deploy demo + prod (founder muốn LUÔN cả hai)
  - Bước báo bằng chứng (output thật, file:dòng)

NHIỀU MẢNG ĐỘC LẬP → 1 message nhiều Agent call SONG SONG, tất cả run_in_background:true.
VERIFY LỜI KHAI WORKER → giao worker khác, đừng tự chạy ở main.

BRIEF WORKER BẮT BUỘC KÈM: "Ghi echo 'NN|<nhãn>' > /tmp/claude-bg-progress/<project>/<slug>.progress sau mỗi bước chính — mốc là SỐ NGUYÊN 0-100 (bộ gợi ý: 10 nhận việc · 20 điều tra · 35 ra nguyên nhân · 50 đang sửa · 65 tự kiểm · 72 build · 78 build xanh+commit · 82 CHỜ KHOÁ deploy · 86 deploy demo · 90 smoke demo · 93 deploy prod · 95 verify prod · 98 dọn+viết báo cáo · 100 xong) — chặng deploy PHẢI tách mốc, đừng nằm lì một số; nhãn 1 dòng ≤60 ký tự, tiếng Việt viết ĐỦ DẤU (hook progress_format_enforce.py chặn nếu sai), <project> = basename CLAUDE_PROJECT_DIR (vd EtsyFulfillChichub). Báo % = chạy ~/.claude/universal-hooks/bg-progress.sh (tự lấy scope, chỉ đọc file project hiện tại), cấm ước lượng."

TRƯỚC KHI BẤM THẢ — CHẠY TIỀN KIỂM BRIEF (bắt buộc; cổng `tien_kiem_gate.py` chặn nếu chưa):
EOF
# 2 dòng path KHÔNG nằm trong heredoc quoted trên -> in riêng để nội suy $P104_SCOPE thật
# (P104/W55 O1.1: heredoc <<'EOF' không expand biến; chuyển cả khối sang unquoted thì các
# backtick-code-span khác trong văn bản trên bị bash hiểu là command substitution -> vỡ).
printf '  mkdir -p /tmp/claude-brief/%s\n' "$P104_SCOPE"
printf "  cat > /tmp/claude-brief/%s/w<NN>.md <<'HET'\n" "$P104_SCOPE"
printf '  <dán Y NGUYÊN brief sắp thả>\n  HET\n'
printf '  python3 ~/.claude/universal-hooks/tien_kiem_brief.py --brief /tmp/claude-brief/%s/w<NN>.md --mo-ta "<description>"\n' "$P104_SCOPE"
cat <<'EOF'
Lệnh chạy THẬT các cổng gác lượt thả lên brief đó rồi in ĐẠT/THIẾU từng cổng. Mã thoát 0 mới
được thả. Ngày 19/09/2026 bốn lượt thả liên tiếp bị cổng chặn ngay lúc bấm, founder chỉ thấy
bốn dòng «0 tool uses ⎿ Done» và tưởng bốn thợ chạy rỗng.

LUẬT SỐ 1 — Worker đang chạy = bất khả xâm phạm (chỉ kill khi: founder bảo / treo-chết / làm sai / đụng file). Đổi chủ đề KHÔNG kill luồng khác — giữ mọi mảng độc lập chạy song song.

Main trống = founder gõ lệnh là có phản hồi tức thì. Đây là ưu tiên số 1.
EOF
)"
DIEU_PHOI_NGAN='⛔ ĐIỀU PHỐI (đủ chữ đã in đầu phiên): việc → Agent(run_in_background) brief tự-chứa mở đầu GHI:/ĐỌC:/TÀI NGUYÊN: + mốc .progress → chạy tien_kiem_brief.py trước khi thả → echo 1-2 dòng → DỪNG; main không tự build/deploy/điều tra sâu; worker đang chạy là bất khả xâm phạm.'
printf '%s' "$INPUT" | NHAC_DAY_DU="$DIEU_PHOI_DU" python3 "$HOOK_DIR/nhac_gon.py" --ten dieu-phoi --ngan "$DIEU_PHOI_NGAN" 2>/dev/null \
  || printf '%s' "$DIEU_PHOI_DU"
printf '\n'

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
    # LƯỢT SOI (P085 §5.4 đường c): founder gõ `%`/`tiến độ` là lượt DUY NHẤT được ĐO LẠI
    # chặng. Hai đường kia (bảng trần mỗi lượt prompt + `bg-progress.sh` worker gọi rất
    # dày) chỉ đọc bộ nhớ đệm -> +0 ms. Thiếu cờ `--soi` ở đây thì đệm không bao giờ được
    # nạp và bảng in "chặng ?/? · chưa đo" mãi mãi.
    BAR="$(cd "$ASK_CWD" && python3 "$BOARD_SH" --day-du --soi 2>/dev/null)"
  else
    BAR="$(cd "$ASK_CWD" && python3 "$BOARD_SH" 2>/dev/null)"
  fi
else
  BAR="$(cd "$ASK_CWD" && bash "$HOOK_DIR/bg-progress.sh" 2>/dev/null)"
fi

# W21 C-HX 20/10/2026 (lệnh founder L40 «in lặp kí tự … tốn token»): bảng chỉ in ĐỦ (và chỉ ép
# main dán lại) khi NỘI DUNG đổi so với lần in trước trong phiên — bỏ qua số phút chạy/chờ —,
# hoặc founder gõ «%»/«tiến độ». Không đổi -> MỘT dòng «Bảng worker không đổi (N chạy · M chờ)»,
# KHÔNG ép main in bảng. Logic + tự kiểm ở nhac_gon.py (`bang`, `dau_bang`). Fail-open: python
# hỏng / trả rỗng -> in đủ như cũ. Cửa tắt: UNIV3_NHAC_GON=0.
BANG_KQ=""
if [ -n "$BAR" ]; then
  if [ "$IS_PROGRESS_ASK" = "1" ]; then
    BANG_KQ="DU"
  else
    BANG_KQ="$(printf '%s' "$INPUT" | NHAC_BANG="$BAR" python3 "$HOOK_DIR/nhac_gon.py" --bang 2>/dev/null)"
  fi
  [ -n "$BANG_KQ" ] || BANG_KQ="DU"
fi
if [ -n "$BAR" ] && [ "$BANG_KQ" != "DU" ]; then
  printf '\n%s\n' "$BANG_KQ"
elif [ -n "$BAR" ]; then
  printf '\n📊 BẢNG WORKER — đã chạy sẵn, KHÔNG chạy lại lệnh nào để lấy lại:\n%s\n' "$BAR"
  if [ "$IS_PROGRESS_ASK" = "1" ]; then
    cat <<'EOF2'

⛔ TRẢ LỜI: in NGUYÊN VĂN khối trên, giữ nguyên từng dòng.
CẤM chế lại thành bảng markdown. CẤM thêm đoạn văn giải thích. CẤM liệt kê lại từng luồng.
Tối đa 1 dòng tình trạng kèm theo, không hơn.
EOF2
  else
    HD_BANG="$(
    cat <<'EOF3'

⛔ MỞ ĐẦU CÂU TRẢ LỜI bằng ĐÚNG khối trên, nguyên văn, trong một khối mã, TRƯỚC mọi thứ khác
— rồi mới trả lời việc founder hỏi. Đây là cách DUY NHẤT founder nhìn ra con nào đang làm gì
(danh sách agent của giao diện không hiện được tên việc). In đúng MỘT lần, KHÔNG bình luận
thêm về bảng, KHÔNG chạy lại lệnh để lấy số khác.

⛔ MỘT LẦN LÀ MỘT LƯỢT, KHÔNG PHẢI MỘT TIN. Bị cổng `Stop` chặn phải viết lại → chỉ viết lại
ĐÚNG câu bị bắt, TUYỆT ĐỐI KHÔNG in bảng lần hai (đo 29/08: một lần chặn «con đầu tiên» làm
founder đọc lại nguyên tin 2.390 ký tự kèm bảng — hai lần liền).
EOF3
)"
    printf '%s' "$INPUT" | NHAC_DAY_DU="$HD_BANG" python3 "$HOOK_DIR/nhac_gon.py" --ten huong-dan-bang \
      --ngan $'\n⛔ Mở đầu câu trả lời bằng ĐÚNG khối bảng trên (khối mã, nguyên văn, một lần mỗi lượt, không bình luận).' 2>/dev/null \
      || printf '%s' "$HD_BANG"
    printf '\n'
  fi
fi

exit 0
