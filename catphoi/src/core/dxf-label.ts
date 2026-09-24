/**
 * ĐỌC TÊN MÃ PHÔI TỪ CHỮ TRONG FILE DXF.
 *
 * Bản vẽ thật của xưởng ghi tên chi tiết bằng MTEXT rải rác quanh hình, KHÔNG
 * phải một dòng liền: tên "mạn 15" nằm thành hai mảnh chữ rời cạnh nhau
 * ({mạn} ở một chỗ, {15} cách đó ~360mm). Ngoài ra còn lẫn chữ kích thước
 * (4520, R500, (5300), 9.9x1500, s=9.9) và chữ rác ở tận x ≈ 2.850.000.
 *
 * CÁCH LÀM — ba bước, mỗi bước có một luật rõ ràng:
 *
 *  1. LỌC. Bỏ mảnh chữ rõ ràng là kích thước. Luật: số nguyên ≤ 3 chữ số là
 *     SỐ HIỆU SƯỜN (15/16/17/19) nên GIỮ; mọi con số khác (≥ 4 chữ số, số thập
 *     phân, số trong ngoặc) là kích thước nên BỎ. Cộng thêm vài khuôn mẫu
 *     quen thuộc: R500 · ø20 · 9.9x1500 · s=9.9 · 1200mm.
 *     Trên file mẫu luật này bỏ đúng 9 mảnh "4520" và giữ đúng 15/16/17/19.
 *
 *  2. GÁN CHO CHI TIẾT. Mỗi mảnh chữ về tay chi tiết mà nó NẰM TRONG, nếu
 *     không nằm trong hình nào thì về tay chi tiết GẦN NHẤT (khoảng cách từ
 *     điểm đặt chữ tới biên). Bỏ hẳn mảnh chữ ở quá xa — ngưỡng
 *     max(20 × cỡ chữ, nửa đường chéo khung bao chi tiết gần nhất) — chính là
 *     thứ loại được mảnh {S10} nằm cách chi tiết gần nhất 1.551.173mm.
 *
 *  3. GOM THÀNH TÊN. Trong một chi tiết, các mảnh chữ được gom cụm theo kiểu
 *     "dây chuyền đơn" (single linkage) với bán kính 4,5 × cỡ chữ (≈ 405mm với
 *     chữ cao 90): hai mảnh gần nhau hơn bán kính đó coi là CÙNG MỘT TÊN.
 *     Trong một cụm: chữ trước, số sau (nên "{15}" + "{mạn}" vẫn đọc ra
 *     "mạn 15" chứ không phải "15 mạn"), mỗi nhóm theo thứ tự đọc
 *     (trên → dưới, rồi trái → phải).
 *     Các cụm của cùng chi tiết xếp theo thứ tự đọc rồi nối bằng " · ".
 *     Cụm nào có tập từ là TẬP CON của cụm khác thì bỏ (cụm "17" biến mất khi
 *     đã có cụm "mạn 17").
 */
import type { Point, Ring } from '../types';
import { pointInRing, pointSegDistance } from './geometry';

/** Một mảnh chữ đọc được từ DXF, toạ độ đã nhân unitScale. */
export interface DxfText {
  x: number;
  y: number;
  /** Cỡ chữ (mm) — dùng làm thước cho mọi ngưỡng khoảng cách. */
  h: number;
  /** Nội dung đã bóc hết mã định dạng MTEXT. */
  text: string;
}

/** Bóc mã định dạng của MTEXT: {\fTimes New Roman|b0|i0|c0|p18;mạn} → mạn */
export function cleanMText(raw: string): string {
  let t = raw;
  t = t.replace(/\\P/g, ' ').replace(/\\~/g, ' ');
  t = t.replace(/\\[fF][^;]*;/g, '');
  t = t.replace(/\\[HWTQAC][^;\\]*;/g, '');
  t = t.replace(/\\p[^;]*;/g, '');
  t = t.replace(/\\S([^;]*);/g, '$1');
  t = t.replace(/\\[LlOoKkNnXx]/g, '');
  t = t.replace(/[{}]/g, '');
  t = t.replace(/\\([\\{}])/g, '$1');
  return t.replace(/\s+/g, ' ').trim();
}

/** Khuôn mẫu chữ KÍCH THƯỚC — gặp là bỏ. */
const DIM_PATTERNS: RegExp[] = [
  /^\(?\s*[-+]?\d+(?:[.,]\d+)?\s*\)?$/, // thuần số, kể cả (5300) và số thập phân
  /^[Rr]\s*\d/, // R500
  /^(?:%%c|%%C|[øØ∅Ø])\s*\d/, // ø20
  /^\d+(?:[.,]\d+)?\s*[xX×*]\s*\d/, // 9.9x1500
  /^[sStTdD]\s*=/, // s=9.9
  /^\d+(?:[.,]\d+)?\s*(?:mm|cm|m|kg|°|%%d)$/i, // 1200mm
];

/**
 * Mảnh chữ này có phải TÊN không?
 * Số nguyên ≤ 3 chữ số = số hiệu sườn → là tên. Mọi số khác → kích thước.
 */
export function isNameFragment(s: string): boolean {
  if (!s) return false;
  if (/^\d{1,3}$/.test(s)) return true;
  for (const re of DIM_PATTERNS) if (re.test(s)) return false;
  if (!/[\p{L}\p{N}]/u.test(s)) return false;
  return true;
}

function isNumberToken(s: string): boolean {
  return /^\d+$/.test(s);
}

/** Khoảng cách từ điểm tới một vòng (0 nếu nằm trong vòng). */
function distToRing(p: Point, ring: Ring): number {
  if (pointInRing(p, ring)) return 0;
  let min = Infinity;
  for (let i = 0; i < ring.length; i++) {
    const d = pointSegDistance(p, ring[i], ring[(i + 1) % ring.length]);
    if (d < min) min = d;
  }
  return min;
}

/** Thứ tự đọc: trên xuống dưới, rồi trái sang phải. */
function readingOrder(a: DxfText, b: DxfText): number {
  if (Math.abs(a.y - b.y) > 1e-9) return b.y - a.y;
  return a.x - b.x;
}

/** Gom một nhóm mảnh chữ (đã thuộc cùng 1 chi tiết) thành chuỗi tên. */
export function buildLabel(frags: DxfText[]): string {
  if (frags.length === 0) return '';
  const h = frags.reduce((s, f) => s + (f.h > 0 ? f.h : 0), 0) / frags.length;
  const radius = h > 0 ? 4.5 * h : 400;

  // gom cụm kiểu dây chuyền đơn
  const n = frags.length;
  const owner = new Array<number>(n).fill(-1);
  const find = (i: number): number => (owner[i] < 0 ? i : (owner[i] = find(owner[i])));
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const d = Math.hypot(frags[i].x - frags[j].x, frags[i].y - frags[j].y);
      if (d > radius) continue;
      const a = find(i);
      const b = find(j);
      if (a !== b) owner[a] = b;
    }
  }
  const buckets = new Map<number, DxfText[]>();
  for (let i = 0; i < n; i++) {
    const r = find(i);
    const arr = buckets.get(r);
    if (arr) arr.push(frags[i]);
    else buckets.set(r, [frags[i]]);
  }

  interface Cluster { text: string; tokens: Set<string>; top: DxfText }
  const clusters: Cluster[] = [];
  for (const arr of buckets.values()) {
    const sorted = arr.slice().sort(readingOrder);
    const words = sorted.filter((f) => !isNumberToken(f.text)).map((f) => f.text);
    const nums = sorted.filter((f) => isNumberToken(f.text)).map((f) => f.text);
    const seen = new Set<string>();
    const parts: string[] = [];
    for (const w of words.concat(nums)) {
      if (seen.has(w)) continue;
      seen.add(w);
      parts.push(w);
    }
    if (parts.length === 0) continue;
    clusters.push({ text: parts.join(' '), tokens: seen, top: sorted[0] });
  }
  clusters.sort((a, b) => readingOrder(a.top, b.top));

  // bỏ cụm có tập từ là tập con của cụm khác ("17" bỏ khi đã có "mạn 17")
  const keep: string[] = [];
  const used = new Set<string>();
  for (let i = 0; i < clusters.length; i++) {
    let subsumed = false;
    for (let j = 0; j < clusters.length && !subsumed; j++) {
      if (i === j) continue;
      if (clusters[j].tokens.size < clusters[i].tokens.size) continue;
      if (clusters[j].tokens.size === clusters[i].tokens.size && j > i) continue;
      let all = true;
      for (const t of clusters[i].tokens) if (!clusters[j].tokens.has(t)) { all = false; break; }
      if (all) subsumed = true;
    }
    if (subsumed) continue;
    if (used.has(clusters[i].text)) continue;
    used.add(clusters[i].text);
    keep.push(clusters[i].text);
  }
  return keep.join(' · ');
}

/**
 * Gán mảnh chữ cho chi tiết rồi dựng tên.
 * @param outers vòng ngoài của từng chi tiết, TOẠ ĐỘ GỐC trong file (chưa dịch về 0).
 * @returns mảng cùng độ dài `outers`, phần tử là tên đọc được ('' nếu không có chữ nào).
 */
export function assignLabels(texts: DxfText[], outers: Ring[]): string[] {
  const out = new Array<string>(outers.length).fill('');
  if (outers.length === 0) return out;

  const boxes = outers.map((r) => {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const p of r) {
      if (p.x < minX) minX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.x > maxX) maxX = p.x;
      if (p.y > maxY) maxY = p.y;
    }
    return { minX, minY, maxX, maxY, diag: Math.hypot(maxX - minX, maxY - minY) };
  });

  const groups = new Map<number, DxfText[]>();
  for (const t of texts) {
    if (!isNameFragment(t.text)) continue;
    let bestI = -1;
    let bestD = Infinity;
    for (let i = 0; i < outers.length; i++) {
      const b = boxes[i];
      // cận dưới rẻ tiền: khoảng cách tới khung bao ≤ khoảng cách tới biên thật
      const dx = t.x < b.minX ? b.minX - t.x : t.x > b.maxX ? t.x - b.maxX : 0;
      const dy = t.y < b.minY ? b.minY - t.y : t.y > b.maxY ? t.y - b.maxY : 0;
      if (Math.hypot(dx, dy) >= bestD) continue;
      const d = distToRing(t, outers[i]);
      if (d < bestD) {
        bestD = d;
        bestI = i;
      }
    }
    if (bestI < 0) continue;
    // chữ rác ở quá xa thì bỏ hẳn
    const limit = Math.max(t.h > 0 ? 20 * t.h : 2000, 0.5 * boxes[bestI].diag);
    if (bestD > limit) continue;
    const arr = groups.get(bestI);
    if (arr) arr.push(t);
    else groups.set(bestI, [t]);
  }

  for (const [i, arr] of groups) out[i] = buildLabel(arr);
  return out;
}
