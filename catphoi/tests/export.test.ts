import { describe, it, expect } from 'vitest';
import { parseDxf } from '../src/core/dxf-parse';
import { exportAllSheetsDxfR12, exportSheetDxfR12, sheetFileName } from '../src/core/dxf-export';
import { generateGcode, gcodeFileName } from '../src/core/gcode';
import { DEFAULT_GCODE_OPTIONS, applyPlacementRing, ringBBox, signedArea, type Part, type Ring, type SheetLayout } from '../src/types';
import { labelPoint as labelPointOf, pointInPart, pointSegDistance, ringLength } from '../src/core/geometry';
import { FIXTURE_MISSING_MSG, hasFixture, readFixture } from './helpers';

/** Lấy các nhãn trên layer LABEL của file DXF xuất ra: toạ độ + nội dung. */
function readLabels(dxf: string): { x: number; y: number; text: string }[] {
  const out: { x: number; y: number; text: string }[] = [];
  const re = /0\r\nTEXT\r\n8\r\nLABEL\r\n10\r\n(-?[\d.]+)\r\n20\r\n(-?[\d.]+)\r\n30\r\n0\r\n40\r\n[\d.]+\r\n1\r\n([^\r]*)\r\n/g;
  for (const m of dxf.matchAll(re)) out.push({ x: parseFloat(m[1]), y: parseFloat(m[2]), text: m[3] });
  return out;
}

/**
 * Đọc các vòng cắt (layer CUT) từ file DXF xuất ra, GIỮ NGUYÊN toạ độ tuyệt đối.
 * Không dùng parseDxf ở đây vì parseDxf dịch mỗi chi tiết về gốc riêng, làm mất
 * đúng cái độ lệch 1mm mà bài kiểm tra kerf cần đo.
 */
function readCutRings(dxf: string): Ring[] {
  const out: Ring[] = [];
  for (const block of dxf.split('0\r\nPOLYLINE\r\n').slice(1)) {
    if (!/^8\r\nCUT\r\n/.test(block)) continue;
    const body = block.split('0\r\nSEQEND')[0];
    const ring: Ring = [];
    const re = /0\r\nVERTEX\r\n8\r\nCUT\r\n10\r\n(-?[\d.]+)\r\n20\r\n(-?[\d.]+)\r\n/g;
    for (const m of body.matchAll(re)) ring.push({ x: parseFloat(m[1]), y: parseFloat(m[2]) });
    if (ring.length >= 3) out.push(ring);
  }
  return out;
}

/** Layout chỉ có 1 chi tiết, đặt gọn trong tấm rộng rãi. */
function soloLayout(part: Part, rotationDeg = 0): SheetLayout {
  const pl = { partId: part.id, instance: 0, rotationDeg, mirrored: false, x: 0, y: 0 };
  const b = ringBBox(applyPlacementRing(part.rings[0], pl));
  pl.x = 100 - b.minX;
  pl.y = 100 - b.minY;
  return {
    index: 0,
    width: Math.ceil(b.maxX - b.minX) + 400,
    height: Math.ceil(b.maxY - b.minY) + 400,
    placements: [pl],
    usedArea: part.area,
    utilization: 0.3,
  };
}

/** Khoảng cách từ 1 điểm tới biên của vòng kín. */
function distToRing(pt: { x: number; y: number }, ring: Ring): number {
  let best = Infinity;
  for (let i = 0; i < ring.length; i++) {
    const d = pointSegDistance(pt, ring[i], ring[(i + 1) % ring.length]);
    if (d < best) best = d;
  }
  return best;
}

const d = hasFixture() ? describe : describe.skip;
if (!hasFixture()) console.warn(FIXTURE_MISSING_MSG);

/** Dựng 1 layout giả: xếp 15 chi tiết theo lưới, mỗi cái xoay một góc lẻ. */
function fakeLayout(parts: Part[]): SheetLayout {
  const placements = parts.map((p, i) => ({
    partId: p.id,
    instance: 0,
    rotationDeg: (i * 37) % 360,
    mirrored: false,
    x: 0,
    y: 0,
  }));
  // dịch từng chi tiết cho nằm gọn trong tấm rất lớn, không cần tránh chồng lấn
  let x = 0;
  placements.forEach((pl, i) => {
    const b = ringBBox(applyPlacementRing(parts[i].rings[0], pl));
    pl.x = x - b.minX + 50;
    pl.y = 50 - b.minY;
    x += b.maxX - b.minX + 100;
  });
  const width = x + 100;
  return {
    index: 0,
    width,
    height: 8000,
    placements,
    usedArea: parts.reduce((s, p) => s + p.area, 0),
    utilization: 0.5,
  };
}

d('US3 — xuất file đem cắt', () => {
  const { parts } = parseDxf(readFixture());
  const byId = new Map(parts.map((p) => [p.id, p]));
  const layout = fakeLayout(parts);
  const dxf = exportSheetDxfR12(layout, byId);

  it('DXF xuất ra là R12 ASCII, có đủ 3 layer', () => {
    expect(dxf).toContain('AC1009');
    expect(dxf).toContain('CUT');
    expect(dxf).toContain('SHEET');
    expect(dxf).toContain('LABEL');
    expect(dxf.endsWith('EOF\r\n')).toBe(true);
  });

  it('round-trip: đọc lại bằng chính parser ra đúng 15 chi tiết, sai số ≤ 0.01mm', () => {
    const back = parseDxf(dxf);
    expect(back.parts.length).toBe(15);

    // ghép chi tiết đọc lại với chi tiết gốc theo diện tích
    const expected = parts.map((p, i) => {
      const ring = applyPlacementRing(p.rings[0], layout.placements[i]);
      const b = ringBBox(ring);
      return { id: p.id, ring: ring.map((q) => ({ x: q.x - b.minX, y: q.y - b.minY })), area: p.area };
    });
    let worst = 0;
    for (const got of back.parts) {
      const exp = expected.find((e) => Math.abs(e.area - got.area) < Math.max(1, e.area * 1e-6));
      expect(exp, `không tìm được chi tiết gốc khớp với ${got.id}`).toBeTruthy();
      const a = exp!.ring;
      const b = got.rings[0];
      expect(b.length).toBe(a.length);
      for (let i = 0; i < a.length; i++) {
        worst = Math.max(worst, Math.hypot(a[i].x - b[i].x, a[i].y - b[i].y));
      }
    }
    console.log(`  sai số round-trip lớn nhất: ${worst.toFixed(6)} mm`);
    expect(worst).toBeLessThanOrEqual(0.01);
  });

  it('xuất 1 file nhiều tấm cạnh nhau', () => {
    const all = exportAllSheetsDxfR12([layout, { ...layout, index: 1 }], byId);
    expect(all).toContain('TAM 01');
    expect(all).toContain('TAM 02');
    const back = parseDxf(all);
    expect(back.parts.length).toBe(30);
  });

  it('tên file đúng quy ước', () => {
    const s: SheetLayout = { ...layout, width: 2000, height: 6000 };
    expect(sheetFileName(s, 'dxf')).toBe('tam-01_2000x6000.dxf');
    expect(gcodeFileName({ ...s, index: 2 }, 'nc')).toBe('tam-03_2000x6000.nc');
  });

  it('G-code: mỗi vòng cắt đúng 1 cặp bật/tắt mỏ, mọi toạ độ nằm trong tấm', () => {
    const nc = generateGcode(layout, byId);
    const on = (nc.match(/^M07$/gm) || []).length;
    const off = (nc.match(/^M08$/gm) || []).length;
    const rings = parts.reduce((s, p) => s + p.rings.length, 0);
    expect(on).toBe(rings);
    expect(off).toBe(rings);
    let bad = 0;
    for (const m of nc.matchAll(/^G0[01] X(-?[\d.]+) Y(-?[\d.]+)/gm)) {
      const x = parseFloat(m[1]);
      const y = parseFloat(m[2]);
      if (x < -1e-9 || y < -1e-9 || x > layout.width + 1e-9 || y > layout.height + 1e-9) bad++;
    }
    expect(bad).toBe(0);
    expect(nc).toContain('G21');
    expect(nc).toContain('G90');
    expect(nc.trimEnd().endsWith('M30')).toBe(true);
  });

  it('G-code: đổi được mã mỏ cắt, feed, số dòng N', () => {
    const nc = generateGcode(layout, byId, {
      ...DEFAULT_GCODE_OPTIONS, torchOn: 'M03', torchOff: 'M05', feedRate: 900, lineNumbers: true,
    });
    expect(nc).toContain('M03');
    expect(nc).toContain('M05');
    expect(nc).toContain('F900');
    expect(nc).toMatch(/^N\d+ G21$/m);
  });
});

d('Việc 2 — nhãn trong DXF nằm trong hình chi tiết', () => {
  const { parts } = parseDxf(readFixture());
  const byId = new Map(parts.map((p) => [p.id, p]));

  it('cả 15 chi tiết: nhãn layer LABEL nằm TRONG hình của chính nó', () => {
    parts.forEach((p, i) => {
      const layout = soloLayout(p, (i * 29) % 360);
      const dxf = exportSheetDxfR12(layout, byId);
      const labels = readLabels(dxf);
      expect(labels.length, `${p.id}: thiếu nhãn`).toBe(1);
      const rings = p.rings.map((r) => applyPlacementRing(r, layout.placements[0]));
      expect(pointInPart(labels[0], rings), `${p.id}: nhãn rơi ra ngoài hình`).toBe(true);
    });
  });
});

d('Việc 3 — tên chi tiết do người dùng tự đặt', () => {
  const { parts } = parseDxf(readFixture());
  const byId = new Map(parts.map((p) => [p.id, p]));
  const layout = fakeLayout(parts);
  const labels = { P0: 'Sườn 15 mạn trái', P3: 'Đà ngang boong' };

  it('DXF: tên tự đặt vào layer LABEL, bỏ dấu cho hợp R12', () => {
    const dxf = exportSheetDxfR12(layout, byId, { labels });
    const texts = readLabels(dxf).map((t) => t.text);
    expect(texts).toContain('Suon 15 man trai');
    expect(texts).toContain('Da ngang boong');
    expect(texts).toContain('P1'); // chi tiết không đặt tên thì giữ mã cũ
    expect(dxf).not.toContain('Sườn');
    // toàn bộ file DXF phải là ASCII thuần
    expect(/[^\x00-\x7F]/.test(dxf)).toBe(false);
  });

  it('G-code: tên tự đặt vào comment chi tiết', () => {
    const nc = generateGcode(layout, byId, DEFAULT_GCODE_OPTIONS, { labels });
    expect(nc).toContain('(CHI TIET Suon 15 man trai)');
    expect(nc).toContain('(CHI TIET Da ngang boong)');
    expect(nc).toContain('(CHI TIET P1)');
    expect(/[^\x00-\x7F]/.test(nc)).toBe(false);
  });
});

d('Việc 4 — bù kerf', () => {
  const { parts } = parseDxf(readFixture());
  const byId = new Map(parts.map((p) => [p.id, p]));

  it('kerf = 0 (mặc định) thì file y hệt như trước, không đổi hình', () => {
    const layout = soloLayout(parts[4]);
    const a = exportSheetDxfR12(layout, byId);
    const b = exportSheetDxfR12(layout, byId, { kerf: 0 });
    expect(a).toBe(b);
    const nc = generateGcode(layout, byId);
    expect(nc).toContain('(KHONG BU KERF');
  });

  it('kerf = 2mm: đường bao ngoài nở đúng 1mm mỗi phía', () => {
    for (const id of ['P0', 'P4', 'P9']) {
      const part = byId.get(id)!;
      const layout = soloLayout(part);
      const cut0 = readCutRings(exportSheetDxfR12(layout, byId, { kerf: 0 }));
      const cut2 = readCutRings(exportSheetDxfR12(layout, byId, { kerf: 2 }));
      expect(cut0.length).toBe(1);
      expect(cut2.length).toBe(1);
      const ring0 = cut0[0];
      const ring2 = cut2[0];
      expect(ring2.length).toBe(ring0.length);

      // 1) diện tích tăng ≈ chu vi × 1mm
      const chuVi = ringLength(ring0);
      const dA = Math.abs(signedArea(ring2)) - Math.abs(signedArea(ring0));
      expect(dA / chuVi, `${id}: nở trung bình`).toBeGreaterThan(0.98);
      expect(dA / chuVi, `${id}: nở trung bình`).toBeLessThan(1.05);

      // 2) mọi đỉnh của đường cắt mới cách hình gốc ≥ 1mm (không bao giờ ăn vào chi tiết)
      const ds = ring2.map((pt) => distToRing(pt, ring0)).sort((a, b) => a - b);
      const median = ds[Math.floor(ds.length / 2)];
      console.log(`  ${id}: nở trung bình ${(dA / chuVi).toFixed(3)}mm · đỉnh gần nhất ${ds[0].toFixed(3)}mm · trung vị ${median.toFixed(3)}mm`);
      expect(ds[0], `${id}: có đỉnh ăn vào trong hình`).toBeGreaterThan(0.995);
      expect(median, `${id}: trung vị phải đúng 1mm`).toBeLessThan(1.02);
    }
  });

  it('kerf = 2mm: lỗ bị THU nhỏ 1mm mỗi phía (lỗ thành phẩm mới đúng cỡ)', () => {
    // chi tiết vuông 1000×1000 có lỗ vuông 400×400 ở giữa
    const outer: Ring = [
      { x: 0, y: 0 }, { x: 1000, y: 0 }, { x: 1000, y: 1000 }, { x: 0, y: 1000 },
    ];
    const hole: Ring = [
      { x: 300, y: 300 }, { x: 300, y: 700 }, { x: 700, y: 700 }, { x: 700, y: 300 },
    ];
    const part: Part = {
      id: 'PH', rings: [outer, hole], area: 1000 * 1000 - 400 * 400,
      bbox: ringBBox(outer), vertexCount: 8, minWidth: 1000, maxLength: Math.hypot(1000, 1000),
      qty: 1, enabled: true, fitsSheet: true,
    };
    const map = new Map([[part.id, part]]);
    const layout = soloLayout(part);
    const back = parseDxf(exportSheetDxfR12(layout, map, { kerf: 2 }));
    expect(back.parts.length).toBe(1);
    const got = back.parts[0];
    expect(got.rings.length).toBe(2);
    const bo = ringBBox(got.rings[0]);
    const bh = ringBBox(got.rings[1]);
    // bao ngoài 1000 → 1002, lỗ 400 → 398
    expect(bo.maxX - bo.minX).toBeCloseTo(1002, 6);
    expect(bo.maxY - bo.minY).toBeCloseTo(1002, 6);
    expect(bh.maxX - bh.minX).toBeCloseTo(398, 6);
    expect(bh.maxY - bh.minY).toBeCloseTo(398, 6);
  });

  it('G-code cũng bù kerf và cảnh báo phải tắt bù bên máy', () => {
    const part = byId.get('P4')!;
    const layout = soloLayout(part);
    const nc0 = generateGcode(layout, byId, DEFAULT_GCODE_OPTIONS, { kerf: 0 });
    const nc2 = generateGcode(layout, byId, DEFAULT_GCODE_OPTIONS, { kerf: 2 });
    expect(nc2).toContain('DA BU KERF 2mm');
    expect(nc2).toContain('PHAI TAT BU KERF');
    const xs = (t: string) => [...t.matchAll(/^G01 X(-?[\d.]+) Y(-?[\d.]+)/gm)].map((m) => ({ x: +m[1], y: +m[2] }));
    const a = xs(nc0);
    const b = xs(nc2);
    expect(b.length).toBe(a.length);
    // đường chạy mỏ dịch ra ngoài, không trùng đường cũ
    const moved = a.filter((p, i) => Math.hypot(p.x - b[i].x, p.y - b[i].y) > 0.5).length;
    expect(moved).toBeGreaterThan(a.length * 0.9);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// VIỆC 1 — đang xem phương án nào thì TẢI RA ĐÚNG phương án đó
// ─────────────────────────────────────────────────────────────────────────────
import {
  pickPlan, planAllDxf, planAllFileName, planFileName, planSheetDxf, planSheetGcode,
  planZipFiles, planZipName,
} from '../src/ui/download';
import { comparePlans, rankPlans, runMultiNest } from '../src/ui/nest-multi-core';
import { fitLabel, inscribedRadius } from '../src/ui/render';
import { exportLabels, fullName, extraName } from '../src/ui/labels';
import { DEFAULT_NEST_PARAMS, type NestResult } from '../src/types';

/** Chi tiết vuông đơn giản, đủ cho engine thật. */
function squarePart(id: string, w: number, h: number, qty = 1): Part {
  const ring: Ring = [{ x: 0, y: 0 }, { x: w, y: 0 }, { x: w, y: h }, { x: 0, y: h }];
  return {
    id, rings: [ring], area: w * h,
    bbox: { minX: 0, minY: 0, maxX: w, maxY: h },
    vertexCount: 4, minWidth: Math.min(w, h), maxLength: Math.hypot(w, h),
    qty, enabled: true, fitsSheet: true,
  };
}

/** Một phương án giả: 1 tấm, chi tiết đặt ở đúng toạ độ cho trước. */
function planAt(xs: number[][], part: Part): NestResult {
  const sheet: SheetLayout = {
    index: 0, width: 2000, height: 6000,
    placements: xs.map(([x, y], i) => ({
      partId: part.id, instance: i, rotationDeg: 0, mirrored: false, x, y,
    })),
    usedArea: xs.length * part.area,
    utilization: (xs.length * part.area) / (2000 * 6000),
  };
  return {
    sheets: [sheet], unplaced: [], utilization: sheet.utilization,
    elapsedMs: 1, iterations: 1, params: DEFAULT_NEST_PARAMS,
  };
}

describe('VIỆC 1 — tải file theo đúng phương án đang xem', () => {
  const part = squarePart('P0', 400, 500, 2);
  const byId = new Map([[part.id, part]]);
  // Hai phương án khác nhau RÕ RỆT về toạ độ, để so được bằng con số.
  const plan1 = planAt([[100, 100], [700, 100]], part);
  const plan2 = planAt([[300, 2500], [1100, 4000]], part);
  const plans = [plan1, plan2];

  it('đang xem phương án 2 thì DXF ra đúng TOẠ ĐỘ của phương án 2', () => {
    const dxf2 = planSheetDxf(plans, 1, 0, byId);
    const rings2 = readCutRings(dxf2);
    expect(rings2).toHaveLength(2);
    const goc = rings2.map((r) => ringBBox(r)).sort((a, b) => a.minY - b.minY);
    expect(goc[0].minX).toBeCloseTo(300, 6);
    expect(goc[0].minY).toBeCloseTo(2500, 6);
    expect(goc[1].minX).toBeCloseTo(1100, 6);
    expect(goc[1].minY).toBeCloseTo(4000, 6);

    // Và KHÁC hẳn phương án 1.
    const dxf1 = planSheetDxf(plans, 0, 0, byId);
    expect(dxf1).not.toBe(dxf2);
    const goc1 = readCutRings(dxf1).map((r) => ringBBox(r)).sort((a, b) => a.minX - b.minX);
    expect(goc1[0].minX).toBeCloseTo(100, 6);
    expect(goc1[0].minY).toBeCloseTo(100, 6);
    console.log(
      `  phương án 1 đặt tại (${goc1[0].minX},${goc1[0].minY})`
      + ` · phương án 2 đặt tại (${goc[0].minX},${goc[0].minY})`
    );
  });

  it('G-code cũng ra đúng phương án đang xem', () => {
    // Chỉ xét ĐƯỜNG CẮT G01; G00 cuối chương trình là lệnh về gốc máy (0,0).
    const cutY = (t: string) => [...t.matchAll(/^G01 X(-?[\d.]+) Y(-?[\d.]+)/gm)].map((m) => +m[2]);
    const ys = cutY(planSheetGcode(plans, 1, 0, byId, DEFAULT_GCODE_OPTIONS));
    // Phương án 2 đặt từ y = 2500 trở lên, không có nhát cắt nào ở vùng y < 2000.
    expect(Math.min(...ys)).toBeGreaterThan(2000);
    const ys1 = cutY(planSheetGcode(plans, 0, 0, byId, DEFAULT_GCODE_OPTIONS));
    expect(Math.min(...ys1)).toBeLessThan(200);
  });

  it('gói .zip và "1 file nhiều tấm" cũng theo phương án đang xem', () => {
    const zip2 = planZipFiles(plans, 1, byId, 'dxf', DEFAULT_GCODE_OPTIONS);
    expect(zip2).toHaveLength(1);
    expect(zip2[0].name).toBe('pa2-tam-01_2000x6000.dxf');
    expect(readCutRings(zip2[0].content).map((r) => ringBBox(r).minY).sort((a, b) => a - b)[0])
      .toBeCloseTo(2500, 6);

    const all2 = planAllDxf(plans, 1, byId);
    expect(readCutRings(all2).map((r) => ringBBox(r).minY).sort((a, b) => a - b)[0])
      .toBeCloseTo(2500, 6);

    expect(planAllFileName(0)).toBe('tat-ca-tam.dxf');
    expect(planAllFileName(1)).toBe('pa2-tat-ca-tam.dxf');
    expect(planZipName(0, 'gcode')).toBe('xep-phoi-gcode.zip');
    expect(planZipName(2, 'gcode')).toBe('pa3-xep-phoi-gcode.zip');
    expect(planFileName(0, plan1.sheets[0], 'dxf')).toBe('tam-01_2000x6000.dxf');
  });

  it('chỉ số phương án hỏng thì tự kẹp lại, không nổ', () => {
    expect(pickPlan(plans, -5)).toBe(plan1);
    expect(pickPlan(plans, 99)).toBe(plan2);
    expect(pickPlan([], 0)).toBeNull();
    expect(() => planSheetDxf(plans, 0, 7, byId)).toThrow(/Không tìm thấy tấm/);
  });

  it('xếp hạng: ít tấm trước, rồi % dùng tôn cao hơn; bỏ phương án trùng', () => {
    const it2 = { ...plan1, sheets: [plan1.sheets[0], { ...plan1.sheets[0], index: 1 }] };
    const ranked = rankPlans([it2 as NestResult, plan2, plan1, plan1]);
    expect(ranked).toHaveLength(3);
    expect(ranked[0].sheets).toHaveLength(1);
    expect(ranked[2].sheets).toHaveLength(2);
    expect(comparePlans(plan1, it2 as NestResult)).toBeLessThan(0);
  });

  it('ENGINE THẬT: ra nhiều phương án, tải phương án nào ra đúng phương án đó', () => {
    const parts = [squarePart('P0', 500, 700, 8), squarePart('P1', 300, 900, 6)];
    const map = new Map(parts.map((p) => [p.id, p]));
    const out = runMultiNest(parts, { ...DEFAULT_NEST_PARAMS, timeLimitMs: 6000, rotationStep: 90 });
    console.log(
      `  engine thật (nestMulti): ${out.plans.length} phương án · `
      + out.plans.map((p) => `${p.sheets.length} tấm ${(p.utilization * 100).toFixed(1)}%`).join(' | ')
    );
    expect(out.plans.length).toBeGreaterThanOrEqual(1);
    expect(out.plans.length).toBeLessThanOrEqual(5);

    // Với MỖI phương án, file tải ra phải khớp toạ độ của CHÍNH nó.
    out.plans.forEach((plan, pi) => {
      const dxf = planSheetDxf(out.plans, pi, 0, map);
      const got = readCutRings(dxf).map((r) => ringBBox(r));
      const want = plan.sheets[0].placements.map((pl) => {
        const p = map.get(pl.partId)!;
        return ringBBox(applyPlacementRing(p.rings[0], pl));
      });
      expect(got.length).toBe(want.length);
      const key = (b: { minX: number; minY: number }) => `${b.minX.toFixed(3)}|${b.minY.toFixed(3)}`;
      expect(new Set(got.map(key))).toEqual(new Set(want.map(key)));
    });
  }, 120_000);
});

// ─────────────────────────────────────────────────────────────────────────────
// VIỆC 4 — tên mã phôi: "P3 · mạn 15"
// ─────────────────────────────────────────────────────────────────────────────
describe('VIỆC 4 — mã P luôn còn, tên chỉ ghép thêm', () => {
  const p0 = squarePart('P0', 100, 100);
  const p3 = { ...squarePart('P3', 100, 100), dxfLabel: 'mạn 15' } as Part;
  const p7 = { ...squarePart('P7', 100, 100), dxfLabel: '   ' } as Part;

  it('không có tên thì chỉ hiện mã P, không có dấu chấm thừa', () => {
    expect(fullName(p0)).toBe('P0');
    expect(fullName(p7)).toBe('P7');
    expect(extraName(p0)).toBe('');
  });

  it('tên đọc từ DXF được ghép sau mã P', () => {
    expect(fullName(p3)).toBe('P3 · mạn 15');
  });

  it('tên founder tự gõ ĐÈ tên đọc từ DXF', () => {
    expect(fullName(p3, { P3: 'sườn mũi' })).toBe('P3 · sườn mũi');
    // Gõ trùng đúng mã P thì coi như không đặt tên.
    expect(fullName(p3, { P3: 'P3' })).toBe('P3');
  });

  it('bảng nhãn cho bộ xuất file chỉ chứa chi tiết CÓ tên', () => {
    const labels = exportLabels([p0, p3, p7], { P0: 'đà ngang' });
    expect(labels).toEqual({ P0: 'P0 · đà ngang', P3: 'P3 · mạn 15' });
  });

  it('DXF và G-code nhận tên đầy đủ, bỏ dấu, vẫn ASCII thuần', () => {
    const part = { ...squarePart('P3', 600, 900), dxfLabel: 'mạn 15' } as Part;
    const byId = new Map([[part.id, part]]);
    const layout = soloLayout(part);
    const labels = exportLabels([part]);
    const dxf = exportSheetDxfR12(layout, byId, { labels });
    const texts = readLabels(dxf).map((t) => t.text);
    expect(texts).toContain('P3 man 15');
    expect(/[^\x00-\x7F]/.test(dxf)).toBe(false);

    const nc = generateGcode(layout, byId, DEFAULT_GCODE_OPTIONS, { labels });
    expect(nc).toContain('(CHI TIET P3 man 15)');
    expect(/[^\x00-\x7F]/.test(nc)).toBe(false);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// VIỆC 5 — nhãn tên dài KHÔNG được lòi ra ngoài hình
// ─────────────────────────────────────────────────────────────────────────────
describe('VIỆC 5 — nhãn co / xuống dòng / cắt bớt cho vừa bề ngang', () => {
  /** Đo giả: mỗi ký tự rộng đúng 0,6 × cỡ chữ (xấp xỉ font sans thật). */
  const measure = (t: string, font: number) => t.length * font * 0.6;

  it('tên ngắn, chỗ rộng: giữ nguyên 1 dòng cỡ chữ to nhất', () => {
    const fit = fitLabel('P3', measure, { maxWidth: 200, maxHeight: 200 });
    expect(fit.lines).toEqual(['P3']);
    expect(fit.font).toBe(11);
    expect(fit.clipped).toBe(false);
  });

  it('LỖI THẬT của thợ trước: tên 16 ký tự trên thanh sườn rộng 250mm', () => {
    // 250mm ở tỉ lệ vẽ thật (~0,17 px/mm) ≈ 42px bề ngang.
    const box = { maxWidth: 42, maxHeight: 42 };
    const fit = fitLabel('P12 · sườn mạn trái', measure, box);
    console.log(`  → ${fit.lines.length} dòng, cỡ ${fit.font}px: ${JSON.stringify(fit.lines)}`);
    for (const line of fit.lines) {
      expect(measure(line, fit.font), `dòng "${line}" vẫn lòi ra ngoài`)
        .toBeLessThanOrEqual(box.maxWidth);
    }
    expect(fit.lines.length * fit.font * 1.15).toBeLessThanOrEqual(box.maxHeight + 1e-9);
  });

  it('tách 2 dòng đúng ở dấu " · "', () => {
    const fit = fitLabel('P3 · mạn 15', measure, { maxWidth: 45, maxHeight: 60 });
    expect(fit.lines).toEqual(['P3', 'mạn 15']);
  });

  it('chỗ quá hẹp thì cắt bớt kèm dấu ba chấm, KHÔNG BAO GIỜ tràn', () => {
    const box = { maxWidth: 14, maxHeight: 10 };
    const fit = fitLabel('P9 · đà ngang boong sau', measure, box);
    expect(fit.clipped).toBe(true);
    expect(fit.lines).toHaveLength(1);
    expect(fit.lines[0].endsWith('…')).toBe(true);
    expect(measure(fit.lines[0], fit.font)).toBeLessThanOrEqual(box.maxWidth);
  });

  it('không tên nào trong 15 chi tiết thật lòi ra khỏi hình', () => {
    if (!hasFixture()) return;
    const { parts } = parseDxf(readFixture());
    const layout = fakeLayout(parts);
    const s = 0.17; // tỉ lệ vẽ xấp xỉ như trên màn 1366×768
    let worstRatio = 0;
    for (const pl of layout.placements) {
      const part = parts.find((p) => p.id === pl.partId)!;
      const rings = part.rings.map((r) => applyPlacementRing(r, pl));
      const at = labelPointOf(rings);
      const rPx = inscribedRadius(rings, at) * s;
      const box = { maxWidth: Math.max(8, rPx * 1.9), maxHeight: Math.max(7, rPx * 1.9) };
      const name = `${part.id} · sườn mạn trái số 12`;
      const fit = fitLabel(name, measure, box);
      for (const line of fit.lines) {
        const w = measure(line, fit.font);
        worstRatio = Math.max(worstRatio, w / box.maxWidth);
        expect(w, `${part.id}: nhãn "${line}" lòi ra ngoài hình`).toBeLessThanOrEqual(box.maxWidth);
      }
    }
    console.log(`  tỉ lệ bề ngang chữ / chỗ trống lớn nhất: ${(worstRatio * 100).toFixed(1)}%`);
  });
});
