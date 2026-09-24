/**
 * Lõi xếp phôi (nesting). Thuần TypeScript — chạy được cả trong Node (test)
 * lẫn trong Web Worker của trình duyệt. Không đụng DOM.
 */
import type {
  NestInput, NestParams, NestProgress, NestResult, Part, Placement, Ring, SheetLayout,
} from '../types';
import { DEFAULT_NEST_PARAMS, applyPlacementRing, ringBBox } from '../types';
import { pointInRing, segSegDistance, segSegIntersect } from '../core/geometry';
import { rasterizeRing, transformRing, type BaseBitmap } from './raster';

export interface NestCallbacks {
  onProgress?: (p: NestProgress) => void;
  shouldStop?: () => boolean;
  now?: () => number;
}

/** Bộ sinh ngẫu nhiên có seed để test tái lập được. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

interface AngleOpt {
  deg: number;
  mirrored: boolean;
  /** Diện tích bbox sau khi xoay (mm²) — dùng để xếp hạng. */
  bboxArea: number;
}

interface PartPrep {
  part: Part;
  /** Vòng ngoài của hình gốc (dùng để raster). */
  simple: Ring;
  /** Các góc hợp lệ, đã xếp hạng theo bbox nhỏ dần. */
  angles: AngleOpt[];
}

interface Inst {
  prepIndex: number;
  instance: number;
  area: number;
}

interface SheetGrid {
  bits: Uint32Array;
  words: number;
  /** Bit cao nhất đang bị chiếm của từng hàng (-1 nếu hàng trống) — lọc va chạm cực nhanh. */
  rowMax: Int32Array;
  /** Hàng ô cao nhất đã dùng (exclusive). */
  maxRow: number;
  placements: Placement[];
  usedArea: number;
}

const BIG = 1e12;

export class Nester {
  readonly cell: number;
  readonly dil: number;
  readonly rx0: number;
  readonly ry0: number;
  readonly gw: number;
  readonly gh: number;
  readonly sheetWords: number;
  /** Bước nhảy theo trục y khi dò vị trí (ô). */
  readonly yStride: number;
  private cache = new Map<string, BaseBitmap | null>();

  constructor(readonly params: NestParams) {
    this.cell = params.gridCell ?? 5;
    this.dil = Math.max(0, Math.ceil(params.gap / 2 / this.cell));
    this.rx0 = params.margin - this.dil * this.cell;
    this.ry0 = params.margin - this.dil * this.cell;
    const rw = params.sheetW - 2 * params.margin + 2 * this.dil * this.cell;
    const rh = params.sheetH - 2 * params.margin + 2 * this.dil * this.cell;
    this.gw = Math.max(1, Math.floor(rw / this.cell));
    this.gh = Math.max(1, Math.floor(rh / this.cell));
    this.sheetWords = ((this.gw + 31) >> 5) + 2;
    this.yStride = Math.max(1, Math.round(15 / this.cell));
  }

  newSheet(): SheetGrid {
    return {
      bits: new Uint32Array(this.sheetWords * this.gh),
      words: this.sheetWords,
      rowMax: new Int32Array(this.gh).fill(-1),
      maxRow: 0,
      placements: [],
      usedArea: 0,
    };
  }

  getBitmap(prep: PartPrep, a: AngleOpt): BaseBitmap | null {
    const key = `${prep.part.id}|${a.deg}|${a.mirrored ? 1 : 0}`;
    const hit = this.cache.get(key);
    if (hit !== undefined) return hit;
    const ring = transformRing(prep.simple, a.deg, a.mirrored);
    const bm = rasterizeRing(ring, this.cell, this.dil);
    const ok = bm.w <= this.gw && bm.h <= this.gh;
    const val = ok ? bm : null;
    this.cache.set(key, val);
    return val;
  }

  /**
   * Dò va chạm khi đặt bitmap `bm` tại ô (px, py) của lưới tấm.
   * Dịch bit tại chỗ (không cấp phát) + bỏ qua ngay hàng nào tấm chưa bị chiếm tới cột px.
   */
  collides(sh: SheetGrid, bm: BaseBitmap, px: number, py: number): boolean {
    const s = px & 31;
    const wo = px >>> 5;
    const sw = sh.words;
    const sheet = sh.bits;
    const pbits = bm.bits;
    const pw = bm.words;
    const rowMax = sh.rowMax;
    const inv = 32 - s;
    for (let r = 0; r < bm.h; r++) {
      const f = bm.rowFirst[r];
      if (f < 0) continue;
      const rm = rowMax[py + r];
      if (rm < px + bm.rowLowBit[r]) continue; // hàng này của tấm chưa chạm tới chi tiết
      const l = bm.rowLast[r];
      const src = r * pw;
      const dst = (py + r) * sw + wo;
      if (s === 0) {
        for (let i = f; i <= l; i++) {
          if ((pbits[src + i] & sheet[dst + i]) !== 0) return true;
        }
      } else {
        let prev = 0;
        for (let i = f; i <= l + 1; i++) {
          const cur = i <= l ? pbits[src + i] : 0;
          const v = ((cur << s) | (prev >>> inv)) >>> 0;
          prev = cur;
          if ((v & sheet[dst + i]) !== 0) return true;
        }
      }
    }
    return false;
  }

  stamp(sh: SheetGrid, bm: BaseBitmap, px: number, py: number): void {
    const s = px & 31;
    const wo = px >>> 5;
    const sw = sh.words;
    const sheet = sh.bits;
    const pbits = bm.bits;
    const pw = bm.words;
    const inv = 32 - s;
    for (let r = 0; r < bm.h; r++) {
      const f = bm.rowFirst[r];
      if (f < 0) continue;
      const l = bm.rowLast[r];
      const src = r * pw;
      const dst = (py + r) * sw + wo;
      if (s === 0) {
        for (let i = f; i <= l; i++) sheet[dst + i] |= pbits[src + i];
      } else {
        let prev = 0;
        for (let i = f; i <= l + 1; i++) {
          const cur = i <= l ? pbits[src + i] : 0;
          sheet[dst + i] |= ((cur << s) | (prev >>> inv)) >>> 0;
          prev = cur;
        }
      }
      const hi = px + (bm.rowLast[r] * 32 + 31);
      const row = py + r;
      if (hi > sh.rowMax[row]) sh.rowMax[row] = hi;
    }
    if (py + bm.h > sh.maxRow) sh.maxRow = py + bm.h;
  }

  /**
   * Tìm chỗ đặt tốt nhất cho 1 bitmap trên 1 tấm.
   * rule 0: ưu tiên KHÔNG làm tấm dài thêm, rồi px nhỏ nhất (hợp với thanh cong lồng nhau).
   * rule 1: bottom-left cổ điển — py nhỏ nhất rồi px nhỏ nhất.
   */
  findSpot(sh: SheetGrid, bm: BaseBitmap, rule: number, capPy: number): { px: number; py: number } | null {
    const maxPx = this.gw - bm.w;
    const maxPy = this.gh - bm.h;
    if (maxPx < 0 || maxPy < 0) return null;
    // Bước nhảy theo y khi dò (mm → ô). Trượt thô rồi ép xuống cho khít.
    // Bỏ sót một vị trí y hẹp chỉ làm chi tiết lệch phải vài ô, không sai kết quả.
    const stride = this.yStride;

    if (rule === 1) {
      // bottom-left cổ điển: py ngoài, px trong, gặp chỗ trống đầu tiên là lấy
      const limitPy = Math.min(maxPy, capPy);
      for (let py = 0; py <= limitPy; py += stride) {
        for (let px = 0; px <= maxPx; px++) {
          if (!this.collides(sh, bm, px, py)) return { px, py: this.settle(sh, bm, px, py, stride) };
        }
      }
      return null;
    }

    // rule 0 — pha 1: tìm chỗ KHÔNG làm tấm dài thêm, ưu tiên px nhỏ nhất.
    // Cho phép chi tiết trượt dọc theo y để "lồng" vào chỗ lõm của chi tiết bên cạnh.
    const phase1Py = Math.min(maxPy, sh.maxRow - bm.h);
    for (let px = 0; px <= maxPx && phase1Py >= 0; px++) {
      for (let py = 0; py <= phase1Py; py += stride) {
        if (!this.collides(sh, bm, px, py)) return { px, py: this.settle(sh, bm, px, py, stride) };
      }
    }
    // pha 2: buộc phải kéo dài tấm — chọn py nhỏ nhất rồi px nhỏ nhất
    const startPy = Math.max(0, sh.maxRow - bm.h + 1);
    const limitPy = Math.min(maxPy, capPy);
    for (let py = startPy; py <= limitPy; py += stride) {
      for (let px = 0; px <= maxPx; px++) {
        if (!this.collides(sh, bm, px, py)) return { px, py: this.settle(sh, bm, px, py, stride) };
      }
    }
    return null;
  }

  /** Ép chi tiết xuống thấp nhất có thể trong phạm vi 1 bước nhảy. */
  private settle(sh: SheetGrid, bm: BaseBitmap, px: number, py: number, stride: number): number {
    if (stride <= 1) return py;
    let best = py;
    for (let k = 1; k < stride && py - k >= 0; k++) {
      if (this.collides(sh, bm, px, py - k)) break;
      best = py - k;
    }
    return best;
  }

  place(sh: SheetGrid, prep: PartPrep, inst: Inst, angleCands: AngleOpt[], rule: number): boolean {
    let bestSpot: { px: number; py: number } | null = null;
    let bestBm: BaseBitmap | null = null;
    let bestA: AngleOpt | null = null;
    let bestKey = Infinity;
    for (const a of angleCands) {
      const bm = this.getBitmap(prep, a);
      if (!bm) continue;
      const cap = bestSpot ? Math.max(0, bestKeyToCap(bestKey, bm.h)) : this.gh;
      const spot = this.findSpot(sh, bm, rule, cap);
      if (!spot) continue;
      const top = spot.py + bm.h;
      const key = Math.max(top, sh.maxRow) * 1e6 + spot.px;
      if (key < bestKey) {
        bestKey = key;
        bestSpot = spot;
        bestBm = bm;
        bestA = a;
      }
    }
    if (!bestSpot || !bestBm || !bestA) return false;
    this.stamp(sh, bestBm, bestSpot.px, bestSpot.py);
    sh.placements.push({
      partId: prep.part.id,
      instance: inst.instance,
      rotationDeg: bestA.deg,
      mirrored: bestA.mirrored,
      x: this.rx0 + bestSpot.px * this.cell - bestBm.originX,
      y: this.ry0 + bestSpot.py * this.cell - bestBm.originY,
    });
    sh.usedArea += prep.part.area;
    return true;
  }
}

function bestKeyToCap(bestKey: number, h: number): number {
  const top = Math.floor(bestKey / 1e6);
  return Math.max(0, top - h);
}

/** Dựng danh sách góc hợp lệ cho 1 chi tiết. */
function buildAngles(prep: Omit<PartPrep, 'angles'>, nester: Nester, params: NestParams): AngleOpt[] {
  const step = Math.max(1, params.rotationStep || 5);
  const mirrors = params.allowMirror ? [false, true] : [false];
  const out: AngleOpt[] = [];
  for (const mirrored of mirrors) {
    for (let deg = 0; deg < 360; deg += step) {
      const ring = transformRing(prep.simple, deg, mirrored);
      const b = ringBBox(ring);
      const w = b.maxX - b.minX + 2 * nester.dil * nester.cell;
      const h = b.maxY - b.minY + 2 * nester.dil * nester.cell;
      if (w > nester.gw * nester.cell || h > nester.gh * nester.cell) continue;
      out.push({ deg, mirrored, bboxArea: (b.maxX - b.minX) * (b.maxY - b.minY) });
    }
  }
  out.sort((a, b) => a.bboxArea - b.bboxArea);
  return out;
}

interface Genome {
  order: number[];
  angleIdx: number[];
  rule: number;
}

interface Evaluated {
  genome: Genome;
  cost: number;
  sheets: SheetLayout[];
  unplaced: string[];
  placedArea: number;
}

export function nest(input: NestInput, cb: NestCallbacks = {}): NestResult {
  const params: NestParams = { ...DEFAULT_NEST_PARAMS, ...input.params };
  const now = cb.now ?? Date.now;
  const t0 = now();
  const deadline = t0 + Math.max(200, params.timeLimitMs);
  const rng = mulberry32(params.seed ?? 12345);

  const nester = new Nester(params);

  // chuẩn bị chi tiết
  const preps: PartPrep[] = [];
  const unplacedFixed: string[] = [];
  for (const p of input.parts) {
    if (!p.enabled) continue;
    if (!p.fitsSheet) {
      for (let i = 0; i < Math.max(1, p.qty); i++) unplacedFixed.push(`${p.id}#${i}`);
      continue;
    }
    // Dùng HÌNH GỐC (không đơn giản hoá) để raster: hình đơn giản hoá có thể
    // hụt vào trong tới 1mm, khiến chi tiết lọt ra ngoài lề tấm.
    const simple = p.rings[0];
    const base = { part: p, simple };
    const angles = buildAngles(base, nester, params);
    if (angles.length === 0) {
      for (let i = 0; i < Math.max(1, p.qty); i++) unplacedFixed.push(`${p.id}#${i}`);
      continue;
    }
    preps.push({ ...base, angles });
  }

  const insts: Inst[] = [];
  preps.forEach((pp, idx) => {
    const q = Math.max(1, Math.floor(pp.part.qty) || 1);
    for (let i = 0; i < q; i++) insts.push({ prepIndex: idx, instance: i, area: pp.part.area });
  });

  const nInst = insts.length;
  if (nInst === 0) {
    return {
      sheets: [], unplaced: unplacedFixed, utilization: 0,
      elapsedMs: now() - t0, iterations: 0, params,
    };
  }

  const ANGLE_TRIES = 4;

  const evaluate = (g: Genome): Evaluated => {
    const sheets: SheetGrid[] = [nester.newSheet()];
    const unplaced: string[] = [];
    let placedArea = 0;
    for (const ii of g.order) {
      const inst = insts[ii];
      const prep = preps[inst.prepIndex];
      const ranked = prep.angles;
      const chosen = ranked[g.angleIdx[ii] % ranked.length];
      const cands: AngleOpt[] = [chosen];
      for (let k = 0; k < ranked.length && cands.length < ANGLE_TRIES; k++) {
        if (ranked[k] !== chosen) cands.push(ranked[k]);
      }
      let ok = false;
      for (const sh of sheets) {
        if (nester.place(sh, prep, inst, cands, g.rule)) {
          ok = true;
          break;
        }
      }
      if (!ok) {
        const sh = nester.newSheet();
        if (nester.place(sh, prep, inst, cands, g.rule)) {
          sheets.push(sh);
          ok = true;
        }
      }
      if (ok) placedArea += prep.part.area;
      else unplaced.push(`${prep.part.id}#${inst.instance}`);
    }
    const used = sheets.filter((s) => s.placements.length > 0);
    const layouts: SheetLayout[] = used.map((s, i) => ({
      index: i,
      width: params.sheetW,
      height: params.sheetH,
      placements: s.placements,
      usedArea: s.usedArea,
      utilization: s.usedArea / (params.sheetW * params.sheetH),
    }));
    // Ưu tiên tuyệt đối: ít tấm nhất. Sau đó: dồn cho tấm CUỐI càng ít càng tốt
    // (để phần tôn thừa còn nguyên khổ, xưởng cất đi dùng lần sau).
    const lastArea = used.length ? used[used.length - 1].usedArea : 0;
    const lastTop = used.length ? used[used.length - 1].maxRow * nester.cell : 0;
    const sumTop = used.reduce((a, s) => a + s.maxRow * nester.cell, 0);
    const cost =
      (used.length + unplaced.length * 10) * BIG +
      (lastArea / 1e6) * 1e7 +
      lastTop * 1e3 +
      sumTop;
    return { genome: g, cost, sheets: layouts, unplaced: unplaced.concat(unplacedFixed), placedArea };
  };

  // ── cá thể khởi đầu ──────────────────────────────────────────────────────
  const idxAll = insts.map((_, i) => i);
  const byArea = idxAll.slice().sort((a, b) => insts[b].area - insts[a].area);
  const byLen = idxAll.slice().sort(
    (a, b) => preps[insts[b].prepIndex].part.maxLength - preps[insts[a].prepIndex].part.maxLength
  );
  const byBBox = idxAll.slice().sort((a, b) => {
    const pa = preps[insts[a].prepIndex].part.bbox;
    const pb = preps[insts[b].prepIndex].part.bbox;
    return (pb.maxX - pb.minX) * (pb.maxY - pb.minY) - (pa.maxX - pa.minX) * (pa.maxY - pa.minY);
  });
  const byMinW = idxAll.slice().sort(
    (a, b) => preps[insts[a].prepIndex].part.minWidth - preps[insts[b].prepIndex].part.minWidth
  );

  // Thứ tự xen kẽ: lấy cách một chi tiết. Với bộ sườn tàu (các đường cong cùng họ)
  // cách xếp này tách được 2 nhóm cùng độ cong, mỗi nhóm lồng vào nhau rất khít.
  const interA = byArea.filter((_, i) => i % 2 === 0).concat(byArea.filter((_, i) => i % 2 === 1));
  const interB = byArea.filter((_, i) => i % 2 === 1).concat(byArea.filter((_, i) => i % 2 === 0));
  const byMinWDesc = byMinW.slice().reverse();

  const zeroAngles = () => new Array(nInst).fill(0);
  const seeds: Genome[] = [
    { order: interA, angleIdx: zeroAngles(), rule: 0 },
    { order: interB, angleIdx: zeroAngles(), rule: 0 },
    { order: byMinWDesc, angleIdx: zeroAngles(), rule: 0 },
    { order: byArea, angleIdx: zeroAngles(), rule: 0 },
    { order: byArea, angleIdx: zeroAngles(), rule: 1 },
    { order: byLen, angleIdx: zeroAngles(), rule: 0 },
    { order: byBBox, angleIdx: zeroAngles(), rule: 0 },
    { order: byMinW, angleIdx: zeroAngles(), rule: 0 },
    { order: byLen, angleIdx: zeroAngles(), rule: 1 },
  ];
  const POP = 12;
  while (seeds.length < POP) {
    const o = idxAll.slice();
    for (let i = o.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      [o[i], o[j]] = [o[j], o[i]];
    }
    seeds.push({
      order: o,
      angleIdx: idxAll.map(() => Math.floor(rng() * 4)),
      rule: rng() < 0.5 ? 0 : 1,
    });
  }

  let iterations = 0;
  let best: Evaluated | null = null;
  let lastReport = t0;

  const report = (label: string) => {
    if (!cb.onProgress) return;
    const el = now() - t0;
    cb.onProgress({
      fraction: Math.min(1, el / params.timeLimitMs),
      elapsedMs: el,
      iterations,
      best: best ? toResult(best, params, now() - t0, iterations) : null,
      label,
    });
  };

  const pop: Evaluated[] = [];
  for (const g of seeds) {
    if (now() > deadline || cb.shouldStop?.()) break;
    const e = evaluate(g);
    iterations++;
    pop.push(e);
    if (!best || e.cost < best.cost) best = e;
    if (now() - lastReport > 250) {
      lastReport = now();
      report('Đang thử phương án khởi đầu…');
    }
  }
  if (!best && pop.length === 0) {
    // hết giờ ngay từ đầu — vẫn phải trả 1 kết quả
    best = evaluate(seeds[0]);
    iterations++;
  }

  // ── vòng tiến hoá ────────────────────────────────────────────────────────
  const orderCrossover = (a: number[], b: number[]): number[] => {
    const n = a.length;
    let i = Math.floor(rng() * n);
    let j = Math.floor(rng() * n);
    if (i > j) [i, j] = [j, i];
    const child = new Array<number>(n).fill(-1);
    const taken = new Set<number>();
    for (let k = i; k <= j; k++) {
      child[k] = a[k];
      taken.add(a[k]);
    }
    let w = 0;
    for (const v of b) {
      if (taken.has(v)) continue;
      while (child[w] !== -1) w++;
      child[w] = v;
    }
    return child;
  };

  while (now() < deadline && !cb.shouldStop?.()) {
    pop.sort((x, y) => x.cost - y.cost);
    if (pop.length > POP) pop.length = POP;
    const pa = pop[Math.floor(rng() * Math.min(4, pop.length))];
    const pb = pop[Math.floor(rng() * pop.length)];
    const order = orderCrossover(pa.genome.order, pb.genome.order);
    const angleIdx = pa.genome.angleIdx.slice();
    // đột biến
    const swaps = 1 + Math.floor(rng() * 3);
    for (let k = 0; k < swaps; k++) {
      const i = Math.floor(rng() * nInst);
      const j = Math.floor(rng() * nInst);
      [order[i], order[j]] = [order[j], order[i]];
    }
    const angMut = 1 + Math.floor(rng() * 4);
    for (let k = 0; k < angMut; k++) {
      const i = Math.floor(rng() * nInst);
      const prep = preps[insts[i].prepIndex];
      angleIdx[i] = Math.floor(rng() * Math.min(8, prep.angles.length));
    }
    const rule = rng() < 0.2 ? 1 - pa.genome.rule : pa.genome.rule;
    const e = evaluate({ order, angleIdx, rule });
    iterations++;
    pop.push(e);
    if (!best || e.cost < best.cost) best = e;
    if (now() - lastReport > 250) {
      lastReport = now();
      report('Đang tối ưu…');
    }
  }

  const res = toResult(best!, params, now() - t0, iterations);
  report('Xong');
  return res;
}

function toResult(e: Evaluated, params: NestParams, elapsed: number, iterations: number): NestResult {
  const total = e.sheets.length * params.sheetW * params.sheetH;
  return {
    sheets: e.sheets,
    unplaced: e.unplaced,
    utilization: total > 0 ? e.placedArea / total : 0,
    elapsedMs: elapsed,
    iterations,
    params,
  };
}

// ─────────────────────────── Kiểm tra kết quả ───────────────────────────

export interface ValidationIssue {
  kind: 'overlap' | 'gap' | 'outside' | 'missing';
  message: string;
  a?: string;
  b?: string;
  value?: number;
}

function placedRings(pl: Placement, part: Part): Ring[] {
  return part.rings.map((r) => applyPlacementRing(r, pl));
}

/** Khoảng cách nhỏ nhất giữa 2 vòng (0 nếu cắt nhau hoặc lồng nhau). */
function ringDistance(a: Ring, b: Ring): number {
  let min = Infinity;
  for (let i = 0; i < a.length; i++) {
    const a1 = a[i];
    const a2 = a[(i + 1) % a.length];
    for (let j = 0; j < b.length; j++) {
      const b1 = b[j];
      const b2 = b[(j + 1) % b.length];
      if (segSegIntersect(a1, a2, b1, b2)) return 0;
      const d = segSegDistance(a1, a2, b1, b2);
      if (d < min) min = d;
    }
  }
  if (pointInRing(a[0], b) || pointInRing(b[0], a)) return 0;
  return min === Infinity ? Infinity : min;
}

export function validateLayout(
  sheets: SheetLayout[], parts: Part[], params: NestParams
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const byId = new Map(parts.map((p) => [p.id, p]));
  const eps = 1e-6;

  let totalPlaced = 0;
  for (const sh of sheets) {
    totalPlaced += sh.placements.length;
    const rings = sh.placements.map((pl) => {
      const part = byId.get(pl.partId)!;
      return { pl, outer: placedRings(pl, part)[0] };
    });
    // trong tấm trừ lề
    for (const { pl, outer } of rings) {
      const b = ringBBox(outer);
      if (
        b.minX < params.margin - eps || b.minY < params.margin - eps ||
        b.maxX > sh.width - params.margin + eps || b.maxY > sh.height - params.margin + eps
      ) {
        issues.push({
          kind: 'outside',
          a: `${pl.partId}#${pl.instance}`,
          message: `Chi tiết ${pl.partId}#${pl.instance} nằm ngoài vùng tấm trừ lề (bbox ${b.minX.toFixed(1)}..${b.maxX.toFixed(1)} × ${b.minY.toFixed(1)}..${b.maxY.toFixed(1)}).`,
        });
      }
    }
    // chồng lấn + khe
    for (let i = 0; i < rings.length; i++) {
      for (let j = i + 1; j < rings.length; j++) {
        const ba = ringBBox(rings[i].outer);
        const bb = ringBBox(rings[j].outer);
        if (
          ba.maxX + params.gap < bb.minX || bb.maxX + params.gap < ba.minX ||
          ba.maxY + params.gap < bb.minY || bb.maxY + params.gap < ba.minY
        ) continue;
        const d = ringDistance(rings[i].outer, rings[j].outer);
        const na = `${rings[i].pl.partId}#${rings[i].pl.instance}`;
        const nb = `${rings[j].pl.partId}#${rings[j].pl.instance}`;
        if (d <= eps) {
          issues.push({ kind: 'overlap', a: na, b: nb, value: d, message: `Chi tiết ${na} và ${nb} chồng lấn nhau.` });
        } else if (d < params.gap - 1e-6) {
          issues.push({ kind: 'gap', a: na, b: nb, value: d, message: `Chi tiết ${na} và ${nb} chỉ cách nhau ${d.toFixed(2)}mm < khe ${params.gap}mm.` });
        }
      }
    }
  }

  const expected = parts.filter((p) => p.enabled).reduce((s, p) => s + Math.max(1, p.qty), 0);
  if (totalPlaced !== expected) {
    issues.push({
      kind: 'missing',
      value: expected - totalPlaced,
      message: `Thiếu chi tiết: đã xếp ${totalPlaced}/${expected}.`,
    });
  }
  return issues;
}
