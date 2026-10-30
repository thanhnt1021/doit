#!/usr/bin/env node
// lam_pdf.mjs — dựng PDF gửi NGƯỜI từ một tệp .md, theo chuẩn infographic của bot Fulfill ChicHub.
// WHY (oHa-28102026-02): PDF góp ý ttkvn in thẳng Markdown ra A4 bị anh Thành chê «format xấu». Fulfill đã
// chốt 08/10/2026: tài liệu gửi người là infographic khung dọc 1080×1600, khối màu + icon, ≤ 420 chữ/trang,
// xuất PNG từng trang + PDF rồi qua cổng đo (EtsyFulfillChichub docs/templates/infographic-tai-lieu.html,
// xuat-infographic.mjs, kiem-infographic.py). Ở đây giữ nguyên CSS mẫu + cách xuất + cổng đó, chỉ thêm
// bước đổi .md thành các khối của mẫu và tự chia trang (Fulfill viết HTML tay từng trang).
// Dùng: node scripts/sep-viec/pdf/lam_pdf.mjs <tệp.md> --ra <tệp.pdf> [--anh <thư-mục-ảnh-trang>]
//   Ảnh trong md (`![chú thích](anh.png)`, đường dẫn tương đối theo tệp md) hiện đúng chỗ; nhiều ảnh trên
//   cùng một dòng thì xếp cạnh nhau. Gạch đầu dòng mở bằng 🔴 🟡 🟢 ✅ thành thẻ màu; «**Ý chính.** chi tiết»
//   tách thành dòng đậm + dòng xám. Danh sách đánh số thành BƯỚC 1, 2… Dòng «Ký hiệu: …» thành nhãn màu.
// Một ảnh: node … <tệp.md> --mot-anh <tệp.png> — ảnh ngang 1080, cao vừa nội dung, không chia trang (tinh_tuy.py anh-chu).
import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, writeFileSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { basename, dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { marked } from 'marked'
import { chromium } from '@playwright/test'

const DAY = dirname(fileURLToPath(import.meta.url))
const thamSo = process.argv.slice(2)
const lay = (ten) => {
  const i = thamSo.indexOf(ten)
  return i >= 0 ? thamSo.splice(i, 2)[1] : null
}
const ra = lay('--ra')
const anhArg = lay('--anh')
const motAnh = lay('--mot-anh')
const md = thamSo[0] && resolve(thamSo[0])
if (!md || !(ra || motAnh) || !existsSync(md)) {
  console.error('Dùng: node scripts/sep-viec/pdf/lam_pdf.mjs <tệp.md> --ra <tệp.pdf> [--anh <thư-mục-ảnh-trang>]  |  <tệp.md> --mot-anh <tệp.png>')
  process.exit(2)
}
const pdf = resolve(ra || motAnh)
const ten = basename(pdf).replace(/\.(pdf|png)$/i, '')
const thuMuc = motAnh ? mkdtempSync(join(tmpdir(), 'mot-anh-')) : resolve(anhArg || join(dirname(pdf), `${ten}-trang`))
mkdirSync(thuMuc, { recursive: true })
const goc = dirname(md)

// ── CSS: khối đầu chép NGUYÊN mẫu Fulfill docs/templates/infographic-tai-lieu.html:19-53 ──
const CSS_MAU = `
@page{size:1080px 1600px;margin:0}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;background:#fff;color:#0f172a}
.page{width:1080px;height:1600px;padding:52px 56px;overflow:hidden;page-break-after:always;position:relative}
h1{font-size:50px;margin:0;line-height:1.15}h1 b{color:#f05a1a}
.sub{font-size:26px;color:#475569;margin:10px 0 26px}
.vi{color:#475569;font-weight:500}
h2{font-size:30px;margin:22px 0 12px;display:flex;align-items:center;gap:12px}
h2 .n{background:#0f172a;color:#fff;border-radius:50%;width:44px;height:44px;display:inline-flex;align-items:center;justify-content:center;font-size:24px;flex:none}
.leg{display:flex;gap:18px;margin-bottom:22px;font-size:24px}
.tag{padding:8px 18px;border-radius:30px;font-weight:700}
.c{background:#fff1e8;color:#c2410c;border:3px solid #f05a1a}.f{background:#e8f0ff;color:#1d4ed8;border:3px solid #2563eb}
.step{display:flex;gap:24px;align-items:center;border-radius:24px;padding:22px 28px;margin-bottom:6px}
.step.c{border:4px solid #f05a1a;color:inherit}.step.f{border:4px solid #2563eb;color:inherit}
.ic{font-size:64px;width:96px;text-align:center;flex:none}
.num{font-size:24px;font-weight:800;opacity:.75}
.t{font-size:34px;font-weight:800;line-height:1.2}
.d{font-size:26px;color:#334155;margin-top:6px;line-height:1.35}
.time{margin-left:auto;flex:none;font-size:28px;font-weight:800;padding:12px 18px;border-radius:16px;background:#0f172a;color:#fff;text-align:center;min-width:140px}
.arrow{text-align:center;font-size:36px;color:#94a3b8;line-height:1;margin:2px 0 6px}
.lane{display:flex;align-items:center;gap:10px;margin:10px 0;border-radius:22px;padding:14px}
.lane.ok{background:#ecfdf5;border:4px solid #16a34a}.lane.bad{background:#fef2f2;border:4px solid #dc2626}
.box{background:#fff;border-radius:16px;padding:14px 16px;font-size:22px;line-height:1.3;text-align:center;flex:1;border:2px solid #cbd5e1}
.box b{font-size:24px;display:block;margin-bottom:4px}
.ar{font-size:36px;color:#64748b;flex:none}
.res{flex:none;width:200px;text-align:center;font-size:24px;font-weight:800}
.res .e{font-size:54px;display:block}.ok .res{color:#15803d}.bad .res{color:#b91c1c}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:24px;margin:8px 0 18px}
th,td{border:2px solid #cbd5e1;padding:12px;text-align:left;vertical-align:top}
th{background:#2563eb;color:#fff}
.q{display:flex;gap:16px;align-items:flex-start;margin:12px 0;font-size:24px;line-height:1.35}
.q .qt{flex:none;background:#f05a1a;color:#fff;font-weight:800;border-radius:12px;padding:6px 12px}
.opt{display:inline-block;border:2px solid #94a3b8;border-radius:10px;padding:2px 10px;margin:6px 8px 0 0;font-size:22px}
.foot{position:absolute;bottom:34px;left:56px;right:56px;font-size:20px;color:#64748b;display:flex;justify-content:space-between}
.note{margin-top:18px;background:#fef9c3;border:3px solid #eab308;border-radius:20px;padding:18px 24px;font-size:26px;line-height:1.4}
code,.mono{font-family:Menlo,Consolas,monospace}
`
// ── Phần thêm cho khối sinh từ md: cùng bảng màu mẫu (đỏ/xanh lá của .lane, vàng của .note, cam/xanh của .c/.f) ──
const CSS_THEM = `
.step{margin-bottom:12px}
.step.do{background:#fef2f2;border:4px solid #dc2626}.step.vang{background:#fefce8;border:4px solid #eab308}
.step.xanh{background:#ecfdf5;border:4px solid #16a34a}.step.tron{background:#f1f5f9;border:3px solid #cbd5e1}
.step .ic{font-size:52px;width:72px}.step .t{font-size:30px}.step .d{font-size:25px}
.step.c .ic{font-size:44px;font-weight:800;color:#c2410c}
.step.tron .d{margin-top:0;font-size:26px;color:#0f172a}
.tag.do{background:#fef2f2;color:#b91c1c;border:3px solid #dc2626}.tag.vang{background:#fefce8;color:#a16207;border:3px solid #eab308}
.tag.xanh{background:#ecfdf5;color:#15803d;border:3px solid #16a34a}
.note{margin:0 0 14px}.note p{margin:0}.note p+p{margin-top:10px}
p.d{margin:4px 0 14px}
h2{background:#f1f5f9;border-radius:18px;padding:10px 16px;margin:18px 0 14px}
h2.nho{font-size:27px}
code{background:#e2e8f0;border-radius:8px;padding:1px 8px;font-size:.88em}
.anh-hang{display:flex;gap:24px;justify-content:center;align-items:flex-start;margin:6px 0 16px}
.anh-hang figure{margin:0;flex:0 1 auto;text-align:center;background:#e8f0ff;border:3px solid #2563eb;border-radius:20px;padding:12px}
.anh-hang img{display:block;max-width:100%;border-radius:10px;margin:0 auto}
.anh-hang figcaption{font-size:20px;color:#1d4ed8;font-weight:700;margin-top:8px}
.page.mot{width:720px;height:auto;padding:34px 30px 26px;overflow:visible}
.page.mot h1{font-size:44px}.page.mot .sub{font-size:28px;margin:8px 0 18px}
.page.mot .step{padding:16px 20px;gap:16px}.page.mot .step .ic{font-size:40px;width:52px}
.page.mot .step .t{font-size:30px}.page.mot .step .d{font-size:28px}.page.mot .step.tron .d{font-size:28px}
.page.mot .step.f{background:#e8f0ff}.page.mot .step.c{background:#fff1e8}.page.mot .step.c .ic{font-size:40px}
.page.mot h2{color:#fff;background:#2563eb}.page.mot h2.m1{background:#f05a1a}.page.mot h2.m2{background:#16a34a}.page.mot h2.m3{background:#ca8a04}
`

const NHOM = { '🔴': 'do', '🟡': 'vang', '🟢': 'xanh', '✅': 'xanh' }
const inl = (s) => marked.parseInline(s)
const thoat = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;')

// Một thẻ cho mỗi ý: «🔴 **Ý chính.** chi tiết» -> icon + dòng đậm + dòng xám.
function the(text, soThuTu) {
  let s = text.trim()
  const m = s.match(/^(🔴|🟡|🟢|✅)\s*/u)
  const icon = m ? m[1] : null
  if (m) s = s.slice(m[0].length)
  const dam = s.match(/^\*\*(.+?)\*\*\s*(.*)$/su)
  const lop = soThuTu ? 'c' : icon ? NHOM[icon] : 'tron'
  const ic = soThuTu ? String(soThuTu) : icon || '▸'
  const num = soThuTu ? `<div class="num">BƯỚC ${soThuTu}</div>` : ''
  // «**Ý chính**, chi tiết» — dấu phẩy nối câu đứng đầu dòng xám trông như lỗi, bỏ đi.
  const phu = dam ? dam[2].replace(/^[,;]\s*/u, '') : ''
  const than = dam
    ? `<div class="t">${inl(dam[1])}</div>${phu ? `<div class="d">${inl(phu)}</div>` : ''}`
    : soThuTu
      ? `<div class="t">${inl(s)}</div>`
      : `<div class="d">${inl(s)}</div>`
  return `<div class="step ${lop}"><div class="ic">${ic}</div><div>${num}${than}</div></div>`
}

function anhHang(tokens) {
  const imgs = tokens.filter((t) => t.type === 'image')
  // Hai ảnh dọc (điện thoại) cạnh nhau thấp hơn để còn chỗ cho các ý cùng mục trên một trang.
  const cao = imgs.length > 1 ? 860 : 1100
  const fig = imgs
    .map((t) => {
      const duong = /^(https?:|data:|file:)/.test(t.href) ? t.href : pathToFileURL(resolve(goc, decodeURI(t.href))).href
      return `<figure><img src="${thoat(duong)}" style="max-height:${cao}px"><figcaption>${inl(t.text || '')}</figcaption></figure>`
    })
    .join('')
  return `<div class="anh-hang">${fig}</div>`
}

// Đổi md thành danh sách khối; mỗi khối là một đơn vị khi chia trang (ý danh sách tách riêng từng thẻ).
const khoi = []
let tieuDe = ''
let daCoH1 = false
let sauH1 = false
for (const t of marked.lexer(readFileSync(md, 'utf8'))) {
  if (t.type === 'space' || t.type === 'hr') continue
  if (t.type === 'heading') {
    if (t.depth === 1 && !daCoH1) {
      daCoH1 = true
      sauH1 = true
      tieuDe = t.text
      khoi.push({ html: `<h1>${inl(t.text)}</h1>`, dau: true })
      continue
    }
    sauH1 = false
    const m = t.text.match(/^(\d+)\.\s+(.*)$/s)
    khoi.push({
      html: m
        ? `<h2><span class="n">${m[1]}</span>${inl(m[2])}</h2>`
        : `<h2 class="${t.depth > 2 ? 'nho' : ''}">${inl(t.text)}</h2>`,
      dau: true,
    })
    continue
  }
  if (t.type === 'paragraph') {
    const con = t.tokens || []
    if (con.some((x) => x.type === 'image') && con.every((x) => x.type === 'image' || /^\s*$/.test(x.raw))) {
      khoi.push({ html: anhHang(con) })
      continue
    }
    if (/^Ký hiệu\s*:/u.test(t.text)) {
      const nhan = [...t.text.matchAll(/(🔴|🟡|🟢|✅)\s*([^·🔴🟡🟢✅]+)/gu)]
        .map((x) => `<span class="tag ${NHOM[x[1]]}">${x[1]} ${inl(x[2].trim())}</span>`)
        .join('')
      khoi.push({ html: `<div class="leg">${nhan}</div>` })
      continue
    }
    // Đoạn ngay dưới tiêu đề = dòng phụ (.sub của mẫu); đoạn khác = khối ghi chú vàng để không thành tường chữ.
    if (sauH1) {
      khoi.push({ html: `<div class="sub">${inl(t.text)}</div>` })
      sauH1 = false
      continue
    }
    khoi.push({ html: `<div class="note"><p>${inl(t.text)}</p></div>` })
    continue
  }
  sauH1 = false
  if (t.type === 'list') {
    t.items.forEach((it, i) => khoi.push({ html: the(it.text, t.ordered ? (Number(t.start) || 1) + i : 0) }))
    continue
  }
  if (t.type === 'blockquote') {
    khoi.push({ html: `<div class="note">${marked.parse(t.text)}</div>` })
    continue
  }
  if (t.type === 'table' || t.type === 'code' || t.type === 'html') {
    khoi.push({ html: marked.parser([t]) })
    continue
  }
  khoi.push({ html: marked.parser([t]) })
}

const nguon = khoi.map((k) => `<div class="k${k.dau ? ' dau' : ''}">${k.html}</div>`).join('\n')
const htmlTep = join(thuMuc, `${ten}.html`)
writeFileSync(
  htmlTep,
  `<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>${thoat(tieuDe || ten)}</title>` +
    `<style>${CSS_MAU}${CSS_THEM}</style></head><body><div id="nguon">${nguon}</div></body></html>`
)

// WHY một ảnh (28/10, anh Thành chê ảnh anh-chu nền đen chữ bé «như cục cứt»): ảnh trong tin Telegram bị thu còn
// ~1/3 bề ngang, nên dựng khung 720 CSS px rồi chụp ×1,5 = 1080 px — chữ to gấp rưỡi bản trang 1080, cao vừa nội dung.
if (motAnh) {
  const b = await chromium.launch()
  try {
    const p = await b.newPage({ viewport: { width: 720, height: 600 }, deviceScaleFactor: 1.5 })
    await p.goto(pathToFileURL(htmlTep).href, { waitUntil: 'load' })
    await p.evaluate(() => {
      const n = document.getElementById('nguon')
      const pg = document.createElement('div')
      pg.className = 'page mot'
      while (n.firstChild) pg.appendChild(n.firstChild)
      n.replaceWith(pg)
      // Thẻ không icon màu thì tô theo mục (mỗi nhãn mục đổi màu) — ảnh xám một màu nhìn như bảng chữ.
      const mau = ['f', 'c', 'xanh', 'vang']
      let i = 0
      for (const k of pg.children) {
        if (k.querySelector('h2')) {
          i++
          k.querySelector('h2').classList.add('m' + (i % mau.length))
        }
        const st = k.querySelector('.step.tron')
        if (st) st.classList.replace('tron', mau[i % mau.length])
      }
    })
    await (await p.$('.page')).screenshot({ path: pdf })
  } finally {
    await b.close()
  }
  console.log(pdf)
  try {
    execFileSync('python3', [join(DAY, 'kiem_infographic.py'), pdf], { stdio: 'inherit' })
  } catch {
    process.exit(1)
  }
  process.exit(0)
}

// Chia trang trong trình duyệt: đáy nội dung ≤ DAY_TOI_DA (xuat-infographic.mjs bắt tràn ở 1540, chừa chỗ chân
// trang) và ≤ CHU_TOI_DA chữ (cổng 420). Tiêu đề mục không đứng cuối trang một mình.
const DAY_TOI_DA = 1480
const CHU_TOI_DA = 400
const anh = []
let tran = 0
const b = await chromium.launch()
try {
  const p = await b.newPage({ viewport: { width: 1080, height: 1600 } })
  await p.goto(pathToFileURL(htmlTep).href, { waitUntil: 'load' })
  const soTrang = await p.evaluate(
    ({ DAY_TOI_DA, CHU_TOI_DA, tieuDe }) => {
      const nguon = document.getElementById('nguon')
      const ds = [...nguon.children]
      const trang = []
      const moi = () => {
        const pg = document.createElement('div')
        pg.className = 'page'
        document.body.appendChild(pg)
        trang.push(pg)
        pg._chu = 0
        return pg
      }
      const dem = (e) => e.textContent.split(/\s+/).filter(Boolean).length
      const day = (pg) => {
        const top = pg.getBoundingClientRect().top
        let m = 0
        for (const c of pg.children) m = Math.max(m, c.getBoundingClientRect().bottom - top)
        return m
      }
      let pg = moi()
      for (const k of ds) {
        pg.appendChild(k)
        const chu = dem(k)
        if ((day(pg) > DAY_TOI_DA || pg._chu + chu > CHU_TOI_DA) && pg.children.length > 1) {
          // Kéo theo các tiêu đề đứng ngay trước khối này sang trang mới.
          const keo = [k]
          while (pg.children.length > keo.length && keo[0].previousElementSibling?.classList.contains('dau'))
            keo.unshift(keo[0].previousElementSibling)
          if (keo.length === pg.children.length) keo.splice(0, keo.length - 1)
          const cu = pg
          for (const x of keo) cu.removeChild(x)
          cu._chu -= keo.slice(0, -1).reduce((s, x) => s + dem(x), 0)
          pg = moi()
          for (const x of keo) pg.appendChild(x)
          pg._chu = keo.reduce((s, x) => s + dem(x), 0)
        } else pg._chu += chu
      }
      nguon.remove()
      trang.forEach((pg, i) => {
        const f = document.createElement('div')
        f.className = 'foot'
        const sau = i < trang.length - 1 ? `Tiếp trang ${i + 2} →` : 'Hết'
        f.innerHTML = `<span>Trang ${i + 1}/${trang.length} · ${tieuDe.replace(/</g, '&lt;')}</span><span>${sau}</span>`
        pg.appendChild(f)
      })
      return trang.length
    },
    { DAY_TOI_DA, CHU_TOI_DA, tieuDe }
  )
  writeFileSync(htmlTep, await p.content())
  // Từ đây giữ đúng xuat-infographic.mjs của Fulfill: đo tràn từng .page, chụp PNG, in PDF 1080×1600.
  const trang = await p.$$('.page')
  for (let i = 0; i < trang.length; i++) {
    const day = await trang[i].evaluate((e) => {
      const top = e.getBoundingClientRect().top
      let m = 0
      for (const c of e.querySelectorAll('*')) {
        if (getComputedStyle(c).position === 'absolute' || c.closest('.foot')) continue
        m = Math.max(m, c.getBoundingClientRect().bottom - top)
      }
      return Math.round(m)
    })
    if (day > 1540) {
      console.error(`✗ trang ${i + 1}: nội dung tràn (đáy ${day}px > 1540) — khối quá cao, tách ý hoặc bớt ảnh`)
      tran++
    }
    const duong = join(thuMuc, `${ten}-trang-${i + 1}.png`)
    await trang[i].screenshot({ path: duong })
    anh.push(duong)
  }
  await p.pdf({ path: pdf, width: '1080px', height: '1600px', printBackground: true })
  console.log(`Đã dựng ${soTrang} trang.`)
} finally {
  await b.close()
}
console.log('Đã xuất:\n  ' + [...anh, pdf].join('\n  '))
let rc = tran ? 1 : 0
try {
  execFileSync('python3', [join(DAY, 'kiem_infographic.py'), pdf, ...anh], { stdio: 'inherit' })
} catch {
  rc = 1
}
process.exit(rc)
