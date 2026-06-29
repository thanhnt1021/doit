// Helper auth dùng chung cho các Pages Functions (file _ đầu = không thành route).
// Session: cookie HttpOnly ký HMAC-SHA256. Mật khẩu: PBKDF2-SHA256 100k vòng + salt.

const enc = new TextEncoder();
const dec = new TextDecoder();

function bytesToHex(b){ return Array.from(b).map(function(x){return x.toString(16).padStart(2,'0');}).join(''); }
function hexToBytes(h){ const a=new Uint8Array(h.length/2); for(let i=0;i<a.length;i++) a[i]=parseInt(h.substr(i*2,2),16); return a; }
function b64url(bytes){ let s=btoa(String.fromCharCode.apply(null,bytes)); return s.replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); }
function b64urlToBytes(s){ s=s.replace(/-/g,'+').replace(/_/g,'/'); const bin=atob(s); const b=new Uint8Array(bin.length); for(let i=0;i<bin.length;i++) b[i]=bin.charCodeAt(i); return b; }

export function randomHex(n){ const b=new Uint8Array(n); crypto.getRandomValues(b); return bytesToHex(b); }

export async function pbkdf2Hash(password, saltHex){
  const key = await crypto.subtle.importKey('raw', enc.encode(password), 'PBKDF2', false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits({ name:'PBKDF2', salt: hexToBytes(saltHex), iterations:100000, hash:'SHA-256' }, key, 256);
  return bytesToHex(new Uint8Array(bits));
}

async function hmac(secret, data){
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), { name:'HMAC', hash:'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(data));
  return b64url(new Uint8Array(sig));
}

export async function signSession(user, secret, days){
  const exp = Date.now() + (days||30)*86400000;
  const payload = b64url(enc.encode(JSON.stringify({ u:user, exp:exp })));
  const sig = await hmac(secret, payload);
  return payload + '.' + sig;
}

export async function verifySession(token, secret){
  if(!token || token.indexOf('.') < 0) return null;
  const parts = token.split('.');
  const expect = await hmac(secret, parts[0]);
  if(parts[1] !== expect) return null;
  let data; try { data = JSON.parse(dec.decode(b64urlToBytes(parts[0]))); } catch(e){ return null; }
  if(!data || !data.exp || Date.now() > data.exp) return null;
  return data.u;
}

export function getCookie(request, name){
  const c = request.headers.get('Cookie') || '';
  const m = c.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
  return m ? decodeURIComponent(m[1]) : null;
}

export async function getSessionUser(request, env){
  if(!env.SESSION_SECRET) return null;
  return await verifySession(getCookie(request, 'doit_session'), env.SESSION_SECRET);
}

export function sessionCookie(token, days){
  return 'doit_session=' + encodeURIComponent(token) + '; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=' + ((days||30)*86400);
}
export function clearCookie(){
  return 'doit_session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0';
}
