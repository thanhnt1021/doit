/**
 * /api/remnants — liệt kê kho tôn thừa (GET) và thêm tấm thừa mới (POST).
 * Không cần đăng nhập: cả xưởng dùng chung một kho, founder đã chốt như vậy.
 */
import {
  json, fail, preflight, noDb, readJsonBody,
  checkName, checkNote, checkDim, checkPolygon, checkStatus, checkCuts,
  rowToRemnant, SELECT_COLS,
} from './_lib.js';

/** Trần số dòng trả về một lượt, tránh kho phình làm nặng máy trong xưởng. */
const MAX_LIMIT = 500;

export const onRequestOptions = () => preflight();

export async function onRequestGet({ request, env }) {
  const bad = noDb(env);
  if (bad) return bad;

  const url = new URL(request.url);
  const statusParam = url.searchParams.get('status') || 'available';
  const limitRaw = Number(url.searchParams.get('limit') || MAX_LIMIT);
  const limit = Number.isFinite(limitRaw) ? Math.min(MAX_LIMIT, Math.max(1, Math.floor(limitRaw))) : MAX_LIMIT;

  try {
    let stmt;
    if (statusParam === 'all') {
      stmt = env.DB
        .prepare(`SELECT ${SELECT_COLS} FROM remnants ORDER BY created_at DESC LIMIT ?1`)
        .bind(limit);
    } else {
      const st = checkStatus(statusParam);
      if (st.error) return fail(st.error);
      stmt = env.DB
        .prepare(`SELECT ${SELECT_COLS} FROM remnants WHERE status = ?1 ORDER BY created_at DESC LIMIT ?2`)
        .bind(st.value, limit);
    }
    const { results } = await stmt.all();
    return json({ ok: true, remnants: (results || []).map(rowToRemnant) });
  } catch (e) {
    return fail(`Không đọc được kho tôn thừa: ${e.message}`, 500);
  }
}

export async function onRequestPost({ request, env }) {
  const bad = noDb(env);
  if (bad) return bad;

  const body = await readJsonBody(request);
  if (body.error) return fail(body.error);
  const b = body.data;

  const name = checkName(b.name);
  if (name.error) return fail(name.error);

  const width = checkDim(b.widthMm, 'Chiều rộng tấm thừa');
  if (width.error) return fail(width.error);

  const length = checkDim(b.lengthMm, 'Chiều dài tấm thừa');
  if (length.error) return fail(length.error);

  const poly = checkPolygon(b.polygon);
  if (poly.error) return fail(poly.error);

  const note = checkNote(b.note);
  if (note.error) return fail(note.error);

  // ── VIỆC 3: khổ tấm gốc + các lỗ đã cắt ─────────────────────────────────
  // Client cũ không gửi 3 trường này → hiểu khổ tấm gốc chính là khung bao đã
  // gửi, lỗ lấy từ polygon[1..]. Không bịa 2000×6000 cho dữ liệu không nói rõ.
  const sheetW = b.sheetWidthMm === undefined
    ? { value: width.value }
    : checkDim(b.sheetWidthMm, 'Khổ tấm gốc (rộng)');
  if (sheetW.error) return fail(sheetW.error);

  const sheetH = b.sheetLengthMm === undefined
    ? { value: length.value }
    : checkDim(b.sheetLengthMm, 'Khổ tấm gốc (dài)');
  if (sheetH.error) return fail(sheetH.error);

  const cuts = checkCuts(b.cuts === undefined ? poly.value.slice(1) : b.cuts);
  if (cuts.error) return fail(cuts.error);

  // Id do máy chủ sinh — không cho client tự đặt để khỏi giẫm lên nhau.
  const id = crypto.randomUUID();
  const now = Date.now();

  try {
    await env.DB
      .prepare(
        `INSERT INTO remnants
           (id, name, width_mm, length_mm, sheet_w_mm, sheet_h_mm, cuts, polygon, note, status, created_at, updated_at)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, 'available', ?10, ?10)`
      )
      .bind(
        id, name.value, width.value, length.value,
        sheetW.value, sheetH.value, JSON.stringify(cuts.value),
        JSON.stringify(poly.value), note.value, now
      )
      .run();
  } catch (e) {
    return fail(`Không lưu được tấm thừa: ${e.message}`, 500);
  }

  return json({
    ok: true,
    remnant: {
      id,
      name: name.value,
      widthMm: width.value,
      lengthMm: length.value,
      sheetWidthMm: sheetW.value,
      sheetLengthMm: sheetH.value,
      cuts: cuts.value,
      polygon: poly.value,
      note: note.value,
      status: 'available',
      createdAt: now,
      updatedAt: now,
    },
  }, 201);
}
