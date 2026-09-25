/**
 * VIỆC 1 — NHẮC BẤM "ĐÃ DÙNG" sau khi tải file của một tấm TÔN THỪA.
 *
 * ── Lỗi thật founder gặp ────────────────────────────────────────────────
 * Chọn tấm thừa trong kho → xếp → tải DXF về → kho VẪN ghi tấm đó còn dùng
 * được → lần xếp sau lại chọn đúng tấm ấy → suýt đem đi cắt trùng lên chỗ đã
 * cắt. `markUsed()` có sẵn trong store nhưng KHÔNG luồng nào gọi; nó chỉ chạy
 * khi bấm tay nút "Đã dùng", mà founder không biết là phải bấm.
 *
 * ── Founder đã chốt ─────────────────────────────────────────────────────
 * KHÔNG tự đánh dấu hộ (bấm XẾP hay tải file đều không được tự đổi trạng thái).
 * Nhưng PHẢI nhắc rõ là cần bấm, và nút bấm để ngay tại lời nhắc.
 *
 * ── Bắt được lúc nào thợ tải file mà KHÔNG sửa file của thợ UI ───────────
 * src/main.ts tải file bằng cách dựng thẻ `<a download="tên-file">` rồi gọi
 * `a.click()`. Sự kiện click đó NỔI BỌT lên `document`, nên module này chỉ cần
 * nghe ở `document` là biết vừa có file rơi xuống máy, kèm đúng TÊN FILE.
 *
 * Tên file do src/ui/download.ts đặt, và nói đủ mọi thứ ta cần:
 *      tam-03_2000x6000.dxf        → phương án 1, tấm thứ 3
 *      pa2-tam-01_2000x6000.nc     → phương án 2, tấm thứ 1
 *      tat-ca-tam.dxf              → phương án 1, TẤT CẢ tấm
 *      pa3-xep-phoi-gcode.zip      → phương án 3, TẤT CẢ tấm
 * Đối chiếu với các phương án mà chính module kho vừa xếp ra (index.ts nhớ lại)
 * là ra đúng những tấm thừa nào vừa được tải bản vẽ.
 */
import type { PlannedSheet, RemnantNestResult } from './plan';

/** Một lượt tải file đã được đọc vị. */
export interface DownloadTarget {
  /** Phương án thứ mấy, đếm từ 0. */
  planIndex: number;
  /** Tấm thứ mấy trong phương án (đếm từ 0), hoặc 'all' khi tải cả gói. */
  sheet: number | 'all';
}

/** Tấm thừa cần nhắc bấm "Đã dùng". */
export interface UsedReminder {
  id: string;
  name: string;
}

/**
 * Đọc tên file xuất ra thành "phương án nào, tấm nào".
 * Tên lạ (không phải file của tool) → null, tuyệt đối không nhắc bừa.
 */
export function parseDownloadName(fileName: unknown): DownloadTarget | null {
  if (typeof fileName !== 'string') return null;
  const name = fileName.trim();
  if (!name) return null;

  // Tiền tố phương án: "pa2-" = phương án 2. Không có = phương án 1.
  let rest = name;
  let planIndex = 0;
  const pa = /^pa(\d+)-/i.exec(rest);
  if (pa) {
    const n = Number(pa[1]);
    if (!Number.isFinite(n) || n < 1) return null;
    planIndex = n - 1;
    rest = rest.slice(pa[0].length);
  }

  // Một tấm: "tam-03_2000x6000.dxf".
  const one = /^tam-(\d+)_/i.exec(rest);
  if (one) {
    const n = Number(one[1]);
    if (!Number.isFinite(n) || n < 1) return null;
    return { planIndex, sheet: n - 1 };
  }

  // Cả phương án: 1 file DXF nhiều tấm, hoặc gói .zip.
  if (/^tat-ca-tam\./i.test(rest) || /^xep-phoi-(dxf|gcode)\.zip$/i.test(rest)) {
    return { planIndex, sheet: 'all' };
  }
  return null;
}

/** Các tấm của phương án ứng với lượt tải này. */
function sheetsOf(plans: readonly RemnantNestResult[], t: DownloadTarget): PlannedSheet[] {
  const plan = plans[t.planIndex];
  if (!plan) return [];
  if (t.sheet === 'all') return plan.sheets;
  // `sheet.index` là số in trên tên file − 1; tìm theo index cho chắc, lệch thì
  // mới lấy theo vị trí mảng.
  const byIndex = plan.sheets.find((s) => s.index === t.sheet);
  return byIndex ? [byIndex] : (plan.sheets[t.sheet] ? [plan.sheets[t.sheet]] : []);
}

/**
 * Tên file vừa tải → danh sách TẤM THỪA TRONG KHO có bản vẽ trong file đó.
 * Chỉ trả tấm lấy từ kho (`source === 'remnant'`), bỏ tấm mới nguyên khổ;
 * bỏ luôn tấm trùng và tấm không có mã.
 */
export function remindersForDownload(
  plans: readonly RemnantNestResult[],
  fileName: string
): UsedReminder[] {
  const target = parseDownloadName(fileName);
  if (!target) return [];
  const out: UsedReminder[] = [];
  const seen = new Set<string>();
  for (const s of sheetsOf(plans, target)) {
    if (s.source !== 'remnant' || !s.remnantId || seen.has(s.remnantId)) continue;
    seen.add(s.remnantId);
    out.push({ id: s.remnantId, name: s.remnantName || s.remnantId });
  }
  return out;
}

/** Câu nhắc hiện lên panel. Viết cho thợ đọc, không viết cho lập trình viên. */
export function reminderText(list: readonly UsedReminder[]): string {
  if (list.length === 0) return '';
  if (list.length === 1) {
    return `Vừa tải bản vẽ của tấm thừa "${list[0].name}". `
      + 'Cắt xong nhớ bấm "Đã dùng" để lần sau khỏi chọn lại đúng tấm ấy.';
  }
  const names = list.map((r) => `"${r.name}"`).join(', ');
  return `Vừa tải bản vẽ của ${list.length} tấm thừa: ${names}. `
    + 'Cắt xong tấm nào thì bấm "Đã dùng" tấm đó để lần sau khỏi chọn lại.';
}

/**
 * Nghe mọi lượt tải file trong trang.
 *
 * src/main.ts tải bằng `<a download>` + `a.click()`, nên chỉ cần bắt click có
 * thuộc tính `download`. Trả về hàm gỡ để test / destroy() gọi lại cho sạch.
 */
export function watchDownloads(
  onDownload: (fileName: string) => void,
  doc: Document = document
): () => void {
  const handler = (ev: Event) => {
    const path = typeof (ev as Event & { composedPath?: () => EventTarget[] }).composedPath === 'function'
      ? (ev as Event & { composedPath: () => EventTarget[] }).composedPath()
      : [ev.target as EventTarget];
    for (const node of path) {
      const el = node as HTMLElement | null;
      if (!el || typeof (el as HTMLElement).getAttribute !== 'function') continue;
      if (String(el.tagName || '').toLowerCase() !== 'a') continue;
      const name = el.getAttribute('download');
      if (!name) continue;
      try {
        onDownload(name);
      } catch {
        /* lời nhắc hỏng thì thôi, KHÔNG được chặn việc tải file */
      }
      return;
    }
  };
  doc.addEventListener('click', handler, true);
  return () => doc.removeEventListener('click', handler, true);
}

/**
 * VIỆC 2 — đoán xem phần tôn thừa sắp lưu được cắt ra TỪ TẤM THỪA CŨ NÀO.
 *
 * src/ui/app.ts (file của thợ UI, tôi không sửa) gọi `saveFromSheet` mà không
 * nói rõ nguồn gốc, nhưng nó có để lại hai dấu vết đủ chắc:
 *   • ghi chú  : "lưu từ phương án 2, 7 chi tiết đã cắt"  → PHƯƠNG ÁN thứ mấy;
 *   • tên gợi ý: "thừa lo-suon.dxf · tấm 3"               → TẤM thứ mấy.
 * Khớp được cả hai thì lấy đúng tấm đó. Thợ gõ tên khác thì lùi về so khổ tấm
 * và số lỗ; vẫn mập mờ (nhiều tấm giống hệt nhau) thì TRẢ NULL — thà không ghi
 * nguồn gốc còn hơn ghi nhầm, ngoài xưởng lần theo mà sai là hỏng tôn.
 */
export function findSourceRemnant(
  plans: readonly RemnantNestResult[],
  args: { name?: string; sheetWidthMm: number; sheetLengthMm: number; cuts: readonly unknown[] }
): UsedReminder | null {
  const fits = (s: PlannedSheet) =>
    s.source === 'remnant' && !!s.remnantId
    && Math.abs(s.width - args.sheetWidthMm) <= 0.5
    && Math.abs(s.height - args.sheetLengthMm) <= 0.5;
  const pick = (s: PlannedSheet): UsedReminder => ({
    id: s.remnantId as string,
    name: s.remnantName || (s.remnantId as string),
  });

  // 1. Đường chắc chắn: đọc thẳng số phương án + số tấm từ chữ app.ts để lại.
  const planNo = /phương án\s*(\d+)/i.exec(String((args as { note?: string }).note || ''));
  const sheetNo = /tấm\s*(\d+)\s*$/i.exec((args.name || '').trim());
  if (sheetNo) {
    const si = Number(sheetNo[1]) - 1;
    const pi = planNo ? Number(planNo[1]) - 1 : 0;
    const plan = plans[pi] || plans[0];
    const sheet = plan?.sheets.find((x) => x.index === si);
    if (sheet && fits(sheet)) return pick(sheet);
  }

  // 2. Đường lùi: so khổ tấm + số lỗ sẽ có sau khi cắt. Chỉ nhận khi DUY NHẤT.
  const hits: PlannedSheet[] = [];
  for (const plan of plans) {
    for (const s of plan.sheets) {
      if (!fits(s)) continue;
      const expect = s.placements.length + (s.cuts ? s.cuts.length : 0);
      if (expect === args.cuts.length) hits.push(s);
    }
  }
  const ids = new Set(hits.map((s) => s.remnantId));
  return ids.size === 1 ? pick(hits[0]) : null;
}
