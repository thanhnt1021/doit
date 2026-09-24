/**
 * Kiểm thử kho tôn thừa: hình học, kiểm tra dữ liệu (cả phía trình duyệt lẫn
 * phía máy chủ), đường lui khi mất mạng, và việc ưu tiên nhét vào tôn thừa.
 * Chạy trong Node, không cần DOM, không cần mạng.
 */
import { describe, it, expect } from 'vitest';
import {
  polygonArea, polygonBounds, rectPolygon, largestInnerRect, pointInPolygon,
} from '../src/remnant/geometry';
import { validateRemnantInput } from '../src/remnant/validate';
import { createRemnantStore, memoryStorage, CACHE_KEY, QUEUE_KEY } from '../src/remnant/store';
import { nestWithRemnants } from '../src/remnant/plan';
import { cornerCutPolygon, parsePointsText } from '../src/remnant/panel';
import type { Remnant } from '../src/remnant/types';
import type { NestInput, NestResult, Part, Ring } from '../src/types';
import { DEFAULT_NEST_PARAMS } from '../src/types';
import { nest as realNest } from '../src/nest';

// ── đồ dùng chung ────────────────────────────────────────────────────────────

function makeRemnant(over: Partial<Remnant> = {}): Remnant {
  const w = over.widthMm ?? 1200;
  const l = over.lengthMm ?? 2400;
  return {
    id: over.id ?? 'r1',
    name: over.name ?? 'thừa lô sườn 15',
    widthMm: w,
    lengthMm: l,
    polygon: over.polygon ?? rectPolygon(w, l),
    note: over.note ?? '',
    status: over.status ?? 'available',
    createdAt: over.createdAt ?? 1,
    updatedAt: over.updatedAt ?? 1,
    pending: over.pending,
  };
}

/** Chi tiết hình chữ nhật đơn giản, đủ dùng cho engine thật. */
function rectPart(id: string, w: number, h: number, qty = 1): Part {
  const rings: Ring[] = rectPolygon(w, h);
  return {
    id,
    rings,
    area: w * h,
    bbox: { minX: 0, minY: 0, maxX: w, maxY: h },
    vertexCount: 4,
    minWidth: Math.min(w, h),
    maxLength: Math.hypot(w, h),
    qty,
    enabled: true,
    fitsSheet: true,
  };
}

// ── 1. Hình học ──────────────────────────────────────────────────────────────

describe('hình học tấm thừa', () => {
  it('tính đúng diện tích hình chữ nhật và hình có lỗ', () => {
    expect(polygonArea(rectPolygon(1000, 2000))).toBe(2_000_000);
    const withHole: Ring[] = [
      ...rectPolygon(1000, 1000),
      [{ x: 200, y: 200 }, { x: 400, y: 200 }, { x: 400, y: 400 }, { x: 200, y: 400 }],
    ];
    expect(polygonArea(withHole)).toBe(1_000_000 - 40_000);
  });

  it('khung bao bám đúng các đỉnh', () => {
    const b = polygonBounds([[{ x: -50, y: 10 }, { x: 150, y: 10 }, { x: 150, y: 90 }]]);
    expect(b).toEqual({ x: -50, y: 10, w: 200, h: 80 });
  });

  it('tấm chữ nhật thì ô dùng được gần bằng cả tấm', () => {
    const r = largestInnerRect(rectPolygon(1200, 2400), 10);
    expect(r.w).toBeGreaterThan(1200 * 0.97);
    expect(r.h).toBeGreaterThan(2400 * 0.97);
    expect(r.coverage).toBeGreaterThan(0.95);
  });

  it('tấm vát góc: ô dùng được nhỏ hơn khung bao nhưng vẫn nằm trong tôn', () => {
    const poly = cornerCutPolygon(1200, 2400, 600, 1200);
    const r = largestInnerRect(poly, 10);
    expect(r.w * r.h).toBeLessThan(1200 * 2400);
    expect(r.coverage).toBeGreaterThan(0.5);
    // Bốn góc của ô dùng được phải nằm trong phần tôn còn lại.
    const eps = 1e-6;
    for (const p of [
      { x: r.x + eps, y: r.y + eps },
      { x: r.x + r.w - eps, y: r.y + eps },
      { x: r.x + r.w - eps, y: r.y + r.h - eps },
      { x: r.x + eps, y: r.y + r.h - eps },
    ]) {
      expect(pointInPolygon(poly, p)).toBe(true);
    }
  });

  it('tấm hình chữ L: ô dùng được không đè lên phần đã bị cắt mất', () => {
    // Chữ L: khoét hẳn góc trên-phải 600×1200 của tấm 1200×2400.
    const L: Ring[] = [[
      { x: 0, y: 0 }, { x: 1200, y: 0 }, { x: 1200, y: 1200 },
      { x: 600, y: 1200 }, { x: 600, y: 2400 }, { x: 0, y: 2400 },
    ]];
    const r = largestInnerRect(L, 10);
    expect(r.w).toBeGreaterThan(0);
    expect(r.h).toBeGreaterThan(0);
    // Lấy 5×5 điểm rải đều trong ô — tất cả phải nằm trong tôn.
    for (let i = 1; i < 5; i++) {
      for (let j = 1; j < 5; j++) {
        const p = { x: r.x + (r.w * i) / 5, y: r.y + (r.h * j) / 5 };
        expect(pointInPolygon(L, p)).toBe(true);
      }
    }
  });

  it('đọc được toạ độ đỉnh người dùng gõ tay, báo lỗi khi gõ sai', () => {
    const ok = parsePointsText('0 0\n1200,0\n1200 1500\n0 2400');
    expect(ok.error).toBeUndefined();
    expect(ok.ring).toHaveLength(4);
    expect(parsePointsText('0 0\n1200 0').error).toMatch(/ít nhất 3 đỉnh/);
    expect(parsePointsText('0 0\nabc xyz\n1 1').error).toMatch(/không phải số/);
  });
});

// ── 2. Kiểm tra dữ liệu phía trình duyệt ─────────────────────────────────────

describe('kiểm tra dữ liệu tấm thừa (phía trình duyệt)', () => {
  const good = { name: 'thừa lô sườn 15', widthMm: 1200, lengthMm: 2400, polygon: rectPolygon(1200, 2400) };

  it('nhận dữ liệu đúng', () => {
    expect(validateRemnantInput(good)).toBeNull();
  });

  it('bắt buộc có tên', () => {
    expect(validateRemnantInput({ ...good, name: '   ' })).toMatch(/Phải đặt tên/);
  });

  it('kích thước phải là số dương', () => {
    expect(validateRemnantInput({ ...good, widthMm: 0 })).toMatch(/lớn hơn 0/);
    expect(validateRemnantInput({ ...good, lengthMm: -3 })).toMatch(/lớn hơn 0/);
    expect(validateRemnantInput({ ...good, widthMm: Number.NaN })).toMatch(/con số/);
    expect(validateRemnantInput({ ...good, widthMm: 1e9 })).toMatch(/lớn quá mức/);
  });

  it('hình dạng phải hợp lệ', () => {
    expect(validateRemnantInput({ ...good, polygon: [] })).toMatch(/Thiếu hình dạng/);
    expect(validateRemnantInput({ ...good, polygon: [[{ x: 0, y: 0 }, { x: 1, y: 1 }]] }))
      .toMatch(/ít nhất 3 đỉnh/);
  });

  it('chặn đa giác quá nhiều đỉnh', () => {
    const huge: Ring = Array.from({ length: 6000 }, (_, i) => ({ x: i, y: i }));
    expect(validateRemnantInput({ ...good, polygon: [huge] })).toMatch(/quá 5000 đỉnh/);
  });
});

// ── 3. Kiểm tra dữ liệu phía MÁY CHỦ (chính file Functions đang chạy thật) ────

describe('kiểm tra dữ liệu phía máy chủ (functions/api/remnants/_lib.js)', () => {
  // Đường dẫn không phải hằng chuỗi → tsc không cần khai báo kiểu cho file .js.
  const libUrl = new URL('../functions/api/remnants/_lib.js', import.meta.url).href;
  const load = async (): Promise<any> => import(/* @vite-ignore */ libUrl);

  it('từ chối tên rỗng, nhận tên đã cắt khoảng trắng', async () => {
    const lib = await load();
    expect(lib.checkName('   ').error).toMatch(/Phải đặt tên/);
    expect(lib.checkName(123).error).toMatch(/chuỗi chữ/);
    expect(lib.checkName('  thừa lô sườn 15  ').value).toBe('thừa lô sườn 15');
  });

  it('từ chối kích thước không phải số dương', async () => {
    const lib = await load();
    expect(lib.checkDim('1200', 'Chiều rộng').error).toMatch(/con số/);
    expect(lib.checkDim(0, 'Chiều rộng').error).toMatch(/lớn hơn 0/);
    expect(lib.checkDim(-1, 'Chiều rộng').error).toMatch(/lớn hơn 0/);
    expect(lib.checkDim(1200, 'Chiều rộng').value).toBe(1200);
  });

  it('chuẩn hoá đa giác một vòng thành dạng nhiều vòng', async () => {
    const lib = await load();
    const one = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }];
    expect(lib.checkPolygon(one).value).toEqual([one]);
    expect(lib.checkPolygon([]).error).toMatch(/Thiếu hình dạng/);
    expect(lib.checkPolygon([[{ x: 0, y: 'a' }, { x: 1, y: 1 }, { x: 2, y: 2 }]]).error)
      .toMatch(/toạ độ x, y là số/);
  });

  it('chặn payload quá lớn dù Content-Length nói dối', async () => {
    const lib = await load();
    const big = JSON.stringify({ name: 'x'.repeat(200_000) });
    const req = new Request('http://x/api/remnants', {
      method: 'POST',
      headers: { 'content-length': '10' },
      body: big,
    });
    const out = await lib.readJsonBody(req);
    expect(out.error).toMatch(/quá lớn/);
  });

  it('chỉ nhận trạng thái còn / đã dùng', async () => {
    const lib = await load();
    expect(lib.checkStatus('available').value).toBe('available');
    expect(lib.checkStatus('used').value).toBe('used');
    expect(lib.checkStatus('DROP TABLE').error).toMatch(/Trạng thái/);
  });
});

// ── 4. Đường lui khi mất mạng ────────────────────────────────────────────────

describe('kho tôn thừa lúc mất mạng', () => {
  const input = { name: 'thừa lô sườn 15', widthMm: 1200, lengthMm: 2400, polygon: rectPolygon(1200, 2400) };

  const offlineFetch = (() => Promise.reject(new TypeError('Failed to fetch'))) as unknown as typeof fetch;

  const okFetch = (server: Remnant[]): typeof fetch =>
    (async (url: any, init: any) => {
      const u = String(url);
      const method = (init?.method || 'GET').toUpperCase();
      if (method === 'POST') {
        const body = JSON.parse(init.body);
        const r = makeRemnant({ ...body, id: `srv-${server.length + 1}`, polygon: body.polygon });
        server.push(r);
        return new Response(JSON.stringify({ ok: true, remnant: r }), { status: 201 });
      }
      if (method === 'PATCH') {
        const id = decodeURIComponent(u.split('/').pop() as string);
        const i = server.findIndex((x) => x.id === id);
        if (i < 0) return new Response(JSON.stringify({ ok: false, error: 'không thấy' }), { status: 404 });
        server[i] = { ...server[i], ...JSON.parse(init.body) };
        return new Response(JSON.stringify({ ok: true, remnant: server[i] }), { status: 200 });
      }
      if (method === 'DELETE') {
        const id = decodeURIComponent(u.split('/').pop() as string);
        const i = server.findIndex((x) => x.id === id);
        if (i < 0) return new Response(JSON.stringify({ ok: false, error: 'không thấy' }), { status: 404 });
        server.splice(i, 1);
        return new Response(JSON.stringify({ ok: true, deleted: id }), { status: 200 });
      }
      return new Response(JSON.stringify({ ok: true, remnants: server }), { status: 200 });
    }) as unknown as typeof fetch;

  it('mất mạng: vẫn thêm được, ghi vào máy và xếp vào hàng chờ', async () => {
    const storage = memoryStorage();
    const store = createRemnantStore({ fetchFn: offlineFetch, storage, uuid: () => 'u1' });

    const out = await store.add(input);
    expect(out.offline).toBe(true);
    expect(out.value.id).toBe('local-u1');
    expect(out.value.pending).toBe(true);
    expect(out.queued).toBe(1);

    const listed = await store.list('available');
    expect(listed.offline).toBe(true);
    expect(listed.remnants.map((r) => r.name)).toEqual(['thừa lô sườn 15']);
    expect(JSON.parse(storage.getItem(CACHE_KEY) as string)).toHaveLength(1);
    expect(JSON.parse(storage.getItem(QUEUE_KEY) as string)).toHaveLength(1);
  });

  it('mất mạng thì chặn dữ liệu sai NGAY, không ghi bừa vào máy', async () => {
    const storage = memoryStorage();
    const store = createRemnantStore({ fetchFn: offlineFetch, storage });
    await expect(store.add({ ...input, name: '  ' })).rejects.toThrow(/Phải đặt tên/);
    await expect(store.add({ ...input, widthMm: -1 })).rejects.toThrow(/lớn hơn 0/);
    expect(store.cached()).toHaveLength(0);
    expect(store.queue()).toHaveLength(0);
  });

  it('có mạng lại: hàng chờ được đẩy lên, mã tạm đổi thành mã thật', async () => {
    const storage = memoryStorage();
    const server: Remnant[] = [];

    const offline = createRemnantStore({ fetchFn: offlineFetch, storage, uuid: () => 'u1' });
    const added = await offline.add(input);
    await offline.patch(added.value.id, { note: 'giá B2' });
    expect(offline.queue()).toHaveLength(1); // sửa tấm chờ thì gộp thẳng vào việc thêm

    const online = createRemnantStore({ fetchFn: okFetch(server), storage });
    const sync = await online.sync();
    expect(sync.sent).toBe(1);
    expect(sync.left).toBe(0);
    expect(server).toHaveLength(1);
    expect(server[0].name).toBe('thừa lô sườn 15');
    expect(server[0].note).toBe('giá B2');
    expect(online.cached()[0].id).toBe('srv-1');
    expect(online.cached()[0].pending).toBe(false);
  });

  it('hàng chờ không tắc vĩnh viễn khi máy chủ chê một việc', async () => {
    const storage = memoryStorage();
    const server: Remnant[] = [];
    const store = createRemnantStore({ fetchFn: okFetch(server), storage });
    // Sửa một tấm không tồn tại → máy chủ trả 404, việc đó phải bị bỏ chứ không lặp mãi.
    storage.setItem(QUEUE_KEY, JSON.stringify([
      { kind: 'patch', id: 'khong-co', patch: { note: 'x' } },
      { kind: 'add', localId: 'local-z', input },
    ]));
    const sync = await store.sync();
    expect(sync.left).toBe(0);
    expect(server).toHaveLength(1);
  });

  it('có mạng: thêm → liệt kê → đánh dấu đã dùng → xoá', async () => {
    const server: Remnant[] = [];
    const store = createRemnantStore({ fetchFn: okFetch(server), storage: memoryStorage() });
    const added = await store.add(input);
    expect(added.offline).toBe(false);

    expect((await store.list('all')).remnants).toHaveLength(1);

    const used = await store.markUsed(added.value.id);
    expect(used.value?.status).toBe('used');
    expect(server[0].status).toBe('used');

    await store.remove(added.value.id);
    expect(server).toHaveLength(0);
    expect(store.cached()).toHaveLength(0);
  });
});

// ── 5. Ưu tiên nhét vào tôn thừa khi xếp ─────────────────────────────────────

describe('xếp phôi có dùng tôn thừa', () => {
  it('nhét vào tấm thừa TRƯỚC rồi mới mở tấm mới', () => {
    const parts = [rectPart('P0', 400, 400, 4)];
    // nest() giả: mỗi tấm nhận tối đa 2 chi tiết, để kiểm tra đúng luồng điều phối.
    const stub = (input: NestInput): NestResult => {
      const cap = 2;
      const sheets = [];
      let left = input.parts.reduce((a, p) => a + p.qty, 0);
      let idx = 0;
      while (left > 0) {
        const n = Math.min(cap, left);
        sheets.push({
          index: idx,
          width: input.params.sheetW,
          height: input.params.sheetH,
          placements: Array.from({ length: n }, (_, i) => ({
            partId: 'P0', instance: i, rotationDeg: 0, mirrored: false, x: i * 500, y: 0,
          })),
          usedArea: n * 160_000,
          utilization: 0.1,
        });
        left -= n;
        idx++;
      }
      return { sheets, unplaced: [], utilization: 0.1, elapsedMs: 1, iterations: 1, params: input.params };
    };

    const rem = makeRemnant({ id: 'r1', name: 'thừa lô sườn 15' });
    const out = nestWithRemnants(parts, { ...DEFAULT_NEST_PARAMS, timeLimitMs: 1000 }, [rem], { nest: stub });

    expect(out.sheets[0].source).toBe('remnant');
    expect(out.sheets[0].remnantName).toBe('thừa lô sườn 15');
    expect(out.sheets[0].placements).toHaveLength(2);
    // 2 con còn lại phải rơi sang tấm mới.
    expect(out.newSheets).toBe(1);
    expect(out.sheets[1].source).toBe('new');
    // Số hiệu bản sao chạy liên tục trên cả phương án, không lặp lại.
    const ins = out.sheets.flatMap((s) => s.placements.map((p) => p.instance));
    expect(new Set(ins).size).toBe(ins.length);
    expect(out.remnantsUsed[0]).toMatchObject({ id: 'r1', placed: 2 });
  });

  it('không chọn tấm thừa nào thì xếp y như cũ, toàn tấm mới', () => {
    const parts = [rectPart('P0', 400, 400, 2)];
    const out = nestWithRemnants(parts, { ...DEFAULT_NEST_PARAMS, timeLimitMs: 1200 }, []);
    expect(out.sheets.every((s) => s.source === 'new')).toBe(true);
    expect(out.remnantsUsed).toHaveLength(0);
    expect(out.unplaced).toEqual([]);
  });

  it('bỏ qua tấm thừa bé hơn lề, có ghi rõ lý do', () => {
    const parts = [rectPart('P0', 400, 400, 1)];
    const tiny = makeRemnant({ id: 'r-tiny', name: 'mẩu vụn', widthMm: 15, lengthMm: 15 });
    const out = nestWithRemnants(parts, { ...DEFAULT_NEST_PARAMS, timeLimitMs: 1200 }, [tiny]);
    expect(out.remnantsUsed).toHaveLength(0);
    expect(out.skipped[0].id).toBe('r-tiny');
    expect(out.skipped[0].reason).toMatch(/nhỏ hơn lề/);
  });

  it('engine THẬT: chi tiết vào hết tấm thừa, không phải mở tấm mới nào', () => {
    // 4 chi tiết 400×400 thừa sức nằm gọn trong tấm thừa 1200×2400.
    const parts = [rectPart('P0', 400, 400, 4)];
    const rem = makeRemnant({ id: 'r1', name: 'thừa lô sườn 15' });
    const out = nestWithRemnants(
      parts,
      { ...DEFAULT_NEST_PARAMS, timeLimitMs: 3000, rotationStep: 90 },
      [rem],
      {}
    );
    console.log(
      `  tấm thừa "${rem.name}": nhét ${out.remnantsUsed[0]?.placed ?? 0}/4 chi tiết`
      + ` · tấm mới phải mở: ${out.newSheets}`
      + ` · tận dụng ${(out.utilization * 100).toFixed(1)}%`
    );
    expect(out.sheets[0].source).toBe('remnant');
    expect(out.remnantsUsed[0].placed).toBe(4);
    expect(out.newSheets).toBe(0);
    expect(out.unplaced).toEqual([]);
  }, 60_000);

  it('engine THẬT: tấm thừa vát góc vẫn xếp được và không chi tiết nào lọt ra ngoài tôn', () => {
    const poly = cornerCutPolygon(1500, 2000, 700, 900);
    const rem = makeRemnant({ id: 'r2', name: 'thừa vát góc', widthMm: 1500, lengthMm: 2000, polygon: poly });
    const parts = [rectPart('P0', 300, 300, 6)];
    const out = nestWithRemnants(
      parts,
      { ...DEFAULT_NEST_PARAMS, timeLimitMs: 3000, rotationStep: 90 },
      [rem],
      {}
    );
    const sheet = out.sheets[0];
    expect(sheet.source).toBe('remnant');
    expect(sheet.placements.length).toBeGreaterThan(0);
    console.log(`  tấm vát góc: nhét ${sheet.placements.length}/6 chi tiết · tấm mới: ${out.newSheets}`);
    // Mọi đỉnh của mọi chi tiết phải nằm trong phần tôn còn thật.
    for (const pl of sheet.placements) {
      const p = parts[0];
      for (const v of p.rings[0]) {
        const a = (pl.rotationDeg * Math.PI) / 180;
        const sx = pl.mirrored ? -v.x : v.x;
        const pt = {
          x: sx * Math.cos(a) - v.y * Math.sin(a) + pl.x,
          y: sx * Math.sin(a) + v.y * Math.cos(a) + pl.y,
        };
        expect(pointInPolygon(poly, pt)).toBe(true);
      }
    }
  }, 60_000);

  it('engine thật của src/nest vẫn dùng được trực tiếp (không bị module này phá)', () => {
    const r = realNest({
      parts: [rectPart('P0', 500, 500, 2)],
      params: { ...DEFAULT_NEST_PARAMS, timeLimitMs: 1000, rotationStep: 90 },
    });
    expect(r.sheets.length).toBeGreaterThan(0);
  }, 30_000);
});
