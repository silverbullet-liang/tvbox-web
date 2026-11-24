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
        'tag': 'v2.8.4', 'message': 'v2.8.4', 'object': commit_sha, 'type': 'commit'})
    req('POST', '/repos/%s/git/refs' % REPO, {'ref': 'refs/tags/v2.8.4', 'sha': tag_obj['sha']})
    print('tag', tag_obj['sha'])
except SystemExit as e:
    print('tag:', e)

BODY = """### 调整

**广告识别转为正式功能**，界面不再标 beta。模型仍是概率输出，是否跳过由阈值与画面佐证决定，这一点没变。

**语音识别与广告识别的模型列表默认折叠**：点标题展开或收起，展开状态记在本机；折叠时标题下方仍显示当前模型是否就绪、用的哪个档位。

### 新增

模型索引每条记录增加 `frontend` 字段，决定是否出现在前端列表。目前只有 Omega（正式 1.0.0）显示，Alpha 与 Beta 保留在仓库里供查阅和直链下载，前端不再出现。

模型拉取增加 gcore.jsdelivr.net 镜像；索引地址带 schema 版本号绕过 CDN 旧缓存，低于当前 schema 的副本会被跳过。

### 修复

- 同时发起两次索引拉取时，第二次可能拿到尚未填充的空列表，模型区显示为空；现在共享同一份请求。
- jsDelivr 缓存的旧索引不含 `frontend` 字段，会让已隐藏的模型重新出现在列表里；现在按 schema 校验，旧副本只在所有镜像都不可用时兜底，并明确标注。
"""

try:
    rel = req('POST', '/repos/%s/releases' % REPO, {
        'tag_name': 'v2.8.4', 'name': 'v2.8.4 · 识别模型转正与折叠', 'body': BODY,
        'draft': False, 'prerelease': False})
    print('release', rel['html_url'])
except SystemExit as e:
    print('release:', e)
