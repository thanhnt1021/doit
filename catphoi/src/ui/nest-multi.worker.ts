/// <reference lib="webworker" />
/**
 * Worker sinh nhiều phương án xếp (VIỆC 1).
 *
 * Vì sao cần worker: engine xếp chạy ĐỒNG BỘ cả phút. Gọi thẳng trên luồng
 * chính thì trang đứng hình, thanh tiến độ không nhúc nhích, nút DỪNG bấm không
 * ăn — y như ghi chú ở src/nest/worker.ts và src/remnant/nest.worker.ts.
 *
 * Nút DỪNG: engine chiếm trọn luồng worker nên không nhận message được. Luồng
 * chính tắt worker và dùng danh sách phương án mới nhất nhận qua 'plans'.
 */
import { runMultiNest, type NestSheetSpec } from './nest-multi-core';
import type { NestParams, Part } from '../types';

interface StartMsg {
  type: 'start';
  parts: Part[];
  params: NestParams;
  count?: number;
  sheets?: NestSheetSpec[];
}

self.onmessage = (ev: MessageEvent<StartMsg>) => {
  const msg = ev.data;
  if (!msg || msg.type !== 'start') return;
  const post = (m: unknown) => (self as unknown as Worker).postMessage(m);
  try {
    const out = runMultiNest(msg.parts, msg.params, {
      count: msg.count,
      sheets: msg.sheets,
      onProgress: (p) => post({ type: 'progress', payload: p }),
    });
    post({ type: 'done', payload: out });
  } catch (e) {
    post({
      type: 'error',
      message: 'Lỗi khi tìm phương án xếp: ' + (e instanceof Error ? e.message : String(e)),
    });
  }
};
