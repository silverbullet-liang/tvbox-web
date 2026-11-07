# TVBox CDN Guide

**English** · [简体中文](README.cdn.zh-CN.md)

What is on the CDN and how to call it. For the player itself and project overview see [README.md](README.md).

Licence: `AGPL-3.0-or-later`. CDN files are the same artifacts as the repo; version numbers match the [releases](https://github.com/silverbullet-liang/tvbox-center/releases).

---

## 1. What is available

| File | Contents | Size |
| --- | --- | --- |
| `dist/tvbox-center.min.js` | Component library, minified; mqtt.js and hls.js inlined | ~1.22 MB |
| `dist/tvbox-center.js` | Component library, source | ~1.22 MB |
| `dist/tvbox-sdk.min.js` | API SDK, minified — requests and parsing only | ~4 KB |
| `dist/tvbox-sdk.js` | API SDK, source | ~8 KB |
| `index.html` | Pro build, open directly or embed in an iframe | ~216 KB |
| `mini.html` | Mini build, single source, lightweight | ~84 KB |
| `promo.html` | Landing page | ~34 KB |

### Three ways to fetch

```html
<!-- jsDelivr, pinned version (recommended, immutable) -->
https://cdn.jsdelivr.net/gh/silverbullet-liang/tvbox-center@v2.0.0/dist/tvbox-center.min.js

<!-- jsDelivr, follow main (changes with every commit) -->
https://cdn.jsdelivr.net/gh/silverbullet-liang/tvbox-center@main/dist/tvbox-center.min.js

<!-- GitHub raw (fallback) -->
https://raw.githubusercontent.com/silverbullet-liang/tvbox-center/main/dist/tvbox-center.min.js
```

jsDelivr applies gzip / brotli on top of these files, so the transferred size is far below the numbers above.

---

## 2. Component library: TVBox.mount()

One instance is a complete media centre: multi-source search, HLS playback, episodes and lines, speed and aspect, casting, Watch Together, encrypted backup, history, favorites, settings, keyboard shortcuts.

### 2.1 Minimal usage

```html
<div id="tvbox-app" style="height:100vh"></div>
<script src="https://cdn.jsdelivr.net/gh/silverbullet-liang/tvbox-center@v2.0.0/dist/tvbox-center.min.js"></script>
<script>
  TVBox.mount('#tvbox-app');
</script>
```

The container must have a height (`height` or `min-height`); the internal layout is percentage-based and collapses to 0 otherwise.

### 2.2 Full options

```js
const app = TVBox.mount(target, {
  sources: [
    {
      key: 'lzi',                                        // unique id, used for history / favorites
      name: 'Quantum',                                   // display name
      api: 'https://cj.lziapi.com/api.php/provide/vod/',  // MacCMS v10 endpoint, trailing slash optional
      type: 1,                                           // 1 = movies/TV, default 1
      enabled: true,                                     // default true
      noProxy: false,                                    // mark sources resolved through a proxy
      search: true,                                      // participate in server-side search
      cors: false                                        // false = known to lack CORS, proxy in auto mode
    }
  ],
  theme: 'purple'                                        // purple | yellow | green | blue
});
```

| Option | Type | Default | Notes |
| --- | --- | --- | --- |
| `sources` | Array | 7 built-in sources | Passing it replaces the built-in set entirely |
| `theme` | String | last saved theme | Initial palette: `purple` / `yellow` / `green` / `blue` |

`key` distinguishes items with the same id and keys history / favorites — duplicates overwrite each other.

### 2.3 Return value and unmounting

```js
const app = TVBox.mount('#tvbox-app', { theme: 'blue' });

app.id;              // 'tvbox-root' — the root node inserted into your container

TVBox.version;       // '2.0.0'
TVBox.unmount();     // removes the node and listeners; you can mount again
```

One instance per page. Calling `mount` again unmounts the previous one first.

### 2.4 Bundled libraries

mqtt.js 5.15.1 and hls.js 1.7.3 are merged into the same file — no extra CDN tags needed:

```js
TVBoxCenter.hls;    // hls.js namespace
TVBoxCenter.mqtt;   // mqtt.js namespace
```

The same file works inside a Worker (it loads the two libraries without running the UI):

```js
importScripts('https://cdn.jsdelivr.net/gh/silverbullet-liang/tvbox-center@v2.0.0/dist/tvbox-center.js');
const { hls, mqtt } = self.TVBoxCenter;
```

### 2.5 Style isolation

All CSS is scoped to `#tvbox-root`; host `body`, `button`, `input` defaults are untouched. The only global side effect is one `<style data-tvbox="css">` node.

### 2.6 Runtime dependencies

On first `mount` the library may load from CDN:

- `hls.js` (skipped when `window.Hls` already exists)
- `iconify-icon` (icons)
- MiSans font CSS (optional, failure is harmless)
- Cast SDK (optional, casting only)

---

## 3. API SDK: TVBoxSDK

Requests and parsing only, no UI, ~4 KB minified. Useful for custom front-ends or data pipelines.

```html
<script src="https://cdn.jsdelivr.net/gh/silverbullet-liang/tvbox-center@v2.0.0/dist/tvbox-sdk.min.js"></script>
```

Node:

```js
const TVBoxSDK = require('./tvbox-sdk.min.js');
```

### 3.1 Create a client

```js
const client = TVBoxSDK.create({
  sources: [
    { key: 'lzi', name: 'Quantum', api: 'https://cj.lziapi.com/api.php/provide/vod/' },
    { api: 'https://cj.ffzyapi.com/api.php/provide/vod/' }   // api alone is fine
  ],
  timeout: 12000
});
```

Each entry can be a URL string, an object, or a `TVBoxSDK.source(...)` instance.

### 3.2 Lists and search

```js
// single source
const r = await client.get('lzi').list({ page: 1, t: '' });
// { ok, list, total, pagecount, error? }

// parallel search across sources, merged, each item tagged with _source / _sourceKey / _api
const items = await client.search('Inception');
const page2 = await client.search('Inception', { page: 2 });

// suggestions
const words = await client.suggest('In', 10);
```

`t` is a MacCMS category id; empty means all.

### 3.3 Detail

```js
const detail = await client.get('lzi').detail('12345');
// detail.vod_name / vod_pic / vod_year / vod_content
// detail.vod_play_from / detail.vod_play_url
```

### 3.4 Standalone source

```js
const src = TVBoxSDK.source({
  key: 'lzi',
  api: 'https://cj.lziapi.com/api.php/provide/vod/'
}, { timeout: 8000 });

await src.list({ page: 1 });
await src.detail('12345');
await src.suggest('In', 10);
src.url({ ac: 'list', pg: 1 });   // URL only, no request
```

### 3.5 Parsing helpers

```js
TVBoxSDK.parseEpisodes('Ep01$https://a/1.m3u8#Ep02$https://a/2.m3u8');
// [{ name: 'Ep01', url: 'https://a/1.m3u8' }, ...]

TVBoxSDK.parsePlayUrls(detail.vod_play_url, detail.vod_play_from);
// { 'Source A': [{ name, url }, ...], 'Source A m3u8': [...] }

TVBoxSDK.buildUrl('https://x.com/api.php/provide/vod/', { ac: 'list', pg: 1 });
// 'https://x.com/api.php/provide/vod/?ac=list&pg=1'
```

### 3.6 Add sources at runtime

```js
client.add({ key: 'new', name: 'New source', api: 'https://example.com/api.php/provide/vod/' });
client.sources.forEach(s => console.log(s.key, s.name));
```

---

## 4. Embedding the full app

If you would rather not write mount code:

```html
<iframe
  src="https://silverbullet-liang.github.io/tvbox-center/index.html"
  style="width:100%;height:100vh;border:0"
  allow="fullscreen; autoplay; clipboard-write"
  referrerpolicy="no-referrer"></iframe>
```

`mini.html` works the same way and is lighter.

An iframe isolates styles and storage; the component library mounts inside your document, which is what you want when the container is yours and the page should share login state.

---

## 5. FAQ

**CORS errors / empty search results?**
Several sources stopped sending CORS headers. The component library proxies automatically through `corsmirror.com`; in Settings → CORS proxy you can supply your own endpoint (`{url}` placeholder supported). The SDK does not proxy — forward requests through your own backend.

**Blank area after `mount`?**
Check the container height first, then the console for blocked dependency scripts (hls.js / iconify come from public CDNs).

**Two instances on one page?**
Not supported. The second `mount` unmounts the first.

**CDN and repo out of sync?**
jsDelivr caches `@main`. Pin a version (`@v2.0.0`) to avoid it, or purge:
`https://purge.jsdelivr.net/gh/silverbullet-liang/tvbox-center@main/dist/tvbox-center.min.js`.

---

## 6. Licence

AGPL-3.0-or-later. Pulling from the CDN counts as using the library unmodified; modified versions offered as a service must be open-sourced too.
