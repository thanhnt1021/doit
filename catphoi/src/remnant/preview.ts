/**
 * VIỆC 2 — vẽ NGAY hình tấm thừa khi vừa tích chọn, trước khi bấm XẾP.
 * Founder muốn "căn ke nhìn trước" xem miếng thừa nằm ở góc nào của tấm.
 *
 * Hình vẽ luôn là NGUYÊN KHỔ tấm gốc (2000×6000), phần đã cắt đi tô xám gạch
 * nét đứt, phần tôn còn lại để trắng-xanh. Xoay 90° cho tấm nằm ngang, giống
 * hệt cách src/ui/render.ts vẽ tấm đã xếp, để nhìn quen mắt.
 */
import type { Ring } from '../types';
import type { Remnant } from './types';

const INK = '#1d2126';
const LINE = '#8b929c';
const STEEL = '#eaf3ec';
const CUT = '#d9dde3';
const CUT_LINE = '#b0454a';

function trace(ctx: CanvasRenderingContext2D, ring: Ring, toPx: (x: number, y: number) => [number, number]): void {
  ctx.beginPath();
  ring.forEach((p, i) => {
    const [x, y] = toPx(p.x, p.y);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.closePath();
}

export interface PreviewOptions {
  cssWidth: number;
  cssHeight: number;
}

/** Chiều cao hợp lý cho ô xem trước, theo bề ngang có sẵn. */
export function previewHeight(r: Remnant, cssWidth: number): number {
  const w = Math.max(1, r.sheetWidthMm);
  const h = Math.max(1, r.sheetLengthMm);
  return Math.max(46, Math.round((cssWidth - 12) * (w / h)) + 12);
}

/** Vẽ tấm thừa nguyên khổ kèm các lỗ đã cắt. Không có canvas 2D thì im lặng bỏ qua. */
export function drawRemnantPreview(canvas: HTMLCanvasElement, r: Remnant, opts: PreviewOptions): void {
  const dpr = Math.min(2, (typeof window !== 'undefined' && window.devicePixelRatio) || 1);
  canvas.style.width = `${opts.cssWidth}px`;
  canvas.style.height = `${opts.cssHeight}px`;
  canvas.width = Math.max(1, Math.round(opts.cssWidth * dpr));
  canvas.height = Math.max(1, Math.round(opts.cssHeight * dpr));
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, opts.cssWidth, opts.cssHeight);

  const W = Math.max(1, r.sheetWidthMm);
  const H = Math.max(1, r.sheetLengthMm);
  const pad = 6;
  const s = Math.min((opts.cssWidth - pad * 2) / H, (opts.cssHeight - pad * 2) / W);
  // Xoay 90°: bề rộng tấm chạy theo trục dọc màn hình, chiều dài theo trục ngang.
  const toPx = (x: number, y: number): [number, number] => [pad + y * s, pad + (W - x) * s];

  // Nền = phần tôn còn dùng được.
  const outer: Ring = r.polygon?.[0] ?? [
    { x: 0, y: 0 }, { x: W, y: 0 }, { x: W, y: H }, { x: 0, y: H },
  ];
  ctx.fillStyle = STEEL;
  ctx.strokeStyle = INK;
  ctx.lineWidth = 1.4;
  trace(ctx, outer, toPx);
  ctx.fill();
  ctx.stroke();

  // Phần ĐÃ CẮT ĐI — đúng vị trí trên tấm gốc.
  ctx.setLineDash([4, 3]);
  for (const cut of r.cuts) {
    if (!cut || cut.length < 3) continue;
    ctx.fillStyle = CUT;
    ctx.strokeStyle = CUT_LINE;
    ctx.lineWidth = 1;
    trace(ctx, cut, toPx);
    ctx.fill();
    ctx.stroke();
  }
  ctx.setLineDash([]);

  // Khung bao NGUYÊN KHỔ — luôn vẽ, kể cả khi biên ngoài nhỏ hơn (tấm kiểu cũ).
  ctx.strokeStyle = LINE;
  ctx.lineWidth = 1;
  ctx.setLineDash([2, 2]);
  const [bx, by] = toPx(W, 0);
  ctx.strokeRect(bx, by, H * s, W * s);
  ctx.setLineDash([]);

  // Ghi khổ tấm cho chắc ăn.
  ctx.font = '600 10px system-ui, -apple-system, Segoe UI, sans-serif';
  ctx.fillStyle = INK;
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  ctx.fillText(`${Math.round(W)}×${Math.round(H)}mm`, pad + 2, pad + 2);
}
