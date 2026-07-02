# GOAL

_Last reviewed: 2026-07-02_

## Mục tiêu cuối cùng
DoIt — Weekly Life Dashboard chạy production trên Cloudflare Pages tại `doit.jst4.fun`, dữ liệu đồng bộ mọi máy qua D1 (`doit-db`), auto-deploy từ GitHub `main`.

## Thành công trông như thế nào
- Site LIVE tại `doit.jst4.fun` (curl 200), auto-deploy khi push `main`.
- API `state`/`save` đọc-ghi D1 hoạt động (đồng bộ đa thiết bị, không chỉ localStorage).
- Đăng ký chế độ chạy đồng bộ qua D1 (`settings.run`) — đã làm 6/2026.

## KHÔNG phải mục tiêu
- Không mở rộng multi-user — dashboard cá nhân 1 người.
- Không đổi stack (giữ Pages + Functions + D1).

## Milestones
- [x] Scaffold Pages/Functions/D1 + deploy LIVE `doit.jst4.fun`.
- [x] Đồng bộ 'đăng ký chế độ chạy' qua D1 thay vì chỉ localStorage.
- [ ] (mở) Nhu cầu mới theo user giao.

## Pending / Cần Quyết Định
- [ ] Đổi mật khẩu seed mặc định nếu còn dùng `123456` (xem SECURITY_CHECKLIST 4.5 — không dùng chung credential giữa project).

## Hiện tại đang ở đâu
Site LIVE, ổn định. 2026-07-02: sync univ2 **2.1.0** từ SSOT mới `thanhnt1021/universal-workflow` (trước đó bản copy ở đây thiếu cả CLOUDFLARE_RULES.md dù doit là project Cloudflare gốc — đã có đủ sau sync). GOAL.md này được điền lần đầu từ template trong đợt audit univ2 (trước đó để placeholder).
