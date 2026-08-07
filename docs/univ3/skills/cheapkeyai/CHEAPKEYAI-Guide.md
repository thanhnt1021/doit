# cheapkeyai.shop — Gọi AI/LLM qua proxy OpenAI-compatible

> Kế thừa & thay thế **v98store** (đã đóng cửa, migrate sang đây). Dùng y hệt SDK `openai`, chỉ đổi `base_url` + key.
> Doc này portable — copy sang project khác dùng luôn.

## 1. cheapkeyai.shop là gì
`https://cheapkeyai.shop` = **proxy trung gian OpenAI-compatible**. Dùng 1 SDK `openai` gọi được mọi model (Claude / GPT / Gemini / Grok / DeepSeek / Kimi...), billing 1 chỗ, không cần key riêng từng hãng. **Endpoint OpenAI cuối cùng PHẢI có `/v1`.**

## 2. Khác v98store (điểm ĐÃ FIX cho chuẩn cheap)
| | v98store (cũ, đã chết) | **cheapkeyai.shop (mới)** |
|---|---|---|
| Base URL OpenAI | `https://v98store.com/v1` | `https://cheapkeyai.shop/v1` |
| Xác thực | Bearer key | Bearer key (như OpenAI chuẩn) |
| **Inject persona (Kiro)** | CÓ — phá nhân vật, hay từ chối | **KHÔNG** (test "bạn là model gì?" → "Tôi là Claude" bình thường) → **KHÔNG cần bọc XML/bypass gắt như v98** |
| Balance endpoint | `/check-balance?key=` | **Kiểu OpenAI**: `/v1/dashboard/billing/subscription` + `/v1/dashboard/billing/usage` (giá trị có thể là placeholder → xem dashboard web cho số thật) |
| Nạp tiền | Telegram @v98storebot | Xem trên web cheapkeyai.shop (dashboard) |

## 3. .env (KHÔNG commit key)
```
CHEAP_API_KEY=sk-xxxxxxxx...                  # key gọi /v1/* (chat/image)
CHEAP_BASE_URL=https://cheapkeyai.shop        # code tự thêm /v1
CHEAP_ACCESS_TOKEN=xxxxxxxx                    # (tuỳ chọn) đọc số dư qua /api/user/self — xem Mục 10
CHEAP_USER_ID=452                             # user id, header New-Api-User
```
> Key + access token là bí mật: gitignore `.env`, KHÔNG echo ra log, KHÔNG hardcode. Access token KHÁC key sk- (xem Mục 10.2). Nhiều project dùng chung 1 key vẫn để mỗi project 1 `.env`.

## 4. Recipe cơ bản (Python)
```bash
pip install openai httpx          # KHÔNG cần anthropic/google-generativeai
```
```python
import os, httpx
from openai import AsyncOpenAI     # Async cho bot/web

key = os.getenv("CHEAP_API_KEY")                                   # đọc .env, KHÔNG hardcode
raw = os.getenv("CHEAP_BASE_URL", "https://cheapkeyai.shop")
base_url = raw if raw.endswith("/v1") else f"{raw.rstrip('/')}/v1" # endpoint cuối PHẢI /v1
client = AsyncOpenAI(api_key=key, base_url=base_url,
                     http_client=httpx.AsyncClient(timeout=120.0)) # 60s mặc định quá ngắn

resp = await client.chat.completions.create(
    model="claude-opus-4-8", messages=messages,
    temperature=0.3, max_tokens=2048, timeout=90.0)
text = resp.choices[0].message.content
```

### JS/TS (SDK openai)
```js
import OpenAI from "openai";
const client = new OpenAI({ apiKey: process.env.CHEAP_API_KEY, baseURL: "https://cheapkeyai.shop/v1" });
const r = await client.chat.completions.create({ model: "claude-opus-4-8", messages });
```

## 5. Model có sẵn (22 model, xác thực bằng `GET /v1/models`)
- **Claude**: `claude-opus-5`, `claude-opus-4-8`, `claude-opus-4-7`, `claude-sonnet-5`, `claude-sonnet-4-6`
- **GPT**: `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, `gpt-5.4-mini`, `gpt-5.4-nano`, `gpt-4.1-nano`
- **Gemini**: `gemini-3.1-pro`, `gemini-3.6-flash`, `gemini-3.5-flash`
- **Grok**: `grok-4.5`, `grok-4.3`, `grok-build-0.1`
- **Khác**: `kimi-k3`, `composer-2.5-fast`, `codex-auto-review`, `text-embedding-3-large`
- Mặc định nên dùng: `claude-sonnet-4-6` (nhanh/rẻ) · `claude-opus-4-8` (nặng, OCR/vision) · `gpt-5.6-*` · `gemini-3.5-flash` (rẻ, tác vụ phụ).

## 6. Vision (đọc ảnh) — ĐÃ TEST OK
Nhét ảnh base64 vào message dạng OpenAI multimodal:
```python
content = [{"type": "text", "text": "Đọc trang này..."}]
for path in imgs:
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
resp = await client.chat.completions.create(
    model="claude-opus-4-8", messages=[{"role": "user", "content": content}],
    max_tokens=8000, temperature=0)
```
> Đã dùng chính cấu hình này để OCR từ điển Mường (project iloveus): 1 trang 4 mảnh ảnh → ~34 mục, chuẩn.

## 7. Endpoint khác (đều dưới `/v1`)
- Chat: `POST /v1/chat/completions` (stream, vision, tool calling)
- Responses API: `POST /v1/responses`
- Ảnh: `POST /v1/images/generations`
- Embeddings / Rerank / Moderations: có (RAG, search)
- Video: async
- List model: `GET /v1/models`
- Billing (OpenAI-style): `GET /v1/dashboard/billing/subscription` (giới hạn) · `GET /v1/dashboard/billing/usage` (đã dùng). Số dư thật xem dashboard web.

## 8. Bypass / độ bền (nhẹ hơn v98, giữ vài cái cho chắc)
cheapkeyai KHÔNG inject persona nên **không bắt buộc** bọc XML / prefill như v98. Nhưng vẫn nên giữ:
1. **Timeout ≥ 90s** (vision/thinking để 180s).
2. **Refusal-retry** (max 3): nếu 400 ký tự đầu chứa `("I cannot","I can't","I'm sorry","请求内容过大")` → retry / giảm ảnh.
3. **`finish_reason=="length"`** → gấp đôi `max_tokens` (trần 65536) rồi retry.
4. Web nhiều job: `Semaphore(1-10)` + tự backoff `429` (đợi ×3).
5. Ảnh quá lớn (`请求内容过大` / context) → giảm scale/quality ảnh (project iloveus dùng 300dpi crop → scale 1.0 q75 ~4-20k token/lượt).

## 9. Lỗi thường gặp
`401` key sai · `402` hết tiền (nạp) · `429` rate limit (backoff ×3) · `503` quá tải / model đang migrate · `httpx.TimeoutException` tăng timeout/đổi model nhẹ.

## 10. TÍNH TIỀN & SỐ DƯ — chuẩn New API (đã nghiên cứu + kiểm chứng thật 2026-07)

cheapkeyai chạy trên **New API** (lỗi trả về ghi `new_api_error`). Có 2 lớp:
- **Key `sk-...`**: chỉ gọi `/v1/*` (chat/image/...) + `/v1/dashboard/billing/*`. **KHÔNG đọc được số dư.**
- **Access token** (lấy ở dashboard web: Personal settings → Access Token, KHÁC key `sk-`): đọc tài khoản qua `/api/user/self`. Cần kèm header **`New-Api-User: <user_id>`** (user id xem trong dashboard).

### 10.1 Đơn vị quota (KIỂM CHỨNG, không phải đoán)
- **`500000` quota = `$1`** (hằng `quota_per_unit` mặc định của New API).
- `/v1/dashboard/billing/usage` trả `total_usage` đơn vị **CENT** (÷100 = USD).
- Kiểm chứng chéo: `used_quota / total_usage = 5000` đúng khít (69092/13.8184=5000) → 2 endpoint cùng ra 1 giá trị USD. Đây là cách VERIFY khi nghi đơn vị.

### 10.2 Số dư thật (USD)
```
GET {host}/api/user/self
  Header: Authorization: <ACCESS_TOKEN>        # KHÔNG có chữ "Bearer"
          New-Api-User: <USER_ID>
→ data.quota (còn lại), data.used_quota (đã dùng)   # đơn vị quota
số dư USD = data.quota / 500000
```

### 10.3 Chi phí 1 request — CÔNG THỨC (kiểm chứng khớp tuyệt đối)
```
quota = (prompt_tokens + completion_tokens × completion_ratio) × model_ratio × group_ratio
cost_USD = quota / 500000
```
- `model_ratio`, `completion_ratio`, `group_ratio` lấy từ `GET /api/pricing` (kèm access token + New-Api-User). `group_ratio` theo group của user (`/api/user/self` field `group`, thường `default` → 1).
- Suy ra **giá per 1M token** cho tiện: `giá_input = model_ratio × group_ratio × $2/1M`; `giá_output = giá_input × completion_ratio`.
- **Đo thật kiểm chứng** (opus-4-8, mr=0.25, cr=1, group=1): 559 prompt + 372 completion → công thức (559+372)×0.25 = **232.75**, quota tiêu thật đo được = **233** ✅ khớp.

### 10.4 Bảng giá vài model (từ /api/pricing, USD per 1M in/out)
| Model | model_ratio | completion_ratio | Giá in /1M | Giá out /1M |
|---|---|---|---|---|
| claude-opus-4-8 | 0.25 | 1 | $0.50 | $0.50 |
| claude-sonnet-4-6 | 0.1825 | 1 | $0.365 | $0.365 |
| deepseek-v3.1 | 2 | 3 | (theo group Self-Deploy, xem /api/pricing) | |
> ⚠️ Giá cheapkeyai RẺ BẤT THƯỜNG (opus $0.5/1M) so với giá gốc hãng — nhớ tính theo ratio thật, ĐỪNG bê giá hãng hay giá v98 cũ (5/25) vào.

### 10.5 Quy đổi VND
`VND = cost_USD × tỷ_giá_VCB_bán_ra`. **KHÔNG chia /8** — cái `/8` là fudge đời v98 (đơn vị quota v98 khác), cheapkeyai `quota/500000` đã ra USD thật.

### 10.6 Cách VERIFY khi thêm/đổi model mới (quy trình chuẩn)
1. `GET /api/pricing` → lấy `model_ratio`, `completion_ratio`, `group_ratio` của model.
2. Đọc `used_quota` (`/api/user/self`) TRƯỚC.
3. Gọi 1 request, lấy `usage.prompt_tokens` + `completion_tokens` từ response.
4. Đọc `used_quota` SAU → `Δquota`.
5. So `Δquota` với `(prompt + completion×completion_ratio)×model_ratio×group_ratio`. Khớp (±ceil) = công thức đúng → `cost_USD = Δquota/500000`.
6. Nếu KHÔNG khớp: có thể là `quota_type: 1` (tính theo lần gọi, `model_price` cố định thay vì ratio) — xem field `model_price` / `quota_type` trong /api/pricing.

## Checklist tích hợp
```
1. .env: CHEAP_API_KEY + CHEAP_BASE_URL (endpoint cuối /v1) — KHÔNG commit key
2. pip install openai httpx; AsyncOpenAI(api_key, base_url, timeout=120)
3. client.chat.completions.create(model, messages) → choices[0].message.content
4. Vision: nhét image_url base64 vào content list
5. Timeout ≥90s · refusal-retry · finish_reason=length → gấp đôi max_tokens
6. Balance: /v1/dashboard/billing/* (OpenAI-style) hoặc xem dashboard web
```
