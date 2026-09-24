import { describe, it, expect } from 'vitest';
import { parseDxf } from '../src/core/dxf-parse';
import { exportAllSheetsDxfR12, exportSheetDxfR12, sheetFileName } from '../src/core/dxf-export';
import { generateGcode, gcodeFileName } from '../src/core/gcode';
import { DEFAULT_GCODE_OPTIONS, applyPlacementRing, ringBBox, signedArea, type Part, type Ring, type SheetLayout } from '../src/types';
import { pointInPart, pointSegDistance, ringLength } from '../src/core/geometry';
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
