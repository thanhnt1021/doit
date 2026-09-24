/**
 * Xếp phôi CÓ DÙNG TÔN THỪA.
 *
 * Ý đồ của founder: lô nào cũng phải nhét vào tôn thừa đang cất trong kho TRƯỚC,
 * hết chỗ mới được mở tấm mới nguyên khổ 2×6m.
 *
 * ── ĐÃ BỎ ĐƯỜNG VÒNG CŨ (VIỆC 3) ────────────────────────────────────────────
 * Bản trước phải đi vòng: mỗi tấm thừa lấy HÌNH CHỮ NHẬT LỚN NHẤT nội tiếp rồi
 * gọi `nest()` riêng cho ô chữ nhật đó — mất khoảng 30% diện tích ở các góc lồi
 * lõm, vì engine chưa nhận được vùng cấm.
 *
 * Nay engine có hợp đồng:
 *     NestSheetSpec { w, h, blocked?: Ring[], label? }
 * nên mỗi tấm thừa đi thẳng vào engine dưới dạng TẤM NGUYÊN KHỔ 2000×6000 kèm
 * `blocked` = đúng các lỗ đã cắt lần trước, giữ nguyên vị trí. Engine tự xếp
 * lần lượt các tấm khai rồi mới mở tấm mới. Đường hình chữ nhật nội tiếp đã
 * XOÁ HẲN khỏi luồng xếp.
 */
import type { NestParams, NestProgress, Part, Ring, SheetLayout } from '../types';
import { DEFAULT_NEST_PARAMS } from '../types';
import type { NestResult } from '../types';
import type { Remnant } from './types';
import { polygonArea } from './geometry';
import { sheetSpecOf } from './sheetspec';
import { MAX_PLANS, runMultiNest } from '../ui/nest-multi-core';

/** Một tấm trong phương án, có thêm thông tin "tấm này là tôn thừa nào". */
export interface PlannedSheet extends SheetLayout {
  source: 'remnant' | 'new';
  remnantId?: string;
  remnantName?: string;
  /** Hình thật của tấm thừa, để UI vẽ đúng phần tôn còn lại. */
  polygon?: Ring[];
  /** Các lỗ ĐÃ CẮT sẵn trên tấm thừa (VIỆC 3) — UI tô xám cho dễ nhìn. */
  cuts?: Ring[];
}

export interface RemnantUsage {
  id: string;
  name: string;
  /** Số chi tiết nhét được vào tấm thừa này. */
  placed: number;
  /** Diện tích chi tiết / diện tích tôn thừa còn thật, 0..1. */
  utilization: number;
}

export interface RemnantNestResult extends Omit<NestResult, 'sheets'> {
  sheets: PlannedSheet[];
  remnantsUsed: RemnantUsage[];
  /** Số tấm mới nguyên khổ phải mở thêm. */
  newSheets: number;
  /** Tấm thừa bị bỏ qua vì quá nhỏ so với lề, kèm lý do. */
  skipped: { id: string; name: string; reason: string }[];
}

export interface PlanDeps {
  now?: () => number;
  onProgress?: (p: NestProgress) => void;
  shouldStop?: () => boolean;
}

/** Kết quả một lượt xếp có tôn thừa, kèm tối đa 5 phương án để founder lật. */
export interface RemnantMultiOutcome {
  /** plans[0] là phương án tốt nhất. */
  plans: RemnantNestResult[];
}

/**
 * Tấm thừa nhỏ hơn lề hai bên thì engine không đặt nổi gì vào — loại sớm cho
 * khỏi tốn ngân sách thời gian, và nói rõ lý do để thợ biết mà dọn kho.
 */
function splitUsable(
  remnants: Remnant[], params: NestParams
): { usable: Remnant[]; skipped: RemnantNestResult['skipped'] } {
  const minSide = 2 * params.margin + Math.max(params.gap, 10);
  const usable: Remnant[] = [];
  const skipped: RemnantNestResult['skipped'] = [];
  for (const r of remnants) {
    if (r.sheetWidthMm < minSide || r.sheetLengthMm < minSide) {
      skipped.push({
        id: r.id,
        name: r.name,
        reason: `Khổ tấm chỉ ${Math.round(r.sheetWidthMm)}×${Math.round(r.sheetLengthMm)}mm, nhỏ hơn lề ${params.margin}mm hai bên.`,
      });
      continue;
    }
    if (polygonArea(r.polygon) <= 0) {
      skipped.push({ id: r.id, name: r.name, reason: 'Tấm thừa đã bị cắt hết, không còn tôn.' });
      continue;
    }
    usable.push(r);
  }
  return { usable, skipped };
}

/**
 * Gắn lại thông tin "tấm này là tôn thừa nào" vào kết quả engine trả về.
 *
 * Engine nhận `params.sheets` theo đúng thứ tự ta gửi và trả về `specIndex` =
 * tấm khai thứ mấy (−1 = tấm mới nguyên khổ). Vẫn viết phòng thủ: chỉ nhận khi
 * khổ tấm khớp, lệch thì coi như tấm mới (thà mất nhãn còn hơn gán nhầm tấm,
 * ra xưởng lấy nhầm tôn).
 */
function tagRemnantSheets(plan: NestResult, remnants: Remnant[]): PlannedSheet[] {
  return plan.sheets.map((s, i) => {
    const echoed = (s as SheetLayout & { label?: string; specIndex?: number });
    const hasSpec = Number.isFinite(echoed.specIndex);
    if (hasSpec && (echoed.specIndex as number) < 0) {
      return { ...s, index: i, source: 'new' as const };
    }
    const byLabel = echoed.label ? remnants.findIndex((r) => r.name === echoed.label) : -1;
    const k = hasSpec ? (echoed.specIndex as number) : (byLabel >= 0 ? byLabel : i);
    const r = k >= 0 && k < remnants.length ? remnants[k] : undefined;
    const fits = r
      && Math.abs(s.width - r.sheetWidthMm) <= 0.5
      && Math.abs(s.height - r.sheetLengthMm) <= 0.5;
    if (!r || !fits) return { ...s, index: i, source: 'new' as const };
    return {
      ...s,
      index: i,
      source: 'remnant' as const,
      remnantId: r.id,
      remnantName: r.name,
      polygon: r.polygon,
      cuts: r.cuts,
    };
  });
}

function toRemnantResult(
  plan: NestResult, remnants: Remnant[], skipped: RemnantNestResult['skipped']
): RemnantNestResult {
  const sheets = tagRemnantSheets(plan, remnants);
  const used = new Map<string, RemnantUsage>();
  let totalUsed = 0;
  let totalAvail = 0;
  for (const s of sheets) {
    // Tấm thừa chỉ còn phần tôn ngoài các lỗ — tính % trên diện tích THẬT còn lại,
    // nếu không thì tấm thừa nào cũng bị chê là "dùng tôn thấp".
    const real = s.source === 'remnant' && s.polygon ? polygonArea(s.polygon) : s.width * s.height;
    totalUsed += s.usedArea;
    totalAvail += real;
    if (s.source === 'remnant' && s.remnantId) {
      used.set(s.remnantId, {
        id: s.remnantId,
        name: s.remnantName || s.remnantId,
        placed: s.placements.length,
        utilization: real > 0 ? s.usedArea / real : 0,
      });
    }
  }
  return {
    ...plan,
    sheets,
    remnantsUsed: [...used.values()],
    newSheets: sheets.filter((s) => s.source === 'new').length,
    skipped,
    utilization: totalAvail > 0 ? totalUsed / totalAvail : plan.utilization,
  };
}

/**
 * Xếp có tôn thừa và trả về NHIỀU phương án (tối đa 5) để founder lật Lùi/Tiến.
 * Tấm thừa truyền thẳng vào engine dạng "nguyên khổ + vùng cấm là các lỗ đã cắt".
 */
export function nestMultiWithRemnants(
  parts: Part[],
  paramsIn: Partial<NestParams>,
  remnants: Remnant[],
  deps: PlanDeps & { count?: number } = {}
): RemnantMultiOutcome {
  const params: NestParams = { ...DEFAULT_NEST_PARAMS, ...paramsIn };
  const count = Math.max(1, Math.min(MAX_PLANS, deps.count ?? MAX_PLANS));
  const { usable, skipped } = splitUsable(remnants, params);

  const out = runMultiNest(parts, params, {
    count,
    sheets: usable.map(sheetSpecOf),
    onProgress: deps.onProgress,
    shouldStop: deps.shouldStop,
    now: deps.now,
  });

  return { plans: out.plans.map((p) => toRemnantResult(p, usable, skipped)) };
}

/**
 * Xếp có tôn thừa, chỉ lấy PHƯƠNG ÁN TỐT NHẤT.
 * Giữ tên cũ cho chỗ nào còn gọi kiểu một-kết-quả.
 */
export function nestWithRemnants(
  parts: Part[],
  paramsIn: Partial<NestParams>,
  remnants: Remnant[],
  deps: PlanDeps = {}
): RemnantNestResult {
  return nestMultiWithRemnants(parts, paramsIn, remnants, { ...deps, count: 1 }).plans[0];
}
