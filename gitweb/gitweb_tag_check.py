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
PAGE_SIZE = 26  # 관찰된 n=26 패턴
# ==========================

def get_session():
    s = requests.Session()
    s.auth = HTTPBasicAuth(USERNAME, PASSWORD)
    return s

def get_tags(session, repo_path):
    """,tags?n=26&S=0 형태로 페이지네이션하며 전체 태그 수집"""
    all_tags = []
    start = 0

    while True:
        url = f"{BASE_URL}/admin/repos/{repo_path},tags?n={PAGE_SIZE}&S={start}"
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
            # 빈 리스트면 더 가져올 페이지 없음
            break

        page_tags = []
        for item in data:
            for link in item.get("web_links", []):
                url_str = link.get("url", "")
                m = re.search(r"refs/tags/([^;\"&]+)", url_str)
                if m:
                    tag_name = m.group(1)
                    page_tags.append(tag_name)
                    break  # 한 item당 태그 이름 하나만 있으면 충분

        if not page_tags:
            # 더 이상 태그 형태가 없으면 종료 (혹은 이 페이지가 마지막)
            break

        all_tags.extend(page_tags)

        if len(data) < PAGE_SIZE:
            # 마지막 페이지
            break

        start += PAGE_SIZE

    return sorted(set(all_tags))

if __name__ == "__main__":
    if not PASSWORD:
        print("[경고] PASSWORD 변수가 비어있어요. 코드 상단에 직접 입력 후 실행하세요.")
    else:
        session = get_session()

        print("=" * 60)
        print(f"  레포지토리: {REPO_PATH}")
        print("=" * 60)

        tags = get_tags(session, REPO_PATH)

        print(f"\n[태그 목록] 총 {len(tags)}개")
        for t in tags:
            print(f"  - {t}")

        keyword = input("\n확인할 키워드(브랜치명 일부 등) 입력: ").strip()
        if keyword:
            matched = [t for t in tags if keyword.lower() in t.lower()]
            if matched:
                print(f"\n✅ '{keyword}' 포함 태그 {len(matched)}개 발견:")
                for m in matched:
                    print(f"  - {m}")
            else:
                print(f"\n❌ '{keyword}' 포함된 태그 없음 — 태깅 안 된 것으로 보여요.")
