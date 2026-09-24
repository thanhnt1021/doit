/**
 * Kiểu dữ liệu của kho tôn thừa (phôi cũ).
 * Quy ước toạ độ giống hệt src/types.ts: đơn vị MILIMET, y hướng lên,
 * gốc (0,0) ở góc dưới-trái khung bao của tấm thừa.
 */
import type { Point, Ring } from '../types';

/** Một tấm tôn thừa trong kho. */
export interface Remnant {
  id: string;
  /** Tên do người đặt, ví dụ "thừa lô sườn 15". Không bao giờ rỗng. */
  name: string;
  /** Khung bao: bề rộng theo trục x, mm. */
  widthMm: number;
  /** Khung bao: chiều dài theo trục y, mm. */
  lengthMm: number;
  /**
   * Hình dạng THẬT của phần còn lại — không phải hình chữ nhật.
   * polygon[0] = biên ngoài, polygon[1..] = lỗ đã khoét.
   */
  polygon: Ring[];
  note: string;
  status: RemnantStatus;
  /** Epoch milisecond. */
  createdAt: number;
  updatedAt: number;
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
