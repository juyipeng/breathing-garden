/* 呼吸花园 Service Worker
   应用本体是一个自包含 HTML（素材已内嵌），这里只是把入口和图标缓存下来，
   让它满足 PWA 的「可安装 + 可离线」条件。 */
var CACHE = 'breathing-garden-v1';
var ASSETS = [
  './',
  './breathing-garden.html',
  './manifest.webmanifest',
  './icon-192.png',
  './icon-512.png'
];

self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE)
      .then(function (c) { return c.addAll(ASSETS); })
      .then(function () { return self.skipWaiting(); })
      .catch(function () { /* 某个资源缺失也不要卡住安装 */ })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys.map(function (k) {
          return k === CACHE ? null : caches.delete(k);
        }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET' || req.url.indexOf('http') !== 0) return;
  e.respondWith(
    caches.match(req).then(function (hit) {
      if (hit) return hit;
      return fetch(req).then(function (res) {
        /* 同源成功响应才写入缓存 */
        if (res && res.status === 200 && res.type === 'basic') {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      }).catch(function () {
        /* 离线兜底：任何导航都回落到应用本体 */
        if (req.mode === 'navigate') return caches.match('./breathing-garden.html');
      });
    })
  );
});
