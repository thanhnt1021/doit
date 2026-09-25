/**
 * BẰNG CHỨNG: engine đặt được chi tiết vào HỐC — chỗ trống bị kẹp giữa/dưới
 * những chi tiết đã xếp — chứ không chỉ đặt lên mặt trên như bản cũ.
 *
 * Ca thử dựng riêng để CHỈ CÓ MỘT ĐÁP ÁN ĐÚNG:
 *   · chi tiết "KHUNG" hình chữ Π (hai chân + một xà ngang) — dưới xà là một
 *     cái hốc rộng 220 × cao 280;
 *   · chi tiết "NHÉT" là hình chữ nhật 160 × 240, chỉ vừa đúng cái hốc đó;
 *   · tấm được cắt vừa khít: bên cạnh KHUNG chỉ còn 140mm (cần 170mm mới nhét
 *     lọt kể cả khe), phía trên KHUNG chỉ còn 20mm.
 * ⇒ Xếp được cả hai lên MỘT tấm thì bắt buộc chi tiết NHÉT phải nằm trong hốc.
 * Bản engine cũ (thả rơi theo một đường bao) cho ra HAI tấm ở ca này.
 */
import { describe, it, expect } from 'vitest';
import { Nester, nest, validateLayout, rasterizeRing } from '../index';
import { DEFAULT_NEST_PARAMS, applyPlacementRing, ringBBox, type Part, type Ring } from '../../types';
import { rectRing } from './helpers';

const SHEET_W = 560;
const SHEET_H = 420;

/** Vòng ngoài hình chữ Π: rộng 400, cao 380, hốc dưới xà rộng 220 cao 280. */
const KHUNG_RING: Ring = [
  { x: 0, y: 0 }, { x: 90, y: 0 }, { x: 90, y: 280 }, { x: 310, y: 280 },
  { x: 310, y: 0 }, { x: 400, y: 0 }, { x: 400, y: 380 }, { x: 0, y: 380 },
];

function partOf(id: string, ring: Ring, area: number, w: number, h: number): Part {
  return {
    id,
    rings: [ring],
    area,
    bbox: { minX: 0, minY: 0, maxX: w, maxY: h },
    vertexCount: ring.length,
    minWidth: Math.min(w, h),
    maxLength: Math.max(w, h),
    qty: 1,
    enabled: true,
    fitsSheet: true,
  };
}

const KHUNG = partOf('KHUNG', KHUNG_RING, 400 * 380 - 220 * 280, 400, 380);
const NHET = partOf('NHET', rectRing(0, 0, 160, 240), 160 * 240, 160, 240);

const PARAMS = {
  ...DEFAULT_NEST_PARAMS,
  sheetW: SHEET_W,
  sheetH: SHEET_H,
  // KHOÁ GÓC 0°: nếu cho xoay 180° thì chữ Π lật thành chữ U, cái hốc ngửa lên
  // trời và phép thả rơi tầm thường cũng nhét được — ca thử mất hết ý nghĩa.
  // Khoá ở 0° thì xà ngang luôn nằm TRÊN, chỗ trống nằm dưới một phần nhô ra,
  // đúng thứ mà engine cũ không bao giờ với tới.
  rotationStep: 360,
  allowMirror: false,
  timeLimitMs: 8000,
};

describe('US — đặt chi tiết vào HỐC (lồng ngược, đường bao nhiều tầng)', () => {
  it('đường bao nhiều tầng nhìn thấy cả khoảng trống DƯỚI xà ngang', () => {
    const nester = new Nester(PARAMS, SHEET_W, SHEET_H);
    const sh = nester.newSheet();
    const khung = rasterizeRing(KHUNG_RING, nester.cell, nester.dil);
    nester.stamp(sh, khung, 0, 0);

    // Que dò 20×20 đặt vào giữa hốc (x ≈ 210mm trên tấm).
    const que = rasterizeRing(rectRing(0, 0, 20, 20), nester.cell, nester.dil);
    const px = Math.round((210 - nester.rx0) / nester.cell);
    const n = nester.freeSpans(sh, que, px, sh.maxRow);

    const spans = Array.from({ length: n }, (_, i) => [nester.spanLoAt(i), nester.spanHiAt(i)]);
    console.log(`  cột x≈210mm có ${n} tầng trống: ` +
      spans.map(([a, b]) => `${(a * nester.cell + nester.ry0).toFixed(0)}..${(b * nester.cell + nester.ry0).toFixed(0)}mm`).join(' · '));

    // Ít nhất 2 tầng: một tầng DƯỚI xà ngang, một tầng TRÊN nóc chi tiết.
    expect(n).toBeGreaterThanOrEqual(2);
    // Tầng dưới cùng phải bắt đầu từ đáy tấm và cao ≥ 240mm (đủ nhét chữ nhật).
    expect(spans[0][0]).toBe(0);
    expect((spans[0][1] - spans[0][0] + 1) * nester.cell).toBeGreaterThanOrEqual(240);
  });

  it('xếp cả KHUNG và NHÉT lên MỘT tấm — chỉ có thể nếu NHÉT chui vào hốc', () => {
    const parts = [KHUNG, NHET];
    const r = nest({ parts, params: PARAMS });

    const placed = r.sheets.reduce((a, s) => a + s.placements.length, 0);
    console.log(`  ${r.sheets.length} tấm · ${placed}/2 chi tiết · ${r.iterations} phương án`);
    expect(r.unplaced).toEqual([]);
    expect(placed).toBe(2);
    expect(r.sheets.length).toBe(1);
    expect(validateLayout(r.sheets, parts, PARAMS)).toEqual([]);

    // Bằng chứng HÌNH HỌC: khung bao của NHÉT nằm TRỌN trong khung bao của KHUNG.
    const byId = new Map(parts.map((p) => [p.id, p]));
    const box = new Map(
      r.sheets[0].placements.map((pl) => [
        pl.partId, ringBBox(applyPlacementRing(byId.get(pl.partId)!.rings[0], pl)),
      ])
    );
    const a = box.get('KHUNG')!;
    const b = box.get('NHET')!;
    console.log(
      `  KHUNG ${a.minX.toFixed(0)}..${a.maxX.toFixed(0)} × ${a.minY.toFixed(0)}..${a.maxY.toFixed(0)} · ` +
      `NHÉT ${b.minX.toFixed(0)}..${b.maxX.toFixed(0)} × ${b.minY.toFixed(0)}..${b.maxY.toFixed(0)}`
    );
    expect(b.minX).toBeGreaterThanOrEqual(a.minX);
    expect(b.maxX).toBeLessThanOrEqual(a.maxX);
    expect(b.minY).toBeGreaterThanOrEqual(a.minY);
    // NẰM DƯỚI XÀ NGANG: mép trên của NHÉT thấp hơn đáy xà (a.minY + 280).
    // Tức là nó thật sự chui vào chỗ trống bị CHE PHÍA TRÊN, không phải đậu lên nóc.
    expect(b.maxY).toBeLessThanOrEqual(a.minY + 280);
  }, 60_000);
});
