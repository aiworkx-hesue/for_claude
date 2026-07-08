"""
Gerrit SSH 인터페이스로 태그/브랜치 정보 조회

============================================================
[사전 준비] SSH 키 생성 및 등록 (PC마다 최초 1회만)
============================================================
이 스크립트는 SSH 키 인증을 사용합니다. 개인키는 실행하는 PC의
~/.ssh 폴더에 있어야 하므로, PC를 옮길 때마다 아래 절차를 1회 수행하세요.
(키를 한 번 등록하면 그 PC에서는 계속 사용 가능합니다.)

1) 키 생성 (물어보는 항목은 전부 엔터 = 기본값/암호없음)
     ssh-keygen -t ed25519 -C "twitch.kim.partner.samsung.com"
   생성 결과:
     ~/.ssh/id_ed25519      (개인키 - 절대 외부 공유 금지)
     ~/.ssh/id_ed25519.pub  (공개키 - Gerrit에 등록할 값)

2) 공개키 내용 확인 후 전체 복사
     cat ~/.ssh/id_ed25519.pub
   (출력된 "ssh-ed25519 AAAA... 이메일" 한 줄 전체를 복사)

3) Gerrit 웹 UI에 등록
     Settings > SSH Keys > 복사한 공개키 붙여넣기 > Add New SSH Key

4) 연결 테스트 (버전이 뜨면 성공. 처음이면 yes 입력)
     ssh -p 29414 twitch.kim.partner.samsung.com@10.166.211.148 gerrit version

※ Gerrit은 계정 하나에 여러 PC의 공개키를 등록할 수 있습니다.
  PC A/B/C 각각의 공개키를 등록해두면 어느 PC에서든 동작합니다.
============================================================
"""

import subprocess
import re

# ========== 설정 ==========
GERRIT_HOST = "10.166.211.148"
GERRIT_SSH_PORT = 29414
USERNAME = "twitch.kim.partner.samsung.com"
REPO_PATH = "Automotive/DBIO/v9/idcevo-manifest"
BRANCH_NAME = "exynosauto9_sop28_stable_scarthgap_6.6-b_15-6.6"  # 확인할 브랜치명
TAG_LIMIT = 10  # 표시할 태그 개수 (최신 기준)
# ==========================

def run_ssh(args):
    """gerrit ssh 명령 실행"""
    cmd = [
        "ssh", "-p", str(GERRIT_SSH_PORT),
        f"{USERNAME}@{GERRIT_HOST}",
    ] + args
    print(f"[실행] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"  [오류] {result.stderr.strip()}")
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        print("  [타임아웃] 포트/네트워크를 확인해 주세요.")
        return None
    except FileNotFoundError:
        print("  [오류] ssh 명령을 찾을 수 없어요. (Windows는 Git Bash/OpenSSH 필요)")
        return None

def check_connection():
    """1단계: 연결 및 인증 확인"""
    print("=" * 60)
    print("[1] Gerrit SSH 연결 확인")
    print("=" * 60)
    out = run_ssh(["gerrit", "version"])
    if out:
        print(f"✅ 연결 성공! {out.strip()}")
        return True
    print("❌ 연결 실패. SSH 키가 이 PC에 등록되어 있는지 확인하세요 (상단 주석 참고).")
    return False

def get_tags_via_git():
    """2단계: git ls-remote 로 태그 목록 조회 (clone 불필요)"""
    print("\n" + "=" * 60)
    print(f"[2] 태그 목록 조회 (최신 {TAG_LIMIT}개)")
    print("=" * 60)

    remote = f"ssh://{USERNAME}@{GERRIT_HOST}:{GERRIT_SSH_PORT}/{REPO_PATH}"
    cmd = ["git", "ls-remote", "--tags", "--sort=-creatordate", remote]
    print(f"[실행] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as e:
        print(f"  [오류] {e}")
        return []

    if result.returncode != 0:
        print(f"  [오류] {result.stderr.strip()}")
        return []

    tags = []
    for line in result.stdout.splitlines():
        # 형식: <commit_sha>\trefs/tags/<tagname>
        m = re.search(r"refs/tags/(\S+)", line)
        if m:
            tag = m.group(1)
            if tag.endswith("^{}"):  # annotated tag 의 peeled 참조는 제외
                continue
            sha = line.split("\t")[0][:10]
            tags.append((tag, sha))

    tags = tags[:TAG_LIMIT]
    if tags:
        print(f"\n✅ 태그 {len(tags)}개:")
        for tag, sha in tags:
            print(f"   - {tag}  ({sha})")
    else:
        print("  태그가 없어요.")
    return tags

def check_branch_tagged(tags, branch_name):
    """3단계: 브랜치명 관련 태그가 있는지 확인"""
    print("\n" + "=" * 60)
    print(f"[3] 브랜치 '{branch_name}' 태깅 여부")
    print("=" * 60)
    matched = [t for t, _ in tags if branch_name.lower() in t.lower()]
    if matched:
        print(f"✅ 관련 태그 {len(matched)}개 발견:")
        for t in matched:
            print(f"   - {t}")
    else:
        print("❌ 상위 태그 목록에서 이 브랜치 관련 태그는 안 보여요.")

if __name__ == "__main__":
    if check_connection():
        tags = get_tags_via_git()
        if tags:
            check_branch_tagged(tags, BRANCH_NAME)
