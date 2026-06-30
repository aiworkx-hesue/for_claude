import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime

# ========== 설정 ==========
JENKINS_URL = "http://your-jenkins-host"  # 실제 Jenkins URL로 변경
USERNAME = "your-id"                       # Jenkins 로그인 ID
PASSWORD = "your-password"                 # 비밀번호 또는 API Token
JOB_NAME = "your-job-name"                # 조회할 Job 이름
# ==========================

def get_today_builds(jenkins_url, username, password, job_name):
    """오늘 빌드된 이미지 정보 조회"""
    
    auth = HTTPBasicAuth(username, password)
    
    # 1. 접속 테스트
    print("[1] Jenkins 접속 테스트...")
    try:
        res = requests.get(f"{jenkins_url}/api/json", auth=auth, timeout=5)
        res.raise_for_status()
        print(f"    접속 성공! (status: {res.status_code})")
    except requests.exceptions.ConnectionError:
        print("    [오류] Jenkins 서버에 접속할 수 없어요. URL을 확인해 주세요.")
        return
    except requests.exceptions.HTTPError as e:
        print(f"    [오류] 인증 실패 또는 권한 없음: {e}")
        return

    # 2. Job의 빌드 목록 조회
    print(f"\n[2] '{job_name}' 빌드 목록 조회...")
    url = f"{jenkins_url}/job/{job_name}/api/json?tree=builds[number,timestamp,result,duration,url]"
    res = requests.get(url, auth=auth, timeout=5)
    
    if res.status_code == 404:
        print(f"    [오류] Job '{job_name}'을 찾을 수 없어요.")
        return
    
    builds = res.json().get("builds", [])
    
    # 3. 오늘 빌드만 필터링
    today = datetime.now().date()
    today_builds = []
    
    for build in builds:
        build_time = datetime.fromtimestamp(build["timestamp"] / 1000).date()
        if build_time == today:
            today_builds.append(build)
    
    # 4. 결과 출력
    print(f"\n[3] 오늘({today}) 빌드 결과: 총 {len(today_builds)}건\n")
    
    if not today_builds:
        print("    오늘 빌드된 항목이 없어요.")
        return
    
    for build in today_builds:
        build_time = datetime.fromtimestamp(build["timestamp"] / 1000)
        duration_sec = build["duration"] / 1000
        print(f"  빌드 번호 : #{build['number']}")
        print(f"  빌드 시각 : {build_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  결과      : {build['result']}")
        print(f"  소요 시간 : {duration_sec:.1f}초")
        print(f"  URL       : {build['url']}")
        print("  " + "-"*40)


if __name__ == "__main__":
    get_today_builds(JENKINS_URL, USERNAME, PASSWORD, JOB_NAME)
