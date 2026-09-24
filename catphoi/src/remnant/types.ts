/**
 * Kiểu dữ liệu của kho tôn thừa (phôi cũ).
 * Quy ước toạ độ giống hệt src/types.ts: đơn vị MILIMET, y hướng lên,
 * gốc (0,0) ở góc dưới-trái KHUNG BAO của tấm.
 *
 * ── VIỆC 3: tấm thừa giữ NGUYÊN KHỔ, kèm phần đã cắt đi ──────────────────
 * Founder nói nguyên văn: *"tấm thừa nên là hình của thừa có cả phần cắt đi cơ,
 * để dễ biết nó ở chỗ nào mà còn vẽ. bounding vẫn luôn phải là 2000x6000 chuẩn"*.
 *
 * Nên một tấm thừa KHÔNG còn là một mảnh rời lơ lửng nữa, mà là:
 *   • `sheetWidthMm × sheetLengthMm` — KHỔ TẤM GỐC lúc đem đi cắt (2000×6000),
 *     và khung bao `widthMm × lengthMm` LUÔN bằng đúng khổ đó, không co lại;
 *   • `cuts` — các LỖ đã cắt lần trước, đúng vị trí trên tấm gốc.
 * Ra xưởng nhìn vào là biết miếng thừa nằm ở góc nào của tấm mà đặt bản vẽ lên.
 *
 * `polygon` vẫn còn để vẽ và để đọc được dữ liệu cũ: polygon[0] = biên ngoài
 * (với tấm kiểu mới chính là hình chữ nhật nguyên khổ), polygon[1..] = các lỗ.
 */
import type { Point, Ring } from '../types';

/** Một tấm tôn thừa trong kho. */
export interface Remnant {
  id: string;
  /** Tên do người đặt, ví dụ "thừa lô sườn 15". Không bao giờ rỗng. */
  name: string;
  /** Khung bao: bề rộng theo trục x, mm. Tấm kiểu mới = đúng khổ tấm gốc. */
  widthMm: number;
  /** Khung bao: chiều dài theo trục y, mm. Tấm kiểu mới = đúng khổ tấm gốc. */
  lengthMm: number;
  /** KHỔ TẤM GỐC lúc cắt — bề rộng, mm. Mặc định 2000. */
  sheetWidthMm: number;
  /** KHỔ TẤM GỐC lúc cắt — chiều dài, mm. Mặc định 6000. */
  sheetLengthMm: number;
  /**
   * Các lỗ ĐÃ CẮT trên tấm gốc, toạ độ trong hệ của tấm gốc
   * (gốc (0,0) = góc dưới-trái tấm). Tấm nguyên chưa cắt gì thì rỗng.
   */
  cuts: Ring[];
  /**
   * Hình để VẼ: polygon[0] = biên ngoài, polygon[1..] = lỗ.
   * Tấm kiểu mới: polygon[0] là hình chữ nhật nguyên khổ 2000×6000.
   */
  polygon: Ring[];
  note: string;
  status: RemnantStatus;
  /** Epoch milisecond. */
  createdAt: number;
  updatedAt: number;
  /**
   * true = dòng dữ liệu CŨ, lưu trước khi đổi cấu trúc: chỉ có mảnh thừa rời,
   * không biết khổ tấm gốc. Vẫn đọc và xếp được, chỉ là khung bao là khung bao
   * của chính mảnh đó. Panel hiện rõ để thợ biết mà lưu lại cho chuẩn.
   */
  legacy?: boolean;
  /**
   * true = đang nằm trong hàng chờ gửi lên máy chủ (lúc thêm bị mất mạng).
   * Chỉ có ở phía trình duyệt, máy chủ không biết trường này.
   */
  pending?: boolean;
}

export type RemnantStatus = 'available' | 'used';

/** Dữ liệu người dùng nhập khi thêm một tấm thừa. */
export interface RemnantInput {
  name: string;
  widthMm: number;
  lengthMm: number;
  /** Khổ tấm gốc. Không gửi thì máy chủ hiểu bằng widthMm/lengthMm. */
  sheetWidthMm?: number;
  sheetLengthMm?: number;
  /** Lỗ đã cắt trên tấm gốc. */
  cuts?: Ring[];
  polygon: Ring[];
  note?: string;
}

/** Sửa được 3 thứ; kích thước và hình dạng là sự thật vật lý, muốn khác thì thêm tấm mới. */
export interface RemnantPatch {
  name?: string;
  note?: string;
  status?: RemnantStatus;
}

export type { Point, Ring };
