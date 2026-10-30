// nghiem_thu_mo_trang.cjs — MỞ TRANG THẬT rồi tìm chuỗi/khối founder yêu cầu.
//
// WHY tệp Node riêng chứ không viết trong hook Python: bằng chứng "đã xong" mà founder
// chốt là NHÌN THẤY TRÊN WEB, mà web này là Next.js — nhiều khối render ở trình duyệt,
// `curl` HTML thô không thấy chữ. Playwright chỉ có trong `node_modules` của DỰ ÁN, còn
// hook nằm ngoài cây dự án nên `import '@playwright/test'` không giải được -> nạp qua
// `createRequire` trỏ thẳng `package.json` của dự án.
//
// Cách đăng nhập chép ĐÚNG cách các worker đã dùng (không phát minh lại):
// docs/handoff/backup-w210/w210-chup-anh.mjs:22-26.
//
// Vào : argv[2] = đường dẫn tệp JSON {du_an, base[], login_path, email_env, pass_env,
//                                     tieu_chi[{url,phai_thay,khoi}], timeout_ms}
// Ra  : JSON ra stdout {ket_qua:[{i_tieu_chi, trang_thai, url_that, bang_chung, ly_do}]}
//       MỘT phần tử cho MỖI (tiêu chí × base) — mở HẾT base, không dừng ở base đầu (P085/F8)
//       trang_thai: 'dat' | 'khong-dat' | 'khong-kiem-duoc'
// LUẬT: mở không được thì trả 'khong-kiem-duoc' — TUYỆT ĐỐI không bao giờ trả 'dat'.
const fs = require('fs')
const path = require('path')
const { createRequire } = require('module')

const vaoP = process.argv[2]
const cfg = JSON.parse(fs.readFileSync(vaoP, 'utf8'))
const TIMEOUT = cfg.timeout_ms || 25000

function ra(ketQua) {
  process.stdout.write(JSON.stringify({ ket_qua: ketQua }, null, 1))
}

function docEnv(duAn) {
  const p = path.join(duAn, '.env')
  if (!fs.existsSync(p)) return {}
  return Object.fromEntries(
    fs.readFileSync(p, 'utf8').split('\n')
      .filter((d) => /^[A-Z0-9_]+=/.test(d))
      .map((d) => [d.slice(0, d.indexOf('=')), d.slice(d.indexOf('=') + 1).replace(/^"|"$/g, '')])
  )
}

function napChromium(duAn) {
  const thu = [path.join(duAn, 'package.json'), path.join(process.cwd(), 'package.json')]
  for (const p of thu) {
    try {
      const req = createRequire(p)
      return req('@playwright/test').chromium
    } catch (e) { /* thử chỗ kế */ }
  }
  try { return require('playwright').chromium } catch (e) { /* hết đường */ }
  return null
}

;(async () => {
  const tieuChi = cfg.tieu_chi || []
  const chromium = napChromium(cfg.du_an || process.cwd())
  if (!chromium) {
    return ra(tieuChi.map(() => ({
      trang_thai: 'khong-kiem-duoc', url_that: '', bang_chung: '',
      ly_do: 'không nạp được Playwright (thiếu node_modules/@playwright/test của dự án)',
    })))
  }
  const env = docEnv(cfg.du_an || process.cwd())
  const EMAIL = env[cfg.email_env || 'DEMO_LOGIN_EMAIL']
  const PASS = env[cfg.pass_env || 'DEMO_ADMIN_PASSWORD']
  // login_path === '' = trang công khai, không cần tài khoản -> đừng đòi creds.
  if (cfg.login_path !== '' && (!EMAIL || !PASS)) {
    return ra(tieuChi.map(() => ({
      trang_thai: 'khong-kiem-duoc', url_that: '', bang_chung: '',
      ly_do: `thiếu ${cfg.email_env}/${cfg.pass_env} trong ${cfg.du_an}/.env — chưa đăng nhập được`,
    })))
  }

  let browser = null
  const ketQua = tieuChi.map(() => null)
  try {
    browser = await chromium.launch()
    const cacBase = cfg.base && cfg.base.length ? cfg.base : []
    // Một context cho mỗi base, đăng nhập MỘT lần rồi dùng lại cho mọi tiêu chí.
    const ctxTheoBase = {}
    async function layTrang(base) {
      if (ctxTheoBase[base]) return ctxTheoBase[base]
      const ctx = await browser.newContext({ viewport: { width: 1440, height: 1200 } })
      const page = await ctx.newPage()
      // login_path rỗng = trang không cần đăng nhập (ca thử cục bộ, trang công khai).
      if (cfg.login_path === '') { ctxTheoBase[base] = page; return page }
      await page.goto(base + (cfg.login_path || '/login'), { waitUntil: 'domcontentloaded', timeout: TIMEOUT })
      await page.fill('input[name="username"], input[name="email"], input[type="email"]', EMAIL)
      await page.fill('input[type="password"]', PASS)
      await page.click('button[type="submit"]')
      await page.waitForLoadState('networkidle', { timeout: TIMEOUT }).catch(() => {})
      if (/\/login/.test(page.url())) throw new Error('đăng nhập không qua, vẫn đứng ở ' + page.url())
      ctxTheoBase[base] = page
      return page
    }

    for (let i = 0; i < tieuChi.length; i++) {
      const tc = tieuChi[i]
      const tuyetDoi = /^https?:\/\//i.test(tc.url || '')
      const dsBase = tuyetDoi ? [''] : cacBase
      if (!dsBase.length) {
        ketQua[i] = [{ trang_thai: 'khong-kiem-duoc', url_that: '', bang_chung: '',
          ly_do: 'chưa cấu hình base URL cho dự án này' }]
        continue
      }
      // P085/F8 (09/09/2026) — CHẠY HẾT MỌI BASE, KHÔNG `break` Ở BASE ĐẦU TIÊN.
      // WHY: bản cũ đặt `xong = true; break` ngay khi khớp, mà cấu hình xếp demo TRƯỚC
      // prod -> prod KHÔNG BAO GIỜ được mở (đo thật: 25/25 tệp sổ không có một dòng prod
      // nào). Hệ quả: điều kiện "đã lên prod" chỉ chứng minh được demo — đúng cái founder
      // bực. Nay mỗi base một phần tử bằng chứng riêng, và phán quyết ở `nghiem_thu_gate`
      // (`all(trang_thai == 'dat')`) tự thành "ĐẠT KHI TẤT CẢ BASE ĐỀU THẤY".
      const phanTu = []
      for (const base of dsBase) {
        const url = tuyetDoi ? tc.url : base + (tc.url || '/')
        let page
        try {
          page = tuyetDoi ? await layTrang(new URL(tc.url).origin) : await layTrang(base)
        } catch (e) {
          phanTu.push({ trang_thai: 'khong-kiem-duoc', url_that: url, bang_chung: '',
            ly_do: `${base || tc.url}: ${e.message}` })
          continue
        }
        try {
          await page.goto(url, { waitUntil: 'networkidle', timeout: TIMEOUT })
          await page.waitForTimeout(cfg.cho_them_ms || 2500)   // khối tải dữ liệu sau khi trang lên
          if (/\/login/.test(page.url())) {
            phanTu.push({ trang_thai: 'khong-kiem-duoc', url_that: url, bang_chung: '',
              ly_do: `${url}: bị đẩy về /login` })
            continue
          }
          const chu = (await page.locator('body').innerText()).replace(/\s+/g, ' ')
          let thay = false
          let bangChung = ''
          if (tc.phai_thay) {
            const vt = chu.toLowerCase().indexOf(String(tc.phai_thay).toLowerCase())
            if (vt >= 0) { thay = true; bangChung = '…' + chu.slice(Math.max(0, vt - 80), vt + 120) + '…' }
          }
          if (!thay && tc.khoi) {
            const n = await page.locator(tc.khoi).count().catch(() => 0)
            if (n > 0) { thay = true; bangChung = `khớp khối \`${tc.khoi}\` (${n} phần tử)` }
          }
          phanTu.push(thay
            ? { trang_thai: 'dat', url_that: url, bang_chung: bangChung, ly_do: '' }
            : { trang_thai: 'khong-dat', url_that: url, bang_chung: '',
                ly_do: `${url}: KHÔNG thấy — chữ trên trang bắt đầu bằng «${chu.slice(0, 300)}»` })
        } catch (e) {
          phanTu.push({ trang_thai: 'khong-kiem-duoc', url_that: url, bang_chung: '',
            ly_do: `${url}: ${e.message}` })
        }
      }
      ketQua[i] = phanTu
    }
  } catch (e) {
    for (let i = 0; i < ketQua.length; i++) {
      if (!ketQua[i]) ketQua[i] = [{ trang_thai: 'khong-kiem-duoc', url_that: '', bang_chung: '', ly_do: String(e.message || e) }]
    }
  } finally {
    // browser.close() PHẢI ở finally — lỗi giữa chừng mà để cuối script là browser sống mãi.
    if (browser) await browser.close().catch(() => {})
  }
  // Trải phẳng: MỘT phần tử cho MỖI (tiêu chí × base), kèm `i_tieu_chi` để bên đọc ghép
  // đúng bằng chứng với đúng tiêu chí (bản ghi CŨ không có khoá này -> bên đọc lùi về ghép
  // theo vị trí, xem `nghiem_thu_gate._bang_chung_cua`).
  const phang = []
  ketQua.forEach((r, i) => {
    const ds = Array.isArray(r) ? r : [r || { trang_thai: 'khong-kiem-duoc', url_that: '', bang_chung: '', ly_do: 'không chạy tới' }]
    ds.forEach((k) => phang.push(Object.assign({ i_tieu_chi: i }, k)))
  })
  ra(phang)
})()
