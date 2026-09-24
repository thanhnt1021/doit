/// <reference lib="webworker" />
/**
 * Worker xếp phôi CÓ DÙNG TÔN THỪA.
 *
 * Vì sao cần: nestWithRemnants() chạy ĐỒNG BỘ và có thể ngốn cả phút. Gọi thẳng
 * trên luồng chính thì trang đứng hình, thanh tiến độ không nhúc nhích và nút
 * DỪNG bấm không ăn. Đưa vào worker thì giao diện vẫn mượt, y như đường xếp
 * thường ở src/nest/worker.ts.
 *
 * Nút DỪNG: engine chiếm trọn luồng worker nên không nhận được message. Luồng
 * chính terminate worker và dùng PHƯƠNG ÁN TỐT NHẤT vừa nhận qua `progress`.
 */
import { nestWithRemnants } from './plan';
import type { NestParams, Part } from '../types';
import type { Remnant } from './types';

interface StartMsg {
  type: 'start';
  parts: Part[];
  params: NestParams;
  remnants: Remnant[];
}

self.onmessage = (ev: MessageEvent<StartMsg>) => {
  const msg = ev.data;
  if (!msg || msg.type !== 'start') return;
  const post = (m: unknown) => (self as unknown as Worker).postMessage(m);
  try {
    const result = nestWithRemnants(msg.parts, msg.params, msg.remnants, {
      onProgress: (p) => post({ type: 'progress', payload: p }),
    });
    post({ type: 'done', payload: result });
  } catch (e) {
    post({
      type: 'error',
      message: 'Lỗi khi xếp có tôn thừa: ' + (e instanceof Error ? e.message : String(e)),
    });
  }
};
