# Google OAuth / Google Login — Universal Setup Guide

> **Dùng cho:** Bất kỳ dự án Next.js nào cần Google Login qua NextAuth.js.
> Bao gồm toàn bộ quy trình: Google Cloud Console → OAuth credentials → Brand verification → NextAuth config → Go live.
>
> **Lưu ý phiên bản:** Guide này dùng NextAuth.js **v4** (package `next-auth`). Nếu dùng Auth.js **v5** (package `next-auth@beta`), xem https://authjs.dev/getting-started — API config và callback patterns khác.

---

## 1. Tổng quan luồng

```
User bấm "Đăng nhập Google"
  → NextAuth redirect → Google OAuth consent screen
  → Google trả code về /api/auth/callback/google
  → NextAuth đổi code lấy access_token + id_token
  → Lấy profile (email, name, avatar)
  → Tạo/cập nhật user trong DB
  → Set session cookie → User đã đăng nhập
```

**Cần có:** Google Cloud Project + OAuth 2.0 Client ID + NextAuth.js config.

---

## 2. Google Cloud Console Setup

### Bước 1 — Tạo Project (nếu chưa có)

1. Vào `console.cloud.google.com`
2. Góc trên trái → dropdown project → **New Project**
3. Đặt tên project (ví dụ: tên website/app) → **Create**
4. Chọn project vừa tạo

### Bước 2 — Cấu hình OAuth Consent Screen *(làm trước khi tạo credentials)*

`APIs & Services` → `OAuth consent screen`:

| Field | Giá trị |
|-------|---------|
| User Type | **External** (cho phép mọi Google account đăng nhập) |

Bấm **Create**, điền form:

| Field | Bắt buộc | Ghi chú |
|-------|----------|---------|
| App name | ✅ | Tên hiển thị trên màn hình đồng ý của Google |
| User support email | ✅ | Email liên hệ hỗ trợ (Google gửi thông báo về đây) |
| App logo | ❌ | Nếu có → hiển thị logo trên consent screen |
| App domain | ❌ (cần để verify) | Trang chủ website, privacy policy URL, terms URL |
| Authorized domains | ✅ | Domain chính, ví dụ: `example.com` (không có https://) |
| Developer contact email | ✅ | Email của developer |

Bấm **Save and Continue**.

**Scopes:** Chỉ cần `email` + `profile` (đã có sẵn). Không cần thêm gì. Bấm **Save and Continue**.

**Test users:** Nếu app đang ở trạng thái **Testing**, chỉ những email trong danh sách này mới đăng nhập được (tối đa 100 người). Thêm email cần test vào đây.

### Bước 3 — Tạo OAuth 2.0 Credentials

`APIs & Services` → `Credentials` → **+ Create Credentials** → **OAuth client ID**:

| Field | Giá trị |
|-------|---------|
| Application type | **Web application** |
| Name | Tên tùy ý (ví dụ: `Web Client Production`) |

**Authorized JavaScript origins** — thêm:
```
https://yourdomain.com
https://demo.yourdomain.com   ← nếu có demo
http://localhost:3000          ← cho dev local
```

**Authorized redirect URIs** — thêm (PHẢI chính xác, bao gồm path):
```
https://yourdomain.com/api/auth/callback/google
https://demo.yourdomain.com/api/auth/callback/google
http://localhost:3000/api/auth/callback/google
```

**⚠️ Hay bị lỗi nhất:** Redirect URI không khớp chính xác → Google trả lỗi `redirect_uri_mismatch`. Phải thêm đúng từng URL, không có trailing slash.

Bấm **Create** → copy **Client ID** và **Client Secret**.

---

## 3. Environment Variables

```env
NEXTAUTH_URL=https://yourdomain.com      # URL đầy đủ của app (không trailing slash)
NEXTAUTH_SECRET=                          # Random string >= 32 chars: openssl rand -base64 32
GOOGLE_CLIENT_ID=                         # Từ Google Cloud Console
GOOGLE_CLIENT_SECRET=                     # Từ Google Cloud Console
```

**⚠️ Demo environment:** Nếu có server demo riêng, `NEXTAUTH_URL` trong `.env` của demo phải là URL demo (không phải production). Nếu sai → callback URL không khớp → login fail.

---

## 4. NextAuth.js Config (Next.js App Router)

### `src/lib/auth.ts`

```typescript
import { NextAuthOptions } from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'
import { PrismaAdapter } from '@next-auth/prisma-adapter' // nếu dùng Prisma
import prisma from './db'

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma), // optional — nếu muốn lưu session/user vào DB
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    async session({ session, token }) {
      // Thêm custom fields vào session
      if (token?.sub) session.user.id = token.sub
      return session
    },
    async jwt({ token, user, account, profile }) {
      if (user) token.sub = user.id
      return token
    },
    async signIn({ user, account, profile }) {
      // Optional: block đăng nhập theo điều kiện
      // return true để cho phép, return false hoặc '/error-page' để block
      return true
    },
  },
  session: { strategy: 'jwt' }, // 'database' nếu dùng adapter
  pages: {
    signIn: '/auth/login',      // Trang login tùy chỉnh (optional)
    error: '/auth/error',       // Trang lỗi (optional)
  },
}
```

### Type augmentation (bắt buộc nếu dùng TypeScript)

Mặc định `session.user` không có field `id`. Thêm file này để TypeScript không báo lỗi:

```typescript
// src/types/next-auth.d.ts
import { DefaultSession } from 'next-auth'

declare module 'next-auth' {
  interface Session {
    user: { id: string } & DefaultSession['user']
  }
}
```

### `src/app/api/auth/[...nextauth]/route.ts`

```typescript
import NextAuth from 'next-auth'
import { authOptions } from '@/lib/auth'

const handler = NextAuth(authOptions)
export { handler as GET, handler as POST }
```

### Nút đăng nhập (client component)

```tsx
'use client'
import { signIn, signOut, useSession } from 'next-auth/react'

export function GoogleLoginButton() {
  const { data: session } = useSession()
  if (session) return <button onClick={() => signOut()}>Đăng xuất</button>
  return (
    <button onClick={() => signIn('google', { callbackUrl: '/dashboard' })}>
      Đăng nhập với Google
    </button>
  )
}
```

### Wrap app với SessionProvider

```tsx
// src/app/layout.tsx hoặc providers.tsx
import { SessionProvider } from 'next-auth/react'

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  )
}
```

### Lấy session phía server

```typescript
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

const session = await getServerSession(authOptions)
if (!session) redirect('/auth/login')
```

---

## 5. Brand Verification — Để vượt giới hạn 100 test users

Khi app ở trạng thái **Testing**, chỉ 100 user trong whitelist mới đăng nhập được. Để mở cho mọi người:

### Cách 1: Publishing app (không cần verify nếu chỉ dùng basic scopes)

Nếu chỉ dùng scope `email` + `profile` (không xin thêm quyền như Gmail, Drive...):

`OAuth consent screen` → **Publishing status** → bấm **Publish App** → **Confirm**

→ App chuyển sang **In production**. Mọi Google account đều đăng nhập được. **Không cần verify brand.**

### Cách 2: Nếu Google yêu cầu verify (có sensitive/restricted scopes hoặc app bị flag)

Google sẽ yêu cầu:
1. **Verify domain:** `Google Search Console` → thêm domain → verify ownership (thêm TXT record vào DNS hoặc upload file HTML)
2. **Privacy Policy URL:** Phải là trang thật, có nội dung rõ ràng, hosted trên domain đã verify
3. **Homepage URL:** Phải trên domain đã verify
4. **App logo:** (optional nhưng khuyến nghị)
5. Submit review → Google xét duyệt (có thể mất vài ngày đến vài tuần)

**⚠️ Lưu ý về Domain Verification:**

Authorized domain trong OAuth consent screen phải khớp với domain đã verify trong Search Console. Ví dụ nếu domain là `example.com`, cần verify `example.com` (không cần verify `www.example.com` riêng).

---

## 6. Prisma Schema (nếu lưu user vào DB)

Nếu không dùng PrismaAdapter, tự tạo/cập nhật user trong callback `signIn`:

```prisma
model User {
  id            String    @id @default(cuid())
  email         String?   @unique
  name          String?
  image         String?   // Avatar URL từ Google
  emailVerified DateTime? @map("email_verified")
  createdAt     DateTime  @default(now())
  // ... các fields custom của project
}

// Nếu dùng PrismaAdapter, cần thêm Account + Session + VerificationToken models
// Xem: https://authjs.dev/reference/adapter/prisma
```

---

## 7. Các lỗi hay gặp

| Lỗi | Nguyên nhân | Fix |
|-----|-------------|-----|
| `redirect_uri_mismatch` | URI trong Google Console không khớp chính xác với callback URL | Thêm đúng URL vào Authorized redirect URIs, bao gồm cả http://localhost |
| `Access blocked: This app's request is invalid` | OAuth consent screen chưa được cấu hình đúng | Kiểm tra lại App domain, authorized domains |
| `Error 403: access_denied` | User không nằm trong Test users (khi app đang Testing) | Thêm email vào Test users HOẶC Publish app |
| Login thành công nhưng session không có | `NEXTAUTH_URL` sai, hoặc thiếu `NEXTAUTH_SECRET` | Kiểm tra `.env`, đảm bảo đúng domain |
| Cookie không được set trên demo | `NEXTAUTH_URL` trong demo `.env` vẫn trỏ về production | Sửa `NEXTAUTH_URL` trong file `.env` của demo |
| `OAuthSignin` / `OAuthCallback` error | `GOOGLE_CLIENT_ID` hoặc `GOOGLE_CLIENT_SECRET` sai | Copy lại từ Google Console |
| Avatar Google không load | CSP hoặc `next.config` chặn domain `lh3.googleusercontent.com` | Thêm vào `images.domains` hoặc `images.remotePatterns` trong `next.config` |

```javascript
// next.config.js — fix avatar Google
module.exports = {
  images: {
    remotePatterns: [{ hostname: 'lh3.googleusercontent.com' }],
  },
}
```

---

## 8. Checklist triển khai

### Google Cloud Console
- [ ] Tạo project
- [ ] Cấu hình OAuth consent screen (app name, email, authorized domain)
- [ ] Thêm `email` + `profile` scopes
- [ ] Tạo OAuth 2.0 credentials (Web application)
- [ ] Thêm đủ Authorized JavaScript origins (production + demo + localhost)
- [ ] Thêm đủ Authorized redirect URIs (`/api/auth/callback/google` cho từng domain)
- [ ] Copy Client ID + Client Secret

### Code
- [ ] Cài package: `next-auth` (+ `@next-auth/prisma-adapter` nếu cần)
- [ ] Tạo `src/lib/auth.ts` với GoogleProvider
- [ ] Tạo `src/app/api/auth/[...nextauth]/route.ts`
- [ ] Wrap app với `SessionProvider`
- [ ] Thêm 4 env vars vào tất cả environments (production + demo)
- [ ] Kiểm tra `NEXTAUTH_URL` đúng với từng environment

### Go live
- [ ] Test login với tài khoản Google thật
- [ ] Test trên cả production và demo (nếu có)
- [ ] Publish app (Testing → In production) để mở cho mọi user
- [ ] (Nếu bị yêu cầu) Verify domain + privacy policy + submit review
