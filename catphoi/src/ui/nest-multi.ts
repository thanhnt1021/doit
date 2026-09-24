/**
 * Cầu nối luồng chính ↔ worker sinh nhiều phương án (VIỆC 1).
 *
 * Không có Worker (test chạy trong Node) thì chạy thẳng, vẫn đúng kết quả.
 */
import type { NestParams, NestProgress, Part } from '../types';
import { runMultiNest, type MultiNestOutcome, type NestSheetSpec } from './nest-multi-core';

export interface StartMultiOptions {
  count?: number;
  sheets?: NestSheetSpec[];
  onProgress?: (p: NestProgress) => void;
  /** Luồng chính hỏi mỗi 120ms; trả true là tắt worker và lấy cái đang có. */
  shouldStop?: () => boolean;
}

export function startMultiNest(
  parts: Part[],
  params: NestParams,
  opts: StartMultiOptions = {}
): Promise<MultiNestOutcome> {
  if (typeof Worker === 'undefined') {
    return Promise.resolve(runMultiNest(parts, params, {
      count: opts.count,
      sheets: opts.sheets,
      onProgress: opts.onProgress,
      shouldStop: opts.shouldStop,
    }));
  }

  return new Promise<MultiNestOutcome>((resolve, reject) => {
    const worker = new Worker(new URL('./nest-multi.worker.ts', import.meta.url), { type: 'module' });
    /**
     * Phương án tốt nhất nhận được cho tới lúc này. Engine chiếm trọn luồng
     * worker nên không nhận message "dừng" được: bấm DỪNG thì luồng chính tắt
     * worker rồi trả về đúng cái này, thay vì để founder mất trắng công chờ.
     */
    let partial: MultiNestOutcome | null = null;
    let timer = 0;
    const cleanup = () => {
      if (timer) window.clearInterval(timer);
      timer = 0;
      worker.terminate();
    };
    worker.onmessage = (ev: MessageEvent) => {
      const m = ev.data;
      if (!m) return;
      if (m.type === 'progress') {
        const p = m.payload as NestProgress;
        if (p.best && p.best.sheets.length > 0) {
          partial = { plans: [p.best], elapsedMs: p.elapsedMs };
        }
        opts.onProgress?.(p);
      } else if (m.type === 'done') {
        cleanup();
        resolve(m.payload as MultiNestOutcome);
      } else if (m.type === 'error') {
        cleanup();
        reject(new Error(String(m.message)));
      }
    };
    worker.onerror = () => {
      cleanup();
      reject(new Error('Worker tìm phương án xếp gặp lỗi. Hãy thử lại với thời gian ngắn hơn.'));
    };
    if (opts.shouldStop) {
      timer = window.setInterval(() => {
        if (!opts.shouldStop?.()) return;
        cleanup();
        if (partial) resolve(partial);
        else reject(new Error('Đã dừng trước khi có phương án nào. Hãy bấm XẾP và chờ thêm vài giây.'));
      }, 120);
    }
    worker.postMessage({
      type: 'start', parts, params, count: opts.count, sheets: opts.sheets,
    });
  });
}

export type { MultiNestOutcome, NestSheetSpec };
