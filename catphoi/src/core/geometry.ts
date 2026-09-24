/**
 * Hình học cơ bản dùng chung: convex hull, rotating calipers, Douglas-Peucker,
 * point-in-polygon, khoảng cách đoạn–đoạn.
 */
import type { Point, Ring, BBox } from '../types';
import { signedArea, ringBBox } from '../types';

/** Bao lồi (convex hull) theo thuật toán monotone chain. Trả về CCW, không lặp đỉnh đầu. */
export function convexHull(pts: Point[]): Point[] {
  if (pts.length < 3) return pts.slice();
  const p = pts.slice().sort((a, b) => (a.x === b.x ? a.y - b.y : a.x - b.x));
  const cross = (o: Point, a: Point, b: Point) =>
    (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const lower: Point[] = [];
  for (const q of p) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], q) <= 0) lower.pop();
    lower.push(q);
  }
  const upper: Point[] = [];
  for (let i = p.length - 1; i >= 0; i--) {
    const q = p[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], q) <= 0) upper.pop();
    upper.push(q);
  }
  lower.pop();
  upper.pop();
  return lower.concat(upper);
}

/** Bề rộng nhỏ nhất khi xoay (rotating calipers) + góc tương ứng (radian). */
export function minWidthOfHull(hull: Point[]): { width: number; angle: number } {
  const n = hull.length;
  if (n < 2) return { width: 0, angle: 0 };
  let best = Infinity;
  let bestAngle = 0;
  for (let i = 0; i < n; i++) {
    const a = hull[i];
    const b = hull[(i + 1) % n];
    const ex = b.x - a.x;
    const ey = b.y - a.y;
    const len = Math.hypot(ex, ey);
    if (len < 1e-9) continue;
    const nx = -ey / len;
    const ny = ex / len;
    let maxD = 0;
    for (let k = 0; k < n; k++) {
      const d = Math.abs((hull[k].x - a.x) * nx + (hull[k].y - a.y) * ny);
      if (d > maxD) maxD = d;
    }
    if (maxD < best) {
      best = maxD;
      bestAngle = Math.atan2(ey, ex);
    }
  }
  return { width: best === Infinity ? 0 : best, angle: bestAngle };
}

/** Đường kính bao lồi (khoảng cách 2 điểm xa nhau nhất). */
export function hullDiameter(hull: Point[]): number {
  let best = 0;
  for (let i = 0; i < hull.length; i++) {
    for (let j = i + 1; j < hull.length; j++) {
      const d = Math.hypot(hull[i].x - hull[j].x, hull[i].y - hull[j].y);
      if (d > best) best = d;
    }
  }
  return best;
}

/** Xoay 1 mảng điểm quanh gốc toạ độ. */
export function rotatePoints(pts: Point[], angleRad: number): Point[] {
  const c = Math.cos(angleRad);
  const s = Math.sin(angleRad);
  return pts.map((p) => ({ x: p.x * c - p.y * s, y: p.x * s + p.y * c }));
}

/** Kiểm tra hình (qua bao lồi) có lọt tấm W×H khi xoay hay không. */
export function fitsInSheet(hull: Point[], W: number, H: number, stepDeg = 1): boolean {
  for (let deg = 0; deg < 180; deg += stepDeg) {
    const r = rotatePoints(hull, (deg * Math.PI) / 180);
    const b = ringBBox(r);
    const w = b.maxX - b.minX;
    const h = b.maxY - b.minY;
    if ((w <= W && h <= H) || (w <= H && h <= W)) return true;
  }
  return false;
}

/** Điểm nằm trong vòng kín (ray casting, even-odd). Biên coi như nằm trong. */
export function pointInRing(pt: Point, ring: Ring): boolean {
  let inside = false;
  const n = ring.length;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const yi = ring[i].y;
    const yj = ring[j].y;
    if (yi > pt.y !== yj > pt.y) {
      const xCross = ring[i].x + ((pt.y - yi) / (yj - yi)) * (ring[j].x - ring[i].x);
      if (pt.x < xCross) inside = !inside;
    }
  }
  return inside;
}

/** Chu vi vòng kín. */
export function ringLength(ring: Ring): number {
  let s = 0;
  for (let i = 0; i < ring.length; i++) {
    const a = ring[i];
    const b = ring[(i + 1) % ring.length];
    s += Math.hypot(b.x - a.x, b.y - a.y);
  }
  return s;
}

/** Douglas-Peucker cho chuỗi hở. */
function dpOpen(pts: Point[], tol: number): Point[] {
  if (pts.length < 3) return pts.slice();
  const keep = new Uint8Array(pts.length);
  keep[0] = 1;
  keep[pts.length - 1] = 1;
  const stack: [number, number][] = [[0, pts.length - 1]];
  while (stack.length) {
    const [i0, i1] = stack.pop()!;
    if (i1 - i0 < 2) continue;
    const a = pts[i0];
    const b = pts[i1];
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const len = Math.hypot(dx, dy);
    let best = -1;
    let bestD = tol;
    for (let k = i0 + 1; k < i1; k++) {
      const p = pts[k];
      let d: number;
      if (len < 1e-12) d = Math.hypot(p.x - a.x, p.y - a.y);
      else d = Math.abs((p.x - a.x) * dy - (p.y - a.y) * dx) / len;
      if (d > bestD) {
        bestD = d;
        best = k;
      }
    }
    if (best >= 0) {
      keep[best] = 1;
      stack.push([i0, best], [best, i1]);
    }
  }
  const out: Point[] = [];
  for (let i = 0; i < pts.length; i++) if (keep[i]) out.push(pts[i]);
  return out;
}

/**
 * Douglas-Peucker cho VÒNG KÍN. Chia vòng tại 2 đỉnh xa nhau nhất rồi ghép lại,
 * để kết quả không phụ thuộc vào điểm bắt đầu tuỳ tiện.
 */
export function simplifyRing(ring: Ring, tolerance: number): Ring {
  const n = ring.length;
  if (n <= 4 || tolerance <= 0) return ring.slice();
  // tìm đỉnh xa đỉnh 0 nhất làm mốc chia
  let far = 0;
  let farD = -1;
  for (let i = 1; i < n; i++) {
    const d = Math.hypot(ring[i].x - ring[0].x, ring[i].y - ring[0].y);
    if (d > farD) {
      farD = d;
      far = i;
    }
  }
  const partA = ring.slice(0, far + 1);
  const partB = ring.slice(far).concat([ring[0]]);
  const sa = dpOpen(partA, tolerance);
  const sb = dpOpen(partB, tolerance);
  const out = sa.slice(0, -1).concat(sb.slice(0, -1));
  return out.length >= 3 ? out : ring.slice();
}

/** Khoảng cách giữa 2 đoạn thẳng. */
export function segSegDistance(a1: Point, a2: Point, b1: Point, b2: Point): number {
  if (segSegIntersect(a1, a2, b1, b2)) return 0;
  return Math.min(
    pointSegDistance(a1, b1, b2),
    pointSegDistance(a2, b1, b2),
    pointSegDistance(b1, a1, a2),
    pointSegDistance(b2, a1, a2)
  );
}

export function pointSegDistance(p: Point, a: Point, b: Point): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const l2 = dx * dx + dy * dy;
  if (l2 < 1e-18) return Math.hypot(p.x - a.x, p.y - a.y);
  let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / l2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}

export function segSegIntersect(p1: Point, p2: Point, p3: Point, p4: Point): boolean {
  const d = (p2.x - p1.x) * (p4.y - p3.y) - (p2.y - p1.y) * (p4.x - p3.x);
  if (Math.abs(d) < 1e-12) return false;
  const t = ((p3.x - p1.x) * (p4.y - p3.y) - (p3.y - p1.y) * (p4.x - p3.x)) / d;
  const u = ((p3.x - p1.x) * (p2.y - p1.y) - (p3.y - p1.y) * (p2.x - p1.x)) / d;
  return t >= 0 && t <= 1 && u >= 0 && u <= 1;
}

/** Vòng A có nằm hoàn toàn trong vòng B không (kiểm bbox + vài đỉnh đại diện). */
export function ringInsideRing(a: Ring, b: Ring): boolean {
  const ba = ringBBox(a);
  const bb = ringBBox(b);
  const eps = 1e-6;
  if (ba.minX < bb.minX - eps || ba.maxX > bb.maxX + eps) return false;
  if (ba.minY < bb.minY - eps || ba.maxY > bb.maxY + eps) return false;
  let votes = 0;
  const samples = Math.min(5, a.length);
  for (let i = 0; i < samples; i++) {
    const p = a[Math.floor((i * a.length) / samples)];
    if (pointInRing(p, b)) votes++;
  }
  return votes * 2 > samples;
}

/** Ép chiều vòng: CCW cho outer, CW cho hole. */
export function orient(ring: Ring, ccw: boolean): Ring {
  const a = signedArea(ring);
  if (ccw ? a < 0 : a > 0) return ring.slice().reverse();
  return ring.slice();
}

export function translateRing(ring: Ring, dx: number, dy: number): Ring {
  return ring.map((p) => ({ x: p.x + dx, y: p.y + dy }));
}

export type { BBox };

// ───────────────────── Khung bao nhỏ nhất khi xoay (min-width rectangle) ─────────────────────

export interface MinRect {
  /** Cạnh dài của khung bao nhỏ nhất khi xoay, mm. */
  length: number;
  /** Cạnh ngắn = bề rộng nhỏ nhất khi xoay, mm. */
  width: number;
  /** Góc (radian) của cạnh DÀI so với trục X. Xoay hình đi -angle là hình nằm ngang. */
  angle: number;
}

/**
 * Khung bao chữ nhật NHỎ NHẤT KHI XOAY (minimum-width bounding rectangle).
 *
 * Vì sao cần: các thanh sườn cong nằm CHÉO trong bản vẽ gốc, nên khung bao theo
 * trục toạ độ (bbox) cho ra số vô nghĩa — ví dụ P0 ra 3409×3996 trong khi thanh
 * thật dài 5253mm, bề rộng nhỏ nhất khi xoay chỉ 1172mm.
 *
 * Thuật toán: rotating calipers. Khung bao nhỏ nhất luôn có MỘT CẠNH ÁP SÁT một
 * cạnh của bao lồi, nên chỉ cần duyệt hết các cạnh bao lồi — kết quả là giá trị
 * nhỏ nhất ĐÚNG (không phải xấp xỉ theo bước quét góc).
 */
export function minAreaRect(pts: Point[]): MinRect {
  const hull = pts.length > 8 ? convexHull(pts) : convexHull(pts.slice());
  const n = hull.length;
  if (n < 2) return { length: 0, width: 0, angle: 0 };
  if (n === 2) {
    return {
      length: Math.hypot(hull[1].x - hull[0].x, hull[1].y - hull[0].y),
      width: 0,
      angle: Math.atan2(hull[1].y - hull[0].y, hull[1].x - hull[0].x),
    };
  }
  let best: MinRect = { length: 0, width: Infinity, angle: 0 };
  for (let i = 0; i < n; i++) {
    const a = hull[i];
    const b = hull[(i + 1) % n];
    const ex = b.x - a.x;
    const ey = b.y - a.y;
    const len = Math.hypot(ex, ey);
    if (len < 1e-9) continue;
    const ux = ex / len;
    const uy = ey / len;
    const nx = -uy;
    const ny = ux;
    let minU = Infinity, maxU = -Infinity, minV = Infinity, maxV = -Infinity;
    for (const p of hull) {
      const u = (p.x - a.x) * ux + (p.y - a.y) * uy;
      const v = (p.x - a.x) * nx + (p.y - a.y) * ny;
      if (u < minU) minU = u;
      if (u > maxU) maxU = u;
      if (v < minV) minV = v;
      if (v > maxV) maxV = v;
    }
    const w = maxV - minV;
    if (w < best.width) {
      const l = maxU - minU;
      // cạnh dài luôn là "length"
      best = w <= l
        ? { length: l, width: w, angle: Math.atan2(ey, ex) }
        : { length: w, width: l, angle: Math.atan2(ny, nx) };
    }
  }
  if (!Number.isFinite(best.width)) return { length: 0, width: 0, angle: 0 };
  return best;
}

// ───────────────────── Điểm đặt nhãn (pole of inaccessibility) ─────────────────────

function segDistSq(x: number, y: number, a: Point, b: Point): number {
  let px = a.x;
  let py = a.y;
  let dx = b.x - px;
  let dy = b.y - py;
  if (dx !== 0 || dy !== 0) {
    const t = ((x - px) * dx + (y - py) * dy) / (dx * dx + dy * dy);
    if (t > 1) {
      px = b.x;
      py = b.y;
    } else if (t > 0) {
      px += dx * t;
      py += dy * t;
    }
  }
  dx = x - px;
  dy = y - py;
  return dx * dx + dy * dy;
}

/**
 * Khoảng cách CÓ DẤU từ (x,y) tới biên đa giác nhiều vòng.
 * Dương = nằm trong chi tiết (ngoài mọi lỗ), âm = nằm ngoài.
 */
function signedDistToRings(x: number, y: number, rings: Ring[]): number {
  let inside = false;
  let minSq = Infinity;
  for (const ring of rings) {
    const len = ring.length;
    for (let i = 0, j = len - 1; i < len; j = i++) {
      const a = ring[i];
      const b = ring[j];
      if (a.y > y !== b.y > y && x < ((b.x - a.x) * (y - a.y)) / (b.y - a.y) + a.x) inside = !inside;
      const d = segDistSq(x, y, a, b);
      if (d < minSq) minSq = d;
    }
  }
  const d = Math.sqrt(minSq);
  return inside ? d : -d;
}

interface LabelCell {
  x: number;
  y: number;
  /** nửa cạnh ô */
  h: number;
  /** khoảng cách có dấu từ tâm ô tới biên */
  d: number;
  /** cận trên của d trong ô này */
  max: number;
}

function makeCell(x: number, y: number, h: number, rings: Ring[]): LabelCell {
  const d = signedDistToRings(x, y, rings);
  return { x, y, h, d, max: d + h * Math.SQRT2 };
}

/**
 * Điểm đặt nhãn: "pole of inaccessibility" — điểm NẰM SÂU NHẤT bên trong hình
 * (thuật toán polylabel của Mapbox, ISC license, viết lại cho kiểu dữ liệu ở đây).
 *
 * Vì sao không dùng trọng tâm: thanh sườn cong hình chữ S có trọng tâm rơi RA
 * NGOÀI hình, nhãn P0/P3/P10 bay ra khoảng trống giữa hai chi tiết. Điểm cực
 * luôn nằm trong đa giác, kể cả hình lõm và hình có lỗ (lỗ được tính là biên).
 *
 * @param rings rings[0] = biên ngoài, rings[1..] = lỗ.
 */
export function labelPoint(rings: Ring[], precision?: number): Point {
  const outer = rings[0];
  if (!outer || outer.length < 3) return outer?.[0] ?? { x: 0, y: 0 };
  const bb = ringBBox(outer);
  const w = bb.maxX - bb.minX;
  const h = bb.maxY - bb.minY;
  const cellSize = Math.min(w, h);
  if (cellSize <= 0) return { x: bb.minX, y: bb.minY };
  const prec = precision ?? Math.max(0.5, cellSize / 400);

  let half = cellSize / 2;
  // hàng đợi ưu tiên đơn giản: mảng + lấy phần tử max (số ô luôn nhỏ, đủ nhanh)
  const queue: LabelCell[] = [];
  const push = (c: LabelCell) => {
    queue.push(c);
  };
  const pop = (): LabelCell => {
    let bi = 0;
    for (let i = 1; i < queue.length; i++) if (queue[i].max > queue[bi].max) bi = i;
    const c = queue[bi];
    queue[bi] = queue[queue.length - 1];
    queue.pop();
    return c;
  };

  for (let x = bb.minX; x < bb.maxX; x += cellSize) {
    for (let y = bb.minY; y < bb.maxY; y += cellSize) {
      push(makeCell(x + half, y + half, half, rings));
    }
  }

  // khởi đầu: tâm bbox và trọng tâm (chỉ làm mốc, có thể nằm ngoài hình)
  let best = makeCell(bb.minX + w / 2, bb.minY + h / 2, 0, rings);
  let cx = 0;
  let cy = 0;
  let area2 = 0;
  for (let i = 0, j = outer.length - 1; i < outer.length; j = i++) {
    const a = outer[i];
    const b = outer[j];
    const f = a.x * b.y - b.x * a.y;
    cx += (a.x + b.x) * f;
    cy += (a.y + b.y) * f;
    area2 += f * 3;
  }
  if (Math.abs(area2) > 1e-9) {
    const centroid = makeCell(cx / area2, cy / area2, 0, rings);
    if (centroid.d > best.d) best = centroid;
  }

  let guard = 0;
  while (queue.length && guard++ < 200_000) {
    const cell = pop();
    if (cell.d > best.d) best = cell;
    if (cell.max - best.d <= prec) continue;
    half = cell.h / 2;
    push(makeCell(cell.x - half, cell.y - half, half, rings));
    push(makeCell(cell.x + half, cell.y - half, half, rings));
    push(makeCell(cell.x - half, cell.y + half, half, rings));
    push(makeCell(cell.x + half, cell.y + half, half, rings));
  }
  return { x: best.x, y: best.y };
}

/** Điểm có nằm trong chi tiết (trong biên ngoài và ngoài mọi lỗ) không. */
export function pointInPart(pt: Point, rings: Ring[]): boolean {
  if (!pointInRing(pt, rings[0])) return false;
  for (let i = 1; i < rings.length; i++) if (pointInRing(pt, rings[i])) return false;
  return true;
}

// ───────────────────── Bù kerf: nở/thu đường cắt ─────────────────────

/**
 * Dời mọi cạnh của vòng ra xa `dist` mm theo pháp tuyến (dy, -dx), dùng mối nối
 * kiểu MITER (có giới hạn mũi nhọn).
 *
 * Quy ước chiều vòng của tool (outer CCW, hole CW) làm cho MỘT hàm này đủ dùng
 * cho cả hai việc bù kerf:
 *  - vòng ngoài CCW  → dist > 0 nở đường cắt RA NGOÀI chi tiết,
 *  - vòng lỗ CW      → dist > 0 THU đường cắt vào trong lòng lỗ (lỗ cắt nhỏ lại),
 * đúng như yêu cầu "nở kerf/2 cho bao ngoài, thu kerf/2 cho lỗ".
 */
export function offsetRing(ring: Ring, dist: number): Ring {
  if (!dist || ring.length < 3) return ring.slice();
  // bỏ đỉnh trùng để pháp tuyến không bị chia cho 0
  const pts: Point[] = [];
  for (const p of ring) {
    const last = pts[pts.length - 1];
    if (!last || Math.hypot(last.x - p.x, last.y - p.y) > 1e-9) pts.push(p);
  }
  while (pts.length > 2 && Math.hypot(pts[0].x - pts[pts.length - 1].x, pts[0].y - pts[pts.length - 1].y) <= 1e-9) pts.pop();
  const n = pts.length;
  if (n < 3) return ring.slice();

  const nrm = (a: Point, b: Point): Point => {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const l = Math.hypot(dx, dy) || 1;
    return { x: dy / l, y: -dx / l };
  };

  const MITER_LIMIT = 4;
  const out: Ring = [];
  for (let i = 0; i < n; i++) {
    const prev = pts[(i - 1 + n) % n];
    const cur = pts[i];
    const next = pts[(i + 1) % n];
    const n1 = nrm(prev, cur);
    const n2 = nrm(cur, next);
    let bx = n1.x + n2.x;
    let by = n1.y + n2.y;
    const bl = Math.hypot(bx, by);
    if (bl < 1e-9) {
      // gập 180° (gai nhọn): dùng luôn pháp tuyến cạnh trước
      out.push({ x: cur.x + n1.x * dist, y: cur.y + n1.y * dist });
      continue;
    }
    bx /= bl;
    by /= bl;
    const cosHalf = bx * n1.x + by * n1.y;
    const scale = 1 / Math.max(Math.abs(cosHalf), 1 / MITER_LIMIT);
    out.push({ x: cur.x + bx * dist * scale, y: cur.y + by * dist * scale });
  }
  return out;
}

/** Bù kerf cho cả chi tiết: rings[0] nở ra, các lỗ thu vào — mỗi bên kerf/2. */
export function offsetRingsForKerf(rings: Ring[], kerf: number): Ring[] {
  if (!kerf || kerf <= 0) return rings.map((r) => r.slice());
  return rings.map((r) => offsetRing(r, kerf / 2));
}

/** Bỏ dấu tiếng Việt + ký tự lạ để ghi vào DXF R12 / G-code (chuẩn ASCII). */
export function toAsciiLabel(s: string): string {
  const t = (s || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .replace(/[^\x20-\x7E]/g, '')
    .replace(/[(),]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  return t;
}
