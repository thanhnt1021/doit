/**
 * Tên hiển thị của chi tiết — VIỆC 4.
 *
 * Founder chốt: *"vẫn có P1 P2 nhưng kèm thêm tên nếu tao biết"*. Nên mã gốc
 * P0…P14 KHÔNG BAO GIỜ mất, tên chỉ được ghép thêm sau dấu chấm giữa:
 *
 *     P3 · mạn 15
 *
 * Thứ tự ưu tiên lấy tên ghép thêm:
 *   1. tên founder tự gõ trong ô bên trái (nhớ theo tên file, localStorage)
 *   2. tên đọc được từ chữ trong file DXF  → Part.dxfLabel (thợ lõi làm)
 *   3. không có gì → chỉ hiện mã P, KHÔNG có dấu chấm thừa
 *
 * `dxfLabel` do thợ lõi trả về: src/core/part.ts nới kiểu `Part` (declaration
 * merging) nên mọi nơi import `Part` đều thấy trường này. Ở đây vẫn đọc qua
 * `PartWithDxfLabel` cho chắc — file src/core không phải của tôi, nếu mai kia
 * họ đổi chỗ khai báo thì hàm này vẫn chạy, không cần sửa.
 */
import type { Part } from '../types';

/** Dấu ngăn giữa mã P và tên. Dùng chung cho màn hình, DXF và G-code. */
export const NAME_SEP = ' · ';

/** Part kèm tên đọc được từ chữ trong DXF (thợ lõi src/core/dxf-parse trả về). */
export type PartWithDxfLabel = Part & { dxfLabel?: string };

/** Tên đọc từ DXF của một chi tiết. Chưa có hoặc rỗng thì trả ''. */
export function dxfLabelOf(part: Part): string {
  const v = (part as PartWithDxfLabel).dxfLabel;
  return typeof v === 'string' ? v.trim() : '';
}

/**
 * Phần tên ghép thêm sau mã P (có thể rỗng).
 * `userNames` là bảng tên founder tự gõ, tra theo Part.id.
 */
export function extraName(part: Part, userNames?: Record<string, string>): string {
  const typed = (userNames?.[part.id] ?? '').trim();
  const chosen = typed || dxfLabelOf(part);
  // Gõ đúng bằng mã P thì coi như không có tên — khỏi ra "P3 · P3".
  return chosen && chosen !== part.id ? chosen : '';
}

/**
 * Tên đầy đủ để hiện lên màn hình / ghi vào file: "P3 · mạn 15" hoặc "P3".
 * Có dấu tiếng Việt; chỗ nào cần ASCII (DXF R12, G-code) thì bên đó tự bỏ dấu
 * bằng toAsciiLabel() như cũ.
 */
export function fullName(part: Part, userNames?: Record<string, string>): string {
  const extra = extraName(part, userNames);
  return extra ? part.id + NAME_SEP + extra : part.id;
}

/**
 * Bảng nhãn đưa cho bộ xuất file (`ExportExtras.labels` của src/core/dxf-export).
 * Bộ xuất tra `labels[part.id]`, không có thì tự dùng `part.id` — nên ở đây chỉ
 * cần ghi những chi tiết THẬT SỰ có tên ghép thêm.
 */
export function exportLabels(parts: Part[], userNames?: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const p of parts) {
    const extra = extraName(p, userNames);
    if (extra) out[p.id] = p.id + NAME_SEP + extra;
  }
  return out;
}
