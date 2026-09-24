/**
 * Hàm dùng chung cho API kho tôn thừa (Cloudflare Pages Functions).
 *
 * Kho là dữ liệu CHUNG, nhiều máy trong xưởng cùng ghi → mọi thứ client gửi lên
 * đều bị coi là không đáng tin: phải kiểm tra sạch sẽ ở đây trước khi chạm D1.
 * Mọi câu SQL đều dùng prepared statement + bind, TUYỆT ĐỐI không nối chuỗi.
 *
 * File bắt đầu bằng "_" nên Pages không coi là route.
 */

/** Chặn payload quá lớn: 128 KB là thừa sức cho một đa giác tôn thừa. */
export const MAX_BODY_BYTES = 128 * 1024;

export const MAX_NAME_LEN = 120;
export const MAX_NOTE_LEN = 500;
/** Tấm tôn to nhất trên đời cũng không tới 100 mét. */
export const MAX_DIM_MM = 100_000;
export const MAX_RINGS = 50;
export const MAX_POINTS_TOTAL = 5_000;
export const MIN_RING_POINTS = 3;

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400',
};

export function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...CORS },
  });
}

/** Lỗi trả về luôn kèm câu tiếng Việt có dấu để panel hiện thẳng cho thợ. */
export function fail(message, status = 400) {
  return json({ ok: false, error: message }, status);
}

export function preflight() {
  return new Response(null, { status: 204, headers: CORS });
}

export function noDb(env) {
  return !env || !env.DB ? fail('Máy chủ chưa gắn kho dữ liệu D1 (binding DB).', 500) : null;
}

/** Đọc body JSON có chặn kích thước. Trả { data } hoặc { error }. */
export async function readJsonBody(request) {
  const declared = Number(request.headers.get('content-length') || '0');
  if (declared > MAX_BODY_BYTES) {
    return { error: `Dữ liệu gửi lên quá lớn (tối đa ${Math.floor(MAX_BODY_BYTES / 1024)} KB).` };
  }
  let text;
  try {
    text = await request.text();
  } catch {
    return { error: 'Không đọc được dữ liệu gửi lên.' };
  }
  // Content-Length có thể bịa hoặc thiếu → đo lại độ dài thật.
  if (new TextEncoder().encode(text).length > MAX_BODY_BYTES) {
    return { error: `Dữ liệu gửi lên quá lớn (tối đa ${Math.floor(MAX_BODY_BYTES / 1024)} KB).` };
  }
  if (!text.trim()) return { error: 'Thiếu nội dung gửi lên.' };
  try {
    const data = JSON.parse(text);
    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      return { error: 'Nội dung gửi lên phải là một đối tượng JSON.' };
    }
    return { data };
  } catch {
    return { error: 'Nội dung gửi lên không phải JSON hợp lệ.' };
  }
}

function isFiniteNumber(v) {
  return typeof v === 'number' && Number.isFinite(v);
}

/** Kiểm tra tên: bắt buộc, không rỗng sau khi bỏ khoảng trắng. */
export function checkName(v) {
  if (typeof v !== 'string') return { error: 'Tên tấm thừa phải là chuỗi chữ.' };
  const name = v.trim();
  if (!name) return { error: 'Phải đặt tên cho tấm thừa, ví dụ "thừa lô sườn 15".' };
  if (name.length > MAX_NAME_LEN) return { error: `Tên tấm thừa dài quá ${MAX_NAME_LEN} ký tự.` };
  return { value: name };
}

export function checkNote(v) {
  if (v === undefined || v === null) return { value: '' };
  if (typeof v !== 'string') return { error: 'Ghi chú phải là chuỗi chữ.' };
  const note = v.trim();
  if (note.length > MAX_NOTE_LEN) return { error: `Ghi chú dài quá ${MAX_NOTE_LEN} ký tự.` };
  return { value: note };
}

export function checkDim(v, label) {
  if (!isFiniteNumber(v)) return { error: `${label} phải là một con số.` };
  if (v <= 0) return { error: `${label} phải lớn hơn 0.` };
  if (v > MAX_DIM_MM) return { error: `${label} lớn quá mức cho phép (${MAX_DIM_MM} mm).` };
  return { value: v };
}

export function checkStatus(v) {
  if (v !== 'available' && v !== 'used') {
    return { error: 'Trạng thái chỉ được là "available" (còn) hoặc "used" (đã dùng).' };
  }
  return { value: v };
}

/**
 * Kiểm tra hình dạng thật của tấm thừa.
 * Chấp nhận 2 dạng cho tiện client: một vòng [{x,y},...] hoặc nhiều vòng [[{x,y},...],...].
 * Luôn chuẩn hoá về dạng NHIỀU VÒNG; vòng[0] là biên ngoài, còn lại là lỗ.
 */
export function checkPolygon(v) {
  if (!Array.isArray(v) || v.length === 0) {
    return { error: 'Thiếu hình dạng tấm thừa (đa giác).' };
  }
  const rings = Array.isArray(v[0]) ? v : [v];
  if (rings.length > MAX_RINGS) return { error: `Hình tấm thừa có quá ${MAX_RINGS} vòng.` };
  let total = 0;
  const out = [];
  for (const ring of rings) {
    if (!Array.isArray(ring) || ring.length < MIN_RING_POINTS) {
      return { error: `Mỗi vòng của hình tấm thừa cần ít nhất ${MIN_RING_POINTS} đỉnh.` };
    }
    total += ring.length;
    if (total > MAX_POINTS_TOTAL) {
      return { error: `Hình tấm thừa có quá ${MAX_POINTS_TOTAL} đỉnh, hãy đơn giản hoá bớt.` };
    }
    const pts = [];
    for (const p of ring) {
      if (!p || typeof p !== 'object' || !isFiniteNumber(p.x) || !isFiniteNumber(p.y)) {
        return { error: 'Đỉnh của hình tấm thừa phải có toạ độ x, y là số.' };
      }
      if (Math.abs(p.x) > MAX_DIM_MM || Math.abs(p.y) > MAX_DIM_MM) {
        return { error: `Toạ độ đỉnh vượt quá ${MAX_DIM_MM} mm.` };
      }
      pts.push({ x: p.x, y: p.y });
    }
    out.push(pts);
  }
  return { value: out };
}

/** Đổi một dòng D1 thành đối tượng gửi cho trình duyệt (camelCase). */
export function rowToRemnant(row) {
  let polygon = [];
  try {
    const parsed = JSON.parse(row.polygon);
    if (Array.isArray(parsed)) polygon = parsed;
  } catch {
    // Dòng hỏng (sửa tay trên D1?) — trả đa giác rỗng còn hơn làm sập cả danh sách.
    polygon = [];
  }
  return {
    id: row.id,
    name: row.name,
    widthMm: row.width_mm,
    lengthMm: row.length_mm,
    polygon,
    note: row.note || '',
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export const SELECT_COLS =
  'id, name, width_mm, length_mm, polygon, note, status, created_at, updated_at';
