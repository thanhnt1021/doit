#!/usr/bin/env node
// MÁY SOI GIAO DIỆN dùng chung mọi dự án (univ3, học từ 13 kho — ĐX2). Như thợ kiểm xe trước khi giao:
// mở trang ở 3 cỡ màn, đo 4 thứ — chữ tràn · chữ quá nhỏ · nút bé · chữ mờ — rồi chấm điểm /20.
// Ngưỡng lấy đúng bảng «Số đo bắt buộc» của skill ui-ux (chữ ≥ 11px · chạm ≥ 44 điện thoại / 24 máy tính ·
// tương phản ≥ 4.5:1, chữ lớn ≥ 3:1).
//
//   node ~/.claude/skills/may-soi/may-soi.mjs --url /orders [--cau-hinh docs/may-chup.json] [--vai admin]
//        [--co 390,768,1440] [--anh /tmp/soi] [--json /tmp/soi.json] [--cho 2500] [--khong-dang-nhap]
//        [--dat 16]   ← điểm tối thiểu; dưới mức này mã thoát 1 (mặc định 16)
//
//        [--ca-khung]  ← tính cả lỗi ở khung chung (thanh bên/đầu/đáy) — dùng khi việc đang sửa chính khung đó
//        [--quet-ma src | --khong-quet-ma]  ← quét tĩnh hiệu ứng lặp thiếu bản «giảm chuyển động» (mặc định src/)
//
// Mã thoát: 0 đạt · 1 dưới --dat hoặc có chữ rác (undefined/NaN…) · 2 sai tham số / mở trang hỏng ·
//           3 TRANG LỖI (mã ≥ 400 / chữ 404 · not found / trang trắng) — chấm 0, không có dòng báo xong.
// --anh: mỗi cỡ màn một ảnh, chỗ lỗi đóng khung màu (đỏ tràn · cam chữ nhỏ · tím nút bé · xanh chữ mờ),
// dữ liệu khách đã che bằng đúng bộ che của máy chụp.
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'
import { choYen, dichDen, docCauHinh, docThamSo, layChromium, layPhien, loiTrang, moTrang, so } from '../may-chup/chung.mjs'
import { COT_KHACH_MAC_DINH, NHAN_KHACH_MAC_DINH, veVaChe } from '../may-chup/may-chup.mjs'

// Điểm một mục theo số lỗi ở cỡ màn tệ nhất: 0 lỗi 5 · 1–2 4 · 3–5 3 · 6–10 2 · 11–20 1 · > 20 0.
const diem = (n) => (n === 0 ? 5 : n <= 2 ? 4 : n <= 5 ? 3 : n <= 10 ? 2 : n <= 20 ? 1 : 0)

// Chạy TRONG trang. Trả về danh sách lỗi theo 4 mục. Phải tự đủ.
const soi = ({ chamToiThieu, dienThoai }) => {
  const cv = document.createElement('canvas')
  cv.width = cv.height = 1
  const g = cv.getContext('2d', { willReadFrequently: true })
  // Màu kiểu oklch / lab / color-mix (Tailwind v4) → để canvas tự đổi ra sRGB.
  const mau = (s) => {
    g.clearRect(0, 0, 1, 1)
    g.fillStyle = '#000'
    g.fillStyle = s
    g.fillRect(0, 0, 1, 1)
    const [r, gg, b, a] = g.getImageData(0, 0, 1, 1).data
    return [r, gg, b, a / 255]
  }
  const L = ([r, gg, b]) => {
    const f = (c) => ((c /= 255) <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * f(r) + 0.7152 * f(gg) + 0.0722 * f(b)
  }
  const tron = (tren, duoi) => {
    const a = tren[3]
    return [0, 1, 2].map((i) => tren[i] * a + duoi[i] * (1 - a)).concat(1)
  }
  const thay = (el) => {
    const r = el.getBoundingClientRect()
    if (r.width <= 1 || r.height <= 1) return false
    const st = getComputedStyle(el)
    if (st.visibility === 'hidden' || st.display === 'none') return false
    // Ẩn cho máy đọc màn (sr-only: clip rect 0 / clip-path inset 50%) — mắt không thấy, không chấm.
    for (let p = el; p; p = p.parentElement) {
      const s = getComputedStyle(p)
      if (s.opacity === '0') return false
      if ((s.clip && s.clip !== 'auto') || /inset\(50%\)/.test(s.clipPath)) return false
      const q = p.getBoundingClientRect()
      if (p !== el && s.overflow !== 'visible' && (q.width <= 1 || q.height <= 1)) return false
    }
    // bị cắt hẳn bởi tổ tiên overflow ẩn (vd menu thu gọn) → không thấy
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const s = getComputedStyle(p)
      if (s.overflowX === 'visible' && s.overflowY === 'visible') continue
      const q = p.getBoundingClientRect()
      if (r.right <= q.left || r.left >= q.right || r.bottom <= q.top || r.top >= q.bottom) return false
    }
    return true
  }
  const ten = (el) => {
    const cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/)[0] : ''
    const chu = (el.innerText ?? el.textContent ?? '').replace(/\s+/g, ' ').trim().slice(0, 40)
    return `${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}${cls ? '.' + cls : ''}${chu ? ` «${chu}»` : ''}`
  }
  const coChuRieng = (el) =>
    [...el.childNodes].some((n) => n.nodeType === 3 && (n.nodeValue ?? '').trim().length > 0)
  const hop = (el) => {
    const r = el.getBoundingClientRect()
    return { x: Math.round(r.x), y: Math.round(r.y + scrollY), w: Math.round(r.width), h: Math.round(r.height) }
  }
  const tatCa = [...document.body.querySelectorAll('*')].filter(
    (el) => !['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'svg', 'path', 'BR'].includes(el.tagName)
  )
  const loi = { tran: [], nho: [], be: [], mo: [] }
  // W39 — KHUNG CHUNG: trang có <main> thì mọi thứ NGOÀI <main> (thanh bên, đầu trang, thanh đáy) là khung
  // dùng chung cho mọi màn. Lỗi ở đó lặp y hệt ở mọi màn được soi → gắn cờ `chung`, báo riêng một lần,
  // không trừ điểm màn đang soi (đo 28/10: 20/38 lỗi của màn đơn 6278 nằm ở thanh bên + thanh đáy).
  const vungMain = document.querySelector('main, [role="main"]')
  const laChung = (el) => !!vungMain && !!el && !vungMain.contains(el)
  const them = (muc, el, ten) => loi[muc].push({ ten, hop: el ? hop(el) : null, chung: laChung(el) })
  const cuonNgang = document.documentElement.scrollWidth > innerWidth + 1
  if (cuonNgang)
    loi.tran.push({ ten: `cả trang cuộn ngang (rộng ${document.documentElement.scrollWidth}px > ${innerWidth}px)`, hop: null, chung: false })

  const dich_ = [] // mọi vùng chạm
  const beTam = [] // vùng chạm nhỏ hơn ngưỡng — xét ngoại lệ khoảng cách sau
  for (const el of tatCa) {
    if (!thay(el)) continue
    const st = getComputedStyle(el)
    const r = el.getBoundingClientRect()
    const chu = coChuRieng(el)
    // 1. TRÀN: chữ bị cắt cụt không có dấu «…» · phần tử thò ra ngoài mép màn (trừ vùng cuộn ngang có chủ ý).
    if (chu && el.scrollWidth > el.clientWidth + 1 && el.clientWidth > 0) {
      const cat = st.overflowX !== 'visible' || st.overflow !== 'visible'
      const coBaCham = st.textOverflow === 'ellipsis' || st.webkitLineClamp !== 'none'
      if (cat && !coBaCham) them('tran', el, `chữ bị cắt cụt: ${ten(el)}`)
    }
    // Lệch ≤ 4px là răng cưa / hiệu ứng xoay — không tính.
    const thoRa = Math.max(r.right - innerWidth, -r.left)
    if (thoRa > 4) {
      let trongVungCuon = false
      for (let p = el.parentElement; p; p = p.parentElement) {
        const s = getComputedStyle(p)
        if (['auto', 'scroll', 'hidden', 'clip'].includes(s.overflowX)) {
          trongVungCuon = true
          break
        }
      }
      const chaCungTran = el.parentElement && el.parentElement.getBoundingClientRect().right > innerWidth + 4
      if (!trongVungCuon && !chaCungTran && st.position !== 'fixed')
        them('tran', el, `thò ra ngoài mép màn ${Math.round(thoRa)}px: ${ten(el)}`)
    }
    // 2. CHỮ NHỎ: chữ thật < 11px.
    if (chu) {
      const fs = parseFloat(st.fontSize)
      if (fs < 11) them('nho', el, `${fs}px: ${ten(el)}`)
    }
    // 3. NÚT BÉ: vùng chạm < ngưỡng. Liên kết nằm giữa câu chữ được miễn (WCAG 2.5.8 ngoại lệ inline).
    const tuongTac = el.matches(
      'a[href], button, select, textarea, summary, [role="button"], [role="tab"], [role="checkbox"], [role="switch"], input:not([type="hidden"])'
    )
    if (tuongTac && !el.disabled) {
      const trongCau = el.tagName === 'A' && el.parentElement && coChuRieng(el.parentElement) && st.display === 'inline'
      const oNhoTrongNhan =
        el.matches('input[type="checkbox"], input[type="radio"]') &&
        (el.closest('label') || (el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`)))
      const conTrongNut = el.parentElement?.closest('a[href], button, [role="button"]')
      if (!trongCau && !oNhoTrongNhan && !conTrongNut) {
        dich_.push(r)
        if (r.width < chamToiThieu || r.height < chamToiThieu)
          beTam.push({ r, el, ten: `${Math.round(r.width)}×${Math.round(r.height)}: ${ten(el)}` })
      }
    }
    // 4. CHỮ MỜ: tương phản chữ/nền. Nền có ảnh/gradient thì không đo được → bỏ (không đoán).
    if (chu && !el.closest('[disabled], [aria-disabled="true"]')) {
      const fg = mau(st.color)
      if (fg[3] === 0) continue
      const lop = []
      let doDuoc = true
      for (let p = el; p; p = p.parentElement) {
        const s = getComputedStyle(p)
        if (s.backgroundImage && s.backgroundImage !== 'none') {
          doDuoc = false
          break
        }
        const b = mau(s.backgroundColor)
        if (b[3] > 0) lop.push(b)
        if (b[3] >= 1) break
      }
      if (!doDuoc) continue
      let nen = [255, 255, 255, 1]
      for (const b of lop.reverse()) nen = tron(b, nen)
      const chuThat = tron(fg, nen)
      const l1 = L(chuThat)
      const l2 = L(nen)
      const tl = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)
      const fs = parseFloat(st.fontSize)
      const lon = fs >= 24 || (fs >= 18.66 && Number(st.fontWeight) >= 700)
      if (tl < (lon ? 3 : 4.5)) them('mo', el, `${tl.toFixed(2)}:1: ${ten(el)}`)
    }
  }
  // WCAG 2.5.8 ngoại lệ khoảng cách (chỉ máy tính): ô vuông ngưỡng đặt giữa đích nhỏ không chạm đích khác → đạt.
  // Điện thoại giữ luật cứng 44×44 của skill ui-ux, không miễn.
  for (const b of beTam) {
    if (!dienThoai) {
      const cx = b.r.x + b.r.width / 2
      const cy = b.r.y + b.r.height / 2
      const h = chamToiThieu / 2
      const vuong = { left: cx - h, right: cx + h, top: cy - h, bottom: cy + h }
      const dung = dich_.some(
        (q) => q !== b.r && q.left < vuong.right && vuong.left < q.right && q.top < vuong.bottom && vuong.top < q.bottom
      )
      if (!dung) continue
    }
    them('be', b.el, b.ten)
  }
  // W39 — DỮ LIỆU HIỂN THỊ (ĐX3 «dữ liệu khó»): (a) cùng một cột bảng mà ô trống hiện HAI kiểu — có ô ghi
  // «—» có ô để trắng (đơn ZK1-9900000004 vs -0005, 28/10) — người đọc tưởng hai nghĩa khác nhau;
  // (b) chữ rác lọt ra màn: undefined · NaN · [object Object] · Invalid Date · null đứng một mình.
  const duLieu = { trong: [], rac: [] }
  for (const bang of document.querySelectorAll('table')) {
    if (!thay(bang)) continue
    const tieu = []
    let c = 0
    for (const x of bang.querySelector('thead tr:last-child')?.children ?? []) {
      for (let k = 0; k < (x.colSpan || 1); k++) tieu[c + k] = (x.innerText ?? '').replace(/\s+/g, ' ').trim()
      c += x.colSpan || 1
    }
    const cot = new Map()
    for (const tr of bang.querySelectorAll('tbody tr')) {
      let i = 0
      for (const td of tr.children) {
        const n = td.colSpan || 1
        if (n === 1) {
          const t = (td.innerText ?? '').replace(/\s+/g, ' ').trim()
          const coVat = td.querySelector('img, svg, input, button, select, canvas, video, [role="img"]')
          const kieu = t === '' ? (coVat ? null : 'trắng') : /^[—–-]$/.test(t) ? 'gạch' : null
          if (kieu) {
            const o = cot.get(i) ?? { trắng: [], gạch: [] }
            o[kieu].push(td)
            cot.set(i, o)
          }
        }
        i += n
      }
    }
    for (const [i, o] of cot)
      if (o.trắng.length && o.gạch.length)
        duLieu.trong.push({
          ten: `cột «${tieu[i] || `thứ ${i + 1}`}»: ${o.gạch.length} ô «—» + ${o.trắng.length} ô để trắng`,
          hop: hop(o.trắng[0]),
        })
  }
  const RX_RAC = /\b(undefined|NaN|Invalid Date)\b|\[object Object\]|^null$/
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT)
  for (let n = w.nextNode(); n; n = w.nextNode()) {
    const v = (n.nodeValue ?? '').trim()
    if (!v || !RX_RAC.test(v) || !n.parentElement || !thay(n.parentElement)) continue
    if (n.parentElement.closest('script, style, code, pre, textarea')) continue
    duLieu.rac.push({ ten: `«${v.slice(0, 40)}»: ${ten(n.parentElement)}`, hop: hop(n.parentElement) })
  }
  // W23 — DẤU HIỆU KỸ THUẬT (học impeccable bản 5e745ac, luật broken-image · skipped-heading · side-tab):
  // ba thứ máy đo chắc được mà 4 mục điểm bỏ lọt — trang mẫu có đủ cả ba vẫn chấm 20/20 (đo 29/10).
  const kyThuat = { anhVo: [], nhayBac: [], vienMotBen: [] }
  const ghi = (ds, el, t) => ds.push({ ten: t, hop: hop(el), chung: laChung(el) })
  for (const img of document.querySelectorAll('img')) {
    if (!thay(img)) continue
    const src = (img.getAttribute('src') ?? '').trim()
    if ((!src && !img.getAttribute('srcset')) || (img.complete && img.naturalWidth === 0))
      ghi(kyThuat.anhVo, img, `${ten(img)} src=«${src.slice(0, 50) || '(trống)'}»`)
  }
  let bacTruoc = 0
  for (const h of document.querySelectorAll('h1, h2, h3, h4, h5, h6')) {
    if (!thay(h)) continue
    const bac = Number(h.tagName[1])
    if (bacTruoc && bac > bacTruoc + 1) ghi(kyThuat.nhayBac, h, `h${bacTruoc} → ${ten(h)}`)
    bacTruoc = bac
  }
  for (const el of tatCa) {
    const st = getComputedStyle(el)
    const r = el.getBoundingClientRect()
    if (r.height < 20 || r.width < 40) continue
    for (const [ben, nguoc] of [['Left', 'Right'], ['Right', 'Left']]) {
      const w = parseFloat(st[`border${ben}Width`])
      if (w < 3 || st[`border${ben}Style`] === 'none') continue
      if (parseFloat(st[`border${nguoc}Width`]) > w / 2) continue
      const [cr, cg, cb, ca] = mau(st[`border${ben}Color`])
      if (ca < 0.5 || Math.max(cr, cg, cb) - Math.min(cr, cg, cb) < 40) continue // xám/nhạt = vạch phân cách, hợp lệ
      if (thay(el)) ghi(kyThuat.vienMotBen, el, `${ten(el)} viền ${ben === 'Left' ? 'trái' : 'phải'} ${w}px màu`)
      break
    }
  }
  return { loi, cuonNgang, duLieu, kyThuat }
}

// Đóng khung chỗ lỗi lên trang để chụp (màu theo mục).
const veLoi = ({ ds, chu }) => {
  const MAU = { tran: '#e11d48', nho: '#ea580c', be: '#7c3aed', mo: '#0284c7' }
  const t = document.createElement('div')
  Object.assign(t.style, {
    position: 'fixed',
    left: '8px',
    bottom: '8px',
    background: '#111827',
    color: '#fff',
    font: '700 14px sans-serif',
    padding: '6px 10px',
    borderRadius: '6px',
    zIndex: 2147483647,
    maxWidth: 'calc(100vw - 16px)',
  })
  t.innerHTML = chu
  document.body.append(t)
  for (const [muc, arr] of Object.entries(ds))
    for (const { hop } of arr.slice(0, 40)) {
      if (!hop) continue
      const k = document.createElement('div')
      Object.assign(k.style, {
        position: 'absolute',
        left: `${hop.x - 2}px`,
        top: `${hop.y - 2}px`,
        width: `${hop.w + 4}px`,
        height: `${hop.h + 4}px`,
        border: `3px solid ${MAU[muc]}`,
        zIndex: 2147483647,
        pointerEvents: 'none',
      })
      document.body.append(k)
    }
}

const TEN_MUC = { tran: 'Tràn chữ', nho: 'Chữ nhỏ', be: 'Nút bé', mo: 'Chữ mờ' }

// W39 — QUÉT TĨNH HIỆU ỨNG LẶP trong mã nguồn. Đo lúc chạy chỉ thấy chuyển động ĐANG chạy lúc soi; vòng
// quay chờ tải (animate-spin) chỉ hiện vài trăm mili-giây nên 5 màn thật đều ra 0 trong khi mã có 59 tệp
// dùng hiệu ứng lặp. Quét: lớp Tailwind animate-spin/ping/pulse/bounce thiếu motion-safe:/motion-reduce:,
// CSS `infinite` trong tệp không có khối prefers-reduced-motion. Có luật chung kiểu
// `@media (prefers-reduced-motion: reduce) { *, ::before { animation: none } }` thì coi như đã chặn hết.
const DUOI_MA = /\.(tsx?|jsx?|mjs|css|scss|vue|svelte|html)$/
const BO_THU_MUC = new Set(['node_modules', '.next', 'dist', 'build', '.git', 'coverage', '.turbo', 'out'])
function quetHieuUng(goc) {
  const tep = []
  const di = (d) => {
    for (const x of readdirSync(d, { withFileTypes: true })) {
      if (x.isDirectory()) {
        if (!BO_THU_MUC.has(x.name)) di(join(d, x.name))
      } else if (DUOI_MA.test(x.name)) tep.push(join(d, x.name))
    }
  }
  di(goc)
  let chanChung = null
  const cho = []
  const RX_TW = /(^|[\s"'`{])((?:[\w-]+:)*)animate-(spin|ping|pulse|bounce)\b/g
  for (const t of tep) {
    const noi = readFileSync(t, 'utf8')
    const ten = relative(process.cwd(), t)
    // Vùng các khối @media (prefers-reduced-motion: reduce) { … } — đếm ngoặc để lấy trọn khối lồng.
    const vungGiam = []
    for (const m of noi.matchAll(/@media[^{]*prefers-reduced-motion\s*:\s*reduce[^{]*\{/g)) {
      let sau = 1
      let i = m.index + m[0].length
      for (; i < noi.length && sau; i++) sau += noi[i] === '{' ? 1 : noi[i] === '}' ? -1 : 0
      vungGiam.push([m.index, i])
    }
    const trongGiam = (i) => vungGiam.some(([a, b]) => i >= a && i < b)
    // Luật CSS: «bộ chọn { thân }». Bộ chọn nào được nhắc lại trong khối giảm chuyển động = đã có bản dự phòng.
    const luat = [...noi.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({
      chon: m[1].trim().replace(/^.*;/s, '').trim(),
      than: m[2],
      i: m.index,
    }))
    const chonGiam = luat.filter((l) => trongGiam(l.i)).flatMap((l) => l.chon.split(',').map((x) => x.trim()))
    if (chonGiam.some((x) => /^(\*|\*::?before|\*::?after|html \*|body \*)$/.test(x)) && luat.some((l) => trongGiam(l.i) && /animation/.test(l.than)))
      chanChung = ten
    for (const l of luat) {
      if (trongGiam(l.i) || !/animation(-iteration-count)?\s*:[^;]*\binfinite\b/.test(l.than)) continue
      const chon = l.chon.split(',').map((x) => x.trim())
      if (chon.every((x) => chonGiam.includes(x))) continue
      cho.push(`${ten}:${noi.slice(0, l.i + l.chon.length).split('\n').length} ${chon[0]} { animation … infinite }`)
    }
    noi.split('\n').forEach((dong, i) => {
      if (/motion-reduce:(animate-none|hidden)/.test(dong)) return
      for (const m of dong.matchAll(RX_TW)) {
        if (m[2].includes('motion-safe:') || m[2].includes('motion-reduce:')) continue
        cho.push(`${ten}:${i + 1} animate-${m[3]}`)
      }
    })
  }
  return { soTep: new Set(cho.map((x) => x.split(':')[0])).size, cho, chanChung }
}

// Bắt chuyển động lặp suốt LÚC TẢI (không chỉ lúc soi xong): cài trước khi trang chạy, cứ 150ms ghi lại
// mọi hoạt ảnh lặp vô hạn đang chạy. Vòng quay chờ tải 300ms vẫn bị bắt.
const CAI_BAT_HIEU_UNG = () => {
  window.__dongLap = new Set()
  setInterval(() => {
    for (const x of document.getAnimations?.() ?? []) {
      if (x.playState !== 'running' || x.effect?.getTiming?.().iterations !== Infinity) continue
      const el = x.effect?.target
      const cls = el && typeof el.className === 'string' ? el.className.trim().split(/\s+/).slice(0, 3).join('.') : ''
      window.__dongLap.add(`${el?.tagName?.toLowerCase() ?? '?'}${cls ? '.' + cls : ''} (${x.animationName ?? 'hiệu ứng'})`)
    }
  }, 150)
}

async function main() {
  const a = docThamSo(process.argv.slice(2))
  if (!a.url) {
    console.error('Dùng: node ~/.claude/skills/may-soi/may-soi.mjs --url /man [--co 390,768,1440] [--anh /tmp/soi] (xem đầu tệp)')
    process.exit(2)
  }
  let ch
  try {
    ch = docCauHinh(a)
  } catch (e) {
    console.error(String(e.message))
    process.exit(2)
  }
  const co = String((a.co ?? ['390,768,1440']).join(','))
    .split(',')
    .map(Number)
    .filter((x) => x > 0)
  const caKhung = a['ca-khung'] === true
  const batDau = Date.now()
  const chromium = await layChromium()
  const browser = await chromium.launch()
  const ketQua = []
  let hieuUng = null
  const loiJs = [] // W23 — lỗi JS chưa bắt khi tải (impeccable script-error): ghi ở lượt «giảm chuyển động»
  let dich
  let trangLoi = null
  try {
    dich = dichDen(ch, a, String(a.url))
    // Đăng nhập MỘT lần (phiên lưu 30 phút, dùng chung với máy chụp) rồi mở 3 cỡ màn + lượt «giảm chuyển
    // động» SONG SONG — bản cũ chạy tuần tự từng cỡ, đo 28/10: ~37–45 giây/màn.
    await layPhien(browser, ch, a)
    delete a['dang-nhap-lai'] // đã đăng nhập mới ở trên — 4 lượt song song dùng chung phiên đó
    const motCo = async (w) => {
      const dt = w < 600
      const { ctx, page, res } = await moTrang(browser, ch, a, dich, {
        viewport: { width: w, height: dt ? 844 : w < 1100 ? 1024 : 900 },
        ...(dt ? { isMobile: true, hasTouch: true } : {}),
      })
      try {
        await choYen(page, so(a.cho, 2500))
        const loiT = await loiTrang(page, res, ch)
        if (loiT) {
          trangLoi ??= loiT
          return
        }
        const { loi, cuonNgang, duLieu, kyThuat } = await page.evaluate(soi, { chamToiThieu: dt ? 44 : 24, dienThoai: dt })
        ketQua.push({ co: w, loi, cuonNgang, duLieu, kyThuat })
        if (a.anh) {
          mkdirSync(resolve(String(a.anh)), { recursive: true })
          await page.evaluate(veVaChe, {
            khung: [],
            che: ch.che ?? [],
            tieuDe: '',
            nhanKhach: ch.nhan_khach ?? NHAN_KHACH_MAC_DINH,
            cotKhach: ch.cot_khach ?? COT_KHACH_MAC_DINH,
            mauPii: ch.mau_pii ?? [],
          })
          const tinh = (m) => loi[m].filter((x) => caKhung || !x.chung)
          const d = (m) => diem(tinh(m).length)
          const chu =
            `Soi ${w}px · <span style="color:#fb7185">■ tràn ${d('tran')}/5</span> · <span style="color:#fb923c">■ chữ nhỏ ${d('nho')}/5</span>` +
            ` · <span style="color:#a78bfa">■ nút bé ${d('be')}/5</span> · <span style="color:#38bdf8">■ chữ mờ ${d('mo')}/5</span>`
          await page.evaluate(veLoi, { ds: Object.fromEntries(Object.keys(TEN_MUC).map((m) => [m, tinh(m)])), chu })
          await page.screenshot({ path: join(resolve(String(a.anh)), `soi-${w}.png`), fullPage: true })
        }
      } finally {
        await ctx.close()
      }
    }
    // Lượt «giảm chuyển động»: bật reducedMotion, ghi mọi chuyển động lặp suốt lúc tải lẫn lúc yên.
    const luotHieuUng = async () => {
      const { ctx, page } = await moTrang(browser, ch, a, 'about:blank', {
        reducedMotion: 'reduce',
        viewport: { width: 1440, height: 900 },
      })
      try {
        await page.addInitScript(CAI_BAT_HIEU_UNG)
        page.on('pageerror', (e) => loiJs.push(String(e.message ?? e).split('\n')[0].slice(0, 80)))
        await page.goto(dich, { waitUntil: 'domcontentloaded' })
        await choYen(page, 1500)
        await page.waitForTimeout(300)
        hieuUng = await page.evaluate(() => [...(window.__dongLap ?? [])])
      } finally {
        await ctx.close()
      }
    }
    await Promise.all([...co.map(motCo), luotHieuUng()])
  } catch (e) {
    console.error(`Soi hỏng: ${e.message}`)
    process.exitCode = 2
  } finally {
    await browser.close()
  }
  if (trangLoi) {
    console.log(`SOI GIAO DIỆN 0/20 — ${dich}`)
    console.log(`  ⛔ TRANG LỖI: ${trangLoi} — không chấm điểm trang lỗi. Kiểm lại đường dẫn / mã bản ghi / quyền vai.`)
    console.log('Dòng cho tin báo xong: (không có — trang lỗi, chưa được báo xong)')
    process.exitCode = 3
    return
  }
  if (!ketQua.length) return
  ketQua.sort((x, y) => x.co - y.co)
  let tong = 0
  const dong = []
  const tinh = (k, m) => k.loi[m].filter((x) => caKhung || !x.chung)
  for (const m of Object.keys(TEN_MUC)) {
    const dem = ketQua.map((k) => tinh(k, m).length)
    let d = diem(Math.max(...dem))
    if (m === 'tran' && ketQua.some((k) => k.cuonNgang)) d = Math.min(d, 2)
    tong += d
    dong.push(`  ${TEN_MUC[m].padEnd(9)} ${d}/5  (${ketQua.map((k) => `${k.co}px: ${tinh(k, m).length}`).join(' · ')})`)
  }
  console.log(`SOI GIAO DIỆN ${tong}/20 — ${dich}${caKhung ? ' (tính cả khung chung)' : ''}`)
  console.log(dong.join('\n'))
  // Khung chung: gom theo (mục, tên lỗi) qua mọi cỡ màn — báo MỘT lần.
  const chung = new Map()
  if (!caKhung)
    for (const k of ketQua)
      for (const m of Object.keys(TEN_MUC))
        for (const x of k.loi[m].filter((y) => y.chung)) {
          const khoa = `${m}|${x.ten}`
          const c = chung.get(khoa) ?? { m, ten: x.ten, co: [] }
          c.co.push(k.co)
          chung.set(khoa, c)
        }
  if (chung.size) {
    const theoMuc = Object.keys(TEN_MUC)
      .map((m) => [m, [...chung.values()].filter((c) => c.m === m).length])
      .filter(([, n]) => n)
      .map(([m, n]) => `${TEN_MUC[m].toLowerCase()} ${n}`)
      .join(' · ')
    console.log(
      `  Khung chung (ngoài <main>: thanh bên, đầu/đáy trang) — KHÔNG trừ điểm màn này, lặp ở mọi màn: ${chung.size} lỗi khác nhau (${theoMuc}). Sửa khung thì soi bằng --ca-khung.`
    )
  }
  const tr = ketQua.flatMap((k) => k.duLieu.trong.map((x) => ({ ...x, co: k.co })))
  const trGom = [...new Map(tr.map((x) => [x.ten, x])).values()]
  const rac = [...new Map(ketQua.flatMap((k) => k.duLieu.rac).map((x) => [x.ten, x])).values()]
  console.log(
    `  Dữ liệu hiển thị: ${trGom.length} cột ô trống hiện 2 kiểu («—» lẫn để trắng) · ${rac.length} chữ rác (undefined/NaN/null…)${rac.length ? ' ⛔' : trGom.length ? ' ⚠' : ''}`
  )
  for (const x of trGom.slice(0, 3)) console.log(`   · Ô trống 2 kiểu — ${x.ten}`)
  for (const x of rac.slice(0, 3)) console.log(`   · Chữ rác — ${x.ten}`)
  const gomKT = (k) => [
    ...new Map(ketQua.flatMap((x) => x.kyThuat[k].filter((y) => caKhung || !y.chung)).map((y) => [y.ten, y])).values(),
  ]
  const kt = { anhVo: gomKT('anhVo'), nhayBac: gomKT('nhayBac'), vienMotBen: gomKT('vienMotBen') }
  const js = [...new Set(loiJs)]
  const soKT = js.length + kt.anhVo.length + kt.nhayBac.length + kt.vienMotBen.length
  console.log(
    `  Dấu hiệu kỹ thuật (không tính điểm): ${kt.anhVo.length} ảnh vỡ · ${js.length} lỗi JS lúc tải · ${kt.nhayBac.length} tiêu đề nhảy bậc · ${kt.vienMotBen.length} viền màu dày một bên${soKT ? ' ⚠' : ''}`
  )
  for (const x of kt.anhVo.slice(0, 3)) console.log(`   · Ảnh vỡ — ${x.ten}`)
  for (const x of js.slice(0, 3)) console.log(`   · Lỗi JS — ${x}`)
  for (const x of kt.nhayBac.slice(0, 3)) console.log(`   · Tiêu đề nhảy bậc — ${x.ten}`)
  for (const x of kt.vienMotBen.slice(0, 3)) console.log(`   · Viền một bên (dấu hiệu máy dựng) — ${x.ten}`)
  console.log(
    `  Hiệu ứng (không tính điểm): ${hieuUng ? hieuUng.length : '?'} chuyển động lặp còn chạy khi bật «giảm chuyển động» (cả lúc đang tải)${hieuUng?.length ? ` ⚠ vd ${hieuUng.slice(0, 2).join(' · ')}` : ''}`
  )
  if (a['khong-quet-ma'] !== true) {
    const goc = resolve(String(a['quet-ma'] ?? 'src'))
    if (existsSync(goc)) {
      const q = quetHieuUng(goc)
      if (q.chanChung) console.log(`  Hiệu ứng trong MÃ (cả dự án, quét tĩnh): đã có luật chặn chung ở ${q.chanChung} — đạt.`)
      else
        console.log(
          `  Hiệu ứng trong MÃ (cả dự án, quét tĩnh): ${q.cho.length} chỗ lặp vô hạn thiếu bản «giảm chuyển động» trong ${q.soTep} tệp${q.cho.length ? ` ⚠ vd ${q.cho.slice(0, 3).join(' · ')}` : ''}`
        )
    }
  }
  for (const k of ketQua)
    for (const m of Object.keys(TEN_MUC))
      for (const x of tinh(k, m).slice(0, 3)) console.log(`   · ${k.co}px ${TEN_MUC[m]}: ${x.ten}`)
  if (a.anh) console.log(`  Ảnh: ${co.map((w) => join(resolve(String(a.anh)), `soi-${w}.png`)).join(' · ')}`)
  if (a.json)
    writeFileSync(resolve(String(a.json)), JSON.stringify({ url: dich, tong, ketQua, hieuUng, loiJs: js, khungChung: [...chung.values()] }, null, 2))
  const giay = ((Date.now() - batDau) / 1000).toFixed(1)
  const kem = [
    trGom.length ? `${trGom.length} cột ô trống 2 kiểu` : '',
    rac.length ? `${rac.length} chữ rác` : '',
    kt.anhVo.length ? `${kt.anhVo.length} ảnh vỡ` : '',
    js.length ? `${js.length} lỗi JS` : '',
  ].filter(Boolean)
  console.log(`Dòng cho tin báo xong: «Soi giao diện ${tong}/20${kem.length ? ` · ⚠ ${kem.join(' · ')}` : ''}» (${giay} giây)`)
  if (tong < so(a.dat, 16) || rac.length) process.exitCode = 1
}

await main()
