/** All requests, including /data/*.json, pass this authentication gate. */
const unauthorized = () => new Response('需要登入：請輸入私人網站帳號與密碼。', {
  status: 401,
  headers: {
    'WWW-Authenticate': 'Basic realm="Private Game Intelligence", charset="UTF-8"',
    'Cache-Control': 'no-store',
    'Content-Type': 'text/plain; charset=utf-8',
    'X-Robots-Tag': 'noindex, nofollow',
  },
});
async function equalSecret(a, b) {
  const enc = new TextEncoder();
  const [x, y] = await Promise.all([crypto.subtle.digest('SHA-256', enc.encode(a)), crypto.subtle.digest('SHA-256', enc.encode(b))]);
  const A = new Uint8Array(x), B = new Uint8Array(y);
  let mismatch = 0;
  for (let i = 0; i < A.length; i++) mismatch |= A[i] ^ B[i];
  return mismatch === 0;
}
export default {
  async fetch(request, env) {
    if (!env.SITE_USERNAME || !env.SITE_PASSWORD) return new Response('網站尚未設定登入憑證。', {status: 503, headers: {'Cache-Control': 'no-store'}});
    const auth = request.headers.get('Authorization') || '';
    if (!auth.startsWith('Basic ') || auth.length > 4096) return unauthorized();
    let decoded;
    try { decoded = atob(auth.slice(6)); } catch { return unauthorized(); }
    const sep = decoded.indexOf(':');
    if (sep < 1) return unauthorized();
    const [okUser, okPass] = await Promise.all([
      equalSecret(decoded.slice(0, sep), env.SITE_USERNAME),
      equalSecret(decoded.slice(sep + 1), env.SITE_PASSWORD),
    ]);
    if (!okUser || !okPass) return unauthorized();
    const response = await env.ASSETS.fetch(request);
    const headers = new Headers(response.headers);
    headers.set('Cache-Control', 'private, no-store');
    headers.set('X-Robots-Tag', 'noindex, nofollow');
    headers.set('X-Content-Type-Options', 'nosniff');
    headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
    headers.set('Content-Security-Policy', "frame-ancestors 'none'");
    return new Response(response.body, {status: response.status, statusText: response.statusText, headers});
  }
};
