#!/usr/bin/env node
// BA BẢN THỬ — chủ nhà bấm chọn (univ3, học từ 13 kho — ĐX4). Màn đổi lớn: dựng 3 bản khác hẳn nhau,
// gom vào MỘT trang thử có nút 1·2·3 + một ảnh ghép «1A · 1B · 1C» để hỏi qua chat; chốt xong bản thua tự xoá.
//
//   node ~/.claude/skills/ba-ban-thu/ba-ban-thu.mjs dung --ten bang-don-moi \
//        --ban <url|/duong|tệp.html> --nhan "Gọn — bảng 1 dòng" \
//        --ban <…> --nhan "Thẻ — mỗi đơn 1 thẻ" \
//        --ban <…> --nhan "Hai cột — danh sách + chi tiết" \
//        [--tep-ban "2:src/app/thu/ban-2"]… [--thu-muc docs/ban-thu] [--rong 1440 --cao 900] [--dien-thoai]
//        [--cau-hinh docs/may-chup.json] [--khong-dang-nhap]
//   node ~/.claude/skills/ba-ban-thu/ba-ban-thu.mjs chot --ten bang-don-moi --chon 2 [--thu-muc docs/ban-thu]
//
// dung: ra <thu-muc>/<ten>/index.html (trang thử, phím 1/2/3) · ban-1..3.png (cắt sát nội dung) · ba-ban.png
//       (ảnh ghép ngang có nhãn 1A/1B/1C) · 1A.png 1B.png 1C.png (ảnh riêng cho điện thoại, nhãn ≥ 28 điểm)
//       · so.json (sổ: nguồn + tệp của từng bản).
// chot: xoá ĐÚNG các tệp đã khai của bản thua (--tep-ban lúc dựng + ảnh của nó, không ký tự đại diện),
//       ghi CHON.txt. Tệp ngoài thư mục dự án thì từ chối.
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { isAbsolute, join, relative, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { dangNhap, dichDen, docCauHinh, docThamSo, layChromium, so } from '../may-chup/chung.mjs'
import { COT_KHACH_MAC_DINH, NHAN_KHACH_MAC_DINH, veVaChe } from '../may-chup/may-chup.mjs'

const a = docThamSo(process.argv.slice(2))
const lenh = a._[0]
const ten = a.ten ? String(a.ten).replace(/[^\w-]/g, '-') : ''
const thuMuc = resolve(String(a['thu-muc'] ?? 'docs/ban-thu'), ten)

function tranh(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c])
}

function trongDuAn(p) {
  const r = relative(process.cwd(), resolve(p))
  return r && !r.startsWith('..') && !isAbsolute(r)
}

async function dung() {
  const ban = (a.ban ?? []).map(String)
  if (!ten || ban.length !== 3) {
    console.error('Dùng: … dung --ten <tên> --ban <1> --ban <2> --ban <3> [--nhan …]×3 (đúng 3 bản)')
    process.exit(2)
  }
  const nhan = (a.nhan ?? []).map(String)
  const tepBan = { 1: [], 2: [], 3: [] }
  for (const x of (a['tep-ban'] ?? []).map(String)) {
    const [n, ...p] = x.split(':')
    const duong = p.join(':')
    if (!tepBan[n] || !duong || !trongDuAn(duong)) {
      console.error(`--tep-ban "${x}" phải dạng "<1|2|3>:<đường dẫn trong dự án>".`)
      process.exit(2)
    }
    tepBan[n].push(duong)
  }
  let ch
  try {
    ch = docCauHinh(a)
  } catch (e) {
    console.error(String(e.message))
    process.exit(2)
  }
  mkdirSync(thuMuc, { recursive: true })
  // Nguồn: tệp .html trong máy → file://; còn lại là URL / đường dẫn của web dự án.
  const dich = ban.map((b) => (existsSync(b) ? pathToFileURL(resolve(b)).href : dichDen(ch, a, b)))
  const dt = a['dien-thoai'] === true
  const rong = so(a.rong, dt ? 390 : 1440)
  const cao = so(a.cao, dt ? 844 : 900)
  const chromium = await layChromium()
  const browser = await chromium.launch()
  const khung = [] // khung nội dung thật của từng bản (để báo cỡ chữ khi xem trên điện thoại)
  try {
    const ctx = await browser.newContext({
      viewport: { width: rong, height: cao },
      // ảnh nét gấp đôi: ảnh ghép thu nhỏ 3 bản vẫn phóng to được trên điện thoại
      deviceScaleFactor: 2,
      ...(dt ? { isMobile: true, hasTouch: true } : {}),
    })
    const page = await ctx.newPage()
    page.setDefaultTimeout(120_000)
    if (dich.some((d) => !d.startsWith('file:'))) await dangNhap(page, ch, a)
    for (let i = 0; i < 3; i++) {
      await page.goto(dich[i], { waitUntil: 'networkidle' }).catch(() => {})
      await page.waitForTimeout(so(a.cho, 2000))
      await page.evaluate(veVaChe, {
        khung: [],
        che: ch.che ?? [],
        tieuDe: '',
        nhanKhach: ch.nhan_khach ?? NHAN_KHACH_MAC_DINH,
        cotKhach: ch.cot_khach ?? COT_KHACH_MAC_DINH,
        mauPii: ch.mau_pii ?? [],
      })
      // W39 — CẮT SÁT NỘI DUNG: bản thử 3 dòng mà ảnh chụp nguyên khung 1440×900 thì 80% ảnh là nền trống,
      // ghép 3 ảnh lại chữ chỉ còn ~1 điểm ảnh trên điện thoại. Đo khung bao mọi phần tử CÓ nội dung
      // (chữ riêng / ảnh / ô nhập / nút) rồi chụp đúng khung đó (+ lề 24).
      const k = await page.evaluate(() => {
        let [x1, y1, x2, y2] = [Infinity, Infinity, 0, 0]
        for (const el of document.body.querySelectorAll('*')) {
          const coNoi =
            [...el.childNodes].some((n) => n.nodeType === 3 && n.nodeValue.trim()) ||
            el.matches('img, svg, canvas, video, input, select, textarea, button, table, [role="img"]')
          if (!coNoi) continue
          const r = el.getBoundingClientRect()
          if (r.width < 1 || r.height < 1 || getComputedStyle(el).visibility === 'hidden') continue
          x1 = Math.min(x1, r.left + scrollX)
          y1 = Math.min(y1, r.top + scrollY)
          x2 = Math.max(x2, r.right + scrollX)
          y2 = Math.max(y2, r.bottom + scrollY)
        }
        const W = document.documentElement.scrollWidth
        const H = document.documentElement.scrollHeight
        if (!Number.isFinite(x1)) return { x: 0, y: 0, width: innerWidth, height: innerHeight }
        const x = Math.max(0, x1 - 24)
        const y = Math.max(0, y1 - 24)
        return { x, y, width: Math.min(W, x2 + 24) - x, height: Math.max(200, Math.min(H, y2 + 24) - y) }
      })
      khung.push(k)
      await page.screenshot({ path: join(thuMuc, `ban-${i + 1}.png`), fullPage: true, clip: k })
    }
    const anh = [1, 2, 3].map((n) => readFileSync(join(thuMuc, `ban-${n}.png`)).toString('base64'))
    // Ảnh ghép NGANG 3 bản (xem trên máy tính / bấm phóng to). Cỡ chữ nhãn tính theo bề ngang điện thoại
    // 390 điểm: ảnh rộng 1800 → nhãn mã 1A/1B/1C 130px ≈ 28 điểm trên điện thoại, chữ mô tả 64px ≈ 14 điểm.
    const RONG_GHEP = 1800
    const o = (n) =>
      `<figure><figcaption><b>1${'ABC'[n]}</b><span>${tranh(nhan[n] ?? `Bản ${n + 1}`)}</span></figcaption><img src="data:image/png;base64,${anh[n]}"></figure>`
    await page.setViewportSize({ width: RONG_GHEP, height: 200 }) // thấp để fullPage cắt sát nội dung
    const coChu = (px) => Math.ceil((px * RONG_GHEP) / 390)
    await page.setContent(
      `<html><body style="margin:0;background:#f3f4f6;font-family:system-ui,sans-serif"><div style="display:flex;gap:20px;padding:20px;align-items:flex-start">${[0, 1, 2]
        .map(o)
        .join('')}</div><style>figure{margin:0;flex:1;min-width:0;background:#fff;border:4px solid #111827;border-radius:12px;overflow:hidden}figcaption{padding:14px 16px;background:#111827;color:#fff;display:flex;flex-direction:column;gap:6px}figcaption b{font-size:${coChu(28)}px;line-height:1;color:#fff;background:#e11d48;padding:4px 18px;border-radius:10px;align-self:flex-start}figcaption span{font-size:${coChu(14)}px;line-height:1.15;font-weight:700}img{width:100%;display:block}</style></body></html>`
    )
    await page.screenshot({ path: join(thuMuc, 'ba-ban.png'), fullPage: true, scale: 'css' })
    // Ba ảnh RIÊNG cho điện thoại (gửi album 3 ảnh): mỗi ảnh một bản, nhãn + mô tả ≥ 28 điểm khi ảnh
    // chiếm trọn bề ngang điện thoại. Chủ nhà vuốt qua 1A → 1B → 1C, gõ mã.
    for (let n = 0; n < 3; n++) {
      const R = Math.max(390, Math.min(1440, Math.round(khung[n].width)))
      await page.setViewportSize({ width: R, height: 200 })
      const c = (px) => Math.ceil((px * R) / 390)
      await page.setContent(
        `<html><body style="margin:0;background:#fff;font-family:system-ui,sans-serif"><div style="background:#111827;color:#fff;padding:${c(8)}px ${c(10)}px;display:flex;gap:${c(8)}px;align-items:center"><b style="font-size:${c(30)}px;line-height:1;background:#e11d48;padding:${c(3)}px ${c(8)}px;border-radius:${c(5)}px">1${'ABC'[n]}</b><span style="font-size:${c(28)}px;line-height:1.1;font-weight:700">${tranh(nhan[n] ?? `Bản ${n + 1}`)}</span></div><img style="width:100%;display:block" src="data:image/png;base64,${anh[n]}"></body></html>`
      )
      await page.screenshot({ path: join(thuMuc, `1${'ABC'[n]}.png`), fullPage: true, scale: 'css' })
    }
  } finally {
    await browser.close()
  }
  // Trang thử: nút 1·2·3 + phím 1/2/3, bản đang xem nằm trong khung; ảnh tĩnh làm dự phòng khi nguồn cần đăng nhập.
  const nut = [0, 1, 2]
    .map(
      (i) =>
        `<button data-n="${i + 1}"><b>${i + 1}</b> ${tranh(nhan[i] ?? `Bản ${i + 1}`)}</button>`
    )
    .join('')
  writeFileSync(
    join(thuMuc, 'index.html'),
    `<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ba bản thử · ${tranh(ten)}</title>
<style>body{margin:0;font-family:system-ui,sans-serif;background:#f3f4f6}header{display:flex;gap:8px;align-items:center;padding:10px;background:#111827;color:#fff;position:sticky;top:0}
button{font:600 15px system-ui;padding:10px 14px;min-height:44px;border-radius:8px;border:2px solid #374151;background:#1f2937;color:#fff;cursor:pointer}button b{background:#e11d48;border-radius:5px;padding:1px 8px;margin-right:6px}
button[aria-pressed=true]{border-color:#e11d48;background:#fff;color:#111827}label{margin-left:auto;font-size:14px}iframe,img{display:block;width:100%;border:0;background:#fff}iframe{height:calc(100vh - 64px)}</style>
<header>${nut}<label><input type="checkbox" id="anh"> Xem ảnh tĩnh</label></header><main></main>
<script>const NGUON=${JSON.stringify(dich)};let n=1;const ve=()=>{document.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.n==n));
const m=document.querySelector('main');m.innerHTML=document.getElementById('anh').checked?'<img src="ban-'+n+'.png">':'<iframe src="'+NGUON[n-1]+'"></iframe>'};
document.querySelectorAll('button').forEach(b=>b.onclick=()=>{n=+b.dataset.n;ve()});document.getElementById('anh').onchange=ve;
addEventListener('keydown',e=>{if('123'.includes(e.key)){n=+e.key;ve()}});ve()</script></html>`
  )
  const so_ = {
    ten,
    luc: new Date().toISOString(),
    ban: [0, 1, 2].map((i) => ({ so: i + 1, nguon: ban[i], nhan: nhan[i] ?? '', tep: tepBan[i + 1] })),
  }
  writeFileSync(join(thuMuc, 'so.json'), JSON.stringify(so_, null, 1))
  console.log(`ĐÃ DỰNG ba bản thử «${ten}»:`)
  console.log(`  Trang thử: ${join(thuMuc, 'index.html')} (nút hoặc phím 1/2/3)`)
  console.log(`  Ảnh ghép ngang (máy tính): ${join(thuMuc, 'ba-ban.png')} — câu hỏi kèm mã 1A · 1B · 1C`)
  console.log(`  Ba ảnh riêng cho điện thoại (gửi album 3 ảnh): ${['1A', '1B', '1C'].map((x) => join(thuMuc, `${x}.png`)).join(' · ')}`)
  console.log(`  Chốt: node ~/.claude/skills/ba-ban-thu/ba-ban-thu.mjs chot --ten ${ten} --chon <1|2|3>`)
}

function chot() {
  const chon = Number(a.chon)
  const tep = join(thuMuc, 'so.json')
  if (!ten || ![1, 2, 3].includes(chon) || !existsSync(tep)) {
    console.error('Dùng: … chot --ten <tên> --chon <1|2|3> (phải có sổ so.json từ lượt dựng)')
    process.exit(2)
  }
  const so_ = JSON.parse(readFileSync(tep, 'utf8'))
  const daXoa = []
  for (const b of so_.ban) {
    if (b.so === chon) continue
    const anhBan = [`ban-${b.so}.png`, `1${'ABC'[b.so - 1]}.png`].map((x) => relative(process.cwd(), join(thuMuc, x)))
    for (const p of [...b.tep, ...anhBan]) {
      if (!trongDuAn(p)) {
        console.error(`(bỏ qua) «${p}» nằm ngoài dự án — không xoá.`)
        continue
      }
      if (!existsSync(p)) continue
      rmSync(p, { recursive: true })
      daXoa.push(p)
    }
  }
  const thang = so_.ban.find((b) => b.so === chon)
  writeFileSync(
    join(thuMuc, 'CHON.txt'),
    `Chủ nhà chọn bản ${chon} — ${thang.nhan}\nNguồn: ${thang.nguon}\nLúc: ${new Date().toISOString()}\nĐã xoá bản thua:\n${daXoa.map((x) => `- ${x}`).join('\n') || '- (không có tệp khai)'}\n`
  )
  console.log(`ĐÃ CHỐT bản ${chon} «${thang.nhan}». Xoá ${daXoa.length} tệp của bản thua:`)
  for (const x of daXoa) console.log(`  - ${x}`)
}

if (lenh === 'dung') await dung()
else if (lenh === 'chot') chot()
else {
  console.error('Dùng: ba-ban-thu.mjs dung|chot … (xem đầu tệp)')
  process.exit(2)
}
