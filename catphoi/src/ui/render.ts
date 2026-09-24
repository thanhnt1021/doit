/** Vẽ tấm tôn và chi tiết bằng Canvas 2D. */
import type { Part, Point, Ring, SheetLayout } from '../types';
import { applyPlacementRing } from '../types';
import { labelPoint, pointSegDistance } from '../core/geometry';
import { NAME_SEP, fullName } from './labels';

/**
 * Tên hiển thị của chi tiết: "P3 · mạn 15" (mã P luôn còn, tên chỉ ghép thêm).
 * Xem src/ui/labels.ts để biết thứ tự ưu tiên tên.
 */
export function displayName(part: Part, labels?: Record<string, string>): string {
  return fullName(part, labels);
}

const COLORS = [
  '#d64545', '#2f8f4e', '#2f5fd6', '#c98a12', '#8b3fbf', '#0f8f96',
  '#c2447a', '#5a7f17', '#3a6ea5', '#a4561d',
];

// ─────────────────────────── VIỆC 5: nhãn không được lòi ra ngoài hình ───────

export interface FitLabelBox {
  /** Bề ngang chỗ đặt nhãn, pixel. */
  maxWidth: number;
  /** Bề cao chỗ đặt nhãn, pixel. */
  maxHeight: number;
  /** Cỡ chữ mong muốn, pixel. Mặc định 11. */
  maxFont?: number;
  /** Cỡ chữ nhỏ nhất còn đọc được, pixel. Mặc định 7. */
  minFont?: number;
}

export interface FittedLabel {
  /** 1 hoặc 2 dòng chữ đã vừa khung. */
  lines: string[];
  /** Cỡ chữ đã chọn, pixel. */
  font: number;
  /** true = đã phải cắt bớt chữ và thêm dấu ba chấm. */
  clipped: boolean;
}

/** Khoảng cách giữa 2 dòng = cỡ chữ × hệ số này. */
const LINE_GAP = 1.15;

function cutToWidth(
  text: string, font: number, maxWidth: number, measure: (t: string, f: number) => number
): { text: string; clipped: boolean } {
  if (measure(text, font) <= maxWidth) return { text, clipped: false };
  // Cắt dần từ cuối, luôn để lại ít nhất 1 ký tự + dấu ba chấm.
  for (let n = text.length - 1; n >= 1; n--) {
    const t = text.slice(0, n) + '…';
    if (measure(t, font) <= maxWidth) return { text: t, clipped: true };
  }
  return { text: '…', clipped: true };
}

/**
 * Nhồi tên chi tiết vào đúng bề rộng chỗ đặt nhãn.
 *
 * Thợ trước báo lỗi thật: tên 16 ký tự tràn ra ngoài thanh sườn rộng 250mm —
 * điểm neo đúng trong hình nhưng chữ dài hơn bề ngang. Cách xử theo thứ tự:
 *   1. giữ 1 dòng, co cỡ chữ từ 11px xuống dần;
 *   2. vẫn không vừa → xuống 2 dòng (tách ở dấu " · ", không có thì tách ở
 *      khoảng trắng gần giữa nhất), co cỡ chữ tiếp;
 *   3. cùng đường → cắt bớt chữ kèm dấu ba chấm ở cỡ nhỏ nhất.
 * Nhờ vậy chữ KHÔNG BAO GIỜ lòi ra ngoài hình.
 *
 * `measure(text, font)` do chỗ gọi cung cấp (canvas đo thật; test đo giả).
 */
export function fitLabel(
  text: string, measure: (t: string, font: number) => number, box: FitLabelBox
): FittedLabel {
  const maxFont = box.maxFont ?? 11;
  const minFont = box.minFont ?? 7;
  const maxW = Math.max(1, box.maxWidth);
  const maxH = Math.max(1, box.maxHeight);

  // Các cách xuống dòng, thử theo thứ tự ưu tiên.
  const oneLine = [text];
  const twoLines = splitTwoLines(text);
  const layouts: string[][] = twoLines ? [oneLine, twoLines] : [oneLine];

  for (let font = maxFont; font >= minFont - 1e-9; font -= 0.5) {
    for (const lines of layouts) {
      if (lines.length * font * LINE_GAP > maxH) continue;
      if (lines.every((l) => measure(l, font) <= maxW)) {
        return { lines, font: Math.round(font * 2) / 2, clipped: false };
      }
    }
  }

  // Hết cửa: cắt bớt chữ ở cỡ nhỏ nhất.
  const lines = twoLines && 2 * minFont * LINE_GAP <= maxH ? twoLines : oneLine;
  let clipped = false;
  const out = lines.map((l) => {
    const c = cutToWidth(l, minFont, maxW, measure);
    if (c.clipped) clipped = true;
    return c.text;
  });
  return { lines: out, font: minFont, clipped };
}

/** Tách tên thành 2 dòng: ưu tiên dấu " · ", không có thì khoảng trắng gần giữa. */
function splitTwoLines(text: string): string[] | null {
  const sep = text.indexOf(NAME_SEP);
  if (sep > 0) {
    const a = text.slice(0, sep).trim();
    const b = text.slice(sep + NAME_SEP.length).trim();
    if (a && b) return [a, b];
  }
  const spaces: number[] = [];
  for (let i = 0; i < text.length; i++) if (text[i] === ' ') spaces.push(i);
  if (spaces.length === 0) return null;
  const mid = text.length / 2;
  let best = spaces[0];
  for (const s of spaces) if (Math.abs(s - mid) < Math.abs(best - mid)) best = s;
  const a = text.slice(0, best).trim();
  const b = text.slice(best + 1).trim();
  return a && b ? [a, b] : null;
}

/**
 * Bán kính hình tròn lớn nhất tâm `at` còn nằm gọn trong hình (mm).
 * Dùng để biết chỗ đặt nhãn rộng bao nhiêu — tính cả lỗ khoét, nên nhãn không
 * bao giờ đè lên mép lỗ.
 */
export function inscribedRadius(rings: Ring[], at: Point): number {
  let best = Infinity;
  for (const ring of rings) {
    for (let i = 0; i < ring.length; i++) {
      const d = pointSegDistance(at, ring[i], ring[(i + 1) % ring.length]);
      if (d < best) best = d;
    }
  }
  return Number.isFinite(best) ? best : 0;
}

// ─────────────────────────── vẽ ─────────────────────────────────────────────

function setupCanvas(canvas: HTMLCanvasElement, cssW: number, cssH: number): CanvasRenderingContext2D | null {
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  canvas.style.width = `${cssW}px`;
  canvas.style.height = `${cssH}px`;
  canvas.width = Math.max(1, Math.round(cssW * dpr));
  canvas.height = Math.max(1, Math.round(cssH * dpr));
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);
  return ctx;
}

function tracePath(ctx: CanvasRenderingContext2D, ring: Ring, toPx: (x: number, y: number) => [number, number]): void {
  ctx.beginPath();
  ring.forEach((p, i) => {
    const [x, y] = toPx(p.x, p.y);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.closePath();
}

const fontOf = (px: number) => `600 ${px}px system-ui, -apple-system, Segoe UI, sans-serif`;

/** Vẽ 1 tấm đã xếp. Khung vẽ lấy theo kích thước CSS của canvas cha. */
export function drawSheet(
  canvas: HTMLCanvasElement,
  sheet: SheetLayout,
  parts: Part[],
  opts: { cssWidth: number; cssHeight: number; labels?: Record<string, string> }
): void {
  const ctx = setupCanvas(canvas, opts.cssWidth, opts.cssHeight);
  if (!ctx) return;
  const pad = 8;
  const sx = (opts.cssWidth - pad * 2) / sheet.height; // tấm nằm ngang: chiều dài theo trục màn hình X
  const sy = (opts.cssHeight - pad * 2) / sheet.width;
  const s = Math.min(sx, sy);
  // xoay 90°: (x tôn = bề rộng) vẽ theo trục dọc màn hình, (y tôn = chiều dài) theo trục ngang
  const toPx = (x: number, y: number): [number, number] => [pad + y * s, pad + (sheet.width - x) * s];

  ctx.fillStyle = '#ffffff';
  ctx.strokeStyle = '#333';
  ctx.lineWidth = 1.5;
  const [x0, y0] = toPx(sheet.width, 0);
  ctx.fillRect(x0, y0, sheet.height * s, sheet.width * s);
  ctx.strokeRect(x0, y0, sheet.height * s, sheet.width * s);

  // Tấm lấy từ kho tôn thừa mang theo các LỖ ĐÃ CẮT của lượt trước (src/remnant).
  // Tô xám để thợ nhìn ra ngay chỗ nào đã mất tôn, không đặt bản vẽ lên đó.
  // `cuts` do src/remnant gắn vào · `blocked` do engine trả về — nhận cả hai.
  const withHoles = sheet as SheetLayout & { cuts?: Ring[]; blocked?: Ring[] };
  const holes = Array.isArray(withHoles.cuts) && withHoles.cuts.length
    ? withHoles.cuts
    : withHoles.blocked;
  if (Array.isArray(holes)) {
    ctx.fillStyle = '#e6e8ec';
    ctx.strokeStyle = '#9aa1ab';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 3]);
    for (const cut of holes) {
      if (!cut || cut.length < 3) continue;
      tracePath(ctx, cut, toPx);
      ctx.fill();
      ctx.stroke();
    }
    ctx.setLineDash([]);
  }

  const measure = (t: string, font: number): number => {
    ctx.font = fontOf(font);
    return ctx.measureText(t).width;
  };

  const byId = new Map(parts.map((p) => [p.id, p]));
  sheet.placements.forEach((pl, i) => {
    const part = byId.get(pl.partId);
    if (!part) return;
    const color = COLORS[i % COLORS.length];
    const rings = part.rings.map((r) => applyPlacementRing(r, pl));
    ctx.fillStyle = color + '33';
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.2;
    tracePath(ctx, rings[0], toPx);
    ctx.fill();
    ctx.stroke();
    for (let k = 1; k < rings.length; k++) {
      ctx.fillStyle = '#ffffff';
      tracePath(ctx, rings[k], toPx);
      ctx.fill();
      ctx.stroke();
    }
    // Nhãn phải nằm TRONG hình: trọng tâm thô của thanh cong chữ S rơi ra ngoài,
    // nên dùng điểm cực (pole of inaccessibility) của chính chi tiết đã đặt.
    const at = labelPoint(rings);
    const [cx, cy] = toPx(at.x, at.y);
    const name = displayName(part, opts.labels) + (part.qty > 1 ? `#${pl.instance + 1}` : '');

    // VIỆC 5: chỗ đặt nhãn rộng đúng bằng đường kính hình tròn nội tiếp tại
    // điểm neo (đổi sang pixel). Co chữ / xuống dòng / cắt bớt cho vừa.
    const rPx = inscribedRadius(rings, at) * s;
    const fit = fitLabel(name, measure, {
      maxWidth: Math.max(8, rPx * 1.9),
      maxHeight: Math.max(7, rPx * 1.9),
    });

    ctx.font = fontOf(fit.font);
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const lineH = fit.font * LINE_GAP;
    const top = cy - ((fit.lines.length - 1) * lineH) / 2;
    fit.lines.forEach((line, k) => {
      const y = top + k * lineH;
      // viền trắng mỏng cho chữ nổi trên nền hình
      ctx.lineWidth = 3;
      ctx.strokeStyle = '#ffffff';
      ctx.strokeText(line, cx, y);
      ctx.fillStyle = '#111';
      ctx.fillText(line, cx, y);
    });
  });
}

/** Vẽ thumbnail 1 chi tiết vừa khung vuông. */
export function drawThumb(canvas: HTMLCanvasElement, part: Part, size = 44): void {
  const ctx = setupCanvas(canvas, size, size);
  if (!ctx) return;
  const w = part.bbox.maxX - part.bbox.minX || 1;
  const h = part.bbox.maxY - part.bbox.minY || 1;
  const s = Math.min((size - 6) / w, (size - 6) / h);
  const ox = (size - w * s) / 2;
  const oy = (size - h * s) / 2;
  const toPx = (x: number, y: number): [number, number] => [ox + x * s, size - oy - y * s];
  ctx.fillStyle = part.fitsSheet ? '#4a7fd622' : '#d6454522';
  ctx.strokeStyle = part.fitsSheet ? '#3a6ea5' : '#d64545';
  ctx.lineWidth = 1;
  tracePath(ctx, part.rings[0], toPx);
  ctx.fill();
  ctx.stroke();
  for (let k = 1; k < part.rings.length; k++) {
    ctx.fillStyle = '#fff';
    tracePath(ctx, part.rings[k], toPx);
    ctx.fill();
    ctx.stroke();
  }
}
