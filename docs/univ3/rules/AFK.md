# AFK — Founder không ngồi máy (lazy rule)

> Nạp khi founder báo **rời máy giữa ngày**: "không ngồi máy", "tao ra ngoài", "đi vắng",
> "not on desk", "afk", hoặc gõ lệnh `/khong-ngoi-may` (bí danh `/afk`).
> **Bản thi hành đầy đủ** nằm ở `commands/khong-ngoi-may.md` — cài về `~/.claude/commands/`.
> Hook `enforce/claude/hooks/afk_mode.py` (UserPromptSubmit) tự rót nhắc khi bắt được câu nói tự do,
> kể cả **viết không dấu** ("khong ngoi may tinh"), đồng thời bật cờ AFK cho cổng `afk_hoi_inbox_gate.py`
> (PreToolUse `AskUserQuestion`) chặn hỏi trong CLI.
> File này là bản luật tóm gọn để hiểu **vì sao** và **ranh giới cứng**; đừng thi hành từ trí nhớ,
> mở `commands/khong-ngoi-may.md` ra đọc.

## Vấn đề cần giải

Founder ra ngoài thường xuyên. Ba thứ hay hỏng khi đó:

1. Agent **dừng lại xin quyền** giữa chừng → founder về sau 3 tiếng thấy phiên đứng im từ phút thứ 5.
2. Worker **treo mà không ai biết** ("ngáo chó") — mốc tiến trình không nhích, không ai đọc log.
3. Việc **đang chạy bị bỏ quên** vì agent chỉ nhìn việc mới founder vừa giao.

Đổi lại, không được lấy "tự chủ" làm cớ **phá dữ liệu gốc hoặc máy chủ**.

## Sáu giai đoạn (thứ tự cứng)

| GĐ | Tên | Ranh giới cứng |
|---|---|---|
| 0 | **Kiểm kê tổng thể** | Liệt kê đủ BA loại: đang chạy · hàng chờ/bị chặn · mới giao. ⛔ Cấm bỏ sót việc đang chạy. |
| 1 | **Câu hỏi vào INBOX** | ⛔ **CẤM `AskUserQuestion`** (chốt 11/10/2026: _"đã bảo /afk thì câu hỏi gửi theo list vào inbox mà"_) — cổng `afk_hoi_inbox_gate.py` chặn cứng khi cờ `~/.claude/afk/trang-thai.json` bật. Gom câu cần quyết thành danh sách `1.` `2.`, mã `1A · 1B`, khuyến nghị đặt đầu ghi «(đề xuất)», gửi MỘT tin vào inbox founder (kênh của dự án; không có thì `~/.claude/afk/cau-hoi-<dự án>.md`). **Không chờ**: chọn phương án đề xuất / theo quy trình mã đã có, ghi `CHỐT: … — vì …`. Cờ tắt khi founder gõ «tao về rồi» / «ngồi máy rồi» / «tắt afk». **Quá 8 tiếng KHÔNG phải đã về** (P005, 18/10/2026): `afk_trang_thai.dang_vang()` vẫn tính vắng tới khi founder gõ một lượt CLI thật, hoặc khi lời mới nhất đến từ Telegram. Kênh inbox dự án khai ở `<dự án>/.claude/afk-inbox.txt`. |
| 2 | **Chạy một mạch** | Không chờ trả lời danh sách GĐ1, không hỏi CLI câu nào. Worker nền song song, trần 5 con/dự án, trùng vùng tệp thì gộp hoặc xếp hàng. Brief worker phải TỰ CHỨA. |
| 3 | **An toàn dữ liệu** | ⛔ Cấm xoá bảng / xoá sạch bảng / xoá dòng trên dữ liệu thật; cấm xoá đệ quy cưỡng bức lên thư mục dự án hay máy chủ; cấm thao tác git khó đảo ngược trên nhánh chung. Mọi thay đổi ghi đè → **backup HAI NƠI trong CÙNG MỘT LỆNH** rồi `ls -la` kiểm cả hai. |
| 4 | **Canh worker** | Mốc không nhích **quá 20 phút** = nghi treo → đọc log, chết thật thì dừng và **thả worker mới** làm nốt. Worker báo xong + im quá 5 phút → dừng ngay. Việc bị chặn vì thiếu quyết định → đẩy sang danh sách chờ quyết, **không chặn cả luồng**. |
| 5 | **Tổng kết khi founder về** | Chỉ chốt khi sạch worker + sạch hàng chờ + đã deploy **cả demo lẫn prod**. In đủ 5 mục: bảng việc có bằng chứng · **danh sách câu cần founder quyết** · **ĐÃ TỰ Ý LÀM** (từng `CHỐT:` kèm lệnh gỡ) · danh sách backup (đủ đường dẫn hai nơi) · PID nền đã dựng và đã tắt. |

## Ranh giới tự chủ khi AFK

**Được tự quyết** (và ghi một dòng `CHỐT: … — vì …`):

> ⛔ **Tự quyết xong là PHẢI BÁO «ĐÃ TỰ Ý LÀM»** (chốt 11/10/2026, mọi dự án: _"khi tao afk mà mày tự quyết thì chạy xong phải báo cáo là đã tự ý làm gì, rồi tao sẽ đọc và báo lại sau"_). Mỗi việc tự quyết chạy xong → gửi inbox founder ngay (gắn đúng thẻ việc, không chờ tới GĐ5): **đã tự ý làm gì · vì sao · đụng tới đâu (máy/tệp/dữ liệu) · gỡ lại bằng lệnh nào**. GĐ5 gom lại thành mục riêng «ĐÃ TỰ Ý LÀM». Founder đọc rồi báo lại — câu báo lại đó là lệnh giữ/gỡ.

- Cách thi công, cấu trúc mã, thứ tự việc, chia worker.
- Dữ liệu thử, cấu hình thử tạm (tự hoàn nguyên sau khi thử).
- Deploy demo **và** deploy prod — founder đã chốt 07/09/2026: worker được đi tới prod,
  _"miễn đéo xóa data của tao là được. và nhỡ làm gì thì phải có backup."_
- Dọn rác: tắt tiến trình nền của chính mình, xoá tệp tạm mình tạo.

**Vẫn phải chờ founder** (đẩy sang danh sách chờ quyết, KHÔNG tự làm):

- Thông tin bí mật: mật khẩu, khoá API, giá trị `.env` thật.
- Quyết định kinh doanh: giá, quy trình nghiệp vụ, ai được làm gì.
- Xoá dữ liệu thật dưới bất kỳ hình thức nào.
- Tắt tính năng bảo mật.
- Hành động không đảo ngược được ngoài phạm vi kho mã (gửi thư/tin nhắn ra ngoài, đăng tải công khai).

## Vì sao đặt ở tầng hệ thống, không đặt trong dự án

Founder chốt: _"cái này cần fix ở tầng hệ thống để dùng lâu dài và cho mọi session, dự án,
chứ không chỉ là session này."_ → lệnh nằm ở `~/.claude/commands/`, hook nằm ở
`~/.claude/universal-hooks/`, cả hai được `install.py` chép từ univ3 nên máy nào cài univ3 cũng có.

## Liên quan

- `rules/AGENTS-ORCH.md` — trần worker, xếp hàng, trùng vùng tệp.
- `rules/GATES.md` §Action-Safety — hành động khó đảo ngược.
- `rules/ASK-BACK.md` — cách hỏi ngược; lúc AFK **không hỏi CLI** — mọi câu dồn vào danh sách gửi inbox ở GĐ1.
- `commands/khong-ngoi-may.md` — bản thi hành đầy đủ, có lệnh chạy nguyên văn.
