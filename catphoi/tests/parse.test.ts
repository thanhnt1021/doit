import { describe, it, expect } from 'vitest';
import { parseDxf } from '../src/core/dxf-parse';
import { FIXTURE_MISSING_MSG, hasFixture, readFixture } from './helpers';

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
