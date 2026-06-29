// POST /api/save
//   { kind:'done', date, exercise, done, level }   → ghi 1 bài của 1 ngày
//   { kind:'settings', levels?, noequip? }         → ghi cài đặt toàn cục
// Bắt buộc đang ĐĂNG NHẬP (cookie session). Khách chỉ xem, không ghi được.
import { getSessionUser } from "../_auth.js";

function json(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

export async function onRequestPost(context) {
  const { request, env } = context;
  if (!env.DB) return json({ error: "no-db" }, 503);
  const user = await getSessionUser(request, env);
  if (!user) return json({ error: "unauthorized" }, 401);

  let body;
  try { body = await request.json(); } catch (e) { return json({ error: "bad-json" }, 400); }

  try {
    if (body.kind === "done") {
      const now = new Date().toISOString();
      await env.DB.prepare(
        "INSERT INTO done_log (date, exercise, done, level, updated_at) VALUES (?,?,?,?,?) " +
        "ON CONFLICT(date, exercise) DO UPDATE SET done=excluded.done, level=excluded.level, updated_at=excluded.updated_at"
      ).bind(
        String(body.date), String(body.exercise),
        body.done ? 1 : 0,
        body.level == null ? null : body.level,
        now
      ).run();
      return json({ ok: true });
    }

    if (body.kind === "settings") {
      const stmts = [];
      if (body.levels !== undefined) {
        stmts.push(env.DB.prepare(
          "INSERT INTO settings (k,v) VALUES ('levels',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v"
        ).bind(JSON.stringify(body.levels)));
      }
      if (body.noequip !== undefined) {
        stmts.push(env.DB.prepare(
          "INSERT INTO settings (k,v) VALUES ('noequip',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v"
        ).bind(body.noequip ? "1" : "0"));
      }
      if (stmts.length) await env.DB.batch(stmts);
      return json({ ok: true });
    }

    return json({ error: "unknown-kind" }, 400);
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
}
