/**
 * Đồ nghề dùng chung cho test của riêng thư mục nest.
 * Cố ý KHÔNG dùng lại `tests/helpers.ts` để test của thợ khác đổi gì cũng
 * không kéo theo test ở đây.
 */
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { Part, Point, Ring } from '../../types';

export const FIXTURE = resolve(__dirname, '../../../fixtures/gui-son.dxf');

export function hasFixture(): boolean {
  return existsSync(FIXTURE);
}

export function readFixture(): string {
  return readFileSync(FIXTURE, 'utf8');
}

/** Hình chữ nhật CCW, góc dưới-trái ở (x, y). */
export function rectRing(x: number, y: number, w: number, h: number): Ring {
  return [
    { x, y },
    { x: x + w, y },
    { x: x + w, y: y + h },
    { x, y: y + h },
  ];
}

/** Dựng một chi tiết hình chữ nhật w × h để test (đã normalize về gốc 0,0). */
export function rectPart(id: string, w: number, h: number, qty = 1): Part {
  return {
    id,
    rings: [rectRing(0, 0, w, h)],
    area: w * h,
    bbox: { minX: 0, minY: 0, maxX: w, maxY: h },
    vertexCount: 4,
    minWidth: Math.min(w, h),
    maxLength: Math.max(w, h),
    qty,
    enabled: true,
    fitsSheet: true,
  };
}

/**
 * CÁCH CŨ của thợ kho tôn thừa: bỏ qua hình dạng thật của phần thừa, chỉ lấy
 * HÌNH CHỮ NHẬT LỚN NHẤT NỘI TIẾP phần còn lại rồi coi nó như một tấm nhỏ.
 * Dựng lại ở đây để có CON SỐ so sánh thật, không phải lời khai.
 *
 * Thuật toán: rời rạc hoá tấm thành lưới `cell` mm, đánh dấu ô nào bị vùng cấm
 * chiếm, rồi chạy "maximal rectangle in binary matrix" (ngăn xếp histogram).
 */
export function largestFreeRect(
  sheetW: number, sheetH: number, blocked: Ring[], cell = 10
): { w: number; h: number; x: number; y: number } {
  const gw = Math.floor(sheetW / cell);
  const gh = Math.floor(sheetH / cell);
  const free = new Uint8Array(gw * gh).fill(1);
  for (const ring of blocked) {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const p of ring) {
      if (p.x < minX) minX = p.x;
      if (p.y < minY) minY = p.y;
      if (p.x > maxX) maxX = p.x;
      if (p.y > maxY) maxY = p.y;
    }
    const c0 = Math.max(0, Math.floor(minX / cell));
    const c1 = Math.min(gw - 1, Math.ceil(maxX / cell));
    const r0 = Math.max(0, Math.floor(minY / cell));
    const r1 = Math.min(gh - 1, Math.ceil(maxY / cell));
    for (let r = r0; r <= r1; r++) {
      for (let c = c0; c <= c1; c++) {
        const px = (c + 0.5) * cell;
        const py = (r + 0.5) * cell;
        if (pointInPoly({ x: px, y: py }, ring)) free[r * gw + c] = 0;
      }
    }
  }
  const heights = new Int32Array(gw);
  let best = { w: 0, h: 0, x: 0, y: 0 };
  let bestArea = 0;
  for (let r = 0; r < gh; r++) {
    for (let c = 0; c < gw; c++) heights[c] = free[r * gw + c] ? heights[c] + 1 : 0;
    // histogram lớn nhất của hàng r (hàng r là ĐỈNH của hình chữ nhật)
    const stack: number[] = [];
    for (let c = 0; c <= gw; c++) {
      const h = c === gw ? 0 : heights[c];
      while (stack.length && heights[stack[stack.length - 1]] >= h) {
        const top = stack.pop()!;
        const hh = heights[top];
        const left = stack.length ? stack[stack.length - 1] + 1 : 0;
        const width = c - left;
        const area = hh * width;
        if (area > bestArea) {
          bestArea = area;
          best = { w: width * cell, h: hh * cell, x: left * cell, y: (r + 1 - hh) * cell };
        }
      }
      stack.push(c);
    }
  }
  return best;
}

function pointInPoly(pt: Point, ring: Ring): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const a = ring[i];
    const b = ring[j];
    if ((a.y > pt.y) !== (b.y > pt.y) && pt.x < ((b.x - a.x) * (pt.y - a.y)) / (b.y - a.y) + a.x) {
      inside = !inside;
    }
  }
  return inside;
}

/** Diện tích tuyệt đối của một vòng. */
export function ringArea(ring: Ring): number {
  let a = 0;
  for (let i = 0; i < ring.length; i++) {
    const p1 = ring[i];
    const p2 = ring[(i + 1) % ring.length];
    a += p1.x * p2.y - p2.x * p1.y;
  }
  return Math.abs(a / 2);
}
