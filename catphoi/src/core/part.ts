/**
 * MỞ RỘNG KIỂU `Part` — thêm trường `dxfLabel`.
 *
 * Vì sao khai ở đây mà không sửa thẳng `src/types.ts`: phần giao diện và kho
 * tôn thừa đang được người khác sửa cùng lúc, `src/types.ts` nằm ngoài phạm vi
 * ghi của việc này. TypeScript cho phép "module augmentation" — khai thêm
 * trường cho một interface đã có ở module khác — nên kết quả giống hệt như đã
 * sửa trực tiếp: mọi nơi import `Part` đều thấy `dxfLabel`.
 *
 * `dxfLabel` = tên mã phôi đọc được từ chữ trong file DXF (xem dxf-label.ts).
 * Chuỗi rỗng / không có = bản vẽ không ghi tên cho chi tiết đó.
 */
declare module '../types' {
  interface Part {
    /** Tên mã phôi đọc từ chữ trong DXF, ví dụ "mạn 15 · Nối · Chân". '' nếu không có. */
    dxfLabel?: string;
  }
}

export {};
