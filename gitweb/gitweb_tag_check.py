import requests
from requests.auth import HTTPBasicAuth
import re
import json
import urllib3
from urllib.parse import quote
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== 설정 ==========
BASE_URL = "http://10.166.211.148:8084"
REPO_PATH = "Automotive/DBIO/v9/idcevo-manifest"   # 실제 레포 경로 (슬래시 포함, 인코딩은 코드에서 처리)
USERNAME = "twitch.kim.partner.samsung.com"
PASSWORD = ""   # 여기에 직접 입력해서 사용하세요 (코드에 그대로 두고 공유/업로드 금지)
SESSION_COOKIE = ""  # 브라우저에서 복사한 전체 쿠키 문자열을 여기에 직접 입력 (공유/업로드 금지)
PAGE_SIZE = 26
# ==========================

def get_session():
    s = requests.Session()
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }
    if SESSION_COOKIE:
        headers["Cookie"] = SESSION_COOKIE
    s.headers.update(headers)
    return s

def strip_xssi_prefix(text):
    """Gerrit REST API는 응답 앞에 )]}' (줄바꿈 포함될 수 있음) 를 붙임"""
    return re.sub(r"^\)\s*\]\s*\}\s*'\s*", "", text)

def get_branch_list(session, repo_path):
    """/projects/{encoded}/branches?n=26&S=0 페이지네이션으로 전체 브랜치 수집"""
    branches = {}  # {브랜치명: ref}
    start = 0
    encoded_repo = quote(repo_path, safe="")

    while True:
        url = f"{BASE_URL}/projects/{encoded_repo}/branches?n={PAGE_SIZE}&S={start}"
        print(f"[요청] {url}")
        r = session.get(url, verify=False, timeout=10)
        print(f"  Status: {r.status_code}")
        print(f"  [디버그] 응답 Content-Type: {r.headers.get('Content-Type')}")

        if r.status_code != 200:
            print(f"  실패. Response 일부: {r.text[:300]}")
            break

        try:
            text = strip_xssi_prefix(r.text)
            data = json.loads(text)
        except Exception as e:
            print(f"  JSON 파싱 실패: {e}. Response 일부:")
            print(r.text[:500])
            break

        if not data:
            break

        for item in data:
            ref = item.get("ref", "")
            if ref == "HEAD":
                continue
            m = re.match(r"refs/heads/(.+)", ref)
            branch_name = m.group(1) if m else ref
            if branch_name:
                branches[branch_name] = ref

        if len(data) < PAGE_SIZE:
            break
        start += PAGE_SIZE

    return branches

def get_tags(session, repo_path):
    """/projects/{encoded}/tags?n=26&S=0 페이지네이션으로 전체 태그 수집"""
    tags = {}  # {태그명: revision}
    start = 0
    encoded_repo = quote(repo_path, safe="")

    while True:
        url = f"{BASE_URL}/projects/{encoded_repo}/tags?n={PAGE_SIZE}&S={start}"
        print(f"[요청] {url}")
        r = session.get(url, verify=False, timeout=10)
        print(f"  Status: {r.status_code}")

        if r.status_code != 200:
            print(f"  실패. Response 일부: {r.text[:300]}")
            break

        try:
            text = strip_xssi_prefix(r.text)
            data = json.loads(text)
        except Exception as e:
            print(f"  JSON 파싱 실패: {e}. Response 일부:")
            print(r.text[:500])
            break

        if not data:
            break

        for item in data:
            ref = item.get("ref", "")
            m = re.match(r"refs/tags/(.+)", ref)
            tag_name = m.group(1) if m else ref
            if tag_name:
                tags[tag_name] = item.get("revision", "")

        if len(data) < PAGE_SIZE:
            break
        start += PAGE_SIZE

    return tags

if __name__ == "__main__":
    if not PASSWORD and not SESSION_COOKIE:
        print("[경고] PASSWORD 또는 SESSION_COOKIE 중 하나는 채워야 해요.")
    else:
        session = get_session()

        print("=" * 60)
        print(f"  레포지토리: {REPO_PATH}")
        print("=" * 60)

        branches = get_branch_list(session, REPO_PATH)
        print(f"\n[브랜치 목록] 총 {len(branches)}개")
        for name in branches:
            print(f"  - {name}")

        tags = get_tags(session, REPO_PATH)
        print(f"\n[태그 목록] 총 {len(tags)}개")
        for name, rev in tags.items():
            print(f"  - {name}  (revision: {rev})")

        keyword = input("\n확인할 키워드(브랜치명 일부 등) 입력: ").strip()
        if keyword:
            matched = [t for t in tags if keyword.lower() in t.lower()]
            if matched:
                print(f"\n✅ '{keyword}' 포함 태그 {len(matched)}개 발견:")
                for m in matched:
                    print(f"  - {m}")
            else:
                print(f"\n❌ '{keyword}' 포함된 태그 없음 — 태깅 안 된 것으로 보여요.")
