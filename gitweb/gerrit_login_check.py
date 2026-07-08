import requests
from requests.auth import HTTPBasicAuth
import re
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== 설정 ==========
BASE_URL = "http://10.166.211.148:8084"
USERNAME = "twitch.kim.partner.samsung.com"
PASSWORD = ""   # 여기에 직접 입력 (공유/업로드 금지)
# ==========================

def strip_xssi(text):
    """Gerrit 응답 앞의 )]}' prefix 제거"""
    return re.sub(r"^\)\s*\]\s*\}\s*'\s*", "", text)

def gerrit_get(session, path, show_response=True):
    """Gerrit 인증 API 호출 (/a/ prefix)"""
    url = f"{BASE_URL}/a{path}"
    try:
        r = session.get(url, verify=False, timeout=10)
    except Exception as e:
        print(f"  [{path}] 요청 오류: {e}")
        return None

    status = r.status_code
    if status == 200:
        try:
            data = json.loads(strip_xssi(r.text))
            if show_response:
                preview = json.dumps(data, indent=2, ensure_ascii=False)[:400]
                print(f"  [{path}] 200 OK\n{preview}\n")
            else:
                print(f"  [{path}] 200 OK")
            return data
        except Exception:
            print(f"  [{path}] 200이지만 JSON 아님 (HTML 등)")
            return None
    else:
        print(f"  [{path}] {status}")
        return None

def check_login(session):
    """1단계: 로그인 확인 - 내 계정 정보 조회"""
    print("=" * 60)
    print("[1] 로그인 확인 (/a/accounts/self)")
    print("=" * 60)
    me = gerrit_get(session, "/accounts/self")
    if me:
        print(f"✅ 로그인 성공!")
        print(f"   이름: {me.get('name')}")
        print(f"   계정ID: {me.get('_account_id')}")
        print(f"   이메일: {me.get('email')}")
        return True
    else:
        print("❌ 로그인 실패. USERNAME/PASSWORD를 확인해 주세요.")
        print("   ※ Gerrit은 웹 비밀번호가 아니라 'HTTP Password'를 요구할 수 있어요.")
        print("   ※ Gerrit 웹 UI → Settings → HTTP Credentials 에서 확인/생성 가능해요.")
        return False

def explore_apis(session):
    """2단계: Gerrit 표준 REST API 엔드포인트 탐색"""
    print("\n" + "=" * 60)
    print("[2] 사용 가능한 API 탐색")
    print("=" * 60)

    # Gerrit 표준 API 카테고리 (공식 REST API 기준)
    endpoints = [
        ("/config/server/version",        "Gerrit 서버 버전"),
        ("/config/server/info",           "서버 설정 정보"),
        ("/accounts/self/capabilities",   "내 계정 권한"),
        ("/projects/?n=5",                "프로젝트 목록 (상위 5개)"),
        ("/changes/?n=5",                 "체인지(리뷰) 목록 (상위 5개)"),
        ("/groups/?n=5",                  "그룹 목록 (상위 5개)"),
    ]

    for path, desc in endpoints:
        print(f"\n--- {desc} ---")
        gerrit_get(session, path)

if __name__ == "__main__":
    if not PASSWORD:
        print("[경고] PASSWORD 변수가 비어있어요. 코드 상단에 직접 입력 후 실행하세요.")
    else:
        session = requests.Session()
        session.auth = HTTPBasicAuth(USERNAME, PASSWORD)
        session.headers.update({"Accept": "application/json"})

        if check_login(session):
            explore_apis(session)
