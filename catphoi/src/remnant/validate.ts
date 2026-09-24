/**
 * Kiểm tra dữ liệu tấm thừa ở phía TRÌNH DUYỆT — chỉ để báo lỗi ngay cho thợ,
 * khỏi phải đợi một vòng mạng.
 *
 * ⚠ Đây KHÔNG phải hàng rào bảo vệ. Hàng rào thật nằm ở
 * functions/api/remnants/_lib.js và chạy trên máy chủ; kho là dữ liệu chung
 * nhiều người ghi nên máy chủ không bao giờ tin trình duyệt.
 * Hai bộ luật phải giống nhau — sửa bên này thì sửa luôn bên kia.
 */
import type { RemnantInput } from './types';

export const MAX_NAME_LEN = 120;
export const MAX_NOTE_LEN = 500;
export const MAX_DIM_MM = 100_000;
export const MAX_RINGS = 50;
export const MAX_POINTS_TOTAL = 5_000;
export const MIN_RING_POINTS = 3;

/** Trả về câu lỗi tiếng Việt, hoặc null nếu dữ liệu sạch. */
export function validateRemnantInput(input: Partial<RemnantInput>): string | null {
  const name = typeof input.name === 'string' ? input.name.trim() : '';
  if (!name) return 'Phải đặt tên cho tấm thừa, ví dụ "thừa lô sườn 15".';
  if (name.length > MAX_NAME_LEN) return `Tên tấm thừa dài quá ${MAX_NAME_LEN} ký tự.`;

  const dim = (v: unknown, label: string): string | null => {
    if (typeof v !== 'number' || !Number.isFinite(v)) return `${label} phải là một con số.`;
    if (v <= 0) return `${label} phải lớn hơn 0.`;
    if (v > MAX_DIM_MM) return `${label} lớn quá mức cho phép (${MAX_DIM_MM} mm).`;
    return null;
  };
  const eW = dim(input.widthMm, 'Chiều rộng tấm thừa');
  if (eW) return eW;
  const eL = dim(input.lengthMm, 'Chiều dài tấm thừa');
  if (eL) return eL;

  // VIỆC 3: khổ tấm gốc (nếu có gửi) cũng phải là số dương hợp lệ.
  if (input.sheetWidthMm !== undefined) {
    const e = dim(input.sheetWidthMm, 'Khổ tấm gốc (rộng)');
    if (e) return e;
  }
  if (input.sheetLengthMm !== undefined) {
    const e = dim(input.sheetLengthMm, 'Khổ tấm gốc (dài)');
    if (e) return e;
  }

  const poly = input.polygon;
  if (!Array.isArray(poly) || poly.length === 0) return 'Thiếu hình dạng tấm thừa (đa giác).';
  if (poly.length > MAX_RINGS) return `Hình tấm thừa có quá ${MAX_RINGS} vòng.`;
  let total = 0;
  for (const ring of poly) {
    if (!Array.isArray(ring) || ring.length < MIN_RING_POINTS) {
      return `Mỗi vòng của hình tấm thừa cần ít nhất ${MIN_RING_POINTS} đỉnh.`;
    }
    total += ring.length;
    if (total > MAX_POINTS_TOTAL) {
      return `Hình tấm thừa có quá ${MAX_POINTS_TOTAL} đỉnh, hãy đơn giản hoá bớt.`;
    }
    for (const p of ring) {
      if (!p || typeof p.x !== 'number' || typeof p.y !== 'number'
        || !Number.isFinite(p.x) || !Number.isFinite(p.y)) {
        return 'Đỉnh của hình tấm thừa phải có toạ độ x, y là số.';
      }
      if (Math.abs(p.x) > MAX_DIM_MM || Math.abs(p.y) > MAX_DIM_MM) {
        return `Toạ độ đỉnh vượt quá ${MAX_DIM_MM} mm.`;
      }
    }
  }

  // Các lỗ đã cắt: cùng luật với đa giác, vì chúng cũng là vòng kín.
  if (input.cuts !== undefined && input.cuts !== null) {
    if (!Array.isArray(input.cuts)) return 'Danh sách lỗ đã cắt phải là một mảng.';
    if (input.cuts.length > MAX_RINGS) return `Tấm thừa có quá ${MAX_RINGS} lỗ đã cắt.`;
    let cutPts = 0;
    for (const ring of input.cuts) {
      if (!Array.isArray(ring) || ring.length < MIN_RING_POINTS) {
        return `Mỗi lỗ đã cắt cần ít nhất ${MIN_RING_POINTS} đỉnh.`;
      }
      cutPts += ring.length;
      if (cutPts > MAX_POINTS_TOTAL) {
        return `Các lỗ đã cắt có quá ${MAX_POINTS_TOTAL} đỉnh, hãy đơn giản hoá bớt.`;
      }
      for (const p of ring) {
        if (!p || typeof p.x !== 'number' || typeof p.y !== 'number'
          || !Number.isFinite(p.x) || !Number.isFinite(p.y)) {
          return 'Đỉnh của lỗ đã cắt phải có toạ độ x, y là số.';
        }
      }
    }
  }

  if (input.note !== undefined && input.note !== null) {
    if (typeof input.note !== 'string') return 'Ghi chú phải là chuỗi chữ.';
    if (input.note.trim().length > MAX_NOTE_LEN) return `Ghi chú dài quá ${MAX_NOTE_LEN} ký tự.`;
  }
  return null;
}
