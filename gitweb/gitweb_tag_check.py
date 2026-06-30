import requests
from requests.auth import HTTPBasicAuth
import re
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== 설정 ==========
GITWEB_BASE = "http://10.166.211.148:8084/gitweb"  # 실제 gitweb 경로 다르면 수정 필요
REPO_PATH = "Automotive/DBIO/v9/idcevo-manifest.git"
USERNAME = "twitch.kim.partner.samsung.com"
PASSWORD = ""   # 여기에 직접 입력해서 사용하세요 (코드에 그대로 두고 공유/업로드 금지)
# ==========================

def get_session():
    """Basic Auth 세션 생성. GitWeb이 form login을 쓰면 별도 처리 필요."""
    s = requests.Session()
    s.auth = HTTPBasicAuth(USERNAME, PASSWORD)
    return s

def list_tags(session, repo_path):
    """gitweb의 a=tags 페이지에서 태그 목록 HTML 파싱"""
    url = f"{GITWEB_BASE}/?p={repo_path};a=tags"
    print(f"[요청] {url}")
    r = session.get(url, verify=False, timeout=10)
    print(f"  Status: {r.status_code}")

    if r.status_code != 200:
        print("  접속 실패. URL 경로나 인증 방식을 확인해 주세요.")
        print(f"  Response 일부: {r.text[:300]}")
        return []

    # gitweb 태그 페이지는 보통 <a class="list" href=".../shortlog;h=refs/tags/TAGNAME">TAGNAME</a> 형태
    tags = re.findall(r'refs/tags/([^"\'?;]+)', r.text)
    tags = sorted(set(tags))
    return tags

def list_branches(session, repo_path):
    """gitweb의 a=heads 페이지에서 브랜치 목록 조회"""
    url = f"{GITWEB_BASE}/?p={repo_path};a=heads"
    print(f"\n[요청] {url}")
    r = session.get(url, verify=False, timeout=10)
    print(f"  Status: {r.status_code}")

    if r.status_code != 200:
        return []

    branches = re.findall(r'refs/heads/([^"\'?;]+)', r.text)
    return sorted(set(branches))

def check_tag_exists(tags, keyword):
    """특정 키워드(예: project명, seq, 버전 등)가 포함된 태그가 있는지 확인"""
    matched = [t for t in tags if keyword.lower() in t.lower()]
    return matched

if __name__ == "__main__":
    if not PASSWORD:
        print("[경고] PASSWORD 변수가 비어있어요. 코드 상단에 직접 입력 후 실행하세요.")
    else:
        session = get_session()

        print("=" * 60)
        print(f"  레포지토리: {REPO_PATH}")
        print("=" * 60)

        tags = list_tags(session, REPO_PATH)
        print(f"\n[태그 목록] 총 {len(tags)}개")
        for t in tags:
            print(f"  - {t}")

        branches = list_branches(session, REPO_PATH)
        print(f"\n[브랜치 목록] 총 {len(branches)}개")
        for b in branches:
            print(f"  - {b}")

        # 예시: "vn" 또는 빌드 seq 번호가 포함된 태그 찾기
        keyword = input("\n확인할 키워드(project명/seq/버전 등) 입력: ").strip()
        if keyword:
            matched = check_tag_exists(tags, keyword)
            if matched:
                print(f"\n✅ '{keyword}' 포함 태그 {len(matched)}개 발견:")
                for m in matched:
                    print(f"  - {m}")
            else:
                print(f"\n❌ '{keyword}' 포함된 태그 없음 — 태깅 안 된 것으로 보여요.")
