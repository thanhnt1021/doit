/**
 * Lõi xếp phôi (nesting). Thuần TypeScript — chạy được cả trong Node (test)
 * lẫn trong Web Worker của trình duyệt. Không đụng DOM.
 *
 * CÁCH ĐẶT CHI TIẾT — "THẢ RƠI THEO ĐƯỜNG BAO" (contour drop)
 * ──────────────────────────────────────────────────────────
 * Bản trước quét vét cạn mọi (px, py) rồi gọi hàm dò va chạm ⇒ tới ~10^8 phép
 * tính cho MỘT lần đặt, cả engine chỉ chạy nổi ~4 phương án/giây nên GA không
 * kịp tìm kiếm gì. Bản này bỏ hẳn kiểu quét đó.
 *
 * Với mỗi tấm ta giữ hai đường bao:
 *   · colTop[c] — hàng cao nhất đang bị chiếm của CỘT c (−1 nếu cột trống)
 *   · rowMax[r] — cột cao nhất đang bị chiếm của HÀNG r (−1 nếu hàng trống)
 * Với mỗi chi tiết (bitmap đã nở theo khe) ta giữ:
 *   · colLow[c] — hàng thấp nhất được bật của cột c (đáy chi tiết)
 *   · rowLowBit[r] — cột thấp nhất được bật của hàng r (mép trái chi tiết)
 *
 * Thả rơi theo −y tại cột px:  py = max_c ( colTop[px+c] + 1 − colLow[c] )
 * Trượt sang −x tại hàng py:   px = max_r ( rowMax[py+r] + 1 − rowLowBit[r] )
 *
 * BẢO ĐẢM: tại vị trí đó chi tiết CHẮC CHẮN không chồng lấn. Chứng minh cho
 * phép thả rơi: mọi ô được bật của chi tiết ở cột c đều có hàng r ≥ colLow[c],
 * nên hàng tuyệt đối py+r ≥ py+colLow[c] ≥ colTop[px+c]+1 > colTop[px+c], tức
 * nằm cao hơn toàn bộ phần đã bị chiếm của cột đó. Tương tự cho phép trượt.
 * ⇒ KHÔNG CẦN gọi dò va chạm, chi phí mỗi ứng viên chỉ O(bề rộng) hoặc
 *   O(chiều cao) phép đọc mảng. Nhanh hơn bản cũ hàng trăm lần.
 *
 * ĐƯỜNG BAO NHIỀU TẦNG — LỒNG NGƯỢC (multi-level contour)
 * ────────────────────────────────────────────────────────
 * Hai công thức trên chỉ với tới MẶT TRÊN của thứ đã xếp: chi tiết không bao
 * giờ chui xuống dưới phần nhô ra của chi tiết khác. Với bộ sườn tàu, đó chính
 * là chỗ phí tôn lớn nhất — cả dải dưới bụng các thanh vòm bỏ trống, trong khi
 * một thanh úp ngược lại nằm khít trong lòng máng đó.
 *
 * Nên mỗi tấm giữ THÊM, cho từng cột, DANH SÁCH DẢI hàng đang bị chiếm
 * (runLo/runHi/runN) thay vì chỉ một con số colTop. Mỗi chi tiết cũng giữ danh
 * sách dải theo cột của nó (colRunPtr/colRuns trong raster.ts).
 *
 * Đặt chi tiết tại cột px, dải [a,b] của cột c đụng dải [s,e] của cột tấm px+c
 * khi và chỉ khi  py ∈ [s − b, e − a].  Gom mọi khoảng cấm đó bằng mảng sai
 * phân rồi quét một lượt ⇒ ra ĐẦY ĐỦ mọi khoảng py đặt được của cột px, kể cả
 * khoảng bị KẸP GIỮA hai chi tiết (xem Nester.freeSpans). Mỗi khoảng cho hai
 * ứng viên: tựa xuống ĐÁY khoảng, và ép NGỬA lên NÓC khoảng — chính là kiểu
 * "hai hình vòm úp vào nhau".
 *
 * BẢO ĐẢM AN TOÀN vẫn nguyên: danh sách dải của tấm là TẬP CHA của tập ô bị
 * chiếm (gộp dải khi tràn sức chứa chỉ làm nó rộng thêm), nên vị trí nằm ngoài
 * mọi khoảng cấm thì chắc chắn không chồng lấn. Bitmap đã nở nửa khe mỗi phía
 * ⇒ không chồng lấn tức khoảng cách thật ≥ khe.
 *
 * Việc đặt vào hốc chỉ bật ở PHA SIẾT CHẶT (exact), vì nó đắt hơn thả rơi.
 */
import type {
  NestInput, NestParams, NestProgress, NestResult, Part, Placement, Ring, SheetLayout,
} from '../types';
import { DEFAULT_NEST_PARAMS, applyPlacementRing, ringBBox } from '../types';
import { pointInRing, segSegDistance, segSegIntersect } from '../core/geometry';
import { rasterizeRing, transformRing, type BaseBitmap } from './raster';
// Chỉ import KIỂU nên không sinh vòng import lúc chạy (index.ts import engine.ts).
import type { NestSheetSpec } from './index';

/**
 * Tấm trong kết quả engine. Bằng SheetLayout cũ cộng thêm hai thông tin của
 * việc "xếp lên tôn thừa": tấm này là tấm khai thứ mấy, và nó có vùng cấm nào.
 */
export interface EngineSheet extends SheetLayout {
  /** Chỉ số trong danh sách tấm được khai. −1 = tấm mới nguyên khổ do engine tự mở. */
  specIndex: number;
  /** Vùng cấm (đa giác, toạ độ theo tấm) — chỗ đã bị cắt mất ở lần trước. */
  blocked?: Ring[];
}

export interface NestCallbacks {
  onProgress?: (p: NestProgress) => void;
  shouldStop?: () => boolean;
  now?: () => number;
}

/** Bộ sinh ngẫu nhiên có seed để test tái lập được. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

interface AngleOpt {
  deg: number;
  mirrored: boolean;
  /** Diện tích bbox sau khi xoay (mm²) — dùng để xếp hạng. */
  bboxArea: number;
  /** Bề cao bbox sau khi xoay (mm) — xếp hạng theo trục dài của tấm. */
  bboxH: number;
  /** Bề rộng bbox sau khi xoay (mm). */
  bboxW: number;
}

interface PartPrep {
  part: Part;
  /** Vòng ngoài của hình gốc (dùng để raster). */
  simple: Ring;
  /** Các góc hợp lệ, đã xếp hạng theo bbox nhỏ dần. */
  angles: AngleOpt[];
  /** Chỉ số vào `angles`, sắp theo bề cao bbox tăng dần. */
  byH: number[];
  /** Chỉ số vào `angles`, sắp theo bề rộng bbox tăng dần. */
  byW: number[];
  /** Tra nhanh: bậc góc (deg/step) → chỉ số trong `angles`, −1 nếu góc bị loại. */
  byDeg: Int32Array;
  /** Như `byDeg` nhưng cho bản ĐÃ LẬT GƯƠNG (rỗng hết nếu không cho lật). */
  byDegM: Int32Array;
}

interface Inst {
  prepIndex: number;
  instance: number;
  area: number;
}

interface SheetGrid {
  bits: Uint32Array;
  words: number;
  /** Nester (kích thước lưới) của chính tấm này — mỗi khổ tấm một Nester riêng. */
  nester: Nester;
  /** Khổ tấm, mm. */
  w: number;
  h: number;
  /** Tấm khai thứ mấy (−1 = tấm mới nguyên khổ). */
  specIndex: number;
  /** Hàng ô cao nhất bị VÙNG CẤM chiếm + 1 (0 nếu không có vùng cấm). */
  blockTop: number;
  /** Vùng cấm của tấm này, giữ lại để trả ra ngoài + để bảng kiểm dùng. */
  blocked?: Ring[];
  /** Bit cao nhất đang bị chiếm của từng hàng (−1 nếu hàng trống). */
  rowMax: Int32Array;
  /** Hàng cao nhất đang bị chiếm của từng cột (−1 nếu cột trống). */
  colTop: Int32Array;
  /**
   * ĐƯỜNG BAO NHIỀU TẦNG. Với mỗi cột, danh sách các DẢI hàng đang bị chiếm,
   * sắp tăng dần và đã gộp các dải dính nhau. Cột c dùng ô nhớ
   * [c*RUN_STRIDE, c*RUN_STRIDE + runN[c]).
   *
   * `colTop` chỉ cho biết NÓC của cột nên engine cũ chỉ biết đặt chi tiết LÊN
   * TRÊN thứ đã có. Danh sách dải cho biết cả những khoảng trống nằm LỌT GIỮA —
   * đó chính là lòng máng dưới bụng thanh sườn cong, chỗ nhét được thanh úp ngược.
   */
  runN: Int32Array;
  runLo: Int32Array;
  runHi: Int32Array;
  /** Hàng ô cao nhất đã dùng (exclusive). */
  maxRow: number;
  /** Hàng thấp nhất / cao nhất đang bị chiếm (dải hàng có vật), −1/−1 nếu trống. */
  rowLo: number;
  rowHi: number;
  placements: Placement[];
  usedArea: number;
}

const BIG = 1e12;
/** Số ứng viên vị trí được giữ lại để tinh chỉnh bằng phép trượt–rơi. */
const TOP_K = 5;
/**
 * Sức chứa danh sách dải của MỘT cột tấm. 15 chi tiết, mỗi chi tiết cắt qua một
 * cột nhiều nhất vài nhánh ⇒ 32 là rộng rãi. Nếu vẫn tràn thì engine gộp hai dải
 * gần nhau nhất lại: kết quả thành TẬP CHA của chỗ thật sự bị chiếm, tức chỉ
 * BỚT chỗ đặt chứ không bao giờ sinh chồng lấn.
 */
const RUN_CAP = 32;
/** Bước nhớ mỗi cột — chừa 2 ô đệm để chèn xong rồi mới gộp cho gọn. */
const RUN_STRIDE = RUN_CAP + 2;
/** Tối đa bao nhiêu "tầng" (khoảng py đặt được) lấy ra cho một cột. */
const MAX_SPANS = 24;
/** Bao nhiêu phương án liên tiếp không tiến bộ thì gieo lại quần thể. */
const STALL_LIMIT = 200;
export interface Spot {
  px: number;
  py: number;
  key: number;
}

/** Lưới vùng cấm dựng sẵn cho một khổ tấm — copy ra mỗi khi mở tấm mới. */
export interface BlockTemplate {
  bits: Uint32Array;
  rowMax: Int32Array;
  colTop: Int32Array;
  runN: Int32Array;
  runLo: Int32Array;
  runHi: Int32Array;
  rowLo: number;
  rowHi: number;
  /** Hàng cao nhất bị chiếm + 1. */
  blockTop: number;
  /** Số ô bị vùng cấm chiếm. */
  cells: number;
}

export class Nester {
  readonly params: NestParams;
  readonly cell: number;
  readonly dil: number;
  readonly rx0: number;
  readonly ry0: number;
  readonly gw: number;
  readonly gh: number;
  readonly sheetWords: number;
  private cache = new Map<string, BaseBitmap | null>();
  private cacheBytes = 0;
  /** Bộ nhớ tạm dùng lại cho dropY/dropX — tránh cấp phát trong vòng lặp nóng. */
  private scratch = new Int32Array(2);
  /**
   * HAI rổ ứng viên riêng, mỗi rổ TOP_K chỗ:
   *  · rổ 0 — chỗ tìm bằng thả rơi / trượt ngang (đặt LÊN TRÊN thứ đã có)
   *  · rổ 1 — chỗ nằm trong HỐC (lọt giữa hoặc dưới bụng chi tiết khác)
   * Để chung một rổ thì chỗ trong hốc (thường "hụt 0") chiếm sạch hạn ngạch và
   * đè mất những chỗ tốt của thả rơi, nên phải tách.
   */
  private candPx = new Int32Array(TOP_K * 2);
  private candPy = new Int32Array(TOP_K * 2);
  private candKey = new Float64Array(TOP_K * 2);
  /** Ứng viên thứ i có phải chỗ trong hốc không (không được "trượt–rơi" lại). */
  private candPocket = new Uint8Array(TOP_K * 2);
  /** Đáy của hốc chứa ứng viên thứ i — để chấm lại điểm sau khi ép sát. */
  private candFloor = new Int32Array(TOP_K * 2);
  /** Mảng sai phân dựng danh sách tầng trống — cấp một lần, dùng lại mãi. */
  private diff: Int32Array;
  private spanLo = new Int32Array(MAX_SPANS);
  private spanHi = new Int32Array(MAX_SPANS);
  /** Đọc kết quả của lần `freeSpans` gần nhất — tầng thứ i chiếm hàng [lo, hi]. */
  spanLoAt(i: number): number { return this.spanLo[i]; }
  spanHiAt(i: number): number { return this.spanHi[i]; }
  /** Bước quét cột ở pha tìm hốc (ô). */
  readonly pxStride: number;

  /** Khổ tấm mà Nester này phục vụ (mm). Mặc định lấy từ params. */
  readonly sheetW: number;
  readonly sheetH: number;

  constructor(params: NestParams, sheetW?: number, sheetH?: number) {
    this.params = params;
    this.sheetW = sheetW ?? params.sheetW;
    this.sheetH = sheetH ?? params.sheetH;
    this.cell = params.gridCell ?? 5;
    this.dil = Math.max(0, Math.ceil(params.gap / 2 / this.cell));
    this.rx0 = params.margin - this.dil * this.cell;
    this.ry0 = params.margin - this.dil * this.cell;
    const rw = this.sheetW - 2 * params.margin + 2 * this.dil * this.cell;
    const rh = this.sheetH - 2 * params.margin + 2 * this.dil * this.cell;
    this.gw = Math.max(1, Math.floor(rw / this.cell));
    this.gh = Math.max(1, Math.floor(rh / this.cell));
    this.sheetWords = ((this.gw + 31) >> 5) + 2;
    // Quét cột 10mm một bước ở pha tìm hốc; phần lẻ được bù lại bằng bước ép
    // sát sang trái (refineLeft) nên không mất chỗ tốt.
    this.pxStride = Math.max(1, Math.round(10 / this.cell));
    this.diff = new Int32Array(this.gh + 2);
  }

  /**
   * Dựng SẴN lưới của các VÙNG CẤM cho một khổ tấm thừa.
   *
   * Vì sao dựng sẵn rồi copy: mỗi lần đánh giá một phương án là một lần tạo
   * tấm mới, engine chạy hàng trăm phương án — raster hoá lại vùng cấm mỗi lần
   * thì tốn hàng giây. Dựng một lần rồi `.slice()` mảng (memcpy) là rẻ nhất.
   *
   * Vùng cấm được NỞ đúng `dil` ô giống hệt chi tiết, nên hai bitmap đã nở mà
   * không chồng nhau thì khoảng cách THẬT từ chi tiết tới vùng cấm ≥ khe —
   * cùng một bảo đảm toán học với ràng buộc khe giữa hai chi tiết.
   */
  buildBlockTemplate(blocked: Ring[] | undefined): BlockTemplate | null {
    if (!blocked || blocked.length === 0) return null;
    const bits = new Uint32Array(this.sheetWords * this.gh);
    const rowMax = new Int32Array(this.gh).fill(-1);
    const colTop = new Int32Array(this.gw).fill(-1);
    let rowLo = -1;
    let rowHi = -1;
    let cells = 0;
    for (const ring of blocked) {
      if (!ring || ring.length < 3) continue;
      const bm = rasterizeRing(ring, this.cell, this.dil);
      const px0 = Math.round((bm.originX - this.rx0) / this.cell);
      const py0 = Math.round((bm.originY - this.ry0) / this.cell);
      for (let r = 0; r < bm.h; r++) {
        const row = py0 + r;
        if (row < 0 || row >= this.gh) continue;
        const lo = bm.rowLowBit[r];
        if (lo < 0) continue;
        const hi = bm.rowHighBit[r];
        const src = r * bm.words;
        const dst = row * this.sheetWords;
        for (let b = lo; b <= hi; b++) {
          if ((bm.bits[src + (b >> 5)] & (1 << (b & 31))) === 0) continue;
          const col = px0 + b;
          if (col < 0 || col >= this.gw) continue;
          const wi = dst + (col >> 5);
          const mask = 1 << (col & 31);
          if ((bits[wi] & mask) !== 0) continue;
          bits[wi] |= mask;
          cells++;
          if (col > rowMax[row]) rowMax[row] = col;
          if (row > colTop[col]) colTop[col] = row;
          if (rowLo < 0) rowLo = row;
          if (row > rowHi) rowHi = row;
        }
      }
    }
    if (cells === 0) return null;
    // Danh sách dải của vùng cấm, dựng thẳng từ bitmap đã raster.
    const runN = new Int32Array(this.gw);
    const runLo = new Int32Array(this.gw * RUN_STRIDE);
    const runHi = new Int32Array(this.gw * RUN_STRIDE);
    for (let col = 0; col < this.gw; col++) {
      const top = colTop[col];
      if (top < 0) continue;
      const wi = col >> 5;
      const mask = 1 << (col & 31);
      const base = col * RUN_STRIDE;
      let n = 0;
      let start = -1;
      for (let row = 0; row <= top; row++) {
        const on = (bits[row * this.sheetWords + wi] & mask) !== 0;
        if (on) {
          if (start < 0) start = row;
        } else if (start >= 0) {
          if (n < RUN_CAP) {
            runLo[base + n] = start;
            runHi[base + n] = row - 1;
            n++;
          } else runHi[base + n - 1] = row - 1; // tràn: gộp vào dải cuối (tập cha)
          start = -1;
        }
      }
      if (start >= 0) {
        if (n < RUN_CAP) {
          runLo[base + n] = start;
          runHi[base + n] = top;
          n++;
        } else runHi[base + n - 1] = top;
      }
      runN[col] = n;
    }
    return { bits, rowMax, colTop, runN, runLo, runHi, rowLo, rowHi, blockTop: rowHi + 1, cells };
  }

  newSheet(opts?: { tpl?: BlockTemplate | null; specIndex?: number; blocked?: Ring[] }): SheetGrid {
    const tpl = opts?.tpl ?? null;
    return {
      bits: tpl ? tpl.bits.slice() : new Uint32Array(this.sheetWords * this.gh),
      words: this.sheetWords,
      nester: this,
      w: this.sheetW,
      h: this.sheetH,
      specIndex: opts?.specIndex ?? -1,
      blockTop: tpl ? tpl.blockTop : 0,
      blocked: opts?.blocked,
      rowMax: tpl ? tpl.rowMax.slice() : new Int32Array(this.gh).fill(-1),
      colTop: tpl ? tpl.colTop.slice() : new Int32Array(this.gw).fill(-1),
      runN: tpl ? tpl.runN.slice() : new Int32Array(this.gw),
      runLo: tpl ? tpl.runLo.slice() : new Int32Array(this.gw * RUN_STRIDE),
      runHi: tpl ? tpl.runHi.slice() : new Int32Array(this.gw * RUN_STRIDE),
      maxRow: 0,
      rowLo: tpl ? tpl.rowLo : -1,
      rowHi: tpl ? tpl.rowHi : -1,
      placements: [],
      usedArea: 0,
    };
  }

  getBitmap(prep: PartPrep, a: AngleOpt): BaseBitmap | null {
    const key = `${prep.part.id}|${a.deg}|${a.mirrored ? 1 : 0}`;
    const hit = this.cache.get(key);
    if (hit !== undefined) return hit;
    const ring = transformRing(prep.simple, a.deg, a.mirrored);
    const bm = rasterizeRing(ring, this.cell, this.dil);
    const ok = bm.w <= this.gw && bm.h <= this.gh;
    const val = ok ? bm : null;
    // Raster hoá lại một thanh sườn tốn ~2ms, mà GA gọi liên tục nên PHẢI cache.
    // Chặn phình bộ nhớ theo DUNG LƯỢNG (không theo số lượng): tối đa ~64MB.
    // Map giữ thứ tự chèn nên xoá từ đầu là bỏ cái cũ nhất.
    this.cacheBytes +=
      bm.bits.byteLength + bm.colLow.byteLength * 2 + bm.rowLowBit.byteLength * 4 +
      bm.colRuns.byteLength + bm.colRunPtr.byteLength;
    while (this.cacheBytes > 64 * 1024 * 1024 && this.cache.size > 8) {
      const it = this.cache.keys().next();
      if (it.done) break;
      const old = this.cache.get(it.value);
      if (old) {
        this.cacheBytes -=
          old.bits.byteLength + old.colLow.byteLength * 2 + old.rowLowBit.byteLength * 4 +
          old.colRuns.byteLength + old.colRunPtr.byteLength;
      }
      this.cache.delete(it.value);
    }
    this.cache.set(key, val);
    return val;
  }

  /**
   * Dò va chạm khi đặt bitmap `bm` tại ô (px, py) của lưới tấm.
   * Chỉ còn dùng cho phần KIỂM TRA (đường đặt chính không cần gọi hàm này).
   */
  collides(sh: SheetGrid, bm: BaseBitmap, px: number, py: number): boolean {
    const s = px & 31;
    const wo = px >>> 5;
    const sw = sh.words;
    const sheet = sh.bits;
    const pbits = bm.bits;
    const pw = bm.words;
    const rowMax = sh.rowMax;
    const inv = 32 - s;
    for (let r = 0; r < bm.h; r++) {
      const f = bm.rowFirst[r];
      if (f < 0) continue;
      const rm = rowMax[py + r];
      if (rm < px + bm.rowLowBit[r]) continue; // hàng này của tấm chưa chạm tới chi tiết
      const l = bm.rowLast[r];
      const src = r * pw;
      const dst = (py + r) * sw + wo;
      if (s === 0) {
        for (let i = f; i <= l; i++) {
          if ((pbits[src + i] & sheet[dst + i]) !== 0) return true;
        }
      } else {
        let prev = 0;
        for (let i = f; i <= l + 1; i++) {
          const cur = i <= l ? pbits[src + i] : 0;
          const v = ((cur << s) | (prev >>> inv)) >>> 0;
          prev = cur;
          if ((v & sheet[dst + i]) !== 0) return true;
        }
      }
    }
    return false;
  }

  stamp(sh: SheetGrid, bm: BaseBitmap, px: number, py: number): void {
    const s = px & 31;
    const wo = px >>> 5;
    const sw = sh.words;
    const sheet = sh.bits;
    const pbits = bm.bits;
    const pw = bm.words;
    const inv = 32 - s;
    for (let r = 0; r < bm.h; r++) {
      const f = bm.rowFirst[r];
      if (f < 0) continue;
      const l = bm.rowLast[r];
      const src = r * pw;
      const dst = (py + r) * sw + wo;
      if (s === 0) {
        for (let i = f; i <= l; i++) sheet[dst + i] |= pbits[src + i];
      } else {
        let prev = 0;
        for (let i = f; i <= l + 1; i++) {
          const cur = i <= l ? pbits[src + i] : 0;
          sheet[dst + i] |= ((cur << s) | (prev >>> inv)) >>> 0;
          prev = cur;
        }
      }
      const hi = px + bm.rowHighBit[r];
      const row = py + r;
      if (hi > sh.rowMax[row]) sh.rowMax[row] = hi;
      if (sh.rowLo < 0 || row < sh.rowLo) sh.rowLo = row;
      if (row > sh.rowHi) sh.rowHi = row;
    }
    const ptr = bm.colRunPtr;
    const runs = bm.colRuns;
    for (let c = 0; c < bm.w; c++) {
      const ch = bm.colHigh[c];
      if (ch < 0) continue;
      const t = py + ch;
      if (t > sh.colTop[px + c]) sh.colTop[px + c] = t;
      const k0 = ptr[c];
      const k1 = ptr[c + 1];
      for (let k = k0; k < k1; k++) {
        this.insertRun(sh, px + c, py + runs[2 * k], py + runs[2 * k + 1]);
      }
    }
    if (py + bm.h > sh.maxRow) sh.maxRow = py + bm.h;
  }

  /**
   * Ghi thêm một dải bị chiếm [lo, hi] vào cột `col`, giữ danh sách SẮP TĂNG và
   * đã GỘP: hai dải chạm hoặc kề nhau (hi + 1 ≥ lo) được nhập làm một.
   * Nhờ luôn gộp nên danh sách mô tả ĐÚNG tập ô bị chiếm của cột.
   */
  private insertRun(sh: SheetGrid, col: number, lo: number, hi: number): void {
    const base = col * RUN_STRIDE;
    const RL = sh.runLo;
    const RH = sh.runHi;
    const n = sh.runN[col];
    let i = 0;
    while (i < n && RH[base + i] + 1 < lo) i++;
    let j = i;
    let nlo = lo;
    let nhi = hi;
    while (j < n && RL[base + j] <= nhi + 1) {
      if (RL[base + j] < nlo) nlo = RL[base + j];
      if (RH[base + j] > nhi) nhi = RH[base + j];
      j++;
    }
    const removed = j - i;
    if (removed > 1) {
      for (let k = 0; k + j < n; k++) {
        RL[base + i + 1 + k] = RL[base + j + k];
        RH[base + i + 1 + k] = RH[base + j + k];
      }
    } else if (removed === 0) {
      for (let k = n - 1; k >= i; k--) {
        RL[base + k + 1] = RL[base + k];
        RH[base + k + 1] = RH[base + k];
      }
    }
    RL[base + i] = nlo;
    RH[base + i] = nhi;
    let cnt = n - removed + 1;
    // TRÀN SỨC CHỨA: gộp hai dải sát nhau nhất. Kết quả là TẬP CHA của chỗ thật
    // sự bị chiếm ⇒ chỉ mất chỗ đặt chứ tuyệt đối không sinh chồng lấn.
    while (cnt > RUN_CAP) {
      let bestK = 0;
      let bestGap = Infinity;
      for (let k = 0; k + 1 < cnt; k++) {
        const g = RL[base + k + 1] - RH[base + k];
        if (g < bestGap) {
          bestGap = g;
          bestK = k;
        }
      }
      RH[base + bestK] = RH[base + bestK + 1];
      for (let k = bestK + 1; k + 1 < cnt; k++) {
        RL[base + k] = RL[base + k + 1];
        RH[base + k] = RH[base + k + 1];
      }
      cnt--;
    }
    sh.runN[col] = cnt;
  }

  /**
   * LIỆT KÊ MỌI TẦNG ĐẶT ĐƯỢC tại cột px — trái tim của việc lồng ngược.
   *
   * Với mỗi cột c của chi tiết và mỗi DẢI [a,b] của nó, đặt tại py sẽ đụng dải
   * [s,e] của cột tấm khi và chỉ khi py + a ≤ e và py + b ≥ s, tức
   *      py ∈ [s − b, e − a].
   * Gom mọi khoảng cấm đó bằng mảng sai phân rồi quét một lượt ⇒ ra ĐẦY ĐỦ các
   * khoảng py đặt được, kể cả khoảng nằm lọt giữa hai chi tiết. Kết quả ghi vào
   * `spanLo`/`spanHi`, trả về số khoảng.
   *
   * BẢO ĐẢM: khoảng trả về là chính xác theo danh sách dải, mà danh sách dải là
   * tập cha của chỗ bị chiếm ⇒ đặt ở đó CHẮC CHẮN không chồng lấn.
   */
  freeSpans(sh: SheetGrid, bm: BaseBitmap, px: number, hiLimit: number): number {
    if (hiLimit < 0) return 0;
    const diff = this.diff;
    const ptr = bm.colRunPtr;
    const runs = bm.colRuns;
    const RL = sh.runLo;
    const RH = sh.runHi;
    let tLo = hiLimit + 1;
    let tHi = -1;
    for (let c = 0; c < bm.w; c++) {
      const col = px + c;
      const n = sh.runN[col];
      if (n === 0) continue;
      const k0 = ptr[c];
      const k1 = ptr[c + 1];
      if (k0 === k1) continue;
      const base = col * RUN_STRIDE;
      for (let k = k0; k < k1; k++) {
        const a = runs[2 * k];
        const b = runs[2 * k + 1];
        for (let m = 0; m < n; m++) {
          let lo = RL[base + m] - b;
          let hi = RH[base + m] - a;
          if (hi < 0 || lo > hiLimit) continue;
          if (lo < 0) lo = 0;
          if (hi > hiLimit) hi = hiLimit;
          diff[lo]++;
          diff[hi + 1]--;
          if (lo < tLo) tLo = lo;
          if (hi + 1 > tHi) tHi = hi + 1;
        }
      }
    }
    const spanLo = this.spanLo;
    const spanHi = this.spanHi;
    if (tHi < 0) {
      spanLo[0] = 0;
      spanHi[0] = hiLimit;
      return 1;
    }
    let cnt = 0;
    let acc = 0;
    let start = 0; // đoạn [0, tLo) chắc chắn rảnh
    const yEnd = Math.min(tHi, hiLimit);
    for (let y = tLo; y <= yEnd; y++) {
      acc += diff[y];
      if (acc === 0) {
        if (start < 0) start = y;
      } else if (start >= 0) {
        if (y - 1 >= start && cnt < MAX_SPANS) {
          spanLo[cnt] = start;
          spanHi[cnt] = y - 1;
          cnt++;
        }
        start = -1;
      }
    }
    diff.fill(0, tLo, tHi + 1);
    if (start < 0) start = yEnd + 1;
    if (start <= hiLimit && cnt < MAX_SPANS) {
      spanLo[cnt] = start;
      spanHi[cnt] = hiLimit;
      cnt++;
    }
    return cnt;
  }

  /**
   * Thả chi tiết từ trên xuống tại cột px.
   * out[0] = py chạm đất · out[1] = DIỆN TÍCH HỤT bên dưới (số ô), tính luôn
   * trong cùng vòng lặp: hụt = Σ_c (py − t_c) với t_c = colTop[px+c]+1−colLow[c].
   * Diện tích hụt là thước đo độ khít tốt hơn nhiều so với "đếm cột chạm sát":
   * nó phạt đúng phần tôn bị bỏ phí nằm dưới chi tiết.
   */
  dropY(sh: SheetGrid, bm: BaseBitmap, px: number, out: Int32Array): void {
    const colTop = sh.colTop;
    const colLow = bm.colLow;
    const n = bm.w;
    let py = 0;
    let cnt = 0;
    let sum = 0;
    for (let c = 0; c < n; c++) {
      const lo = colLow[c];
      if (lo < 0) continue;
      const t = colTop[px + c] + 1 - lo;
      if (t > py) py = t;
      sum += t;
      cnt++;
    }
    out[0] = py;
    let v = py * cnt - sum;
    if (v > 1e7) v = 1e7;
    out[1] = v;
  }

  /** Chỉ lấy py chạm đất (dùng trong vòng lặp trượt–rơi). */
  dropYOnly(sh: SheetGrid, bm: BaseBitmap, px: number): number {
    const colTop = sh.colTop;
    const colLow = bm.colLow;
    const n = bm.w;
    let py = 0;
    for (let c = 0; c < n; c++) {
      const lo = colLow[c];
      if (lo < 0) continue;
      const t = colTop[px + c] + 1 - lo;
      if (t > py) py = t;
    }
    return py;
  }

  /**
   * Vị trí dừng khi đẩy chi tiết từ phải sang trái tại hàng py.
   * Chỉ quét những hàng của tấm ĐANG CÓ VẬT: hàng trống có rowMax = −1 nên
   * t = −lb ≤ 0, không bao giờ nâng được px (px khởi tạo 0) ⇒ bỏ qua an toàn.
   */
  dropX(sh: SheetGrid, bm: BaseBitmap, py: number): number {
    if (sh.rowLo < 0) return 0;
    const rowMax = sh.rowMax;
    const rowLow = bm.rowLowBit;
    let r0 = sh.rowLo - py;
    let r1 = sh.rowHi - py;
    if (r0 < 0) r0 = 0;
    if (r1 > bm.h - 1) r1 = bm.h - 1;
    let px = 0;
    for (let r = r0; r <= r1; r++) {
      const lb = rowLow[r];
      if (lb < 0) continue;
      const t = rowMax[py + r] + 1 - lb;
      if (t > px) px = t;
    }
    return px;
  }





  /** Diện tích hụt (số ô) nếu đặt chi tiết đúng tại (px, py). */
  voidAt(sh: SheetGrid, bm: BaseBitmap, px: number, py: number): number {
    const colTop = sh.colTop;
    const colLow = bm.colLow;
    const n = bm.w;
    let v = 0;
    for (let c = 0; c < n; c++) {
      const lo = colLow[c];
      if (lo < 0) continue;
      const d = py + lo - colTop[px + c] - 1;
      // Chặn dưới ở 0 theo TỪNG CỘT. Với vị trí thả rơi thì d luôn ≥ 0 nên không
      // đổi gì; nhưng với vị trí nằm LỌT DƯỚI vật khác thì d rất âm, không chặn
      // sẽ cho điểm "âm vô lý" và ứng viên xấu chiếm hết hạn ngạch.
      if (d > 0) v += d;
    }
    return v > 9999999 ? 9999999 : v;
  }


  /**
   * Chấm điểm và bỏ vào rổ "hốc" một vị trí do `freeSpans` sinh ra.
   * `floor` là đáy của hốc: đặt cao hơn đáy bao nhiêu thì phí đúng bấy nhiêu ô
   * tôn nằm lọt dưới bụng, nên cộng thẳng vào diện tích hụt để hai kiểu đặt
   * (tựa đáy / ép ngửa lên trần) so được với nhau.
   */
  private pushPocket(
    sh: SheetGrid, bm: BaseBitmap, rule: number,
    push: (base: number, px: number, py: number, key: number, pocket: number, floor: number) => void,
    px: number, py: number, floor: number, maxPy: number, worst: number
  ): void {
    if (py < 0 || py > maxPy) return;
    const newTop = py + bm.h > sh.maxRow ? py + bm.h : sh.maxRow;
    // LỌC RẺ TRƯỚC: khoá ứng với "hụt = 0" là cận DƯỚI của khoá thật. Thua rồi
    // thì khỏi tính diện tích hụt (tốn O(bề rộng)) — đây là phần đắt nhất của
    // vòng quét hốc, mỗi cột có tới vài chục tầng.
    const lowBound = this.keyOf(rule, px, py, newTop, (py - floor) * bm.w);
    if (lowBound >= worst) return;
    let v = this.voidAt(sh, bm, px, py) + (py - floor) * bm.w;
    if (v > 9999999) v = 9999999;
    push(TOP_K, px, py, this.keyOf(rule, px, py, newTop, v), 1, floor);
  }

  /**
   * ÉP SÁT chỗ trong hốc: đẩy sang trái rồi hạ xuống từng ô chừng nào còn không
   * chồng lấn. Bù lại phần độ phân giải mất đi do quét cột theo bước `pxStride`.
   * Chỉ chạy cho vài ứng viên lọt vào chung kết nên phép dò va chạm ở đây rẻ.
   */
  private refinePocket(sh: SheetGrid, bm: BaseBitmap, px: number, py: number, out: Int32Array): void {
    const lim = this.pxStride;
    for (let k = 0; k < lim && px > 0; k++) {
      if (this.collides(sh, bm, px - 1, py)) break;
      px--;
    }
    for (let k = 0; k < lim && py > 0; k++) {
      if (this.collides(sh, bm, px, py - 1)) break;
      py--;
    }
    out[0] = px;
    out[1] = py;
  }

  /**
   * TRƯỢT–RƠI LẶP: từ một vị trí hợp lệ, luân phiên "đẩy sang trái tới khi
   * chạm" rồi "thả xuống tới khi chạm", tối đa 5 vòng. Đây là thứ cho phép
   * thanh sườn CHUI vào chỗ lõm của thanh bên cạnh chứ không chỉ đậu lên trên:
   * rơi xuống một gờ → trượt trái vào lòng máng → rơi tiếp.
   * Mọi vị trí trung gian đều được bảo đảm không chồng lấn bởi chính hai công
   * thức thả rơi, nên không cần dò va chạm.
   */
  settle(sh: SheetGrid, bm: BaseBitmap, px0: number, py0: number, maxPx: number, out: Int32Array): void {
    let px = px0;
    let py = py0;
    for (let it = 0; it < 5; it++) {
      let moved = false;
      const nx = this.dropX(sh, bm, py);
      if (nx < px && nx >= 0 && nx <= maxPx) {
        px = nx;
        moved = true;
      }
      const ny = this.dropYOnly(sh, bm, px);
      if (ny < py) {
        py = ny;
        moved = true;
      }
      if (!moved) break;
    }
    out[0] = px;
    out[1] = py;
  }


  /**
   * Khoá sắp xếp vị trí. `rule` chọn triết lý xếp:
   *  0 — tấm ngắn nhất, rồi khít nhất (mặc định, đúng mục tiêu ít tấm nhất)
   *  1 — bottom-left cổ điển: py nhỏ nhất, rồi khít nhất
   *  2 — left-bottom: px nhỏ nhất, rồi py nhỏ nhất — đây là triết lý của bản
   *      engine cũ, chính nó cho bộ sườn cong lồng vào nhau khít nhất khi kết
   *      hợp với quét vét cạn, nên phải giữ nguyên chứ không thay bằng độ khít
   *  3 — khít nhất trước, rồi tấm ngắn nhất
   */
  private keyOf(rule: number, px: number, py: number, newTop: number, voidCells: number): number {
    const v = voidCells < 9999999 ? voidCells : 9999999;
    switch (rule) {
      case 1: return py * 1e7 + v;
      case 2: return px * 1e10 + py * 1e7 + v;
      case 3: return v * 1e7 + newTop * 1e3 + px;
      default: return newTop * 1e7 + v;
    }
  }

  /**
   * Tìm chỗ đặt tốt nhất cho 1 bitmap trên 1 tấm.
   *
   * BỐN bộ sinh ứng viên, mỗi bộ cho một hướng "ép sát":
   *   A · thả rơi xuống   (đậu lên mặt trên của thứ đã có)
   *   B · trượt sang trái (tựa vào mép phải của thứ đã có)
   *   C · nâng lên ép sát mặt dưới + đặt sát đáy tấm  → chui vào bụng thanh cong
   *   D · đẩy ép sát mép trái + đặt sát mép trái tấm   → chui vào lòng thanh cong
   * A/B và C/D có hạn ngạch ứng viên RIÊNG, nếu không C/D (thường "hụt 0") sẽ
   * chiếm hết chỗ và đè mất các vị trí tốt của A/B.
   * Ứng viên giữ lại được cho "trượt–rơi" tinh chỉnh rồi mới chấm điểm lần cuối.
   */
  findSpot(sh: SheetGrid, bm: BaseBitmap, rule: number, exact: boolean, abort?: () => boolean): Spot | null {
    const maxPx = this.gw - bm.w;
    const maxPy = this.gh - bm.h;
    if (maxPx < 0 || maxPy < 0) return null;

    const K = TOP_K;
    const kx = this.candPx;
    const ky = this.candPy;
    const kk = this.candKey;
    const kp = this.candPocket;
    const kf = this.candFloor;
    for (let i = 0; i < K * 2; i++) {
      kx[i] = -1;
      kk[i] = Infinity;
      kp[i] = 0;
      kf[i] = 0;
    }
    const push = (base: number, px: number, py: number, key: number, pocket: number, floor: number): void => {
      if (key >= kk[base + K - 1]) return;
      let i = base + K - 1;
      while (i > base && kk[i - 1] > key) {
        kk[i] = kk[i - 1];
        kx[i] = kx[i - 1];
        ky[i] = ky[i - 1];
        kp[i] = kp[i - 1];
        kf[i] = kf[i - 1];
        i--;
      }
      kk[i] = key;
      kx[i] = px;
      ky[i] = py;
      kp[i] = pocket;
      kf[i] = floor;
    };

    const out = this.scratch;
    const empty = sh.rowLo < 0;

    // A) thả rơi từ trên xuống, thử mọi cột
    for (let px = 0; px <= maxPx; px++) {
      this.dropY(sh, bm, px, out);
      const py = out[0];
      if (py > maxPy) continue;
      const newTop = py + bm.h > sh.maxRow ? py + bm.h : sh.maxRow;
      push(0, px, py, this.keyOf(rule, px, py, newTop, out[1]), 0, 0);
    }

    // B) trượt từ phải sang trái. Chỉ quét tới mép trên đang dùng của tấm:
    // cao hơn mức đó chi tiết luôn dừng ở px = 0, trùng ứng viên bộ sinh A đã cho.
    // Với tấm rất dài thì lấy mẫu thưa rồi để phép trượt–rơi tinh chỉnh lại.
    if (!empty) {
      // Trên tấm thừa, phần bị chiếm cao nhất có thể là VÙNG CẤM chứ không phải
      // chi tiết đã xếp, nên mốc quét phải lấy cả blockTop.
      const limitPy = Math.min(maxPy, Math.max(sh.maxRow, sh.blockTop));
      const stepY = limitPy > 256 ? Math.ceil(limitPy / 256) : 1;
      for (let py = 0; py <= limitPy; py += stepY) {
        const px = this.dropX(sh, bm, py);
        if (px > maxPx) continue;
        const newTop = py + bm.h > sh.maxRow ? py + bm.h : sh.maxRow;
        // cận dưới của khoá (ứng với diện tích hụt = 0): thua rồi thì khỏi tính hụt
        if (this.keyOf(rule, px, py, newTop, 0) >= kk[K - 1]) continue;
        push(0, px, py, this.keyOf(rule, px, py, newTop, this.voidAt(sh, bm, px, py)), 0, 0);
      }
    }

    // F) ĐẶT VÀO HỐC — chỉ bật ở pha tinh chỉnh.
    //
    // Đây là chỗ dạy engine LỒNG NGƯỢC. Với mỗi cột px, `freeSpans` trả về MỌI
    // khoảng py đặt được, kể cả khoảng nằm lọt dưới bụng hoặc giữa hai thanh cong
    // đã xếp. Hai vị trí đáng thử trong mỗi khoảng:
    //   · ĐÁY khoảng — thanh rơi xuống tựa lên nóc thứ bên dưới;
    //   · NÓC khoảng — thanh được ép NGỬA lên ôm sát bụng thanh phía trên.
    // Vị trí thứ hai chính là kiểu "hai hình vòm úp vào nhau" mà đường bao một
    // tầng (colTop) không bao giờ nghĩ ra được.
    //
    // Chi phí: mỗi cột tốn cỡ (số dải chi tiết × số dải tấm) + độ dài dải quét,
    // tức vài nghìn phép tính — rẻ hơn hẳn phép dò va chạm của bản cũ, mà lại
    // LIỆT KÊ ĐỦ chứ không phải mò theo hạn ngạch.
    if (exact) {
      const hiLimit = Math.min(maxPy, Math.max(sh.maxRow, sh.blockTop));
      const step = this.pxStride;
      for (let px = 0; px <= maxPx; px += step) {
        if ((px & 31) === 0 && abort?.()) break;
        const nsp = this.freeSpans(sh, bm, px, hiLimit);
        for (let i = 0; i < nsp; i++) {
          const lo = this.spanLo[i];
          const hi = this.spanHi[i];
          const worst = kk[K * 2 - 1];
          // đáy hốc
          this.pushPocket(sh, bm, rule, push, px, lo, lo, maxPy, worst);
          // nóc hốc — chỉ đáng thử khi hốc CÓ TRẦN (không phải khoảng trên cùng)
          if (hi > lo && hi < hiLimit) this.pushPocket(sh, bm, rule, push, px, hi, lo, maxPy, worst);
        }
      }
    }

    // E) QUÉT VÉT CẠN theo cột — ĐÃ BỎ HẲN, bộ sinh F ở trên thay thế.
    // Bản cũ mò từng (cột, hàng) rồi gọi dò va chạm, phải chặn bằng trần số lần
    // dò nên vừa chậm vừa bỏ sót. Bộ sinh F liệt kê ĐỦ mọi tầng đặt được bằng
    // phép tính khoảng trên danh sách dải, không cần dò va chạm lần nào.

    let bestKey = Infinity;
    let bestPx = -1;
    let bestPy = 0;
    for (let i = 0; i < K * 2; i++) {
      if (kx[i] < 0) continue;
      if (kk[i] < bestKey) {
        bestKey = kk[i];
        bestPx = kx[i];
        bestPy = ky[i];
      }
      // Chỗ trong HỐC thì KHÔNG được "trượt–rơi": hai phép đó đi theo đường bao
      // một tầng nên sẽ lôi chi tiết ra khỏi hốc. Thay vào đó ép sát tại chỗ.
      if (kp[i]) this.refinePocket(sh, bm, kx[i], ky[i], out);
      else this.settle(sh, bm, kx[i], ky[i], maxPx, out);
      const px = out[0];
      const py = out[1];
      if (py > maxPy || px > maxPx || px < 0 || py < 0) continue;
      let v = this.voidAt(sh, bm, px, py);
      if (kp[i]) {
        // Phí thật của chỗ trong hốc = phần tôn bỏ trống nằm DƯỚI chi tiết,
        // tính từ đáy hốc lên. Không cộng khoản này thì kiểu "ép ngửa lên trần"
        // lúc nào cũng được chấm 0 và thắng oan kiểu "tựa xuống đáy".
        const extra = (py - kf[i]) * bm.w;
        v = v + (extra > 0 ? extra : 0);
        if (v > 9999999) v = 9999999;
      }
      const newTop = py + bm.h > sh.maxRow ? py + bm.h : sh.maxRow;
      const key = this.keyOf(rule, px, py, newTop, v);
      if (key < bestKey) {
        bestKey = key;
        bestPx = px;
        bestPy = py;
      }
    }

    if (bestPx < 0) return null;
    return { px: bestPx, py: bestPy, key: bestKey };
  }

  place(
    sh: SheetGrid, prep: PartPrep, inst: Inst, angleCands: AngleOpt[],
    rule: number, exact: boolean, abort?: () => boolean
  ): boolean {
    let bestSpot: Spot | null = null;
    let bestBm: BaseBitmap | null = null;
    let bestA: AngleOpt | null = null;
    let bestKey = Infinity;
    for (const a of angleCands) {
      // Canh hạn GIỮA CÁC GÓC: ở pha vét cạn một lần tìm chỗ có thể tốn hàng
      // trăm mili-giây, canh hạn ở mức thô hơn là vượt giờ cho phép.
      if (bestSpot && abort?.()) break;
      const bm = this.getBitmap(prep, a);
      if (!bm) continue;
      const spot = this.findSpot(sh, bm, rule, exact, abort);
      if (!spot) continue;
      if (spot.key < bestKey) {
        bestKey = spot.key;
        bestSpot = spot;
        bestBm = bm;
        bestA = a;
      }
    }
    if (!bestSpot || !bestBm || !bestA) return false;
    this.stamp(sh, bestBm, bestSpot.px, bestSpot.py);
    sh.placements.push({
      partId: prep.part.id,
      instance: inst.instance,
      rotationDeg: bestA.deg,
      mirrored: bestA.mirrored,
      x: this.rx0 + bestSpot.px * this.cell - bestBm.originX,
      y: this.ry0 + bestSpot.py * this.cell - bestBm.originY,
    });
    sh.usedArea += prep.part.area;
    return true;
  }
}

/**
 * Dấu vân tay hình dạng: raster thô 20mm rồi băm. Hai biến thể (góc × lật) cho
 * CÙNG một vân tay thì đặt lên tấm giống hệt nhau — giữ cả hai chỉ làm loãng
 * việc tìm kiếm chứ không thêm được lựa chọn nào.
 */
const SIG_CELL = 20;
function shapeSig(ring: Ring): number {
  const bm = rasterizeRing(ring, SIG_CELL, 0);
  let h = 0x811c9dc5;
  h = Math.imul(h ^ bm.w, 0x01000193);
  h = Math.imul(h ^ bm.h, 0x01000193);
  for (let i = 0; i < bm.bits.length; i++) h = Math.imul(h ^ bm.bits[i], 0x01000193);
  return h >>> 0;
}

interface AngleSet {
  angles: AngleOpt[];
  /** bậc góc → chỉ số trong `angles` của bản KHÔNG lật (hoặc bản trùng hình). */
  byDeg: Int32Array;
  /** bậc góc → chỉ số của bản ĐÃ LẬT (hoặc bản trùng hình). */
  byDegM: Int32Array;
}

/**
 * Dựng danh sách góc hợp lệ cho 1 chi tiết, ĐÃ BỎ TRÙNG.
 *
 * Vì sao phải bỏ trùng: thanh sườn tàu gần như đối xứng gương, nên bản lật ở
 * góc θ đặt lên tấm y hệt bản không lật ở một góc nào đó. Bật "lật gương" mà
 * không bỏ trùng thì số góc tăng gấp đôi (72 → 144) trong khi số lựa chọn THẬT
 * gần như không tăng — đo thật: bật lật gương làm chiều dài dải TỆ ĐI vì việc
 * tìm kiếm bị loãng. Bỏ trùng xong thì bật lật gương chỉ có lợi, không có hại.
 *
 * Bảng tra `byDeg`/`byDegM` vẫn trả về ĐẦY ĐỦ mọi bậc góc: biến thể bị bỏ được
 * trỏ sang bản trùng hình còn giữ lại, nên phép "xoay đúng bằng thanh trước"
 * và "úp ngược 180°" không mất ứng viên nào.
 */
function buildAngles(simple: Ring, nester: Nester, params: NestParams, nSteps: number, step: number): AngleSet {
  const out: AngleOpt[] = [];
  const byDeg = new Int32Array(nSteps).fill(-1);
  const byDegM = new Int32Array(nSteps).fill(-1);
  const seen = new Map<number, number>();
  const mirrors = params.allowMirror ? [false, true] : [false];
  for (const mirrored of mirrors) {
    const table = mirrored ? byDegM : byDeg;
    for (let k = 0; k < nSteps; k++) {
      const deg = k * step;
      if (deg >= 360) break;
      const ring = transformRing(simple, deg, mirrored);
      const b = ringBBox(ring);
      const bw = b.maxX - b.minX;
      const bh = b.maxY - b.minY;
      const w = bw + 2 * nester.dil * nester.cell;
      const h = bh + 2 * nester.dil * nester.cell;
      if (w > nester.gw * nester.cell || h > nester.gh * nester.cell) continue;
      const sig = shapeSig(ring);
      const hit = seen.get(sig);
      if (hit !== undefined) {
        table[k] = hit; // trùng hình — trỏ sang bản đã giữ, KHÔNG thêm góc mới
        continue;
      }
      seen.set(sig, out.length);
      table[k] = out.length;
      out.push({ deg, mirrored, bboxArea: bw * bh, bboxH: bh, bboxW: bw });
    }
  }
  // Sắp theo bbox nhỏ dần — phải vá lại bảng tra vì chỉ số thay đổi.
  const order = out.map((_, i) => i).sort((a, b) => out[a].bboxArea - out[b].bboxArea);
  const remap = new Int32Array(out.length);
  order.forEach((oldIdx, newIdx) => { remap[oldIdx] = newIdx; });
  const sorted = order.map((i) => out[i]);
  for (let k = 0; k < nSteps; k++) {
    if (byDeg[k] >= 0) byDeg[k] = remap[byDeg[k]];
    if (byDegM[k] >= 0) byDegM[k] = remap[byDegM[k]];
  }
  return { angles: sorted, byDeg, byDegM };
}

interface Genome {
  order: number[];
  angleIdx: number[];
  rule: number;
}

interface Evaluated {
  genome: Genome;
  cost: number;
  sheets: EngineSheet[];
  unplaced: string[];
  placedArea: number;
  /** Số tấm thật sự dùng. */
  nSheets: number;
  /** Chỉ số instance nằm trên tấm CUỐI (để phép đột biến "dọn tấm cuối"). */
  lastSheetInsts: number[];
  /** Lưới thật của các tấm đang dùng — để bước hậu xử lý dời chi tiết. */
  grids: SheetGrid[];
  /** Instance nào nằm ở tấm nào (−1 = chưa xếp được). */
  sheetOf: Int32Array;
}

/**
 * Một phương án đã được chấm điểm, ở dạng NHẸ (không giữ lưới bit) để engine
 * có thể lưu hàng trăm cái mà không phình bộ nhớ. `nestMulti` dùng kho này để
 * chọn ra 5 phương án khác nhau rõ rệt.
 */
export interface CandidateSnapshot {
  cost: number;
  nSheets: number;
  sheets: EngineSheet[];
  unplaced: string[];
  placedArea: number;
  /** Tổng diện tích tôn của các tấm đã dùng, mm². */
  totalArea: number;
  /** instance thứ i nằm ở tấm nào (−1 = không xếp được). */
  assign: Int32Array;
  /** Chiều dài tôn đã dùng của từng tấm, mm. */
  topY: number[];
}

export interface RunOptions {
  /** Danh sách tấm được khai (kèm vùng cấm). Rỗng = luôn dùng tấm nguyên khổ. */
  specs?: NestSheetSpec[];
  /** Gọi mỗi khi engine chấm xong một phương án. */
  onCandidate?: (snap: CandidateSnapshot) => void;
}

/** Giữ nguyên chữ ký cũ — mọi code đang gọi `nest()` không phải đổi gì. */
export function nest(input: NestInput, cb: NestCallbacks = {}): NestResult {
  return runNest(input, cb, {}).result;
}

export function runNest(
  input: NestInput, cb: NestCallbacks = {}, opts: RunOptions = {}
): { result: NestResult; best: CandidateSnapshot } {
  const params: NestParams = { ...DEFAULT_NEST_PARAMS, ...input.params };
  const now = cb.now ?? Date.now;
  const t0 = now();
  const deadline = t0 + Math.max(200, params.timeLimitMs);
  let rng = mulberry32(params.seed ?? 12345);

  // MỖI KHỔ TẤM MỘT NESTER. Lưới ô (gw × gh) phụ thuộc khổ tấm, mà tấm thừa
  // được khai có thể khác khổ tấm mới, nên không dùng chung một Nester được.
  // Cache theo khổ để các tấm cùng khổ dùng chung bộ nhớ đệm bitmap.
  const specs: NestSheetSpec[] = (opts.specs ?? []).filter((sp) => sp && sp.w > 0 && sp.h > 0);
  const nesterCache = new Map<string, Nester>();
  const nesterFor = (w: number, h: number): Nester => {
    const k = `${w}|${h}`;
    let n = nesterCache.get(k);
    if (!n) {
      n = new Nester(params, w, h);
      nesterCache.set(k, n);
    }
    return n;
  };
  const defaultNester = nesterFor(params.sheetW, params.sheetH);
  const specNester = specs.map((sp) => nesterFor(sp.w, sp.h));
  const specTpl = specs.map((sp, i) => specNester[i].buildBlockTemplate(sp.blocked));
  // Bộ góc hợp lệ phải tính theo khổ tấm TO NHẤT, nếu không một chi tiết chỉ
  // vừa tấm nguyên khổ sẽ bị loại oan vì tấm thừa đầu danh sách quá nhỏ.
  const nester = nesterFor(
    Math.max(params.sheetW, ...specs.map((sp) => sp.w)),
    Math.max(params.sheetH, ...specs.map((sp) => sp.h))
  );
  /** Mở tấm thứ k: theo đúng thứ tự khai, hết danh sách thì tấm mới nguyên khổ. */
  const makeSheet = (k: number): SheetGrid =>
    k < specs.length
      ? specNester[k].newSheet({ tpl: specTpl[k], specIndex: k, blocked: specs[k].blocked })
      : defaultNester.newSheet();

  const angStep = Math.max(1, params.rotationStep || 5);
  const nSteps = Math.max(1, Math.round(360 / angStep));

  // chuẩn bị chi tiết
  const preps: PartPrep[] = [];
  const unplacedFixed: string[] = [];
  for (const p of input.parts) {
    if (!p.enabled) continue;
    if (!p.fitsSheet) {
      for (let i = 0; i < Math.max(1, p.qty); i++) unplacedFixed.push(`${p.id}#${i}`);
      continue;
    }
    // Dùng HÌNH GỐC (không đơn giản hoá) để raster: hình đơn giản hoá có thể
    // hụt vào trong tới 1mm, khiến chi tiết lọt ra ngoài lề tấm.
    const simple = p.rings[0];
    const { angles, byDeg, byDegM } = buildAngles(simple, nester, params, nSteps, angStep);
    if (angles.length === 0) {
      for (let i = 0; i < Math.max(1, p.qty); i++) unplacedFixed.push(`${p.id}#${i}`);
      continue;
    }
    const idx = angles.map((_, i) => i);
    const byH = idx.slice().sort((a, b) => angles[a].bboxH - angles[b].bboxH);
    const byW = idx.slice().sort((a, b) => angles[a].bboxW - angles[b].bboxW);
    preps.push({ part: p, simple, angles, byH, byW, byDeg, byDegM });
  }

  const insts: Inst[] = [];
  preps.forEach((pp, idx) => {
    const q = Math.max(1, Math.floor(pp.part.qty) || 1);
    for (let i = 0; i < q; i++) insts.push({ prepIndex: idx, instance: i, area: pp.part.area });
  });

  const nInst = insts.length;
  if (nInst === 0) {
    return {
      result: {
        sheets: [], unplaced: unplacedFixed, utilization: 0,
        elapsedMs: now() - t0, iterations: 0, params,
      },
      best: {
        cost: 0, nSheets: 0, sheets: [], unplaced: unplacedFixed, placedArea: 0,
        totalArea: 0, assign: new Int32Array(0), topY: [],
      },
    };
  }

  /**
   * Bộ góc thử cho 1 chi tiết theo gen. Luôn kèm góc bbox nhỏ nhất, góc thấp
   * nhất theo trục dài tấm và góc hẹp nhất theo bề ngang tấm, cộng một cửa sổ
   * quanh giá trị gen để GA dò dần.
   */
  const ANGLE_TRIES = 10;
  const ANGLE_TRIES_EXACT = 10;
  const wantBuf: number[] = [];
  const seenBuf = new Set<number>();
  /**
   * `prevDeg`/`prevMir` là góc và trạng thái lật của chi tiết vừa đặt xong. Bộ
   * sườn tàu là một họ đường cong gần giống nhau, muốn LỒNG vào nhau thì thanh
   * sau phải hoặc xoay gần đúng bằng thanh trước (lồng đồng tâm), hoặc ÚP NGƯỢC
   * 180° (hai hình vòm ôm vào nhau).
   *
   * LẬT GƯƠNG: bản lật của cùng một góc là "cùng một đường cong nhìn từ mặt kia",
   * thường lồng khít hơn bản không lật, nên cả bốn tổ hợp (góc × lật) đều được
   * thử trước mọi ứng viên khác. Trước đây bảng tra chỉ có bản KHÔNG lật, nên dù
   * bật ô "lật gương" engine vẫn gần như không bao giờ chọn bản lật.
   */
  const angleCandsOf = (
    prep: PartPrep, gene: number, prevDeg: number, prevMir: boolean, tries: number
  ): AngleOpt[] => {
    const n = prep.angles.length;
    wantBuf.length = 0;
    if (prevDeg >= 0) {
      const k = Math.round(prevDeg / angStep) % nSteps;
      const kf = (k + Math.round(nSteps / 2)) % nSteps;
      const same = prevMir ? prep.byDegM : prep.byDeg;
      const other = prevMir ? prep.byDeg : prep.byDegM;
      wantBuf.push(same[k], same[kf], other[k], other[kf]);
      wantBuf.push(same[(k + 1) % nSteps], same[(k + nSteps - 1) % nSteps]);
    }
    wantBuf.push(gene % n, 0, prep.byH[0], prep.byW[0], (gene + 1) % n, (gene + n - 1) % n, 1);
    seenBuf.clear();
    const out: AngleOpt[] = [];
    for (const i of wantBuf) {
      if (i < 0 || i >= n || seenBuf.has(i)) continue;
      seenBuf.add(i);
      out.push(prep.angles[i]);
      if (out.length >= tries) break;
    }
    return out;
  };

  const abort = (): boolean => now() > workDeadline || cb.shouldStop?.() === true;

  /**
   * Giá của một phương án. Ưu tiên tuyệt đối: ít tấm nhất. Sau đó: dồn cho tấm
   * CUỐI càng ít càng tốt (vừa là đường dốc để xoá hẳn tấm cuối, vừa để tôn
   * thừa còn nguyên khổ). Cuối cùng: tổng chiều dài đã dùng càng ngắn càng chặt.
   * Tách riêng vì bước dọn tấm cuối phải CHẤM LẠI giá sau khi dời chi tiết.
   */
  const costOf = (used: SheetGrid[], nUnplaced: number): number => {
    const lastArea = used.length ? used[used.length - 1].usedArea : 0;
    const lastTop = used.length ? used[used.length - 1].maxRow * used[used.length - 1].nester.cell : 0;
    const sumTop = used.reduce((a, s) => a + s.maxRow * s.nester.cell, 0);
    return (used.length + nUnplaced * 10) * BIG + (lastArea / 1e6) * 1e7 + lastTop * 1e3 + sumTop;
  };
  const evaluate = (g: Genome, exact = false): Evaluated => {
    const sheets: SheetGrid[] = [makeSheet(0)];
    const sheetOf = new Int32Array(nInst).fill(-1);
    const unplaced: string[] = [];
    let placedArea = 0;
    let prevDeg = -1;
    let prevMir = false;
    for (const ii of g.order) {
      const inst = insts[ii];
      const prep = preps[inst.prepIndex];
      // Ở pha vét cạn mỗi góc đắt gấp cả trăm lần, nên thử ít góc hơn để một
      // lần đánh giá CHẠY XONG trong hạn — đánh giá dở dang thì vứt đi, phí sạch.
      const cands = angleCandsOf(prep, g.angleIdx[ii], prevDeg, prevMir, exact ? ANGLE_TRIES_EXACT : ANGLE_TRIES);
      let ok = -1;
      for (let s = 0; s < sheets.length; s++) {
        if (sheets[s].nester.place(sheets[s], prep, inst, cands, g.rule, exact, abort)) {
          ok = s;
          break;
        }
      }
      if (ok < 0) {
        // Mở tấm tiếp theo theo đúng THỨ TỰ KHAI. Nếu tấm khai kế tiếp cũng
        // không chứa nổi chi tiết này thì thử tấm khai sau nữa, cuối cùng mới
        // tới tấm mới nguyên khổ.
        // Cận trên = max(số tấm khai, số tấm đang mở): vòng CUỐI luôn ứng với
        // một tấm MỚI NGUYÊN KHỔ (makeSheet(k) với k >= specs.length), nên khi
        // không khai tấm nào (specs rỗng) engine vẫn mở tấm mới như xưa.
        const kLast = Math.max(specs.length, sheets.length);
        for (let k = sheets.length; k <= kLast; k++) {
          const sh = makeSheet(k);
          if (!sh.nester.place(sh, prep, inst, cands, g.rule, exact, abort)) continue;
          // các tấm khai bị nhảy qua vẫn phải mở ra để giữ đúng thứ tự + để
          // những chi tiết sau còn có cơ hội xếp vào chúng
          while (sheets.length < k) sheets.push(makeSheet(sheets.length));
          sheets.push(sh);
          ok = sheets.length - 1;
          break;
        }
      }
      if (ok >= 0) {
        placedArea += prep.part.area;
        sheetOf[ii] = ok;
        const pls = sheets[ok].placements;
        prevDeg = pls[pls.length - 1].rotationDeg;
        prevMir = pls[pls.length - 1].mirrored;
      } else unplaced.push(`${prep.part.id}#${inst.instance}`);
    }
    const used = sheets.filter((s) => s.placements.length > 0);
    const layouts: EngineSheet[] = used.map((s, i) => ({
      index: i,
      width: s.w,
      height: s.h,
      placements: s.placements,
      usedArea: s.usedArea,
      utilization: s.usedArea / (s.w * s.h),
      specIndex: s.specIndex,
      blocked: s.blocked,
    }));
    const lastIdx = sheets.length - 1;
    const lastSheetInsts: number[] = [];
    for (let i = 0; i < nInst; i++) if (sheetOf[i] === lastIdx) lastSheetInsts.push(i);

    // Ưu tiên tuyệt đối: ít tấm nhất. Sau đó: dồn cho tấm CUỐI càng ít càng tốt
    // (vừa là đường dốc để xoá hẳn tấm cuối, vừa để tôn thừa còn nguyên khổ).
    // Cuối cùng: tổng chiều dài đã dùng của mọi tấm càng ngắn càng chặt.
    const cost = costOf(used, unplaced.length);
    return {
      genome: g, cost, sheets: layouts, unplaced: unplaced.concat(unplacedFixed),
      placedArea, nSheets: used.length, lastSheetInsts, grids: used, sheetOf,
    };
  };

  // ── cá thể khởi đầu ──────────────────────────────────────────────────────
  const idxAll = insts.map((_, i) => i);
  const byArea = idxAll.slice().sort((a, b) => insts[b].area - insts[a].area);
  const byLen = idxAll.slice().sort(
    (a, b) => preps[insts[b].prepIndex].part.maxLength - preps[insts[a].prepIndex].part.maxLength
  );
  const byBBox = idxAll.slice().sort((a, b) => {
    const pa = preps[insts[a].prepIndex].part.bbox;
    const pb = preps[insts[b].prepIndex].part.bbox;
    return (pb.maxX - pb.minX) * (pb.maxY - pb.minY) - (pa.maxX - pa.minX) * (pa.maxY - pa.minY);
  });
  const byMinW = idxAll.slice().sort(
    (a, b) => preps[insts[a].prepIndex].part.minWidth - preps[insts[b].prepIndex].part.minWidth
  );

  // Thứ tự xen kẽ: lấy cách một chi tiết. Với bộ sườn tàu (các đường cong cùng họ)
  // cách xếp này tách được 2 nhóm cùng độ cong, mỗi nhóm lồng vào nhau rất khít.
  const interA = byArea.filter((_, i) => i % 2 === 0).concat(byArea.filter((_, i) => i % 2 === 1));
  const interB = byArea.filter((_, i) => i % 2 === 1).concat(byArea.filter((_, i) => i % 2 === 0));
  const byMinWDesc = byMinW.slice().reverse();
  const byLenAsc = byLen.slice().reverse();

  const zeroAngles = () => new Array(nInst).fill(0);
  const seeds: Genome[] = [];
  const baseOrders = [byArea, byLen, byBBox, interA, interB, byMinWDesc, byMinW, byLenAsc];
  for (let rule = 0; rule < 4; rule++) {
    for (const o of baseOrders) seeds.push({ order: o.slice(), angleIdx: zeroAngles(), rule });
  }

  const POP = 24;
  const shuffled = (): number[] => {
    const o = idxAll.slice();
    for (let i = o.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      [o[i], o[j]] = [o[j], o[i]];
    }
    return o;
  };

  let iterations = 0;
  let best: Evaluated | null = null;
  let lastReport = t0;
  /**
   * HAI PHA. Pha 1 đặt chi tiết bằng phép thả rơi (rẻ, ~20 lần/giây) để dò ra
   * THỨ TỰ và BỘ GÓC tốt. Pha 2 giữ nguyên bộ gen đó nhưng đặt bằng quét vét
   * cạn (đắt, ~2 lần/giây) để siết cho khít. Đo trên file mẫu: chỉ-thả-rơi cho
   * dải 13,2m, chỉ-vét-cạn cho 12,4m nhưng chạy được quá ít phương án; ghép hai
   * pha lấy được cả cấu trúc tốt lẫn độ khít.
   */
  /**
   * Mốc chuyển pha TRONG MỘT CHẶNG. Đo thật trên file mẫu (dải 2000 × N, ngân
   * sách 60 giây, trung bình 2 hạt giống — dải càng ngắn càng tốt):
   *   chuyển ở 20%: 12.361mm · 35%: 12.252mm · 50%: 12.264mm · 65%: 12.453mm
   * Pha siết chặt mới (đặt vào hốc) là pha ĐẺ RA kết quả, nên phải cho nó quá
   * nửa ngân sách. Chọn 40%.
   */
  const EXACT_AT = 0.40;
  let switchAt = t0 + Math.max(200, params.timeLimitMs) * EXACT_AT;
  let exact = false;
  /**
   * Hạn cho vòng tìm kiếm — DÀNH LẠI một quỹ cho pha hậu xử lý (gộp tấm + dọn
   * tấm cuối) ở cuối hàm. Không dành thì vòng GA ăn hết giờ và pha đó không chạy
   * được ô nào. Đo thật ở ngân sách 180 giây: pha này chạy ~0,37 giây một lượt
   * dọn và ~3 giây một lượt gộp, và CHÍNH nó là nước biến 7/7/1 thành 8/7 (bớt
   * hẳn một tấm) ở những hạt giống mà vòng tiến hoá tự mình không tìm ra. Nên
   * quỹ rộng tay: 20% ngân sách, tối đa 30 giây.
   *
   * ĐÃ THỬ NỚI LÊN 25% / 45 giây: ĐO RA XẤU HƠN — 5 hạt giống ở 180 giây cho
   * 2/5 lượt ra 2 tấm, so với 4/5 khi giữ 20% / 30 giây. Vòng tiến hoá cần giờ
   * hơn pha cuối cần, nên giữ nguyên mốc cũ.
   */
  const sweepBudget = Math.min(30_000, Math.max(200, params.timeLimitMs) * 0.2);
  let workDeadline = deadline - sweepBudget;

  const report = (label: string) => {
    if (!cb.onProgress) return;
    const el = now() - t0;
    cb.onProgress({
      fraction: Math.min(1, el / params.timeLimitMs),
      elapsedMs: el,
      iterations,
      best: best ? toResult(best, params, now() - t0, iterations) : null,
      label,
    });
  };

  /**
   * Chụp lại một phương án ở dạng nhẹ. PHẢI copy mảng `placements` vì mảng gốc
   * thuộc về lưới của phương án và còn bị bước "dọn tấm cuối" sửa về sau.
   */
  const snapOf = (e: Evaluated): CandidateSnapshot => ({
    cost: e.cost,
    nSheets: e.nSheets,
    sheets: e.sheets.map((sh) => ({ ...sh, placements: sh.placements.slice() })),
    unplaced: e.unplaced.slice(),
    placedArea: e.placedArea,
    totalArea: e.sheets.reduce((a, sh) => a + sh.width * sh.height, 0),
    assign: e.sheetOf.slice(),
    topY: e.grids.map((g) => g.maxRow * g.nester.cell),
  });

  /** Tra instance theo "partId#instance" — dùng ở pha hậu xử lý. */
  const instKey = new Map<string, number>();
  insts.forEach((it, i) => instKey.set(`${preps[it.prepIndex].part.id}#${it.instance}`, i));

  /**
   * HẬU XỬ LÝ — DỌN TẤM CUỐI.
   * Mục tiêu của đề bài là ÍT TẤM NHẤT, nên việc đáng giá nhất sau khi tìm kiếm
   * là thử nhấc từng chi tiết đang nằm ở tấm cuối sang các tấm trước, quét TOÀN
   * BỘ góc xoay chứ không chỉ vài góc như trong vòng lặp GA. Nếu dọn sạch được
   * thì bớt hẳn một tấm; nếu không thì tấm cuối cũng nhẹ đi, phần tôn thừa còn
   * nguyên khổ hơn. Chỉ THÊM chi tiết vào tấm trước nên không phá ràng buộc nào.
   */
  const sweepLastSheet = (e: Evaluated, until: number): boolean => {
    if (e.grids.length < 2) return false;
    const last = e.grids[e.grids.length - 1];
    if (last.placements.length === 0 || last.placements.length > 4) return false;
    const byPartId = new Map<string, number>();
    preps.forEach((pp, i) => byPartId.set(pp.part.id, i));
    let movedAny = false;
    for (const pl of last.placements.slice()) {
      if (now() > until || cb.shouldStop?.()) break;
      const pi = byPartId.get(pl.partId);
      if (pi === undefined) continue;
      const prep = preps[pi];
      const inst: Inst = { prepIndex: pi, instance: pl.instance, area: prep.part.area };
      let moved = false;
      // Vòng 1: quét TOÀN BỘ góc bằng phép đặt nhanh (mỗi góc cỡ 1ms).
      for (let sIdx = 0; sIdx < e.grids.length - 1 && !moved; sIdx++) {
        if (e.grids[sIdx].nester.place(e.grids[sIdx], prep, inst, prep.angles, e.genome.rule, false, abort)) moved = true;
      }
      // Vòng 2: chưa lọt thì trả giá pha SIẾT CHẶT (đặt vào hốc) — đắt hơn nhưng
      // đây là nước cờ cuối để xoá hẳn một tấm nên đáng quét TOÀN BỘ góc, kể cả
      // bản lật gương. Bốn kiểu xếp (rule) cũng được thử vì mỗi kiểu ưu tiên một
      // hướng ép sát khác nhau.
      if (!moved) {
        for (let r = 0; r < 4 && !moved; r++) {
          const rule = (e.genome.rule + r) % 4;
          for (let sIdx = 0; sIdx < e.grids.length - 1 && !moved; sIdx++) {
            if (now() > until || cb.shouldStop?.()) break;
            if (e.grids[sIdx].nester.place(e.grids[sIdx], prep, inst, prep.angles, rule, true, abort)) moved = true;
          }
        }
      }
      if (!moved) continue;
      const k = last.placements.indexOf(pl);
      if (k >= 0) last.placements.splice(k, 1);
      last.usedArea -= prep.part.area;
      movedAny = true;
    }
    if (!movedAny) return false;
    const used = e.grids.filter((g) => g.placements.length > 0);
    e.grids = used;
    e.nSheets = used.length;
    e.sheets = used.map((g, i) => ({
      index: i,
      width: g.w,
      height: g.h,
      placements: g.placements,
      usedArea: g.usedArea,
      utilization: g.usedArea / (g.w * g.h),
      specIndex: g.specIndex,
      blocked: g.blocked,
    }));
    // sheetOf / lastSheetInsts phải dựng lại: chi tiết vừa đổi tấm. Không dựng
    // thì vân tay cách chia, ảnh chụp cho giao diện và phép đột biến "đánh vào
    // tấm cuối" đều đọc nhầm bản cũ.
    e.sheetOf = new Int32Array(nInst).fill(-1);
    used.forEach((g, gi) => {
      for (const pl of g.placements) {
        const k = instKey.get(`${pl.partId}#${pl.instance}`);
        if (k !== undefined) e.sheetOf[k] = gi;
      }
    });
    e.lastSheetInsts = [];
    for (let i = 0; i < nInst; i++) if (e.sheetOf[i] === used.length - 1) e.lastSheetInsts.push(i);
    e.cost = costOf(used, e.unplaced.length - unplacedFixed.length);
    return true;
  };
  /**
   * CẬN DƯỚI SỐ TẤM theo diện tích: không tấm nào chứa nổi nhiều tôn hơn diện
   * tích của chính nó. Chạm cận này là hết đường bớt tấm — dùng để biết khi nào
   * nên thôi, cả trong vòng tiến hoá lẫn ở pha cuối.
   */
  const cậnDưới = Math.max(
    1,
    Math.ceil(insts.reduce((a, it) => a + it.area, 0) / Math.max(1, params.sheetW * params.sheetH))
  );

  const pop: Evaluated[] = [];
  /**
   * HỘI ĐỒNG — những phương án ĐÁNG DỌN TẤM CUỐI, giữ xuyên suốt mọi chặng.
   * Quần thể `pop` bị xoá sạch mỗi khi sang chặng mới (xem vòng chặng bên dưới),
   * mà phương án "chỉ thừa đúng 1 chi tiết ở tấm cuối" — loại dọn được là bớt
   * hẳn một tấm — có thể đã xuất hiện ở chặng trước. Nên phải giữ riêng.
   *
   * VÀ PHẢI ĐA DẠNG — mỗi CÁCH CHIA chỉ giữ MỘT bản.
   *
   * Vì sao: đo thật ở ngân sách 180 giây, hội đồng cũ (danh sách phẳng, chọn
   * theo giá) chứa 8-12 bản của CÙNG một cách chia (ví dụ 7/7/1 lặp lại), nên
   * pha gộp tấm ở cuối thử đi thử lại đúng một bài toán đã thua. Khoá theo
   * "chi tiết nào nằm chung tấm nào" rồi mỗi khoá giữ bản rẻ nhất, pha gộp
   * mới thật sự được thử NHIỀU cách chia khác nhau.
   */
  const hall = new Map<string, Evaluated>();
  /** Vân tay CÁCH CHIA: nhóm chi tiết theo tấm, không phụ thuộc thứ tự tấm. */
  const partSig = (e: Evaluated): string => {
    const groups: number[][] = e.grids.map(() => []);
    for (let i = 0; i < nInst; i++) {
      const g = e.sheetOf[i];
      if (g >= 0 && g < groups.length) groups[g].push(i);
    }
    return groups
      .map((g) => g.join(','))
      .sort()
      .join('|');
  };
  const remember = (e: Evaluated) => {
    if (e.grids.length < 2) return;
    // Ngưỡng bằng đúng ngưỡng của tryMergeSheets: tấm cuối ≤ 4 chi tiết thì
    // mới đáng mang đi gộp. Trước đây là 3 — hẹp hơn cả bước dùng nó.
    if (e.grids[e.grids.length - 1].placements.length > 4) return;
    const k = partSig(e);
    const cũ = hall.get(k);
    if (cũ && cũ.cost <= e.cost) return;
    hall.set(k, e);
    if (hall.size > 96) {
      const giữ = [...hall.entries()].sort((a, b) => a[1].cost - b[1].cost).slice(0, 64);
      hall.clear();
      for (const [kk, vv] of giữ) hall.set(kk, vv);
    }
  };
  /** Số phương án liên tiếp không cải thiện — để biết khi nào GA đã bế tắc. */
  let sinceImprove = 0;
  /**
   * ĐÃ THỬ, ĐO RA KHÔNG ĂN THUA: gọi "dọn tấm cuối" NGAY trong vòng tiến hoá
   * mỗi khi có phương án dẫn đầu mới (chặn 8% quỹ, mỗi cách chia một lần).
   * 10 hạt giống ở ngân sách 180 giây: 6/10 lượt ra 2 tấm — ĐÚNG BẰNG bản không
   * dọn sớm. Nước dọn ăn mất giờ của vòng tiến hoá đúng bằng phần nó kiếm thêm,
   * nên bỏ cho gọn. Ghi lại đây để người sau khỏi thử lại.
   */
  const consider = (e: Evaluated) => {
    iterations++;
    opts.onCandidate?.(snapOf(e));
    pop.push(e);
    remember(e);
    if (!best || e.cost < best.cost) {
      best = e;
      sinceImprove = 0;
    } else sinceImprove++;
    if (now() - lastReport > 250) {
      lastReport = now();
      report(iterations <= seeds.length ? 'Đang thử phương án khởi đầu…' : 'Đang tối ưu…');
    }
  };

  /**
   * CHIA NGÂN SÁCH THÀNH NHIỀU CHẶNG ĐỘC LẬP.
   *
   * Vì sao: đo thật 6 hạt giống ở ngân sách 180 giây trên file mẫu — 5 lượt cho
   * 3 tấm, 1 lượt (hạt 777) cho 2 TẤM. Tức lời giải 2 tấm CÓ TỒN TẠI và engine
   * tìm được, nhưng nó phụ thuộc vào việc quần thể ban đầu rơi vào lưu vực nào.
   * Chạy một mạch 180 giây thì chỉ bốc đúng MỘT lưu vực; chia thành 4 chặng 45
   * giây, mỗi chặng gieo lại quần thể bằng một dòng ngẫu nhiên khác, là bốc BỐN
   * lần. Phương án tốt nhất (`best`) và hội đồng được giữ xuyên chặng nên không
   * mất gì, chỉ được thêm cơ hội.
   *
   * Ngân sách nhỏ (≤ 67 giây) vẫn chạy một chặng như cũ — chia nhỏ nữa thì mỗi
   * chặng không đủ cho pha siết chặt.
   */
  const workBudget = workDeadline - t0;
  const nSeg = Math.max(1, Math.min(4, Math.round(Math.max(200, params.timeLimitMs) / 45_000)));
  const baseSeed = params.seed ?? 12345;

  for (let seg = 0; seg < nSeg; seg++) {
    if (now() >= workDeadline || cb.shouldStop?.()) break;
    const segEnd = Math.min(workDeadline, t0 + Math.round((workBudget * (seg + 1)) / nSeg));
    const segStart = t0 + Math.round((workBudget * seg) / nSeg);
    switchAt = segStart + Math.round((workBudget / nSeg) * EXACT_AT);
    exact = false;
    sinceImprove = 0;
    pop.length = 0;
    // Chặng sau dùng một DÒNG NGẪU NHIÊN KHÁC — đó mới là thứ đổi lưu vực.
    if (seg > 0) rng = mulberry32(baseSeed + seg * 7919);
    const segSeeds: Genome[] = seg === 0
      ? seeds
      : baseOrders.map((o) => ({
          order: o.slice(),
          angleIdx: idxAll.map((i) => Math.floor(rng() * preps[insts[i].prepIndex].angles.length)),
          rule: Math.floor(rng() * 4),
        }));
    for (const g of segSeeds) {
      if (now() > segEnd || cb.shouldStop?.()) break;
      consider(evaluate(g));
    }
    if (pop.length === 0) {
      if (!best) {
        best = evaluate(seeds[0]);
        iterations++;
        pop.push(best);
      } else break;
    }

  // ── vòng tiến hoá ────────────────────────────────────────────────────────
  const orderCrossover = (a: number[], b: number[]): number[] => {
    const n = a.length;
    let i = Math.floor(rng() * n);
    let j = Math.floor(rng() * n);
    if (i > j) [i, j] = [j, i];
    const child = new Array<number>(n).fill(-1);
    const taken = new Set<number>();
    for (let k = i; k <= j; k++) {
      child[k] = a[k];
      taken.add(a[k]);
    }
    let w = 0;
    for (const v of b) {
      if (taken.has(v)) continue;
      while (child[w] !== -1) w++;
      child[w] = v;
    }
    return child;
  };

  /** Đưa toàn bộ chi tiết đang nằm ở tấm cuối lên đầu hàng đợi — đánh thẳng vào tấm thừa. */
  const lastSheetFirst = (e: Evaluated): number[] => {
    if (!e.lastSheetInsts.length) return e.genome.order.slice();
    const set = new Set(e.lastSheetInsts);
    return e.lastSheetInsts.concat(e.genome.order.filter((v) => !set.has(v)));
  };

    while (now() < segEnd && !cb.shouldStop?.()) {
    if (!exact && now() >= switchAt) {
      exact = true;
      sinceImprove = 0;
      pop.sort((x, y) => x.cost - y.cost);
      const elite = pop.slice(0, 4).map((e) => e.genome);
      pop.length = 0;
      for (const g of elite) {
        if (now() >= segEnd || cb.shouldStop?.()) break;
        consider(evaluate(g, true));
      }
      if (pop.length === 0) break;
    }
    // KHỞI ĐỘNG LẠI KHI BẾ TẮC. Đo thực tế: chạy 60s ra đúng kết quả của 20s,
    // tức quần thể đã hội tụ vào một cực trị cục bộ và phần thời gian còn lại
    // bị phí. Gieo lại quần thể (vẫn giữ phương án tốt nhất) cho biên độ giữa
    // các lần gieo biến thành phần thắng, thay vì phải may mắn ngay từ đầu.
    if (sinceImprove > (exact ? STALL_LIMIT >> 2 : STALL_LIMIT) && best) {
      sinceImprove = 0;
      const keep = best;
      pop.length = 0;
      pop.push(keep);
      // PHÁ–DỰNG LẠI: nhấc ngẫu nhiên vài chi tiết ra khỏi thứ tự của phương án
      // tốt nhất rồi chèn lại chỗ khác, kèm đổi góc vài chi tiết. Gieo lại bằng
      // thứ tự NGẪU NHIÊN HOÀN TOÀN đo ra kết quả xấu hơn (14.462 so với 13.511mm
      // trên dải dài): thứ tự "to trước / xen kẽ" là cấu trúc phải giữ.
      for (let k = 0; k < POP >> 2; k++) {
        if (now() >= segEnd || cb.shouldStop?.()) break;
        const order = keep.genome.order.slice();
        const angleIdx = keep.genome.angleIdx.slice();
        const moves = 3 + Math.floor(rng() * 5);
        for (let m = 0; m < moves; m++) {
          const from = Math.floor(rng() * nInst);
          const to = Math.floor(rng() * nInst);
          const [v] = order.splice(from, 1);
          order.splice(to, 0, v);
        }
        for (let m = 0; m < 5; m++) {
          const i = Math.floor(rng() * nInst);
          angleIdx[i] = Math.floor(rng() * preps[insts[i].prepIndex].angles.length);
        }
        consider(evaluate({ order, angleIdx, rule: Math.floor(rng() * 4) }, exact));
      }
      for (const o of baseOrders) {
        if (now() >= segEnd || cb.shouldStop?.()) break;
        consider(evaluate({
          order: o.slice(),
          angleIdx: idxAll.map((i) => Math.floor(rng() * preps[insts[i].prepIndex].angles.length)),
          rule: Math.floor(rng() * 4),
        }, exact));
      }
    }
    pop.sort((x, y) => x.cost - y.cost);
    if (pop.length > POP) pop.length = POP;
    const pa = pop[Math.floor(rng() * Math.min(6, pop.length))];
    const pb = pop[Math.floor(rng() * pop.length)];

    const roll = rng();
    let order: number[];
    if (roll < 0.15) order = lastSheetFirst(pa);
    else if (roll < 0.22) order = shuffled();
    else order = orderCrossover(pa.genome.order, pb.genome.order);

    const angleIdx = pa.genome.angleIdx.slice();
    // đột biến thứ tự: hoán vị + phép "nhấc một chi tiết chèn chỗ khác"
    const swaps = 1 + Math.floor(rng() * 3);
    for (let k = 0; k < swaps; k++) {
      const i = Math.floor(rng() * nInst);
      const j = Math.floor(rng() * nInst);
      [order[i], order[j]] = [order[j], order[i]];
    }
    if (rng() < 0.5) {
      const from = Math.floor(rng() * nInst);
      const to = Math.floor(rng() * nInst);
      const [v] = order.splice(from, 1);
      order.splice(to, 0, v);
    }
    const angMut = 1 + Math.floor(rng() * 4);
    for (let k = 0; k < angMut; k++) {
      const i = Math.floor(rng() * nInst);
      const prep = preps[insts[i].prepIndex];
      angleIdx[i] =
        rng() < 0.5
          ? Math.floor(rng() * prep.angles.length)
          : Math.floor(rng() * Math.min(10, prep.angles.length));
    }
    const rule = rng() < 0.25 ? Math.floor(rng() * 4) : pa.genome.rule;
    consider(evaluate({ order, angleIdx, rule }, exact));
    } // hết vòng tiến hoá của chặng này
  } // hết một CHẶNG — chặng sau gieo lại quần thể bằng dòng ngẫu nhiên khác

  if (!best) {
    best = evaluate(seeds[0]);
    iterations++;
    remember(best);
  }

  /** Dựng một tấm trống ĐÚNG loại (khổ + vùng cấm) của một lưới đang có. */
  const blankLike = (g: SheetGrid): SheetGrid =>
    g.specIndex >= 0
      ? specNester[g.specIndex].newSheet({
          tpl: specTpl[g.specIndex], specIndex: g.specIndex, blocked: specs[g.specIndex].blocked,
        })
      : defaultNester.newSheet();

  /**
   * XẾP LẠI TỪ ĐẦU một nhóm chi tiết lên MỘT tấm. Trả về lưới nếu nhét được HẾT,
   * null nếu không. Thử lần lượt nhiều thứ tự; mỗi thứ tự đặt bằng pha siết chặt
   * (có đặt vào hốc) nên đây là phép thử "nhóm này có vừa một tấm không" mạnh
   * nhất mà engine có.
   */
  const repackOnOneSheet = (like: SheetGrid, group: number[], until: number): SheetGrid | null => {
    const orders: number[][] = [
      group.slice().sort((a, b) => insts[b].area - insts[a].area),
      group.slice().sort((a, b) => preps[insts[b].prepIndex].part.maxLength - preps[insts[a].prepIndex].part.maxLength),
      group.slice().sort((a, b) => insts[a].area - insts[b].area),
    ];
    const big = orders[0];
    orders.push(big.filter((_, i) => i % 2 === 0).concat(big.filter((_, i) => i % 2 === 1)));
    /**
     * THỨ TỰ THỬ LÀ VÔ HẠN, DỪNG THEO ĐỒNG HỒ.
     * Bản cũ chốt cứng 44 thứ tự; đo thật thì 44 thứ tự × 4 kiểu xếp chạy hết
     * trong ~3 giây rồi hàm trả "không vừa", trong khi quỹ cấp cho nó là 15
     * giây — tức 80% thời gian của nước cờ ăn tiền nhất bị vứt đi. Nay cứ còn
     * giờ là còn sinh thứ tự ngẫu nhiên mới để thử.
     */
    let qi = 0;
    const nextOrder = (): number[] => {
      if (qi < orders.length) return orders[qi++];
      const o = big.slice();
      for (let i = o.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [o[i], o[j]] = [o[j], o[i]];
      }
      return o;
    };
    while (now() <= until && !cb.shouldStop?.()) {
      const order = nextOrder();
      for (let rule = 0; rule < 4; rule++) {
        if (now() > until || cb.shouldStop?.()) return null;
        const sh = blankLike(like);
        let prevDeg = -1;
        let prevMir = false;
        let ok = true;
        for (const ii of order) {
          const inst = insts[ii];
          const prep = preps[inst.prepIndex];
          const cands = angleCandsOf(prep, 0, prevDeg, prevMir, ANGLE_TRIES_EXACT);
          if (!sh.nester.place(sh, prep, inst, cands, rule, true, () => now() > until)) {
            ok = false;
            break;
          }
          const pl = sh.placements[sh.placements.length - 1];
          prevDeg = pl.rotationDeg;
          prevMir = pl.mirrored;
        }
        if (ok) return sh;
      }
    }
    return null;
  };

  /**
   * GỘP HAI TẤM LÀM MỘT — nước cờ quyết định "3 tấm hay 2 tấm".
   *
   * Vì sao cần, dù đã có bước dọn tấm cuối: dọn tấm cuối chỉ THÊM chi tiết vào
   * chỗ trống còn lại của tấm trước, giữ nguyên cách sắp sẵn có. Tấm trước đã
   * xếp chặt cho 7 chi tiết thì gần như không còn khe nào nhét thêm chi tiết
   * thứ 8 — dù nếu XẾP LẠI CẢ TÁM từ đầu thì chúng vừa.
   *
   * Nên ở đây làm đúng thế: gom chi tiết của tấm cuối với chi tiết của một tấm
   * khác rồi xếp lại toàn bộ nhóm đó lên một tấm trống. Vừa thì bớt hẳn một tấm.
   * Đây chính là bước đưa file mẫu từ 3 tấm xuống 2 tấm.
   */
  const tryMergeSheets = (e: Evaluated, until: number): boolean => {
    if (e.grids.length < 2) return false;
    const lastIdx = e.grids.length - 1;
    const last = e.grids[lastIdx];
    if (last.placements.length === 0 || last.placements.length > 4) return false;
    const idsOf = (g: SheetGrid): number[] => {
      const out: number[] = [];
      for (const pl of g.placements) {
        const k = instKey.get(`${pl.partId}#${pl.instance}`);
        if (k === undefined) return [];
        out.push(k);
      }
      return out;
    };
    const lastIds = idsOf(last);
    if (lastIds.length === 0) return false;
    // Ưu tiên tấm RỖNG NHẤT — còn nhiều chỗ nhất nên dễ nuốt thêm nhất.
    const order = e.grids
      .map((g, i) => i)
      .filter((i) => i !== lastIdx)
      .sort((a, b) => e.grids[a].usedArea - e.grids[b].usedArea);
    // Quỹ phải CHIA cho từng tấm bạn: repackOnOneSheet nay chạy tới hết giờ
    // được cấp, không chia thì tấm bạn đầu tiên ăn sạch quỹ.
    let còn = order.length;
    for (const oi of order) {
      if (now() > until || cb.shouldStop?.()) break;
      const other = e.grids[oi];
      const otherIds = idsOf(other);
      if (otherIds.length === 0) { còn--; continue; }
      const hạn = Math.min(until, now() + Math.max(500, Math.floor((until - now()) / Math.max(1, còn))));
      còn--;
      const merged = repackOnOneSheet(other, otherIds.concat(lastIds), hạn);
      if (!merged) continue;
      const grids = e.grids.filter((_, i) => i !== lastIdx && i !== oi);
      grids.splice(Math.min(oi, grids.length), 0, merged);
      e.grids = grids;
      e.nSheets = grids.length;
      e.sheets = grids.map((g, i) => ({
        index: i,
        width: g.w,
        height: g.h,
        placements: g.placements,
        usedArea: g.usedArea,
        utilization: g.usedArea / (g.w * g.h),
        specIndex: g.specIndex,
        blocked: g.blocked,
      }));
      // sheetOf phải dựng lại: chi tiết đã đổi tấm.
      e.sheetOf = new Int32Array(nInst).fill(-1);
      grids.forEach((g, gi) => {
        for (const pl of g.placements) {
          const k = instKey.get(`${pl.partId}#${pl.instance}`);
          if (k !== undefined) e.sheetOf[k] = gi;
        }
      });
      e.lastSheetInsts = [];
      for (let i = 0; i < nInst; i++) if (e.sheetOf[i] === grids.length - 1) e.lastSheetInsts.push(i);
      e.cost = costOf(grids, e.unplaced.length - unplacedFixed.length);
      return true;
    }
    return false;
  };

  /**
   * DỌN TẤM CUỐI CHO NHIỀU PHƯƠNG ÁN, không riêng phương án tốt nhất.
   * Phương án đang dẫn đầu có thể là loại "hai tấm rất đầy + tấm cuối 3 chi tiết"
   * — dọn không nổi. Trong khi một phương án xếp hạng dưới lại chỉ thừa ĐÚNG một
   * chi tiết ở tấm cuối, dọn được là bớt hẳn một tấm. Vì vậy quét vài phương án
   * đầu bảng rồi mới chốt.
   */
  workDeadline = deadline;
  if (best && !cb.shouldStop?.()) {
    // Danh sách thử: phương án tốt nhất trước, rồi các CÁCH CHIA khác nhau
    // trong hội đồng, rẻ trước. Khử trùng theo vân tay cách chia.
    const đãThử = new Set<string>();
    const thử: Evaluated[] = [best];
    đãThử.add(partSig(best));
    for (const e of [...hall.values()].sort((x, y) => x.cost - y.cost)) {
      const k = partSig(e);
      if (đãThử.has(k)) continue;
      đãThử.add(k);
      thử.push(e);
    }
    /**
     * QUỸ CHO MỘT LẦN THỬ GỘP. Đo thật: một lần gộp có ích chạy 5-8 giây là
     * đủ dùng hết các thứ tự đáng thử; cấp rộng hơn thì chỉ thử được 2-3 cách
     * chia trong 30 giây, mà bài học từ bản cũ đúng là "thử ít cách chia quá".
     */
    const LÁT = 6_000;

    const nộp = (e: Evaluated) => {
      opts.onCandidate?.(snapOf(e));
      if (e.cost < best!.cost) best = e;
    };

    /**
     * LƯỢT 1 — DỌN TẤM CUỐI, RẺ TRƯỚC.
     * Nước này chỉ nhấc vài chi tiết của tấm cuối sang tấm trước, giữ nguyên
     * cách sắp đã tốt, nên chạy dưới một giây và đúng là nước biến 7/7/1 thành
     * 8/7. Đo thật ở bản trước: pha gộp (đắt, 3 giây/lượt) ăn sạch quỹ cuối và
     * KHÔNG lần nào thành công, còn nước dọn rẻ này thì không bao giờ tới lượt.
     * Nay dọn hết lượt các cách chia trước, gộp mới tới sau.
     */
    // Chia đôi quỹ cuối: nửa cho lượt dọn (rẻ, quét được nhiều cách chia),
    // nửa cho lượt gộp (đắt). Không chia thì lượt rẻ ăn hết giờ khi hội đồng
    // đông, đúng lỗi ngược lại của bản trước.
    const hạnDọn = now() + Math.floor((deadline - now()) / 2);
    for (const e of thử) {
      if (now() > hạnDọn || cb.shouldStop?.()) break;
      if (best!.nSheets <= cậnDưới) break;
      const until = Math.min(hạnDọn, now() + 2_000);
      const đổi = sweepLastSheet(e, until);
      if (đổi) nộp(e);
    }

    /**
     * LƯỢT 2 — GỘP HAI TẤM, ĐẮT SAU. Xếp lại từ đầu cả hai tấm lên một tấm là
     * nước mạnh nhất nhưng tốn vài giây một lần, nên chỉ tiêu phần giờ còn lại.
     */
    for (const e of thử) {
      if (now() > deadline || cb.shouldStop?.()) break;
      if (best!.nSheets <= cậnDưới) break;
      let đổi = false;
      // Gộp LIÊN TIẾP: 4 tấm có thể xuống 3 rồi xuống 2 trong cùng một lượt.
      while (now() < deadline && !cb.shouldStop?.()) {
        const until = Math.min(deadline, now() + LÁT);
        if (!tryMergeSheets(e, until)) break;
        đổi = true;
      }
      if (đổi) nộp(e);
    }
  }

  const res = toResult(best!, params, now() - t0, iterations);
  const bestSnap = snapOf(best!);
  // Phương án tốt nhất SAU khi dọn tấm cuối cũng phải vào kho, vì bản trước khi
  // dọn đã nằm trong kho rồi và nó khác hẳn bản cuối cùng.
  opts.onCandidate?.(bestSnap);
  report('Xong');
  return { result: res, best: bestSnap };
}

function toResult(e: Evaluated, params: NestParams, elapsed: number, iterations: number): NestResult {
  const total = e.sheets.reduce((a, s) => a + s.width * s.height, 0);
  return {
    sheets: e.sheets,
    unplaced: e.unplaced,
    utilization: total > 0 ? e.placedArea / total : 0,
    elapsedMs: elapsed,
    iterations,
    params,
  };
}

// ─────────────────────────── Kiểm tra kết quả ───────────────────────────

export interface ValidationIssue {
  kind: 'overlap' | 'gap' | 'outside' | 'missing' | 'blocked';
  message: string;
  a?: string;
  b?: string;
  value?: number;
}

function placedRings(pl: Placement, part: Part): Ring[] {
  return part.rings.map((r) => applyPlacementRing(r, pl));
}

/** Khoảng cách nhỏ nhất giữa 2 vòng (0 nếu cắt nhau hoặc lồng nhau). */
function ringDistance(a: Ring, b: Ring): number {
  let min = Infinity;
  for (let i = 0; i < a.length; i++) {
    const a1 = a[i];
    const a2 = a[(i + 1) % a.length];
    for (let j = 0; j < b.length; j++) {
      const b1 = b[j];
      const b2 = b[(j + 1) % b.length];
      if (segSegIntersect(a1, a2, b1, b2)) return 0;
      const d = segSegDistance(a1, a2, b1, b2);
      if (d < min) min = d;
    }
  }
  if (pointInRing(a[0], b) || pointInRing(b[0], a)) return 0;
  return min === Infinity ? Infinity : min;
}

/**
 * Bảng kiểm an toàn. Chữ ký CŨ giữ nguyên (3 tham số) — tham số thứ 4 là tuỳ chọn.
 *
 * VÙNG CẤM: nếu tấm được trả ra từ engine (kiểu EngineSheet) thì nó đã mang sẵn
 * `blocked`, không cần truyền gì thêm. Tham số `blockedBySheet` chỉ dùng khi
 * người gọi muốn kiểm một mảng SheetLayout trần.
 */
export function validateLayout(
  sheets: SheetLayout[], parts: Part[], params: NestParams,
  blockedBySheet?: (Ring[] | undefined)[]
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const byId = new Map(parts.map((p) => [p.id, p]));
  const eps = 1e-6;

  let totalPlaced = 0;
  for (let si = 0; si < sheets.length; si++) {
    const sh = sheets[si];
    totalPlaced += sh.placements.length;
    const rings = sh.placements.map((pl) => {
      const part = byId.get(pl.partId)!;
      return { pl, outer: placedRings(pl, part)[0] };
    });
    // trong tấm trừ lề
    for (const { pl, outer } of rings) {
      const b = ringBBox(outer);
      if (
        b.minX < params.margin - eps || b.minY < params.margin - eps ||
        b.maxX > sh.width - params.margin + eps || b.maxY > sh.height - params.margin + eps
      ) {
        issues.push({
          kind: 'outside',
          a: `${pl.partId}#${pl.instance}`,
          message: `Chi tiết ${pl.partId}#${pl.instance} nằm ngoài vùng tấm trừ lề (bbox ${b.minX.toFixed(1)}..${b.maxX.toFixed(1)} × ${b.minY.toFixed(1)}..${b.maxY.toFixed(1)}).`,
        });
      }
    }
    // KHÔNG ĐÈ LÊN VÙNG CẤM, và cách vùng cấm cũng ≥ khe
    const blocked = (sh as EngineSheet).blocked ?? blockedBySheet?.[si];
    if (blocked && blocked.length) {
      for (const { pl, outer } of rings) {
        const ob = ringBBox(outer);
        for (let k = 0; k < blocked.length; k++) {
          const br = blocked[k];
          if (!br || br.length < 3) continue;
          const bb = ringBBox(br);
          if (
            ob.maxX + params.gap < bb.minX || bb.maxX + params.gap < ob.minX ||
            ob.maxY + params.gap < bb.minY || bb.maxY + params.gap < ob.minY
          ) continue;
          const d = ringDistance(outer, br);
          const na = `${pl.partId}#${pl.instance}`;
          if (d <= eps) {
            issues.push({
              kind: 'blocked', a: na, b: `vùng cấm #${k + 1}`, value: d,
              message: `Chi tiết ${na} đè lên vùng cấm #${k + 1} của tấm ${sh.index + 1}.`,
            });
          } else if (d < params.gap - 1e-6) {
            issues.push({
              kind: 'blocked', a: na, b: `vùng cấm #${k + 1}`, value: d,
              message: `Chi tiết ${na} chỉ cách vùng cấm #${k + 1} ${d.toFixed(2)}mm < khe ${params.gap}mm.`,
            });
          }
        }
      }
    }

    // chồng lấn + khe
    for (let i = 0; i < rings.length; i++) {
      for (let j = i + 1; j < rings.length; j++) {
        const ba = ringBBox(rings[i].outer);
        const bb = ringBBox(rings[j].outer);
        if (
          ba.maxX + params.gap < bb.minX || bb.maxX + params.gap < ba.minX ||
          ba.maxY + params.gap < bb.minY || bb.maxY + params.gap < ba.minY
        ) continue;
        const d = ringDistance(rings[i].outer, rings[j].outer);
        const na = `${rings[i].pl.partId}#${rings[i].pl.instance}`;
        const nb = `${rings[j].pl.partId}#${rings[j].pl.instance}`;
        if (d <= eps) {
          issues.push({ kind: 'overlap', a: na, b: nb, value: d, message: `Chi tiết ${na} và ${nb} chồng lấn nhau.` });
        } else if (d < params.gap - 1e-6) {
          issues.push({ kind: 'gap', a: na, b: nb, value: d, message: `Chi tiết ${na} và ${nb} chỉ cách nhau ${d.toFixed(2)}mm < khe ${params.gap}mm.` });
        }
      }
    }
  }

  const expected = parts.filter((p) => p.enabled).reduce((s, p) => s + Math.max(1, p.qty), 0);
  if (totalPlaced !== expected) {
    issues.push({
      kind: 'missing',
      value: expected - totalPlaced,
      message: `Thiếu chi tiết: đã xếp ${totalPlaced}/${expected}.`,
    });
  }
  return issues;
}
