#!/usr/bin/env python3
"""
afk_mode.py — UserPromptSubmit hook.

Founder hay rời máy giữa chừng. Khi founder BÁO là không ngồi máy (bằng câu nói tự do,
không nhất thiết gõ slash command), phiên phải chuyển sang GIAO THỨC AFK: BẬT cờ AFK (cổng `afk_hoi_inbox_gate.py`
chặn AskUserQuestion), câu cần founder quyết gửi theo danh sách vào inbox, rồi chạy một mạch không xin quyền,
canh worker không để treo, và chốt bằng danh sách câu cần founder quyết.

Markdown trong `~/.claude/commands/khong-ngoi-may.md` chỉ được đọc khi founder gõ đúng
slash command. Hook này vá đúng lỗ đó: founder nói "tao đi ra ngoài" giữa câu chuyện thì
context AFK vẫn được rót vào, không phụ thuộc model tự nhớ.

Nhận diện KHÔNG phân biệt hoa/thường và BỎ DẤU vẫn trúng ("khong ngoi may" = "không ngồi máy").

Không match → im, exit 0 (cấm rót nhiễu vào mọi lượt chat).
"""
import json
import re
import sys
import os
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import afk_trang_thai as _TT  # noqa: E402 — một nguồn cờ AFK, cổng AskUserQuestion đọc cùng tệp

# ── Chuẩn hoá: hạ chữ thường + bỏ dấu tiếng Việt + nén khoảng trắng ────────────
# WHY bỏ dấu: founder gõ nhanh không dấu là chuyện thường ("tao khong ngoi may tinh").
# Nếu chỉ khớp bản có dấu thì trượt đúng lúc cần nhất.


def khong_dau(s: str) -> str:
    s = s.lower().replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)


# Mọi mẫu viết ở dạng ĐÃ BỎ DẤU vì prompt được chuẩn hoá trước khi dò.
# `\b` quanh "afk" để không trúng nhầm giữa từ khác (vd "kafka", "afkl").
MAU = re.compile(
    r"khong ngoi may"            # "không ngồi máy", "không ngồi máy tính"
    r"|khong ngoi truoc may"
    r"|khong o may"
    r"|roi may"                  # "rời máy"
    r"|not (on|at) (the )?desk"
    r"|away from keyboard"
    r"|\bafk\b"
    r"|tao di vang|toi di vang|di vang day"
    r"|tao ra ngoai|toi ra ngoai|di ra ngoai|ra ngoai day"
    r"|tao khong o nha|toi khong o nha"
    r"|khong ngoi truoc man hinh",
)

# Founder báo ĐÃ VỀ → tắt cờ AFK (cổng `afk_hoi_inbox_gate.py` thôi chặn AskUserQuestion).
# WHY không tắt khi founder gõ tin thường: lúc AFK founder vẫn nhắn từ điện thoại (chính lời than
# 11/10 được gõ lúc đang AFK) — gõ tin ≠ đã ngồi máy. Chỉ tắt khi nói rõ. P005 (18/10): quá 8 tiếng thì
# cờ hết hạn nhưng `afk_trang_thai.dang_vang()` VẪN tính vắng tới khi founder gõ một lượt CLI thật.
# WHY mẫu hẹp («đơn về rồi» không được tính): khớp rộng là cờ tắt oan giữa lúc founder vắng.
MAU_VE = re.compile(
    r"^\s*(da )?ve (roi|may roi)\b"
    r"|\b(tao|toi|anh|em) (da )?ve (roi|nha|may|day)\b"
    r"|\b(da )?ve may roi\b"
    r"|\b(tao|toi|anh|em)? ?(dang )?ngoi (may|lai may|truoc may) (roi|day)\b"
    r"|\b(tat|het|thoi|bo|ket thuc) (che do )?afk\b"
    r"|\bback at (my |the )?desk\b|\bi'?m back\b"
)

NHAC = """\
⚠️ FOUNDER BÁO KHÔNG NGỒI MÁY → BẬT **GIAO THỨC AFK**. Đây là rule, không phải gợi ý.
📖 Bản đầy đủ: `~/.claude/commands/khong-ngoi-may.md` (bí danh `/afk`) — MỞ RA ĐỌC, đừng làm từ trí nhớ.

GĐ0 — KIỂM KÊ TRƯỚC KHI HỎI. Liệt kê đủ BA loại việc rồi mới mở miệng:
  (a) đang CHẠY  → `ListAgents` + `bash ~/.claude/universal-hooks/bg-progress.sh`
  (b) HÀNG CHỜ / bị chặn → `ls ~/.claude/worker-queue/*/` + `wlock.sh status` + dòng `ĐỂ LẠI:` chưa có vé
  (c) việc MỚI founder vừa giao trong chính lượt này
  ⛔ CẤM bỏ sót việc đang chạy — founder chốt: "không được để các running task bị ignored".

GĐ1 — ⛔ CẤM AskUserQuestion (anh Thành 11/10/2026: «đã bảo /afk thì câu hỏi gửi theo list vào inbox»).
  Cổng `afk_hoi_inbox_gate.py` CHẶN cứng AskUserQuestion suốt lúc AFK (cờ ~/.claude/afk/trang-thai.json).
  · Câu cần founder quyết → gom thành DANH SÁCH đánh số `1.` `2.`, lựa chọn mang mã `1A · 1B · 1C`,
    khuyến nghị đặt ĐẦU ghi "(đề xuất)", rồi gửi MỘT tin vào INBOX founder:
      ChicHub → TASK_DEV_URL=https://fulfill.thechic.site node scripts/task-dev.mjs tin --rieng --loai hoi --ma <Task-…> …
               (chưa có thẻ: --loai khong-task --ly-do-khong-task "…"; chạy --thu trước rồi mới gửi thật)
      Dự án khác → lệnh khai ở <dự án>/.claude/afk-inbox.txt (C-HX: python3 scripts/sep-viec/sep_viec.py gui …);
               không có thì ghi ~/.claude/afk/cau-hoi-<dự án>.md + nhắc lúc founder về.
  · KHÔNG CHỜ trả lời: câu chưa có lời đáp → chọn phương án đề xuất / theo quy trình mã đã có,
    ghi `CHỐT: … — vì …`, việc khác chạy tiếp. Cấm hỏi bằng văn bản trong CLI rồi đứng chờ.
  · Founder gõ «tao về rồi» / «ngồi máy rồi» / «tắt afk» → cờ tắt, hỏi CLI lại được. Quá 8 tiếng KHÔNG
    phải đã về: vẫn vắng tới khi founder gõ một lượt CLI thật (thông báo nền / tin máy không tính).

GĐ2 — CHẠY MỘT MẠCH, KHÔNG XIN QUYỀN NỮA. Thả worker nền song song, trần 5 con/dự án;
  trùng vùng tệp thì BẮT BUỘC gộp hoặc xếp hàng. Brief worker phải TỰ CHỨA:
  thi công → verify bằng lệnh thật → commit local → deploy demo → smoke → deploy prod → verify prod
  → báo cáo có bằng chứng (commit, output lệnh, tệp:dòng, ảnh, dòng `ĐỂ LẠI:`).

GĐ3 — AN TOÀN DỮ LIỆU (cứng): ⛔ cấm xoá bảng/xoá sạch bảng/xoá dòng trên dữ liệu thật, cấm xoá
  đệ quy cưỡng bức lên thư mục dự án/máy chủ, cấm thao tác git khó đảo ngược trên nhánh chung.
  Mọi UPDATE / migration / ghi đè tệp quan trọng → BACKUP TRƯỚC, lưu HAI NƠI TRONG CÙNG MỘT LỆNH
  (`/tmp/` + thư mục bền trong kho, vd `docs/handoff/backup-<slug>-<ngày>/`) rồi `ls -la` kiểm cả hai.
  Deploy: dựng ra `.next-new` rồi hoán đổi, KHÔNG xoá thư mục đang phục vụ; bắt mã thoát riêng,
  CẤM nối `npm run build` vào ống dẫn. Founder: "địt cụ thằng nào không backup."

GĐ4 — CANH WORKER, CẤM ĐỂ TREO: mỗi lần được đánh thức thì đọc lại toàn bộ mốc tiến trình và so
  với lần trước. Mốc không nhích quá 20 phút = NGHI TREO → đọc log; chết thật thì `TaskStop` rồi
  THẢ WORKER MỚI làm nốt phần dở, ghi lý do. Worker báo xong + im quá 5 phút → `TaskStop` ngay
  (cấm tắt con vừa gọi lệnh trong 5 phút gần đây). Việc bị chặn vì thiếu quyết định founder →
  đẩy sang DANH SÁCH CHỜ QUYẾT, việc khác chạy tiếp, KHÔNG chặn cả luồng.
  Chờ tài nguyên dùng chung bằng ĐÚNG một dòng, chỉ xét mã thoát (cấm vòng `until … sleep`, cấm dò chữ):
    bash ~/.claude/universal-hooks/wlock.sh wait deploy --owner=<slug> --pid=$$ --timeout=900 || exit 75

GĐ5 — TỔNG KẾT KHI FOUNDER VỀ. Chỉ chốt khi KHÔNG còn worker chạy + hàng chờ RỖNG + đã deploy
  CẢ demo LẪN prod. In đủ bốn mục: (1) bảng việc kèm commit/demo/prod/bằng chứng ·
  (2) DANH SÁCH CÂU CẦN FOUNDER QUYẾT (đánh số, mỗi câu một dòng bối cảnh + lựa chọn) ·
  (3) danh sách backup đã tạo, ghi đủ đường dẫn cả hai nơi · (4) PID nền đã dựng và đã tắt.

Xuyên suốt: tiếng Việt có dấu · gọi đơn theo MÃ `{mã_shop}-{mã_đơn_Etsy}`, cấm mã nội bộ ·
không xin lỗi, có lỗi thì đưa giải pháp · kiểm được bằng một lệnh thì CHẠY rồi mới nói.
"""


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    prompt = str(data.get("prompt", ""))
    if not prompt.strip():
        return 0
    # Thông báo nền của harness (báo cáo worker trích lại «tao ra ngoài»…) cũng đi qua UserPromptSubmit — 19:22 09/10 rót giao thức AFK oan.
    # Tin phiên Claude khác cũng đi qua UserPromptSubmit — 11/10/2026 18:59 tin Fulfill gửi C-HX trích «(đang AFK)» bật cờ AFK oan cho cả máy.
    if re.search(r"<task-notification>|\[SYSTEM NOTIFICATION|<system-reminder>|<cross-session-message", prompt):
        return 0
    p = khong_dau(prompt)
    # «tao không ngồi máy rồi» chứa «ngồi máy rồi» → phủ định thì KHÔNG coi là đã về.
    if MAU_VE.search(p) and not re.search(r"khong (ngoi|o) (truoc )?may|roi may", p):
        try:
            _TT.tat()
        except Exception:
            pass
        return 0
    if MAU.search(p):
        try:
            _TT.bat(prompt.strip())
        except Exception:
            pass
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": NHAC,
                    }
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
