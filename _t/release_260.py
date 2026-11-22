#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2.6.0：校验远端树、建 annotated tag、发 Release。"""
import json, os, subprocess, urllib.request, urllib.error

REPO = 'silverbullet-liang/tvbox-web'
API = 'https://api.github.com'
TOK = os.environ['GITHUB_TOKEN']
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def req(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(API + path, data=data, method=method)
    r.add_header('Authorization', 'Bearer ' + TOK)
    r.add_header('Accept', 'application/vnd.github+json')
    r.add_header('User-Agent', 'tvbox-release')
    if data:
        r.add_header('Content-Type', 'application/json')
    for i in range(3):
        try:
            with urllib.request.urlopen(r, timeout=120) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode('utf-8', 'replace')
            if e.code < 500:
                raise SystemExit('HTTP %s %s: %s' % (e.code, path, msg[:300]))
            if i == 2:
                raise


def local_sha(path):
    return subprocess.check_output(['git', 'hash-object', path], cwd=ROOT).decode().strip()


ref = req('GET', '/repos/%s/git/ref/heads/main' % REPO)
commit_sha = ref['object']['sha']
tree_sha = req('GET', '/repos/%s/git/commits/%s' % (REPO, commit_sha))['tree']['sha']
tree = req('GET', '/repos/%s/git/trees/%s?recursive=1' % (REPO, tree_sha))
remote = {f['path']: f['sha'] for f in tree['tree'] if f['type'] == 'blob'}
local_files = [p for p in subprocess.check_output(
    ['git', '-c', 'core.quotepath=false', 'ls-files'], cwd=ROOT).decode().splitlines() if p]

diff = [p for p in local_files if remote.get(p) != local_sha(p)]
extra = [p for p in remote if p not in local_files]
print('commit', commit_sha, '| local', len(local_files), '| remote', len(remote))
print('不一致:', diff if diff else '无', '| 远端多余:', extra if extra else '无')
if diff or extra:
    raise SystemExit('远端与本地不一致，停止打 tag')

try:
    tag_obj = req('POST', '/repos/%s/git/tags' % REPO, {
        'tag': 'v2.6.0', 'message': 'v2.6.0', 'object': commit_sha, 'type': 'commit'})
    req('POST', '/repos/%s/git/refs' % REPO, {'ref': 'refs/tags/v2.6.0', 'sha': tag_obj['sha']})
    print('tag', tag_obj['sha'])
except SystemExit as e:
    print('tag:', e)

BODY = """### 新增

- **检测程序可选**：设置页新增「广告识别」区块，可在「规则版」（原来的画面色彩判定，零下载）与「模型版」之间切换。
- **三模态识别模型（beta）**：视频 8 帧 / 音频 64×32 mel / 图片 32×32，可单独给也可一起给，分别输出各自的疑似广告概率；只给音频就只报音频概率。
- **模型管理**：列表从仓库实时拉取，条目带 beta 标记与三个量化档（原始 195 KB / int8 168 KB / int8 全量 83 KB），下载带进度与 sha256 校验，存浏览器缓存。
- **智能推荐**：按核数、内存、是否移动端推荐档位并说明理由。
- **阈值可调**：50%–99%，默认 85%。
- **失败不误伤**：模型只出概率，跳不跳仍由程序按阈值判断；未下载或加载失败时自动走规则版。

### 说明

- 模型是本项目第一款，mini 规格、beta 状态：48,963 参数，训练素材仅 2 支广告 + 5 支开放影片，测试集为同片后段。实测图片/视频分支接近满分、音频 65%，**不代表真实场景准确率**。
- 模型与索引在独立仓库 silverbullet-liang/tvbox-web-models（AGPL-3.0）。
- 首次启用需下载 onnxruntime wasm（约 9.7 MB），之后走浏览器缓存。
"""

try:
    rel = req('POST', '/repos/%s/releases' % REPO, {
        'tag_name': 'v2.6.0', 'name': 'v2.6.0 · 广告识别可选模型', 'body': BODY,
        'draft': False, 'prerelease': False})
    print('release', rel['html_url'])
except SystemExit as e:
    print('release:', e)
