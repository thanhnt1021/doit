/**
 * VIỆC 1 — sinh TỐI ĐA 5 PHƯƠNG ÁN xếp để founder lật qua lại mà so bằng mắt.
 *
 * ── HỢP ĐỒNG VỚI THỢ LÕI (đã chốt, đã nối xong) ───────────────────────────
 *   export function nestMulti(args: {
 *     parts: Part[];
 *     params: NestParams & { sheets?: NestSheetSpec[] };
 *     onProgress?: (p: number, best: NestPlan) => void;
 *     shouldStop?: () => boolean;
 *   }): NestOutcome            // { best, alternatives }  · alternatives[0] === best
 *
 * Trước đây file này có một LỚP BỌC TẠM (chạy `nest()` nhiều lượt với hạt giống
 * khác nhau) phòng khi thợ lõi chưa đẩy `nestMulti` lên. Thợ lõi đã xong nên
 * lớp bọc đó ĐÃ GỠ HẲN: ở đây gọi thẳng `nestMulti`, không còn dò xét gì nữa.
 *
 * Tấm tôn thừa đi vào qua `opts.sheets` dạng `NestSheetSpec` — NGUYÊN KHỔ
 * 2000×6000 kèm `blocked` là các lỗ đã cắt lần trước (xem src/remnant/sheetspec.ts).
 */
import { nestMulti } from '../nest';
import type { NestPlan, NestSheetSpec } from '../nest';
import type { NestParams, NestProgress, NestResult, Part, Placement, SheetLayout } from '../types';
import { DEFAULT_NEST_PARAMS } from '../types';

/** Tối đa 5 phương án — đúng như founder yêu cầu. */
export const MAX_PLANS = 5;

/** Một tấm đưa cho engine: khổ tấm + các vùng CẤM (lỗ đã cắt của tấm thừa). */
export type { NestSheetSpec };

export interface MultiNestOptions {
  /** Số phương án mong muốn, tự kẹp trong 1..5. Mặc định 5. */
  count?: number;
  /** Các tấm có sẵn (tôn thừa) xếp trước tấm mới, nguyên khổ + vùng cấm. */
  sheets?: NestSheetSpec[];
  onProgress?: (p: NestProgress) => void;
  shouldStop?: () => boolean;
  now?: () => number;
}

export interface MultiNestOutcome {
  /** plans[0] LUÔN là phương án tốt nhất. Dài tối đa 5. */
  plans: NestResult[];
  elapsedMs: number;
}

/**
 * Đổi một `NestPlan` của thợ lõi về `NestResult` mà giao diện đang vẽ.
 * Viết phòng thủ: thiếu trường nào thì tự suy ra, không ném lỗi. Các trường
 * phụ engine gắn thêm (`specIndex`, `label`, `blocked`) được giữ nguyên để
 * src/remnant biết tấm nào là tôn thừa nào và src/ui/render.ts vẽ được lỗ.
 */
export function planToResult(plan: unknown, params: NestParams, elapsedMs = 0): NestResult {
  const p = (plan || {}) as {
    sheets?: unknown[];
    unplaced?: unknown[];
    utilization?: number;
    sheetUtil?: number[];
  };
  const rawSheets = Array.isArray(p.sheets) ? p.sheets : [];
  const sheets: SheetLayout[] = rawSheets.map((s, i) => {
    const o = (s || {}) as Partial<SheetLayout> & { usedArea?: number };
    const width = Number.isFinite(o.width) ? (o.width as number) : params.sheetW;
    const height = Number.isFinite(o.height) ? (o.height as number) : params.sheetH;
    const placements = Array.isArray(o.placements) ? (o.placements as Placement[]) : [];
    const usedArea = Number.isFinite(o.usedArea) ? (o.usedArea as number) : 0;
    const util = Number.isFinite(o.utilization)
      ? (o.utilization as number)
      : (Array.isArray(p.sheetUtil) && Number.isFinite(p.sheetUtil[i])
        ? p.sheetUtil[i]
        : (width * height > 0 ? usedArea / (width * height) : 0));
    return {
      ...(o as object),
      index: Number.isFinite(o.index) ? (o.index as number) : i,
      width, height, placements, usedArea, utilization: util,
    } as SheetLayout;
  });
  const unplaced = (Array.isArray(p.unplaced) ? p.unplaced : []).map((u) => {
    if (typeof u === 'string') return u;
    const part = u as Partial<Part>;
    return typeof part?.id === 'string' ? part.id : String(u);
  });
  let utilization = Number.isFinite(p.utilization) ? (p.utilization as number) : 0;
  if (!utilization) {
    let used = 0;
    let avail = 0;
    for (const s of sheets) {
      used += s.usedArea;
      avail += s.width * s.height;
    }
    utilization = avail > 0 ? used / avail : 0;
  }
  return { sheets, unplaced, utilization, elapsedMs, iterations: 0, params };
}

/** Chữ ký của một phương án — để loại các phương án trùng hệt nhau. */
export function planSignature(r: NestResult): string {
  return r.sheets
    .map((s) => s.placements
      .map((pl) => `${pl.partId}:${Math.round(pl.x)}:${Math.round(pl.y)}:${Math.round(pl.rotationDeg)}:${pl.mirrored ? 1 : 0}`)
      .sort()
      .join('|'))
    .join('#');
}

/**
 * Xếp hạng: ÍT TẤM trước, rồi ít chi tiết chưa xếp được, rồi % dùng tôn cao hơn.
 * Founder so bằng mắt theo đúng thứ tự này.
 */
export function comparePlans(a: NestResult, b: NestResult): number {
  if (a.sheets.length !== b.sheets.length) return a.sheets.length - b.sheets.length;
  if (a.unplaced.length !== b.unplaced.length) return a.unplaced.length - b.unplaced.length;
  return b.utilization - a.utilization;
}

/** Bỏ phương án trùng, xếp hạng, cắt còn tối đa `count` cái. */
export function rankPlans(plans: NestResult[], count = MAX_PLANS): NestResult[] {
  const seen = new Set<string>();
  const out: NestResult[] = [];
  for (const p of plans) {
    if (!p || p.sheets.length === 0) continue;
    const sig = planSignature(p);
    if (seen.has(sig)) continue;
    seen.add(sig);
    out.push(p);
  }
  out.sort(comparePlans);
  return out.slice(0, Math.max(1, Math.min(MAX_PLANS, count)));
}

/** Chạy một lượt sinh nhiều phương án. Gọi THẲNG `nestMulti` của engine. */
export function runMultiNest(
  parts: Part[],
  paramsIn: Partial<NestParams>,
  opts: MultiNestOptions = {}
): MultiNestOutcome {
  const params: NestParams = { ...DEFAULT_NEST_PARAMS, ...paramsIn };
  const now = opts.now ?? (() => Date.now());
  const t0 = now();
  const count = Math.max(1, Math.min(MAX_PLANS, opts.count ?? MAX_PLANS));

  const outcome = nestMulti({
    parts,
    params: opts.sheets && opts.sheets.length ? { ...params, sheets: opts.sheets } : params,
    shouldStop: opts.shouldStop,
    onProgress: opts.onProgress
      ? (frac: number, best: NestPlan) => {
        opts.onProgress?.({
          fraction: Math.max(0, Math.min(1, frac)),
          elapsedMs: now() - t0,
          iterations: 0,
          best: best ? planToResult(best, params, now() - t0) : null,
          label: 'Đang tìm các phương án…',
        });
      }
      : undefined,
  });

  const list = outcome.alternatives?.length ? outcome.alternatives : [outcome.best];
  const plans = rankPlans(
    list.filter(Boolean).map((pl) => planToResult(pl, params, now() - t0)),
    count
  );
  return { plans, elapsedMs: now() - t0 };
}
