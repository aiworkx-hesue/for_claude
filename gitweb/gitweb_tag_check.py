import requests
from requests.auth import HTTPBasicAuth
import re
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== 설정 ==========
BASE_URL = "http://10.166.211.148:8084"
REPO_PATH = "Automotive/DBIO/v9/idcevo-manifest"   # admin/repos/ 뒤에 붙는 경로
USERNAME = "twitch.kim.partner.samsung.com"
PASSWORD = ""   # 여기에 직접 입력해서 사용하세요 (코드에 그대로 두고 공유/업로드 금지)
# ==========================

def get_session():
    s = requests.Session()
    s.auth = HTTPBasicAuth(USERNAME, PASSWORD)
    return s

def list_refs(session, repo_path, ref_type):
    """ref_type: 'branches' 또는 'tags'"""
    url = f"{BASE_URL}/admin/repos/{repo_path},{ref_type}"
    print(f"\n[요청] {url}")
    r = session.get(url, verify=False, timeout=10)
    print(f"  Status: {r.status_code}")

    if r.status_code != 200:
        print(f"  접속 실패. Response 일부: {r.text[:300]}")
        return []

    # HTML 구조를 모르니 일단 넓게 텍스트/링크 패턴을 긁어봄
    # 1) href 안에 ref 이름이 들어간 패턴
    candidates = re.findall(r'href="[^"]*' + ref_type + r'[^"]*?/([^"/]+)"', r.text)
    # 2) <td> 혹은 <span class="name">이름</span> 형태 (흔한 admin UI 패턴)
    if not candidates:
        candidates = re.findall(r'class="[^"]*name[^"]*"[^>]*>([^<]+)<', r.text)

    candidates = sorted(set(c.strip() for c in candidates if c.strip()))
    return candidates, r.text  # 원문도 같이 반환 (패턴 안 맞을 때 직접 확인용)

if __name__ == "__main__":
    if not PASSWORD:
        print("[경고] PASSWORD 변수가 비어있어요. 코드 상단에 직접 입력 후 실행하세요.")
    else:
        session = get_session()

        print("=" * 60)
        print(f"  레포지토리: {REPO_PATH}")
        print("=" * 60)

        branches, branch_html = list_refs(session, REPO_PATH, "branches")
        print(f"\n[브랜치 목록] 총 {len(branches)}개")
        for b in branches:
            print(f"  - {b}")
        if not branches:
            print("  (패턴 매칭 실패 — 아래 HTML 일부를 보고 구조 확인 필요)")
            print(branch_html[:1000])

        tags, tag_html = list_refs(session, REPO_PATH, "tags")
        print(f"\n[태그 목록] 총 {len(tags)}개")
        for t in tags:
            print(f"  - {t}")
        if not tags:
            print("  (패턴 매칭 실패 — 아래 HTML 일부를 보고 구조 확인 필요)")
            print(tag_html[:1000])

        keyword = input("\n확인할 키워드(project명/seq/버전 등) 입력: ").strip()
        if keyword:
            matched = [t for t in tags if keyword.lower() in t.lower()]
            if matched:
                print(f"\n✅ '{keyword}' 포함 태그 {len(matched)}개 발견:")
                for m in matched:
                    print(f"  - {m}")
            else:
                print(f"\n❌ '{keyword}' 포함된 태그 없음 — 태깅 안 된 것으로 보여요.")
