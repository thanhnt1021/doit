/**
 * Kho tôn thừa — cửa vào duy nhất của module.
 *
 * GHÉP VÀO APP: thêm ĐÚNG MỘT DÒNG vào src/main.ts (file của thợ khác, tôi không sửa):
 *
 *     import './remnant';
 *
 * Module tự gắn panel vào <div id="remnant-slot"></div> khi trang tải xong và
 * treo API lên window.catphoiRemnant để chỗ khác gọi:
 *
 *     window.catphoiRemnant.getSelected()                 // tấm thừa đang tích chọn
 *     await window.catphoiRemnant.nestWithSelected(parts) // xếp, ưu tiên tôn thừa
 */
export type { Remnant, RemnantInput, RemnantPatch, RemnantStatus } from './types';
export { createRemnantStore, memoryStorage, CACHE_KEY, QUEUE_KEY } from './store';
export type { RemnantStore, StorageLike, QueuedOp, ListOutcome, WriteOutcome } from './store';
export { validateRemnantInput } from './validate';
export {
  polygonArea, polygonBounds, rectPolygon, largestInnerRect, pointInPolygon,
} from './geometry';
export type { Box, UsableRect } from './geometry';
export { nestWithRemnants } from './plan';
export type { PlannedSheet, RemnantNestResult, RemnantUsage, PlanDeps } from './plan';
export {
  mountRemnantPanel, ensureSlot, readNestOptions, cornerCutPolygon, parsePointsText, SLOT_ID,
} from './panel';
export type { RemnantPanel } from './panel';

import type { NestParams, NestProgress, Part } from '../types';
import { mountRemnantPanel, readNestOptions, type RemnantPanel } from './panel';
import { nestWithRemnants, type RemnantNestResult } from './plan';
import type { Remnant } from './types';

/**
 * Chạy một lượt xếp có tôn thừa TRONG WEB WORKER.
 *
 * nestWithRemnants() là hàm đồng bộ, chạy cả phút. Gọi thẳng trên luồng chính
 * thì trang đứng hình: thanh tiến độ không chạy, nút DỪNG bấm không ăn. Nên đẩy
 * vào worker, y hệt cách src/main.ts làm với đường xếp thường.
 *
 * Nút DỪNG: engine chiếm trọn luồng worker nên không nhận message được. Luồng
 * chính hỏi `shouldStop()` mỗi 120ms; đến lúc cần dừng thì terminate worker và
 * lấy phương án tốt nhất vừa nhận qua `progress`.
 */
function runInWorker(
  parts: Part[],
  params: NestParams,
  remnants: Remnant[],
  onProgress?: (p: NestProgress) => void,
  shouldStop?: () => boolean
): Promise<RemnantNestResult> {
  // Không có Worker (môi trường test Node, trình duyệt quá cũ) → chạy thẳng.
  if (typeof Worker === 'undefined') {
    return Promise.resolve(nestWithRemnants(parts, params, remnants, { onProgress, shouldStop }));
  }
  return new Promise<RemnantNestResult>((resolve, reject) => {
    const worker = new Worker(new URL('./nest.worker.ts', import.meta.url), { type: 'module' });
    let best: RemnantNestResult | null = null;
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
        if (p.best) best = p.best as RemnantNestResult;
        onProgress?.(p);
      } else if (m.type === 'done') {
        cleanup();
        resolve(m.payload as RemnantNestResult);
      } else if (m.type === 'error') {
        cleanup();
        reject(new Error(String(m.message)));
      }
    };
    worker.onerror = () => {
      cleanup();
      reject(new Error('Worker xếp phôi có tôn thừa gặp lỗi. Hãy thử lại với thời gian ngắn hơn.'));
    };
    if (shouldStop) {
      timer = window.setInterval(() => {
        if (!shouldStop()) return;
        cleanup();
        if (best) resolve(best);
        else reject(new Error('Đã dừng trước khi có phương án nào. Hãy bấm XẾP và chờ thêm vài giây.'));
      }, 120);
    }
    worker.postMessage({ type: 'start', parts, params, remnants });
  });
}

export interface RemnantApi {
  panel: RemnantPanel;
  getSelected(): Remnant[];
  /**
   * Xếp phôi có ưu tiên tôn thừa đang tích chọn.
   * Thông số lượt xếp lấy từ getNestOptions() của thợ UI; chưa có thì dùng mặc định.
   */
  nestWithSelected(
    parts: Part[],
    onProgress?: (p: NestProgress) => void,
    shouldStop?: () => boolean
  ): Promise<RemnantNestResult>;
}

let api: RemnantApi | null = null;

/** Gắn panel + dựng API. Gọi nhiều lần cũng chỉ chạy một lần. */
export function setupRemnants(): RemnantApi {
  if (api) return api;
  const panel = mountRemnantPanel();
  api = {
    panel,
    getSelected: () => panel.getSelected(),
    async nestWithSelected(parts, onProgress, shouldStop) {
      const params = await readNestOptions();
      return runInWorker(parts, params, panel.getSelected(), onProgress, shouldStop);
    },
  };
  (globalThis as Record<string, unknown>).catphoiRemnant = api;
  return api;
}

// Tự khởi động khi chạy trong trình duyệt. Trong test (Node) thì không có
// document nên khối này im lặng bỏ qua.
if (typeof document !== 'undefined') {
  const boot = () => {
    try {
      setupRemnants();
    } catch (e) {
      // Panel hỏng thì thôi, tuyệt đối không được làm sập tool xếp phôi.
      console.error('[kho tôn thừa] không gắn được panel:', e);
    }
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
}
