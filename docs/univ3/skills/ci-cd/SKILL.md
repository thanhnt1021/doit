---
name: ci-cd
description: Kích hoạt khi tạo pipeline CI/CD hoặc GitHub Actions tự động build/test/deploy. User thường nói "setup GitHub Actions", "tự động deploy khi push", "chạy test/lint trong CI", "deploy lên VPS qua SSH". Trigger vi+en - continuous integration, automation deploy, .github/workflows, ci.yml, Docker build push, pnpm/pytest/lint/typecheck trong workflow, GitHub Secrets.
---

# CI/CD — GitHub Actions templates

> Skill ngữ cảnh tự kích hoạt, self-contained (mọi nội dung nằm trong skill này).

## Khi nào dùng skill này
- Người dùng cần tạo / sửa file `.github/workflows/ci.yml`.
- Thiết lập pipeline tự động: lint, typecheck, test, build, security audit, deploy.
- Deploy lên VPS qua SSH, hoặc build & push Docker image rồi deploy.
- Cần SSH deploy pattern để deploy lên server tự host (skill **infra** lo phần server đích).

## Checklist cốt lõi (bắt buộc)
Chọn 1 trong 3 template theo stack:

- [ ] **Node.js/Next.js**: `pnpm/action-setup@v4` (v9) + `setup-node@v4` (cache pnpm) → `pnpm install --frozen-lockfile` → `pnpm run lint` → `pnpm exec tsc --noEmit` → `pnpm run build` → `pnpm run test --passWithNoTests`. Security: `pnpm audit --audit-level=high`.
- [ ] **Python**: `setup-python@v5` (cache pip) → `pip install -r requirements.txt` → `python -m py_compile [MAIN_FILE]` → `ruff check .` → `python -m pytest --tb=short -q`. Security: `pip-audit -r requirements.txt --strict`.
- [ ] **Docker**: `docker/login-action@v3` + `docker/build-push-action@v5` (tag `:latest` và `:${{ github.sha }}`). Security: `aquasecurity/trivy-action` quét CRITICAL,HIGH.

Chung cho mọi template:
- [ ] `on: push/pull_request` nhánh `main`.
- [ ] Job `deploy` có `needs: [check, security]` + điều kiện `if: github.ref == 'refs/heads/main' && github.event_name == 'push'`.
- [ ] Deploy dùng `appleboy/ssh-action@v1` với `secrets.SERVER_HOST`, `SERVER_USER`, `SSH_PRIVATE_KEY`.
- [ ] Setup GitHub Secrets: `SERVER_HOST`, `SERVER_USER`, `SSH_PRIVATE_KEY` (ed25519); thêm `DOCKER_USERNAME`, `DOCKER_TOKEN` nếu dùng Docker.
- [ ] Thay tất cả `[PLACEHOLDER]`: `[PROJECT_NAME]`, `[NODE_VERSION]`, `[PYTHON_VERSION]`, `[MAIN_FILE]`, `[SERVICE_NAME]`, `[DOCKER_USERNAME]`, `[PORT]`.

## Build MỘT lần rồi promote — đừng build lại cho từng môi trường
Có staging + production thì **build 1 artifact duy nhất**, kiểm ở staging, rồi **chép đúng artifact đó** sang prod. Build lại cho prod là vừa tốn gấp đôi, vừa mất bảo đảm "thứ đã kiểm chính là thứ đem chạy".

- [ ] **Không nhúng biến môi trường vào lúc build.** Next.js thay `process.env.NEXT_PUBLIC_*` bằng literal ngay lúc `next build` (cả bundle server) — mỗi giá trị khác nhau là một bản build khác nhau. Vite `import.meta.env.VITE_*`, CRA `REACT_APP_*` cũng vậy. Kiểm bằng `grep -o '^[A-Z_]*=' .env | grep -E 'NEXT_PUBLIC_|VITE_|REACT_APP_'` ở từng môi trường: **khác nhau chỗ nào là chỗ đó chặn dùng chung bản build**. Đổi sang biến không tiền tố, đọc phía server lúc CHẠY.
- [ ] **Build ở đường dẫn TRUNG LẬP**, đừng build trong thư mục của một môi trường rồi bê sang môi trường kia. Bundle có nhúng đường dẫn thư mục build (Next: `.next/server/**` — kiểm bằng `grep -rl "<đường-dẫn-build>" <distDir> | wc -l`). Build ở thư mục riêng dùng chung thì hai bên nhận đường dẫn giống hệt nhau, không bên nào phụ thuộc bên kia.
- [ ] **Giữ nguyên cổng staging.** Dùng chung artifact KHÔNG có nghĩa bỏ được lưới an toàn: thứ tự bắt buộc vẫn là promote staging → smoke → chỉ khi xanh mới promote prod. DB, `.env`, dữ liệu thật hai bên vẫn khác nhau.
- [ ] **Chờ app ấm sau khi reload rồi mới smoke.** `pm2 reload` / `systemctl reload` trả về ngay khi vừa ra lệnh, chưa đợi tiến trình mới nghe cổng → `curl` liền sau đó gặp 502 dù app hoàn toàn lành. Vòng chờ tới khi trả 200 (vài chục giây) chứ đừng kết luận gãy ngay.

## Cạm bẫy / lỗi hay gặp
- Kết luận "không dùng chung được bản build" khi mới thấy đường dẫn tuyệt đối trong bundle — phần lớn là **định danh module**, không phải chỗ đọc đĩa. Mổ theo nhóm tệp rồi mới kết luận.
- Quên `--frozen-lockfile` (Node) → cài lệch version so với lockfile.
- Để `deploy` chạy cả trên `pull_request` → deploy nhầm từ PR; phải kiểm tra `github.event_name == 'push'`.
- Còn sót `[PLACEHOLDER]` chưa thay → workflow fail hoặc deploy sai service.
- Thiếu GitHub Secrets → bước SSH/Docker fail xác thực.
- Dùng SSH key dạng password-protected hoặc RSA cũ; nên ed25519 không passphrase cho CI.
- Python deploy: quên `source venv/bin/activate` trước `pip install`/restart service.
- Không verify sau deploy → service chết âm thầm; thêm `systemctl is-active [SERVICE_NAME]`.

## Verify trước khi báo xong
- [ ] File đặt đúng `.github/workflows/ci.yml`, YAML hợp lệ (indent đúng).
- [ ] Không còn `[PLACEHOLDER]` nào.
- [ ] Đã liệt kê đủ Secrets cần tạo trong repo Settings.
- [ ] Job `deploy` có `needs` + `if` đúng để chỉ deploy từ push vào `main`.
- [ ] (Khuyến nghị) Push thử để workflow chạy, hoặc validate bằng `act`/lint YAML.
