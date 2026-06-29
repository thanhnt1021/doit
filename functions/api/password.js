// POST /api/password  { current, next } → đổi mật khẩu (phải đang đăng nhập).
import { getSessionUser, pbkdf2Hash, randomHex } from '../_auth.js';

function json(o, s){
  return new Response(JSON.stringify(o), { status: s||200,
    headers: { 'Content-Type':'application/json', 'Cache-Control':'no-store' } });
}

export async function onRequestPost(context){
  const { request, env } = context;
  if(!env.DB) return json({ error:'no-db' }, 503);
  const user = await getSessionUser(request, env);
  if(!user) return json({ error:'unauthorized' }, 401);
  let b; try { b = await request.json(); } catch(e){ return json({ error:'bad-json' }, 400); }
  const cur = String(b.current||''), next = String(b.next||'');
  if(next.length < 4) return json({ error:'too-short' }, 400);
  const row = await env.DB.prepare("SELECT salt, hash FROM auth WHERE username=?").bind(user).first();
  if(!row) return json({ error:'no-user' }, 400);
  const curHash = await pbkdf2Hash(cur, row.salt);
  if(curHash !== row.hash) return json({ error:'wrong-current' }, 403);
  const salt = randomHex(16);
  const hash = await pbkdf2Hash(next, salt);
  await env.DB.prepare("UPDATE auth SET salt=?, hash=?, updated_at=? WHERE username=?")
    .bind(salt, hash, new Date().toISOString(), user).run();
  return json({ ok:true });
}
