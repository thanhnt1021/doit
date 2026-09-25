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

/**
 * VIỆC 2 — mã/tên tấm thừa CŨ đã sinh ra tấm này. Không gửi = không biết nguồn.
 * Chỉ là chữ để tra cứu, KHÔNG phải khoá ngoại: tấm mẹ có bị xoá thì dòng con
 * vẫn phải đọc được, chứ không được mất luôn tấm thừa đang nằm ngoài xưởng.
 */
export function checkSourceRef(v, label, maxLen) {
  if (v === undefined || v === null || v === '') return { value: null };
  if (typeof v !== 'string') return { error: `${label} phải là chuỗi chữ.` };
  const s = v.trim();
  if (!s) return { value: null };
  if (s.length > maxLen) return { error: `${label} dài quá ${maxLen} ký tự.` };
  return { value: s };
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

/**
 * Các LỖ ĐÃ CẮT trên tấm gốc (VIỆC 3). Cùng luật với đa giác.
 * Không gửi / gửi rỗng đều hợp lệ (tấm nguyên chưa cắt gì).
 */
export function checkCuts(v) {
  if (v === undefined || v === null) return { value: [] };
  if (!Array.isArray(v)) return { error: 'Danh sách lỗ đã cắt phải là một mảng.' };
  if (v.length === 0) return { value: [] };
  if (v.length > MAX_RINGS) return { error: `Tấm thừa có quá ${MAX_RINGS} lỗ đã cắt.` };
  let total = 0;
  const out = [];
  for (const ring of v) {
    if (!Array.isArray(ring) || ring.length < MIN_RING_POINTS) {
      return { error: `Mỗi lỗ đã cắt cần ít nhất ${MIN_RING_POINTS} đỉnh.` };
    }
    total += ring.length;
    if (total > MAX_POINTS_TOTAL) {
      return { error: `Các lỗ đã cắt có quá ${MAX_POINTS_TOTAL} đỉnh, hãy đơn giản hoá bớt.` };
    }
    const pts = [];
    for (const p of ring) {
      if (!p || typeof p !== 'object' || !isFiniteNumber(p.x) || !isFiniteNumber(p.y)) {
        return { error: 'Đỉnh của lỗ đã cắt phải có toạ độ x, y là số.' };
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

function parseJsonRings(text) {
  try {
    const v = JSON.parse(text);
    return Array.isArray(v) ? v : [];
  } catch {
    // Dòng hỏng (sửa tay trên D1?) — trả rỗng còn hơn làm sập cả danh sách.
    return [];
  }
}

/**
 * Đổi một dòng D1 thành đối tượng gửi cho trình duyệt (camelCase).
 *
 * ── DỮ LIỆU CŨ TRONG KHO PRODUCTION (VIỆC 3) ─────────────────────────────
 * Cột sheet_w_mm / sheet_h_mm / cuts mới thêm nên các dòng lưu TRƯỚC khi đổi
 * cấu trúc đang để NULL. Không xoá, không sửa dữ liệu cũ. Khi đọc:
 *   • sheet_w_mm NULL → lấy tạm width_mm/length_mm làm khổ (không bịa 2000×6000,
 *     bịa là sai vị trí), cuts lấy từ polygon[1..], và gắn cờ legacy = true;
 *   • sheet_w_mm có giá trị → tấm kiểu mới, khung bao LUÔN bằng khổ tấm gốc.
 * Trình duyệt còn chuẩn hoá thêm một lần ở src/remnant/normalize.ts.
 */
export function rowToRemnant(row) {
  const polygon = parseJsonRings(row.polygon);
  const hasStock = isFiniteNumber(row.sheet_w_mm) && isFiniteNumber(row.sheet_h_mm)
    && row.sheet_w_mm > 0 && row.sheet_h_mm > 0;
  const cutsCol = row.cuts ? parseJsonRings(row.cuts) : null;
  const cuts = cutsCol && cutsCol.length ? cutsCol : polygon.slice(1);
  const sheetW = hasStock ? row.sheet_w_mm : row.width_mm;
  const sheetH = hasStock ? row.sheet_h_mm : row.length_mm;

  const out = {
    id: row.id,
    name: row.name,
    widthMm: hasStock ? sheetW : row.width_mm,
    lengthMm: hasStock ? sheetH : row.length_mm,
    sheetWidthMm: sheetW,
    sheetLengthMm: sheetH,
    cuts,
    polygon,
    note: row.note || '',
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
  if (!hasStock) out.legacy = true;
  // VIỆC 2 — nguồn gốc. Cột có thể chưa tồn tại (chưa chạy migration) → undefined.
  if (row.source_id) out.sourceId = row.source_id;
  if (row.source_name) out.sourceName = row.source_name;
  return out;
}

/** Bộ cột CŨ — không có source_id/source_name. Dùng làm đường lui. */
export const SELECT_COLS_LEGACY =
  'id, name, width_mm, length_mm, sheet_w_mm, sheet_h_mm, cuts, polygon, note, status, created_at, updated_at';

/** Bộ cột ĐẦY ĐỦ, có nguồn gốc (VIỆC 2). */
export const SELECT_COLS = `${SELECT_COLS_LEGACY}, source_id, source_name`;

/**
 * Thiếu cột thì SQLite ném "no such column". Gặp lỗi đó thì chạy lại bằng bộ
 * cột cũ, để code mới deploy trước khi kịp chạy migration vẫn KHÔNG sập kho.
 * Mọi lỗi khác ném tiếp như bình thường.
 */
export function isMissingColumn(e) {
  const m = String((e && e.message) || e || '').toLowerCase();
  return m.includes('no such column') || m.includes('has no column named');
}

/** Chạy `run(cols)`; thiếu cột nguồn gốc thì chạy lại với bộ cột cũ. */
export async function withSourceColumns(run) {
  try {
    return await run(true);
  } catch (e) {
    if (!isMissingColumn(e)) throw e;
    return await run(false);
  }
}
