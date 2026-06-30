import requests
import json

# ========== 설정 ==========
BASE_URL = "https://automotive-cicd.samsungds.net:3090"
# 인증이 필요한 경우 아래 설정
SESSION_COOKIE = ""   # 브라우저 쿠키값 (필요시)
AUTH_TOKEN = ""       # Bearer 토큰 (필요시)
# ==========================

def get_headers():
    headers = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    if SESSION_COOKIE:
        headers["Cookie"] = SESSION_COOKIE
    return headers

def call_api(endpoint, method="GET", payload=None):
    url = f"{BASE_URL}{endpoint}"
    print(f"\n[{method}] {url}")
    try:
        if method == "GET":
            r = requests.get(url, headers=get_headers(), verify=False, timeout=10)
        else:
            r = requests.post(url, headers=get_headers(), json=payload, verify=False, timeout=10)

        print(f"  Status : {r.status_code}")
        try:
            data = r.json()
            print(f"  Response:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
            return data
        except:
            print(f"  Response (text): {r.text[:500]}")
            return None
    except requests.exceptions.SSLError:
        print("  [SSL 오류] verify=False 로 재시도 중...")
    except requests.exceptions.ConnectionError as e:
        print(f"  [연결 오류] {e}")
    except Exception as e:
        print(f"  [오류] {e}")
    return None

def explore_apis():
    print("=" * 60)
    print("  CICD 관리 웹페이지 API 탐색")
    print("=" * 60)

    # 1. 프로젝트 목록 조회 (확인된 API)
    call_api("/api/project/get_project")

    # 2. 패턴 기반 추가 탐색 (일반적인 CICD API 패턴)
    candidate_apis = [
        "/api/project/list",
        "/api/project/get_all",
        "/api/build/list",
        "/api/build/get_build",
        "/api/build/history",
        "/api/pipeline/list",
        "/api/pipeline/get_pipeline",
        "/api/deploy/list",
        "/api/deploy/get_deploy",
        "/api/image/list",
        "/api/image/get_image",
        "/api/artifact/list",
        "/api/user/list",
        "/api/docs",
        "/api/swagger",
        "/swagger-ui",
        "/openapi.json",
        "/api-docs",
    ]

    print("\n" + "=" * 60)
    print("  추가 API 엔드포인트 탐색")
    print("=" * 60)
    for api in candidate_apis:
        call_api(api)

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    explore_apis()
