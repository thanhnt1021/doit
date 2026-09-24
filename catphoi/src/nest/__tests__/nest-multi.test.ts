import { describe, it, expect } from 'vitest';
import { parseDxf } from '../../core/dxf-parse';
import { nest, nestMulti, validateLayout, type NestPlan } from '../index';
import { DEFAULT_NEST_PARAMS } from '../../types';
import { hasFixture, readFixture } from './helpers';

const d = hasFixture() ? describe : describe.skip;
if (!hasFixture()) console.warn('THIẾU fixtures/gui-son.dxf — bỏ qua nhóm test nestMulti.');

/** In một phương án ra màn hình đúng cái chủ xưởng cần nhìn. */
function show(p: NestPlan, i: number): void {
  const từng = p.sheetUtil.map((u) => `${(u * 100).toFixed(1)}%`).join(' · ');
  console.log(
    `  phương án #${i + 1}: ${p.sheets.length} tấm · tổng ${(p.utilization * 100).toFixed(1)}% ` +
    `· từng tấm ${từng} · còn thừa ${p.unplaced.length} chi tiết`
  );
}

/**
 * Chữ ký để so hai phương án có khác nhau THẬT không.
 * Gồm hai phần, đúng hai tầng thước đo mà engine dùng:
 *  1. chi tiết nào nằm tấm nào (đã sắp xếp nên không phụ thuộc thứ tự đặt);
 *  2. % sử dụng từng tấm làm tròn 0,1% — bắt được trường hợp cùng cách chia
 *     tấm nhưng sắp khác hẳn trên tấm.
 */
function chữKý(p: NestPlan): string {
  const chia = p.sheets
    .map((s) => s.placements.map((pl) => `${pl.partId}#${pl.instance}`).sort().join(','))
    .join(' | ');
  return `${chia} @ ${p.sheetUtil.map((u) => (u * 100).toFixed(1)).join('/')}`;
}

d('US — engine trả NHIỀU phương án cho chủ xưởng tự chọn', () => {
  const { parts } = parseDxf(readFixture());
  const params = { ...DEFAULT_NEST_PARAMS, timeLimitMs: 12_000 };

  it('trả ≥2 phương án KHÁC NHAU RÕ RỆT, sắp tốt dần, [0] chính là best', () => {
    const t0 = Date.now();
    const out = nestMulti({ parts, params });
    console.log(`  chạy ${Date.now() - t0}ms · ${out.alternatives.length} phương án`);
    out.alternatives.forEach(show);

    // hợp đồng
    expect(out.alternatives[0]).toBe(out.best);
    expect(out.alternatives.length).toBeGreaterThanOrEqual(2);
    expect(out.alternatives.length).toBeLessThanOrEqual(5);

    // mỗi phương án phải tự đứng vững: đủ số liệu + hợp lệ về an toàn
    for (const p of out.alternatives) {
      expect(p.sheetUtil.length).toBe(p.sheets.length);
      p.sheets.forEach((s, i) => expect(p.sheetUtil[i]).toBeCloseTo(s.utilization, 9));
      expect(p.utilization).toBeGreaterThan(0);
      expect(validateLayout(p.sheets, parts, params)).toEqual([]);
    }

    // KHÁC NHAU RÕ RỆT: không hai phương án nào chia chi tiết lên tấm y hệt nhau
    const kýs = out.alternatives.map(chữKý);
    expect(new Set(kýs).size).toBe(kýs.length);

    // sắp TỐT DẦN XUỐNG: số tấm không được giảm khi đi xuống danh sách
    for (let i = 1; i < out.alternatives.length; i++) {
      expect(out.alternatives[i].sheets.length).toBeGreaterThanOrEqual(
        out.alternatives[i - 1].sheets.length
      );
    }
  }, 180_000);

  it('best của nestMulti trùng khớp kết quả nest() cũ (cùng seed, cùng ngân sách)', () => {
    const r = nest({ parts, params });
    const out = nestMulti({ parts, params });
    console.log(`  nest(): ${r.sheets.length} tấm ${(r.utilization * 100).toFixed(1)}% · ` +
      `nestMulti().best: ${out.best.sheets.length} tấm ${(out.best.utilization * 100).toFixed(1)}%`);
    expect(out.best.sheets.length).toBe(r.sheets.length);
    expect(out.best.utilization).toBeCloseTo(r.utilization, 9);
    expect(out.best.unplaced.length).toBe(r.unplaced.length);
  }, 180_000);

  it('thanh tiến độ vẫn chạy, và bấm Dừng thì trả ngay phương án đang có', () => {
    const mốc: number[] = [];
    let cóBest = false;
    const t0 = Date.now();
    const out = nestMulti({
      parts,
      params: { ...DEFAULT_NEST_PARAMS, timeLimitMs: 60_000 },
      onProgress: (p, best) => {
        mốc.push(p);
        if (best.sheets.length > 0) cóBest = true;
      },
      shouldStop: () => Date.now() - t0 > 3000,
    });
    const ms = Date.now() - t0;
    console.log(`  dừng sau ${ms}ms · ${mốc.length} lần báo tiến độ · ${out.alternatives.length} phương án`);
    expect(ms).toBeLessThan(20_000);
    expect(mốc.length).toBeGreaterThan(0);
    expect(mốc[mốc.length - 1]).toBeGreaterThanOrEqual(mốc[0]);
    expect(cóBest).toBe(true);
    expect(out.best.sheets.length).toBeGreaterThan(0);
    expect(out.alternatives[0]).toBe(out.best);
  }, 120_000);
});
