/**
 * Màn hình duy nhất của tool "Xếp phôi tôn".
 * Toàn bộ chữ tiếng Việt có dấu. Bố cục 2 cột, vừa màn 1366x768 không cuộn ngang.
 */
import './styles.css';
import type {
  GcodeOptions, NestParams, NestProgress, NestResult, Part, ParseOptions, ParseResult, SheetLayout,
} from '../types';
import { DEFAULT_GCODE_OPTIONS, DEFAULT_NEST_PARAMS, applyPlacementRing, ringBBox } from '../types';
import { drawSheet, drawThumb, displayName } from './render';
import { exportLabels } from './labels';
import { startMultiNest } from './nest-multi';
import { MAX_PLANS } from './nest-multi-core';
import {
  pickPlan, planAllDxf, planAllFileName, planFileName, planSheetDxf, planSheetGcode,
  planZipFiles, planZipName,
} from './download';
import { cutsFromSheet } from '../remnant/sheetspec';

export interface AppServices {
  parseFile(file: File, opts: ParseOptions, onProgress: (f: number, label: string) => void): Promise<ParseResult>;
  /**
   * ⚠ Từ VIỆC 1, màn hình KHÔNG gọi hàm này nữa — nó chỉ trả về MỘT phương án,
   * mà founder cần lật qua tối đa 5. Đường xếp mới nằm ở src/ui/nest-multi.ts.
   * Giữ lại trong hợp đồng để src/main.ts (file của thợ khác) vẫn biên dịch được.
   */
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
/** Tên chi tiết do người dùng tự đặt: { "<tên file>": { "P0": "Sườn 15 mạn" } }. */
const LS_NAMES_KEY = 'catphoi.names.v1';

interface Settings {
  sheetW: number; sheetH: number; gap: number; margin: number;
  rotationStep: number; allowMirror: boolean; timeLimitSec: number; unitScale: number;
  /** Bù kerf (bề rộng mạch cắt), mm. 0 = KHÔNG bù (mặc định). */
  kerf: number;
  gcode: GcodeOptions;
}

/** Thông số hiện tại trên màn hình — panel kho tôn thừa (người khác làm) đọc qua đây. */
export interface NestOptionsSnapshot extends NestParams {
  /** Khe người dùng nhập, mm. */
  gapInput: number;
  /** Bù kerf, mm. */
  kerf: number;
  /** Khe hiệu dụng khi xếp = khe + kerf (để 2 đường cắt đã nở không chạm nhau). */
  effectiveGap: number;
  unitScale: number;
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
  kerf: 0,
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

type NameStore = Record<string, Record<string, string>>;

function loadNameStore(): NameStore {
  try {
    const raw = localStorage.getItem(LS_NAMES_KEY);
    if (!raw) return {};
    const v = JSON.parse(raw);
    return v && typeof v === 'object' ? (v as NameStore) : {};
  } catch {
    return {};
  }
}

function saveNameStore(store: NameStore): void {
  try {
    localStorage.setItem(LS_NAMES_KEY, JSON.stringify(store));
  } catch {
    /* bỏ qua — tên tự đặt chỉ là tiện ích, không được làm hỏng app */
  }
}

/**
 * Thông số hiện tại của màn hình. Mặc định khi chưa mount: giá trị gốc.
 * Panel kho tôn thừa (do người khác viết, cắm vào #remnant-slot) gọi hàm này.
 */
let readNestOptions: (() => NestOptionsSnapshot) | null = null;

export function getNestOptions(): NestOptionsSnapshot {
  if (readNestOptions) return readNestOptions();
  const d = DEFAULT_SETTINGS;
  return {
    sheetW: d.sheetW, sheetH: d.sheetH, gap: d.gap, margin: d.margin,
    rotationStep: d.rotationStep, allowMirror: d.allowMirror,
    timeLimitMs: Math.round(d.timeLimitSec * 1000),
    gridCell: DEFAULT_NEST_PARAMS.gridCell, seed: DEFAULT_NEST_PARAMS.seed,
    gapInput: d.gap, kerf: d.kerf, effectiveGap: d.gap + d.kerf, unitScale: d.unitScale,
  };
}

/**
 * API mà module kho tôn thừa (src/remnant) treo lên window khi trang tải xong.
 * Khai ở đây cho gọn thay vì import chéo module — nút XẾP chỉ cần 2 hàm này.
 */
interface RemnantBridge {
  getSelected(): { id: string; name: string }[];
  nestWithSelected(
    parts: Part[],
    onProgress?: (p: NestProgress) => void,
    shouldStop?: () => boolean
  ): Promise<NestResult>;
  /** VIỆC 1 — bản nhiều phương án. Có từ bản kho tôn thừa mới. */
  nestMultiWithSelected?(
    parts: Part[],
    onProgress?: (p: NestProgress) => void,
    shouldStop?: () => boolean,
    count?: number
  ): Promise<{ plans: NestResult[] }>;
  /** VIỆC 3 — lưu một tấm vừa xếp vào kho, giữ nguyên khổ + các lỗ vừa cắt. */
  saveFromSheet?(args: {
    name: string;
    sheetWidthMm: number;
    sheetLengthMm: number;
    cuts: import('../types').Ring[];
    note?: string;
  }): Promise<{ id: string; name: string }>;
}

/** Trả API kho tôn thừa nếu module đó đã nạp và đúng hình dạng, không thì null. */
function remnantBridge(): RemnantBridge | null {
  const api = (globalThis as Record<string, unknown>).catphoiRemnant as RemnantBridge | undefined;
  if (!api) return null;
  return typeof api.getSelected === 'function' && typeof api.nestWithSelected === 'function' ? api : null;
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
  /** Tên tự đặt của file đang mở: { "P0": "Sườn 15 mạn" }. */
  let names: Record<string, string> = {};
  let nameStore: NameStore = loadNameStore();
  let fileKey = '';
  /**
   * VIỆC 1 — tối đa 5 phương án xếp; plans[0] là tốt nhất, mở mặc định ở đó.
   * MỌI nút tải đều đi qua `planIndex` này (xem src/ui/download.ts).
   */
  let plans: NestResult[] = [];
  let planIndex = 0;
  let running = false;
  /** Người dùng đã bấm DỪNG cho lượt xếp đang chạy chưa (đường tôn thừa hỏi cờ này). */
  let stopRequested = false;

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
  // Bù kerf: MẶC ĐỊNH 0 = không bù (giữ đúng quy trình cũ: bù bên FastCAM/máy).
  const inKerf = numField('Bù kerf (mm)', settings.kerf, 0, 0.1, (v) => {
    settings.kerf = v;
    updateNote();
    renderCurrent();
  });
  inKerf.title = 'Bề rộng mạch cắt. 0 = không bù (bù bên FastCAM/máy như cũ).';

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
    inKerf.value = String(settings.kerf);
    selRot.value = String(settings.rotationStep);
    selUnit.value = String(settings.unitScale);
    chkMirror.checked = settings.allowMirror;
    syncGcodeInputs();
    updateNote();
  });
  side.appendChild(btnReset);

  // Chỗ cắm sẵn cho panel "kho tôn thừa" (người khác làm) — để trống, không tự viết.
  const remnantSlot = el('div');
  remnantSlot.id = 'remnant-slot';
  side.appendChild(remnantSlot);

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

  const note = el('div', 'note');
  content.appendChild(note);
  function updateNote(): void {
    const base = 'G-code chỉ là tham khảo — chạy thử không tải trước khi cắt thật. ' +
      'Khuyến nghị: nạp DXF vào FastCAM như cũ. ';
    note.innerHTML = settings.kerf > 0
      ? base + `Tool <b>ĐÃ BÙ KERF ${settings.kerf}mm trong file</b> (bao ngoài nở ${(settings.kerf / 2).toFixed(2)}mm, ` +
        `lỗ thu vào ${(settings.kerf / 2).toFixed(2)}mm) — <b>PHẢI TẮT bù kerf bên FastCAM/máy</b>, ` +
        'kẻo bù hai lần làm chi tiết hụt.'
      : base + 'Tool <b>không bù kerf</b> (ô "Bù kerf" đang để 0), hãy bù trên máy/FastCAM như cũ.';
  }

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

  // ── VIỆC 1: thanh lật qua lại giữa các phương án ────────────────────────
  const planbar = el('div', 'planbar hidden');
  const btnPrevPlan = el('button', 'sm', '◀ Lùi');
  btnPrevPlan.title = 'Xem phương án trước';
  const planLabel = el('span', 'plan-lb', '');
  const btnNextPlan = el('button', 'sm', 'Tiến ▶');
  btnNextPlan.title = 'Xem phương án sau';
  const planNote = el('span', 'plan-note', '');
  planbar.appendChild(btnPrevPlan);
  planbar.appendChild(planLabel);
  planbar.appendChild(btnNextPlan);
  planbar.appendChild(planNote);
  content.appendChild(planbar);

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

  /**
   * Khe hiệu dụng khi xếp = khe người dùng nhập + kerf. Vì đường cắt của 2 chi tiết
   * cạnh nhau mỗi bên nở ra kerf/2, không cộng thêm thì 2 vệt cắt chạm nhau.
   * Engine nest không có tham số kerf nên cộng ở đây trước khi gọi.
   */
  function effectiveGap(): number {
    return settings.gap + Math.max(0, settings.kerf);
  }

  function currentParams(): NestParams {
    return {
      sheetW: settings.sheetW,
      sheetH: settings.sheetH,
      gap: effectiveGap(),
      margin: settings.margin,
      rotationStep: settings.rotationStep,
      allowMirror: settings.allowMirror,
      timeLimitMs: Math.round(settings.timeLimitSec * 1000),
      gridCell: DEFAULT_NEST_PARAMS.gridCell,
      seed: DEFAULT_NEST_PARAMS.seed,
    };
  }

  function partsById(): Map<string, Part> {
    return new Map(parts.map((p) => [p.id, p]));
  }

  function persistNames(): void {
    if (!fileKey) return;
    if (Object.keys(names).length) nameStore[fileKey] = { ...names };
    else delete nameStore[fileKey];
    saveNameStore(nameStore);
  }

  /**
   * Tuỳ chọn xuất file: tên chi tiết + bù kerf.
   * VIỆC 4 — tên ghi vào DXF / G-code là tên ĐẦY ĐỦ "P3 · mạn 15" (bộ xuất tự
   * bỏ dấu), chứ không chỉ phần tên gõ thêm. Mã P không bao giờ mất khỏi file.
   */
  function exportExtras(): { labels: Record<string, string>; kerf: number } {
    return { labels: exportLabels(parts, names), kerf: Math.max(0, settings.kerf) };
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

      // KÍCH THƯỚC = dài × bề rộng nhỏ nhất khi xoay (khung bao nhỏ nhất xoay được).
      // KHÔNG dùng bbox theo trục toạ độ gốc: thanh cong nằm chéo nên bbox cho số sai
      // (P0 ra 3409×3996 trong khi thanh thật 5253×1172).
      const L = Math.round(p.maxLength);
      const W = Math.round(p.minWidth);
      const meta = el('div', 'meta');
      const nameInp = el('input', 'pname');
      nameInp.type = 'text';
      nameInp.id = `name-${p.id}`;
      nameInp.name = `name-${p.id}`;
      nameInp.value = names[p.id] ?? '';
      nameInp.placeholder = p.id;
      nameInp.title = `Tên chi tiết (mặc định ${p.id}) — hiện trên preview, ghi vào DXF và G-code`;
      nameInp.setAttribute('aria-label', `Tên chi tiết ${p.id}`);
      const commitName = () => {
        const v = nameInp.value.trim();
        if (v) names[p.id] = v;
        else delete names[p.id];
        persistNames();
        dims.title = `${displayName(p, names)} · dài ${L}mm × bề rộng nhỏ nhất khi xoay ${W}mm`;
        renderCurrent();
      };
      nameInp.addEventListener('change', commitName);
      nameInp.addEventListener('blur', commitName);
      meta.appendChild(nameInp);
      const dims = el('span');
      dims.innerHTML = `${L}×${W}mm · ${fmtM2(p.area)}m² · ${p.vertexCount} đỉnh` +
        (p.fitsSheet ? '' : ' · <i class="bad-tag">Không vừa tấm</i>');
      dims.title = `${displayName(p, names)} · dài ${L}mm × bề rộng nhỏ nhất khi xoay ${W}mm`;
      meta.appendChild(dims);
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

  /** Phương án đang xem. */
  function currentPlan(): NestResult | null {
    return pickPlan(plans, planIndex);
  }

  /**
   * Nạp danh sách phương án mới và vẽ lại màn hình.
   * Mặc định mở ở phương án 1 (tốt nhất) — đúng yêu cầu của founder.
   */
  function setPlans(list: NestResult[], index = 0): void {
    plans = list.filter((p) => p && p.sheets.length > 0);
    planIndex = plans.length ? Math.max(0, Math.min(plans.length - 1, index)) : 0;
    renderPlanBar();
    renderCurrent();
  }

  /** Giữ nguyên tên cũ để các chỗ gọi lẻ vẫn chạy: một kết quả = một phương án. */
  function renderResult(r: NestResult | null): void {
    setPlans(r ? [r] : [], 0);
  }

  function renderPlanBar(): void {
    if (plans.length === 0) {
      planbar.classList.add('hidden');
      return;
    }
    planbar.classList.remove('hidden');
    const cur = currentPlan();
    planLabel.innerHTML = `Phương án <b>${planIndex + 1}/${plans.length}</b>`
      + (cur ? ` · <b>${cur.sheets.length} tấm</b> · dùng tôn <b>${fmtPct(cur.utilization)}</b>` : '');
    btnPrevPlan.disabled = plans.length < 2;
    btnNextPlan.disabled = plans.length < 2;
    planNote.textContent = plans.length < 2
      ? 'Chỉ tìm được 1 phương án — thử tăng "Thời gian tối đa" để có thêm.'
      : 'File tải về luôn đúng phương án đang xem.';
  }

  function stepPlan(delta: number): void {
    if (plans.length < 2) return;
    // Lật vòng: ở cuối bấm Tiến thì quay về đầu, khỏi cụt tay.
    planIndex = (planIndex + delta + plans.length) % plans.length;
    renderPlanBar();
    renderCurrent();
  }

  btnPrevPlan.addEventListener('click', () => stepPlan(-1));
  btnNextPlan.addEventListener('click', () => stepPlan(1));

  /**
   * VIỆC 3 — lưu tấm đang xem vào kho tôn thừa: giữ NGUYÊN KHỔ tấm và ghi lại
   * đúng các lỗ vừa cắt, để lần sau biết miếng thừa nằm ở góc nào.
   */
  async function saveSheetAsRemnant(sheet: SheetLayout): Promise<void> {
    const bridge = remnantBridge();
    if (!bridge || typeof bridge.saveFromSheet !== 'function') {
      showError('Panel kho tôn thừa chưa sẵn sàng — hãy tải lại trang rồi thử lại.');
      return;
    }
    const base = (lastFile?.name || 'lô').replace(/\.dxf$/i, '');
    const def = `thừa ${base} · tấm ${sheet.index + 1}`;
    const typed = window.prompt('Tên tấm thừa muốn lưu vào kho:', def);
    if (typed === null) return;
    try {
      const cuts = cutsFromSheet(sheet, partsById());
      await bridge.saveFromSheet({
        name: typed.trim() || def,
        sheetWidthMm: sheet.width,
        sheetLengthMm: sheet.height,
        cuts,
        note: `lưu từ phương án ${planIndex + 1}, ${cuts.length} chi tiết đã cắt`,
      });
      clearError();
    } catch (e) {
      showError(e instanceof Error ? e.message : 'Không lưu được tấm thừa.');
    }
  }

  function renderCurrent(): void {
    const r = currentPlan();
    sheetsBox.innerHTML = '';
    if (!r || r.sheets.length === 0) {
      summary.textContent = '';
      dlRow.classList.add('hidden');
      return;
    }
    hint.classList.add('hidden');
    dlRow.classList.remove('hidden');
    const rr = r as NestResult & { remnantsUsed?: { name: string }[]; newSheets?: number };
    summary.innerHTML = `Dùng <b>${r.sheets.length} tấm</b> · tổng sử dụng tôn <b>${fmtPct(r.utilization)}</b>` +
      (rr.remnantsUsed && rr.remnantsUsed.length
        ? ` · trong đó <b>${rr.remnantsUsed.length} tấm thừa</b> trong kho, mở thêm ${rr.newSheets ?? 0} tấm mới`
        : '') +
      (r.unplaced.length ? ` · <span style="color:#c0392b">chưa xếp được: ${r.unplaced.join(', ')}</span>` : '');

    const boxW = Math.max(320, content.clientWidth - 40);
    r.sheets.forEach((sheet, sheetIdx) => {
      const card = el('div', 'sheet');
      const head = el('header');
      // Tấm lấy từ kho tôn thừa mang thêm source/remnantName (src/remnant/plan.ts).
      const src = sheet as SheetLayout & { source?: string; remnantName?: string };
      const dims = `${Math.round(sheet.width)}×${Math.round(sheet.height)}mm`;
      head.appendChild(el('h3', undefined,
        src.source === 'remnant' && src.remnantName
          ? `Tấm ${sheet.index + 1} — TÔN THỪA "${src.remnantName}" ${dims}`
          : `Tấm ${sheet.index + 1} — ${dims}`));
      const pct = el('span', 'pct', fmtPct(sheet.utilization));
      head.appendChild(pct);
      head.appendChild(el('span', 'rest',
        `${sheet.placements.length} chi tiết · đã dùng ${Math.round(usedLength(sheet))}mm chiều dài · còn thừa ${Math.max(0, Math.round(sheet.height - usedLength(sheet)))}mm`));
      const bDxf = el('button', 'sm', 'Tải DXF tấm này');
      bDxf.addEventListener('click', () => {
        // Đi qua download.ts để CHẮC CHẮN lấy đúng phương án đang xem.
        services.downloadText(
          planFileName(planIndex, sheet, 'dxf'),
          planSheetDxf(plans, planIndex, sheetIdx, partsById(), exportExtras())
        );
      });
      const bNc = el('button', 'sm', 'Tải G-code tấm này');
      bNc.addEventListener('click', () => {
        services.downloadText(
          planFileName(planIndex, sheet, settings.gcode.extension),
          planSheetGcode(plans, planIndex, sheetIdx, partsById(), settings.gcode, exportExtras())
        );
      });
      const bKeep = el('button', 'sm', '+ Lưu tấm thừa');
      bKeep.title = 'Lưu tấm này vào kho tôn thừa — giữ nguyên khổ, kèm các lỗ vừa cắt';
      bKeep.addEventListener('click', () => void saveSheetAsRemnant(sheet));
      head.appendChild(bDxf);
      head.appendChild(bNc);
      head.appendChild(bKeep);
      card.appendChild(head);
      const cv = el('canvas');
      card.appendChild(cv);
      sheetsBox.appendChild(card);
      const h = Math.max(70, Math.round((boxW - 20) * sheet.width / sheet.height) + 16);
      drawSheet(cv, sheet, parts, { cssWidth: boxW - 20, cssHeight: h, labels: names });
    });
  }

  btnZipDxf.addEventListener('click', () => {
    if (!currentPlan()) return;
    void services.downloadZip(
      planZipName(planIndex, 'dxf'),
      planZipFiles(plans, planIndex, partsById(), 'dxf', settings.gcode, exportExtras())
    );
  });
  btnOneDxf.addEventListener('click', () => {
    if (!currentPlan()) return;
    services.downloadText(
      planAllFileName(planIndex),
      planAllDxf(plans, planIndex, partsById(), exportExtras())
    );
  });
  btnZipNc.addEventListener('click', () => {
    if (!currentPlan()) return;
    void services.downloadZip(
      planZipName(planIndex, 'gcode'),
      planZipFiles(plans, planIndex, partsById(), 'gcode', settings.gcode, exportExtras())
    );
  });

  async function loadFile(file: File): Promise<void> {
    clearError();
    if (/\.dwg$/i.test(file.name)) {
      showError('File .dwg chưa hỗ trợ. Hãy Save As sang DXF trong AutoCAD rồi thử lại.');
      return;
    }
    lastFile = file;
    // Tên tự đặt nhớ theo TÊN FILE + chỉ số chi tiết (P0, P1…).
    fileKey = file.name;
    nameStore = loadNameStore();
    names = { ...(nameStore[fileKey] || {}) };
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
    stopRequested = false;
    btnNest.disabled = true;
    btnStop.disabled = false;
    barFill.style.width = '0%';
    const t0 = Date.now();
    const onProgress = (p: NestProgress) => {
      barFill.style.width = `${Math.round(p.fraction * 100)}%`;
      runInfo.textContent = `${Math.round(p.elapsedMs / 1000)}s · ${p.iterations} phương án` +
        (p.best && p.best.sheets.length
          ? ` · tốt nhất ${p.best.sheets.length} tấm (${fmtPct(p.best.utilization)})`
          : '') +
        // Nhãn của đường xếp có tôn thừa ("Đang thử nhét vào tấm thừa …") — không
        // có nhãn này thì người dùng tưởng máy treo vì bộ đếm đứng yên cả chục giây.
        (p.label ? ` · ${p.label}` : '');
      if (p.best && p.best.sheets.length) renderResult(p.best);
    };
    try {
      // Có tích tấm thừa trong kho → xếp qua module kho tôn thừa (nhét tôn thừa
      // trước, hết chỗ mới mở tấm mới). Không tích → chạy y như cũ.
      const bridge = remnantBridge();
      const chosenRemnants = bridge ? bridge.getSelected() : [];
      let list: NestResult[];
      if (chosenRemnants.length > 0 && bridge && typeof bridge.nestMultiWithSelected === 'function') {
        runInfo.textContent = `Đang nhét vào ${chosenRemnants.length} tấm thừa đã chọn…`;
        const out = await bridge.nestMultiWithSelected(parts, onProgress, () => stopRequested, MAX_PLANS);
        list = out.plans;
      } else if (chosenRemnants.length > 0 && bridge) {
        // Bản kho tôn thừa cũ chỉ trả một phương án — vẫn chạy được.
        runInfo.textContent = `Đang nhét vào ${chosenRemnants.length} tấm thừa đã chọn…`;
        list = [await bridge.nestWithSelected(parts, onProgress, () => stopRequested)];
      } else {
        const out = await startMultiNest(parts, currentParams(), {
          count: MAX_PLANS,
          onProgress,
          shouldStop: () => stopRequested,
        });
        list = out.plans;
      }
      // Mặc định mở ở phương án 1 (tốt nhất).
      setPlans(list, 0);
      barFill.style.width = '100%';
      const cur = currentPlan();
      runInfo.textContent = `Xong sau ${Math.round((Date.now() - t0) / 1000)}s · `
        + `${plans.length} phương án để chọn`
        + (cur ? ` · tốt nhất ${cur.sheets.length} tấm (${fmtPct(cur.utilization)})` : '');
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
    // Đường tôn thừa đọc cờ này; đường xếp thường tắt worker như cũ.
    stopRequested = true;
    services.stopNest();
  });

  let resizeTimer = 0;
  window.addEventListener('resize', () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => renderCurrent(), 150);
  });

  readNestOptions = () => ({
    ...currentParams(),
    gapInput: settings.gap,
    kerf: Math.max(0, settings.kerf),
    effectiveGap: effectiveGap(),
    unitScale: settings.unitScale,
  });

  // Panel kho tôn thừa (src/remnant/panel.ts) tìm getNestOptions trên globalThis
  // TRƯỚC khi thử import động. Treo ở đây thì bản build production cũng đọc đúng
  // thông số đang gõ trên màn hình, không rơi về mặc định.
  (globalThis as Record<string, unknown>).getNestOptions = getNestOptions;

  syncGcodeInputs();
  updateNote();
  updateTotals();
}
