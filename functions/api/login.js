// POST /api/login  { username, password } → đặt cookie session nếu đúng.
import { pbkdf2Hash, signSession, sessionCookie } from '../_auth.js';

function json(o, s, extra){
  return new Response(JSON.stringify(o), { status: s||200,
    headers: Object.assign({ 'Content-Type':'application/json', 'Cache-Control':'no-store' }, extra||{}) });
}

export async function onRequestPost(context){
  const { request, env } = context;
  if(!env.DB || !env.SESSION_SECRET) return json({ error:'not-configured' }, 503);
  let b; try { b = await request.json(); } catch(e){ return json({ error:'bad-json' }, 400); }
  const u = String(b.username||'').trim().toLowerCase();
  const p = String(b.password||'');
  const row = await env.DB.prepare("SELECT username, salt, hash FROM auth WHERE username=?").bind(u).first();
  if(!row) return json({ error:'invalid' }, 401);
  const h = await pbkdf2Hash(p, row.salt);
  if(h !== row.hash) return json({ error:'invalid' }, 401);
  const token = await signSession(row.username, env.SESSION_SECRET, 30);
  return json({ ok:true, user: row.username }, 200, { 'Set-Cookie': sessionCookie(token, 30) });
}
