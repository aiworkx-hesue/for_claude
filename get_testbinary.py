import requests
import json
import os
import re
from urllib.parse import urljoin, unquote
from xml.etree import ElementTree

# ========== 설정 ==========
BASE_URL = "https://automotive-cicd.samsungds.net:3090"
PROJECT = "IDCEVO_SOP28V2"
# 인증이 필요한 경우 아래 설정
CICD_COOKIE = ""       # 브라우저 쿠키값 (필요시)
WEBDAV_USER = "share"  # WebDAV 사용자명
WEBDAV_PASS = "share"  # WebDAV 패스워드
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

def list_webdav_files(webdav_dir_url):
    """WebDAV 디렉토리(PROPFIND)에서 파일 목록을 가져옴.
    Depth:1 로 해당 디렉토리 바로 아래 항목만 조회.
    반환: 파일 이름 리스트 (하위 폴더 제외, 파일만)
    """
    headers = {"Depth": "1", "Content-Type": "application/xml"}
    r = requests.request(
        "PROPFIND", webdav_dir_url,
        auth=(WEBDAV_USER, WEBDAV_PASS),
        headers=headers, verify=False, timeout=30
    )
    if r.status_code not in (207, 200):
        print(f"  [WebDAV 목록 오류] Status {r.status_code}")
        print(f"  {r.text[:300]}")
        return []

    # WebDAV 응답은 XML(멀티스테이터스). <d:href> 안에 각 항목 경로가 들어있음.
    files = []
    try:
        tree = ElementTree.fromstring(r.content)
        # 네임스페이스가 있어서 태그명에 {DAV:} 접두어가 붙음
        for resp in tree.iter("{DAV:}response"):
            href_el = resp.find("{DAV:}href")
            if href_el is None or not href_el.text:
                continue
            href = unquote(href_el.text)
            # 디렉토리 자기 자신(끝이 /)은 건너뜀
            if href.endswith("/"):
                continue
            filename = os.path.basename(href.rstrip("/"))
            if filename:
                files.append(filename)
    except Exception as e:
        print(f"  [XML 파싱 오류] {e}")
        return []

    return files

def download_webdav_file(file_url, save_path):
    """WebDAV 파일 하나를 다운로드해서 저장"""
    r = requests.get(
        file_url, auth=(WEBDAV_USER, WEBDAV_PASS),
        verify=False, timeout=120, stream=True
    )
    if r.status_code != 200:
        print(f"    [실패] {os.path.basename(save_path)} (Status {r.status_code})")
        return False
    with open(save_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print(f"    [완료] {os.path.basename(save_path)}")
    return True

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
        detail = r.json()
        print(f"Response: detail[0] \n{detail[0]}")
    except Exception as e:
        print(f"  [오류] {e}")
        return None

    # 3) WebDAV 경로 조합 (file_link + '/' + project_image_path)
    file_link = detail[0]["file_link"]
    image_path = detail[0]["project_image_path"]
    # 사이에 슬래시가 없으면 넣고, 양쪽 다 있으면 중복 제거
    webdav_dir_url = file_link.rstrip("/") + "/" + image_path.lstrip("/")
    # 끝에 / 가 없으면 붙여줌 (디렉토리 조회용)
    if not webdav_dir_url.endswith("/"):
        webdav_dir_url += "/"
    print(f"\n  WebDAV 디렉토리: {webdav_dir_url}")

    # 4) image_path 중간의 다섯자리 숫자로 저장 폴더명 결정
    m = re.search(r"/(\d{5})/", image_path)
    if not m:
        print(f"  [오류] image_path에서 다섯자리 숫자 폴더를 찾지 못했어요: {image_path}")
        return None
    save_dir = m.group(1)
    os.makedirs(save_dir, exist_ok=True)
    print(f"  저장 폴더: ./{save_dir}/")

    # 5) 디렉토리 내 파일 목록 조회 후 전부 다운로드
    files = list_webdav_files(webdav_dir_url)
    if not files:
        print("  [경고] 다운로드할 파일이 없어요.")
        return None

    print(f"\n  총 {len(files)}개 파일 다운로드 시작:")
    success = 0
    for fname in files:
        file_url = urljoin(webdav_dir_url, fname)
        save_path = os.path.join(save_dir, fname)
        if download_webdav_file(file_url, save_path):
            success += 1

    print(f"\n  ✅ {success}/{len(files)}개 다운로드 완료 → ./{save_dir}/")
    return save_dir


if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    binary = get_binary()
