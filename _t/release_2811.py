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
        'tag': 'v2.8.11', 'message': 'v2.8.11', 'object': commit_sha, 'type': 'commit'})
    req('POST', '/repos/%s/git/refs' % REPO, {'ref': 'refs/tags/v2.8.11', 'sha': tag_obj['sha']})
    print('tag', tag_obj['sha'])
except SystemExit as e:
    print('tag:', e)

BODY = """### 调整

数据源重新逐个实测筛选，20 个精简为 7 个。

口径：同一接口分别搜索「流浪地球」与「甄嬛传」，比较两批结果的重合度，重合度超过 60% 判定为忽略关键词、返回固定列表；同时检查片名、播放地址、年份的字段完整度与首页内容是否真实更新。

保留非凡、红牛、火狐、无尽、魔都、U酷，新增猫眼。这七个都用两个关键词实测过，结果按关键词返回、播放地址齐全。

移除量子资源与暴风资源（连接超时或重置）、最大资源（忽略关键词，任何搜索都返回首页那 20 条）、百度云盘、电影天堂、360 资源、如意资源、新浪资源、优质资源（不可达）、极速资源、光速资源、虎牙资源、金鹰资源（搜索被 Cloudflare 拒绝）、速播资源（与火狐同源镜像）。

轻量版固定 4 源同步更新为非凡、红牛、无尽、U酷。

源列表以程序内置为准，本机只保存开关状态，升级后自动生效。
"""

try:
    rel = req('POST', '/repos/%s/releases' % REPO, {
        'tag_name': 'v2.8.11', 'name': 'v2.8.11 · 数据源重筛', 'body': BODY,
        'draft': False, 'prerelease': False})
    print('release', rel['html_url'])
except SystemExit as e:
    print('release:', e)
