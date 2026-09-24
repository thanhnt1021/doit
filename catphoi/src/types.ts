/**
 * Hợp đồng kiểu dữ liệu dùng chung cho toàn bộ tool "Xếp phôi tôn".
 * MỌI module (core / nest / ui) đều import từ đây. Không module nào được
 * định nghĩa lại các kiểu này.
 *
 * Quy ước hệ toạ độ:
 *  - Đơn vị nội bộ luôn là MILIMET, trục Y hướng lên (chuẩn DXF/AutoCAD).
 *  - Tấm tôn nằm ở góc phần tư thứ nhất: (0,0) là góc dưới-trái tấm,
 *    x chạy theo BỀ RỘNG tấm (mặc định 2000), y chạy theo CHIỀU DÀI tấm (mặc định 6000).
 */

// ─────────────────────────────── Hình học cơ bản ───────────────────────────────

export interface Point {
  x: number;
  y: number;
}

/**
 * Vòng kín. KHÔNG lặp lại đỉnh đầu ở cuối (ring[0] !== ring[ring.length-1]).
 * Vòng ngoài (outer) luôn CCW (diện tích có dấu > 0).
 * Vòng lỗ (hole) luôn CW (diện tích có dấu < 0).
 */
export type Ring = Point[];

export interface BBox {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

// ─────────────────────────────── Chi tiết (phôi) ───────────────────────────────

export interface Part {
  /** Mã hiển thị: "P0", "P1", ... theo thứ tự xuất hiện trong file. */
  id: string;
  /**
   * rings[0] = biên ngoài (CCW). rings[1..] = lỗ bên trong (CW).
   * Toạ độ ĐÃ normalize: bbox của rings[0] có minX = 0, minY = 0.
   * Đây là HÌNH GỐC (đầy đủ đỉnh), dùng để xuất DXF + G-code.
   */
  rings: Ring[];
  /** Diện tích thực = |outer| - Σ|holes|, đơn vị mm². */
  area: number;
  /** BBox của rings[0] sau normalize (minX = minY = 0). */
  bbox: BBox;
  /** Tổng số đỉnh của mọi vòng (dùng để hiển thị). */
  vertexCount: number;
  /** Bề rộng nhỏ nhất khi xoay (rotating calipers trên convex hull), mm. */
  minWidth: number;
  /**
   * Cạnh DÀI của khung bao nhỏ nhất khi xoay (minAreaRect trên bao lồi), mm.
   * Đi cặp với minWidth ở trên: minWidth × maxLength chính là khung bao nhỏ nhất đó.
   * KHÔNG phải đường kính bao lồi, cũng không phải cạnh của bbox theo trục toạ độ.
   */
  maxLength: number;
  /** Số lượng cần cắt. Mặc định 1, người dùng sửa được trên UI. */
  qty: number;
  /** Có đưa vào xếp hay không. Mặc định true. */
  enabled: boolean;
  /** false nếu chi tiết không thể nhét vừa tấm dù xoay kiểu gì. */
  fitsSheet: boolean;
}

export interface ParseStats {
  /** Đếm entity theo loại trong model space, ví dụ { LWPOLYLINE: 15, MTEXT: 43 }. */
  entityCounts: Record<string, number>;
  /** Số vòng kín tìm được (kể cả lỗ). */
  closedRings: number;
  /** Số chuỗi hở bị loại. */
  openDropped: number;
  /** Số vòng được nhận là lỗ (nằm trong vòng khác). */
  holes: number;
  /** Thời gian parse, ms. */
  ms: number;
}

export interface ParseResult {
  parts: Part[];
  stats: ParseStats;
  /** Cảnh báo tiếng Việt có dấu để hiện lên UI. */
  warnings: string[];
}

export interface ParseOptions {
  /** Hệ số nhân để quy về mm. mm=1, cm=10, m=1000. Mặc định 1. */
  unitScale?: number;
  /** Dung sai ghép chuỗi LINE/ARC thành vòng kín, mm. Mặc định 0.1. */
  chainTol?: number;
  /** Bề rộng tấm (mm) để đánh dấu fitsSheet. Mặc định 2000. */
  sheetWidth?: number;
  /** Chiều dài tấm (mm) để đánh dấu fitsSheet. Mặc định 6000. */
  sheetHeight?: number;
  /** Callback tiến độ 0..1 (dùng trong Web Worker). */
  onProgress?: (fraction: number, label: string) => void;
}

// ─────────────────────────────── Nesting ───────────────────────────────

export interface NestParams {
  /** Bề rộng tấm, mm. Mặc định 2000. */
  sheetW: number;
  /** Chiều dài tấm, mm. Mặc định 6000. */
  sheetH: number;
  /** Khe hở tối thiểu giữa 2 chi tiết, mm. Mặc định 10. */
  gap: number;
  /** Lề mép tấm, mm. Mặc định 10. */
  margin: number;
  /** Bước xoay, độ. Mặc định 5. Tập góc = 0, step, 2*step, ... < 360. */
  rotationStep: number;
  /** Cho phép lật gương. Mặc định false. */
  allowMirror: boolean;
  /** Giới hạn thời gian, ms. Mặc định 60000. */
  timeLimitMs: number;
  /** Cạnh ô lưới raster, mm. Mặc định 5. Nhỏ hơn = chính xác hơn nhưng chậm hơn. */
  gridCell?: number;
  /** Seed cho bộ sinh ngẫu nhiên, để test tái lập được. Mặc định 12345. */
  seed?: number;
}

export const DEFAULT_NEST_PARAMS: NestParams = {
  sheetW: 2000,
  sheetH: 6000,
  gap: 10,
  margin: 10,
  rotationStep: 5,
  allowMirror: false,
  timeLimitMs: 60_000,
  gridCell: 5,
  seed: 12345,
};

/**
 * Một lần đặt chi tiết lên tấm.
 * Phép biến hình áp lên TỪNG ĐIỂM p của Part.rings, theo đúng thứ tự:
 *   1. lật gương (nếu mirrored): p.x -> -p.x
 *   2. xoay quanh gốc toạ độ (0,0) một góc rotationDeg (ngược chiều kim đồng hồ)
 *   3. tịnh tiến: + (x, y)
 * Xem hàm applyPlacement() ở cuối file — MỌI module phải dùng hàm này.
 */
export interface Placement {
  /** Part.id */
  partId: string;
  /** Chỉ số bản sao (0..qty-1) của chi tiết đó. */
  instance: number;
  /** Góc xoay, độ, ngược chiều kim đồng hồ. */
  rotationDeg: number;
  mirrored: boolean;
  /** Tịnh tiến sau khi xoay, mm, trong hệ toạ độ tấm. */
  x: number;
  y: number;
}

export interface SheetLayout {
  /** 0-based. */
  index: number;
  width: number;
  height: number;
  placements: Placement[];
  /** Tổng diện tích chi tiết trên tấm này, mm². */
  usedArea: number;
  /** usedArea / (width*height), 0..1. */
  utilization: number;
}

export interface NestResult {
  sheets: SheetLayout[];
  /** Danh sách "partId#instance" không xếp được (ví dụ to hơn tấm). */
  unplaced: string[];
  /** Tổng % sử dụng tôn trên toàn bộ số tấm đã dùng, 0..1. */
  utilization: number;
  elapsedMs: number;
  /** Số phương án đã thử. */
  iterations: number;
  params: NestParams;
}

export interface NestProgress {
  /** 0..1 theo thời gian. */
  fraction: number;
  elapsedMs: number;
  iterations: number;
  /** Phương án tốt nhất hiện tại (có thể chưa đủ chi tiết ở vòng đầu). */
  best: NestResult | null;
  /** Nhãn tiếng Việt để hiện lên UI. */
  label: string;
}

/** Đầu vào của engine: danh sách chi tiết đã nhân theo số lượng do engine tự lo. */
export interface NestInput {
  parts: Part[];
  params: NestParams;
}

// ─────────────────────────────── Xuất file ───────────────────────────────

export interface GcodeOptions {
  /** Mã bật mỏ cắt. Mặc định "M07". */
  torchOn: string;
  /** Mã tắt mỏ cắt. Mặc định "M08". */
  torchOff: string;
  /** Tốc độ cắt, mm/phút. Mặc định 1500. */
  feedRate: number;
  /** Chiều dài lead-in thẳng, mm. Mặc định 5. 0 = tắt. */
  leadIn: number;
  /** Có đánh số dòng N hay không. Mặc định false. */
  lineNumbers: boolean;
  /** Đuôi file: "nc" | "txt" | "cnc". Mặc định "nc". */
  extension: 'nc' | 'txt' | 'cnc';
  /** Số chữ số thập phân. Mặc định 2. */
  decimals: number;
}

export const DEFAULT_GCODE_OPTIONS: GcodeOptions = {
  torchOn: 'M07',
  torchOff: 'M08',
  feedRate: 1500,
  leadIn: 5,
  lineNumbers: false,
  extension: 'nc',
  decimals: 2,
};

export interface ExportContext {
  /** Tra cứu Part theo id (engine chỉ trả về id). */
  partsById: Map<string, Part>;
}

// ─────────────────────────────── Hàm dùng chung ───────────────────────────────

/** Áp phép biến hình của một Placement lên 1 điểm của hình gốc. */
export function applyPlacement(p: Point, pl: Placement): Point {
  const sx = pl.mirrored ? -p.x : p.x;
  const sy = p.y;
  const a = (pl.rotationDeg * Math.PI) / 180;
  const c = Math.cos(a);
  const s = Math.sin(a);
  return { x: sx * c - sy * s + pl.x, y: sx * s + sy * c + pl.y };
}

/** Áp phép biến hình lên cả một vòng. */
export function applyPlacementRing(ring: Ring, pl: Placement): Ring {
  return ring.map((p) => applyPlacement(p, pl));
}

/** Diện tích có dấu (CCW > 0). */
export function signedArea(ring: Ring): number {
  let a = 0;
  const n = ring.length;
  for (let i = 0; i < n; i++) {
    const p1 = ring[i];
    const p2 = ring[(i + 1) % n];
    a += p1.x * p2.y - p2.x * p1.y;
  }
  return a / 2;
}

export function ringBBox(ring: Ring): BBox {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of ring) {
    if (p.x < minX) minX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.x > maxX) maxX = p.x;
    if (p.y > maxY) maxY = p.y;
  }
  return { minX, minY, maxX, maxY };
}

export function bboxOfRings(rings: Ring[]): BBox {
  let b: BBox = { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };
  for (const r of rings) {
    const rb = ringBBox(r);
    b = {
      minX: Math.min(b.minX, rb.minX),
      minY: Math.min(b.minY, rb.minY),
      maxX: Math.max(b.maxX, rb.maxX),
      maxY: Math.max(b.maxY, rb.maxY),
    };
  }
  return b;
}
