/**
 * Hình học riêng cho kho tôn thừa.
 *
 * Việc khó nhất ở đây: tấm tôn thừa sau khi cắt KHÔNG phải hình chữ nhật, nhưng
 * engine xếp phôi (src/nest) chỉ biết xếp lên hình chữ nhật (NestParams.sheetW/sheetH).
 * Nên ta tìm HÌNH CHỮ NHẬT LỚN NHẤT NẰM GỌN TRONG tấm thừa rồi bảo engine xếp vào đó.
 * Cách này thiệt một ít diện tích ở các góc lồi lõm, nhưng bù lại TUYỆT ĐỐI an toàn:
 * không bao giờ đặt chi tiết ra ngoài phần tôn còn thật.
 */
import type { Point, Ring } from '../types';

/** Diện tích thật của đa giác nhiều vòng = |biên ngoài| − Σ|lỗ|, mm². */
export function polygonArea(rings: Ring[]): number {
  if (rings.length === 0) return 0;
  const abs = (r: Ring) => {
    let a = 0;
    for (let i = 0; i < r.length; i++) {
      const p1 = r[i];
      const p2 = r[(i + 1) % r.length];
      a += p1.x * p2.y - p2.x * p1.y;
    }
    return Math.abs(a / 2);
  };
  let area = abs(rings[0]);
  for (let i = 1; i < rings.length; i++) area -= abs(rings[i]);
  return Math.max(0, area);
}

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Khung bao của toàn bộ các vòng. */
export function polygonBounds(rings: Ring[]): Box {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const r of rings) {
    for (const p of r) {
      if (p.x < minX) minX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.x > maxX) maxX = p.x;
      if (p.y > maxY) maxY = p.y;
    }
  }
  if (!Number.isFinite(minX)) return { x: 0, y: 0, w: 0, h: 0 };
  return { x: minX, y: minY, w: maxX - minX, h: maxY - minY };
}

/** Hình chữ nhật đầy đủ (dùng khi người dùng chỉ khai rộng × dài). */
export function rectPolygon(w: number, h: number): Ring[] {
  return [[{ x: 0, y: 0 }, { x: w, y: 0 }, { x: w, y: h }, { x: 0, y: h }]];
}

/**
 * Quét ngang một hàng y, trả về mảng ô (cột) nằm TRONG đa giác theo luật chẵn-lẻ.
 * Luật chẵn-lẻ tự động xử lý luôn các lỗ thủng nên không cần phân biệt vòng ngoài/lỗ.
 */
function scanRow(rings: Ring[], y: number, x0: number, cell: number, cols: number, out: Uint8Array): void {
  const xs: number[] = [];
  for (const r of rings) {
    const n = r.length;
    for (let i = 0; i < n; i++) {
      const a = r[i];
      const b = r[(i + 1) % n];
      // Cạnh cắt đường y nếu y nằm giữa a.y và b.y (nửa mở để không đếm đôi ở đỉnh).
      if ((a.y <= y && b.y > y) || (b.y <= y && a.y > y)) {
        xs.push(a.x + ((y - a.y) / (b.y - a.y)) * (b.x - a.x));
      }
    }
  }
  out.fill(0);
  if (xs.length < 2) return;
  xs.sort((p, q) => p - q);
  for (let k = 0; k + 1 < xs.length; k += 2) {
    const left = xs[k];
    const right = xs[k + 1];
    // Chỉ nhận ô nằm GỌN trong khoảng [left, right] — thà thiếu còn hơn thừa ra ngoài tôn.
    let c0 = Math.ceil((left - x0) / cell);
    let c1 = Math.floor((right - x0) / cell) - 1;
    if (c0 < 0) c0 = 0;
    if (c1 > cols - 1) c1 = cols - 1;
    for (let c = c0; c <= c1; c++) out[c] = 1;
  }
}

/** Hình chữ nhật to nhất trong một ma trận 0/1, thuật toán histogram O(hàng × cột). */
function maxRectInMask(mask: Uint8Array, cols: number, rows: number): { c: number; r: number; w: number; h: number } {
  const heights = new Int32Array(cols);
  const stack = new Int32Array(cols + 1);
  let best = { c: 0, r: 0, w: 0, h: 0 };
  let bestArea = 0;
  for (let r = 0; r < rows; r++) {
    const base = r * cols;
    for (let c = 0; c < cols; c++) heights[c] = mask[base + c] ? heights[c] + 1 : 0;
    let sp = 0;
    for (let c = 0; c <= cols; c++) {
      const h = c === cols ? 0 : heights[c];
      while (sp > 0 && heights[stack[sp - 1]] >= h) {
        const top = stack[--sp];
        const hh = heights[top];
        const left = sp > 0 ? stack[sp - 1] + 1 : 0;
        const w = c - left;
        const area = w * hh;
        if (area > bestArea && hh > 0 && w > 0) {
          bestArea = area;
          best = { c: left, r: r - hh + 1, w, h: hh };
        }
      }
      stack[sp++] = c;
    }
  }
  return best;
}

export interface UsableRect extends Box {
  /** Tỉ lệ diện tích hình chữ nhật này so với diện tích thật của tấm thừa, 0..1. */
  coverage: number;
}

/**
 * Tìm hình chữ nhật lớn nhất nằm gọn trong tấm thừa.
 * @param cellHint cạnh ô lưới mong muốn (mm); hàm tự nới ra để lưới không quá ~240×240 ô.
 * Trả về hình chữ nhật trong hệ toạ độ GỐC của đa giác (đã tính cả offset khung bao).
 */
export function largestInnerRect(rings: Ring[], cellHint = 10): UsableRect {
  const bb = polygonBounds(rings);
  if (bb.w <= 0 || bb.h <= 0) return { x: bb.x, y: bb.y, w: 0, h: 0, coverage: 0 };

  const MAX_SIDE = 240;
  const cell = Math.max(cellHint, bb.w / MAX_SIDE, bb.h / MAX_SIDE, 0.5);
  const cols = Math.max(1, Math.floor(bb.w / cell));
  const rows = Math.max(1, Math.floor(bb.h / cell));

  const mask = new Uint8Array(cols * rows);
  const row = new Uint8Array(cols);
  for (let r = 0; r < rows; r++) {
    // Quét ở MÉP TRÊN và MÉP DƯỚI của ô rồi lấy giao: ô chỉ được nhận khi cả hai
    // mép đều nằm trong tôn, nên ô không bao giờ thò ra ngoài phần vật liệu thật.
    const yLo = bb.y + r * cell;
    const yHi = bb.y + (r + 1) * cell;
    scanRow(rings, yLo + 1e-6, bb.x, cell, cols, row);
    mask.set(row, r * cols);
    scanRow(rings, yHi - 1e-6, bb.x, cell, cols, row);
    const base = r * cols;
    for (let c = 0; c < cols; c++) if (!row[c]) mask[base + c] = 0;
  }

  const best = maxRectInMask(mask, cols, rows);
  const rect: Box = {
    x: bb.x + best.c * cell,
    y: bb.y + best.r * cell,
    w: best.w * cell,
    h: best.h * cell,
  };
  const total = polygonArea(rings);
  return { ...rect, coverage: total > 0 ? (rect.w * rect.h) / total : 0 };
}

/** Kiểm tra nhanh một điểm có nằm trong đa giác (luật chẵn-lẻ) — dùng để test. */
export function pointInPolygon(rings: Ring[], p: Point): boolean {
  let inside = false;
  for (const r of rings) {
    const n = r.length;
    for (let i = 0; i < n; i++) {
      const a = r[i];
      const b = r[(i + 1) % n];
      if ((a.y > p.y) !== (b.y > p.y)) {
        const x = a.x + ((p.y - a.y) / (b.y - a.y)) * (b.x - a.x);
        if (x > p.x) inside = !inside;
      }
    }
  }
  return inside;
}
