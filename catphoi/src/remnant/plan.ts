/**
 * Xếp phôi CÓ DÙNG TÔN THỪA.
 *
 * Ý đồ của founder: lô nào cũng phải nhét vào tôn thừa đang cất trong kho TRƯỚC,
 * hết chỗ mới được mở tấm mới nguyên khổ 2×6m.
 *
 * ⚠ CHẶN Ở ĐÂU: API public của engine là `nest({ parts, params })`, mà
 * `NestParams` chỉ có MỘT cặp `sheetW`/`sheetH` (src/types.ts) — engine dựng mọi
 * tấm bằng `nester.newSheet()` nên tấm nào cũng y hệt nhau, và không có đường
 * nào khai báo vùng cấm (phần đã bị cắt mất của tấm thừa). Mình KHÔNG được sửa
 * src/nest (thợ khác đang làm), nên ở đây đi đường vòng:
 *
 *   1. Mỗi tấm thừa → lấy HÌNH CHỮ NHẬT LỚN NHẤT nằm gọn trong nó (geometry.ts).
 *   2. Gọi `nest()` một lượt RIÊNG cho hình chữ nhật đó, chỉ lấy TẤM ĐẦU TIÊN.
 *   3. Trừ những chi tiết đã nhét được ra khỏi danh sách, sang tấm thừa kế tiếp.
 *   4. Còn dư bao nhiêu mới gọi `nest()` lần cuối với khổ tấm mới.
 *
 * Giá phải trả: phần lồi lõm ngoài hình chữ nhật của tấm thừa bị bỏ không.
 * Muốn tận dụng hết thì engine phải nhận được tấm nhiều kích thước + vùng cấm —
 * xem ghi chú BLOCKER ở cuối file.
 */
import { nest as realNest } from '../nest';
import type { NestParams, NestProgress, NestResult, Part, Placement, Ring, SheetLayout } from '../types';
import { DEFAULT_NEST_PARAMS } from '../types';
import type { Remnant } from './types';
import { largestInnerRect, polygonArea, type Box } from './geometry';

/** Một tấm trong phương án, có thêm thông tin "tấm này là tôn thừa nào". */
export interface PlannedSheet extends SheetLayout {
  source: 'remnant' | 'new';
  remnantId?: string;
  remnantName?: string;
  /** Hình thật của tấm thừa, để UI vẽ đúng phần tôn còn lại. */
  polygon?: Ring[];
  /** Ô chữ nhật thực sự dùng được bên trong tấm thừa (toạ độ tấm). */
  usableRect?: Box;
}

export interface RemnantUsage {
  id: string;
  name: string;
  /** Số chi tiết nhét được vào tấm thừa này. */
  placed: number;
  /** Diện tích chi tiết / diện tích tôn thừa thật, 0..1. */
  utilization: number;
  /** Phần diện tích tấm thừa mà hình chữ nhật nội tiếp với tới được, 0..1. */
  coverage: number;
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
  nest?: typeof realNest;
  now?: () => number;
  onProgress?: (p: NestProgress) => void;
  shouldStop?: () => boolean;
}

function clonePart(p: Part, qty: number): Part {
  return { ...p, qty };
}

/** Đếm mỗi partId xuất hiện bao nhiêu lần trên một tấm. */
function countByPart(placements: Placement[]): Map<string, number> {
  const m = new Map<string, number>();
  for (const pl of placements) m.set(pl.partId, (m.get(pl.partId) || 0) + 1);
  return m;
}

export function nestWithRemnants(
  parts: Part[],
  paramsIn: Partial<NestParams>,
  remnants: Remnant[],
  deps: PlanDeps = {}
): RemnantNestResult {
  const params: NestParams = { ...DEFAULT_NEST_PARAMS, ...paramsIn };
  const nestFn = deps.nest ?? realNest;
  const now = deps.now ?? (() => Date.now());
  const t0 = now();

  const cell = params.gridCell ?? 5;
  /** Tấm thừa nhỏ hơn lề hai bên + một chút thì vô dụng, khỏi mất công gọi engine. */
  const minSide = 2 * params.margin + Math.max(params.gap, 10);

  const skipped: RemnantNestResult['skipped'] = [];
  const usable: { r: Remnant; rect: ReturnType<typeof largestInnerRect> }[] = [];
  for (const r of remnants) {
    const poly = r.polygon && r.polygon.length ? r.polygon : [];
    if (poly.length === 0) {
      skipped.push({ id: r.id, name: r.name, reason: 'Tấm thừa chưa có hình dạng.' });
      continue;
    }
    const rect = largestInnerRect(poly, cell);
    if (rect.w < minSide || rect.h < minSide) {
      skipped.push({
        id: r.id,
        name: r.name,
        reason: `Phần dùng được chỉ ${Math.round(rect.w)}×${Math.round(rect.h)}mm, nhỏ hơn lề ${params.margin}mm hai bên.`,
      });
      continue;
    }
    usable.push({ r, rect });
  }
  // Tấm thừa to đem xếp trước: chi tiết lớn chỉ có cửa vào tấm to.
  usable.sort((a, b) => b.rect.w * b.rect.h - a.rect.w * a.rect.h);

  // Chia thời gian: gần nửa cho các tấm thừa, phần còn lại cho khổ nguyên.
  const totalMs = Math.max(400, params.timeLimitMs);
  const perRemnant = usable.length
    ? Math.max(1200, Math.floor((totalMs * 0.45) / usable.length))
    : 0;

  let remaining: Part[] = parts
    .filter((p) => p.enabled)
    .map((p) => clonePart(p, Math.max(1, Math.floor(p.qty) || 1)));

  /** Số bản đã đặt của từng chi tiết, để đánh số instance liên tục trên cả phương án. */
  const nextInstance = new Map<string, number>();
  const takeInstance = (partId: string): number => {
    const v = nextInstance.get(partId) || 0;
    nextInstance.set(partId, v + 1);
    return v;
  };

  const sheets: PlannedSheet[] = [];
  const remnantsUsed: RemnantUsage[] = [];
  let iterations = 0;

  /**
   * Ảnh chụp phương án đang có, để nút DỪNG trên giao diện vẫn lấy được kết quả
   * dở dang thay vì mất trắng. `extra` là các tấm mới của lượt xếp cuối (nếu đã có).
   */
  const snapshot = (extra: PlannedSheet[] = [], extraUnplaced: string[] = []): RemnantNestResult => {
    const all = [...sheets, ...extra];
    let used = 0;
    let avail = 0;
    for (const s of all) {
      used += s.usedArea;
      avail += s.source === 'remnant' && s.polygon ? polygonArea(s.polygon) : s.width * s.height;
    }
    return {
      sheets: all,
      remnantsUsed: [...remnantsUsed],
      newSheets: extra.length,
      skipped: [...skipped],
      unplaced: extraUnplaced,
      utilization: avail > 0 ? used / avail : 0,
      elapsedMs: now() - t0,
      iterations,
      params,
    };
  };

  for (const { r, rect } of usable) {
    if (remaining.length === 0) break;
    if (deps.shouldStop?.()) break;

    deps.onProgress?.({
      fraction: Math.min(0.9, (now() - t0) / totalMs),
      elapsedMs: now() - t0,
      iterations,
      best: null,
      label: `Đang thử nhét vào tấm thừa "${r.name}"…`,
    });

    // Chuyển tiếp tiến độ của lượt xếp con ra ngoài, KHÔNG kèm phương án con
    // (phương án con chỉ nói về ô chữ nhật bên trong tấm thừa, vẽ ra là sai chỗ).
    // `best` ở đây là các tấm thừa ĐÃ CHỐT trước đó, để bấm DỪNG vẫn còn cái mà dùng.
    const subRelay = deps.onProgress
      ? (p: NestProgress) => {
        deps.onProgress?.({
          fraction: Math.min(0.9, (now() - t0) / totalMs),
          elapsedMs: now() - t0,
          iterations: iterations + p.iterations,
          best: sheets.length ? snapshot() : null,
          label: `Đang thử nhét vào tấm thừa "${r.name}"…`,
        });
      }
      : undefined;

    let sub: NestResult;
    try {
      sub = nestFn(
        {
          parts: remaining,
          params: { ...params, sheetW: rect.w, sheetH: rect.h, timeLimitMs: perRemnant },
        },
        { shouldStop: deps.shouldStop, now: deps.now, onProgress: subRelay }
      );
    } catch {
      // Một tấm thừa hỏng không được làm sập cả lượt xếp.
      skipped.push({ id: r.id, name: r.name, reason: 'Engine xếp phôi báo lỗi với tấm này.' });
      continue;
    }
    iterations += sub.iterations;

    const first = sub.sheets[0];
    if (!first || first.placements.length === 0) {
      skipped.push({ id: r.id, name: r.name, reason: 'Không chi tiết nào nhét vừa tấm thừa này.' });
      continue;
    }

    // Dời toàn bộ vị trí về đúng chỗ của ô chữ nhật bên trong tấm thừa.
    const placements: Placement[] = first.placements.map((pl) => ({
      ...pl,
      instance: takeInstance(pl.partId),
      x: pl.x + rect.x,
      y: pl.y + rect.y,
    }));

    const realArea = polygonArea(r.polygon);
    sheets.push({
      index: sheets.length,
      width: r.widthMm,
      height: r.lengthMm,
      placements,
      usedArea: first.usedArea,
      utilization: realArea > 0 ? first.usedArea / realArea : 0,
      source: 'remnant',
      remnantId: r.id,
      remnantName: r.name,
      polygon: r.polygon,
      usableRect: { x: rect.x, y: rect.y, w: rect.w, h: rect.h },
    });
    remnantsUsed.push({
      id: r.id,
      name: r.name,
      placed: placements.length,
      utilization: realArea > 0 ? first.usedArea / realArea : 0,
      coverage: rect.coverage,
    });

    deps.onProgress?.({
      fraction: Math.min(0.9, (now() - t0) / totalMs),
      elapsedMs: now() - t0,
      iterations,
      best: snapshot(),
      label: `Đã nhét ${placements.length} chi tiết vào tấm thừa "${r.name}".`,
    });

    // Trừ những gì đã nhét được ra khỏi danh sách còn phải xếp.
    const used = countByPart(first.placements);
    remaining = remaining
      .map((p) => clonePart(p, p.qty - (used.get(p.id) || 0)))
      .filter((p) => p.qty > 0);
  }

  // ── Phần còn dư: mở tấm mới nguyên khổ ──────────────────────────────────
  let unplaced: string[] = [];
  let newSheets = 0;
  if (remaining.length > 0) {
    const leftMs = Math.max(Math.floor(totalMs * 0.35), totalMs - (now() - t0));
    deps.onProgress?.({
      fraction: 0.92,
      elapsedMs: now() - t0,
      iterations,
      best: null,
      label: 'Hết chỗ trong kho tôn thừa — đang xếp nốt lên tấm mới…',
    });
    // Tiến độ của lượt cuối chỉ biết các TẤM MỚI. Gộp thêm tấm thừa đã xếp ở trên
    // vào rồi mới báo ra ngoài, để nút DỪNG trả về phương án đầy đủ.
    const relay = deps.onProgress
      ? (p: NestProgress) => {
        const extra: PlannedSheet[] = (p.best?.sheets || []).map((s, i) => ({
          ...s,
          index: sheets.length + i,
          source: 'new' as const,
        }));
        deps.onProgress?.({
          ...p,
          fraction: 0.92 + p.fraction * 0.08,
          best: p.best ? snapshot(extra, p.best.unplaced) : snapshot(),
          label: 'Xếp nốt lên tấm mới — ' + p.label,
        });
      }
      : undefined;
    const last = nestFn(
      { parts: remaining, params: { ...params, timeLimitMs: leftMs } },
      { shouldStop: deps.shouldStop, now: deps.now, onProgress: relay }
    );
    iterations += last.iterations;
    unplaced = last.unplaced;
    for (const s of last.sheets) {
      sheets.push({
        ...s,
        index: sheets.length,
        placements: s.placements.map((pl) => ({ ...pl, instance: takeInstance(pl.partId) })),
        source: 'new',
      });
      newSheets++;
    }
  }

  // Tỉ lệ dùng tôn tính trên diện tích THẬT: tấm thừa tính theo đa giác, tấm mới theo khổ.
  let totalUsed = 0;
  let totalAvail = 0;
  for (const s of sheets) {
    totalUsed += s.usedArea;
    totalAvail += s.source === 'remnant' && s.polygon ? polygonArea(s.polygon) : s.width * s.height;
  }

  return {
    sheets,
    remnantsUsed,
    newSheets,
    skipped,
    unplaced,
    utilization: totalAvail > 0 ? totalUsed / totalAvail : 0,
    elapsedMs: now() - t0,
    iterations,
    params,
  };
}

/*
 * ─────────────────────────── BLOCKER (cần thợ engine) ───────────────────────────
 * Muốn tận dụng HẾT tấm tôn thừa (cả phần lồi lõm, không chỉ hình chữ nhật nội tiếp),
 * API của src/nest phải mở thêm MỘT trong hai đường:
 *
 *   (a) NestParams nhận danh sách tấm:
 *         sheets?: { w: number; h: number; blocked?: Ring[] }[]
 *       engine xếp lần lượt theo thứ tự đó rồi mới mở tấm mặc định sheetW×sheetH.
 *
 *   (b) hoặc đơn giản hơn: export cách nạp sẵn vùng cấm vào lưới của một tấm, kiểu
 *         Nester.newSheet(blockedRings?: Ring[])
 *       (hiện `newSheet()` không nhận tham số, và `PartPrep`/`AngleOpt` không được
 *        export nên không thể tự lái `Nester.place()` từ ngoài module).
 *
 * Trước khi có một trong hai, hàm trên là cách an toàn nhất làm được từ bên ngoài.
 */
