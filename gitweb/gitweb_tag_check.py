import requests
from requests.auth import HTTPBasicAuth
import re
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== 설정 ==========
BASE_URL = "http://10.166.211.148:8084"
REPO_PATH = "Automotive/DBIO/v9/idcevo-manifest"   # admin/repos/ 뒤에 붙는 경로
GITWEB_REPO_Q = "Automotive/DBIO/idcevo-manifest.git"  # gitweb ?q= 파라미터에 쓰이는 경로 (관찰된 값 기준, 다를 수 있음)
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
        "Referer": f"{BASE_URL}/admin/repos/{REPO_PATH}",
        "X-Requested-With": "XMLHttpRequest",
    }
    if SESSION_COOKIE:
        headers["Cookie"] = SESSION_COOKIE
    s.headers.update(headers)
    # Basic Auth는 쿠키 기반 세션과 충돌할 수 있어 우선 제외.
    # 그래도 안 되면 아래 줄 주석 해제해서 같이 시도해볼 것:
    # s.auth = HTTPBasicAuth(USERNAME, PASSWORD)
    return s

def get_branch_list(session, repo_path):
    """,branches?n=26&S=0 페이지네이션으로 전체 브랜치명 + shortlog URL 수집"""
    branches = {}  # {브랜치명: shortlog_url}
    start = 0

    while True:
        url = f"{BASE_URL}/admin/repos/{repo_path},branches?n={PAGE_SIZE}&S={start}"
        print(f"[요청] {url}")
        r = session.get(url, verify=False, timeout=10)
        print(f"  Status: {r.status_code}")

        if r.status_code != 200:
            print(f"  실패. Response 일부: {r.text[:300]}")
            break

        try:
            data = r.json()
        except Exception:
            print("  JSON 파싱 실패. Response 일부:")
            print(r.text[:500])
            break

        if not data:
            break

        for item in data:
            for link in item.get("web_links", []):
                url_str = link.get("url", "")
                m = re.search(r"refs/heads/([^;\"&]+)", url_str)
                if m:
                    branch_name = m.group(1)
                    # url_str이 상대경로(/gitweb?...)일 수 있으니 BASE_URL과 합쳐줌
                    full_url = url_str if url_str.startswith("http") else BASE_URL + url_str
                    branches[branch_name] = full_url
                    break

        if len(data) < PAGE_SIZE:
            break
        start += PAGE_SIZE

    return branches

def get_tags_from_shortlog(session, shortlog_url):
    """shortlog 페이지 HTML에서 태그 라벨 추출"""
    print(f"  [shortlog 요청] {shortlog_url}")
    r = session.get(shortlog_url, verify=False, timeout=10)

    if r.status_code != 200:
        print(f"    실패 (status {r.status_code})")
        return []

    # gitweb은 보통 <span class="refs"> ... <span class="tag-deco">TAGNAME</span> ... </span> 형태로 표시함
    # 우선 넓게 "tag" 관련 class 안의 텍스트를 긁어봄
    tags = re.findall(r'class="[^"]*tag[^"]*"[^>]*>\s*([^<]+?)\s*<', r.text)
    tags = sorted(set(t.strip() for t in tags if t.strip()))
    return tags, r.text

def check_branch_tag(session, branch_name, shortlog_url):
    print(f"\n[브랜치] {branch_name}")
    tags, html = get_tags_from_shortlog(session, shortlog_url)
    if tags:
        print(f"  ✅ 태그 발견 {len(tags)}개:")
        for t in tags:
            print(f"     - {t}")
    else:
        print("  ❌ 태그 라벨을 못 찾음 (패턴 안 맞을 수 있음, HTML 일부 출력)")
        print("  ", html[:800].replace("\n", " "))
    return tags

if __name__ == "__main__":
    if not PASSWORD:
        print("[경고] PASSWORD 변수가 비어있어요. 코드 상단에 직접 입력 후 실행하세요.")
    else:
        session = get_session()

        print("=" * 60)
        print(f"  레포지토리: {REPO_PATH}")
        print("=" * 60)

        branches = get_branch_list(session, REPO_PATH)
        print(f"\n[브랜치 목록] 총 {len(branches)}개")
        for name in branches:
            print(f"  - {name}")

        target = input("\n태그를 확인할 브랜치명 입력 (정확히 입력): ").strip()
        if target in branches:
            check_branch_tag(session, target, branches[target])
        else:
            print(f"'{target}' 브랜치를 목록에서 찾지 못했어요. 정확한 이름인지 확인해 주세요.")
