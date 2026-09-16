/* Cache no private pages, API responses, session content or inventory. */
self.addEventListener('install',()=>self.skipWaiting());
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('fetch',event=>{
 if(event.request.mode!=='navigate')return;
 event.respondWith(fetch(event.request).catch(()=>new Response(`<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nexo · Sin conexión</title><style>body{font:16px system-ui;background:#f7f8fa;color:#284c3b;display:grid;place-content:center;min-height:90vh;padding:24px}main{max-width:420px}h1{font-size:30px}p{line-height:1.7;color:#61766a}a{display:inline-block;background:#197459;color:white;padding:12px 20px;border-radius:8px;text-decoration:none}</style><main><h1>Volvamos a conectar.</h1><p>Nexo necesita internet para consultar y confirmar el inventario de todas tus sucursales. No se han enviado movimientos desde esta pantalla.</p><a href="/">Volver a intentar</a></main></html>`,{status:503,headers:{'Content-Type':'text/html;charset=utf-8','Cache-Control':'no-store'}})));
});
