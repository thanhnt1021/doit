---
name: cheapkeyai
description: Kích hoạt khi tích hợp AI/LLM qua proxy cheapkeyai.shop (OpenAI-compatible, nền New API) — gọi Claude/GPT/Gemini/Grok/DeepSeek bằng 1 SDK openai duy nhất. User thường nói "gọi AI qua cheapkeyai", "cheapapikey", "thêm chatbot AI", "dịch bằng AI", "tính tiền AI / số dư còn bao nhiêu", hoặc migrate từ v98store (đã chết). Trigger vi+en - cheapkeyai, cheapapikey, New API, OpenAI-compatible proxy, base_url /v1, AsyncOpenAI, số dư balance /api/user/self, pricing model_ratio, cost tracking USD→VND, image generation, thinking model, migrate v98store.
---

# cheapkeyai.shop — Gọi AI/LLM qua proxy OpenAI-compatible

> Skill ngữ cảnh, self-contained. Chi tiết đầy đủ (billing, verify model mới, image) ở file kèm **`CHEAPKEYAI-Guide.md`** cùng thư mục.
> **Kế thừa & thay v98store** (đã đóng cửa 2026-07). Cả hai đều chạy nền **New API** nên cách tính tiền giống nhau; khác lớn: cheapkeyai **KHÔNG inject persona** → không cần bypass gắt.

## Khi nào dùng
- Thêm AI vào bot/web (chat, dịch, phân tích) — gọi Claude/GPT/Gemini/Grok/DeepSeek qua **1 SDK `openai`**.
- Cần đọc **số dư tài khoản** hoặc **tính chi phí** mỗi request.
- Migrate project cũ từ v98store sang cheapkeyai.

## 1. cheapkeyai là gì
`https://cheapkeyai.shop` = **proxy trung gian OpenAI-compatible** (nền New API). Dùng SDK `openai`, trỏ `base_url` sang cheapkeyai → 1 SDK gọi mọi model, billing 1 chỗ. **Endpoint cuối PHẢI có `/v1`.**

## 2. Recipe cơ bản (Python)
```bash
pip install openai httpx      # KHÔNG cần anthropic/google-generativeai
```
```python
import os, httpx
from openai import AsyncOpenAI   # Async cho bot/web (tránh block event loop)

api_key = os.getenv("CHEAP_API_KEY")           # sk-xxx... — ĐỌC .env, KHÔNG hardcode
raw = os.getenv("CHEAP_BASE_URL", "https://cheapkeyai.shop")
base_url = raw if raw.endswith("/v1") else f"{raw.rstrip('/')}/v1"   # endpoint cuối PHẢI /v1
client = AsyncOpenAI(api_key=api_key, base_url=base_url,
                     http_client=httpx.AsyncClient(timeout=120.0))   # 60s mặc định quá ngắn

resp = await client.chat.completions.create(
    model="claude-sonnet-4-6", messages=messages,
    temperature=0.7, max_tokens=2048, timeout=90.0)
text = resp.choices[0].message.content
```
- **`.env`** (KHÔNG commit): `CHEAP_API_KEY=sk-xxx...` · `CHEAP_BASE_URL=https://cheapkeyai.shop`. Đọc số dư cần thêm `CHEAP_ACCESS_TOKEN` + `CHEAP_USER_ID` (xem §4).
  - _Project migrate từ v98 giữ tên biến `V98_API_KEY`/`V98_BASE_URL` (chỉ đổi VALUE) để đỡ sửa code — chấp nhận được._
- Model hay dùng (xác thực `GET /v1/models`): `claude-sonnet-4-6` (nhanh/rẻ) · `claude-opus-4-8` (nặng, vision) · `deepseek-v3.1` (rẻ, dịch/tác vụ phụ — `deepseek-v3.2` hay flaky) · `gemini-3.5-flash`.
  ⚠️ Model trên cheapkeyai **flaky theo kênh** — có model lúc chạy lúc "可用渠道不存在". Test vài lần trước khi chọn làm default; giữ retry/backoff.

## 3. Bypass — NHẸ (khác hẳn v98)
cheapkeyai **KHÔNG inject persona Kiro** → hỏi "bạn là model gì" trả lời "Tôi là Claude" bình thường. Vì vậy **dùng `role: system` CHUẨN, KHÔNG nhét system vào user, KHÔNG assistant-prefill** — mấy hack đời v98 trên cheapkeyai còn gây **leak prompt/prefill ra đầu output**. Chỉ giữ vài lớp bền bỉ:
1. **Timeout ≥ 90s** (vision/thinking 180s).
2. **finish_reason=="length"** → gấp đôi `max_tokens` (trần 65536) rồi retry.
3. Web nhiều job: `Semaphore` + tự backoff `429` (đợi ×3). `max_retries=0` ở SDK để tự quản.
4. (Tuỳ chọn) refusal-retry nếu 400 ký tự đầu chứa `("I cannot","I'm sorry")`.

## 4. Số dư + CHI PHÍ (New API — chuẩn, đã kiểm chứng)
Key `sk-` KHÔNG đọc được số dư. Cần **access token** (lấy ở dashboard, KHÁC key sk-) + header `New-Api-User: <user_id>`:
```python
# Số dư USD còn lại
r = httpx.get(f"{host}/api/user/self",
              headers={"Authorization": ACCESS_TOKEN, "New-Api-User": str(USER_ID)})
balance_usd = r.json()["data"]["quota"] / 500000      # 500000 quota = $1 (đã verify)
```
**Chi phí 1 request** (đọc ratio từ `GET /api/pricing`):
```
quota = (prompt_tokens + completion_tokens × completion_ratio) × model_ratio × group_ratio
cost_USD = quota / 500000        # giá per 1M = model_ratio × $2
```
- Đo thật kiểm chứng: opus-4-8 (mr=0.25, cr=1) → $0.5/1M in+out. VD 559+372 token = 233 quota = khớp.
- **VND**: `cost_USD × tỷ_giá_VCB` (lấy **max** sell/transfer/buy, fetch live cache ngắn — **KHÔNG hardcode, KHÔNG chia /8** như v98 xưa).
- `total_usage` ở `/v1/dashboard/billing/usage` là **CENT** (÷100 = USD) — dùng verify chéo.
- Cost cộng DỒN, không reset: lưu DB sau mỗi chunk; resume load `prev_cost`. Dùng `(d.get("cost") or 0)`.
> Quy trình VERIFY model mới + bảng giá đầy đủ: xem `CHEAPKEYAI-Guide.md` Mục 10.

## 5. Ảnh / Vision / TTS
- **Vision (đọc ảnh)** OK: nhét `image_url` base64 vào `content` list (OpenAI multimodal), model `claude-opus-4-8`.
- **Sinh ảnh**: `POST {base_url}/images/generations`. Trên cheapkeyai nhiều model ảnh "không có kênh" — hiện chỉ `grok-imagine-image(-pro)` chạy (không nude). Kiểm bằng `/v1/models` trước.
- **TTS**: hiện cheapkeyai **chưa có model TTS chạy được** (tts-1/speech-*/gemini-tts đều 500/503) — kiểm lại trước khi hứa tính năng giọng đọc.

## 6. Lỗi thường gặp
`401` key/token sai · `402` hết tiền (nạp ở dashboard) · `429` rate limit (backoff ×3) · `503`/"可用渠道不存在" model đang thiếu kênh (đổi model/thử lại) · `httpx.TimeoutException` tăng timeout.

## Checklist tích hợp
```
1. .env: CHEAP_API_KEY + CHEAP_BASE_URL (/v1) [+ CHEAP_ACCESS_TOKEN + CHEAP_USER_ID nếu cần số dư] — KHÔNG commit
2. AsyncOpenAI(api_key, base_url, timeout=120); dùng role:system CHUẨN (không bypass v98)
3. client.chat.completions.create(model, messages) → choices[0].message.content
4. Cost: (prompt + completion×completion_ratio)×model_ratio×group_ratio /500000; VND × rate VCB max live
5. Số dư: /api/user/self (access token + New-Api-User) → quota/500000
6. Model flaky → test trước + giữ retry; timeout≥90s; finish_reason=length → gấp đôi max_tokens
```
