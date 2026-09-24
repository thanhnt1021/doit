/**
 * Chuẩn hoá tấm thừa — VIỆC 3.
 *
 * Mọi dữ liệu tấm thừa chảy vào trình duyệt đều phải đi qua `normalizeRemnant()`:
 * từ máy chủ, từ bản chép localStorage (có thể còn dữ liệu kiểu CŨ), hay từ kết
 * quả vừa xếp. Sau khi qua đây thì chắc chắn có đủ:
 *   sheetWidthMm / sheetLengthMm  (khổ tấm gốc)
 *   cuts                          (các lỗ đã cắt)
 *   polygon                       ([biên ngoài, ...lỗ] để vẽ)
 * và khung bao widthMm × lengthMm ĐÚNG BẰNG khổ tấm gốc với tấm kiểu mới.
 *
 * DỮ LIỆU CŨ ĐANG NẰM TRONG KHO PRODUCTION xử lý thế nào:
 *   Dòng cũ chỉ có `polygon` = mảnh thừa rời + `width_mm/length_mm` = khung bao
 *   của chính mảnh đó, KHÔNG biết khổ tấm gốc. Ta KHÔNG bịa ra 2000×6000 cho nó
 *   (bịa là sai vị trí, ra xưởng đặt bản vẽ nhầm chỗ). Thay vào đó:
 *     • sheetWidthMm/sheetLengthMm := đúng khung bao cũ của mảnh;
 *     • cuts := polygon[1..] (các lỗ nếu dòng cũ có ghi);
 *     • đánh dấu `legacy: true` để panel hiện "tấm kiểu cũ — không rõ khổ gốc".
 *   Tấm cũ vẫn xem được, vẫn xếp được; chỉ là không có phần "đã cắt đi" của tấm
 *   nguyên khổ. Muốn chuẩn thì thợ lưu lại tấm đó theo kiểu mới.
 */
import type { Ring } from '../types';
import type { Remnant, RemnantInput } from './types';

/** Khổ tấm tôn tiêu chuẩn của xưởng. */
export const STOCK_W = 2000;
export const STOCK_H = 6000;

/** Hình chữ nhật đủ 4 đỉnh, ngược chiều kim đồng hồ, gốc ở (0,0). */
export function stockRing(w: number, h: number): Ring {
  return [{ x: 0, y: 0 }, { x: w, y: 0 }, { x: w, y: h }, { x: 0, y: h }];
}

/** Hình chữ nhật bất kỳ (dùng cho một lỗ đã cắt hình hộp). */
export function cutRectRing(x: number, y: number, w: number, h: number): Ring {
  return [{ x, y }, { x: x + w, y }, { x: x + w, y: y + h }, { x, y: y + h }];
}

function num(v: unknown, fallback: number): number {
  return typeof v === 'number' && Number.isFinite(v) && v > 0 ? v : fallback;
}

function cleanRings(v: unknown): Ring[] {
  if (!Array.isArray(v)) return [];
  const out: Ring[] = [];
  for (const ring of v) {
    if (!Array.isArray(ring) || ring.length < 3) continue;
    const pts = ring
      .filter((p): p is { x: number; y: number } =>
        !!p && typeof p === 'object'
        && Number.isFinite((p as { x: unknown }).x) && Number.isFinite((p as { y: unknown }).y))
      .map((p) => ({ x: p.x, y: p.y }));
    if (pts.length >= 3) out.push(pts);
  }
  return out;
}

/** Hình chữ nhật này có đúng là nguyên khổ w×h không (sai số ≤ 0.01mm)? */
export function isFullSheetRing(ring: Ring | undefined, w: number, h: number): boolean {
  if (!ring || ring.length !== 4) return false;
  const xs = ring.map((p) => p.x);
  const ys = ring.map((p) => p.y);
  const eps = 0.01;
  const near = (a: number, b: number) => Math.abs(a - b) <= eps;
  return near(Math.min(...xs), 0) && near(Math.max(...xs), w)
    && near(Math.min(...ys), 0) && near(Math.max(...ys), h)
    && ring.every((p) => (near(p.x, 0) || near(p.x, w)) && (near(p.y, 0) || near(p.y, h)));
}

/**
 * Đưa một bản ghi tấm thừa bất kỳ (mới, cũ, từ cache) về dạng chuẩn.
 * KHÔNG BAO GIỜ ném lỗi — dữ liệu hỏng thì trả tấm nguyên khổ mặc định.
 */
export function normalizeRemnant(raw: unknown): Remnant {
  const r = (raw || {}) as Partial<Remnant> & Record<string, unknown>;

  const polygonIn = cleanRings(r.polygon);
  const cutsIn = cleanRings(r.cuts);

  // Máy chủ đã kết luận "tấm kiểu cũ" (cột sheet_w_mm còn NULL) thì tin nó —
  // rowToRemnant có điền sheetWidthMm cho tiện dùng, nhưng đó chỉ là khung bao
  // của chính mảnh thừa, KHÔNG phải khổ tấm gốc.
  const flaggedLegacy = r.legacy === true;

  // Có khổ tấm gốc → tấm KIỂU MỚI.
  const hasStock = !flaggedLegacy
    && Number.isFinite(r.sheetWidthMm) && Number.isFinite(r.sheetLengthMm)
    && (r.sheetWidthMm as number) > 0 && (r.sheetLengthMm as number) > 0;

  let sheetW: number;
  let sheetH: number;
  let cuts: Ring[];
  let legacy = false;

  if (hasStock) {
    sheetW = r.sheetWidthMm as number;
    sheetH = r.sheetLengthMm as number;
    cuts = cutsIn.length ? cutsIn : polygonIn.slice(1);
  } else if (!flaggedLegacy && polygonIn.length
    && isFullSheetRing(polygonIn[0], num(r.widthMm, STOCK_W), num(r.lengthMm, STOCK_H))) {
    // Dòng cũ nhưng biên ngoài đã là hình chữ nhật nguyên khổ → coi như kiểu mới.
    sheetW = num(r.widthMm, STOCK_W);
    sheetH = num(r.lengthMm, STOCK_H);
    cuts = cutsIn.length ? cutsIn : polygonIn.slice(1);
  } else {
    // Dòng CŨ thật: mảnh thừa rời. Giữ nguyên khung bao của chính mảnh đó.
    sheetW = num(r.widthMm, STOCK_W);
    sheetH = num(r.lengthMm, STOCK_H);
    cuts = cutsIn.length ? cutsIn : polygonIn.slice(1);
    legacy = flaggedLegacy || polygonIn.length > 0;
  }

  const polygon = legacy
    ? polygonIn
    : [stockRing(sheetW, sheetH), ...cuts];

  return {
    id: typeof r.id === 'string' ? r.id : '',
    name: typeof r.name === 'string' && r.name.trim() ? r.name : 'tấm thừa chưa đặt tên',
    // Khung bao LUÔN bằng khổ tấm gốc với tấm kiểu mới — không co lại theo phần còn thừa.
    widthMm: legacy ? num(r.widthMm, sheetW) : sheetW,
    lengthMm: legacy ? num(r.lengthMm, sheetH) : sheetH,
    sheetWidthMm: sheetW,
    sheetLengthMm: sheetH,
    cuts,
    polygon: polygon.length ? polygon : [stockRing(sheetW, sheetH)],
    note: typeof r.note === 'string' ? r.note : '',
    status: r.status === 'used' ? 'used' : 'available',
    createdAt: Number.isFinite(r.createdAt) ? (r.createdAt as number) : 0,
    updatedAt: Number.isFinite(r.updatedAt) ? (r.updatedAt as number) : 0,
    ...(legacy ? { legacy: true } : {}),
    ...(r.pending !== undefined ? { pending: Boolean(r.pending) } : {}),
  };
}

export function normalizeMany(list: unknown): Remnant[] {
  return Array.isArray(list) ? list.map(normalizeRemnant) : [];
}

/**
 * Dựng dữ liệu gửi lên máy chủ cho một tấm thừa KIỂU MỚI.
 * `polygon` vẫn được tính sẵn để máy chủ cũ / bản chép cũ vẫn đọc được.
 */
export function buildRemnantInput(args: {
  name: string;
  sheetWidthMm?: number;
  sheetLengthMm?: number;
  cuts?: Ring[];
  note?: string;
}): RemnantInput {
  const w = num(args.sheetWidthMm, STOCK_W);
  const h = num(args.sheetLengthMm, STOCK_H);
  const cuts = cleanRings(args.cuts);
  return {
    name: args.name.trim(),
    widthMm: w,
    lengthMm: h,
    sheetWidthMm: w,
    sheetLengthMm: h,
    cuts,
    polygon: [stockRing(w, h), ...cuts],
    note: (args.note || '').trim(),
  };
}
