/**
 * VIỆC 2 — MÃ TỰ SINH cho tấm tôn thừa mới.
 *
 * Founder nói nguyên văn: *"sao lại lưu đè, phải đặt mã mới chứ. auto đặt tên mã
 * theo batch cắt + số thứ tự + ngày tháng"*.
 *
 * ── Khuôn mã đã chốt ─────────────────────────────────────────────────────
 *
 *      LO-2026-09-25-01
 *      ^^  ^^^^^^^^^^ ^^
 *      |   |          └── SỐ THỨ TỰ trong ngày, 2 chữ số, đếm từ 01
 *      |   └───────────── NGÀY THÁNG cắt, YYYY-MM-DD (giờ máy của thợ)
 *      └───────────────── LÔ CẮT — mọi tấm thừa sinh ra trong ngày đều mang "LO"
 *
 * Đọc lên là ra ngay "lô cắt ngày 25/09/2026, tấm thừa thứ nhất" — ngoài xưởng
 * viết bằng bút dạ lên tấm tôn cũng ngắn, không nhầm được với tên tự đặt.
 *
 * SỐ THỨ TỰ không trùng trong cùng một ngày: trước khi đặt mã, ta đọc lại TOÀN
 * BỘ kho (kể cả tấm đã dùng) và lấy số lớn nhất của ngày hôm đó rồi +1. Mất mạng
 * thì đọc bản chép trong máy — vẫn không đụng số với những tấm máy này đã lưu.
 *
 * Tấm thừa mới LUÔN là MỘT DÒNG MỚI trong kho. Tấm cũ giữ nguyên si, không ghi
 * đè, không sửa — muốn nó biến khỏi danh sách thì bấm "Đã dùng" (VIỆC 1 + 3).
 */
import type { Ring } from '../types';
import type { Remnant, RemnantInput } from './types';
import type { RemnantStore, WriteOutcome } from './store';
import { buildRemnantInput } from './normalize';

/** Phần đầu của mã — "lô cắt". */
export const CODE_PREFIX = 'LO';

/** Bắt đúng khuôn `LO-YYYY-MM-DD-NN` ở ĐẦU tên (phía sau cho phép ghi thêm). */
export const CODE_RE = /^LO-(\d{4})-(\d{2})-(\d{2})-(\d{1,4})\b/;

/**
 * Tên mặc định mà src/ui/app.ts gợi ý trong hộp prompt ("thừa <file> · tấm 3").
 * Thợ bấm OK luôn thì coi như KHÔNG đặt tên riêng → chỉ lấy mã cho gọn.
 * (File đó của thợ UI, tôi không sửa — chỉ nhận dạng.)
 */
export const UI_DEFAULT_NAME_RE = /^thừa\s.*·\s*tấm\s*\d+\s*$/i;

const pad2 = (n: number) => String(n).padStart(2, '0');

/** Phần ngày tháng của mã, theo lịch MÁY CỦA THỢ (xưởng dùng giờ Việt Nam). */
export function codeDatePart(d: Date = new Date()): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

/** Tách một tên bất kỳ ra `{ date, seq }`; tên không theo khuôn thì trả null. */
export function parseRemnantCode(name: unknown): { date: string; seq: number } | null {
  if (typeof name !== 'string') return null;
  const m = CODE_RE.exec(name.trim());
  if (!m) return null;
  return { date: `${m[1]}-${m[2]}-${m[3]}`, seq: Number(m[4]) };
}

/**
 * Mã kế tiếp cho ngày `d`, biết trước các tên đang có trong kho.
 * Không trùng số với bất kỳ tên nào CÙNG NGÀY, kể cả tấm đã dùng.
 */
export function nextRemnantCode(existingNames: readonly unknown[], d: Date = new Date()): string {
  const today = codeDatePart(d);
  let max = 0;
  for (const n of existingNames) {
    const got = parseRemnantCode(n);
    if (got && got.date === today && got.seq > max) max = got.seq;
  }
  return `${CODE_PREFIX}-${today}-${pad2(max + 1)}`;
}

/**
 * Hỏi kho xem hôm nay đã có mã nào rồi, trả mã kế tiếp.
 * Máy chủ chết / mất mạng → dùng bản chép trong máy, KHÔNG ném lỗi: thà mã hơi
 * lệch còn hơn không lưu được tấm thừa.
 */
export async function allocateRemnantCode(
  store: RemnantStore,
  now: () => number = () => Date.now()
): Promise<string> {
  let names: string[] = [];
  try {
    const out = await store.list('all');
    names = out.remnants.map((r) => r.name);
  } catch {
    names = store.cached().map((r) => r.name);
  }
  // Bản chép trong máy có thể còn tấm chưa kịp lên máy chủ — gộp cả hai cho chắc.
  for (const r of store.cached()) names.push(r.name);
  return nextRemnantCode(names, new Date(now()));
}

/** Ghép mã với tên thợ tự gõ. Không gõ gì (hoặc để nguyên gợi ý) thì chỉ lấy mã. */
export function composeLeftoverName(code: string, typed?: string): string {
  const t = (typed || '').trim();
  if (!t || UI_DEFAULT_NAME_RE.test(t)) return code;
  if (parseRemnantCode(t)) return t; // thợ đã tự gõ đúng khuôn mã rồi
  return `${code} · ${t}`;
}

/** Những gì cần biết để lưu phần tôn CÒN LẠI sau một lượt cắt. */
export interface LeftoverArgs {
  /** Tên thợ tự gõ (có thể bỏ trống — lúc đó tên chính là mã tự sinh). */
  name?: string;
  sheetWidthMm: number;
  sheetLengthMm: number;
  cuts: Ring[];
  note?: string;
  /** Tấm thừa CŨ mà lượt cắt này chạy trên đó (nếu có). */
  sourceId?: string;
  sourceName?: string;
}

/** Ghi chú nguồn gốc, để ngoài xưởng lần ra tấm này đẻ từ đâu. */
export function originNote(args: LeftoverArgs): string {
  const own = (args.note || '').trim();
  if (!args.sourceName && !args.sourceId) return own;
  const from = `sinh ra từ tấm thừa "${args.sourceName || args.sourceId}"`;
  return own ? `${from} · ${own}` : from;
}

/** Dựng dữ liệu gửi lên kho cho một tấm thừa mới, mã đã điền sẵn. */
export function buildLeftoverInput(code: string, args: LeftoverArgs): RemnantInput {
  return buildRemnantInput({
    name: composeLeftoverName(code, args.name),
    sheetWidthMm: args.sheetWidthMm,
    sheetLengthMm: args.sheetLengthMm,
    cuts: args.cuts,
    note: originNote(args),
    sourceId: args.sourceId,
    sourceName: args.sourceName,
  });
}

/**
 * Lưu phần tôn còn lại thành MỘT DÒNG MỚI trong kho, mã tự sinh.
 * KHÔNG đụng đến tấm cũ: tấm cũ chỉ đổi trạng thái khi thợ tự bấm "Đã dùng".
 */
export async function saveLeftoverToStore(
  store: RemnantStore,
  args: LeftoverArgs,
  deps: { now?: () => number } = {}
): Promise<WriteOutcome<Remnant>> {
  const code = await allocateRemnantCode(store, deps.now);
  return store.add(buildLeftoverInput(code, args));
}
