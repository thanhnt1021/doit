import { describe, it, expect } from 'vitest';
import { parseDxf } from '../src/core/dxf-parse';
import { exportAllSheetsDxfR12, exportSheetDxfR12, sheetFileName } from '../src/core/dxf-export';
import { generateGcode, gcodeFileName } from '../src/core/gcode';
import { DEFAULT_GCODE_OPTIONS, applyPlacementRing, ringBBox, type Part, type SheetLayout } from '../src/types';
import { FIXTURE_MISSING_MSG, hasFixture, readFixture } from './helpers';

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
