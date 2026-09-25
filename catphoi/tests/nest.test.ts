import { describe, it, expect } from 'vitest';
import { parseDxf } from '../src/core/dxf-parse';
import { nest, validateLayout } from '../src/nest/engine';
import { nestMulti, type NestPlan } from '../src/nest';
import { DEFAULT_NEST_PARAMS, applyPlacementRing, ringBBox, type NestParams, type Part } from '../src/types';
import { FIXTURE_MISSING_MSG, hasFixture, readFixture } from './helpers';

const d = hasFixture() ? describe : describe.skip;
if (!hasFixture()) console.warn(FIXTURE_MISSING_MSG);

/**
 * ĐÚNG BỘ THÔNG SỐ MÀN HÌNH ĐANG DÙNG — chép từ `currentParams()` +
 * `DEFAULT_SETTINGS` trong `src/ui/app.ts`: lật gương BẬT, khổ 2000 × 6000,
 * khe 10, lề 10, bước xoay 5°. Chỉ ngân sách là thay đổi theo từng phép đo.
 *
 * Vì sao phải có hằng này: màn hình gọi `nestMulti()`, KHÔNG gọi `nest()`, và
 * mặc định của màn hình khác `DEFAULT_NEST_PARAMS` (60 giây, KHÔNG lật gương).
 * Đo bằng `nest()` + `DEFAULT_NEST_PARAMS` rồi báo là "kết quả của màn hình"
 * đúng là lỗi đã từng xảy ra ở phiếu này.
 */
const SCREEN = {
  sheetW: 2000,
  sheetH: 6000,
  gap: 10,
  margin: 10,
  rotationStep: 5,
  allowMirror: true,
  gridCell: DEFAULT_NEST_PARAMS.gridCell,
  seed: DEFAULT_NEST_PARAMS.seed,
};
const screen = (timeLimitMs: number): NestParams => ({ ...SCREEN, timeLimitMs });

/** Tổng số chi tiết đã xếp của một phương án. */
const placedOf = (p: NestPlan): number => p.sheets.reduce((a, s) => a + s.placements.length, 0);

/** Bảng kiểm phải SẠCH ở MỌI phương án trả về, không riêng phương án tốt nhất. */
function expectMọiPhươngÁnSạch(out: { alternatives: NestPlan[] }, parts: Part[], params: NestParams): void {
  out.alternatives.forEach((p, i) => {
    const issues = validateLayout(p.sheets, parts, params);
    if (issues.length) console.log(`  LỖI ở phương án ${i + 1}:`, issues.slice(0, 5).map((x) => x.message));
    expect(issues, `phương án ${i + 1}`).toEqual([]);
    expect(placedOf(p), `phương án ${i + 1} phải đủ 15 chi tiết`).toBe(15);
  });
}

d('US2 — xếp tự động', () => {
  const { parts } = parseDxf(readFixture());

  /**
   * PHÉP ĐO CHÍNH — đi ĐÚNG đường màn hình chạy: `nestMulti()` với thông số
   * màn hình (lật gương bật). Ngân sách rút còn 60 giây thay vì 180 giây của
   * màn hình, để cả bộ test không dài thành 4 phút; con số ở 180 giây nằm ở
   * phép đo có cờ NEST180 bên dưới và trong báo cáo.
   *
   * SỐ THẬT ĐO ĐƯỢC (máy founder, ngân sách 60 giây, hạt giống mặc định 12345):
   * 2 tấm · 58,2% · ~56 giây · đủ 15/15 · bảng kiểm sạch ở cả 5 phương án.
   * Chốt ngưỡng ở "≤ 3 tấm" chứ không phải "= 2 tấm" vì kết quả 2 tấm CHƯA ỔN
   * ĐỊNH TUYỆT ĐỐI theo hạt giống: đo 10 hạt ở ngân sách 180 giây ra 7/10 lượt
   * 2 tấm (bản trước khi sửa: 3/10). Chốt "= 2 tấm" là biến test thành trò may
   * rủi, đúng thứ phiếu này cấm.
   */
  it('nestMulti (đường màn hình) — đủ 15/15, mọi phương án sạch, xong trong ngân sách', () => {
    const params = screen(60_000);
    const t0 = Date.now();
    const out = nestMulti({ parts, params });
    const ms = Date.now() - t0;

    console.log(`  nestMulti 60s: ${out.best.sheets.length} tấm · ${(out.best.utilization * 100).toFixed(1)}% · ${ms}ms`);
    out.alternatives.forEach((p, i) =>
      console.log(`   · phương án ${i + 1}: ${p.sheets.length} tấm · ${(p.utilization * 100).toFixed(1)}%`)
    );

    expect(out.alternatives[0]).toBe(out.best);
    expect(out.best.unplaced).toEqual([]);
    expect(placedOf(out.best)).toBe(15);
    expectMọiPhươngÁnSạch(out, parts, params);
    expect(out.best.sheets.length).toBeLessThanOrEqual(3);
    // Ngân sách phải được tôn trọng: vượt quá 10% là sai hẹn với người ở xưởng.
    expect(ms).toBeLessThanOrEqual(66_000);
  }, 120_000);

  /**
   * TÔN TRỌNG NGÂN SÁCH — đo riêng ở ngân sách ngắn để chạy nhanh.
   * Mốc đo thật: ngân sách 8 giây → nestMulti trả về sau ~8,0 giây.
   */
  it('nestMulti dừng đúng hẹn: ngân sách 8 giây thì không chạy quá 8,8 giây', () => {
    const params = screen(8_000);
    const t0 = Date.now();
    const out = nestMulti({ parts, params });
    const ms = Date.now() - t0;
    console.log(`  nestMulti 8s → ${out.best.sheets.length} tấm, ${ms}ms`);
    expect(ms).toBeLessThanOrEqual(8_800);
    expect(placedOf(out.best)).toBe(15);
    expectMọiPhươngÁnSạch(out, parts, params);
  }, 60_000);

  it('nestMulti ngân sách 5 giây vẫn ra kết quả hợp lệ, đủ 15 chi tiết', () => {
    const params = screen(5_000);
    const t0 = Date.now();
    const out = nestMulti({ parts, params });
    const ms = Date.now() - t0;
    console.log(`  nestMulti 5s → ${out.best.sheets.length} tấm, ${ms}ms`);
    expect(ms).toBeLessThan(15_000);
    expect(placedOf(out.best)).toBe(15);
    expectMọiPhươngÁnSạch(out, parts, params);
  }, 60_000);

  it('bấm Dừng thì nestMulti trả ngay phương án tốt nhất đang có', () => {
    let calls = 0;
    const out = nestMulti({
      parts,
      params: screen(60_000),
      shouldStop: () => ++calls > 3,
    });
    expect(out.best.sheets.length).toBeGreaterThan(0);
    expect(out.alternatives.length).toBeGreaterThan(0);
  }, 60_000);

  it('khe và lề đổi được, mọi phương án vẫn đúng ràng buộc', () => {
    const params: NestParams = { ...screen(8_000), gap: 25, margin: 40 };
    const out = nestMulti({ parts, params });
    console.log(`  khe 25 / lề 40 → ${out.best.sheets.length} tấm`);
    out.alternatives.forEach((p, i) => expect(validateLayout(p.sheets, parts, params), `phương án ${i + 1}`).toEqual([]));
  }, 60_000);

  it('chi tiết to hơn tấm thì bị bỏ ra và báo rõ, không crash', () => {
    const huge = { ...parts[0], id: 'PX', fitsSheet: false, enabled: true };
    const out = nestMulti({ parts: [...parts, huge], params: screen(5_000) });
    expect(out.best.unplaced.some((p) => p.id === 'PX')).toBe(true);
  }, 60_000);

  /**
   * PHÉP ĐO QUYẾT ĐỊNH "2 TẤM CÓ KHẢ THI KHÔNG".
   * Mọi phương án 2 tấm hợp lệ đều đổi được thành một phương án trên dải rộng
   * 2000 dài 12.000 (xếp tấm 2 lên trên tấm 1), nên nếu chiều dài tối thiểu cần
   * cho dải > 12.000mm thì 2 tấm là bất khả thi. Đây là cận TRÊN do thuật toán
   * tìm được, không phải cận dưới toán học, nên nó KHÔNG chứng minh bất khả thi
   * tuyệt đối — nhưng nó cho con số thật thay cho lời khai.
   *
   * Dùng `nest()` ở đây là CỐ Ý: phép đo này hỏi về sức đóng gói của engine
   * trên một dải dài, không phải hỏi màn hình ra mấy tấm.
   */
  it('đo chiều dài tối thiểu khi đóng gói 15 chi tiết lên dải 2000 × N', () => {
    const params = { ...DEFAULT_NEST_PARAMS, sheetH: 30_000, timeLimitMs: 20_000 };
    const r = nest({ parts, params });
    const byId = new Map(parts.map((p) => [p.id, p]));
    let maxY = 0;
    for (const s of r.sheets) {
      for (const pl of s.placements) {
        const b = ringBBox(applyPlacementRing(byId.get(pl.partId)!.rings[0], pl));
        if (b.maxY > maxY) maxY = b.maxY;
      }
    }
    const placed = r.sheets.reduce((a, s) => a + s.placements.length, 0);
    console.log(
      `  chiều dài tối thiểu đo được: ${maxY.toFixed(0)}mm · ngân sách 2 tấm: 12000mm · ` +
      `vượt ${(maxY - 12000).toFixed(0)}mm (${((maxY / 12000 - 1) * 100).toFixed(1)}%) · ` +
      `mật độ ${(13.968e6 / (2000 * maxY) * 100).toFixed(1)}%`
    );
    expect(placed).toBe(15);
    expect(validateLayout(r.sheets, parts, params)).toEqual([]);
    // Xếp trên dải liền phải KHÔNG tệ hơn xếp 3 tấm rời (3 × 6000 = 18.000mm).
    expect(maxY).toBeLessThan(18_000);
  }, 60_000);

  it('bảng kiểm tự bắt được lỗi khi cố tình đặt chồng lấn', () => {
    const p = parts[1];
    const sheets = [{
      index: 0, width: 2000, height: 6000,
      placements: [
        { partId: p.id, instance: 0, rotationDeg: 0, mirrored: false, x: 100, y: 100 },
        { partId: p.id, instance: 1, rotationDeg: 0, mirrored: false, x: 120, y: 110 },
      ],
      usedArea: p.area * 2, utilization: 0.1,
    }];
    const issues = validateLayout(sheets, [{ ...p, qty: 2 }], DEFAULT_NEST_PARAMS);
    expect(issues.some((i) => i.kind === 'overlap')).toBe(true);
  });

  /**
   * PHÉP ĐO ĐẦY ĐỦ Ở ĐÚNG NGÂN SÁCH MÀN HÌNH (180 giây). Tốn 3 phút một lượt
   * nên KHÔNG chạy trong bộ test thường; bật bằng `NEST180=1 pnpm test`.
   * Số thật đo được (10 hạt giống, máy founder, 5 tiến trình song song):
   * 7/10 lượt ra 2 tấm · 58,2%, 3/10 lượt ra 3 tấm · 38,8%. Lượt ra 2 tấm xong
   * ở 150-172 giây (chạm cận dưới số tấm thì dừng sớm), lượt ra 3 tấm chạy hết
   * 180,0 giây. Lượt lâu nhất 180.007ms — vượt ngân sách 0,004%.
   */
  const slow = process.env.NEST180 ? it : it.skip;
  slow('nestMulti ở đúng ngân sách màn hình 180 giây', () => {
    const params = screen(180_000);
    const t0 = Date.now();
    const out = nestMulti({ parts, params });
    const ms = Date.now() - t0;
    console.log(`  nestMulti 180s: ${out.best.sheets.length} tấm · ${(out.best.utilization * 100).toFixed(1)}% · ${ms}ms`);
    expect(placedOf(out.best)).toBe(15);
    expectMọiPhươngÁnSạch(out, parts, params);
    expect(out.best.sheets.length).toBeLessThanOrEqual(3);
    expect(ms).toBeLessThanOrEqual(198_000);
  }, 240_000);
});
