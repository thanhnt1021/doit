/**
 * Panel "KHO TÔN THỪA" — tự chứa hoàn toàn.
 *
 * Gắn vào phần tử <div id="remnant-slot"></div> mà thợ UI đặt ở cột trái,
 * ngay dưới khối THÔNG SỐ. Panel tự bơm CSS riêng (mọi lớp đều có tiền tố
 * "rmn-") nên KHÔNG cần đụng một dòng nào trong src/ui/.
 *
 * Nếu lúc chạy chưa thấy #remnant-slot (thợ UI chưa đẩy code), panel tự dựng
 * một ô tạm ở cuối trang để vẫn dùng và thử được — xem ensureSlot().
 */
import type { NestParams, Ring } from '../types';
import { DEFAULT_NEST_PARAMS } from '../types';
import type { Remnant, RemnantInput } from './types';
import { createRemnantStore, type RemnantStore } from './store';
import { polygonArea, rectPolygon } from './geometry';
import { STOCK_H, STOCK_W, buildRemnantInput, cutRectRing } from './normalize';
import { drawRemnantPreview, previewHeight } from './preview';

export const SLOT_ID = 'remnant-slot';

const CSS = `
/* Bám theo bảng màu của src/ui/styles.css (--ink, --line, --muted, --accent...)
   nên panel tự đổi màu theo giao diện chung. Có fallback để vẫn đọc được khi
   chạy một mình (ô tạm, chưa nạp styles.css của app). */
.rmn{--rmn-line:var(--line,#d8dbe0);--rmn-ink:var(--ink,#1d2126);
  --rmn-muted:var(--muted,#667085);--rmn-acc:var(--accent,#1f6feb);
  border:1px solid var(--rmn-line);border-radius:6px;padding:9px 10px;margin:14px 0 6px;
  color:var(--rmn-ink);font:13px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
.rmn h3{margin:0 0 7px;font-size:11px;text-transform:uppercase;letter-spacing:.8px;
  color:var(--rmn-muted);font-weight:700}
.rmn-bar{display:flex;gap:5px;align-items:center;margin-bottom:7px;flex-wrap:wrap}
.rmn-msg{font-size:11.5px;padding:5px 7px;border-radius:4px;margin-bottom:7px;display:none}
.rmn-msg.on{display:block}
.rmn-msg.err{background:#fdecea;border:1px solid #f0b7b1;color:var(--danger,#c0392b)}
.rmn-msg.warn{background:var(--warn-bg,#fff8e1);border:1px solid var(--warn-line,#e6c34a);color:#6b5200}
.rmn-msg.ok{background:#eaf6ee;border:1px solid #a9d8ba;color:var(--ok,#2f8f4e)}
.rmn-list{max-height:240px;overflow-y:auto;display:flex;flex-direction:column;gap:5px}
.rmn-item{display:flex;flex-wrap:wrap;gap:6px;align-items:flex-start;
  border:1px solid var(--rmn-line);border-radius:5px;padding:6px 7px}
.rmn-item.used{opacity:.55}
.rmn-item>input[type=checkbox]{margin:2px 0 0;flex:none}
.rmn-it-body{flex:1 1 140px;min-width:0}
.rmn-it-name{font-weight:600;word-break:break-word;font-size:12.5px}
.rmn-it-sub{color:var(--rmn-muted);font-size:11px;margin-top:2px;word-break:break-word}
.rmn-it-act{display:flex;gap:4px;flex:0 0 auto;margin-left:auto}
.rmn-form{display:none;margin-top:8px;border-top:1px dashed var(--rmn-line);padding-top:8px}
.rmn-form.on{display:block}
.rmn-row{display:flex;gap:6px;margin-bottom:6px}
.rmn-row>label{flex:1;min-width:0;display:block;font-size:11px;color:var(--rmn-muted)}
.rmn-row>label>input,.rmn-row>label>textarea,.rmn-row>label>select{margin-top:2px}
.rmn textarea{min-height:56px;resize:vertical;font-family:ui-monospace,monospace;font-size:11px;
  width:100%;padding:4px 6px;border:1px solid var(--rmn-line);border-radius:4px;
  background:var(--panel,#fff);color:var(--rmn-ink)}
.rmn-empty{color:var(--rmn-muted);font-style:italic;padding:6px 2px;font-size:12px}
.rmn-foot{margin-top:7px;font-size:11px;color:var(--rmn-muted)}
/* VIỆC 2 — ô xem trước tấm thừa, hiện ngay khi tích chọn. */
.rmn-prev{flex:1 1 100%;margin-top:5px}
.rmn-prev canvas{display:block;border:1px solid var(--rmn-line);border-radius:4px;background:#fff}
.rmn-prev .cap{font-size:10.5px;color:var(--rmn-muted);margin-top:2px}
.rmn-tag{display:inline-block;font-size:10px;padding:0 4px;border-radius:3px;
  background:var(--warn-bg,#fff8e1);border:1px solid var(--warn-line,#e6c34a);color:#6b5200;margin-left:4px}
`;

function injectCss(doc: Document): void {
  if (doc.getElementById('rmn-css')) return;
  const s = doc.createElement('style');
  s.id = 'rmn-css';
  s.textContent = CSS;
  doc.head.appendChild(s);
}

function h<K extends keyof HTMLElementTagNameMap>(
  tag: K, cls?: string, html?: string
): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

const mm = (v: number) => `${Math.round(v)}`;
const m2 = (mm2: number) => (mm2 / 1e6).toFixed(2);

/**
 * Lấy thông số lượt xếp từ hàm getNestOptions() do thợ UI export.
 * Thợ UI có thể đặt ở ui/index, ui/app, hoặc treo lên globalThis — thử cả ba,
 * chưa có thì dùng mặc định, TUYỆT ĐỐI không làm sập panel.
 */
export async function readNestOptions(): Promise<NestParams> {
  const tryCall = (fn: unknown): Partial<NestParams> | null => {
    if (typeof fn !== 'function') return null;
    try {
      const v = (fn as () => unknown)();
      return v && typeof v === 'object' ? (v as Partial<NestParams>) : null;
    } catch {
      return null;
    }
  };

  const g = tryCall((globalThis as Record<string, unknown>).getNestOptions);
  if (g) return { ...DEFAULT_NEST_PARAMS, ...g };

  for (const spec of ['../ui/index', '../ui/app']) {
    try {
      const mod = (await import(/* @vite-ignore */ spec)) as unknown as Record<string, unknown>;
      const v = tryCall(mod.getNestOptions);
      if (v) return { ...DEFAULT_NEST_PARAMS, ...v };
    } catch {
      /* thợ UI chưa export — bỏ qua */
    }
  }
  return { ...DEFAULT_NEST_PARAMS };
}

/**
 * Tìm ô để gắn panel. Chưa có #remnant-slot thì tự dựng một ô tạm.
 * Trả kèm cờ để báo cáo / hiện cảnh báo cho người dùng.
 */
export function ensureSlot(doc: Document = document): { slot: HTMLElement; temporary: boolean } {
  const found = doc.getElementById(SLOT_ID);
  if (found) return { slot: found, temporary: false };
  const tmp = doc.createElement('div');
  tmp.id = SLOT_ID;
  tmp.dataset.rmnTemporary = '1';
  tmp.style.cssText = 'max-width:420px;margin:12px;';
  (doc.getElementById('app') || doc.body).appendChild(tmp);
  return { slot: tmp, temporary: true };
}

/** Dựng đa giác cho ô "cắt vát một góc" — dạng tôn thừa hay gặp nhất ở xưởng. */
export function cornerCutPolygon(w: number, h: number, cutW: number, cutH: number): Ring[] {
  const cw = Math.max(0, Math.min(cutW, w));
  const ch = Math.max(0, Math.min(cutH, h));
  if (cw <= 0 || ch <= 0) return rectPolygon(w, h);
  // Vát góc TRÊN-PHẢI, đi ngược chiều kim đồng hồ.
  return [[
    { x: 0, y: 0 }, { x: w, y: 0 }, { x: w, y: h - ch },
    { x: w - cw, y: h }, { x: 0, y: h },
  ]];
}

/** Đọc textarea "x y" hoặc "x,y" mỗi dòng một đỉnh. */
export function parsePointsText(text: string): { ring?: Ring; error?: string } {
  const ring: Ring = [];
  const lines = text.split(/[\r\n;]+/).map((s) => s.trim()).filter(Boolean);
  for (const line of lines) {
    const parts = line.split(/[\s,]+/).filter(Boolean);
    if (parts.length < 2) return { error: `Dòng "${line}" phải có 2 số: x và y.` };
    const x = Number(parts[0]);
    const y = Number(parts[1]);
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      return { error: `Dòng "${line}" có toạ độ không phải số.` };
    }
    ring.push({ x, y });
  }
  if (ring.length < 3) return { error: 'Cần ít nhất 3 đỉnh để tạo thành một hình.' };
  return { ring };
}

export interface RemnantPanel {
  /** Các tấm thừa người dùng đang tích chọn để đưa vào lượt xếp. */
  getSelected(): Remnant[];
  /** Tải lại danh sách từ máy chủ. */
  refresh(): Promise<void>;
  /** Đánh dấu đã dùng hàng loạt (gọi sau khi xếp xong và thợ đã cắt). */
  markUsed(ids: string[]): Promise<void>;
  /** Lưu một tấm thừa mới từ code khác (ví dụ lấy phần dư của tấm vừa xếp). */
  save(input: RemnantInput): Promise<Remnant>;
  /**
   * VIỆC 3 — lưu thẳng một tấm trong phương án vừa xếp: giữ NGUYÊN KHỔ tấm gốc
   * và ghi lại đúng các lỗ vừa cắt.
   */
  saveFromSheet(args: {
    name: string;
    sheetWidthMm: number;
    sheetLengthMm: number;
    cuts: Ring[];
    note?: string;
  }): Promise<Remnant>;
  onSelectionChange(fn: (sel: Remnant[]) => void): void;
  store: RemnantStore;
  /** true = panel đang nằm trong ô tạm do chính nó dựng, chưa có #remnant-slot. */
  temporarySlot: boolean;
  destroy(): void;
}

export function mountRemnantPanel(
  slotIn?: HTMLElement | null,
  store: RemnantStore = createRemnantStore()
): RemnantPanel {
  injectCss(document);
  const resolved = slotIn ? { slot: slotIn, temporary: false } : ensureSlot();
  const slot = resolved.slot;

  let items: Remnant[] = [];
  const selected = new Set<string>();
  let showUsed = false;
  let selectionListener: ((sel: Remnant[]) => void) | null = null;

  const root = h('section', 'rmn');
  root.setAttribute('aria-label', 'Kho tôn thừa');
  root.appendChild(h('h3', undefined, 'Kho tôn thừa'));

  const msg = h('div', 'rmn-msg');
  const bar = h('div', 'rmn-bar');
  const btnAdd = h('button', 'primary sm', '+ Lưu tấm thừa');
  const btnReload = h('button', 'sm', 'Tải lại');
  const btnToggleUsed = h('button', 'sm', 'Hiện cả đã dùng');
  bar.append(btnAdd, btnReload, btnToggleUsed);

  const list = h('div', 'rmn-list');
  const foot = h('div', 'rmn-foot');
  root.append(msg, bar, list, foot);

  // ── ô nhập tấm thừa mới ────────────────────────────────────────────────
  const form = h('div', 'rmn-form');
  form.innerHTML = `
    <div class="rmn-row">
      <label>Tên tấm thừa (bắt buộc)
        <input type="text" id="rmn-name" placeholder="ví dụ: thừa lô sườn 15" maxlength="120">
      </label>
    </div>
    <div class="rmn-row">
      <label>Khổ tấm GỐC — rộng (mm)<input type="number" id="rmn-w" min="1" step="1" value="${STOCK_W}"></label>
      <label>Khổ tấm GỐC — dài (mm)<input type="number" id="rmn-l" min="1" step="1" value="${STOCK_H}"></label>
    </div>
    <div class="rmn-row">
      <label>Phần ĐÃ CẮT ĐI khỏi tấm
        <select id="rmn-shape">
          <option value="none">Chưa cắt gì — tấm nguyên</option>
          <option value="rect" selected>Một ô chữ nhật đã cắt</option>
          <option value="corner">Đã cắt vát một góc (trên-phải)</option>
          <option value="free">Tự nhập đỉnh lỗ đã cắt</option>
        </select>
      </label>
    </div>
    <div class="rmn-row" id="rmn-rect-row">
      <label>Lỗ — góc dưới-trái x (mm)<input type="number" id="rmn-cx" step="1" value="0"></label>
      <label>y (mm)<input type="number" id="rmn-cy" step="1" value="0"></label>
    </div>
    <div class="rmn-row" id="rmn-size-row">
      <label>Lỗ — rộng (mm)<input type="number" id="rmn-cw" min="1" step="1" value="800"></label>
      <label>Lỗ — dài (mm)<input type="number" id="rmn-ch" min="1" step="1" value="3000"></label>
    </div>
    <div class="rmn-row" id="rmn-free-row" style="display:none">
      <label>Các đỉnh của LỖ đã cắt, mỗi dòng "x y" (mm, gốc ở góc dưới-trái TẤM GỐC)
        <textarea id="rmn-pts" placeholder="0 0&#10;800 0&#10;800 3000&#10;0 3000"></textarea>
      </label>
    </div>
    <div class="rmn-row">
      <label>Ghi chú<input type="text" id="rmn-note" placeholder="mác thép, độ dày, để ở giá nào…" maxlength="500"></label>
    </div>
    <div class="rmn-prev" id="rmn-form-prev"></div>
    <div class="rmn-bar">
      <button class="primary sm" id="rmn-save">Lưu vào kho</button>
      <button class="sm" id="rmn-cancel">Huỷ</button>
    </div>`;
  root.appendChild(form);
  slot.appendChild(root);

  const q = <T extends HTMLElement>(id: string) => form.querySelector(`#${id}`) as T;
  const inName = q<HTMLInputElement>('rmn-name');
  const inW = q<HTMLInputElement>('rmn-w');
  const inL = q<HTMLInputElement>('rmn-l');
  const inShape = q<HTMLSelectElement>('rmn-shape');
  const inCx = q<HTMLInputElement>('rmn-cx');
  const inCy = q<HTMLInputElement>('rmn-cy');
  const inCw = q<HTMLInputElement>('rmn-cw');
  const inCh = q<HTMLInputElement>('rmn-ch');
  const inPts = q<HTMLTextAreaElement>('rmn-pts');
  const inNote = q<HTMLInputElement>('rmn-note');
  const rowRect = q<HTMLElement>('rmn-rect-row');
  const rowSize = q<HTMLElement>('rmn-size-row');
  const rowFree = q<HTMLElement>('rmn-free-row');
  const formPrev = q<HTMLElement>('rmn-form-prev');
  const btnSave = q<HTMLButtonElement>('rmn-save');
  const btnCancel = q<HTMLButtonElement>('rmn-cancel');

  const say = (text: string, kind: 'err' | 'warn' | 'ok' = 'ok') => {
    msg.textContent = text;
    msg.className = `rmn-msg on ${kind}`;
  };
  const hush = () => {
    msg.textContent = '';
    msg.className = 'rmn-msg';
  };

  const fireSelection = () => selectionListener?.(getSelected());

  function getSelected(): Remnant[] {
    return items.filter((r) => selected.has(r.id) && r.status === 'available');
  }

  function renderFoot(): void {
    const sel = getSelected();
    const area = sel.reduce((a, r) => a + polygonArea(r.polygon), 0);
    foot.textContent = sel.length
      ? `Đã chọn ${sel.length} tấm thừa · tổng ${m2(area)} m² sẽ được nhét trước khi mở tấm mới.`
      : 'Chưa chọn tấm thừa nào — lượt xếp sẽ mở thẳng tấm mới nguyên khổ.';
  }

  function render(): void {
    list.textContent = '';
    const shown = showUsed ? items : items.filter((r) => r.status === 'available');
    if (shown.length === 0) {
      list.appendChild(h('div', 'rmn-empty', 'Kho trống. Cắt xong tấm nào còn thừa thì bấm "+ Lưu tấm thừa".'));
      renderFoot();
      return;
    }
    for (const r of shown) {
      const row = h('div', `rmn-item${r.status === 'used' ? ' used' : ''}`);

      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = selected.has(r.id);
      cb.disabled = r.status === 'used';
      cb.title = 'Tích để nhét chi tiết vào tấm thừa này trước';
      cb.addEventListener('change', () => {
        if (cb.checked) selected.add(r.id);
        else selected.delete(r.id);
        // VIỆC 2: vẽ lại cả danh sách để ô xem trước hiện ra / biến mất ngay.
        render();
        fireSelection();
      });

      const body = h('div', 'rmn-it-body');
      const nameEl = h('div', 'rmn-it-name');
      nameEl.textContent = r.name + (r.pending ? ' · chờ gửi lên' : '');
      if (r.legacy) {
        const tag = h('span', 'rmn-tag', 'tấm kiểu cũ');
        tag.title = 'Lưu trước khi đổi cấu trúc — không rõ khổ tấm gốc, '
          + 'khung bao đang là khung bao của chính mảnh thừa.';
        nameEl.appendChild(tag);
      }
      // VIỆC 3: khung bao LUÔN là khổ tấm gốc, kèm số lỗ đã cắt.
      const sub = h('div', 'rmn-it-sub');
      sub.textContent =
        `khổ gốc ${mm(r.sheetWidthMm)}×${mm(r.sheetLengthMm)}mm`
        + ` · ${r.cuts.length} lỗ đã cắt`
        + ` · còn ${m2(polygonArea(r.polygon))} m²`
        + (r.status === 'used' ? ' · ĐÃ DÙNG' : '')
        + (r.note ? ` · ${r.note}` : '');
      body.append(nameEl, sub);

      const act = h('div', 'rmn-it-act');
      const bRename = h('button', 'sm', 'Sửa');
      bRename.title = 'Đổi tên / ghi chú';
      bRename.addEventListener('click', () => void doRename(r));
      const bUsed = h('button', 'sm', r.status === 'used' ? 'Còn' : 'Đã dùng');
      bUsed.addEventListener('click', () => void doToggleUsed(r));
      const bDel = h('button', 'sm', 'Xoá');
      bDel.addEventListener('click', () => void doDelete(r));
      act.append(bRename, bUsed, bDel);

      row.append(cb, body, act);
      // Đưa vào DOM TRƯỚC rồi mới vẽ: canvas cần bề ngang thật để không méo.
      list.appendChild(row);

      // ── VIỆC 2: tích chọn là hiện ngay hình tấm, bỏ tích là mất ──────────
      if (selected.has(r.id) && r.status === 'available') {
        const prev = h('div', 'rmn-prev');
        const cv = document.createElement('canvas');
        prev.appendChild(cv);
        const cap = h('div', 'cap');
        cap.textContent = r.cuts.length
          ? `Ô xám gạch = phần đã cắt lần trước · khung bao giữ nguyên ${mm(r.sheetWidthMm)}×${mm(r.sheetLengthMm)}mm`
          : `Tấm nguyên khổ ${mm(r.sheetWidthMm)}×${mm(r.sheetLengthMm)}mm, chưa cắt gì`;
        prev.appendChild(cap);
        row.appendChild(prev);
        // Canvas phải nằm trong DOM mới đo được bề ngang thật.
        const width = Math.max(140, row.clientWidth - 16 || list.clientWidth - 20 || 260);
        try {
          drawRemnantPreview(cv, r, { cssWidth: width, cssHeight: previewHeight(r, width) });
        } catch {
          /* canvas hỏng thì thôi, panel vẫn phải chạy */
        }
      }
    }
    renderFoot();
  }

  async function refresh(): Promise<void> {
    try {
      const out = await store.list('all');
      items = out.remnants;
      for (const id of Array.from(selected)) {
        if (!items.some((r) => r.id === id && r.status === 'available')) selected.delete(id);
      }
      if (out.offline) say(out.message || 'Mất mạng — đang dùng bản lưu trong máy.', 'warn');
      else if (out.queued > 0) say(`Còn ${out.queued} thay đổi chờ gửi lên.`, 'warn');
      else hush();
      render();
      fireSelection();
    } catch (e) {
      say(`Không tải được kho tôn thừa: ${(e as Error).message}`, 'err');
    }
  }

  async function doRename(r: Remnant): Promise<void> {
    const name = window.prompt('Tên tấm thừa:', r.name);
    if (name === null) return;
    if (!name.trim()) {
      say('Tên tấm thừa không được để trống.', 'err');
      return;
    }
    const note = window.prompt('Ghi chú:', r.note) ?? r.note;
    try {
      const out = await store.patch(r.id, { name, note });
      await refresh();
      say(out.offline ? (out.message || 'Đã sửa trong máy, chờ có mạng.') : 'Đã sửa xong.', out.offline ? 'warn' : 'ok');
    } catch (e) {
      say(`Không sửa được: ${(e as Error).message}`, 'err');
    }
  }

  async function doToggleUsed(r: Remnant): Promise<void> {
    const next = r.status === 'used' ? 'available' : 'used';
    try {
      const out = await store.patch(r.id, { status: next });
      await refresh();
      say(
        out.offline
          ? (out.message || 'Đã đổi trạng thái trong máy, chờ có mạng.')
          : (next === 'used' ? `Đã đánh dấu "${r.name}" là đã dùng.` : `Đã trả "${r.name}" về còn dùng được.`),
        out.offline ? 'warn' : 'ok'
      );
    } catch (e) {
      say(`Không đổi được trạng thái: ${(e as Error).message}`, 'err');
    }
  }

  async function doDelete(r: Remnant): Promise<void> {
    if (!window.confirm(`Xoá hẳn tấm thừa "${r.name}" khỏi kho? Cả xưởng sẽ không thấy nó nữa.`)) return;
    try {
      const out = await store.remove(r.id);
      await refresh();
      say(out.offline ? (out.message || 'Đã xoá trong máy, chờ có mạng.') : 'Đã xoá khỏi kho.', out.offline ? 'warn' : 'ok');
    } catch (e) {
      say(`Không xoá được: ${(e as Error).message}`, 'err');
    }
  }

  /**
   * Gom dữ liệu trong ô nhập thành RemnantInput — VIỆC 3.
   *
   * Khác trước: người dùng khai KHỔ TẤM GỐC (2000×6000) và PHẦN ĐÃ CẮT ĐI,
   * chứ không khai mảnh thừa rời. Khung bao vì thế luôn đúng khổ tấm gốc.
   */
  function collectInput(): { input?: RemnantInput; error?: string } {
    const name = inName.value.trim();
    const w = Number(inW.value);
    const l = Number(inL.value);
    if (!name) return { error: 'Phải đặt tên cho tấm thừa, ví dụ "thừa lô sườn 15".' };
    if (!Number.isFinite(w) || w <= 0) return { error: 'Khổ tấm gốc (rộng) phải là số lớn hơn 0.' };
    if (!Number.isFinite(l) || l <= 0) return { error: 'Khổ tấm gốc (dài) phải là số lớn hơn 0.' };

    const cuts: Ring[] = [];
    if (inShape.value === 'rect') {
      const x = Number(inCx.value) || 0;
      const y = Number(inCy.value) || 0;
      const cw = Number(inCw.value);
      const ch = Number(inCh.value);
      if (!Number.isFinite(cw) || cw <= 0 || !Number.isFinite(ch) || ch <= 0) {
        return { error: 'Lỗ đã cắt phải có chiều rộng và chiều dài lớn hơn 0.' };
      }
      if (x < 0 || y < 0 || x + cw > w + 0.001 || y + ch > l + 0.001) {
        return { error: 'Lỗ đã cắt phải nằm gọn trong khổ tấm gốc.' };
      }
      cuts.push(cutRectRing(x, y, cw, ch));
    } else if (inShape.value === 'corner') {
      const cw = Math.min(Math.max(0, Number(inCw.value) || 0), w);
      const ch = Math.min(Math.max(0, Number(inCh.value) || 0), l);
      if (cw <= 0 || ch <= 0) return { error: 'Góc vát phải có kích thước lớn hơn 0.' };
      // Tam giác vát ở góc TRÊN-PHẢI của tấm gốc.
      cuts.push([{ x: w - cw, y: l }, { x: w, y: l }, { x: w, y: l - ch }]);
    } else if (inShape.value === 'free') {
      const parsed = parsePointsText(inPts.value);
      if (parsed.error || !parsed.ring) return { error: parsed.error || 'Hình lỗ không hợp lệ.' };
      for (const pt of parsed.ring) {
        if (pt.x < -0.001 || pt.y < -0.001 || pt.x > w + 0.001 || pt.y > l + 0.001) {
          return { error: 'Đỉnh của lỗ đã cắt phải nằm trong khổ tấm gốc.' };
        }
      }
      cuts.push(parsed.ring);
    }

    return {
      input: buildRemnantInput({
        name, sheetWidthMm: w, sheetLengthMm: l, cuts, note: inNote.value.trim(),
      }),
    };
  }

  /** Vẽ ô xem trước ngay trong khung nhập, để thợ thấy mình đang khai cái gì. */
  function renderFormPreview(): void {
    formPrev.textContent = '';
    const got = collectInput();
    if (!got.input) return;
    const fake: Remnant = {
      id: 'preview', name: got.input.name || 'tấm mới', status: 'available',
      widthMm: got.input.widthMm, lengthMm: got.input.lengthMm,
      sheetWidthMm: got.input.sheetWidthMm ?? got.input.widthMm,
      sheetLengthMm: got.input.sheetLengthMm ?? got.input.lengthMm,
      cuts: got.input.cuts ?? [], polygon: got.input.polygon,
      note: '', createdAt: 0, updatedAt: 0,
    };
    const cv = document.createElement('canvas');
    const width = Math.max(140, formPrev.clientWidth || root.clientWidth - 24 || 280);
    formPrev.appendChild(cv);
    try {
      drawRemnantPreview(cv, fake, { cssWidth: width, cssHeight: previewHeight(fake, width) });
    } catch {
      /* canvas hỏng thì thôi, không được làm sập panel */
    }
  }

  async function save(input: RemnantInput): Promise<Remnant> {
    const out = await store.add(input);
    await refresh();
    if (out.offline) say(out.message || 'Mất mạng — đã lưu tạm trong máy này, có mạng lại sẽ tự gửi lên.', 'warn');
    else say(`Đã lưu "${out.value.name}" vào kho, cả xưởng đều thấy.`, 'ok');
    return out.value;
  }

  btnAdd.addEventListener('click', () => {
    form.classList.toggle('on');
    if (form.classList.contains('on')) {
      inName.focus();
      renderFormPreview();
    }
  });
  btnCancel.addEventListener('click', () => form.classList.remove('on'));
  btnReload.addEventListener('click', () => {
    void store.sync().then(() => refresh());
  });
  btnToggleUsed.addEventListener('click', () => {
    showUsed = !showUsed;
    btnToggleUsed.textContent = showUsed ? 'Chỉ hiện còn dùng được' : 'Hiện cả đã dùng';
    render();
  });
  inShape.addEventListener('change', () => {
    const v = inShape.value;
    rowRect.style.display = v === 'rect' ? 'flex' : 'none';
    rowSize.style.display = v === 'rect' || v === 'corner' ? 'flex' : 'none';
    rowFree.style.display = v === 'free' ? 'flex' : 'none';
    renderFormPreview();
  });
  // Gõ tới đâu vẽ lại tới đó — founder "căn ke nhìn trước" rồi mới bấm lưu.
  for (const inp of [inW, inL, inCx, inCy, inCw, inCh, inPts, inName]) {
    inp.addEventListener('input', renderFormPreview);
  }
  btnSave.addEventListener('click', () => {
    const got = collectInput();
    if (got.error || !got.input) {
      say(got.error || 'Dữ liệu chưa hợp lệ.', 'err');
      return;
    }
    btnSave.disabled = true;
    void save(got.input)
      .then(() => {
        form.classList.remove('on');
        inName.value = '';
        inNote.value = '';
        inPts.value = '';
      })
      .catch((e: Error) => say(`Không lưu được: ${e.message}`, 'err'))
      .finally(() => {
        btnSave.disabled = false;
      });
  });

  if (resolved.temporary) {
    say('Chưa thấy ô #remnant-slot trên giao diện — panel đang tạm nằm ở cuối trang.', 'warn');
  }

  void store.sync().then(() => refresh()).catch(() => void refresh());

  return {
    getSelected,
    refresh,
    async markUsed(ids: string[]) {
      for (const id of ids) {
        try {
          await store.patch(id, { status: 'used' });
        } catch {
          /* một tấm hỏng không chặn các tấm còn lại */
        }
      }
      await refresh();
    },
    save,
    saveFromSheet(args) {
      return save(buildRemnantInput(args));
    },
    onSelectionChange(fn) {
      selectionListener = fn;
      fireSelection();
    },
    store,
    temporarySlot: resolved.temporary,
    destroy() {
      root.remove();
      if (resolved.temporary) slot.remove();
    },
  };
}
