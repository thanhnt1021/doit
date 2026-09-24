/// <reference lib="webworker" />
/**
 * Worker parse DXF. Chạy ngoài luồng giao diện để file 8.6MB không làm đơ UI.
 */
import { parseDxf } from '../core/dxf-parse';
import type { ParseOptions } from '../types';

interface StartMsg {
  type: 'parse';
  text: string;
  opts: Omit<ParseOptions, 'onProgress'>;
}

self.onmessage = (ev: MessageEvent<StartMsg>) => {
  const msg = ev.data;
  if (!msg || msg.type !== 'parse') return;
  try {
    const result = parseDxf(msg.text, {
      ...msg.opts,
      onProgress: (fraction, label) => {
        (self as unknown as Worker).postMessage({ type: 'progress', fraction, label });
      },
    });
    (self as unknown as Worker).postMessage({ type: 'done', result });
  } catch (e) {
    (self as unknown as Worker).postMessage({
      type: 'error',
      message: 'Không đọc được file DXF: ' + (e instanceof Error ? e.message : String(e)),
    });
  }
};
