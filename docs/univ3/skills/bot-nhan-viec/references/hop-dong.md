# Hợp đồng máy chủ ⇄ máy nhà (bản gọn và bản đầy đủ phải giữ cùng tên, cùng JSON)

## Kho — 2 bảng (bản gọn SQLite; bản đầy đủ map sang bảng thẻ việc + sổ tin nhóm)

```sql
CREATE TABLE tin (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id TEXT NOT NULL, message_id INTEGER NOT NULL,
  luc INTEGER NOT NULL, tu_id TEXT, tu_ten TEXT, la_bot INTEGER NOT NULL DEFAULT 0,
  noi_dung TEXT NOT NULL DEFAULT '', reply_to INTEGER, media_group TEXT, anh TEXT,   -- anh = file_id Telegram
  ma_viec TEXT, sua_luc INTEGER, raw TEXT, nhan_luc INTEGER NOT NULL,
  can_bao INTEGER NOT NULL DEFAULT 0,      -- 1 = tin người cần phiên Claude xử lý
  claude_doc_luc INTEGER,                  -- NULL = chưa đọc
  ban_truoc TEXT,                          -- nội dung trước lần sửa cuối
  UNIQUE(chat_id, message_id)              -- chống trùng khi Telegram gửi lại
);
CREATE INDEX tin_ma ON tin(ma_viec);
CREATE INDEX tin_chua_doc ON tin(can_bao, claude_doc_luc);

CREATE TABLE viec (
  ma TEXT PRIMARY KEY, ngay TEXT NOT NULL, stt INTEGER NOT NULL,
  tieu_de TEXT NOT NULL, noi_dung TEXT NOT NULL DEFAULT '', nguoi_giao TEXT, giao_luc INTEGER,
  trang_thai TEXT NOT NULL, tin_goc INTEGER, tao_luc INTEGER NOT NULL, cap_nhat INTEGER NOT NULL
);
```
SQLite: `PRAGMA busy_timeout=8000; PRAGMA journal_mode=WAL;`. Nâng cấu trúc thì chụp bản sao (`VACUUM INTO`) trước,
DDL trong giao dịch, tin cũ coi như đã đọc (khỏi đổ cả lịch sử vào phiên đầu).

Bản đầy đủ (Postgres): giữ cờ đọc trong JSONB của sự kiện (`meta.claude_da_doc`), quan hệ Reply + cảm xúc trong
`meta.tg.tra_loi` / `meta.tg.cam_xuc[<id tài khoản>]` — không cần thêm bảng.

## Webhook `hook.php` (hoặc route `/api/telegram/webhook`)
- Header `X-Telegram-Bot-Api-Secret-Token` ≠ `TG_WEBHOOK_SECRET` → `401` (thiếu cấu hình secret cũng `401` — fail-closed).
- `chat.id` không thuộc danh sách nhóm (`TG_CHAT_SEP` + các nhóm nội bộ khác bot đang ở) → `200 {"ok":true}`, không lưu,
  không đáp. Chat riêng của chủ nhà được nhận như nhóm. Nhóm có người ngoài nằm danh sách RIÊNG: chỉ để máy gửi tin vào
  (có lọc chữ tài chính nội bộ → `422`), không chạy lệnh, không vào sổ nội bộ.
- Mọi lời gọi lối máy mang header nhịp tim → máy chủ ghi mốc «máy nhà còn sống» (dùng cho câu trả lời mặc định khi máy tắt).
- Ghi trong một giao dịch; ném lỗi → `500` (Telegram gửi lại tới 24 giờ). Bước phụ SAU khi ghi (đáp «Đã nhận») lỗi thì
  vẫn `200` — tránh «Đã nhận» lặp.
- «Đã nhận · Task-…» trả ngay trong phản hồi webhook (`method: sendMessage`, `reply_to_message_id`).

## Lối máy `api.php?act=…` (header `X-Sep-Viec-Token`, sai → `401`)

| act | Vào | Ra / tác dụng |
|---|---|---|
| `moc` | — | mốc tin mới nhất (cho `theo-doi` cũ) |
| `tat-ca` | — | mọi việc + tin (cho `keo` dựng sổ `SO-VIEC.md`) |
| `chua-doc` | — | tin `can_bao=1 AND claude_doc_luc IS NULL`, cũ → mới |
| `da-doc` | `{"ids":[12,13]}` | gắn đã đọc ĐÚNG các id; `ids` rỗng → `400` |
| `tao-viec` | `{tieu_de, noi_dung?, ma?, giao_luc?, nguoi_giao?, tin_goc?, trang_thai?}` | cấp mã theo NGÀY của `giao_luc` |
| `gan-tin` | `{ma, message_ids:[…]}` | gắn tin có sẵn vào việc |
| `trang-thai` | `{ma, trang_thai}` | đổi trạng thái (máy chủ PHẢI kiểm giá trị hợp lệ) |
| `gui` | `{ma?, chu, anh?:[base64…], html?, reply_to?, chat_id?, rieng?}` | không `ma` → cấp mã mới; thay `{MA}` trong chữ; gửi Telegram; **ghi tin bot vào kho kèm mã** (để Reply gắn được) |
| `nhap` | mảng update `getUpdates` cũ | chỉ lưu, không tạo việc |
| `xoa` | `{tin:[message_id…], ma:[…]}` | xoá đích danh tin/việc thử |
| `clitell` | header `X-Canh: 1` khi con canh hỏi · header `X-Phien: 1` khi nhịp phiên hỏi | lời `/clitell` chưa nhận `[{id, luc, chu, noi_tiep}]` (mục 7d); `X-Canh` → ghi mốc `canh` («đang nghe», ≤ 2 phút) · `X-Phien` → ghi mốc `phien` («phiên còn mở», ≤ 3 phút) — hai mốc riêng trên cùng dòng trạng thái, máy chủ phân ba trạng thái nghe / bận / tắt (mục 7d.5) |
| `clitell-da-nhan` | `{"ids":[5]}` | gắn «CLI đã nhận» đúng id + thả 👀 lên tin chủ |
| `clitell-tra` | `{id, chu, thu?}` | Reply đúng tin chủ, dấu `🤖 Phiên CLI:`, ≤ 6 dòng / ≤ 600 ký tự (quá → `422`); ghi mã tin bot vào dòng lời |
| `chua-doc` (thêm) | — | thêm khoá `duyet_luot` = lượt duyệt đang cần máy `{id, trang_thai, ban, cap_nhat, gop_y}` hoặc `null` (mục 7e) |
| `duyet-luot-xem` | `{id?}` | lượt đang mở (hoặc id) + `cho` (mã việc đang chờ) + `mo_khac` (việc đang mở khác — đích gộp); chỉ đọc |
| `phuong-an` | `{phuong_an:{lam,hoi,gop,bo,de_sau}, text, anh:[1–3], thu?}` | `thu`: chỉ soát → `{loi:[…]}`; thật: soát (sai → `400`) rồi gửi ảnh + chú thích vào chat riêng chủ nhà, bản +1, ghi bảng tin phương án |
| `ap-phuong-an` | `{thu?}` | chỉ khi lượt `da-ok` (`dang-ap` = chạy lại): gộp → khởi động → bỏ/để sau trong MỘT giao dịch; trả câu hỏi chưa gửi |
| `ap-hoi` | `{id, ma}` | ghi đã gửi câu hỏi của việc đó (chạy lại không gửi trùng) |
| `ap-xong` | `{id}` | lượt `da-ap` + một tin «✅ Đã làm theo phương án» vào chat riêng; còn câu chưa gửi → `400` |
| `gui` (thêm) | `duyet_luot: <id>` | mở lối riêng cho việc NHÓM chỉ khi câu nằm trong mục «hỏi chủ nhà» của lượt đang áp |

## CLI máy nhà (`scripts/sep-viec/sep_viec.py`, thư viện chuẩn Python; `--nhan-anh` cần Pillow)

| Lệnh | Việc |
|---|---|
| `gui --ma … --tieu-de … --hoi "1. … 1A · … 1B · …" [--anh a.png --nhan-anh "1A · …"] [--html] [--thu]` | gửi theo khuôn, đo trần trước khi gửi |
| `moi [--json]` | tin chưa đọc, giờ VN, tự tải ảnh in đường dẫn, tin sửa in `ĐÃ SỬA «cũ» → «mới»` |
| `da-doc --id 12,13` | id kho (cột đầu dòng `moi`), không phải message_id |
| `canh [--phut 110]` | con canh nền; pid + trạng thái ở `<dự án>/.claude/sep-viec/` |
| `nhip-phien [--giay 60] [--thu-muc <dự án>]` | NHỊP PHIÊN nền (bật từ SessionStart qua `.claude/nhip-phien.sh`): gọi `clitell` kèm `X-Phien: 1` mỗi `--giay`; không còn tiến trình Claude CLI có thư mục trong dự án → tự thoát; tệp pid mở `wx` → mỗi máy một nhịp (SKILL mục 7d.5) |
| `keo` | kéo sổ về `docs/<…>/SEP-VIEC/SO-VIEC.md`, tải ảnh vào `SEP-VIEC/anh/<mã>/` |
| `anh --id 12` | tải ảnh/tệp một tin (`getFile`, thử lại 3 lượt, ghi `.tmp` rồi đổi tên) |
| `tao-viec`, `trang-thai`, `nhap`, `xoa`, `dat-webhook` | như bảng act |
| `clitell-tra --id 5 --chu "…" [--thu]` | trả lời chủ một lời `/clitell` (`canh`/`moi` tự in lời + tự báo `clitell-da-nhan`) |
| `duyet-luot [--ra x.json]` | gom lượt + việc đang chờ (nội dung, tin, diễn biến) + mẫu phương án ra JSON, in tóm tắt (mục 7e) |
| `phuong-an --tep pa.json [--thu] [--ra a.png]` | dựng ảnh bảng + chú thích, máy chủ soát rồi gửi chat riêng chủ nhà |
| `ap-phuong-an [--thu]` | áp lượt chủ nhà đã OK; gửi câu hỏi qua `gui`; xong thì `ap-xong` |

Bản đầy đủ thêm: `ghi` (dòng diễn biến lên việc), `ket-qua` (tóm tắt + cách kiểm + ảnh), `chuyen --cot … --cho "<tên>"`,
`tin --loai xong|hoi|khong-task [--nhom <id>] [--reply <message_id>] [--rieng]` (lối gửi DUY NHẤT — nhóm chính, nhóm
khác, nối tin người hỏi, chat riêng chủ nhà; sự kiện ghi `chat_id` nhóm đó để Reply vào đúng thẻ), `tim` (BOT thả ❤ tin việc + tin trả lời = «đã xử»; ❤ chủ nhà thả thì không bao giờ là trả lời — SKILL mục 4.9),
`phan-hoi` (gom việc theo người đang chờ).
