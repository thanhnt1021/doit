// GET /api/state?date=YYYY-MM-DD
// Trả về { levels, noequip, done } — done là map {exercise:true} của riêng ngày đó.
// Nếu chưa bind D1 (env.DB rỗng) → 503, frontend tự fallback localStorage.

function json(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

export async function onRequestGet(context) {
  const { request, env } = context;
  if (!env.DB) return json({ error: "no-db" }, 503);
  const date = new URL(request.url).searchParams.get("date") || "";
  try {
    const settings = await env.DB.prepare("SELECT k, v FROM settings").all();
    let levels = {}, noequip = false;
    for (const row of settings.results || []) {
      if (row.k === "levels") { try { levels = JSON.parse(row.v); } catch (e) {} }
      if (row.k === "noequip") noequip = row.v === "1";
    }
    const done = {};
    if (date) {
      const rows = await env.DB
        .prepare("SELECT exercise, done FROM done_log WHERE date = ?")
        .bind(date)
        .all();
      for (const row of rows.results || []) if (row.done) done[row.exercise] = true;
    }
    return json({ levels, noequip, done });
  } catch (e) {
    return json({ error: String(e) }, 500);
  }
}
