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
        'tag': 'v2.8.10', 'message': 'v2.8.10', 'object': commit_sha, 'type': 'commit'})
    req('POST', '/repos/%s/git/refs' % REPO, {'ref': 'refs/tags/v2.8.10', 'sha': tag_obj['sha']})
    print('tag', tag_obj['sha'])
except SystemExit as e:
    print('tag:', e)

BODY = """### 修复

条款文档改为每次动态读取。此前有三层缓存叠在一起：启动后 12 小时内不校验条款版本、文档请求走浏览器默认 HTTP 缓存、同一页面内重复打开全文直接复用第一次的结果。条款更新后，老用户既不会被重新征询，点开看到的仍可能是旧版。

现在每次启动都校验版本，文档地址带唯一时间戳并禁用 HTTP 缓存，每次点开全文都重新拉取。条款内容本身没有变化，仍是 2026-11-25 版的隐私政策、免责声明与用户协议。
"""

try:
    rel = req('POST', '/repos/%s/releases' % REPO, {
        'tag_name': 'v2.8.10', 'name': 'v2.8.10 · 条款动态读取', 'body': BODY,
        'draft': False, 'prerelease': False})
    print('release', rel['html_url'])
except SystemExit as e:
    print('release:', e)
