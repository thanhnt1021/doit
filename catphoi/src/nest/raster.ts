/**
 * Raster hoá chi tiết thành bitmap bit-packed để dò va chạm cực nhanh.
 *
 * VÌ SAO DÙNG BITMAP CHỨ KHÔNG DÙNG NFP/Minkowski:
 * bước xoay mặc định 5° → 72 góc. NFP phải dựng và cache cho TỪNG CẶP
 * (chi tiết × góc) → 72² tổ hợp cho mỗi cặp chi tiết, nổ tổ hợp. Đó đúng là
 * chỗ Deepnest chết trên file thật. Bitmap xử lý góc bất kỳ và hình lõm
 * (cần cho việc các thanh sườn cong lồng vào nhau) với chi phí ổn định.
 *
 * BẢO ĐẢM TOÁN HỌC (không được phá):
 *  - Raster hoá theo kiểu BẢO TOÀN: ô được bật nếu ô vuông đó GIAO với đa giác
 *    (cạnh đi qua ô → bật; ô nằm trọn bên trong → bật). Kết quả là TẬP CHA của hình.
 *  - Nở (dilate) thêm m ô với m = ceil((khe/2)/cạnh_ô) → tập kết quả chứa
 *    hình ⊕ đĩa(khe/2).
 *  ⇒ Hai bitmap đã nở KHÔNG chồng nhau ⟹ khoảng cách 2 hình thật ≥ khe.
 */
import type { Point, Ring } from '../types';

export interface BaseBitmap {
  /** Số ô theo trục x, y. */
  w: number;
  h: number;
  /** Số word (Uint32) mỗi hàng. */
  words: number;
  bits: Uint32Array;
  /** Word khác 0 đầu/cuối của từng hàng (-1 nếu hàng rỗng) — để thoát sớm. */
  rowFirst: Int32Array;
  rowLast: Int32Array;
  /** Bit thấp nhất được bật của từng hàng (-1 nếu rỗng) — lọc nhanh khi dò va chạm. */
  rowLowBit: Int32Array;
  /** Bit cao nhất được bật của từng hàng (-1 nếu rỗng). */
  rowHighBit: Int32Array;
  /**
   * Hàng THẤP NHẤT được bật của từng cột (-1 nếu cột rỗng) — "đáy" của chi tiết.
   * Dùng cho phép THẢ RƠI theo trục y: vị trí chạm đất tính được bằng công thức,
   * không cần dò va chạm (xem Nester.dropY).
   */
  colLow: Int32Array;
  /** Hàng CAO NHẤT được bật của từng cột (-1 nếu rỗng) — để cập nhật đường bao tấm. */
  colHigh: Int32Array;
  /** Số ô được bật (diện tích raster, để tính độ chặt). */
  cellCount: number;
  /** Toạ độ (mm) góc dưới-trái của ô (0,0), trong hệ toạ độ của HÌNH ĐÃ XOAY. */
  originX: number;
  originY: number;
  cell: number;
}

/** Đi qua mọi ô mà đoạn thẳng cắt (Amanatides–Woo). */
function walkEdge(
  ax: number, ay: number, bx: number, by: number,
  w: number, h: number, mark: (i: number, j: number) => void
): void {
  let ix = Math.floor(ax);
  let iy = Math.floor(ay);
  const ixEnd = Math.floor(bx);
  const iyEnd = Math.floor(by);
  const dx = bx - ax;
  const dy = by - ay;
  const stepX = dx > 0 ? 1 : -1;
  const stepY = dy > 0 ? 1 : -1;
  const adx = Math.abs(dx);
  const ady = Math.abs(dy);
  let tMaxX = adx < 1e-12 ? Infinity : (dx > 0 ? ix + 1 - ax : ax - ix) / adx;
  let tMaxY = ady < 1e-12 ? Infinity : (dy > 0 ? iy + 1 - ay : ay - iy) / ady;
  const tDx = adx < 1e-12 ? Infinity : 1 / adx;
  const tDy = ady < 1e-12 ? Infinity : 1 / ady;
  let guard = 0;
  const limit = w + h + 8;
  for (;;) {
    if (ix >= 0 && iy >= 0 && ix < w && iy < h) mark(ix, iy);
    if (ix === ixEnd && iy === iyEnd) break;
    if (++guard > limit * 4) break;
    if (tMaxX < tMaxY) {
      tMaxX += tDx;
      ix += stepX;
    } else {
      tMaxY += tDy;
      iy += stepY;
    }
  }
}

/**
 * Raster hoá 1 vòng kín (đã ở hệ toạ độ mm sau khi xoay) thành bitmap đã nở.
 * @param ring vòng ngoài của chi tiết (MVP coi chi tiết là ĐẶC — bỏ qua lỗ khi xếp).
 * @param cell cạnh ô, mm.
 * @param dil số ô nở thêm mỗi phía.
 */
export function rasterizeRing(ring: Ring, cell: number, dil: number): BaseBitmap {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of ring) {
    if (p.x < minX) minX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.x > maxX) maxX = p.x;
    if (p.y > maxY) maxY = p.y;
  }
  const w0 = Math.floor((maxX - minX) / cell) + 1;
  const h0 = Math.floor((maxY - minY) / cell) + 1;
  const tmp = new Uint8Array(w0 * h0);

  // 1) cạnh đi qua ô nào thì bật ô đó
  const n = ring.length;
  for (let i = 0; i < n; i++) {
    const a = ring[i];
    const b = ring[(i + 1) % n];
    walkEdge(
      (a.x - minX) / cell, (a.y - minY) / cell,
      (b.x - minX) / cell, (b.y - minY) / cell,
      w0, h0,
      (ix, iy) => { tmp[iy * w0 + ix] = 1; }
    );
  }

  // 2) tô trong: quét scanline theo tâm ô
  const xs: number[] = [];
  for (let j = 0; j < h0; j++) {
    const yc = minY + (j + 0.5) * cell;
    xs.length = 0;
    for (let i = 0; i < n; i++) {
      const a = ring[i];
      const b = ring[(i + 1) % n];
      if ((a.y > yc) !== (b.y > yc)) {
        xs.push(a.x + ((yc - a.y) / (b.y - a.y)) * (b.x - a.x));
      }
    }
    if (xs.length < 2) continue;
    xs.sort((p, q) => p - q);
    const rowOff = j * w0;
    for (let k = 0; k + 1 < xs.length; k += 2) {
      let i0 = Math.ceil((xs[k] - minX) / cell - 0.5);
      let i1 = Math.floor((xs[k + 1] - minX) / cell - 0.5);
      if (i0 < 0) i0 = 0;
      if (i1 >= w0) i1 = w0 - 1;
      for (let i = i0; i <= i1; i++) tmp[rowOff + i] = 1;
    }
  }

  // 3) nở dil ô (hình vuông Chebyshev ⊇ đĩa) — tách rời ngang rồi dọc
  const w = w0 + 2 * dil;
  const h = h0 + 2 * dil;
  const hz = new Uint8Array(w * h0);
  for (let j = 0; j < h0; j++) {
    const src = j * w0;
    const dst = j * w;
    for (let i = 0; i < w0; i++) {
      if (tmp[src + i]) {
        const a = i + dil - dil;
        const b = i + dil + dil;
        for (let k = a; k <= b; k++) hz[dst + k] = 1;
      }
    }
  }
  const words = ((w + 31) >> 5);
  const bits = new Uint32Array(words * h);
  for (let j = 0; j < h; j++) {
    const lo = Math.max(0, j - 2 * dil);
    const hi = Math.min(h0 - 1, j);
    const dst = j * words;
    for (let s = lo; s <= hi; s++) {
      const src = s * w;
      for (let i = 0; i < w; i++) {
        if (hz[src + i]) bits[dst + (i >> 5)] |= 1 << (i & 31);
      }
    }
  }

  const rowFirst = new Int32Array(h).fill(-1);
  const rowLast = new Int32Array(h).fill(-1);
  const rowLowBit = new Int32Array(h).fill(-1);
  const rowHighBit = new Int32Array(h).fill(-1);
  const colLow = new Int32Array(w).fill(-1);
  const colHigh = new Int32Array(w).fill(-1);
  let cellCount = 0;
  for (let j = 0; j < h; j++) {
    const off = j * words;
    let f = -1, l = -1;
    for (let i = 0; i < words; i++) {
      const wv = bits[off + i];
      if (wv !== 0) {
        if (f < 0) f = i;
        l = i;
        // duyệt từng bit đang bật để dựng đường bao theo cột
        let m = wv >>> 0;
        while (m !== 0) {
          const lsb = m & -m;
          const b = 31 - Math.clz32(lsb >>> 0);
          const col = i * 32 + b;
          if (colLow[col] < 0) colLow[col] = j;
          colHigh[col] = j;
          cellCount++;
          m = (m ^ lsb) >>> 0;
        }
      }
    }
    rowFirst[j] = f;
    rowLast[j] = l;
    if (f >= 0) {
      const wv = bits[off + f];
      let b = 0;
      while (((wv >>> b) & 1) === 0) b++;
      rowLowBit[j] = f * 32 + b;
      const hv = bits[off + l];
      rowHighBit[j] = l * 32 + (31 - Math.clz32(hv >>> 0));
    }
  }

  return {
    w, h, words, bits, rowFirst, rowLast, rowLowBit, rowHighBit,
    colLow, colHigh, cellCount,
    originX: minX - dil * cell,
    originY: minY - dil * cell,
    cell,
  };
}

/** Bitmap chi tiết đã dịch bit sẵn `s` bit (0..31) để AND thẳng theo word. */
export interface ShiftedBitmap {
  words: number;
  bits: Uint32Array;
  rowFirst: Int32Array;
  rowLast: Int32Array;
  h: number;
}

export function shiftBitmap(bm: BaseBitmap, s: number): ShiftedBitmap {
  const sw = bm.words + 1;
  const out = new Uint32Array(sw * bm.h);
  const rf = new Int32Array(bm.h).fill(-1);
  const rl = new Int32Array(bm.h).fill(-1);
  for (let j = 0; j < bm.h; j++) {
    const f = bm.rowFirst[j];
    if (f < 0) continue;
    const l = bm.rowLast[j];
    const src = j * bm.words;
    const dst = j * sw;
    if (s === 0) {
      for (let i = f; i <= l; i++) out[dst + i] = bm.bits[src + i];
      rf[j] = f;
      rl[j] = l;
    } else {
      for (let i = f; i <= l + 1; i++) {
        const cur = i <= l ? bm.bits[src + i] : 0;
        const prev = i - 1 >= f ? bm.bits[src + i - 1] : 0;
        out[dst + i] = ((cur << s) | (prev >>> (32 - s))) >>> 0;
      }
      rf[j] = f;
      rl[j] = l + 1;
    }
  }
  return { words: sw, bits: out, rowFirst: rf, rowLast: rl, h: bm.h };
}

/** Xoay (và lật gương) 1 vòng quanh gốc toạ độ — cùng quy ước với applyPlacement(). */
export function transformRing(ring: Ring, deg: number, mirrored: boolean): Ring {
  const a = (deg * Math.PI) / 180;
  const c = Math.cos(a);
  const s = Math.sin(a);
  const out: Point[] = new Array(ring.length);
  for (let i = 0; i < ring.length; i++) {
    const px = mirrored ? -ring[i].x : ring[i].x;
    const py = ring[i].y;
    out[i] = { x: px * c - py * s, y: px * s + py * c };
  }
  return out;
}
