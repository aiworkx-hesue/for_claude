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

if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    test = get_testpipeline()
