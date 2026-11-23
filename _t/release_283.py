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
        'tag': 'v2.8.3', 'message': 'v2.8.3', 'object': commit_sha, 'type': 'commit'})
    req('POST', '/repos/%s/git/refs' % REPO, {'ref': 'refs/tags/v2.8.3', 'sha': tag_obj['sha']})
    print('tag', tag_obj['sha'])
except SystemExit as e:
    print('tag:', e)

BODY = """### 修复

**模型列表总是显示读取失败**，三处原因一起改掉了：打开设置时先渲染后拉取，第一帧必然落到失败提示；拉取链路把国内最不稳的 raw.githubusercontent.com 排在最前，而且没有超时，一旦丢包就长时间挂着；三源全不通时的内置清单里还没有 Omega，默认模型找不到，点下载只会提示「未就绪」。

现在 jsDelivr 打头、每个源 6 秒超时、加载期间显示「正在读取模型列表」，内置清单补齐 Omega 三档并注明「以下为内置清单」。模型文件下载同样加了 20 秒超时。

### 新增

**隐私政策与免责声明**：放在仓库 legal/ 目录，站点运行时动态拉取（同源 → jsDelivr → raw 三路回退），以后改文档不用重新发版。

**首次打开需同意**：同时给出核心摘要与两份全文入口；不同意则停留在提示页，无法使用。条款版本变化后会重新征询一次。

**设置 → 账户与条款**：正式版与轻量版都有这两个入口，随时查看全文，并显示当前条款版本日期。

### 说明

免责声明写明：内置源只有一份地址清单，程序只检查资源可用性，不检查合规。源能正常响应只说明技术上可达，不代表内容已授权；认为侵权请直接找该源对应的运营方，本工具能做到的只是把源从内置清单里移除。

同意状态只存在本机 localStorage，不上传，也没有服务端副本可删。
"""

try:
    rel = req('POST', '/repos/%s/releases' % REPO, {
        'tag_name': 'v2.8.3', 'name': 'v2.8.3 · 模型列表修复与条款', 'body': BODY,
        'draft': False, 'prerelease': False})
    print('release', rel['html_url'])
except SystemExit as e:
    print('release:', e)
