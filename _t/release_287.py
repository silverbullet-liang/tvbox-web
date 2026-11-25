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
        'tag': 'v2.8.7', 'message': 'v2.8.7', 'object': commit_sha, 'type': 'commit'})
    req('POST', '/repos/%s/git/refs' % REPO, {'ref': 'refs/tags/v2.8.7', 'sha': tag_obj['sha']})
    print('tag', tag_obj['sha'])
except SystemExit as e:
    print('tag:', e)

BODY = """### 新增

用户协议：写明使用规则、你提供素材的授权范围、知识产权归属、服务变更与终止、争议解决方式。

### 完善

隐私政策把本机数据整理成清单，标明存储位置与清除方式；第三方请求按用途列出接收方与可见信息；补充权限使用场景、数据留存期限和你的权利。

免责声明补上下载与录制功能的责任边界、一起看公共房间的风险、投稿素材的授权与撤回、开源许可与第三方内容归属。

### 变更

三份条款统一标注版本日期 2026-11-25，版本变化后会重新征询，不同意就不会继续使用。正式版与轻量版的同意门、设置里的账户与条款，都同时列出这三份文档，可随时查看全文。
"""

try:
    rel = req('POST', '/repos/%s/releases' % REPO, {
        'tag_name': 'v2.8.7', 'name': 'v2.8.7 · 三份条款齐备', 'body': BODY,
        'draft': False, 'prerelease': False})
    print('release', rel['html_url'])
except SystemExit as e:
    print('release:', e)
