// Phần dùng chung của máy chụp + máy soi: đọc cấu hình dự án, tìm Playwright của dự án, đăng nhập đúng vai.
// WHY tách: hai công cụ cùng phải mở web thật bằng tài khoản thử — viết hai lần là hai chỗ lệch nhau.
import { createHash } from 'node:crypto'
import { createRequire } from 'node:module'
import { chmodSync, existsSync, mkdirSync, readFileSync, rmSync, statSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

export function docThamSo(argv) {
  const a = { _: [] }
  const NHIEU = new Set(['chon', 'khoanh', 'ghi', 'che', 'co', 'ban', 'nhan', 'tep-ban'])
  for (let i = 0; i < argv.length; i++) {
    const t = argv[i]
    if (!t.startsWith('--')) {
      a._.push(t)
      continue
    }
    const k = t.slice(2)
    const v = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true
    if (NHIEU.has(k)) (a[k] ??= []).push(v)
    else a[k] = v
  }
  return a
}

// Cấu hình dự án: --cau-hinh <tệp> hoặc tệp mặc định docs/may-chup.json của thư mục đang đứng.
export function docCauHinh(a) {
  const tep = a['cau-hinh'] ? resolve(String(a['cau-hinh'])) : resolve('docs/may-chup.json')
  if (!existsSync(tep)) {
    if (a['cau-hinh']) throw new Error(`Không thấy tệp cấu hình ${tep}`)
    return { tep: null }
  }
  return { ...JSON.parse(readFileSync(tep, 'utf8')), tep }
}

// Đọc biến từ tệp env của dự án (không in ra) — rơi về biến môi trường.
export function bien(ch, ten) {
  if (!ten) return undefined
  if (process.env[ten]) return process.env[ten]
  const tep = resolve(ch.tep_env ?? '.env')
  if (!existsSync(tep)) return undefined
  const dong = readFileSync(tep, 'utf8')
    .split('\n')
    .find((l) => l.startsWith(ten + '='))
  return dong
    ?.slice(ten.length + 1)
    .trim()
    .replace(/^["']|["']$/g, '')
}

// Playwright lấy từ node_modules của DỰ ÁN (thư mục đang đứng), không cài thêm gói nào.
export async function layChromium() {
  const req = createRequire(join(process.cwd(), 'package.json'))
  for (const goi of ['playwright', '@playwright/test', 'playwright-core']) {
    try {
      const m = await import(req.resolve(goi))
      const c = m.chromium ?? m.default?.chromium
      if (c) return c
    } catch {}
  }
  throw new Error(
    'Dự án này chưa có Playwright (không thấy playwright / @playwright/test trong node_modules). Hỏi chủ nhà trước khi cài.'
  )
}

export function dichDen(ch, a, url) {
  const goc = String(a.goc ?? ch.goc ?? '').replace(/\/$/, '')
  if (/^(https?|file):\/\//.test(url)) return url
  if (!goc) throw new Error('Thiếu --goc (hoặc "goc" trong cấu hình) cho đường dẫn tương đối.')
  return `${goc}${url.startsWith('/') ? '' : '/'}${url}`
}

// Đăng nhập theo khuôn trong cấu hình. Không có khối dang_nhap hoặc --khong-dang-nhap → bỏ qua.
export async function dangNhap(page, ch, a) {
  const d = ch.dang_nhap
  if (!d || a['khong-dang-nhap']) return null
  const vai = String(a.vai ?? ch.vai_mac_dinh ?? 'admin')
  const ten = d.bien_ten ? bien(ch, d.bien_ten) : String(d.ten ?? '').replaceAll('{vai}', vai)
  const mk = bien(ch, d.bien_mat_khau)
  if (!ten || !mk)
    throw new Error(
      `Thiếu tài khoản thử: tên (${d.bien_ten ?? d.ten}) hoặc mật khẩu (${d.bien_mat_khau}) trong ${ch.tep_env ?? '.env'}.`
    )
  const goc = String(a.goc ?? ch.goc).replace(/\/$/, '')
  await page.goto(`${goc}${d.duong ?? '/login'}`, { waitUntil: 'domcontentloaded' })
  await page.fill(d.o_ten, ten)
  await page.fill(d.o_mat_khau, mk)
  await page.click(d.nut ?? 'button[type="submit"]')
  const roi = d.cho_roi_khoi ?? d.duong ?? '/login'
  await page.waitForURL((u) => !u.pathname.startsWith(roi), { timeout: Number(d.cho_ms ?? 120_000) })
  return vai
}

// W39 — PHIÊN DÙNG LẠI: đăng nhập là khúc chậm nhất của một lần chụp (đo 28/10: ~5 giây/lần trên bản thật,
// chụp 5 ảnh = 5 lần đăng nhập). Lưu phiên của tài khoản THỬ vào tệp tạm quyền 600, sống 30 phút; hết hạn hoặc
// bị đẩy về trang đăng nhập thì tự đăng nhập lại một lần. Không lưu mật khẩu — chỉ cookie phiên của tài khoản thử.
const PHIEN_SONG_MS = 30 * 60_000
function tepPhien(ch, a) {
  const d = ch.dang_nhap
  const vai = String(a.vai ?? ch.vai_mac_dinh ?? 'admin')
  const ten = d.bien_ten ? bien(ch, d.bien_ten) : String(d.ten ?? '').replaceAll('{vai}', vai)
  const goc = String(a.goc ?? ch.goc ?? '')
  const khoa = createHash('sha1').update(`${goc}|${vai}|${ten}`).digest('hex').slice(0, 16)
  return join(tmpdir(), 'may-chup-phien', `${khoa}.json`)
}

export async function layPhien(browser, ch, a, lamMoi = false) {
  if (!ch.dang_nhap || a['khong-dang-nhap']) return undefined
  const tep = tepPhien(ch, a)
  if (!lamMoi && !a['dang-nhap-lai'] && existsSync(tep) && Date.now() - statSync(tep).mtimeMs < PHIEN_SONG_MS) return tep
  const ctx = await browser.newContext()
  try {
    const p = await ctx.newPage()
    p.setDefaultTimeout(120_000)
    await dangNhap(p, ch, a)
    mkdirSync(join(tmpdir(), 'may-chup-phien'), { recursive: true, mode: 0o700 })
    await ctx.storageState({ path: tep })
    chmodSync(tep, 0o600)
    return tep
  } finally {
    await ctx.close()
  }
}

// Chờ trang YÊN thay cho chờ cứng: hết lượt tải mạng (tối đa 15 giây — trang có kết nối treo vẫn đi tiếp)
// rồi DOM đứng im 700ms (tối đa `toiDa`). Trang tĩnh xong sớm thì đi sớm, trang chậm vẫn được chờ đủ.
export async function choYen(page, toiDa = 2500) {
  await page.waitForLoadState('networkidle', { timeout: 15_000 }).catch(() => {})
  await page
    .evaluate(
      (toiDa) =>
        new Promise((xong) => {
          let hen = setTimeout(xong, 700)
          const mo = new MutationObserver(() => {
            clearTimeout(hen)
            hen = setTimeout(xong, 700)
          })
          mo.observe(document.documentElement, { subtree: true, childList: true, characterData: true, attributes: true })
          setTimeout(() => {
            mo.disconnect()
            xong()
          }, toiDa)
        }),
      toiDa
    )
    .catch(() => {})
}

// Mở một trang bằng phiên đã lưu (đăng nhập lại một lần nếu phiên hết hạn). Trả { ctx, page, res }.
export async function moTrang(browser, ch, a, url, opts = {}) {
  for (let lan = 0; lan < 2; lan++) {
    const phien = await layPhien(browser, ch, a, lan > 0)
    const ctx = await browser.newContext({ ...opts, ...(phien ? { storageState: phien } : {}) })
    const page = await ctx.newPage()
    page.setDefaultTimeout(120_000)
    page.setDefaultNavigationTimeout(180_000)
    const res = await page.goto(url, { waitUntil: 'domcontentloaded' })
    const roi = ch.dang_nhap?.cho_roi_khoi ?? ch.dang_nhap?.duong ?? '/login'
    if (phien && new URL(page.url()).pathname.startsWith(roi) && !new URL(url).pathname.startsWith(roi)) {
      await ctx.close()
      if (lan === 0) rmSync(phien, { force: true })
      continue
    }
    return { ctx, page, res }
  }
  throw new Error('Đăng nhập xong vẫn bị đẩy về trang đăng nhập — tài khoản thử sai vai hoặc hết quyền vào màn này.')
}

// W39 — TRANG LỖI: trước đây trang 404 vẫn được chấm 20/20 và vẫn «ĐÃ CHỤP» (Next trả 200 kèm chữ
// «404 This page could not be found»). Bắt cả mã máy chủ ≥ 400 lẫn chữ trang lỗi ở tiêu đề / h1 / h2;
// dự án có trang lỗi tự viết thì khai câu chữ của nó ở "chu_trang_loi" (regex) trong cấu hình.
export const RX_TRANG_LOI =
  '^\\s*[45]\\d\\d\\s*($|[:|·–-])|could not be found|page not found|not found$|application error|internal server error|this page isn.t working|không tìm thấy trang|trang không tồn tại|đã xảy ra lỗi'
export async function loiTrang(page, res, ch) {
  const st = res?.status?.() ?? 0
  if (st >= 400) return `máy chủ trả mã ${st}`
  const rieng = ch.chu_trang_loi ? [ch.chu_trang_loi].flat().join('|') : ''
  const t = await page.evaluate(
    ({ chung, rieng }) => {
      const r = new RegExp(rieng ? `${chung}|${rieng}` : chung, 'i')
      const tieu = [document.title, ...[...document.querySelectorAll('h1, h2, [role="alert"]')].map((x) => x.innerText ?? '')]
        .map((x) => x.replace(/\s+/g, ' ').trim())
        .filter(Boolean)
      // Câu chữ trang lỗi tự viết của dự án (chu_trang_loi) có thể nằm ở <p> — chỉ xét khi dự án khai.
      const rr = rieng ? new RegExp(rieng, 'i') : null
      const them = rr ? [...document.querySelectorAll('p, div')].filter((x) => x.children.length === 0).map((x) => (x.innerText ?? '').trim()) : []
      const trung = tieu.find((x) => r.test(x)) ?? them.find((x) => rr.test(x))
      return { trung, chu: (document.body?.innerText ?? '').trim().length }
    },
    { chung: RX_TRANG_LOI, rieng }
  )
  if (t.trung) return `trang báo lỗi «${t.trung.slice(0, 60)}»`
  if (t.chu === 0) return 'trang trắng — không có chữ nào'
  return null
}

export function so(v, mac) {
  return Number.isFinite(Number(v)) && Number(v) > 0 ? Number(v) : mac
}
