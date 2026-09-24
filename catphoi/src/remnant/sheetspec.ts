/**
 * Đổi tấm thừa trong kho thành "tấm có vùng cấm" để đưa thẳng cho engine xếp.
 *
 * ── Vì sao có file này (VIỆC 3) ──────────────────────────────────────────
 * Thợ trước phải đi đường vòng: tìm HÌNH CHỮ NHẬT LỚN NHẤT nội tiếp phần thừa
 * rồi bảo engine xếp vào đó — mất khoảng 30% diện tích ở các góc lồi lõm, vì
 * engine chưa nhận được vùng cấm. Nay hợp đồng của thợ lõi có:
 *
 *     NestSheetSpec { w, h, blocked?: Ring[], label? }
 *
 * nên chỉ việc truyền THẲNG các lỗ đã cắt vào `blocked`, bỏ hẳn cách cũ.
 * Tấm gửi cho engine LUÔN là nguyên khổ 2000×6000 (hoặc đúng khổ tấm gốc),
 * các lỗ giữ đúng vị trí — ra xưởng đặt bản vẽ không lệch.
 */
import type { Part, Ring, SheetLayout } from '../types';
import { applyPlacementRing } from '../types';
import type { NestSheetSpec } from '../ui/nest-multi-core';
import type { Remnant } from './types';
import { polygonBounds } from './geometry';
import { isFullSheetRing } from './normalize';

export type { NestSheetSpec };

/**
 * Các ô chữ nhật phủ kín phần NẰM NGOÀI biên ngoài, trong khung bao w×h.
 * Chỉ dùng cho tấm KIỂU CŨ (mảnh thừa rời, biên ngoài không phải hình chữ nhật
 * nguyên khổ): phải cấm luôn phần "không có tôn" quanh mảnh đó.
 *
 * Quét lưới rồi gộp theo hàng — thà cấm rộng hơn một ô còn hơn để chi tiết lọt
 * ra ngoài tôn.
 */
export function blockedOutside(outer: Ring, w: number, h: number, cell = 25): Ring[] {
  if (!outer || outer.length < 3 || w <= 0 || h <= 0) return [];
  const cols = Math.max(1, Math.ceil(w / cell));
  const rows = Math.max(1, Math.ceil(h / cell));
  const inside = (px: number, py: number): boolean => {
    let hit = false;
    for (let i = 0, j = outer.length - 1; i < outer.length; j = i++) {
      const a = outer[i];
      const b = outer[j];
      if ((a.y > py) !== (b.y > py)) {
        const x = a.x + ((py - a.y) / (b.y - a.y)) * (b.x - a.x);
        if (x > px) hit = !hit;
      }
    }
    return hit;
  };
  /** Ô được coi là "có tôn" khi CẢ 4 góc + tâm đều nằm trong biên ngoài. */
  const cellOk = (c: number, r: number): boolean => {
    const x0 = c * cell;
    const y0 = r * cell;
    const x1 = Math.min(w, x0 + cell);
    const y1 = Math.min(h, y0 + cell);
    const e = 1e-6;
    return inside(x0 + e, y0 + e) && inside(x1 - e, y0 + e)
      && inside(x1 - e, y1 - e) && inside(x0 + e, y1 - e)
      && inside((x0 + x1) / 2, (y0 + y1) / 2);
  };

  const out: Ring[] = [];
  for (let r = 0; r < rows; r++) {
    let run = -1;
    for (let c = 0; c <= cols; c++) {
      const bad = c < cols && !cellOk(c, r);
      if (bad && run < 0) run = c;
      if (!bad && run >= 0) {
        const x0 = run * cell;
        const x1 = Math.min(w, c * cell);
        const y0 = r * cell;
        const y1 = Math.min(h, (r + 1) * cell);
        out.push([{ x: x0, y: y0 }, { x: x1, y: y0 }, { x: x1, y: y1 }, { x: x0, y: y1 }]);
        run = -1;
      }
    }
  }
  return out;
}

/**
 * Tấm gửi cho engine: khổ NGUYÊN của tấm gốc + mọi vùng cấm.
 * Tấm kiểu mới: vùng cấm = đúng các lỗ đã cắt.
 * Tấm kiểu cũ  : vùng cấm = các lỗ + phần trống quanh mảnh thừa.
 */
export function sheetSpecOf(r: Remnant): NestSheetSpec {
  const w = r.sheetWidthMm;
  const h = r.sheetLengthMm;
  const blocked: Ring[] = [...r.cuts];
  const outer = r.polygon?.[0];
  if (r.legacy && outer && !isFullSheetRing(outer, w, h)) {
    blocked.push(...blockedOutside(outer, w, h));
  }
  return { w, h, blocked, label: r.name };
}

/** Đổi cả danh sách tấm thừa đang tích chọn thành danh sách tấm cho engine. */
export function sheetSpecsOf(list: Remnant[]): NestSheetSpec[] {
  return list.map(sheetSpecOf);
}

/**
 * Lấy CÁC LỖ mà một tấm vừa xếp sẽ để lại sau khi cắt.
 * Đây chính là thứ nút "Lưu tấm thừa từ tấm này" ghi vào kho: biên ngoài của
 * từng chi tiết đã đặt, trong hệ toạ độ của tấm.
 */
export function cutsFromSheet(sheet: SheetLayout, partsById: Map<string, Part>): Ring[] {
  const out: Ring[] = [];
  for (const pl of sheet.placements) {
    const part = partsById.get(pl.partId);
    if (!part || !part.rings.length) continue;
    out.push(applyPlacementRing(part.rings[0], pl));
  }
  // Tấm thừa có thể được xếp tiếp → gộp luôn các lỗ đã có sẵn từ lượt trước.
  const prev = (sheet as SheetLayout & { cuts?: Ring[] }).cuts;
  if (Array.isArray(prev)) out.push(...prev.filter((c) => Array.isArray(c) && c.length >= 3));
  return out;
}

/** Diện tích tôn CÒN LẠI của tấm thừa = khổ gốc − tổng các lỗ, mm². */
export function remainingArea(r: Remnant): number {
  const abs = (ring: Ring) => {
    let a = 0;
    for (let i = 0; i < ring.length; i++) {
      const p1 = ring[i];
      const p2 = ring[(i + 1) % ring.length];
      a += p1.x * p2.y - p2.x * p1.y;
    }
    return Math.abs(a / 2);
  };
  const outer = r.polygon?.[0];
  const base = outer ? abs(outer) : r.sheetWidthMm * r.sheetLengthMm;
  let holes = 0;
  for (const c of r.cuts) holes += abs(c);
  // Tấm kiểu cũ đã trừ lỗ trong polygon rồi thì polygon[1..] chính là cuts.
  return Math.max(0, base - holes);
}

/** Khung bao thật của hình đang lưu — dùng để kiểm tra "luôn là 2000×6000". */
export function boundsOf(r: Remnant): { w: number; h: number } {
  const b = polygonBounds(r.polygon);
  return { w: b.w, h: b.h };
}
