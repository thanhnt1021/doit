/// <reference lib="webworker" />
/**
 * Worker xếp phôi. Engine chạy đồng bộ và chiếm trọn luồng của worker, nên nút
 * "Dừng" không gửi message vào được. Cách xử lý: worker bắn `progress` kèm
 * PHƯƠNG ÁN TỐT NHẤT hiện tại mỗi ~250ms; khi người dùng bấm Dừng thì luồng
 * chính terminate worker và dùng luôn phương án tốt nhất vừa nhận.
 * Nhờ vậy không cần SharedArrayBuffer (không phải bật COOP/COEP).
 */
import { nest } from './engine';
import type { NestParams, Part } from '../types';

interface StartMsg {
  type: 'start';
  parts: Part[];
  params: NestParams;
}

self.onmessage = (ev: MessageEvent<StartMsg>) => {
  const msg = ev.data;
  if (!msg || msg.type !== 'start') return;
  try {
    const result = nest(
      { parts: msg.parts, params: msg.params },
      {
        onProgress: (p) => {
          (self as unknown as Worker).postMessage({ type: 'progress', payload: p });
        },
      }
    );
    (self as unknown as Worker).postMessage({ type: 'done', payload: result });
  } catch (e) {
    (self as unknown as Worker).postMessage({
      type: 'error',
      message: 'Lỗi khi xếp: ' + (e instanceof Error ? e.message : String(e)),
    });
  }
};
