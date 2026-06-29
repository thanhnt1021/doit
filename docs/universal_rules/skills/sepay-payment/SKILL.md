---
name: sepay-payment
description: Kích hoạt khi tích hợp thanh toán QR chuyển khoản qua SePay vào dự án (đặc biệt Next.js App Router) — payment, cổng thanh toán, QR code, nạp tiền, đơn hàng, webhook thanh toán, banking, bank transfer, payment gateway. Dùng khi cần tạo API create-order/webhook/status, hiển thị QR qr.sepay.vn + polling, thêm field SePay vào DB Order, verify webhook bằng API key, hoặc xây hệ thống chống mất đơn (sweep, watchdog, retry, claim transfer) khi server crash giữa lúc nhận tiền và hoàn thành dịch vụ.
---

# SePay — Tích hợp thanh toán QR

> Skill ngữ cảnh tự kích hoạt. Chi tiết đầy đủ: `docs/universal_rules/rules/SEPAY_PAYMENT.md`.

## Khi nào dùng skill này
- Thêm thanh toán QR chuyển khoản (SePay) vào project Next.js.
- Tạo/sửa 3 API: `create-order`, `sepay-webhook`, `status`.
- Làm trang thanh toán: hiển thị QR + poll trạng thái đã thanh toán.
- Thêm field SePay vào model Order / migrate DB.
- Xây hệ thống chống mất đơn khi webhook trigger async job (AI, PDF, email) và server có thể crash.

## Luồng hoạt động (1 dòng)
Khách quét QR/CK → Ngân hàng → SePay detect mã → POST webhook → Server xử lý → Kích hoạt dịch vụ.
QR là `<img>` tĩnh, KHÔNG cần API call. Webhook field `code` chứa mã đã nhận diện.

## Checklist cốt lõi (bắt buộc)
- [ ] **SePay Dashboard** (my.sepay.vn): link bank → cấu hình mã CK (Tiền tố = PREFIX project 3–5 ký tự chữ; Hậu tố = 6 ký tự Số nguyên) → tạo Webhook (sự kiện `Có tiền vào`, `Bỏ qua nếu không có code`=`Có`, URL `/api/payment/sepay-webhook`, chứng thực `API Key`, Content-Type `application/json`).
- [ ] **Env vars** (thêm vào TẤT CẢ env, gồm cả demo): `SEPAY_API_KEY` (tự tạo `openssl rand -hex 20`, khớp dashboard), `BANK_ACCOUNT_NUMBER`, `BANK_ACCOUNT_NAME` (viết hoa), `BANK_NAME` (format SePay, xem `qr.sepay.vn/banks.json`).
- [ ] **`POST /api/payment/create-order`**: tạo record DB → gen `transferCode = PREFIX + order.id.padStart(6,'0')` → trả `{orderId, transferCode, amount (Int VND, không dấu chấm), bankAccount, bankName, bankAccountName}`. `transferCode` PHẢI khớp cấu hình dashboard.
- [ ] **`POST /api/payment/sepay-webhook`** (`export const dynamic='force-dynamic'`): (1) verify header `Authorization: Apikey {SEPAY_API_KEY}` bằng `crypto.timingSafeEqual` (check length trước) → 401 nếu sai; (2) bỏ qua nếu `transferType!=='in'` hoặc `!code`; (3) dedup theo `sepayTxnId`; (4) match order `transferCode===code && paymentStatus==='unpaid'`; (5) mark `paid` + `paidAt` + `sepayTxnId` + `status='processing'`; (6) trigger service fire-and-forget. **LUÔN trả `{success:true}` status 200** — kể cả khi lỗi/không match (tránh SePay retry).
- [ ] **`GET /api/payment/status?orderId=`**: trả `{paymentStatus, jobId, status}` cho frontend poll.
- [ ] **Frontend**: QR `https://qr.sepay.vn/img?acc=${bankAccount}&bank=${bankName}&amount=${amount}&des=${transferCode}`. Poll `status` mỗi **3s** + listener `visibilitychange` để poll ngay khi tab focus lại (mobile/iOS timer bị suspend). Redirect khi `paymentStatus==='paid'`.
- [ ] **DB Order**: thêm `transferCode @unique`, `amount Int`, `paymentStatus default("unpaid")`, `paidAt`, `sepayTxnId @unique` (chống dup), `jobId`. Rồi migrate.
- [ ] **Sau deploy**: restart production để webhook endpoint có hiệu lực; test curl webhook trước khi live.

## Resilient Order System (khi webhook trigger async job)
- [ ] **Startup Sweep**: khi server boot, query `paymentStatus='paid' && status='pending' && jobId=null` → start job (đơn đã nhận tiền nhưng job chưa kịp tạo trước khi crash).
- [ ] **Job Watchdog**: `setInterval` mỗi 2 phút (delay 30s sau boot), per-service threshold (~12–20 phút theo độ dài job) → job stuck thì `smartRetryOrder`.
- [ ] **`smartRetryOrder(orderId, triggeredBy)`**: gom MỌI retry path (sweep/watchdog/admin/customer). Atomic lock bằng `updateMany` (status `failed`/`processing` → `retrying`); 4 outcome: `skipped` (lock đã bị lấy), `pdfResent` (artifact đã có trên disk → chỉ resend, tiết kiệm cost), `quotaExceeded` (`retryCount>=3`, non-admin → email recovery + alert admin), `retrying` (increment retryCount + tạo job). Admin bypass: reset `retryCount=0`.
- [ ] **Claim Transfer** `POST /api/payment/claim-transfer`: khách tự báo đã CK khi countdown hết / webhook miss. KHÔNG tự mark paid — lưu `claimedAt`+`claimInfo`, alert admin với nút Mark Paid.
- [ ] **Schema bổ sung**: `status` (pending/processing/retrying/failed/completed/cancelled), `retryCount`, `recoveryToken`, `claimedAt`, `claimInfo Json`, `lastActivity` (watchdog), `completedAt`, `emailSent`.

## Cạm bẫy / lỗi hay gặp
- **QR trống**: deploy script restore `.env` từ thư mục demo (khác production) → ghi đè vars. Phải set vars ở mọi env.
- **QR fail**: KHÔNG thêm `&template=compact` vào URL `qr.sepay.vn/img` — SePay không hỗ trợ.
- **Webhook trả non-2xx khi lỗi nội bộ** → SePay retry vô hạn (Fibonacci). Luôn trả 200.
- **`amount` có dấu chấm/format** → sai; phải là Int VND thuần.
- **So sánh API key thường (`===`)** → timing attack; dùng `timingSafeEqual`.
- **Quên dedup `sepayTxnId`** → xử lý đơn 2 lần.
- **Poll chỉ bằng `setInterval`** → mobile background freeze; thiếu `visibilitychange`.
- **`transferCode` không khớp cấu hình prefix/hậu tố dashboard** → SePay không điền field `code` → không match đơn.

## Verify trước khi báo xong
```bash
# Webhook (Expected: {"success":true})
curl -s -X POST https://{domain}/api/payment/sepay-webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Apikey {SEPAY_API_KEY}" \
  -d '{"id":1,"gateway":"TPBank","code":"{PREFIX}000001","content":"{PREFIX}000001","transferType":"in","transferAmount":99000}'
```
- Dán URL `https://qr.sepay.vn/img?acc={BANK_ACCOUNT}&bank={BANK_NAME}&amount=99000&des={PREFIX}000001` vào browser → phải load được ảnh QR.
- Gửi webhook sai/thiếu Authorization → phải nhận 401.
- Gửi webhook trùng `sepayTxnId` lần 2 → order không bị xử lý lại.
- Đã chạy migrate DB; restart production sau deploy.
