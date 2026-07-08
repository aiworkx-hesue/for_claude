import requests
from requests.auth import HTTPBasicAuth
import re
import json
import urllib3
from urllib.parse import quote
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== 설정 ==========
BASE_URL = "http://10.166.211.148:8084"
REPO_PATH = "Automotive/DBIO/v9/idcevo-manifest"
BRANCH_NAME = "exynosauto9_sop28_stable_scarthgap_6.6-b_15-6.6"  # 확인할 브랜치명
USERNAME = "twitch.kim.partner.samsung.com"
PASSWORD = ""   # 여기에 직접 입력 (공유/업로드 금지)
TAG_LIMIT = 10  # 가져올 태그 수
# ==========================

def get_session():
    s = requests.Session()
    s.auth = HTTPBasicAuth(USERNAME, PASSWORD)
    s.headers.update({"Accept": "application/json"})
    return s

def strip_xssi(text):
    """Gerrit 응답 앞에 붙는 )]}' 제거"""
    return re.sub(r"^\)\s*\]\s*\}\s*'\s*", "", text)

def gerrit_get(session, path):
    """Gerrit 인증 API 호출 (/a/ prefix 사용)"""
    url = f"{BASE_URL}/a{path}"
    print(f"[요청] {url}")
    r = session.get(url, verify=False, timeout=10)
    print(f"  Status: {r.status_code}")

    if r.status_code == 401:
        print("  [인증 실패] 사용자명/패스워드를 확인해 주세요.")
        return None
    if r.status_code == 404:
        print("  [404] 경로 또는 레포를 찾을 수 없어요.")
        return None
    if r.status_code != 200:
        print(f"  [오류] {r.text[:300]}")
        return None

    try:
        return json.loads(strip_xssi(r.text))
    except Exception as e:
        print(f"  JSON 파싱 실패: {e}")
        print(f"  Response 일부: {r.text[:300]}")
        return None

def get_tags(session, repo_path, limit=10):
    """레포의 태그 상위 N개 조회"""
    encoded = quote(repo_path, safe="")
    data = gerrit_get(session, f"/projects/{encoded}/tags?n={limit}")
    if data is None:
        return {}
    tags = {}
    for item in data:
        ref = item.get("ref", "")
        m = re.match(r"refs/tags/(.+)", ref)
        tag_name = m.group(1) if m else ref
        if tag_name:
            tags[tag_name] = item.get("revision", "")
    return tags

def get_tags_by_branch(session, repo_path, branch_name, limit=10):
    """특정 브랜치 기준으로 태그 필터링 (태그명에 브랜치명 일부가 포함된 경우)"""
    tags = get_tags(session, repo_path, limit=limit)
    matched = {k: v for k, v in tags.items() if branch_name.lower() in k.lower()}
    return tags, matched

if __name__ == "__main__":
    if not PASSWORD:
        print("[경고] PASSWORD 변수가 비어있어요. 코드 상단에 직접 입력 후 실행하세요.")
    else:
        session = get_session()

        print("=" * 60)
        print(f"  레포: {REPO_PATH}")
        print(f"  브랜치: {BRANCH_NAME}")
        print("=" * 60)

        tags, matched = get_tags_by_branch(session, REPO_PATH, BRANCH_NAME, limit=TAG_LIMIT)

        print(f"\n[태그 목록] 상위 {len(tags)}개")
        for name, rev in tags.items():
            print(f"  - {name}  ({rev[:10]}...)")

        print(f"\n[브랜치 '{BRANCH_NAME}' 관련 태그] {len(matched)}개")
        if matched:
            print("  ✅ 태깅 되어 있음:")
            for name, rev in matched.items():
                print(f"     - {name}  ({rev[:10]}...)")
        else:
            print("  ❌ 해당 브랜치 관련 태그 없음")
