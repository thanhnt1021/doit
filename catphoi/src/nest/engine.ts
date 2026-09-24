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
 * Đổi lại, kiểu đặt này không "chui" xuống dưới phần nhô ra của chi tiết khác.
 * Đó đúng là cách đặt vật lý (thả từ trên xuống / đẩy từ phải sang) và vẫn LỒNG
 * được thanh cong vào nhau, vì đường bao colTop/rowMax thay đổi theo từng cột /
 * từng hàng: thanh sau tự ôm theo chỗ lõm của thanh trước.
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
/** Bao nhiêu phương án liên tiếp không tiến bộ thì gieo lại quần thể. */
const STALL_LIMIT = 200;
/**
 * Trần số lần dò va chạm cho MỘT lần tìm chỗ ở pha vét cạn. Không có trần thì
 * một lần tìm chỗ trên dải dài có thể chạy hàng phút (đo thật: ngân sách 60
 * giây chạy mất 703 giây). Hạn thời gian được canh thêm ở mức giữa các góc xoay
 * nên phần vượt giờ tối đa bằng ĐÚNG một lần tìm chỗ.
 */
const EXACT_PROBES = 400_000;

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
  /** Bước nhảy theo trục y khi sinh ứng viên trượt ngang (ô). */
  readonly yStride: number;
  private cache = new Map<string, BaseBitmap | null>();
  private cacheBytes = 0;
  /** Bộ nhớ tạm dùng lại cho dropY/dropX — tránh cấp phát trong vòng lặp nóng. */
  private scratch = new Int32Array(2);
  private candPx = new Int32Array(TOP_K);
  private candPy = new Int32Array(TOP_K);
  private candKey = new Float64Array(TOP_K);

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
    // Bước nhảy khi quét vét cạn theo y: 15mm. Bỏ sót một vị trí y hẹp chỉ làm
    // chi tiết lệch vài ô chứ không sai kết quả, mà rẻ hơn 3 lần so với quét từng ô.
    this.yStride = Math.max(1, Math.round(15 / this.cell));
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
    return { bits, rowMax, colTop, rowLo, rowHi, blockTop: rowHi + 1, cells };
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
    this.cacheBytes += bm.bits.byteLength + bm.colLow.byteLength * 2 + bm.rowLowBit.byteLength * 4;
    while (this.cacheBytes > 64 * 1024 * 1024 && this.cache.size > 8) {
      const it = this.cache.keys().next();
      if (it.done) break;
      const old = this.cache.get(it.value);
      if (old) this.cacheBytes -= old.bits.byteLength + old.colLow.byteLength * 2 + old.rowLowBit.byteLength * 4;
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
    for (let c = 0; c < bm.w; c++) {
      const ch = bm.colHigh[c];
      if (ch < 0) continue;
      const t = py + ch;
      if (t > sh.colTop[px + c]) sh.colTop[px + c] = t;
    }
    if (py + bm.h > sh.maxRow) sh.maxRow = py + bm.h;
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





  /**
   * Lọc RẺ: trả true khi CHẮC CHẮN không chồng lấn — mọi cột của chi tiết đều
   * nằm trọn dưới hoặc trọn trên dải đã bị chiếm của cột tấm tương ứng.
   * Trả false thì chưa kết luận được, phải gọi collides(). Một lần lọc tốn
   * O(bề rộng) thay vì O(chiều cao × số word) của phép dò va chạm đầy đủ.
   */
  freeQuick(sh: SheetGrid, bm: BaseBitmap, px: number, py: number): boolean {
    const colTop = sh.colTop;
    const colLow = bm.colLow;
    const colHigh = bm.colHigh;
    const n = bm.w;
    for (let c = 0; c < n; c++) {
      const lo = colLow[c];
      if (lo < 0) continue;
      const ct = colTop[px + c];
      if (ct < 0) continue;
      if (py + lo <= ct) return false; // có thể đụng phần đã chiếm của cột này
    }
    return true;
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
    for (let i = 0; i < K; i++) {
      kx[i] = -1;
      kk[i] = Infinity;
    }
    const push = (base: number, px: number, py: number, key: number): void => {
      if (key >= kk[base + K - 1]) return;
      let i = base + K - 1;
      while (i > base && kk[i - 1] > key) {
        kk[i] = kk[i - 1];
        kx[i] = kx[i - 1];
        ky[i] = ky[i - 1];
        i--;
      }
      kk[i] = key;
      kx[i] = px;
      ky[i] = py;
    };

    const out = this.scratch;
    const empty = sh.rowLo < 0;

    // A) thả rơi từ trên xuống, thử mọi cột
    for (let px = 0; px <= maxPx; px++) {
      this.dropY(sh, bm, px, out);
      const py = out[0];
      if (py > maxPy) continue;
      const newTop = py + bm.h > sh.maxRow ? py + bm.h : sh.maxRow;
      push(0, px, py, this.keyOf(rule, px, py, newTop, out[1]));
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
        push(0, px, py, this.keyOf(rule, px, py, newTop, this.voidAt(sh, bm, px, py)));
      }
    }

    // E) QUÉT VÉT CẠN theo cột — chỉ bật ở pha tinh chỉnh.
    // Thả rơi chỉ với tới MẶT TRÊN của thứ đã xếp; chỗ trống nằm lọt dưới bụng
    // thanh cong thì phải dò va chạm thật mới thấy, mà đó đúng là phần tôn phí
    // lớn nhất (đo trên file mẫu: bản chỉ-thả-rơi dừng ở dải 13,2m, có vét cạn
    // xuống 12,2m).
    //
    // BẮT BUỘC CÓ TRẦN CÔNG VIỆC. Một lần dò va chạm của thanh sườn dài tốn cỡ
    // 10^4 phép tính; quét hết mọi cột × mọi hàng là 10^10 — đo thật: ngân sách
    // 60 giây chạy mất 703 giây. Nên ở đây: quét cột từ trái sang, mỗi cột chỉ
    // lấy vài mẫu theo y, dừng khi đã đủ EXACT_SPOTS chỗ hoặc hết trần dò.
    if (exact) {
      const stride = this.yStride;
      let budget = EXACT_PROBES;
      for (let px = 0; px <= maxPx && budget > 0; px++) {
        // Tự canh giờ ngay trong vòng quét: cứ 128 lần dò lại hỏi đã hết hạn chưa.
        // Nhờ vậy KHÔNG cần chặn chất lượng bằng một trần cứng — hết giờ thì bỏ
        // dở phần quét, phần đã quét vẫn dùng được, và mức vượt giờ tối đa chỉ
        // bằng 128 lần dò (cỡ vài mili-giây).
        if ((px & 15) === 0 && abort?.()) break;
        const land = this.dropYOnly(sh, bm, px);
        if (land > maxPy || land <= 0) continue;
        let found = -1;
        for (let py = 0; py < land && budget > 0; py += stride) {
          if (this.freeQuick(sh, bm, px, py)) {
            found = py;
            break;
          }
          budget--;
          if (!this.collides(sh, bm, px, py)) {
            found = py;
            break;
          }
        }
        if (found < 0) continue;
        // ép xuống từng ô cho khít, trong phạm vi một bước quét
        for (let k = 0; k < stride && found > 0 && budget > 0; k++) {
          budget--;
          if (this.collides(sh, bm, px, found - 1)) break;
          found--;
        }
        const newTop = found + bm.h > sh.maxRow ? found + bm.h : sh.maxRow;
        push(0, px, found, this.keyOf(rule, px, found, newTop, this.voidAt(sh, bm, px, found)));
      }
    }

    let bestKey = Infinity;
    let bestPx = -1;
    let bestPy = 0;
    for (let i = 0; i < K; i++) {
      if (kx[i] < 0) continue;
      if (kk[i] < bestKey) {
        bestKey = kk[i];
        bestPx = kx[i];
        bestPy = ky[i];
      }
      this.settle(sh, bm, kx[i], ky[i], maxPx, out);
      const px = out[0];
      const py = out[1];
      if (py > maxPy || px > maxPx || px < 0 || py < 0) continue;
      const v = this.voidAt(sh, bm, px, py);
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

/** Dựng danh sách góc hợp lệ cho 1 chi tiết. */
function buildAngles(simple: Ring, nester: Nester, params: NestParams): AngleOpt[] {
  const step = Math.max(1, params.rotationStep || 5);
  const mirrors = params.allowMirror ? [false, true] : [false];
  const out: AngleOpt[] = [];
  for (const mirrored of mirrors) {
    for (let deg = 0; deg < 360; deg += step) {
      const ring = transformRing(simple, deg, mirrored);
      const b = ringBBox(ring);
      const bw = b.maxX - b.minX;
      const bh = b.maxY - b.minY;
      const w = bw + 2 * nester.dil * nester.cell;
      const h = bh + 2 * nester.dil * nester.cell;
      if (w > nester.gw * nester.cell || h > nester.gh * nester.cell) continue;
      out.push({ deg, mirrored, bboxArea: bw * bh, bboxH: bh, bboxW: bw });
    }
  }
  out.sort((a, b) => a.bboxArea - b.bboxArea);
  return out;
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
  const rng = mulberry32(params.seed ?? 12345);

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
    const angles = buildAngles(simple, nester, params);
    if (angles.length === 0) {
      for (let i = 0; i < Math.max(1, p.qty); i++) unplacedFixed.push(`${p.id}#${i}`);
      continue;
    }
    const idx = angles.map((_, i) => i);
    const byH = idx.slice().sort((a, b) => angles[a].bboxH - angles[b].bboxH);
    const byW = idx.slice().sort((a, b) => angles[a].bboxW - angles[b].bboxW);
    const byDeg = new Int32Array(nSteps).fill(-1);
    angles.forEach((a, i) => {
      if (!a.mirrored) byDeg[Math.round(a.deg / angStep) % nSteps] = i;
    });
    preps.push({ part: p, simple, angles, byH, byW, byDeg });
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
  const ANGLE_TRIES = 9;
  const ANGLE_TRIES_EXACT = 9;
  const wantBuf: number[] = [];
  const seenBuf = new Set<number>();
  /**
   * `prevDeg` là góc của chi tiết vừa đặt xong. Bộ sườn tàu là một họ đường
   * cong gần giống nhau, muốn LỒNG ĐỒNG TÂM thì thanh sau phải xoay gần đúng
   * bằng thanh trước (hoặc úp ngược 180°) — nên hai góc đó luôn được thử.
   */
  const angleCandsOf = (prep: PartPrep, gene: number, prevDeg: number, tries: number): AngleOpt[] => {
    const n = prep.angles.length;
    wantBuf.length = 0;
    if (prevDeg >= 0) {
      const k = Math.round(prevDeg / angStep) % nSteps;
      wantBuf.push(prep.byDeg[k]);
      wantBuf.push(prep.byDeg[(k + Math.round(nSteps / 2)) % nSteps]);
      wantBuf.push(prep.byDeg[(k + 1) % nSteps]);
      wantBuf.push(prep.byDeg[(k + nSteps - 1) % nSteps]);
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
  const evaluate = (g: Genome, exact = false): Evaluated => {
    const sheets: SheetGrid[] = [makeSheet(0)];
    const sheetOf = new Int32Array(nInst).fill(-1);
    const unplaced: string[] = [];
    let placedArea = 0;
    let prevDeg = -1;
    for (const ii of g.order) {
      const inst = insts[ii];
      const prep = preps[inst.prepIndex];
      // Ở pha vét cạn mỗi góc đắt gấp cả trăm lần, nên thử ít góc hơn để một
      // lần đánh giá CHẠY XONG trong hạn — đánh giá dở dang thì vứt đi, phí sạch.
      const cands = angleCandsOf(prep, g.angleIdx[ii], prevDeg, exact ? ANGLE_TRIES_EXACT : ANGLE_TRIES);
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
    const lastArea = used.length ? used[used.length - 1].usedArea : 0;
    const lastTop = used.length ? used[used.length - 1].maxRow * used[used.length - 1].nester.cell : 0;
    const sumTop = used.reduce((a, s) => a + s.maxRow * s.nester.cell, 0);
    const cost =
      (used.length + unplaced.length * 10) * BIG +
      (lastArea / 1e6) * 1e7 +
      lastTop * 1e3 +
      sumTop;
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
  const switchAt = t0 + Math.max(200, params.timeLimitMs) * 0.65;
  let exact = false;
  /**
   * Hạn cho vòng tìm kiếm — để DÀNH LẠI một quỹ nhỏ cho bước dọn tấm cuối ở
   * cuối hàm. Không dành thì vòng GA ăn hết giờ và bước dọn không chạy được ô nào.
   */
  const sweepBudget = Math.min(4000, Math.max(200, params.timeLimitMs) * 0.12);
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

  const pop: Evaluated[] = [];
  /** Số phương án liên tiếp không cải thiện — để biết khi nào GA đã bế tắc. */
  let sinceImprove = 0;
  const consider = (e: Evaluated) => {
    iterations++;
    opts.onCandidate?.(snapOf(e));
    pop.push(e);
    if (!best || e.cost < best.cost) {
      best = e;
      sinceImprove = 0;
    } else sinceImprove++;
    if (now() - lastReport > 250) {
      lastReport = now();
      report(iterations <= seeds.length ? 'Đang thử phương án khởi đầu…' : 'Đang tối ưu…');
    }
  };

  for (const g of seeds) {
    if (now() > workDeadline || cb.shouldStop?.()) break;
    consider(evaluate(g));
  }
  if (!best) {
    best = evaluate(seeds[0]);
    iterations++;
    pop.push(best);
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

  while (now() < workDeadline && !cb.shouldStop?.()) {
    if (!exact && now() >= switchAt) {
      exact = true;
      sinceImprove = 0;
      pop.sort((x, y) => x.cost - y.cost);
      const elite = pop.slice(0, 4).map((e) => e.genome);
      pop.length = 0;
      for (const g of elite) {
        if (now() >= workDeadline || cb.shouldStop?.()) break;
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
        if (now() >= workDeadline || cb.shouldStop?.()) break;
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
        if (now() >= workDeadline || cb.shouldStop?.()) break;
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
  }

  /**
   * HẬU XỬ LÝ — DỌN TẤM CUỐI.
   * Mục tiêu của đề bài là ÍT TẤM NHẤT, nên việc đáng giá nhất sau khi tìm kiếm
   * là thử nhấc từng chi tiết đang nằm ở tấm cuối sang các tấm trước, quét TOÀN
   * BỘ góc xoay chứ không chỉ vài góc như trong vòng lặp GA. Nếu dọn sạch được
   * thì bớt hẳn một tấm; nếu không thì tấm cuối cũng nhẹ đi, phần tôn thừa còn
   * nguyên khổ hơn. Chỉ THÊM chi tiết vào tấm trước nên không phá ràng buộc nào.
   */
  const sweepLastSheet = (e: Evaluated): boolean => {
    if (e.grids.length < 2) return false;
    const last = e.grids[e.grids.length - 1];
    if (last.placements.length === 0 || last.placements.length > 4) return false;
    const byPartId = new Map<string, number>();
    preps.forEach((pp, i) => byPartId.set(pp.part.id, i));
    let movedAny = false;
    for (const pl of last.placements.slice()) {
      if (now() > deadline || cb.shouldStop?.()) break;
      const pi = byPartId.get(pl.partId);
      if (pi === undefined) continue;
      const prep = preps[pi];
      const inst: Inst = { prepIndex: pi, instance: pl.instance, area: prep.part.area };
      let moved = false;
      // Vòng 1: quét TOÀN BỘ góc bằng phép đặt nhanh (mỗi góc cỡ 1ms).
      for (let sIdx = 0; sIdx < e.grids.length - 1 && !moved; sIdx++) {
        if (e.grids[sIdx].nester.place(e.grids[sIdx], prep, inst, prep.angles, e.genome.rule, false, abort)) moved = true;
      }
      // Vòng 2: nếu vẫn không lọt thì mới trả giá vét cạn, và chỉ với những góc
      // có bbox nhỏ nhất — vét cạn đắt gấp trăm lần nên không quét hết 72 góc.
      if (!moved) {
        const few = prep.angles.slice(0, 12);
        for (let sIdx = 0; sIdx < e.grids.length - 1 && !moved; sIdx++) {
          if (now() > deadline || cb.shouldStop?.()) break;
          if (e.grids[sIdx].nester.place(e.grids[sIdx], prep, inst, few, e.genome.rule, true, abort)) moved = true;
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
    return true;
  };
  workDeadline = deadline;
  if (best && !cb.shouldStop?.()) sweepLastSheet(best);

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
