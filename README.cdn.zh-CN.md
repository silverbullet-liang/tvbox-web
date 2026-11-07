# TVBox CDN 使用说明

[English](README.cdn.md) · **简体中文**

本文只讲 CDN 上能拿到什么、怎么调。播放器源码与项目说明见 [README.zh-CN.md](README.zh-CN.md)。

许可：`AGPL-3.0-or-later`。CDN 上的文件与仓库同源，版本号与 [Release](https://github.com/silverbullet-liang/tvbox-center/releases) 一致。

---

## 1. 可用资源

| 文件 | 说明 | 大小 |
| --- | --- | --- |
| `dist/tvbox-center.min.js` | 组件库（压缩版），已内联 mqtt.js 与 hls.js | 约 1.22 MB |
| `dist/tvbox-center.js` | 组件库（源码版），同上 | 约 1.22 MB |
| `dist/tvbox-sdk.min.js` | 采集接口 SDK（压缩版），只做接口请求与解析 | 约 4 KB |
| `dist/tvbox-sdk.js` | 采集接口 SDK（源码版） | 约 8 KB |
| `index.html` | Pro 版整站，可直接打开或嵌 iframe | 约 216 KB |
| `mini.html` | Mini 版整站，单源、轻量 | 约 84 KB |
| `promo.html` | 宣传页 | 约 34 KB |

### 三种取法

```html
<!-- jsDelivr，锁定版本（推荐，内容不会变） -->
https://cdn.jsdelivr.net/gh/silverbullet-liang/tvbox-center@v2.0.0/dist/tvbox-center.min.js

<!-- jsDelivr，跟随 main（有新提交就变，适合尝鲜） -->
https://cdn.jsdelivr.net/gh/silverbullet-liang/tvbox-center@main/dist/tvbox-center.min.js

<!-- GitHub raw（jsDelivr 不可用时的兜底） -->
https://raw.githubusercontent.com/silverbullet-liang/tvbox-center/main/dist/tvbox-center.min.js
```

jsDelivr 会对文件再做一次 gzip / brotli，实际传输远小于上表体积。

---

## 2. 组件库：TVBox.mount()

一个组件库实例 = 一整套影视中心（多源搜索、HLS 播放、选集与线路、倍速与画幅、投屏、一起看、加密备份、历史、收藏、设置、键盘快捷键）。

### 2.1 最小用法

```html
<div id="tvbox-app" style="height:100vh"></div>
<script src="https://cdn.jsdelivr.net/gh/silverbullet-liang/tvbox-center@v2.0.0/dist/tvbox-center.min.js"></script>
<script>
  TVBox.mount('#tvbox-app');
</script>
```

容器必须给定高度（`height` 或 `min-height`），否则内部是按 `100%` 布局的，会塌成 0。

### 2.2 完整参数

```js
const app = TVBox.mount(target, {
  sources: [
    {
      key: 'lzi',                                  // 唯一标识，进历史/收藏的键
      name: '量子资源',                             // 展示名
      api: 'https://cj.lziapi.com/api.php/provide/vod/', // 采集接口，末尾斜杠可省
      type: 1,                                     // 1 = 影视（苹果 CMS v10 分类），默认 1
      enabled: true,                               // 是否启用，默认 true
      noProxy: false,                              // 标记该源需要代理解析
      search: true,                                // 是否参与服务端搜索
      cors: false                                  // false = 已知无 CORS，自动模式直接走代理
    }
  ],
  theme: 'purple'                                  // purple | yellow | green | blue
});
```

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `sources` | Array | 内置 7 个源 | 数据源列表，传了就整套替换内置源 |
| `theme` | String | 本机已保存的主题 | 初始配色，`purple` / `yellow` / `green` / `blue` |

`sources` 的 `key` 用于区分同 id 作品、拼接历史记录与收藏，重复会导致互相覆盖。

### 2.3 返回值与卸载

```js
const app = TVBox.mount('#tvbox-app', { theme: 'blue' });

app.id;              // 'tvbox-root'，实际插入到容器里的根节点

TVBox.version;       // '2.0.0'
TVBox.unmount();     // 移除根节点与事件监听，可再次 mount
```

同一页面只支持一个实例。再次 `mount` 会先自动卸载上一个。

### 2.4 内置第三方库

组件库已把 mqtt.js 5.15.1 与 hls.js 1.7.3 合并进同一个文件，不需要额外引 CDN：

```js
TVBoxCenter.hls;    // hls.js 命名空间
TVBoxCenter.mqtt;   // mqtt.js 命名空间
```

在 Worker 里同样可以拿到（不执行 UI，只取这两个库）：

```js
importScripts('https://cdn.jsdelivr.net/gh/silverbullet-liang/tvbox-center@v2.0.0/dist/tvbox-center.js');
const { hls, mqtt } = self.TVBoxCenter;
```

### 2.5 样式隔离

组件库的 CSS 全部作用域限定在 `#tvbox-root` 内，不会改宿主页面的 `body`、`button`、`input` 等默认样式。唯一的全局影响是插入一个 `<style data-tvbox="css">` 节点。

### 2.6 依赖的运行时

首次 `mount` 时会按需从 CDN 加载：

- `hls.js`（若宿主未提供 `window.Hls`）
- `iconify-icon`（图标）
- MiSans 字体样式（可选，失败不影响）
- Cast SDK（可选，仅投屏时用到）

如果宿主环境已自带 `window.Hls`，不会重复加载。

---

## 3. 采集 SDK：TVBoxSDK

只做接口请求与数据解析，不含 UI，体积约 4 KB（压缩）。适合自己写界面、或做数据聚合。

```html
<script src="https://cdn.jsdelivr.net/gh/silverbullet-liang/tvbox-center@v2.0.0/dist/tvbox-sdk.min.js"></script>
```

Node 下：

```js
const TVBoxSDK = require('./tvbox-sdk.min.js');
```

### 3.1 创建客户端

```js
const client = TVBoxSDK.create({
  sources: [
    { key: 'lzi', name: '量子资源', api: 'https://cj.lziapi.com/api.php/provide/vod/' },
    { api: 'https://cj.ffzyapi.com/api.php/provide/vod/' }   // 只给 api 也行
  ],
  timeout: 12000
});
```

`sources` 的元素可以是字符串（接口地址）、对象或 `TVBoxSDK.source(...)` 实例。

### 3.2 列表与搜索

```js
// 单源列表
const r = await client.get('lzi').list({ page: 1, t: '' });
// { ok, list, total, pagecount, error? }

// 多源并行搜索（合并结果，自动打 _source / _sourceKey / _api）
const items = await client.search('庆余年');
const page2 = await client.search('庆余年', { page: 2 });

// 搜索联想
const words = await client.suggest('庆', 10);
```

`list` 的 `t` 是苹果 CMS 分类 id，传空表示全部。

### 3.3 详情

```js
const detail = await client.get('lzi').detail('12345');
// detail.vod_name / vod_pic / vod_year / vod_content
// detail.vod_play_from / detail.vod_play_url
```

### 3.4 单源实例

```js
const src = TVBoxSDK.source({
  key: 'lzi',
  api: 'https://cj.lziapi.com/api.php/provide/vod/'
}, { timeout: 8000 });

await src.list({ page: 1 });
await src.detail('12345');
await src.suggest('庆', 10);
src.url({ ac: 'list', pg: 1 });   // 只拼 URL，不发请求
```

### 3.5 解析工具

```js
TVBoxSDK.parseEpisodes('第01集$https://a/1.m3u8#第02集$https://a/2.m3u8');
// [{ name: '第01集', url: 'https://a/1.m3u8' }, ...]

TVBoxSDK.parsePlayUrls(detail.vod_play_url, detail.vod_play_from);
// { '量子资源': [{ name, url }, ...], '量子资源m3u8': [...] }

TVBoxSDK.buildUrl('https://x.com/api.php/provide/vod/', { ac: 'list', pg: 1 });
// 'https://x.com/api.php/provide/vod/?ac=list&pg=1'
```

### 3.6 动态增删源

```js
client.add({ key: 'new', name: '新源', api: 'https://example.com/api.php/provide/vod/' });
client.sources.forEach(s => console.log(s.key, s.name));
```

---

## 4. 直接嵌入整站

不想写挂载代码，直接嵌页面：

```html
<iframe
  src="https://silverbullet-liang.github.io/tvbox-center/index.html"
  style="width:100%;height:100vh;border:0"
  allow="fullscreen; autoplay; clipboard-write"
  referrerpolicy="no-referrer"></iframe>
```

`mini.html` 同理，单源、更轻。

iframe 与宿主页面天然隔离样式和存储；组件库则是同一文档内的挂载，适合需要与页面共享登录态或自己控制容器的场景。

---

## 5. 常见问题

**Q：跨域报错 / 搜索一直空？**
量子、暴风等源关闭了 CORS，组件库默认走第三方代理（`corsmirror.com`）。自建部署可在「设置 → 跨域代理」里填自己的地址（支持 `{url}` 占位）。SDK 不做代理，需要在自有后端转发。

**Q：`mount` 后一片空白？**
先看容器有没有高度，再看控制台是不是依赖脚本被拦截（hls.js / iconify 走公共 CDN）。

**Q：能在同一个页面挂两个实例吗？**
不能。第二次 `mount` 会卸载前一个。

**Q：CDN 上的版本和仓库对不上？**
jsDelivr 对 `@main` 有缓存，锁定到具体版本号（如 `@v2.0.0`）可避免。刷新缓存可访问 `https://purge.jsdelivr.net/gh/silverbullet-liang/tvbox-center@main/dist/tvbox-center.min.js`。

---

## 6. 许可

AGPL-3.0-or-later。通过 CDN 引入视为使用未修改的库；修改后对外提供服务需同样开源。
