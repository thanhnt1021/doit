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
