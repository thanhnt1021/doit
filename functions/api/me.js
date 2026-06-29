// GET /api/me → { user } nếu đang đăng nhập, ngược lại { user:null }.
import { getSessionUser } from '../_auth.js';

export async function onRequestGet(context){
  const user = await getSessionUser(context.request, context.env);
  return new Response(JSON.stringify({ user: user || null }), { status:200,
    headers: { 'Content-Type':'application/json', 'Cache-Control':'no-store' } });
}
