/* Service Worker — 台南市開放資料檢視器
 * 策略:
 *  - 頁面導覽:網路優先,離線時顯示 /offline
 *  - 靜態資源 (/assets/, /static/, /pwa/):stale-while-revalidate
 *  - Gradio API / 檔案 / 佇列:一律不快取(資料需即時)
 */
const VERSION = "v1";
const CACHE = `tainan-data-${VERSION}`;
const PRECACHE = [
  "/offline",
  "/pwa/icons/icon-192.png",
  "/pwa/icons/icon-512.png",
];
const CACHEABLE_PREFIXES = ["/assets/", "/static/", "/pwa/"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // 頁面導覽
  if (req.mode === "navigate") {
    event.respondWith(fetch(req).catch(() => caches.match("/offline")));
    return;
  }

  // 靜態資源
  if (CACHEABLE_PREFIXES.some((p) => url.pathname.startsWith(p))) {
    event.respondWith(
      caches.open(CACHE).then(async (cache) => {
        const cached = await cache.match(req);
        const network = fetch(req)
          .then((res) => {
            if (res && res.ok) cache.put(req, res.clone());
            return res;
          })
          .catch(() => cached);
        return cached || network;
      })
    );
  }
  // 其餘 (gradio_api 等) 交給瀏覽器預設處理
});
