---
name: seo-geo
description: Kích hoạt khi làm SEO/GEO cho web — lên Google, được AI (ChatGPT/Perplexity/AI Overviews) trích dẫn, xử canonical/www, sitemap, robots.txt, schema JSON-LD, og:image. CŨNG bật khi DỰNG/LAUNCH website mới (mọi web PHẢI có OG share card + title trước khi ship). Trigger vi+en - SEO, GEO, canonical, sitemap, robots, schema, og, og image, share card, "chia sẻ link mất ảnh/sai tiêu đề", "dựng website mới", "launch site", "trang đã xoá vẫn còn trên Google", "sao chưa index Google", meta description, rich result, Google Search Console, Google Business Profile.
---

# SEO + GEO — Tối ưu tìm kiếm & AI citation

> Skill ngữ cảnh tự kích hoạt & self-contained.
> **Sinh từ sự cố thật:** `www` báo 522 vì proxied vào origin chết + chưa là Pages custom domain; og:title share sai vì tách khỏi `<title>`; trang đã xoá vẫn hiện trên Google do soft-404; bot AI no-JS mù internal link vì nav render bằng JS.

## Nguyên tắc bất biến
- **MỌI website khi ship PHẢI có OG share card** (không đợi nhắc): `og:image` 1200×630 URL tuyệt đối + `og:title` + `og:description` + `og:type=website` + `og:url` + `twitter:card=summary_large_image`. Thiếu = gửi link ra card trống = CHƯA XONG. Chi tiết §2.
- **1 canonical host DUY NHẤT** (apex `example.com` HOẶC `www.example.com`). MỌI tín hiệu trỏ về nó: `<link rel=canonical>`, `og:url`, sitemap, internal link.
- **SEO ≠ GEO.** SEO = Google xếp hạng. GEO = AI trích dẫn (cần text thật trong HTML + schema + robots cho AI-citation bot). Tối ưu **cả hai**.
- **SEO on-page KHÔNG đổi UI/UX** — chỉ thêm meta/schema/`<noscript>` ẩn. Đổi pixel nào = sai scope.
- Verify bằng số thật (`curl -I` / `dig` / `site:domain`), KHÔNG đoán; cache-bust khi đo (`?z=$RANDOM`).

## 1. Canonical host (www vs non-www)
- Chọn 1 host chính. Host kia: **301 redirect** về host chính, HOẶC **cả 2 serve 200 + canonical tag tuyệt đối → host chính**.
- **Cloudflare Pages — `www` báo 522:** `www` proxied (đám mây cam) nhưng **chưa thêm làm Pages custom domain** / DNS trỏ origin chết. Sửa:
  - **Muốn www serve site:** DNS record `www` = `CNAME → <project>.pages.dev` (Proxied) + thêm `www` vào **Pages → Custom domains**. Cả apex + www sẽ Active.
  - **Muốn www chỉ redirect:** tạo **Redirect Rule** ở edge (`http_request_dynamic_redirect`): match `http.host eq "www..."` → 301 `concat("https://apex", http.request.uri.path)`, **Dynamic + preserve query**. Chạy trước origin nên diệt 522 luôn.
  - ⚠️ Redirect rule khớp `www` sẽ **chặn Pages verify** custom domain `www` (Pages probe bị 301) → muốn www serve thì **gỡ rule** rồi mới Active được.

## 2. On-page meta — MỖI trang public phải đủ khối này
Template `<head>` chuẩn (unique nội dung/trang):
```html
<title>…</title>                          <!-- unique, ≤60 ký tự, có brand -->
<meta name="description" content="…">     <!-- unique/trang, ~120-160 ký tự -->
<link rel="canonical" href="https://HOST/path">   <!-- TUYỆT ĐỐI, canonical host -->
<meta name="robots" content="index, follow, max-image-preview:large">  <!-- hoặc noindex, nofollow -->
<!-- Open Graph -->
<meta property="og:type" content="website">
<meta property="og:site_name" content="…">
<meta property="og:locale" content="vi_VN">
<meta property="og:title" content="…">        <!-- TÁCH khỏi <title>, xem dưới -->
<meta property="og:description" content="…">
<meta property="og:url" content="https://HOST/path">
<meta property="og:image" content="https://HOST/…absolute.jpg">
<!-- Twitter -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="…">
<meta name="twitter:description" content="…">
<meta name="twitter:image" content="https://HOST/…absolute.jpg">
<!-- slot verify (để sẵn, bỏ comment khi có token GSC) -->
<!-- <meta name="google-site-verification" content="…"> -->
```
- `og:title` **TÁCH khỏi `<title>`** — share card (FB/Zalo/Messenger) đọc `og:title`, KHÔNG đọc `<title>`. Homepage nên để `og:title` = brand-only. Sửa xong PHẢI **re-scrape** (developers.facebook.com/tools/debug → Scrape Again) — social cache OG rất lì. Warning `fb:app_id` = **bỏ qua**.
- `og:image` phải là **URL tuyệt đối** trên canonical host (không relative). Ảnh mất khi share thường do URL relative hoặc social cache cũ → re-scrape.
- `robots` = `noindex, nofollow` cho trang thin/legacy/admin.

## 2b. H1 — MỖI trang đúng 1 `<h1>` (điểm hay sót)
- **Mọi trang phải có đúng 1 `<h1>`** chứa tên/chủ đề trang. Nhiều `<h1>` → gộp 1 (dùng `<span>` cho dòng con).
- **Trang mà title là ẢNH/canvas/chữ tạo hình** (không có heading text thật) → thêm **`<h1>` ẩn sr-only** (crawler + screen-reader đọc được, mắt không thấy, **0 đổi UI**):
  ```html
  <h1 class="sr-only" style="position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0;">Tên trang mô tả rõ ràng</h1>
  ```
- Đặt ngay sau `<body>` (hoặc đầu content). Nội dung h1 ẩn = câu mô tả thật, KHÔNG nhồi keyword.

## 2c. JSON-LD schema (AI + rich result đọc cái này — GEO quan trọng)
Chọn `@type` theo loại trang, nhúng `<script type="application/ld+json">`:
| Trang | Schema |
|---|---|
| Toàn site (homepage) | `WebSite` + `Organization` / `EducationalOrganization` |
| Business có địa điểm | `LocalBusiness` + `PostalAddress` (NAP) + `City` |
| Trang khoá học/dịch vụ | `Course` (kèm provider, offers/giá nếu có) |
| Trang có Q&A | `FAQPage` (`Question` + `Answer`) |
| Blog listing / bài viết | `Blog` + `BlogPosting` |
- NAP trong schema (`PostalAddress`) phải **khớp chính xác** web ↔ GBP (§6).

## 3. Sitemap + robots.txt
- `sitemap.xml`: **chỉ canonical host**, URL sạch (không `.html`), có `<lastmod>`.
- `robots.txt`: **phải có dòng `Sitemap:`** (FULL URL). Chính sách GEO:
  - **Allow** search + AI-citation bot: `OAI-SearchBot`, `ChatGPT-User`, `PerplexityBot`, `Perplexity-User` (cho được trích dẫn).
  - **Disallow** AI-training crawler: `GPTBot`, `Google-Extended`, `ClaudeBot`, `anthropic-ai`, `CCBot`, `Bytespider`, `Amazonbot`, `Meta-ExternalAgent`... (chặn train miễn phí).
- Trang thin/legacy/admin → `noindex` qua header `X-Robots-Tag: noindex, nofollow` (`_headers` trên Pages).

## 4. GEO — bot AI (điểm KHÁC SEO thường)
- **Nav/footer render bằng JS → bot no-JS (nhiều AI crawler) MÙ internal link.** Thêm `<noscript>` chứa internal links tĩnh + NAP ngay sau `<body>`. **JS bật → `<noscript>` ẩn 100% (0 đổi UI)**; bot no-JS đọc được link.
- Nội dung phải là **text thật trong HTML**, không chỉ ảnh/canvas (AI không OCR).
- Schema + NAP rõ ràng để AI trích chính xác.

## 5. Google Search Console (GSC)
- **Domain property** phủ cả `www` + non-`www`. Submit sitemap = **FULL URL** (`https://host/sitemap.xml`) — Domain property không nhận đường dẫn tương đối.
- **"Đã phát hiện / đã thu thập – chưa lập chỉ mục" = độ trễ BÌNH THƯỜNG** (site nhỏ/mới crawl chậm), KHÔNG phải lỗi. Chỉ lo khi báo noindex/lỗi crawl.
- Request index: dùng URL **canonical**, **1 lần/URL** (bấm lại không nhanh hơn).
- **Live-test xanh ("có thể lập chỉ mục") ≠ đã index.** Kiểm tra thật: `site:domain` trên Google, hoặc tab "Chỉ mục của Google".

## 6. Google Business Profile (GBP) — local SEO (business có địa điểm)
- **NAP (Name/Address/Phone) KHỚP CHÍNH XÁC** giữa web ↔ schema LocalBusiness ↔ GBP. Lệch = yếu tín hiệu local.
- **Services** = sản phẩm/khoá **thật** (lấy tên + giá từ web), không để trống/generic.
- **Post định kỳ** (2–4 tuần/lần) → freshness; ảnh thật; mời review sao (đòn bẩy local + AI Overviews mạnh nhất).
- Bẫy: nút **"Complete info" / Profile strength** hay route sang **bán ads/mail** — bỏ qua, dùng nút **Edit profile / Edit services / Photos / Posts** cụ thể.

## 7. Xoá trang (deleted URL vẫn hiện trên Google)
- **Nguyên nhân:** (a) Google index CŨ chưa re-crawl; (b) Pages/SPA `not_found` serve **homepage 200** cho URL không tồn tại → **soft-404** → Google không thấy 404 để rớt.
- **Fix:** giữ `noindex` header cho path đã xoá (Google rớt khi re-crawl) + **GSC → Xóa URL** (Removal tool, dùng **tiền tố** để xoá loạt) + nếu cần airtight: trả **410 Gone** qua Pages Function/middleware cho path đã xoá.

## 8. Token cho thao tác infra (Cloudflare/DNS/CDN)
- **Least-privilege:** scope hẹp đúng việc (vd `DNS:Edit` + `Single Redirect:Edit` + `Zone:Read`) + **Specific zone** + **TTL ngắn**.
- Token nạp qua **FILE ngoài repo** (`umask 077 > ~/.cf_token`), **KHÔNG paste vào chat/transcript**, tham chiếu `$VAR`. **Revoke sau khi xong.**
- Tạo/sửa rule qua API = **append-only** (đọc ruleset hiện có rồi thêm), KHÔNG PUT đè cả ruleset.

## Bất biến
- Mọi tín hiệu (canonical/OG/sitemap/internal link) về **1 canonical host**.
- SEO on-page = **0 đổi UI/UX**.
- Verify bằng số thật (`curl`/`dig`/`site:`), không đoán; cache-bust khi đo.
