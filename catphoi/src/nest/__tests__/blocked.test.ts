import { describe, it, expect } from 'vitest';
import { nestMulti, validateLayout, type NestSheetSpec } from '../index';
import { DEFAULT_NEST_PARAMS, type Ring } from '../../types';
import { largestFreeRect, rectPart, rectRing, ringArea } from './helpers';

/**
 * TẤM THỪA THẬT: vẫn nguyên khổ 2000 × 6000, nhưng lần cắt trước đã lấy đi ba
 * mảng, để lại ba LỖ HỔNG. Engine phải xếp luồn quanh ba lỗ này.
 */
const SHEET_W = 2000;
const SHEET_H = 6000;
const BLOCKED: Ring[] = [
  rectRing(0, 0, 1200, 900),        // góc dưới-trái đã bị lấy
  rectRing(1400, 2500, 600, 900),   // một mảng ở mép phải, khoảng giữa tấm
  rectRing(0, 4800, 700, 1200),     // góc trên-trái đã bị lấy
];

const PARAMS = { ...DEFAULT_NEST_PARAMS, timeLimitMs: 8000 };

describe('US — xếp lên tấm có VÙNG CẤM (tôn thừa giữ nguyên khổ)', () => {
  it('không chi tiết nào đè lên vùng cấm, và cách vùng cấm ≥ khe', () => {
    const parts = [rectPart('R', 400, 400, 40)];
    const sheets: NestSheetSpec[] = [{ w: SHEET_W, h: SHEET_H, blocked: BLOCKED, label: 'Tấm thừa A' }];
    const out = nestMulti({ parts, params: { ...PARAMS, sheets } });

    const s0 = out.best.sheets[0];
    expect(s0.specIndex).toBe(0);
    expect(s0.label).toBe('Tấm thừa A');
    expect(s0.blocked).toBe(BLOCKED);

    const issues = validateLayout(out.best.sheets, parts, PARAMS);
    const bad = issues.filter((i) => i.kind !== 'missing'); // thiếu chi tiết là chuyện bình thường ở đây
    if (bad.length) console.log('  LỖI:', bad.slice(0, 5).map((i) => i.message));
    expect(bad).toEqual([]);
    expect(issues.some((i) => i.kind === 'blocked')).toBe(false);

    console.log(`  tấm thừa nhận ${s0.placements.length} chi tiết 400×400, sử dụng ${(s0.utilization * 100).toFixed(1)}%`);
    expect(s0.placements.length).toBeGreaterThan(0);
  }, 120_000);

  it('mọi phương án trả ra đều sạch vùng cấm, không riêng phương án tốt nhất', () => {
    const parts = [rectPart('R', 400, 400, 40)];
    const sheets: NestSheetSpec[] = [{ w: SHEET_W, h: SHEET_H, blocked: BLOCKED }];
    const out = nestMulti({ parts, params: { ...PARAMS, sheets } });
    for (const plan of out.alternatives) {
      const issues = validateLayout(plan.sheets, parts, PARAMS).filter((i) => i.kind !== 'missing');
      expect(issues).toEqual([]);
    }
  }, 120_000);

  it('so với CÁCH CŨ (hình chữ nhật lớn nhất nội tiếp): xếp được nhiều hơn hẳn', () => {
    const parts = [rectPart('R', 400, 400, 40)];

    // CÁCH MỚI — khai nguyên khổ + vùng cấm
    const mới = nestMulti({
      parts,
      params: { ...PARAMS, sheets: [{ w: SHEET_W, h: SHEET_H, blocked: BLOCKED }] },
    });
    const nMới = mới.best.sheets[0].placements.length;

    // CÁCH CŨ — co tấm thừa về hình chữ nhật lớn nhất nội tiếp rồi xếp vào đó
    const rect = largestFreeRect(SHEET_W, SHEET_H, BLOCKED);
    const cũ = nestMulti({ parts, params: { ...PARAMS, sheetW: rect.w, sheetH: rect.h } });
    const nCũ = cũ.best.sheets[0].placements.length;

    const freeArea = SHEET_W * SHEET_H - BLOCKED.reduce((s, r) => s + ringArea(r), 0);
    const rectArea = rect.w * rect.h;
    console.log(
      `  phần thừa thật: ${(freeArea / 1e6).toFixed(2)} m² · hình chữ nhật nội tiếp lớn nhất: ` +
      `${rect.w}×${rect.h} = ${(rectArea / 1e6).toFixed(2)} m² → cách cũ vứt mất ` +
      `${((1 - rectArea / freeArea) * 100).toFixed(0)}% diện tích`
    );
    console.log(`  CÁCH CŨ (hình chữ nhật nội tiếp): xếp được ${nCũ} chi tiết 400×400`);
    console.log(`  CÁCH MỚI (nguyên khổ + vùng cấm): xếp được ${nMới} chi tiết 400×400`);
    console.log(`  → hơn ${nMới - nCũ} chi tiết (+${(((nMới / nCũ) - 1) * 100).toFixed(0)}%)`);

    expect(rectArea).toBeLessThan(freeArea);
    expect(nMới).toBeGreaterThan(nCũ);
  }, 180_000);
});
