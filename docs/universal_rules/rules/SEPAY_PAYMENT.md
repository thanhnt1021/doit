# SePay Payment Integration — Universal Guide

> **Dùng cho:** Bất kỳ dự án Next.js (App Router) nào cần tích hợp thanh toán QR chuyển khoản qua SePay.
> Đọc file này + `docs/SEPAY_INTEGRATION_BRIEF.md` trong project (nếu có) là đủ để implement và debug.

---

## 1. Cách SePay hoạt động

```
Khách quét QR / chuyển khoản → Ngân hàng → SePay detect → POST webhook → Server xử lý → Kích hoạt dịch vụ
```

**3 thứ cần nắm:**

| Thứ | Cách hoạt động |
|-----|---------------|
| **QR Code** | Nhúng `<img src="https://qr.sepay.vn/img?acc=...&bank=...&amount=...&des=...">` — không cần API call |
| **Webhook** | SePay POST JSON về server khi nhận giao dịch khớp mã. Field `code` chứa mã thanh toán đã nhận diện |
| **Xác thực** | SePay gửi header `Authorization: Apikey {key}` — server verify trước khi xử lý |

---

## 2. Setup SePay Dashboard (my.sepay.vn)

### Bước 1 — Liên kết tài khoản ngân hàng
`Tài khoản ngân hàng` → `Thêm tài khoản` → chọn ngân hàng → nhập số TK → xác thực.

### Bước 2 — Cấu hình mã thanh toán
`Công ty` → `Cấu hình chung` → `Cấu trúc mã thanh toán` → `Thêm`:
- **Tiền tố:** Prefix của project, ví dụ `HGCT`, `NCM`, `SHOP`... (3–5 ký tự chữ)
- **Hậu tố:** `6 ký tự`, loại `Số nguyên`

→ SePay nhận diện `PREFIX000042` trong nội dung CK → đặt vào field `code` của webhook.

### Bước 3 — Tạo Webhook
`WebHooks` → `+ Thêm webhooks`:

| Field | Giá trị |
|-------|---------|
| Sự kiện | `Có tiền vào` |
| Tài khoản | TK đã liên kết |
| Bỏ qua nếu không có code | **`Có`** ← bắt buộc |
| URL | `https://{domain}/api/payment/sepay-webhook` |
| Kiểu chứng thực | `API Key` |
| API Key | Chuỗi tự tạo — điền cùng giá trị vào `SEPAY_API_KEY` trong `.env` |
| Content Type | `application/json` |
| Gọi lại khi | HTTP Status Code không 2xx |

---

## 3. Env vars cần thêm

```env
SEPAY_API_KEY=          # Tự tạo bất kỳ (openssl rand -hex 20), điền khớp với SePay Dashboard
BANK_ACCOUNT_NUMBER=    # Số TK ngân hàng
BANK_ACCOUNT_NAME=      # Tên chủ TK (viết hoa)
BANK_NAME=              # Format SePay: TPBank / MBBank / Vietcombank / ACB / Techcombank...
                        # Xem full list: https://qr.sepay.vn/banks.json
```

**⚠️ Nếu có demo environment riêng:** Phải thêm vars vào file `.env` của demo, không chỉ production. Nếu deploy script restore file `.env` từ thư mục demo (khác production), vars sẽ bị ghi đè → QR trống.

---

## 4. File cần tạo (Next.js App Router)

### `POST /api/payment/create-order`

Nhận thông tin đơn hàng từ frontend → tạo record trong DB → gen mã CK → trả bank info.

```typescript
// Trả về cho frontend:
{
  orderId: number,
  transferCode: string,   // "PREFIX000042" — PHẢI khớp với cấu hình SePay dashboard
  amount: number,         // Integer VND, không dấu chấm
  bankAccount: process.env.BANK_ACCOUNT_NUMBER,
  bankName: process.env.BANK_NAME,
  bankAccountName: process.env.BANK_ACCOUNT_NAME,
}

// Gen mã: PREFIX + orderId padded
const transferCode = `${PREFIX}${order.id.toString().padStart(6, '0')}`
```

### `POST /api/payment/sepay-webhook`

```typescript
export const dynamic = 'force-dynamic'

export async function POST(request: Request) {
  // 1. Verify API key (timing-safe comparison to prevent timing attacks)
  const auth = request.headers.get('Authorization') || ''
  const expected = `Apikey ${process.env.SEPAY_API_KEY}`
  const isValid = auth.length === expected.length &&
    crypto.timingSafeEqual(Buffer.from(auth), Buffer.from(expected))
  if (!isValid) {
    return Response.json({ success: false }, { status: 401 })
  }

  try {
    const { id: txnId, code, transferType, transferAmount } = await request.json()

    // 2. Chỉ xử lý tiền vào
    if (transferType !== 'in' || !code) return Response.json({ success: true })

    // 3. Chống duplicate
    const exists = await db.order.findFirst({ where: { sepayTxnId: txnId } })
    if (exists) return Response.json({ success: true })

    // 4. Match order
    const order = await db.order.findFirst({
      where: { transferCode: code, paymentStatus: 'unpaid' }
    })
    if (!order) return Response.json({ success: true })

    // 5. Mark paid + tạo job/trigger service
    await db.order.update({
      where: { id: order.id },
      data: { paymentStatus: 'paid', paidAt: new Date(), sepayTxnId: txnId, status: 'processing' }
    })

    // 6. Trigger xử lý (fire-and-forget)
    triggerService(order).catch(console.error)

    return Response.json({ success: true })  // LUÔN trả 200 — kể cả khi lỗi nội bộ
  } catch (err) {
    console.error('[sepay-webhook]', err)
    return Response.json({ success: true })  // Vẫn 200 — tránh SePay retry vô hạn
  }
}
```

### `GET /api/payment/status?orderId=xxx`

Frontend dùng để poll:

```typescript
const order = await db.order.findUnique({
  where: { id: Number(orderId) },
  select: { paymentStatus: true, jobId: true, status: true }
})
return Response.json(order)
```

---

## 5. Frontend — Trang thanh toán

### Hiển thị QR

```tsx
// Bank info nhận từ URL params (truyền qua từ create-order response)
const qrUrl = `https://qr.sepay.vn/img?acc=${bankAccount}&bank=${bankName}&amount=${amount}&des=${transferCode}`

<img src={qrUrl} alt="QR thanh toán" width={200} height={200} />
```

**⚠️ KHÔNG dùng `&template=compact`** — SePay không hỗ trợ param này, làm QR fail.

### Poll thanh toán thành công

```typescript
// Poll mỗi 3 giây
const poll = async () => {
  const res = await fetch(`/api/payment/status?orderId=${orderId}`)
  const data = await res.json()
  if (data.paymentStatus === 'paid' && data.jobId) {
    // Redirect sang trang xử lý / success
    router.replace(`/processing?job=${data.jobId}`)
  }
}
useEffect(() => {
  const id = setInterval(poll, 3000)
  return () => clearInterval(id)
}, [])
```

**⚠️ Mobile UX — setInterval bị suspend khi tab background:**
Trên iOS Safari, khi user chuyển sang app ngân hàng, timer đóng băng. Khi quay lại, cần ~3–5s để poll tiếp. Thêm `visibilitychange` để poll ngay khi tab được focus lại:

```typescript
useEffect(() => {
  const onVisible = () => { if (document.visibilityState === 'visible') poll() }
  document.addEventListener('visibilitychange', onVisible)
  return () => document.removeEventListener('visibilitychange', onVisible)
}, [])
```

---

## 6. DB Schema — fields cần thêm vào Order model

```prisma
// Thêm vào model Order hiện có:
transferCode  String?   @unique @map("transfer_code")  // "PREFIX000042"
amount        Int?                                      // VND integer
paymentStatus String    @default("unpaid") @map("payment_status")
paidAt        DateTime? @map("paid_at")
sepayTxnId    Int?      @unique @map("sepay_txn_id")   // Chống duplicate webhook
jobId         String?   @map("job_id")                 // Link sang job xử lý (nếu có)
```

---

## 7. Kiểm tra sau khi setup

```bash
# Test webhook endpoint
curl -s -X POST https://{domain}/api/payment/sepay-webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Apikey {SEPAY_API_KEY}" \
  -d '{
    "id": 1,
    "gateway": "TPBank",
    "transactionDate": "2026-01-01 00:00:00",
    "accountNumber": "123456789",
    "code": "{PREFIX}000001",
    "content": "{PREFIX}000001",
    "transferType": "in",
    "transferAmount": 99000,
    "accumulated": 0,
    "subAccount": null,
    "referenceCode": "TEST",
    "description": ""
  }'
# Expected: {"success":true}

# Test QR URL — dán vào browser, phải load được ảnh QR
# https://qr.sepay.vn/img?acc={BANK_ACCOUNT}&bank={BANK_NAME}&amount=99000&des={PREFIX}000001
```

---

## 8. Checklist triển khai

- [ ] Tạo `POST /api/payment/create-order` — gen transferCode, lưu DB, trả bank info
- [ ] Tạo `POST /api/payment/sepay-webhook` — verify key, dedup, match order, trigger service
- [ ] Tạo `GET /api/payment/status` — frontend poll
- [ ] Thêm fields SePay vào Order model + migrate DB
- [ ] Thêm 4 env vars vào **tất cả** environments (production + demo)
- [ ] Trang payment: QR từ URL `qr.sepay.vn`, poll 3s + `visibilitychange` listener
- [ ] Setup SePay dashboard: link bank → cấu hình mã (prefix khớp code) → tạo webhook
- [ ] Restart production sau deploy để webhook endpoint có hiệu lực
- [ ] Test curl webhook trước khi live

---

## 9. Resilient Order System — Chống mất đơn khi server crash

> Áp dụng khi: SePay webhook kích hoạt async job (AI, PDF, email...) — server có thể crash bất kỳ lúc nào giữa "nhận tiền" và "hoàn thành dịch vụ".

### Vấn đề cần giải quyết

```
Khách CK → SePay webhook nhận → server crash → job biến mất → khách mất tiền, không nhận được dịch vụ
```

3 tình huống crash phổ biến:
1. Server restart (deploy) sau khi nhận tiền nhưng trước khi job xong
2. Job stuck (AI timeout, OOM, network fail) — không có progress, không có error
3. Webhook nhận tiền thành công nhưng chưa tạo được job (crash giữa chừng)

---

### Pattern 1 — Startup Sweep: tìm paid+pending+no-job

Chạy **ngay khi server boot**. Tìm orders đã nhận tiền nhưng chưa có job → start job ngay:

```typescript
// src/lib/jobs.ts (hoặc instrumentation.ts)
async function sweepPaidPendingOrders() {
  const orders = await db.order.findMany({
    where: { paymentStatus: 'paid', status: 'pending', jobId: null },
  })
  for (const order of orders) {
    await createReportJob(order)  // hoặc hàm trigger service tương đương
    console.log(`[SWEEP] Started job for paid+pending order ${order.id}`)
  }
}
```

_Lý do: SePay webhook có thể đã nhận tiền và update `paymentStatus='paid'` trước khi server crash — nhưng job chưa kịp tạo. Restart lại không có gì chạy nếu không có sweep này._

---

### Pattern 2 — Job Watchdog: phát hiện job stuck

Chạy mỗi 2–5 phút. Tìm job đang processing nhưng không có activity trong một khoảng thời gian → retry:

```typescript
// src/lib/job-watchdog.ts
const STUCK_THRESHOLDS: Record<string, number> = {
  fast_service: 12 * 60 * 1000,   // 12 phút
  slow_service: 20 * 60 * 1000,   // 20 phút (AI output dài hơn)
}

async function runWatchdog() {
  const now = Date.now()
  // Lấy jobs đang processing + in-memory lastActivity
  for (const [jobId, job] of activeJobs.entries()) {
    const threshold = STUCK_THRESHOLDS[job.service] ?? 15 * 60 * 1000
    if (job.status === 'processing' && now - job.lastActivity > threshold) {
      const order = await db.order.findFirst({ where: { jobId } })
      if (order) await smartRetryOrder(order.id, 'watchdog')
    }
  }
}

// Khởi động: delay 30s sau boot (chờ server ổn định), sau đó mỗi 2 phút
setTimeout(() => {
  runWatchdog()
  setInterval(runWatchdog, 2 * 60 * 1000)
}, 30_000)
```

**Per-service threshold:** Service chạy lâu hơn (AI output dài) cần threshold cao hơn — tránh false positive retry khi job đang chạy bình thường.

---

### Pattern 3 — `smartRetryOrder()`: Centralized retry logic

Thay vì mỗi nơi (sweep, watchdog, admin, customer) tự handle retry riêng → gom vào 1 hàm:

```typescript
// src/lib/smart-retry.ts
type TriggeredBy = 'sweep' | 'watchdog' | 'admin' | 'customer'
type RetryResult = 'skipped' | 'pdfResent' | 'quotaExceeded' | 'retrying'

async function smartRetryOrder(orderId: number, triggeredBy: TriggeredBy): Promise<RetryResult> {
  // 0. Admin bypass: reset retryCount để không bị quota block
  if (triggeredBy === 'admin') {
    await db.order.update({ where: { id: orderId }, data: { retryCount: 0 } })
  }

  // 1. Atomic lock: chỉ lấy lock nếu status là failed/processing (tránh race condition)
  const locked = await db.order.updateMany({
    where: { id: orderId, status: { in: ['failed', 'processing'] } },
    data: { status: 'retrying' },
  })
  if (locked.count === 0) return 'skipped'  // Ai đó đã lấy lock trước

  const order = await db.order.findUnique({ where: { id: orderId } })
  if (!order) return 'skipped'  // Race condition: order bị xóa giữa lock và query

  // 2. Check PDF đã tồn tại — nếu có chỉ cần resend email (tiết kiệm API cost)
  const pdfPath = resolvePdfPath(order.pdfUrl)  // /var/[project]/pdfs/{id}.pdf
  if (pdfPath && fs.existsSync(pdfPath)) {
    await resendEmailOnly(order, pdfPath)
    await db.order.update({ where: { id: orderId }, data: { status: 'completed' } })
    return 'pdfResent'
  }

  // 3. Quota check (bỏ qua nếu admin)
  if (triggeredBy !== 'admin' && order.retryCount >= 3) {
    await db.order.update({ where: { id: orderId }, data: { status: 'failed' } })
    await sendRecoveryEmail(order)
    await notifyAdmin(`Đơn #${orderId} hết quota retry`)
    return 'quotaExceeded'
  }

  // 4. Full retry
  await db.order.update({
    where: { id: orderId },
    data: { retryCount: { increment: 1 } },
  })
  await createJob(order)  // fire-and-forget
  return 'retrying'
}
```

**4 outcomes:**

| Outcome | Khi nào | Hành động |
|---------|---------|-----------|
| `skipped` | Race condition — ai đó đã lấy lock | Không làm gì |
| `pdfResent` | PDF đã có trên disk | Chỉ resend email, không re-generate |
| `quotaExceeded` | retryCount ≥ 3 (non-admin) | Gửi email recovery, alert admin |
| `retrying` | Đủ điều kiện | Tạo job mới, full pipeline |

**Dùng ở mọi điểm trigger:** sweep, watchdog, admin bot retry button, customer `/recover` page.

---

### Pattern 4 — Claim Transfer: khách tự báo đã CK

Khi countdown hết mà SePay chưa nhận được webhook (webhook miss, CK sai nội dung, network lag):

```typescript
// POST /api/payment/claim-transfer
// { orderId, amount?, transferContent? }

// 1. Verify order: pending + unpaid + chưa claim
const order = await db.order.findFirst({
  where: { id: orderId, paymentStatus: 'unpaid', status: 'pending', claimedAt: null }
})
if (!order) return error('Không tìm thấy đơn hoặc đã xử lý')

// 2. Lưu claim — KHÔNG tự mark paid, chờ admin verify
await db.order.update({
  where: { id: orderId },
  data: { claimedAt: new Date(), claimInfo: { amount, transferContent } }
})

// 3. Alert admin với nút [✅ Mark Paid]
await sendTelegramAlert(`🖐️ Khách báo đã CK! Đơn #${orderId} | ${order.email}
💰 Báo: ${amount}đ | 📝 ${transferContent}`, {
  keyboard: [[{ text: '✅ Mark Paid', callback_data: `o_pay_${orderId}` }]]
})
```

**Frontend UI khi countdown hết:**
```
Hết 15 phút — bạn muốn:

[Quay lại / Chưa CK]    [Tôi đã chuyển khoản ✋]
                               ↓
                    Form: số tiền + nội dung CK
                               ↓
                    "Đã ghi nhận! Admin xác nhận trong 30 phút."
```

---

### Schema fields bổ sung cho Resilient System

```prisma
model Order {
  // ... fields SePay cơ bản từ Section 6 ...

  // Recovery
  status          String    @default("pending")     // pending/processing/retrying/failed/completed/cancelled
  retryCount      Int       @default(0) @map("retry_count")
  recoveryToken   String?   @map("recovery_token")  // 8 chars uppercase — cho khách tự recover

  // Claim transfer
  claimedAt       DateTime? @map("claimed_at")
  claimInfo       Json?     @map("claim_info")      // { amount, transferContent }

  // Tracking
  completedAt     DateTime? @map("completed_at")
  emailSent       Boolean   @default(false) @map("email_sent")
  lastActivity    DateTime? @map("last_activity")   // watchdog dùng để detect stuck
}
```

---

### Checklist bổ sung (ngoài checklist cơ bản ở Section 8)

- [ ] Startup sweep: `sweepPaidPendingOrders()` chạy khi server boot
- [ ] Job Watchdog: `setInterval` 2 phút, per-service threshold
- [ ] `smartRetryOrder()`: centralize mọi retry path qua 1 hàm
- [ ] Claim Transfer API: `POST /api/payment/claim-transfer`
- [ ] Frontend payment page: countdown pause khi mất kết nối, 2-branch UI khi countdown hết
- [ ] Webhook luôn trả 200 — kể cả khi lỗi nội bộ (tránh SePay retry Fibonacci)
- [ ] Schema: thêm `retryCount`, `recoveryToken`, `claimedAt`, `claimInfo`, `lastActivity`
