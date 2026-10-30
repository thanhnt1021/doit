#!/usr/bin/env node
// MÁY CHỤP ẢNH dùng chung mọi dự án (univ3, học từ 13 kho — ĐX1): mở web thật, đăng nhập đúng vai,
// chụp, khoanh đỏ, che dữ liệu khách. Thay cho việc mỗi thợ tự viết một tệp Playwright + một tệp khoanh.
//
//   node ~/.claude/skills/may-chup/may-chup.mjs --url /orders --ra /tmp/anh/sau.png \
//        [--cau-hinh docs/may-chup.json] [--vai admin] [--goc https://…] \
//        [--chon "<css>" | --chon "chu:<đoạn chữ>"]… [--khoanh "x,y,w,h"]… [--ghi "chú thích"]… \
//        [--tieu-de "dòng tiêu đề"] [--che "<css>"]… [--rong 1440 --cao 900 | --dien-thoai] \
//        [--ca-trang] [--cho 2500] [--khong-dang-nhap] [--cho-sot-pii] [--giam-chuyen-dong]
//
// Chạy từ GỐC dự án (Playwright lấy từ node_modules của dự án). CHỈ XEM — không bấm gì ngoài nút đăng nhập.
// Mã thoát: 0 chụp xong · 1 mọi khung đỏ đều không thấy phần tử · 2 sai tham số/cấu hình ·
//           3 sau khi che vẫn còn thư điện tử / mẫu PII lộ trên ảnh (ảnh vẫn ghi, KHÔNG được gửi đi) ·
//           4 trang lỗi (mã ≥ 400, chữ «404 / not found / không tìm thấy trang», trang trắng) — ảnh KHÔNG được gửi.
// Phiên đăng nhập dùng lại 30 phút (tệp tạm quyền 600) — `--dang-nhap-lai` để ép đăng nhập mới.
import { mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { choYen, dichDen, docCauHinh, docThamSo, layChromium, loiTrang, moTrang, so } from './chung.mjs'

// Chạy TRONG trang: che PII rồi vẽ khung đỏ + chú thích. Phải tự đủ (không dùng biến ngoài).
export const veVaChe = ({ khung, che, tieuDe, nhanKhach, cotKhach, mauPii }) => {
  const RX_MAIL = /[\w.+-]+@[\w-]+(\.[\w-]+)+/g
  const CO_MAIL = /[\w.+-]+@[\w-]+(\.[\w-]+)+/
  const mau = (mauPii ?? []).map((s) => new RegExp(s, 'g'))
  let daChe = 0
  const mo = (el) => {
    if (el && el.style.filter !== 'blur(7px)') {
      el.style.filter = 'blur(7px)'
      daChe++
    }
  }
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    let v = n.nodeValue ?? ''
    if (CO_MAIL.test(v)) v = v.replace(RX_MAIL, '••••@••••')
    for (const r of mau) v = v.replace(r, '••••')
    if (v !== n.nodeValue) {
      n.nodeValue = v
      daChe++
    }
  }
  for (const el of document.querySelectorAll('input, textarea'))
    if (CO_MAIL.test(el.value)) {
      el.value = '••••@••••'
      daChe++
    }
  for (const el of document.querySelectorAll(['[data-pii]', 'address', ...che].join(','))) mo(el)
  // Bảng: cột có tiêu đề là thông tin khách → che cả cột.
  const rxCot = new RegExp(cotKhach, 'i')
  // Ghép ô theo VỊ TRÍ CỘT thật (cộng dồn colspan), không theo thứ tự con — dòng có ô gộp thì thứ tự con lệch cột.
  const oTaiCot = (tr, cot) => {
    let c = 0
    for (const td of tr.children) {
      const n = td.colSpan || 1
      if (cot >= c && cot < c + n) return n === 1 ? td : null // ô gộp nhiều cột: không phải ô của riêng cột khách
      c += n
    }
    return null
  }
  for (const bang of document.querySelectorAll('table')) {
    const hang = bang.querySelector('thead tr:last-child')
    if (!hang) continue
    let c = 0
    for (const x of hang.children) {
      const n = x.colSpan || 1
      if (rxCot.test((x.textContent ?? '').trim()))
        for (let k = c; k < c + n; k++) for (const tr of bang.querySelectorAll('tbody tr')) mo(oTaiCot(tr, k))
      c += n
    }
  }
  // Màn chi tiết: nhãn thông tin khách → che phần tử đứng ngay sau nhãn.
  // Tiêu đề bảng (thead) KHÔNG xét ở đây — ô «Customer» của thead làm mờ nhầm tiêu đề cột kế bên (W39).
  const rxNhan = new RegExp(nhanKhach, 'i')
  for (const el of document.querySelectorAll('dt, label, span, div, p, th'))
    if (el.children.length === 0 && !el.closest('thead') && rxNhan.test((el.textContent ?? '').trim()))
      mo(el.nextElementSibling)

  const thieu = []
  const can = [] // {r, chu}: vẽ khung trước hết, chú thích sau — để chú thích né được MỌI khung
  const ve = (r, chu) => can.push({ r, chu })
  for (const k of khung) {
    if (k.r) {
      ve(k.r, k.chu)
      continue
    }
    // «chu:<chữ>» = phần tử NHỎ NHẤT chứa đoạn chữ (màn không có selector riêng).
    const el = k.sel.startsWith('chu:')
      ? [...document.querySelectorAll('body *')]
          .filter((x) => (x.textContent ?? '').includes(k.sel.slice(4)))
          // chỉ phần tử THẤY được: bản sao ẩn (sr-only, title ẩn) có cùng chữ thì khung vẽ ra góc 0,0.
          .filter((x) => {
            const r = x.getBoundingClientRect()
            return r.width > 0 && r.height > 0 && getComputedStyle(x).visibility !== 'hidden'
          })
          .pop()
      : document.querySelector(k.sel)
    if (!el) {
      thieu.push(k.sel)
      continue
    }
    // Chỉ cuộn khi phần tử nằm ngoài màn — cuộn vô cớ làm lệch khung đã đo của phần tử trước.
    const r_ = el.getBoundingClientRect()
    if (r_.top < 0 || r_.bottom > innerHeight) el.scrollIntoView({ block: 'center' })
    // Khung = phần THẤY được: cắt theo tổ tiên có overflow ẩn + khung nhìn, không thì khung tràn ra ngoài.
    const r0 = el.getBoundingClientRect()
    let [x1, y1, x2, y2] = [r0.left, r0.top, r0.right, r0.bottom]
    for (let p = el.parentElement; p; p = p.parentElement) {
      const st = getComputedStyle(p)
      if (st.overflowX === 'visible' && st.overflowY === 'visible') continue
      const q = p.getBoundingClientRect()
      x1 = Math.max(x1, q.left)
      y1 = Math.max(y1, q.top)
      x2 = Math.min(x2, q.right)
      y2 = Math.min(y2, q.bottom)
    }
    x1 = Math.max(x1, 0)
    y1 = Math.max(y1, 0)
    x2 = Math.min(x2, innerWidth)
    y2 = Math.min(y2, innerHeight)
    ve(x2 > x1 && y2 > y1 ? { x: x1, y: y1, width: x2 - x1, height: y2 - y1 } : r0, k.chu)
  }
  for (const { r } of can) {
    const k = document.createElement('div')
    Object.assign(k.style, {
      position: 'fixed',
      left: `${r.x - 5}px`,
      top: `${r.y - 5}px`,
      width: `${r.width + 10}px`,
      height: `${r.height + 10}px`,
      border: '4px solid #e11d48',
      borderRadius: '8px',
      zIndex: 2147483647,
      pointerEvents: 'none',
    })
    document.body.append(k)
  }
  const cham = (p, q) => p.left < q.right && q.left < p.right && p.top < q.bottom && q.top < p.bottom
  const vung = can.map(({ r }) => ({ left: r.x - 5, top: r.y - 5, right: r.x + r.width + 5, bottom: r.y + r.height + 5 }))
  can.forEach(({ r, chu }, i) => {
    if (!chu) return
    const c = document.createElement('div')
    Object.assign(c.style, {
      position: 'fixed',
      left: `${Math.max(0, Math.min(r.x - 5, innerWidth - 260))}px`,
      background: '#e11d48',
      color: '#fff',
      font: '700 16px sans-serif',
      padding: '5px 10px',
      borderRadius: '5px',
      zIndex: 2147483647,
      pointerEvents: 'none',
      maxWidth: `${Math.min(760, innerWidth - 16)}px`,
    })
    c.textContent = chu
    document.body.append(c)
    // Thử: trên khung · dưới khung · bên phải khung — lấy chỗ đầu tiên không đè khung/chú thích khác.
    const h = c.getBoundingClientRect().height
    const thu = [
      { top: r.y - h - 10, left: r.x - 5 },
      { top: r.y + r.height + 10, left: r.x - 5 },
      { top: r.y, left: r.x + r.width + 12 },
    ]
    for (const t of thu) {
      c.style.top = `${Math.max(0, t.top)}px`
      c.style.left = `${Math.max(0, Math.min(t.left, innerWidth - c.getBoundingClientRect().width - 4))}px`
      const q = c.getBoundingClientRect()
      if (!vung.some((v, j) => j !== i && cham(q, v))) break
    }
    vung.push(c.getBoundingClientRect())
  })
  if (tieuDe) {
    const t = document.createElement('div')
    Object.assign(t.style, {
      position: 'fixed',
      left: '50%',
      transform: 'translateX(-50%)',
      bottom: '24px',
      background: '#111827',
      color: '#fff',
      font: '700 18px sans-serif',
      padding: '10px 18px',
      borderRadius: '8px',
      border: '3px solid #e11d48',
      zIndex: 2147483647,
      maxWidth: `${Math.min(1100, innerWidth - 24)}px`,
      textAlign: 'center',
    })
    t.textContent = tieuDe
    document.body.append(t)
  }
  // Soát lại: còn chuỗi thư điện tử / mẫu PII nào THẤY được mà không nằm trong vùng đã làm mờ?
  const mo_ = (el) => {
    for (let p = el; p; p = p.parentElement) if (getComputedStyle(p).filter.includes('blur')) return true
    return false
  }
  const sot = []
  const w2 = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  for (let n = w2.nextNode(); n; n = w2.nextNode()) {
    const v = n.nodeValue ?? ''
    const lo = CO_MAIL.test(v) || mau.some((r) => new RegExp(r.source).test(v))
    if (!lo || !n.parentElement || mo_(n.parentElement)) continue
    const r = n.parentElement.getBoundingClientRect()
    if (r.width && r.height) sot.push(v.trim().slice(0, 40))
  }
  return { thieu, daChe, sot }
}

// W39 — nhãn/tiêu đề phải khớp TRỌN chữ: bản cũ khớp «bắt đầu bằng» nên «Buyer Paid» (cột TIỀN) bị coi là
// cột khách và bị làm mờ, «Shop name»/«Product name» cũng bị che (đo trên màn Khách hàng + Đơn, 28/10/2026).
export const NHAN_KHACH_MAC_DINH =
  '^(khách hàng|tên|tên khách|họ tên|((customer|buyer|recipient|full|first|last) )?name|địa chỉ giao|địa chỉ|address(\\s*\\d)?|city|state|zip|phone|email|customer|ship to|người nhận|personali[sz]ation|cá nhân hoá|cá nhân hóa)\\s*:?$'
export const COT_KHACH_MAC_DINH =
  '^(customer|buyer|recipient|ship[ -]?to|shipping address|address|e-?mail|phone|personali[sz]ation|khách( hàng)?|tên khách|người nhận|địa chỉ( giao)?|(số )?điện thoại|cá nhân ho[áa])( (name|e-?mail|address|phone|info|details))?[\\s:↑↓▲▼⇅·]*$'

async function main() {
  const a = docThamSo(process.argv.slice(2))
  if (!a.url || !a.ra) {
    console.error('Dùng: node ~/.claude/skills/may-chup/may-chup.mjs --url /man --ra /tmp/anh/sau.png [--chon "<css>"] [--ghi "chú thích"] … (xem đầu tệp)')
    process.exit(2)
  }
  let ch
  try {
    ch = docCauHinh(a)
  } catch (e) {
    console.error(String(e.message))
    process.exit(2)
  }
  const khung = [
    ...(a.chon ?? []).map((sel) => ({ sel: String(sel) })),
    ...(a.khoanh ?? []).map((x) => {
      const [x0, y0, w, h] = String(x).split(',').map(Number)
      if (![x0, y0, w, h].every(Number.isFinite)) {
        console.error(`--khoanh "${x}" phải dạng "x,y,w,h".`)
        process.exit(2)
      }
      return { r: { x: x0, y: y0, width: w, height: h } }
    }),
  ].map((k, i) => ({ ...k, chu: String((a.ghi ?? [])[i] ?? '') }))
  const dt = a['dien-thoai'] === true
  const chromium = await layChromium()
  const browser = await chromium.launch()
  let kq
  let loi = null
  const ra = resolve(String(a.ra))
  try {
    const dich = dichDen(ch, a, String(a.url))
    const vai = ch.dang_nhap && !a['khong-dang-nhap'] ? String(a.vai ?? ch.vai_mac_dinh ?? 'admin') : null
    const { page, res } = await moTrang(browser, ch, a, dich, {
      viewport: { width: so(a.rong, dt ? 390 : 1440), height: so(a.cao, dt ? 844 : 900) },
      ...(dt ? { isMobile: true, hasTouch: true, deviceScaleFactor: 2 } : {}),
      // ảnh bản dự phòng của trang hiệu ứng (luật hiệu ứng skill ui-ux)
      ...(a['giam-chuyen-dong'] ? { reducedMotion: 'reduce' } : {}),
    })
    await choYen(page, so(a.cho, 2500))
    loi = await loiTrang(page, res, ch)
    kq = await page.evaluate(veVaChe, {
      khung,
      che: [...(ch.che ?? []), ...(a.che ?? []).map(String)],
      tieuDe: a['tieu-de'] ? String(a['tieu-de']) : '',
      nhanKhach: ch.nhan_khach ?? NHAN_KHACH_MAC_DINH,
      cotKhach: ch.cot_khach ?? COT_KHACH_MAC_DINH,
      mauPii: ch.mau_pii ?? [],
    })
    await page.waitForTimeout(300)
    mkdirSync(dirname(ra), { recursive: true })
    await page.screenshot({ path: ra, fullPage: a['ca-trang'] === true })
    if (loi) console.error(`⛔ TRANG LỖI (${loi}) — ảnh vẫn ghi để xem nhưng KHÔNG phải ảnh báo xong: ${dich}`)
    console.log(
      `${loi ? 'CHỤP TRANG LỖI' : 'ĐÃ CHỤP'} ${dich} → ${ra}${vai ? ` · vai ${vai}` : ''} · ${khung.length - kq.thieu.length}/${khung.length} khung đỏ · che ${kq.daChe} chỗ · sót PII ${kq.sot.length}`
    )
  } catch (e) {
    console.error(`Chụp hỏng: ${e.message}`)
    process.exitCode = 2
  } finally {
    await browser.close()
  }
  if (!kq) return
  if (loi) {
    process.exitCode = 4
    return
  }
  for (const s of kq.thieu) console.error(`(cảnh báo) không thấy "${s}" trên màn — khung đó bỏ qua.`)
  if (kq.sot.length && a['cho-sot-pii'] !== true) {
    console.error(`⛔ Còn ${kq.sot.length} chỗ lộ thư điện tử / mẫu PII chưa che (vd «${kq.sot[0]}»). Thêm --che "<css>" rồi chụp lại; ảnh này KHÔNG được gửi.`)
    process.exitCode = 3
    return
  }
  if (khung.length && kq.thieu.length === khung.length) process.exitCode = 1
}

// Chỉ chạy khi gọi trực tiếp (máy soi import veVaChe thì không chạy main).
if (process.argv[1]?.endsWith('may-chup.mjs')) {
  await main()
}
