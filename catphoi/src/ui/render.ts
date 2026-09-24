/** Vẽ tấm tôn và chi tiết bằng Canvas 2D. */
import type { Part, Ring, SheetLayout } from '../types';
import { applyPlacementRing } from '../types';
import { labelPoint } from '../core/geometry';

/** Tên hiển thị của chi tiết: tên người dùng tự đặt (có dấu) hoặc mã P0/P1… */
export function displayName(part: Part, labels?: Record<string, string>): string {
  const raw = (labels?.[part.id] ?? '').trim();
  return raw || part.id;
}

const COLORS = [
  '#d64545', '#2f8f4e', '#2f5fd6', '#c98a12', '#8b3fbf', '#0f8f96',
  '#c2447a', '#5a7f17', '#3a6ea5', '#a4561d',
];

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
    ctx.font = '600 11px system-ui, -apple-system, Segoe UI, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    // viền trắng mỏng cho chữ nổi trên nền hình
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#ffffff';
    ctx.strokeText(name, cx, cy);
    ctx.fillStyle = '#111';
    ctx.fillText(name, cx, cy);
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
