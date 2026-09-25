/**
 * Khép kín quy trình LƯU và DÙNG tấm tôn thừa — ba việc founder chốt:
 *
 *   VIỆC 1 · tải bản vẽ của tấm thừa xong thì phải NHẮC bấm "Đã dùng"
 *            (nhắc thôi, tuyệt đối không tự đánh dấu hộ);
 *   VIỆC 2 · phần tôn còn lại đẻ MÃ MỚI `LO-<ngày>-<số>`, là DÒNG MỚI trong
 *            kho, tấm cũ giữ nguyên si — KHÔNG ghi đè;
 *   VIỆC 3 · tấm đã dùng ẩn khỏi danh sách, bật "Hiện cả đã dùng" mới thấy
 *            lại và không tích chọn được.
 *
 * Chạy trong Node, không cần DOM, không cần mạng (máy chủ giả bằng fetch giả).
 */
import { describe, it, expect } from 'vitest';
import {
  codeDatePart, nextRemnantCode, parseRemnantCode, composeLeftoverName,
  originNote, buildLeftoverInput, allocateRemnantCode, saveLeftoverToStore,
} from '../naming';
import {
  parseDownloadName, remindersForDownload, reminderText, watchDownloads, findSourceRemnant,
} from '../remind';
import { visibleRemnants, canSelectRemnant } from '../panel';
import { createRemnantStore, memoryStorage } from '../store';
import { normalizeRemnant, cutRectRing, STOCK_H, STOCK_W } from '../normalize';
import type { Remnant } from '../types';
import type { PlannedSheet, RemnantNestResult } from '../plan';

// ── máy chủ giả: đủ 4 việc GET / POST / PATCH / DELETE như Functions thật ────

/** Kho trong bộ nhớ, cư xử y như functions/api/remnants/*. */
function fakeServer(seed: Partial<Remnant>[] = []) {
  let seq = 0;
  const rows: Remnant[] = seed.map((r, i) => normalizeRemnant({
    id: r.id ?? `seed-${i}`,
    name: r.name ?? `tấm ${i}`,
    widthMm: r.widthMm ?? STOCK_W,
    lengthMm: r.lengthMm ?? STOCK_H,
    sheetWidthMm: r.sheetWidthMm ?? STOCK_W,
    sheetLengthMm: r.sheetLengthMm ?? STOCK_H,
    cuts: r.cuts ?? [],
    polygon: r.polygon ?? [[{ x: 0, y: 0 }, { x: STOCK_W, y: 0 }, { x: STOCK_W, y: STOCK_H }, { x: 0, y: STOCK_H }]],
    note: r.note ?? '',
    status: r.status ?? 'available',
    createdAt: 1000 + i,
    updatedAt: 1000 + i,
  }));

  const reply = (data: unknown, status = 200) =>
    new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });

  const fetchFn = (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method || 'GET').toUpperCase();
    const body = init?.body ? JSON.parse(String(init.body)) : null;

    if (method === 'GET') {
      const status = /status=([^&]+)/.exec(url)?.[1] ?? 'available';
      const out = status === 'all' ? rows : rows.filter((r) => r.status === status);
      return reply({ ok: true, remnants: [...out].reverse() });
    }
    if (method === 'POST') {
      seq += 1;
      const row = normalizeRemnant({ ...body, id: `srv-${seq}`, createdAt: 2000 + seq, updatedAt: 2000 + seq });
      rows.push(row);
      return reply({ ok: true, remnant: row }, 201);
    }
    const id = decodeURIComponent(url.split('/').pop() as string);
    const i = rows.findIndex((r) => r.id === id);
    if (i < 0) return reply({ ok: false, error: 'Không tìm thấy tấm thừa này trong kho.' }, 404);
    if (method === 'PATCH') {
      rows[i] = normalizeRemnant({ ...rows[i], ...body, updatedAt: 9999 });
      return reply({ ok: true, remnant: rows[i] });
    }
    if (method === 'DELETE') {
      rows.splice(i, 1);
      return reply({ ok: true, deleted: id });
    }
    return reply({ ok: false, error: 'phương thức lạ' }, 405);
  }) as unknown as typeof fetch;

  return { rows, fetchFn };
}

function newStore(seed: Partial<Remnant>[] = []) {
  const srv = fakeServer(seed);
  return {
    srv,
    store: createRemnantStore({
      fetchFn: srv.fetchFn,
      storage: memoryStorage(),
      baseUrl: '/api/remnants',
    }),
  };
}

const day = (iso: string) => new Date(`${iso}T09:30:00`);

// ── VIỆC 2 · MÃ TỰ SINH ─────────────────────────────────────────────────────

describe('VIỆC 2 — mã tự sinh cho tấm thừa mới', () => {
  it('khuôn mã là LO-<năm>-<tháng>-<ngày>-<số thứ tự 2 chữ số>', () => {
    expect(codeDatePart(day('2026-09-25'))).toBe('2026-09-25');
    expect(nextRemnantCode([], day('2026-09-25'))).toBe('LO-2026-09-25-01');
    expect(parseRemnantCode('LO-2026-09-25-01')).toEqual({ date: '2026-09-25', seq: 1 });
    expect(parseRemnantCode('thừa lô sườn 15')).toBeNull();
  });

  it('không trùng số trong CÙNG MỘT NGÀY, kể cả với tấm đã dùng', () => {
    const có = ['LO-2026-09-25-01', 'LO-2026-09-25-03 · thừa mạn phải', 'thừa lô sườn 15'];
    expect(nextRemnantCode(có, day('2026-09-25'))).toBe('LO-2026-09-25-04');
  });

  it('sang ngày mới thì đếm lại từ 01, không dính số của hôm qua', () => {
    const có = ['LO-2026-09-25-07'];
    expect(nextRemnantCode(có, day('2026-09-26'))).toBe('LO-2026-09-26-01');
  });

  it('thợ gõ tên riêng thì ghép "mã · tên"; để nguyên gợi ý của app thì chỉ lấy mã', () => {
    expect(composeLeftoverName('LO-2026-09-25-01', 'thừa mạn phải'))
      .toBe('LO-2026-09-25-01 · thừa mạn phải');
    expect(composeLeftoverName('LO-2026-09-25-01', 'thừa lo-suon.dxf · tấm 2'))
      .toBe('LO-2026-09-25-01');
    expect(composeLeftoverName('LO-2026-09-25-01', '')).toBe('LO-2026-09-25-01');
  });

  it('ghi rõ nguồn gốc vào ghi chú khi cắt trên một tấm thừa cũ', () => {
    const note = originNote({
      sheetWidthMm: STOCK_W, sheetLengthMm: STOCK_H, cuts: [],
      note: 'lưu từ phương án 1', sourceId: 'r9', sourceName: 'thừa lô sườn 15',
    });
    expect(note).toBe('sinh ra từ tấm thừa "thừa lô sườn 15" · lưu từ phương án 1');

    const input = buildLeftoverInput('LO-2026-09-25-02', {
      sheetWidthMm: STOCK_W, sheetLengthMm: STOCK_H, cuts: [], sourceId: 'r9', sourceName: 'thừa lô sườn 15',
    });
    expect(input.sourceId).toBe('r9');
    expect(input.sourceName).toBe('thừa lô sườn 15');
    expect(input.name).toBe('LO-2026-09-25-02');
  });

  it('mã kế tiếp đọc từ kho thật, không đụng số với tấm đã có', async () => {
    const { store } = newStore([{ name: 'LO-2026-09-25-01' }, { name: 'LO-2026-09-25-02', status: 'used' }]);
    const code = await allocateRemnantCode(store, () => day('2026-09-25').getTime());
    expect(code).toBe('LO-2026-09-25-03');
  });
});

describe('VIỆC 2 — lưu phần thừa HAI LẦN liên tiếp trong cùng ngày', () => {
  it('ra HAI MÃ KHÁC NHAU và tấm cũ vẫn còn nguyên trong kho', async () => {
    const { store, srv } = newStore([{ id: 'cu-1', name: 'thừa lô sườn 15' }]);
    const now = () => day('2026-09-25').getTime();
    const cũ = { ...srv.rows[0] };

    const một = await saveLeftoverToStore(store, {
      sheetWidthMm: STOCK_W,
      sheetLengthMm: STOCK_H,
      cuts: [cutRectRing(0, 0, 800, 3000)],
      note: 'lưu từ phương án 1, 1 chi tiết đã cắt',
      sourceId: 'cu-1',
      sourceName: 'thừa lô sườn 15',
    }, { now });

    const hai = await saveLeftoverToStore(store, {
      sheetWidthMm: STOCK_W,
      sheetLengthMm: STOCK_H,
      cuts: [cutRectRing(0, 0, 900, 3000)],
      note: 'lưu từ phương án 1, 1 chi tiết đã cắt',
      sourceId: 'cu-1',
      sourceName: 'thừa lô sườn 15',
    }, { now });

    expect(một.value.name).toBe('LO-2026-09-25-01');
    expect(hai.value.name).toBe('LO-2026-09-25-02');
    expect(một.value.name).not.toBe(hai.value.name);
    // Hai DÒNG MỚI, mã khác nhau, không phải một dòng bị ghi đè hai lần.
    expect(một.value.id).not.toBe(hai.value.id);

    // Tấm CŨ còn nguyên si: cùng mã, cùng tên, cùng trạng thái, cùng hình.
    const sau = srv.rows.find((r) => r.id === 'cu-1');
    expect(sau).toBeTruthy();
    expect(sau!.name).toBe(cũ.name);
    expect(sau!.status).toBe('available');
    expect(sau!.cuts).toEqual(cũ.cuts);
    expect(sau!.polygon).toEqual(cũ.polygon);

    // Kho nay có 3 dòng: tấm cũ + 2 tấm mới.
    const all = await store.list('all');
    expect(all.remnants).toHaveLength(3);
    expect(all.remnants.map((r) => r.name).sort())
      .toEqual(['LO-2026-09-25-01', 'LO-2026-09-25-02', 'thừa lô sườn 15']);

    // Nguồn gốc ghi lại được để ngoài xưởng lần ngược.
    expect(một.value.sourceName).toBe('thừa lô sườn 15');
    expect(hai.value.note).toContain('sinh ra từ tấm thừa "thừa lô sườn 15"');
  });

  it('LƯU KHÔNG ĐÁNH DẤU HỘ: tấm nguồn vẫn "còn dùng được" sau khi lưu phần thừa', async () => {
    const { store, srv } = newStore([{ id: 'cu-1', name: 'thừa lô sườn 15' }]);
    await saveLeftoverToStore(store, {
      sheetWidthMm: STOCK_W, sheetLengthMm: STOCK_H, cuts: [], sourceId: 'cu-1', sourceName: 'thừa lô sườn 15',
    }, { now: () => day('2026-09-25').getTime() });
    expect(srv.rows.find((r) => r.id === 'cu-1')!.status).toBe('available');
  });
});

// ── VIỆC 3 · ẨN TẤM ĐÃ DÙNG ─────────────────────────────────────────────────

describe('VIỆC 3 — đánh dấu đã dùng thì tấm biến khỏi danh sách', () => {
  it('danh sách mặc định không còn nó; bật "Hiện cả đã dùng" thì thấy lại và không tích chọn được', async () => {
    const { store } = newStore([
      { id: 'r1', name: 'thừa lô sườn 15' },
      { id: 'r2', name: 'thừa mạn phải' },
    ]);

    let items = (await store.list('all')).remnants;
    expect(visibleRemnants(items, false).map((r) => r.id).sort()).toEqual(['r1', 'r2']);

    // Thợ tự bấm "Đã dùng" cho r1.
    await store.markUsed('r1');
    items = (await store.list('all')).remnants;

    // Mặc định: BIẾN MẤT.
    const mặcĐịnh = visibleRemnants(items, false);
    expect(mặcĐịnh.map((r) => r.id)).toEqual(['r2']);
    expect(mặcĐịnh.some((r) => r.id === 'r1')).toBe(false);
    // Con số phải khớp đúng những gì đang hiện.
    expect(mặcĐịnh).toHaveLength(1);

    // Bật "Hiện cả đã dùng": thấy lại, nhưng CHỈ ĐỂ XEM.
    const hiệnHết = visibleRemnants(items, true);
    expect(hiệnHết).toHaveLength(2);
    const r1 = hiệnHết.find((r) => r.id === 'r1') as Remnant;
    expect(r1.status).toBe('used');
    expect(canSelectRemnant(r1)).toBe(false);
    expect(canSelectRemnant(hiệnHết.find((r) => r.id === 'r2') as Remnant)).toBe(true);

    // Máy chủ cũng chỉ trả tấm còn dùng được khi hỏi mặc định.
    expect((await store.list('available')).remnants.map((r) => r.id)).toEqual(['r2']);
  });

  it('trả tấm về "còn dùng được" thì nó hiện lại và tích chọn được', async () => {
    const { store } = newStore([{ id: 'r1', name: 'thừa lô sườn 15' }]);
    await store.markUsed('r1');
    await store.patch('r1', { status: 'available' });
    const items = (await store.list('all')).remnants;
    expect(visibleRemnants(items, false)).toHaveLength(1);
    expect(canSelectRemnant(items[0])).toBe(true);
  });
});

// ── VIỆC 1 · NHẮC BẤM "ĐÃ DÙNG" ─────────────────────────────────────────────

function sheet(over: Partial<PlannedSheet>): PlannedSheet {
  return {
    index: 0,
    width: STOCK_W,
    height: STOCK_H,
    placements: [],
    usedArea: 0,
    utilization: 0,
    source: 'new',
    ...over,
  } as PlannedSheet;
}

function plan(sheets: PlannedSheet[]): RemnantNestResult {
  return {
    sheets,
    unplaced: [],
    utilization: 0.5,
    elapsedMs: 1,
    remnantsUsed: [],
    newSheets: 0,
    skipped: [],
  } as unknown as RemnantNestResult;
}

describe('VIỆC 1 — đọc tên file vừa tải để biết nhắc tấm thừa nào', () => {
  it('đọc đúng phương án và số tấm từ tên file do src/ui/download.ts đặt', () => {
    expect(parseDownloadName('tam-01_2000x6000.dxf')).toEqual({ planIndex: 0, sheet: 0 });
    expect(parseDownloadName('tam-03_2000x6000.nc')).toEqual({ planIndex: 0, sheet: 2 });
    expect(parseDownloadName('pa2-tam-01_2000x6000.dxf')).toEqual({ planIndex: 1, sheet: 0 });
    expect(parseDownloadName('tat-ca-tam.dxf')).toEqual({ planIndex: 0, sheet: 'all' });
    expect(parseDownloadName('pa3-xep-phoi-gcode.zip')).toEqual({ planIndex: 2, sheet: 'all' });
    // File lạ thì im lặng, không nhắc bừa.
    expect(parseDownloadName('anh-cuoi.jpg')).toBeNull();
    expect(parseDownloadName('')).toBeNull();
    expect(parseDownloadName(undefined)).toBeNull();
  });

  it('chỉ nhắc TẤM THỪA TRONG KHO, bỏ qua tấm mới nguyên khổ', () => {
    const plans = [plan([
      sheet({ index: 0, source: 'remnant', remnantId: 'r1', remnantName: 'thừa lô sườn 15' }),
      sheet({ index: 1, source: 'new' }),
      sheet({ index: 2, source: 'remnant', remnantId: 'r2', remnantName: 'thừa mạn phải' }),
    ])];

    expect(remindersForDownload(plans, 'tam-01_2000x6000.dxf'))
      .toEqual([{ id: 'r1', name: 'thừa lô sườn 15' }]);
    // Tấm mới nguyên khổ: không nhắc gì cả.
    expect(remindersForDownload(plans, 'tam-02_2000x6000.dxf')).toEqual([]);
    // Tải cả gói thì nhắc đủ mọi tấm thừa có trong gói.
    expect(remindersForDownload(plans, 'xep-phoi-dxf.zip').map((r) => r.id)).toEqual(['r1', 'r2']);
    // Phương án không tồn tại → không nhắc.
    expect(remindersForDownload(plans, 'pa4-tam-01_2000x6000.dxf')).toEqual([]);
  });

  it('câu nhắc nói rõ phải bấm "Đã dùng"', () => {
    const một = reminderText([{ id: 'r1', name: 'thừa lô sườn 15' }]);
    expect(một).toContain('thừa lô sườn 15');
    expect(một).toContain('Đã dùng');
    const nhiều = reminderText([{ id: 'r1', name: 'A' }, { id: 'r2', name: 'B' }]);
    expect(nhiều).toContain('2 tấm thừa');
    expect(reminderText([])).toBe('');
  });

  it('bắt được lượt tải file qua thẻ <a download> mà không đụng file của thợ UI', () => {
    // Giả lập đúng cách src/main.ts tải file: dựng <a download> rồi click.
    const seen: string[] = [];
    const listeners: ((ev: unknown) => void)[] = [];
    const anchor = { tagName: 'A', getAttribute: (k: string) => (k === 'download' ? 'tam-01_2000x6000.dxf' : null) };
    const fakeDoc = {
      addEventListener: (_t: string, fn: (ev: unknown) => void) => void listeners.push(fn),
      removeEventListener: () => void listeners.splice(0, listeners.length),
    } as unknown as Document;

    const off = watchDownloads((name) => void seen.push(name), fakeDoc);
    listeners[0]({ target: anchor, composedPath: () => [anchor] });
    expect(seen).toEqual(['tam-01_2000x6000.dxf']);

    // Bấm vào thứ khác (không phải link tải) thì im.
    const button = { tagName: 'BUTTON', getAttribute: () => null };
    listeners[0]({ target: button, composedPath: () => [button] });
    expect(seen).toHaveLength(1);

    off();
    expect(listeners).toHaveLength(0);
  });
});

describe('VIỆC 2 — lần ra tấm thừa nguồn từ dấu vết app.ts để lại', () => {
  const plans = [plan([
    sheet({ index: 0, source: 'new' }),
    sheet({
      index: 1, source: 'remnant', remnantId: 'r1', remnantName: 'thừa lô sườn 15',
      cuts: [], placements: [{ partId: 'P0' }, { partId: 'P1' }] as PlannedSheet['placements'],
    }),
  ])];

  it('tên gợi ý "... · tấm 2" + ghi chú "phương án 1" → đúng tấm thừa r1', () => {
    expect(findSourceRemnant(plans, {
      name: 'thừa lo-suon.dxf · tấm 2',
      note: 'lưu từ phương án 1, 2 chi tiết đã cắt',
      sheetWidthMm: STOCK_W,
      sheetLengthMm: STOCK_H,
      cuts: [1, 2],
    } as never)).toEqual({ id: 'r1', name: 'thừa lô sườn 15' });
  });

  it('thợ gõ tên khác thì lùi về so khổ tấm + số lỗ', () => {
    expect(findSourceRemnant(plans, {
      name: 'tấm để dành cho lô sau',
      sheetWidthMm: STOCK_W,
      sheetLengthMm: STOCK_H,
      cuts: [1, 2],
    })).toEqual({ id: 'r1', name: 'thừa lô sườn 15' });
  });

  it('tấm mới nguyên khổ (không phải tôn thừa) thì KHÔNG bịa ra nguồn gốc', () => {
    expect(findSourceRemnant(plans, {
      name: 'thừa lo-suon.dxf · tấm 1',
      note: 'lưu từ phương án 1, 0 chi tiết đã cắt',
      sheetWidthMm: STOCK_W,
      sheetLengthMm: STOCK_H,
      cuts: [],
    } as never)).toBeNull();
  });
});
