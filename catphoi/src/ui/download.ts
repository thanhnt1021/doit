/**
 * Tải file theo ĐÚNG PHƯƠNG ÁN ĐANG XEM (VIỆC 1 — chỗ dễ sai nhất).
 *
 * Trước đây màn hình chỉ giữ một kết quả nên nút tải lấy đại cái đó. Nay có tới
 * 5 phương án, founder lật tới phương án 2 rồi bấm tải thì file PHẢI là phương
 * án 2, không phải phương án tốt nhất. Mọi nút tải đều phải đi qua các hàm dưới
 * đây — chúng nhận NGUYÊN danh sách phương án + chỉ số đang xem, tự chọn đúng
 * cái. Có bài kiểm tra so TOẠ ĐỘ thật trong tests/export.test.ts.
 */
import type { GcodeOptions, NestResult, Part, SheetLayout } from '../types';
import { exportAllSheetsDxfR12, exportSheetDxfR12, sheetFileName, type ExportExtras } from '../core/dxf-export';
import { generateGcode } from '../core/gcode';

/** Lấy phương án đang xem; chỉ số hỏng thì tự kẹp về khoảng hợp lệ. */
export function pickPlan(plans: NestResult[], planIndex: number): NestResult | null {
  if (!plans || plans.length === 0) return null;
  const i = Math.max(0, Math.min(plans.length - 1, Math.floor(planIndex) || 0));
  return plans[i];
}

/**
 * Tên file có gắn số phương án để không đè lên nhau trong thư mục Tải về.
 * Phương án 1 (tốt nhất) giữ nguyên tên cũ `tam-01_2000x6000.dxf` cho quen tay;
 * từ phương án 2 trở đi thêm tiền tố `pa2-`.
 */
export function planFileName(planIndex: number, sheet: SheetLayout, ext: string): string {
  const base = sheetFileName(sheet, ext);
  return planIndex > 0 ? `pa${planIndex + 1}-${base}` : base;
}

/** Tên file "1 file nhiều tấm". */
export function planAllFileName(planIndex: number): string {
  return planIndex > 0 ? `pa${planIndex + 1}-tat-ca-tam.dxf` : 'tat-ca-tam.dxf';
}

/** Tên file .zip. */
export function planZipName(planIndex: number, kind: 'dxf' | 'gcode'): string {
  const base = kind === 'dxf' ? 'xep-phoi-dxf.zip' : 'xep-phoi-gcode.zip';
  return planIndex > 0 ? `pa${planIndex + 1}-${base}` : base;
}

/** DXF của MỘT tấm trong phương án đang xem. */
export function planSheetDxf(
  plans: NestResult[], planIndex: number, sheetIndex: number,
  partsById: Map<string, Part>, extras: ExportExtras = {}
): string {
  const plan = pickPlan(plans, planIndex);
  const sheet = plan?.sheets[sheetIndex];
  if (!sheet) throw new Error('Không tìm thấy tấm này trong phương án đang xem.');
  return exportSheetDxfR12(sheet, partsById, extras);
}

/** G-code của MỘT tấm trong phương án đang xem. */
export function planSheetGcode(
  plans: NestResult[], planIndex: number, sheetIndex: number,
  partsById: Map<string, Part>, opts: GcodeOptions, extras: ExportExtras = {}
): string {
  const plan = pickPlan(plans, planIndex);
  const sheet = plan?.sheets[sheetIndex];
  if (!sheet) throw new Error('Không tìm thấy tấm này trong phương án đang xem.');
  return generateGcode(sheet, partsById, opts, extras);
}

/** 1 file DXF chứa mọi tấm của phương án đang xem. */
export function planAllDxf(
  plans: NestResult[], planIndex: number,
  partsById: Map<string, Part>, extras: ExportExtras = {}
): string {
  const plan = pickPlan(plans, planIndex);
  if (!plan) throw new Error('Chưa có phương án nào để tải.');
  return exportAllSheetsDxfR12(plan.sheets, partsById, extras);
}

export interface ZipEntry {
  name: string;
  content: string;
}

/** Danh sách file cho gói .zip của phương án đang xem. */
export function planZipFiles(
  plans: NestResult[], planIndex: number, partsById: Map<string, Part>,
  kind: 'dxf' | 'gcode', gcode: GcodeOptions, extras: ExportExtras = {}
): ZipEntry[] {
  const plan = pickPlan(plans, planIndex);
  if (!plan) return [];
  return plan.sheets.map((s, i) => (
    kind === 'dxf'
      ? { name: planFileName(planIndex, s, 'dxf'), content: planSheetDxf(plans, planIndex, i, partsById, extras) }
      : {
        name: planFileName(planIndex, s, gcode.extension),
        content: planSheetGcode(plans, planIndex, i, partsById, gcode, extras),
      }
  ));
}
