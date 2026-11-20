#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2.5.0：校验远端树、建 annotated tag、发 Release。"""
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
        'tag': 'v2.5.0', 'message': 'v2.5.0', 'object': commit_sha, 'type': 'commit'})
    req('POST', '/repos/%s/git/refs' % REPO, {'ref': 'refs/tags/v2.5.0', 'sha': tag_obj['sha']})
    print('tag', tag_obj['sha'])
except SystemExit as e:
    print('tag:', e)

BODY = """### 新增

- **搜索历史**：自动记录最近 20 个关键词，输入框为空时直接列出，点一下就重搜；输入过程中的前缀延伸不会重复入栈。右上「清空」需二次确认。Pro 与轻量版均有。
- **源可用性检测**：设置 → 数据源 → 「检测全部源」，逐个源按 直连 → 代理 1 → 代理 2 的顺序实测取数，三条全不通就判不可用并自动停用（红点标注）。检测中直连命中的源会被记为「直连」，之后优先直连。
- **数据源 13 → 20**：新增火狐、极速、U 酷、光速、如意、速播、新浪、优质；非凡改用 `api.ffzyapi.com`（原域名多数网络不可达）。

### 变更

- 直连策略改为按检测结果决定：未检测过的源直接走代理，只有确认直连可用才先直连——20 个源并发时不再白等一轮 3.5 秒。
- 多源请求加并发上限（搜索 6 / 首页 6 / 联想 3 / 检测 4）。
- 联想建议改走统一取数通道，此前裸 fetch 被 CORS 拦下，一直是空的。

### 移除

- 飘零资源（`p2100.net`）：两条代理都取不到数据，确认失效。
- 源列表里误导性的「免代理」标签。

### 说明

- 内置 20 个源**全部不发送 CORS 响应头**，浏览器裸连一律被拦（真实浏览器实测，控制台报 `blocked by CORS policy`）。所以「排除不可用」实现为：检测时尽力直连，直连不成再走代理，两条都不通的源自动停用。
- **轻量版固定 4 个源**（量子、非凡、红牛、最大），同样带搜索历史与可用性检测。
"""

try:
    rel = req('POST', '/repos/%s/releases' % REPO, {
        'tag_name': 'v2.5.0', 'name': 'v2.5.0 · 七款语音模型与识别语言', 'body': BODY,
        'draft': False, 'prerelease': False})
    print('release', rel['html_url'])
except SystemExit as e:
    print('release:', e)
