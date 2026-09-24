import { describe, it, expect } from 'vitest';
import { parseDxf } from '../src/core/dxf-parse';
import { labelPoint, pointInPart } from '../src/core/geometry';
import { applyPlacementRing } from '../src/types';
import { FIXTURE_MISSING_MSG, hasFixture, readFixture } from './helpers';

/**
 * Bảng mục 4 của PROBLEM_STATEMENT_nesting-ton-tau.md:
 * [bề rộng nhỏ nhất khi xoay (mm), dài (mm)] của P0..P14.
 */
const BANG_KICH_THUOC: [number, number][] = [
  [1172, 5253], [600, 1512], [600, 1323], [622, 3549], [600, 970],
  [600, 1143], [666, 3700], [600, 1709], [589, 3398], [739, 4319],
  [851, 4567], [1057, 5032], [954, 4804], [690, 3854], [724, 4015],
];

const d = hasFixture() ? describe : describe.skip;
if (!hasFixture()) console.warn(FIXTURE_MISSING_MSG);

d('US1 — nạp và làm sạch file DXF', () => {
  const text = readFixture();

  it('nhận đúng 15 chi tiết, tổng diện tích 13.97 m² (±0.5%)', () => {
    const r = parseDxf(text);
    expect(r.parts.length).toBe(15);
    const total = r.parts.reduce((s, p) => s + p.area, 0) / 1e6;
    expect(total).toBeGreaterThan(13.97 * 0.995);
    expect(total).toBeLessThan(13.97 * 1.005);
  });

  it('bỏ hết mũi tên chú thích (40 LINE hở) và chữ (TEXT/MTEXT/INSERT)', () => {
    const r = parseDxf(text);
    expect(r.stats.entityCounts.MTEXT).toBe(43);
    expect(r.stats.entityCounts.LINE).toBe(40);
    expect(r.stats.entityCounts.INSERT).toBe(2);
    expect(r.stats.openDropped).toBe(40);
    expect(r.stats.closedRings).toBe(15);
  });

  it('mọi chi tiết đều vừa tấm 2000x6000 và đã dịch về gốc riêng', () => {
    const r = parseDxf(text);
    for (const p of r.parts) {
      expect(p.fitsSheet).toBe(true);
      expect(p.bbox.minX).toBeCloseTo(0, 6);
      expect(p.bbox.minY).toBeCloseTo(0, 6);
      expect(p.qty).toBe(1);
    }
  });

  it('parse file 8.6MB trong ≤ 10 giây', () => {
    const t0 = Date.now();
    parseDxf(text);
    const ms = Date.now() - t0;
    console.log(`  parse ${(text.length / 1e6).toFixed(1)}MB mất ${ms}ms`);
    expect(ms).toBeLessThan(10_000);
  });

  it('đổi đơn vị sang mét thì chi tiết to gấp 1000 lần và bị đánh dấu không vừa tấm', () => {
    const r = parseDxf(text, { unitScale: 1000 });
    expect(r.parts.every((p) => !p.fitsSheet)).toBe(true);
    expect(r.warnings.join(' ')).toContain('đơn vị');
  });

  it('file rỗng thì báo lỗi tiếng Việt dễ hiểu', () => {
    const r = parseDxf('0\r\nSECTION\r\n2\r\nENTITIES\r\n0\r\nENDSEC\r\n0\r\nEOF\r\n');
    expect(r.parts.length).toBe(0);
    expect(r.warnings[0]).toContain('Không tìm thấy đường khép kín');
  });
});

d('Việc 1 — kích thước chi tiết = khung bao nhỏ nhất khi xoay', () => {
  const text = readFixture();

  it('15 chi tiết khớp bảng PROBLEM_STATEMENT (dài sai số ≤ 2%)', () => {
    const r = parseDxf(text);
    expect(r.parts.length).toBe(15);
    console.log('  chi tiết | bbox trục gốc (SAI) | dài×rộng mới | bảng đề bài | lệch');
    let worstL = 0;
    r.parts.forEach((p, i) => {
      const [tw, tl] = BANG_KICH_THUOC[i];
      const L = p.maxLength;
      const W = p.minWidth;
      const eL = ((L - tl) / tl) * 100;
      const eW = ((W - tw) / tw) * 100;
      worstL = Math.max(worstL, Math.abs(eL));
      const bw = Math.round(p.bbox.maxX - p.bbox.minX);
      const bh = Math.round(p.bbox.maxY - p.bbox.minY);
      console.log(
        `  ${p.id.padEnd(4)} | ${bw}×${bh} | ${Math.round(L)}×${Math.round(W)} | ${tl}×${tw} | ` +
        `dài ${eL.toFixed(2)}% · rộng ${eW.toFixed(2)}%`
      );
      expect(Math.abs(eL), `${p.id}: dài ${L.toFixed(0)} vs bảng ${tl}`).toBeLessThanOrEqual(2);
      // Bề rộng: bảng đề bài được đo bằng cách quét xoay từng 1°, còn ở đây dùng
      // rotating calipers nên ra giá trị nhỏ nhất ĐÚNG (luôn ≤ bảng, lệch lớn nhất
      // là P6: 652 so với 666 = -2.04%). Không bao giờ được lớn hơn bảng quá 2%.
      expect(W, `${p.id}: rộng ${W.toFixed(0)} vs bảng ${tw}`).toBeLessThanOrEqual(tw * 1.02);
      expect(W, `${p.id}: rộng ${W.toFixed(0)} vs bảng ${tw}`).toBeGreaterThanOrEqual(tw * 0.97);
    });
    console.log(`  lệch chiều dài lớn nhất: ${worstL.toFixed(2)}%`);
  });

  it('P0 dài 5253mm chứ không phải bbox 3409×3996', () => {
    const p = parseDxf(text).parts[0];
    expect(Math.round(p.maxLength)).toBeGreaterThan(5200);
    expect(Math.round(p.maxLength)).toBeLessThan(5310);
    // bbox theo trục toạ độ gốc vẫn là 3409×3996 — đó chính là con số cũ bị sai
    expect(Math.round(p.bbox.maxX - p.bbox.minX)).toBe(3409);
  });
});

d('Việc 2 — điểm đặt nhãn luôn nằm trong hình', () => {
  const text = readFixture();

  it('cả 15 chi tiết: điểm đặt nhãn nằm TRONG đa giác của chính nó', () => {
    const r = parseDxf(text);
    for (const p of r.parts) {
      const at = labelPoint(p.rings);
      expect(pointInPart(at, p.rings), `${p.id}: nhãn rơi ra ngoài hình`).toBe(true);
    }
  });

  it('trọng tâm thô rơi RA NGOÀI ít nhất 1 thanh cong — đúng lỗi đang gặp', () => {
    const r = parseDxf(text);
    let ngoai = 0;
    for (const p of r.parts) {
      const b = p.bbox;
      const c = { x: (b.minX + b.maxX) / 2, y: (b.minY + b.maxY) / 2 };
      if (!pointInPart(c, p.rings)) ngoai++;
    }
    console.log(`  số chi tiết có tâm bbox nằm ngoài hình: ${ngoai}/15`);
    expect(ngoai).toBeGreaterThan(0);
  });

  it('vẫn nằm trong hình sau khi xoay và dịch lên tấm', () => {
    const r = parseDxf(text);
    r.parts.forEach((p, i) => {
      const pl = { partId: p.id, instance: 0, rotationDeg: (i * 23) % 360, mirrored: i % 3 === 0, x: 137, y: 421 };
      const rings = p.rings.map((ring) => applyPlacementRing(ring, pl));
      const at = labelPoint(rings);
      expect(pointInPart(at, rings), `${p.id}: nhãn rơi ra ngoài sau khi xoay`).toBe(true);
    });
  });
});
