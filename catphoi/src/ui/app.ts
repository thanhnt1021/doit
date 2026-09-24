/**
 * Màn hình duy nhất của tool "Xếp phôi tôn".
 * Toàn bộ chữ tiếng Việt có dấu. Bố cục 2 cột, vừa màn 1366x768 không cuộn ngang.
 */
import './styles.css';
import type {
  GcodeOptions, NestParams, NestProgress, NestResult, Part, ParseOptions, ParseResult, SheetLayout,
} from '../types';
import { DEFAULT_GCODE_OPTIONS, DEFAULT_NEST_PARAMS, applyPlacementRing, ringBBox } from '../types';
import { drawSheet, drawThumb } from './render';

export interface AppServices {
  parseFile(file: File, opts: ParseOptions, onProgress: (f: number, label: string) => void): Promise<ParseResult>;
  startNest(parts: Part[], params: NestParams, onProgress: (p: NestProgress) => void): Promise<NestResult>;
  stopNest(): void;
  exportSheetDxf(sheet: SheetLayout, parts: Part[]): string;
  exportAllDxf(sheets: SheetLayout[], parts: Part[]): string;
  exportGcode(sheet: SheetLayout, parts: Part[], opts: GcodeOptions): string;
  sheetFileName(sheet: SheetLayout, ext: string): string;
  downloadText(name: string, content: string): void;
  downloadZip(zipName: string, files: { name: string; content: string }[]): Promise<void>;
}

const LS_KEY = 'catphoi.settings.v1';

interface Settings {
  sheetW: number; sheetH: number; gap: number; margin: number;
  rotationStep: number; allowMirror: boolean; timeLimitSec: number; unitScale: number;
  gcode: GcodeOptions;
}

const DEFAULT_SETTINGS: Settings = {
  sheetW: DEFAULT_NEST_PARAMS.sheetW,
  sheetH: DEFAULT_NEST_PARAMS.sheetH,
  gap: DEFAULT_NEST_PARAMS.gap,
  margin: DEFAULT_NEST_PARAMS.margin,
  rotationStep: DEFAULT_NEST_PARAMS.rotationStep,
  allowMirror: DEFAULT_NEST_PARAMS.allowMirror,
  timeLimitSec: 60,
  unitScale: 1,
  gcode: { ...DEFAULT_GCODE_OPTIONS },
};

function loadSettings(): Settings {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return { ...DEFAULT_SETTINGS, gcode: { ...DEFAULT_GCODE_OPTIONS } };
    const v = JSON.parse(raw);
    return { ...DEFAULT_SETTINGS, ...v, gcode: { ...DEFAULT_GCODE_OPTIONS, ...(v.gcode || {}) } };
  } catch {
    return { ...DEFAULT_SETTINGS, gcode: { ...DEFAULT_GCODE_OPTIONS } };
  }
}

function saveSettings(s: Settings): void {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(s));
  } catch {
    /* chế độ riêng tư / hết dung lượng — bỏ qua, không làm hỏng app */
  }
}

const el = <K extends keyof HTMLElementTagNameMap>(
  tag: K, cls?: string, html?: string
): HTMLElementTagNameMap[K] => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
};

const fmtM2 = (mm2: number) => (mm2 / 1e6).toFixed(2);
const fmtPct = (v: number) => (v * 100).toFixed(1) + '%';

export function mountApp(root: HTMLElement, services: AppServices): void {
  let settings = loadSettings();
  let parts: Part[] = [];
  let lastFile: File | null = null;
  let result: NestResult | null = null;
  let running = false;

  root.innerHTML = '';

  // ── thanh đầu ───────────────────────────────────────────────────────────
  const topbar = el('div', 'topbar');
  topbar.appendChild(el('h1', undefined, 'XẾP PHÔI TÔN'));
  topbar.appendChild(el('div', 'sub', 'Chạy hoàn toàn trên máy bạn · file không gửi đi đâu'));
  const drop = el('div', 'drop', 'Kéo file <b>DXF</b> vào đây hoặc bấm để chọn');
  const fileInput = el('input');
  fileInput.type = 'file';
  fileInput.accept = '.dxf,.DXF';
  fileInput.className = 'hidden';
  topbar.appendChild(drop);
  topbar.appendChild(fileInput);
  root.appendChild(topbar);

  const main = el('div', 'main');
  const side = el('div', 'side');
  const content = el('div', 'content');
  main.appendChild(side);
  main.appendChild(content);
  root.appendChild(main);

  // ── cột trái: thông số ──────────────────────────────────────────────────
  side.appendChild(el('h2', undefined, 'Thông số'));
  const grid = el('div', 'grid2');
  side.appendChild(grid);

  let uid = 0;
  const numField = (label: string, value: number, min: number, step: number, on: (v: number) => void) => {
    const wrap = el('div');
    const id = `f${++uid}`;
    const lb = el('label', 'f', label);
    lb.setAttribute('for', id);
    wrap.appendChild(lb);
    const inp = el('input');
    inp.id = id;
    inp.name = id;
    inp.type = 'number';
    inp.value = String(value);
    inp.min = String(min);
    inp.step = String(step);
    inp.addEventListener('change', () => {
      const v = parseFloat(inp.value);
      if (!Number.isFinite(v) || v < min) {
        inp.value = String(min);
        on(min);
      } else on(v);
      saveSettings(settings);
    });
    wrap.appendChild(inp);
    grid.appendChild(wrap);
    return inp;
  };

  const inW = numField('Bề rộng tấm (mm)', settings.sheetW, 100, 10, (v) => { settings.sheetW = v; });
  const inH = numField('Chiều dài tấm (mm)', settings.sheetH, 100, 10, (v) => { settings.sheetH = v; });
  const inGap = numField('Khe giữa chi tiết (mm)', settings.gap, 0, 1, (v) => { settings.gap = v; });
  const inMargin = numField('Lề mép tấm (mm)', settings.margin, 0, 1, (v) => { settings.margin = v; });

  const rotWrap = el('div');
  const rotLb = el('label', 'f', 'Bước xoay');
  rotLb.setAttribute('for', 'sel-rot');
  rotWrap.appendChild(rotLb);
  const selRot = el('select');
  selRot.id = 'sel-rot';
  selRot.name = 'sel-rot';
  for (const v of [1, 2, 5, 15, 90]) {
    const o = el('option');
    o.value = String(v);
    o.textContent = `${v}°`;
    selRot.appendChild(o);
  }
  selRot.value = String(settings.rotationStep);
  selRot.addEventListener('change', () => { settings.rotationStep = parseInt(selRot.value, 10); saveSettings(settings); });
  rotWrap.appendChild(selRot);
  grid.appendChild(rotWrap);

  const inTime = numField('Thời gian tối đa (giây)', settings.timeLimitSec, 3, 1, (v) => { settings.timeLimitSec = v; });

  const unitWrap = el('div');
  const unitLb = el('label', 'f', 'Đơn vị file');
  unitLb.setAttribute('for', 'sel-unit');
  unitWrap.appendChild(unitLb);
  const selUnit = el('select');
  selUnit.id = 'sel-unit';
  selUnit.name = 'sel-unit';
  for (const [v, t] of [[1, 'mm'], [10, 'cm'], [1000, 'm']] as [number, string][]) {
    const o = el('option');
    o.value = String(v);
    o.textContent = t;
    selUnit.appendChild(o);
  }
  selUnit.value = String(settings.unitScale);
  selUnit.addEventListener('change', () => {
    settings.unitScale = parseInt(selUnit.value, 10);
    saveSettings(settings);
    if (lastFile) void loadFile(lastFile);
  });
  unitWrap.appendChild(selUnit);
  grid.appendChild(unitWrap);

  const mirrorWrap = el('div', 'chk');
  const chkMirror = el('input');
  chkMirror.type = 'checkbox';
  chkMirror.checked = settings.allowMirror;
  chkMirror.id = 'chk-mirror';
  chkMirror.addEventListener('change', () => { settings.allowMirror = chkMirror.checked; saveSettings(settings); });
  const mirrorLabel = el('label');
  mirrorLabel.setAttribute('for', 'chk-mirror');
  mirrorLabel.innerHTML = 'Lật gương <small>(sườn mạn trái/phải là 2 chi tiết khác nhau)</small>';
  mirrorWrap.appendChild(chkMirror);
  mirrorWrap.appendChild(mirrorLabel);
  side.appendChild(mirrorWrap);

  const btnReset = el('button', 'sm', 'Khôi phục mặc định');
  btnReset.addEventListener('click', () => {
    settings = { ...DEFAULT_SETTINGS, gcode: { ...DEFAULT_GCODE_OPTIONS } };
    saveSettings(settings);
    inW.value = String(settings.sheetW);
    inH.value = String(settings.sheetH);
    inGap.value = String(settings.gap);
    inMargin.value = String(settings.margin);
    inTime.value = String(settings.timeLimitSec);
    selRot.value = String(settings.rotationStep);
    selUnit.value = String(settings.unitScale);
    chkMirror.checked = settings.allowMirror;
    syncGcodeInputs();
  });
  side.appendChild(btnReset);

  // ── cột trái: danh sách chi tiết ────────────────────────────────────────
  const partsTitle = el('h2', undefined, 'Chi tiết (0)');
  side.appendChild(partsTitle);
  const selRow = el('div', 'dlrow');
  const btnAll = el('button', 'sm', 'Chọn tất cả');
  const btnNone = el('button', 'sm', 'Bỏ chọn tất cả');
  btnAll.addEventListener('click', () => { parts.forEach((p) => { if (p.fitsSheet) p.enabled = true; }); renderParts(); });
  btnNone.addEventListener('click', () => { parts.forEach((p) => { p.enabled = false; }); renderParts(); });
  selRow.appendChild(btnAll);
  selRow.appendChild(btnNone);
  side.appendChild(selRow);
  const partsBox = el('div', 'parts');
  side.appendChild(partsBox);
  const partsTotal = el('div', 'runinfo');
  side.appendChild(partsTotal);

  // ── cột phải ────────────────────────────────────────────────────────────
  const errBox = el('div', 'err hidden');
  content.appendChild(errBox);

  const runbar = el('div', 'runbar');
  const btnNest = el('button', 'primary', 'XẾP');
  const btnStop = el('button', undefined, 'DỪNG');
  btnStop.disabled = true;
  const bar = el('div', 'bar');
  const barFill = el('i');
  bar.appendChild(barFill);
  const runInfo = el('div', 'runinfo', '');
  runbar.appendChild(btnNest);
  runbar.appendChild(btnStop);
  runbar.appendChild(bar);
  runbar.appendChild(runInfo);
  content.appendChild(runbar);

  const note = el('div', 'note',
    'G-code chỉ là tham khảo — chạy thử không tải trước khi cắt thật. ' +
    'Khuyến nghị: nạp DXF vào FastCAM như cũ. Tool <b>không bù kerf</b>, hãy bù trên máy/FastCAM.');
  content.appendChild(note);

  const dlRow = el('div', 'dlrow hidden');
  const btnZipDxf = el('button', undefined, 'Tải tất cả DXF (.zip)');
  const btnOneDxf = el('button', undefined, 'Tải 1 file DXF nhiều tấm');
  const btnZipNc = el('button', undefined, 'Tải tất cả G-code (.zip)');
  const btnGset = el('button', undefined, '⚙ Cài đặt G-code');
  dlRow.appendChild(btnZipDxf);
  dlRow.appendChild(btnOneDxf);
  dlRow.appendChild(btnZipNc);
  dlRow.appendChild(btnGset);
  content.appendChild(dlRow);

  // panel cài đặt G-code
  const gpanel = el('div', 'gpanel hidden');
  gpanel.innerHTML = '<b>Cài đặt G-code</b>';
  const ggrid = el('div', 'grid2');
  gpanel.appendChild(ggrid);
  const gField = (label: string, type: 'text' | 'number', get: () => string, set: (v: string) => void) => {
    const w = el('div');
    const id = `g${++uid}`;
    const lb = el('label', 'f', label);
    lb.setAttribute('for', id);
    w.appendChild(lb);
    const i = el('input');
    i.id = id;
    i.name = id;
    i.type = type;
    i.value = get();
    i.addEventListener('change', () => { set(i.value); saveSettings(settings); });
    w.appendChild(i);
    ggrid.appendChild(w);
    return i;
  };
  const gOn = gField('Mã bật mỏ', 'text', () => settings.gcode.torchOn, (v) => { settings.gcode.torchOn = v.trim() || 'M07'; });
  const gOff = gField('Mã tắt mỏ', 'text', () => settings.gcode.torchOff, (v) => { settings.gcode.torchOff = v.trim() || 'M08'; });
  const gFeed = gField('Tốc độ cắt (mm/phút)', 'number', () => String(settings.gcode.feedRate), (v) => { settings.gcode.feedRate = Math.max(1, parseFloat(v) || 1500); });
  const gLead = gField('Lead-in (mm)', 'number', () => String(settings.gcode.leadIn), (v) => { settings.gcode.leadIn = Math.max(0, parseFloat(v) || 0); });
  const gExtWrap = el('div');
  const gExtLb = el('label', 'f', 'Đuôi file');
  gExtLb.setAttribute('for', 'sel-ext');
  gExtWrap.appendChild(gExtLb);
  const gExt = el('select');
  gExt.id = 'sel-ext';
  gExt.name = 'sel-ext';
  for (const e2 of ['nc', 'txt', 'cnc']) {
    const o = el('option');
    o.value = e2;
    o.textContent = '.' + e2;
    gExt.appendChild(o);
  }
  gExt.value = settings.gcode.extension;
  gExt.addEventListener('change', () => { settings.gcode.extension = gExt.value as GcodeOptions['extension']; saveSettings(settings); });
  gExtWrap.appendChild(gExt);
  ggrid.appendChild(gExtWrap);
  const gNWrap = el('div', 'chk');
  const gN = el('input');
  gN.type = 'checkbox';
  gN.id = 'chk-n';
  gN.checked = settings.gcode.lineNumbers;
  gN.addEventListener('change', () => { settings.gcode.lineNumbers = gN.checked; saveSettings(settings); });
  const gNL = el('label');
  gNL.setAttribute('for', 'chk-n');
  gNL.textContent = 'Đánh số dòng N';
  gNWrap.appendChild(gN);
  gNWrap.appendChild(gNL);
  gpanel.appendChild(gNWrap);
  content.appendChild(gpanel);
  btnGset.addEventListener('click', () => gpanel.classList.toggle('hidden'));
  function syncGcodeInputs(): void {
    gOn.value = settings.gcode.torchOn;
    gOff.value = settings.gcode.torchOff;
    gFeed.value = String(settings.gcode.feedRate);
    gLead.value = String(settings.gcode.leadIn);
    gExt.value = settings.gcode.extension;
    gN.checked = settings.gcode.lineNumbers;
  }

  const summary = el('div', 'summary');
  content.appendChild(summary);
  const sheetsBox = el('div');
  content.appendChild(sheetsBox);

  const hint = el('div', 'hint');
  hint.innerHTML =
    '<b>Dùng trong 3 bước</b><ol>' +
    '<li>Kéo file <b>.dxf</b> (AutoCAD Save As DXF) vào ô trên cùng.</li>' +
    '<li>Xem lại danh sách chi tiết bên trái, chỉnh số lượng nếu cần, rồi bấm <b>XẾP</b>.</li>' +
    '<li>Bấm <b>Tải DXF</b> của từng tấm (hoặc tải cả gói .zip) rồi nạp vào FastCAM như mọi khi.</li>' +
    '</ol>';
  content.appendChild(hint);

  // ── hành vi ─────────────────────────────────────────────────────────────
  function showError(msg: string): void {
    errBox.textContent = msg;
    errBox.classList.remove('hidden');
  }
  function clearError(): void {
    errBox.textContent = '';
    errBox.classList.add('hidden');
  }

  function currentParams(): NestParams {
    return {
      sheetW: settings.sheetW,
      sheetH: settings.sheetH,
      gap: settings.gap,
      margin: settings.margin,
      rotationStep: settings.rotationStep,
      allowMirror: settings.allowMirror,
      timeLimitMs: Math.round(settings.timeLimitSec * 1000),
      gridCell: DEFAULT_NEST_PARAMS.gridCell,
      seed: DEFAULT_NEST_PARAMS.seed,
    };
  }

  function renderParts(): void {
    partsBox.innerHTML = '';
    partsTitle.textContent = `Chi tiết (${parts.length})`;
    for (const p of parts) {
      const row = el('div', 'part' + (p.fitsSheet ? '' : ' bad'));
      const chk = el('input');
      chk.type = 'checkbox';
      chk.id = `en-${p.id}`;
      chk.name = `en-${p.id}`;
      chk.setAttribute('aria-label', `Chọn chi tiết ${p.id}`);
      chk.checked = p.enabled && p.fitsSheet;
      chk.disabled = !p.fitsSheet;
      chk.addEventListener('change', () => { p.enabled = chk.checked; updateTotals(); });
      row.appendChild(chk);

      const cv = el('canvas');
      row.appendChild(cv);

      const w = Math.round(p.bbox.maxX - p.bbox.minX);
      const h = Math.round(p.bbox.maxY - p.bbox.minY);
      const meta = el('div', 'meta');
      meta.innerHTML = `<b>${p.id}</b> ${w}×${h}<span>${fmtM2(p.area)} m² · ${p.vertexCount} đỉnh` +
        (p.fitsSheet ? '' : ' · <i class="bad-tag">Không vừa tấm</i>') + '</span>';
      row.appendChild(meta);

      const qty = el('input');
      qty.type = 'number';
      qty.min = '1';
      qty.value = String(p.qty);
      qty.title = 'Số lượng';
      qty.setAttribute('aria-label', `Số lượng ${p.id}`);
      qty.name = `qty-${p.id}`;
      qty.id = `qty-${p.id}`;
      qty.addEventListener('change', () => {
        const v = Math.max(1, Math.round(parseFloat(qty.value) || 1));
        qty.value = String(v);
        p.qty = v;
        updateTotals();
      });
      row.appendChild(qty);
      partsBox.appendChild(row);
      drawThumb(cv, p);
    }
    updateTotals();
  }

  function updateTotals(): void {
    const on = parts.filter((p) => p.enabled && p.fitsSheet);
    const n = on.reduce((s, p) => s + p.qty, 0);
    const a = on.reduce((s, p) => s + p.area * p.qty, 0);
    partsTotal.textContent = `Đã chọn ${n} chi tiết · ${fmtM2(a)} m²`;
    btnNest.disabled = running || n === 0;
  }

  function usedLength(sheet: SheetLayout): number {
    let max = 0;
    const byId = new Map(parts.map((p) => [p.id, p]));
    for (const pl of sheet.placements) {
      const p = byId.get(pl.partId);
      if (!p) continue;
      max = Math.max(max, ringBBox(applyPlacementRing(p.rings[0], pl)).maxY);
    }
    return max;
  }

  function renderResult(r: NestResult | null): void {
    result = r;
    sheetsBox.innerHTML = '';
    if (!r || r.sheets.length === 0) {
      summary.textContent = '';
      dlRow.classList.add('hidden');
      return;
    }
    hint.classList.add('hidden');
    dlRow.classList.remove('hidden');
    summary.innerHTML = `Dùng <b>${r.sheets.length} tấm</b> · tổng sử dụng tôn <b>${fmtPct(r.utilization)}</b>` +
      (r.unplaced.length ? ` · <span style="color:#c0392b">chưa xếp được: ${r.unplaced.join(', ')}</span>` : '');

    const boxW = Math.max(320, content.clientWidth - 40);
    for (const sheet of r.sheets) {
      const card = el('div', 'sheet');
      const head = el('header');
      head.appendChild(el('h3', undefined, `Tấm ${sheet.index + 1} — ${Math.round(sheet.width)}×${Math.round(sheet.height)}mm`));
      const pct = el('span', 'pct', fmtPct(sheet.utilization));
      head.appendChild(pct);
      head.appendChild(el('span', 'rest',
        `${sheet.placements.length} chi tiết · đã dùng ${Math.round(usedLength(sheet))}mm chiều dài · còn thừa ${Math.max(0, Math.round(sheet.height - usedLength(sheet)))}mm`));
      const bDxf = el('button', 'sm', 'Tải DXF tấm này');
      bDxf.addEventListener('click', () => {
        services.downloadText(services.sheetFileName(sheet, 'dxf'), services.exportSheetDxf(sheet, parts));
      });
      const bNc = el('button', 'sm', 'Tải G-code tấm này');
      bNc.addEventListener('click', () => {
        services.downloadText(
          services.sheetFileName(sheet, settings.gcode.extension),
          services.exportGcode(sheet, parts, settings.gcode)
        );
      });
      head.appendChild(bDxf);
      head.appendChild(bNc);
      card.appendChild(head);
      const cv = el('canvas');
      card.appendChild(cv);
      sheetsBox.appendChild(card);
      const h = Math.max(70, Math.round((boxW - 20) * sheet.width / sheet.height) + 16);
      drawSheet(cv, sheet, parts, { cssWidth: boxW - 20, cssHeight: h });
    }
  }

  btnZipDxf.addEventListener('click', () => {
    if (!result) return;
    void services.downloadZip('xep-phoi-dxf.zip', result.sheets.map((s) => ({
      name: services.sheetFileName(s, 'dxf'),
      content: services.exportSheetDxf(s, parts),
    })));
  });
  btnOneDxf.addEventListener('click', () => {
    if (!result) return;
    services.downloadText('tat-ca-tam.dxf', services.exportAllDxf(result.sheets, parts));
  });
  btnZipNc.addEventListener('click', () => {
    if (!result) return;
    void services.downloadZip('xep-phoi-gcode.zip', result.sheets.map((s) => ({
      name: services.sheetFileName(s, settings.gcode.extension),
      content: services.exportGcode(s, parts, settings.gcode),
    })));
  });

  async function loadFile(file: File): Promise<void> {
    clearError();
    if (/\.dwg$/i.test(file.name)) {
      showError('File .dwg chưa hỗ trợ. Hãy Save As sang DXF trong AutoCAD rồi thử lại.');
      return;
    }
    lastFile = file;
    drop.innerHTML = `Đang đọc <b>${file.name}</b>…`;
    btnNest.disabled = true;
    try {
      const r = await services.parseFile(
        file,
        {
          unitScale: settings.unitScale,
          sheetWidth: settings.sheetW,
          sheetHeight: settings.sheetH,
        },
        (f, label) => { drop.innerHTML = `${label} <b>${Math.round(f * 100)}%</b>`; }
      );
      parts = r.parts;
      renderParts();
      renderResult(null);
      hint.classList.remove('hidden');
      drop.innerHTML = `<b>${file.name}</b> — ${r.parts.length} chi tiết · bấm để chọn file khác`;
      if (r.warnings.length) showError(r.warnings.join(' '));
    } catch (e) {
      drop.innerHTML = 'Kéo file <b>DXF</b> vào đây hoặc bấm để chọn';
      showError(e instanceof Error ? e.message : 'Không đọc được file.');
    }
    updateTotals();
  }

  drop.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    const f = fileInput.files?.[0];
    if (f) void loadFile(f);
  });
  for (const ev of ['dragenter', 'dragover']) {
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); });
  }
  for (const ev of ['dragleave', 'drop']) {
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('over'); });
  }
  drop.addEventListener('drop', (e) => {
    const f = (e as DragEvent).dataTransfer?.files?.[0];
    if (f) void loadFile(f);
  });

  btnNest.addEventListener('click', async () => {
    const chosen = parts.filter((p) => p.enabled && p.fitsSheet);
    if (chosen.length === 0) {
      showError('Chưa chọn chi tiết nào để xếp.');
      return;
    }
    clearError();
    running = true;
    btnNest.disabled = true;
    btnStop.disabled = false;
    barFill.style.width = '0%';
    const t0 = Date.now();
    try {
      const r = await services.startNest(parts, currentParams(), (p) => {
        barFill.style.width = `${Math.round(p.fraction * 100)}%`;
        runInfo.textContent = `${Math.round(p.elapsedMs / 1000)}s · ${p.iterations} phương án` +
          (p.best ? ` · tốt nhất ${p.best.sheets.length} tấm (${fmtPct(p.best.utilization)})` : '');
        if (p.best) renderResult(p.best);
      });
      renderResult(r);
      barFill.style.width = '100%';
      runInfo.textContent = `Xong sau ${Math.round((Date.now() - t0) / 1000)}s · ${r.iterations} phương án`;
    } catch (e) {
      showError(e instanceof Error ? e.message : 'Lỗi khi xếp.');
    } finally {
      running = false;
      btnStop.disabled = true;
      updateTotals();
    }
  });

  btnStop.addEventListener('click', () => {
    btnStop.disabled = true;
    services.stopNest();
  });

  let resizeTimer = 0;
  window.addEventListener('resize', () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => renderResult(result), 150);
  });

  syncGcodeInputs();
  updateTotals();
}
