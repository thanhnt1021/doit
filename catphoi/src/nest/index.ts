/**
 * CỬA RA CỦA ENGINE XẾP PHÔI.
 *
 * Mọi thứ phần giao diện cần đều nằm ở đây. Bốn kiểu dưới đây là HỢP ĐỒNG
 * đã chốt với thợ giao diện — không đổi tên, không đổi nghĩa.
 */
import type { NestParams, Part, Ring, SheetLayout } from '../types';
import { runNest, type CandidateSnapshot, type NestCallbacks } from './engine';

export { nest, validateLayout, Nester, runNest } from './engine';
export type {
  NestCallbacks, ValidationIssue, EngineSheet, CandidateSnapshot, RunOptions, BlockTemplate,
} from './engine';
export { rasterizeRing, shiftBitmap, transformRing } from './raster';
export type { BaseBitmap, ShiftedBitmap } from './raster';

// ─────────────────────────── HỢP ĐỒNG (không đổi) ───────────────────────────

/**
 * Một tấm tôn được khai để xếp lên.
 *
 * `blocked` = danh sách VÙNG CẤM: những mảng đã bị cắt mất ở lần trước, nay là
 * lỗ hổng trên tấm. Toạ độ của vùng cấm tính THEO TẤM — (0,0) là góc dưới-trái
 * của tấm, cùng hệ toạ độ với Placement.x/y. Tấm thừa vẫn giữ NGUYÊN KHỔ
 * (w × h = 2000 × 6000), không co lại thành hình chữ nhật nhỏ.
 */
export interface NestSheetSpec { w: number; h: number; blocked?: Ring[]; label?: string }

/** Một tấm trong kết quả. Bằng SheetLayout cũ + thông tin tấm thừa. */
export interface NestSheet extends SheetLayout {
  /** Tấm này là tấm khai thứ mấy (−1 = tấm mới nguyên khổ engine tự mở). */
  specIndex?: number;
  /** Nhãn do người dùng đặt cho tấm khai (NestSheetSpec.label). */
  label?: string;
  /** Vùng cấm của tấm, để vẽ lên giao diện. */
  blocked?: Ring[];
}

/** Một PHƯƠNG ÁN xếp hoàn chỉnh. */
export interface NestPlan {
  sheets: NestSheet[];
  /** Chi tiết không xếp được. Một chi tiết cần 3 cái mà thiếu 2 thì xuất hiện 2 lần. */
  unplaced: Part[];
  /** % sử dụng tôn TỔNG trên mọi tấm đã dùng, 0..1. */
  utilization: number;
  /** % sử dụng tôn của TỪNG tấm, cùng thứ tự với `sheets`, 0..1. */
  sheetUtil: number[];
}

/** Kết quả của nestMulti. `alternatives[0] === best`. */
export interface NestOutcome { best: NestPlan; alternatives: NestPlan[] }

// ─────────────────────────── Chọn phương án khác nhau ───────────────────────────

/** Tối đa bao nhiêu phương án trả về cho người dùng lật xem. */
const MAX_PLANS = 5;
/**
 * NGƯỠNG "KHÁC NHAU RÕ RỆT" — tầng 1.
 * Thước đo: coi mỗi phương án là tập các CẶP chi tiết NẰM CHUNG MỘT TẤM.
 * Khoảng cách giữa hai phương án = khoảng cách Jaccard giữa hai tập cặp đó
 * (phần khác nhau / phần hợp lại). Thước này không phụ thuộc thứ tự tấm, nên
 * hai phương án chỉ đổi chỗ tấm 1 với tấm 2 vẫn bị coi là GIỐNG NHAU — đúng ý.
 * 0,15 nghĩa là ít nhất 15% số cặp phải đổi, tức thật sự có chi tiết nhảy tấm.
 */
const PAIR_DIFF = 0.15;
/**
 * NGƯỠNG tầng 2 — chỉ dùng khi tầng 1 không gom đủ 5 phương án.
 * Cùng số tấm, cùng cách chia chi tiết, nhưng TỔNG CHIỀU DÀI TÔN ĐÃ DÙNG lệch
 * nhau ≥ 100mm thì cách sắp trên tấm khác nhau đủ để mắt thường thấy.
 * (Dưới 100mm thì đúng là "bản gần giống nhau xê dịch vài mm" — loại.)
 */
const LEN_DIFF_MM = 100;

/** Tập cặp "nằm chung một tấm", mã hoá thành số i*N+j. */
function samePairs(assign: Int32Array): Set<number> {
  const out = new Set<number>();
  const n = assign.length;
  for (let i = 0; i < n; i++) {
    if (assign[i] < 0) continue;
    for (let j = i + 1; j < n; j++) {
      if (assign[j] === assign[i]) out.add(i * n + j);
    }
  }
  return out;
}

function jaccardDist(a: Set<number>, b: Set<number>): number {
  if (a.size === 0 && b.size === 0) return 0;
  let inter = 0;
  for (const v of a) if (b.has(v)) inter++;
  const uni = a.size + b.size - inter;
  return uni === 0 ? 0 : 1 - inter / uni;
}

interface Scored { snap: CandidateSnapshot; pairs: Set<number>; lenSum: number }

function score(snap: CandidateSnapshot): Scored {
  return {
    snap,
    pairs: samePairs(snap.assign),
    lenSum: snap.topY.reduce((a, b) => a + b, 0),
  };
}

/** Phương án `c` có khác rõ rệt so với MỌI phương án đã chọn không? */
function distinctFrom(c: Scored, chosen: Scored[], tier: 1 | 2): boolean {
  for (const p of chosen) {
    if (c.snap.nSheets !== p.snap.nSheets) continue; // khác số tấm = chắc chắn khác
    if (jaccardDist(c.pairs, p.pairs) >= PAIR_DIFF) continue;
    if (tier === 2 && Math.abs(c.lenSum - p.lenSum) >= LEN_DIFF_MM) continue;
    return false;
  }
  return true;
}

// ─────────────────────────── nestMulti ───────────────────────────

function planOf(snap: CandidateSnapshot, specs: NestSheetSpec[], byId: Map<string, Part>): NestPlan {
  const sheets: NestSheet[] = snap.sheets.map((s) => ({
    ...s,
    label: s.specIndex >= 0 ? specs[s.specIndex]?.label : undefined,
  }));
  const unplaced: Part[] = [];
  for (const key of snap.unplaced) {
    const p = byId.get(key.split('#')[0]);
    if (p) unplaced.push(p);
  }
  return {
    sheets,
    unplaced,
    utilization: snap.totalArea > 0 ? snap.placedArea / snap.totalArea : 0,
    sheetUtil: sheets.map((s) => s.utilization),
  };
}

/**
 * Xếp phôi và trả về NHIỀU phương án để chủ xưởng tự chọn bằng mắt.
 *
 * - `best` = đúng phương án mà `nest()` trả về hôm nay (không đổi gì).
 * - `alternatives` sắp theo thứ tự TỐT DẦN XUỐNG, phần tử [0] chính là `best`.
 * - Tối đa 5 phương án, và chúng KHÁC NHAU RÕ RỆT theo thước đo ở trên
 *   (khác số tấm, hoặc ≥ 15% số cặp chi tiết đổi tấm; bí quá mới xét tới
 *   chênh lệch chiều dài tôn ≥ 100mm).
 * - Tiến độ và nút Dừng chạy y như cũ: `onProgress` được gọi định kỳ kèm
 *   phương án tốt nhất hiện tại, `shouldStop` được hỏi liên tục.
 *
 * Tấm có VÙNG CẤM khai qua `params.sheets` (xem NestSheetSpec).
 */
export function nestMulti(args: {
  parts: Part[];
  params: NestParams & { sheets?: NestSheetSpec[] };
  onProgress?: (p: number, best: NestPlan) => void;
  shouldStop?: () => boolean;
}): NestOutcome {
  const specs = (args.params.sheets ?? []).filter((s) => s && s.w > 0 && s.h > 0);
  const byId = new Map(args.parts.map((p) => [p.id, p]));

  // Kho phương án. Giữ tối đa 600 rồi tỉa còn 300 tốt nhất — đủ đa dạng mà
  // không phình bộ nhớ dù engine chạy hàng nghìn phương án.
  let pool: CandidateSnapshot[] = [];
  const prune = () => {
    if (pool.length <= 600) return;
    pool.sort((a, b) => a.cost - b.cost);
    pool.length = 300;
  };

  const cb: NestCallbacks = {
    shouldStop: args.shouldStop,
    onProgress: args.onProgress
      ? (p) => {
          const b = p.best;
          args.onProgress!(
            p.fraction,
            b
              ? {
                  sheets: b.sheets as NestSheet[],
                  unplaced: b.unplaced
                    .map((k) => byId.get(k.split('#')[0]))
                    .filter((x): x is Part => !!x),
                  utilization: b.utilization,
                  sheetUtil: b.sheets.map((s) => s.utilization),
                }
              : { sheets: [], unplaced: [], utilization: 0, sheetUtil: [] }
          );
        }
      : undefined,
  };

  const run = runNest({ parts: args.parts, params: args.params }, cb, {
    specs,
    onCandidate: (snap) => {
      pool.push(snap);
      prune();
    },
  });

  const best = planOf(run.best, specs, byId);
  const chosen: Scored[] = [score(run.best)];
  const alternatives: NestPlan[] = [best];

  pool.sort((a, b) => a.cost - b.cost);
  // Bỏ những phương án CHƯA xếp hết chi tiết nếu phương án tốt nhất đã xếp hết:
  // chủ xưởng không có lý do gì chọn một phương án thiếu chi tiết.
  const need = run.best.unplaced.length;
  const cands = pool.filter((s) => s.unplaced.length <= need).map(score);

  for (const tier of [1, 2] as const) {
    for (const c of cands) {
      if (alternatives.length >= MAX_PLANS) break;
      if (!distinctFrom(c, chosen, tier)) continue;
      chosen.push(c);
      alternatives.push(planOf(c.snap, specs, byId));
    }
    if (alternatives.length >= MAX_PLANS) break;
  }

  pool = [];
  return { best, alternatives };
}
