import requests
import json

# ========== 설정 ==========
BASE_URL = "https://automotive-cicd.samsungds.net:3090"
PROJECT = "IDCEVO_SOP28V2"
# 인증이 필요한 경우 아래 설정
CICD_COOKIE = ""   # 브라우저 쿠키값 (필요시)
# ==========================

def get_headers():
    headers = {"Content-Type": "application/json"}
    if CICD_COOKIE:
        headers["Cookie"] = CICD_COOKIE
    return headers

def get_testpipeline():
    url = f"{BASE_URL}{'/api/bundle/get_request/'}{PROJECT}{'/TEST-PIPELINE/none'}"
    print(f"\n[GET] {url}")
    try:
        r = requests.get(url, headers=get_headers(), verify=False, timeout=10)

        print(f"  Status : {r.status_code}")
        try:
            data = r.json()
            # print(f"  Response:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
            print(f"Response: data[0] \n{data[0]}")
            return data
        except:
            print(f"  Response (text): {r.text[:500]}")
            return None
    except requests.exceptions.ConnectionError as e:
        print(f"  [연결 오류] {e}")
    except Exception as e:
        print(f"  [오류] {e}")
    return None

def get_binary():
    # 1) 테스트 파이프라인 정보에서 request_run_id 획득
    data = get_testpipeline()
    if not data:
        print("  [중단] 파이프라인 데이터를 받지 못했어요.")
        return None

    request_run_id = data[0]["request_run_id"]
    print(f"\n  request_run_id: {request_run_id}")

    # 2) detail/status 로 바이너리(웹다브) 상세 정보 조회
    url = f"{BASE_URL}{'/api/detail/status/'}{PROJECT}{'/test-pipeline/'}{request_run_id}"
    print(f"\n[GET] {url}")
    try:
        r = requests.get(url, headers=get_headers(), verify=False, timeout=10)
        print(f"  Status : {r.status_code}")
        try:
            detail = r.json()
            print(f"Response: detail[0] \n{detail[0]}")
            return detail
        except:
            print(f"  Response (text): {r.text[:500]}")
            return None
    except requests.exceptions.ConnectionError as e:
        print(f"  [연결 오류] {e}")
    except Exception as e:
        print(f"  [오류] {e}")
    return None


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    binary = get_binary()
