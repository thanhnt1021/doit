/// <reference lib="webworker" />
/**
 * Worker xếp phôi CÓ DÙNG TÔN THỪA.
 *
 * Vì sao cần: lượt xếp chạy ĐỒNG BỘ và có thể ngốn cả phút. Gọi thẳng trên
 * luồng chính thì trang đứng hình, thanh tiến độ không nhúc nhích và nút DỪNG
 * bấm không ăn. Đưa vào worker thì giao diện vẫn mượt, y như đường xếp thường
 * ở src/nest/worker.ts.
 *
 * Nút DỪNG: engine chiếm trọn luồng worker nên không nhận được message. Luồng
 * chính terminate worker và dùng phương án tốt nhất vừa nhận qua 'progress'.
 */
import { nestMultiWithRemnants } from './plan';
import type { NestParams, Part } from '../types';
import type { Remnant } from './types';

interface StartMsg {
  type: 'start';
  parts: Part[];
  params: NestParams;
  remnants: Remnant[];
  /** Số phương án muốn sinh (VIỆC 1). Mặc định 5. */
  count?: number;
}

self.onmessage = (ev: MessageEvent<StartMsg>) => {
  const msg = ev.data;
  if (!msg || msg.type !== 'start') return;
  const post = (m: unknown) => (self as unknown as Worker).postMessage(m);
  try {
    const out = nestMultiWithRemnants(msg.parts, msg.params, msg.remnants, {
      count: msg.count,
      onProgress: (p) => post({ type: 'progress', payload: p }),
    });
    post({ type: 'done', payload: out });
  } catch (e) {
    post({
      type: 'error',
      message: 'Lỗi khi xếp có tôn thừa: ' + (e instanceof Error ? e.message : String(e)),
    });
  }
};
