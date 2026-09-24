/**
 * /api/remnants/:id — sửa tên/ghi chú, đánh dấu đã dùng (PATCH) và xoá (DELETE).
 */
import {
  json, fail, preflight, noDb, readJsonBody,
  checkName, checkNote, checkStatus, rowToRemnant, SELECT_COLS,
} from './_lib.js';

export const onRequestOptions = () => preflight();

function readId(params) {
  const id = params && typeof params.id === 'string' ? params.id.trim() : '';
  if (!id || id.length > 64) return { error: 'Thiếu mã tấm thừa hoặc mã không hợp lệ.' };
  return { value: id };
}

export async function onRequestPatch({ request, env, params }) {
  const bad = noDb(env);
  if (bad) return bad;

  const idc = readId(params);
  if (idc.error) return fail(idc.error);

  const body = await readJsonBody(request);
  if (body.error) return fail(body.error);
  const b = body.data;

  // Chỉ cho sửa 3 thứ: tên, ghi chú, trạng thái còn/đã dùng.
  // Kích thước và hình dạng là sự thật vật lý của tấm tôn — muốn khác thì thêm tấm mới.
  const sets = [];
  const binds = [];
  if (b.name !== undefined) {
    const name = checkName(b.name);
    if (name.error) return fail(name.error);
    binds.push(name.value);
    sets.push(`name = ?${binds.length}`);
  }
  if (b.note !== undefined) {
    const note = checkNote(b.note);
    if (note.error) return fail(note.error);
    binds.push(note.value);
    sets.push(`note = ?${binds.length}`);
  }
  if (b.status !== undefined) {
    const st = checkStatus(b.status);
    if (st.error) return fail(st.error);
    binds.push(st.value);
    sets.push(`status = ?${binds.length}`);
  }
  if (sets.length === 0) {
    return fail('Không có gì để sửa. Hãy gửi name, note hoặc status.');
  }

  binds.push(Date.now());
  sets.push(`updated_at = ?${binds.length}`);
  binds.push(idc.value);
  const idPos = binds.length;

  try {
    const row = await env.DB
      .prepare(`UPDATE remnants SET ${sets.join(', ')} WHERE id = ?${idPos} RETURNING ${SELECT_COLS}`)
      .bind(...binds)
      .first();
    if (!row) return fail('Không tìm thấy tấm thừa này trong kho.', 404);
    return json({ ok: true, remnant: rowToRemnant(row) });
  } catch (e) {
    return fail(`Không sửa được tấm thừa: ${e.message}`, 500);
  }
}

export async function onRequestDelete({ env, params }) {
  const bad = noDb(env);
  if (bad) return bad;

  const idc = readId(params);
  if (idc.error) return fail(idc.error);

  try {
    const res = await env.DB
      .prepare('DELETE FROM remnants WHERE id = ?1')
      .bind(idc.value)
      .run();
    const changes = res && res.meta ? res.meta.changes : 0;
    if (!changes) return fail('Không tìm thấy tấm thừa này trong kho.', 404);
    return json({ ok: true, deleted: idc.value });
  } catch (e) {
    return fail(`Không xoá được tấm thừa: ${e.message}`, 500);
  }
}
