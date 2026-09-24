/**
 * Parser DXF tối giản, viết riêng cho bài toán xếp phôi tôn.
 *
 * Vì sao không dùng thư viện có sẵn: file bản vẽ tàu thật có 2.392 block rác
 * (logo, cửa sổ, vô lăng...) chiếm ~93% dung lượng file. Thư viện tổng quát
 * parse hết BLOCKS nên rất chậm. Ở đây ta NHẢY THẲNG qua section BLOCKS và
 * chỉ đọc ENTITIES của model space.
 */
import type { Part, ParseOptions, ParseResult, ParseStats, Point, Ring } from '../types';
import { signedArea, ringBBox } from '../types';
import './part'; // mở rộng kiểu Part: thêm dxfLabel
import { assignLabels, cleanMText, type DxfText } from './dxf-label';
import {
  convexHull,
  fitsInSheet,
  minAreaRect,
  orient,
  pointInRing,
  pointSegDistance,
  ringInsideRing,
  translateRing,
} from './geometry';

const ARC_SAG_TOL = 0.05; // sai số cung khi nở thành đoạn thẳng, mm
const ARC_MAX_SEG = 64;
const MIN_RING_AREA = 100; // mm², nhỏ hơn coi là rác

interface RawShape {
  closed: boolean;
  pts: Point[];
}

/** Đọc cặp group-code, có bỏ qua section không cần. */
class DxfScanner {
  private pos = 0;
  constructor(private readonly text: string) {}

  /** Đọc 1 dòng đã trim, null nếu hết file. */
  private line(): string | null {
    const t = this.text;
    if (this.pos >= t.length) return null;
    let e = t.indexOf('\n', this.pos);
    if (e < 0) e = t.length;
    let s = this.pos;
    this.pos = e + 1;
    let end = e;
    if (end > s && t.charCodeAt(end - 1) === 13) end--;
    // trim khoảng trắng đầu/cuối (DXF hay pad "  0")
    while (s < end && t.charCodeAt(s) <= 32) s++;
    while (end > s && t.charCodeAt(end - 1) <= 32) end--;
    return t.slice(s, end);
  }

  /** Đọc 1 cặp (code, value). null nếu hết. */
  next(): { code: number; value: string } | null {
    const a = this.line();
    if (a === null) return null;
    const b = this.line();
    if (b === null) return null;
    const code = parseInt(a, 10);
    return { code: Number.isNaN(code) ? -1 : code, value: b };
  }

  /** Nhảy tới đầu dòng ngay sau chuỗi ENDSEC gần nhất (phải giữ đúng nhịp cặp code/value). */
  skipToEndSec(): void {
    const idx = this.text.indexOf('ENDSEC', this.pos);
    if (idx < 0) {
      this.pos = this.text.length;
      return;
    }
    const nl = this.text.indexOf('\n', idx);
    this.pos = nl < 0 ? this.text.length : nl + 1;
  }
}

function arcSegments(radius: number, sweepAbs: number): number {
  if (radius <= 0) return 1;
  const maxStep = 2 * Math.acos(Math.max(-1, Math.min(1, 1 - ARC_SAG_TOL / radius)));
  const n = Math.ceil(sweepAbs / Math.max(maxStep, 1e-4));
  return Math.max(1, Math.min(ARC_MAX_SEG, n));
}

/** Nở cung theo bulge giữa p1 và p2. Trả các điểm TRUNG GIAN (không gồm p1, p2). */
function bulgeToPoints(p1: Point, p2: Point, bulge: number): Point[] {
  if (!bulge || Math.abs(bulge) < 1e-12) return [];
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  const chord = Math.hypot(dx, dy);
  if (chord < 1e-9) return [];
  const theta = 4 * Math.atan(bulge);
  const half = theta / 2;
  const sinHalf = Math.sin(half);
  if (Math.abs(sinHalf) < 1e-12) return [];
  const r = chord / (2 * sinHalf);
  const mx = (p1.x + p2.x) / 2;
  const my = (p1.y + p2.y) / 2;
  const h = r * Math.cos(half);
  const cx = mx + (-dy / chord) * h;
  const cy = my + (dx / chord) * h;
  const a1 = Math.atan2(p1.y - cy, p1.x - cx);
  const n = arcSegments(Math.abs(r), Math.abs(theta));
  const out: Point[] = [];
  for (let i = 1; i < n; i++) {
    const a = a1 + (theta * i) / n;
    out.push({ x: cx + Math.abs(r) * Math.cos(a), y: cy + Math.abs(r) * Math.sin(a) });
  }
  return out;
}

function arcToPoints(cx: number, cy: number, r: number, startDeg: number, endDeg: number): Point[] {
  let sweep = ((endDeg - startDeg) * Math.PI) / 180;
  while (sweep <= 0) sweep += Math.PI * 2;
  const a1 = (startDeg * Math.PI) / 180;
  const n = arcSegments(r, sweep);
  const out: Point[] = [];
  for (let i = 0; i <= n; i++) {
    const a = a1 + (sweep * i) / n;
    out.push({ x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) });
  }
  return out;
}

function circleToPoints(cx: number, cy: number, r: number): Point[] {
  const n = arcSegments(r, Math.PI * 2);
  const out: Point[] = [];
  for (let i = 0; i < n; i++) {
    const a = (Math.PI * 2 * i) / n;
    out.push({ x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) });
  }
  return out;
}

/**
 * Layer bị bỏ qua khi đọc. Đây là QUY ƯỚC RIÊNG của tool: file do chính tool
 * xuất ra có viền tấm ở layer SHEET và nhãn ở layer LABEL — đọc lại chúng sẽ
 * hiểu nhầm cả tấm là 1 chi tiết còn 15 chi tiết thật thành 15 cái lỗ.
 * Bản vẽ của khách không dùng 2 tên layer này (tên layer của họ là mã linh tinh).
 */
const IGNORED_LAYERS = new Set(['SHEET', 'LABEL']);

const IGNORED = new Set([
  'TEXT', 'MTEXT', 'DIMENSION', 'INSERT', 'HATCH', 'VIEWPORT', 'ATTDEF', 'ATTRIB',
  'LEADER', 'MLEADER', 'MULTILEADER', 'SOLID', 'POINT', 'IMAGE', '3DFACE', 'TOLERANCE',
  'RAY', 'XLINE', 'TRACE', 'SHAPE', 'BODY', 'REGION', '3DSOLID', 'MESH', 'WIPEOUT',
]);

/** Gom các entity trong section ENTITIES thành các chuỗi điểm. */
function readEntities(
  text: string,
  scale: number,
  counts: Record<string, number>,
  texts: DxfText[]
): RawShape[] {
  const sc = new DxfScanner(text);
  const shapes: RawShape[] = [];

  // Tìm section ENTITIES, nhảy qua HEADER/CLASSES/TABLES/BLOCKS (BLOCKS chiếm ~93% file)
  let found = false;
  let pair = sc.next();
  while (pair) {
    if (pair.code === 0 && pair.value === 'SECTION') {
      const nameP = sc.next();
      const name = nameP && nameP.code === 2 ? nameP.value : '';
      if (name === 'ENTITIES') {
        found = true;
        break;
      }
      sc.skipToEndSec();
    }
    pair = sc.next();
  }
  if (!found) return shapes;

  // Gom từng entity thành mảng cặp (code, value) rồi mới dựng hình.
  // Section ENTITIES của file thật chỉ ~10k dòng nên cách này thừa sức nhanh.
  type Pair = { code: number; value: string };
  let curType = '';
  let curPairs: Pair[] = [];
  // trạng thái POLYLINE cũ (kiểu AutoCAD R12): POLYLINE + nhiều VERTEX + SEQEND
  let polyOpen = false;
  let polyClosed = false;
  let polyPts: Point[] = [];
  let polyBulges: number[] = [];

  const num = (ps: Pair[], code: number, def = 0): number => {
    for (const p of ps) if (p.code === code) return parseFloat(p.value);
    return def;
  };
  const int = (ps: Pair[], code: number, def = 0): number => {
    for (const p of ps) if (p.code === code) return parseInt(p.value, 10) || 0;
    return def;
  };
  const all = (ps: Pair[], code: number): number[] => {
    const out: number[] = [];
    for (const p of ps) if (p.code === code) out.push(parseFloat(p.value));
    return out;
  };

  const expandBulged = (pts: Point[], bul: number[], closed: boolean): Point[] => {
    const out: Point[] = [];
    const n = pts.length;
    const limit = closed ? n : n - 1;
    for (let i = 0; i < limit; i++) {
      out.push(pts[i]);
      const b = bul[i] || 0;
      if (b) out.push(...bulgeToPoints(pts[i], pts[(i + 1) % n], b));
    }
    if (!closed) out.push(pts[n - 1]);
    return out;
  };

  /** LWPOLYLINE có thể xen kẽ 10/20/42 theo đỉnh — phải đọc tuần tự. */
  const lwPolyPoints = (ps: Pair[]): { pts: Point[]; bulges: number[] } => {
    const pts: Point[] = [];
    const bulges: number[] = [];
    let x: number | null = null;
    for (const p of ps) {
      if (p.code === 10) {
        x = parseFloat(p.value);
      } else if (p.code === 20 && x !== null) {
        pts.push({ x: x * scale, y: parseFloat(p.value) * scale });
        bulges.push(0);
        x = null;
      } else if (p.code === 42 && pts.length > 0) {
        bulges[pts.length - 1] = parseFloat(p.value);
      }
    }
    return { pts, bulges };
  };

  const finishEntity = () => {
    if (!curType) return;
    const ps = curPairs;
    const t = curType;
    curType = '';
    curPairs = [];

    let layer = '';
    for (const q of ps) if (q.code === 8) { layer = q.value.toUpperCase(); break; }
    if (layer && IGNORED_LAYERS.has(layer)) {
      counts[t] = (counts[t] || 0) + 1;
      return;
    }

    if (t === 'VERTEX') {
      if (polyOpen) {
        const x = num(ps, 10);
        const y = num(ps, 20);
        polyPts.push({ x: x * scale, y: y * scale });
        polyBulges.push(num(ps, 42, 0));
      }
      return;
    }

    counts[t] = (counts[t] || 0) + 1;
    if (t === 'TEXT' || t === 'MTEXT') {
      // TEXT/MTEXT vẫn KHÔNG tạo ra hình, nhưng giữ lại toạ độ + nội dung để
      // đọc tên mã phôi (xem dxf-label.ts).
      const chunks: string[] = [];
      for (const q of ps) if (q.code === 3) chunks.push(q.value);
      for (const q of ps) if (q.code === 1) chunks.push(q.value);
      const body = cleanMText(chunks.join(''));
      if (body) {
        // TEXT căn lề (mã 72/73 khác 0) thì điểm đặt thật nằm ở 11/21.
        const aligned = t === 'TEXT' && (int(ps, 72, 0) !== 0 || int(ps, 73, 0) !== 0);
        const hasAlt = ps.some((q) => q.code === 11);
        const useAlt = aligned && hasAlt;
        texts.push({
          x: num(ps, useAlt ? 11 : 10) * scale,
          y: num(ps, useAlt ? 21 : 20) * scale,
          h: num(ps, 40, 0) * scale,
          text: body,
        });
      }
    }
    if (IGNORED.has(t)) return;

    if (t === 'LWPOLYLINE') {
      const { pts, bulges } = lwPolyPoints(ps);
      if (pts.length >= 2) {
        const closed = (int(ps, 70) & 1) === 1;
        shapes.push({ closed, pts: expandBulged(pts, bulges, closed) });
      }
    } else if (t === 'LINE') {
      const x1 = num(ps, 10);
      const y1 = num(ps, 20);
      const x2 = num(ps, 11);
      const y2 = num(ps, 21);
      shapes.push({
        closed: false,
        pts: [
          { x: x1 * scale, y: y1 * scale },
          { x: x2 * scale, y: y2 * scale },
        ],
      });
    } else if (t === 'ARC') {
      const r = num(ps, 40);
      if (r > 0) {
        shapes.push({
          closed: false,
          pts: arcToPoints(num(ps, 10) * scale, num(ps, 20) * scale, r * scale, num(ps, 50), num(ps, 51)),
        });
      }
    } else if (t === 'CIRCLE') {
      const r = num(ps, 40);
      if (r > 0) shapes.push({ closed: true, pts: circleToPoints(num(ps, 10) * scale, num(ps, 20) * scale, r * scale) });
    } else if (t === 'SPLINE') {
      const fx = all(ps, 11);
      const fy = all(ps, 21);
      const useFit = fx.length >= 2 && fy.length >= 2;
      const sxs = useFit ? fx : all(ps, 10);
      const sys = useFit ? fy : all(ps, 20);
      const n = Math.min(sxs.length, sys.length);
      if (n >= 2) {
        const pts: Point[] = [];
        for (let i = 0; i < n; i++) pts.push({ x: sxs[i] * scale, y: sys[i] * scale });
        shapes.push({ closed: (int(ps, 70) & 1) === 1, pts });
      }
    } else if (t === 'POLYLINE') {
      polyOpen = true;
      polyClosed = (int(ps, 70) & 1) === 1;
      polyPts = [];
      polyBulges = [];
    }
  };

  const finishPolyline = () => {
    if (!polyOpen) return;
    polyOpen = false;
    if (polyPts.length >= 2) {
      shapes.push({ closed: polyClosed, pts: expandBulged(polyPts, polyBulges, polyClosed) });
    }
    polyPts = [];
    polyBulges = [];
  };

  pair = sc.next();
  while (pair) {
    if (pair.code === 0) {
      finishEntity();
      const v = pair.value;
      if (v === 'ENDSEC') {
        finishPolyline();
        break;
      }
      if (v === 'SEQEND') {
        finishPolyline();
        curType = '';
        curPairs = [];
        pair = sc.next();
        continue;
      }
      if (polyOpen && v !== 'VERTEX') finishPolyline();
      curType = v;
      curPairs = [];
      pair = sc.next();
      continue;
    }
    if (curType) curPairs.push(pair);
    pair = sc.next();
  }
  finishEntity();
  finishPolyline();
  return shapes;
}

/** Ghép các chuỗi hở thành vòng kín theo dung sai. */
function chainOpenShapes(open: RawShape[], tol: number): { closed: Ring[]; dropped: number } {
  const key = (p: Point) => `${Math.round(p.x / tol)}|${Math.round(p.y / tol)}`;
  interface Seg {
    pts: Point[];
    used: boolean;
  }
  const segs: Seg[] = open.filter((s) => s.pts.length >= 2).map((s) => ({ pts: s.pts, used: false }));
  const map = new Map<string, number[]>();
  const addKey = (k: string, i: number) => {
    const arr = map.get(k);
    if (arr) arr.push(i);
    else map.set(k, [i]);
  };
  // thêm cả các ô lân cận để dung sai không bị "rơi khe"
  const keysOf = (p: Point): string[] => {
    const gx = Math.round(p.x / tol);
    const gy = Math.round(p.y / tol);
    return [`${gx}|${gy}`];
  };
  segs.forEach((s, i) => {
    keysOf(s.pts[0]).forEach((k) => addKey(k, i));
    keysOf(s.pts[s.pts.length - 1]).forEach((k) => addKey(k, i));
  });

  const near = (a: Point, b: Point) => Math.hypot(a.x - b.x, a.y - b.y) <= tol;
  const closed: Ring[] = [];
  let dropped = 0;

  for (let i = 0; i < segs.length; i++) {
    if (segs[i].used) continue;
    segs[i].used = true;
    const chain: Point[] = segs[i].pts.slice();
    let grew = true;
    while (grew) {
      grew = false;
      const tail = chain[chain.length - 1];
      if (near(tail, chain[0]) && chain.length > 3) break;
      const cands = new Set<number>();
      for (const k of keysOf(tail)) {
        const gx = parseInt(k.split('|')[0], 10);
        const gy = parseInt(k.split('|')[1], 10);
        for (let dx = -1; dx <= 1; dx++)
          for (let dy = -1; dy <= 1; dy++) {
            const arr = map.get(`${gx + dx}|${gy + dy}`);
            if (arr) arr.forEach((v) => cands.add(v));
          }
      }
      for (const j of cands) {
        if (segs[j].used) continue;
        const sp = segs[j].pts;
        if (near(tail, sp[0])) {
          chain.push(...sp.slice(1));
          segs[j].used = true;
          grew = true;
          break;
        }
        if (near(tail, sp[sp.length - 1])) {
          const rev = sp.slice(0, -1).reverse();
          chain.push(...rev);
          segs[j].used = true;
          grew = true;
          break;
        }
      }
    }
    if (chain.length >= 4 && near(chain[chain.length - 1], chain[0])) {
      chain.pop();
      closed.push(chain);
    } else {
      dropped++;
    }
  }
  return { closed, dropped };
}

function dedupRing(ring: Ring, tol = 1e-6): Ring {
  const out: Ring = [];
  for (const p of ring) {
    const last = out[out.length - 1];
    if (!last || Math.hypot(last.x - p.x, last.y - p.y) > tol) out.push(p);
  }
  while (out.length > 1 && Math.hypot(out[0].x - out[out.length - 1].x, out[0].y - out[out.length - 1].y) <= tol) out.pop();
  return out;
}

export function parseDxf(text: string, opts: ParseOptions = {}): ParseResult {
  const t0 = Date.now();
  const scale = opts.unitScale ?? 1;
  const chainTol = opts.chainTol ?? 0.1;
  const sheetW = opts.sheetWidth ?? 2000;
  const sheetH = opts.sheetHeight ?? 6000;
  const warnings: string[] = [];
  const counts: Record<string, number> = {};
  const texts: DxfText[] = [];

  opts.onProgress?.(0.05, 'Đang đọc file DXF…');
  const shapes = readEntities(text, scale, counts, texts);
  opts.onProgress?.(0.45, 'Đang lọc các đường khép kín…');

  // tách kín / hở
  const closedRaw: Ring[] = [];
  const openShapes: RawShape[] = [];
  for (const s of shapes) {
    if (s.closed && s.pts.length >= 3) closedRaw.push(dedupRing(s.pts));
    else openShapes.push(s);
  }
  const chained = chainOpenShapes(openShapes, chainTol);
  for (const r of chained.closed) closedRaw.push(dedupRing(r));

  opts.onProgress?.(0.6, 'Đang nhận diện lỗ và chi tiết…');

  // loại vòng rác
  const rings = closedRaw.filter((r) => r.length >= 3 && Math.abs(signedArea(r)) >= MIN_RING_AREA);

  // phân cấp lồng nhau → độ sâu chẵn = chi tiết, lẻ = lỗ
  const order = rings.map((r, i) => ({ i, area: Math.abs(signedArea(r)) })).sort((a, b) => b.area - a.area);
  const parent = new Array<number>(rings.length).fill(-1);
  for (let a = 0; a < order.length; a++) {
    const ia = order[a].i;
    for (let b = a - 1; b >= 0; b--) {
      const ib = order[b].i;
      if (ringInsideRing(rings[ia], rings[ib])) {
        parent[ia] = ib;
        break;
      }
    }
  }
  const depth = new Array<number>(rings.length).fill(0);
  const calcDepth = (i: number): number => {
    if (depth[i] > 0) return depth[i];
    depth[i] = parent[i] < 0 ? 0 : calcDepth(parent[i]) + 1;
    return depth[i];
  };
  for (let i = 0; i < rings.length; i++) calcDepth(i);

  const outerIdx: number[] = [];
  const holesOf = new Map<number, number[]>();
  let holeCount = 0;
  for (let i = 0; i < rings.length; i++) {
    if (depth[i] % 2 === 0) outerIdx.push(i);
    else {
      holeCount++;
      const p = parent[i];
      const arr = holesOf.get(p);
      if (arr) arr.push(i);
      else holesOf.set(p, [i]);
    }
  }
  // giữ nguyên thứ tự xuất hiện trong file
  outerIdx.sort((a, b) => a - b);

  opts.onProgress?.(0.8, 'Đang tính kích thước chi tiết…');

  // Tên mã phôi đọc từ chữ — gán theo TOẠ ĐỘ GỐC (trước khi dịch chi tiết về 0,0).
  const labels = assignLabels(texts, outerIdx.map((oi) => rings[oi]));

  const parts: Part[] = [];
  let tooBig = 0;
  for (let k = 0; k < outerIdx.length; k++) {
    const oi = outerIdx[k];
    let outer = orient(rings[oi], true);
    const holes = (holesOf.get(oi) || []).map((hi) => orient(rings[hi], false));
    const bb = ringBBox(outer);
    const dx = -bb.minX;
    const dy = -bb.minY;
    outer = translateRing(outer, dx, dy);
    const holesN = holes.map((h) => translateRing(h, dx, dy));
    const allRings = [outer, ...holesN];
    const area = Math.abs(signedArea(outer)) - holesN.reduce((s, h) => s + Math.abs(signedArea(h)), 0);
    const hull = convexHull(outer);
    // Kích thước hiển thị = KHUNG BAO NHỎ NHẤT KHI XOAY, không phải bbox theo trục
    // toạ độ gốc: thanh sườn cong nằm chéo trong bản vẽ nên bbox cho số vô nghĩa
    // (P0 ra 3409×3996 trong khi thanh thật 5253×1172).
    const rect = minAreaRect(hull);
    const mw = rect.width;
    const ml = rect.length;
    const fits = fitsInSheet(hull, sheetW, sheetH, 1);
    if (!fits) tooBig++;
    parts.push({
      id: `P${k}`,
      rings: allRings,
      area,
      bbox: ringBBox(outer),
      vertexCount: allRings.reduce((s, r) => s + r.length, 0),
      minWidth: mw,
      maxLength: ml,
      qty: 1,
      enabled: fits,
      fitsSheet: fits,
      dxfLabel: labels[k] ?? '',
    });
  }

  if (parts.length === 0) {
    warnings.push('Không tìm thấy đường khép kín nào trong file. Hãy kiểm tra lại bản vẽ.');
  }
  if (tooBig > 0) {
    warnings.push(`Có ${tooBig} chi tiết to hơn tấm tôn — đã đánh dấu đỏ và bỏ khỏi danh sách xếp.`);
  }
  if (parts.length > 0) {
    const avg = parts.reduce((s, p) => s + Math.sqrt(p.area), 0) / parts.length;
    if (avg < 20) warnings.push('Các chi tiết rất nhỏ — có thể file dùng đơn vị mét/centimét. Thử đổi ô "Đơn vị file".');
    else if (tooBig === parts.length) warnings.push('Mọi chi tiết đều to hơn tấm — có thể file dùng đơn vị khác mm. Thử đổi ô "Đơn vị file".');
  }

  const stats: ParseStats = {
    entityCounts: counts,
    closedRings: rings.length,
    openDropped: chained.dropped,
    holes: holeCount,
    ms: Date.now() - t0,
  };
  opts.onProgress?.(1, 'Xong');
  return { parts, stats, warnings };
}
