---
name: google-oauth
description: Kích hoạt khi tích hợp đăng nhập Google vào dự án Next.js (Google Login, Sign in with Google, social login, đăng nhập mạng xã hội). Dùng cho cấu hình NextAuth.js / Auth.js, OAuth 2.0, OAuth consent screen, Google Cloud Console credentials, authentication/session, hoặc fix lỗi redirect_uri_mismatch, access_denied, brand verification.
---

# Google OAuth — Đăng nhập Google (NextAuth.js)

> Skill ngữ cảnh tự kích hoạt. Chi tiết đầy đủ: `docs/universal_rules/rules/GOOGLE_OAUTH_SETUP.md`.
> Guide dùng NextAuth.js **v4** (`next-auth`). Auth.js **v5** (`next-auth@beta`) có API khác → xem authjs.dev.

## Khi nào dùng skill này
- Thêm "Đăng nhập với Google" vào app Next.js (App Router).
- Cấu hình Google Cloud Console: project, OAuth consent screen, credentials.
- Setup NextAuth.js: `auth.ts`, route handler, `SessionProvider`, `getServerSession`.
- Debug lỗi OAuth: `redirect_uri_mismatch`, `access_denied`, session rỗng, avatar không load.
- Mở giới hạn 100 test users → publish app / brand verification.

## Checklist cốt lõi (bắt buộc)

### Google Cloud Console (`console.cloud.google.com`)
- [ ] Tạo project → chọn project đó.
- [ ] **OAuth consent screen** TRƯỚC khi tạo credentials. User Type = **External**. Điền: App name, User support email, Authorized domains (vd `example.com`, KHÔNG có `https://`), Developer contact email.
- [ ] Scopes: chỉ cần `email` + `profile` (có sẵn) → không xin thêm để khỏi phải verify.
- [ ] **Credentials** → Create OAuth client ID → Application type = **Web application**.
- [ ] **Authorized JavaScript origins**: `https://yourdomain.com`, `https://demo...`, `http://localhost:3000`.
- [ ] **Authorized redirect URIs** (PHẢI chính xác, KHÔNG trailing slash): mỗi domain thêm `.../api/auth/callback/google`.
- [ ] Copy **Client ID** + **Client Secret**.

### Environment variables (mọi environment: prod + demo)
- [ ] `NEXTAUTH_URL` = URL đầy đủ của app, KHÔNG trailing slash (demo phải dùng URL demo, không phải prod).
- [ ] `NEXTAUTH_SECRET` ≥ 32 ký tự: `openssl rand -base64 32`.
- [ ] `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.

### Code (Next.js App Router)
- [ ] Cài `next-auth` (+ `@next-auth/prisma-adapter` nếu lưu DB).
- [ ] `src/lib/auth.ts`: export `authOptions: NextAuthOptions` với `GoogleProvider({ clientId, clientSecret })`. `session: { strategy: 'jwt' }` (hoặc `'database'` nếu dùng adapter). Callbacks `session`/`jwt` để gắn `session.user.id = token.sub`. `signIn` callback để chặn login có điều kiện (return true/false/'/error').
- [ ] `src/app/api/auth/[...nextauth]/route.ts`: `const handler = NextAuth(authOptions); export { handler as GET, handler as POST }`.
- [ ] Wrap app bằng `<SessionProvider>` (layout/providers).
- [ ] Nút login: `signIn('google', { callbackUrl: '/dashboard' })` / `signOut()` / `useSession()`.
- [ ] Server: `const session = await getServerSession(authOptions)`.
- [ ] TypeScript: thêm `src/types/next-auth.d.ts` augment `Session.user` có `id` (mặc định không có).

### Prisma (nếu lưu user)
- [ ] Dùng `PrismaAdapter(prisma)` HOẶC tự create/update user trong callback `signIn`.
- [ ] Model `User` (id, email @unique, name, image avatar, emailVerified...). PrismaAdapter cần thêm `Account` + `Session` + `VerificationToken`.

### Go live
- [ ] Test login bằng tài khoản Google thật (cả prod + demo).
- [ ] Publish app: consent screen → **Publish App** → In production (chỉ basic scopes thì KHÔNG cần verify, mở cho mọi user).

## Cạm bẫy / lỗi hay gặp
- **`redirect_uri_mismatch`** (lỗi #1): redirect URI không khớp tuyệt đối → thêm đúng từng URL kể cả `http://localhost:3000/api/auth/callback/google`, không trailing slash.
- **`Error 403: access_denied`**: app đang **Testing**, email chưa nằm trong Test users (tối đa 100) → thêm email HOẶC publish app.
- **Session rỗng / login xong vẫn chưa đăng nhập**: `NEXTAUTH_URL` sai domain hoặc thiếu `NEXTAUTH_SECRET`.
- **Cookie không set trên demo**: `NEXTAUTH_URL` của demo vẫn trỏ prod → sửa trong `.env` demo.
- **`OAuthSignin` / `OAuthCallback`**: `GOOGLE_CLIENT_ID`/`SECRET` sai → copy lại.
- **Avatar Google không load**: thêm `lh3.googleusercontent.com` vào `images.remotePatterns` trong `next.config`.
- **Brand verification**: chỉ cần khi có sensitive/restricted scopes hoặc bị flag. Khi đó verify domain qua Search Console (TXT/HTML), Privacy Policy + Homepage hosted trên domain đã verify. Authorized domain phải khớp domain verify.

## Verify trước khi báo xong
- [ ] Redirect URI trong Console khớp 100% với `NEXTAUTH_URL` + `/api/auth/callback/google` của từng environment.
- [ ] 4 env vars có đủ ở mọi environment, `NEXTAUTH_URL` đúng từng nơi.
- [ ] Đã test login bằng Google account thật, có session, có `session.user.id`.
- [ ] Nếu cần mở public: đã Publish App (Testing → In production).
