/**
 * Điểm vào của ứng dụng: nối giao diện với 2 Web Worker (parse DXF, xếp phôi)
 * và các hàm xuất file. Không có backend — mọi thứ chạy trong trình duyệt.
 */
import { zipSync, strToU8 } from 'fflate';
import { mountApp, type AppServices } from './ui/app';
// Kho tôn thừa: module tự gắn panel vào <div id="remnant-slot"> và treo
// window.catphoiRemnant để nút XẾP dùng khi có tấm thừa được tích chọn.
import './remnant';
import { exportAllSheetsDxfR12, exportSheetDxfR12, sheetFileName } from './core/dxf-export';
import { generateGcode } from './core/gcode';
import type {
  GcodeOptions, NestParams, NestProgress, NestResult, Part, ParseOptions, ParseResult, SheetLayout,
} from './types';

let nestWorker: Worker | null = null;

function partsMap(parts: Part[]): Map<string, Part> {
  return new Map(parts.map((p) => [p.id, p]));
}

function download(name: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

const services: AppServices = {
  parseFile(file, opts, onProgress) {
    return new Promise<ParseResult>((resolve, reject) => {
      const worker = new Worker(new URL('./workers/parse.worker.ts', import.meta.url), { type: 'module' });
      const fail = (m: string) => {
        worker.terminate();
        reject(new Error(m));
      };
      worker.onmessage = (ev) => {
        const m = ev.data;
        if (m.type === 'progress') onProgress(m.fraction, m.label);
        else if (m.type === 'done') {
          worker.terminate();
          resolve(m.result as ParseResult);
        } else if (m.type === 'error') fail(m.message);
      };
      worker.onerror = () => fail('Worker đọc file gặp lỗi. Hãy thử tải lại trang.');
      const reader = new FileReader();
      reader.onerror = () => fail('Không đọc được file từ ổ đĩa.');
      reader.onload = () => {
        const opts2: Omit<ParseOptions, 'onProgress'> = {
          unitScale: opts.unitScale,
          chainTol: opts.chainTol,
          sheetWidth: opts.sheetWidth,
          sheetHeight: opts.sheetHeight,
        };
        worker.postMessage({ type: 'parse', text: String(reader.result), opts: opts2 });
      };
      reader.readAsText(file);
    });
  },

  startNest(parts: Part[], params: NestParams, onProgress: (p: NestProgress) => void) {
    return new Promise<NestResult>((resolve, reject) => {
      nestWorker?.terminate();
      const worker = new Worker(new URL('./nest/worker.ts', import.meta.url), { type: 'module' });
      nestWorker = worker;
      let best: NestResult | null = null;
      worker.onmessage = (ev) => {
        const m = ev.data;
        if (m.type === 'progress') {
          const p = m.payload as NestProgress;
          if (p.best) best = p.best;
          onProgress(p);
        } else if (m.type === 'done') {
          worker.terminate();
          if (nestWorker === worker) nestWorker = null;
          resolve(m.payload as NestResult);
        } else if (m.type === 'error') {
          worker.terminate();
          if (nestWorker === worker) nestWorker = null;
          reject(new Error(m.message));
        }
      };
      worker.onerror = () => {
        worker.terminate();
        if (nestWorker === worker) nestWorker = null;
        reject(new Error('Worker xếp phôi gặp lỗi. Hãy thử lại với thời gian ngắn hơn.'));
      };
      // Bấm Dừng: luồng chính tắt worker và lấy phương án tốt nhất đã nhận được.
      (worker as Worker & { __stop?: () => void }).__stop = () => {
        worker.terminate();
        if (nestWorker === worker) nestWorker = null;
        if (best) resolve(best);
        else reject(new Error('Đã dừng trước khi có phương án nào. Hãy bấm XẾP và chờ thêm vài giây.'));
      };
      worker.postMessage({ type: 'start', parts, params });
    });
  },

  stopNest() {
    const w = nestWorker as (Worker & { __stop?: () => void }) | null;
    w?.__stop?.();
  },

  exportSheetDxf(sheet: SheetLayout, parts: Part[]) {
    return exportSheetDxfR12(sheet, partsMap(parts));
  },
  exportAllDxf(sheets: SheetLayout[], parts: Part[]) {
    return exportAllSheetsDxfR12(sheets, partsMap(parts));
  },
  exportGcode(sheet: SheetLayout, parts: Part[], opts: GcodeOptions) {
    return generateGcode(sheet, partsMap(parts), opts);
  },
  sheetFileName,

  downloadText(name, content) {
    download(name, new Blob([content], { type: 'text/plain;charset=utf-8' }));
  },

  async downloadZip(zipName, files) {
    const entries: Record<string, Uint8Array> = {};
    for (const f of files) entries[f.name] = strToU8(f.content);
    const zipped = zipSync(entries, { level: 6 });
    download(zipName, new Blob([zipped as unknown as BlobPart], { type: 'application/zip' }));
  },
};

const root = document.getElementById('app');
if (root) mountApp(root, services);
