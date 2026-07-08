"""
Gerrit SSH로 특정 태그(IR날짜_시간) + 브랜치명 조합 태그 조회

태그 명명 규칙: IR<날짜>_<시간>_<브랜치명>
예) IR260707_125629_exynosauto9_sop28_stable_scarthgap_6.6-b_15-6.6

이 스크립트는 'IR<날짜>_<시간>' 접두어(PREFIX)와 브랜치명(BRANCH_NAME)을 받아:
  1) PREFIX + "_" + BRANCH_NAME 태그가 존재하는지 확인
  2) 같은 PREFIX 로 시작하는 (= 같은 빌드 시점의) 다른 브랜치 태그들도 함께 표시
전체 이력 fetch 없이 태그 목록만 조회하므로 빠름.

============================================================
[사전 준비] SSH 키 생성 및 등록 (PC마다 최초 1회만)
============================================================
1) ssh-keygen -t ed25519 -C "twitch.kim.partner.samsung.com"   (전부 엔터)
2) cat ~/.ssh/id_ed25519.pub                                   (전체 복사)
3) Gerrit 웹 > Settings > SSH Keys > 붙여넣기 > Add New SSH Key
4) ssh -p 29414 twitch.kim.partner.samsung.com@10.166.211.148 gerrit version
※ 개인키는 실행 PC의 ~/.ssh 에 있어야 함.
============================================================
"""

import subprocess
import re
import sys

# ========== 설정 ==========
GERRIT_HOST = "10.166.211.148"
GERRIT_SSH_PORT = 29414
USERNAME = "twitch.kim.partner.samsung.com"
REPO_PATH = "Automotive/DBIO/v9/idcevo-manifest"

PREFIX = "IR260707_125629"   # IR<날짜>_<시간> 부분
BRANCH_NAME = "exynosauto9_sop28_stable_scarthgap_6.6-b_15-6.6"  # 확인할 브랜치명(전체)
BRANCH_TAG_STRIP = "exynosauto9_"  # 태그명 조합 시 브랜치명 맨 앞에서 제거할 접두어
# ==========================

REMOTE = f"ssh://{USERNAME}@{GERRIT_HOST}:{GERRIT_SSH_PORT}/{REPO_PATH}"

def branch_to_tag_suffix(branch):
    """브랜치명을 태그 접미사로 변환.
    태그에는 브랜치명 맨 앞의 'exynosauto9_' 가 빠지므로 제거함.
    예) exynosauto9_sop28_stable_...  ->  sop28_stable_...
    """
    if BRANCH_TAG_STRIP and branch.startswith(BRANCH_TAG_STRIP):
        return branch[len(BRANCH_TAG_STRIP):]
    return branch

def list_tags_with_prefix(prefix):
    """PREFIX 로 시작하는 태그만 서버에서 직접 필터링해 조회.

    git ls-remote 는 refspec 패턴을 줄 수 있어서, 서버가 해당 태그만
    돌려줌 -> 전체 태그를 다 받지 않아 빠름.
    """
    pattern = f"refs/tags/{prefix}*"
    cmd = ["git", "ls-remote", "--tags", REMOTE, pattern]
    print(f"[실행] git ls-remote --tags ... {pattern}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"[오류] {r.stderr.strip()}")
        return []

    tags = []
    for line in r.stdout.splitlines():
        m = re.search(r"refs/tags/(\S+)", line)
        if not m:
            continue
        name = m.group(1)
        if name.endswith("^{}"):   # annotated 태그의 peeled 참조는 중복이라 제외
            continue
        sha = line.split("\t")[0][:10]
        tags.append((name, sha))
    return tags

def main():
    # 실행 인자로도 받을 수 있음: python gerrit_ssh_tags.py <PREFIX> [BRANCH_NAME]
    prefix = sys.argv[1] if len(sys.argv) > 1 else PREFIX
    branch = sys.argv[2] if len(sys.argv) > 2 else BRANCH_NAME

    tag_suffix = branch_to_tag_suffix(branch)
    target_tag = f"{prefix}_{tag_suffix}"

    print("=" * 60)
    print(f"  접두어(PREFIX): {prefix}")
    print(f"  브랜치명(전체) : {branch}")
    print(f"  태그 접미사    : {tag_suffix}  (exynosauto9_ 제거됨)")
    print(f"  찾는 태그      : {target_tag}")
    print("=" * 60)

    tags = list_tags_with_prefix(prefix)

    if not tags:
        print(f"\n❌ '{prefix}' 로 시작하는 태그가 없어요.")
        return

    tag_names = [t for t, _ in tags]

    # 1) 정확히 일치하는 태그 확인
    print("\n" + "=" * 60)
    print("  [1] 브랜치 태그 존재 여부")
    print("=" * 60)
    if target_tag in tag_names:
        sha = dict(tags)[target_tag]
        print(f"  ✅ 있음: {target_tag}  ({sha})")
    else:
        print(f"  ❌ 없음: {target_tag}")
        print("     (이 브랜치는 해당 빌드 시점에 태깅되지 않았을 수 있어요)")

    # 2) 같은 PREFIX 를 가진 다른 태그들 (= 같은 빌드 시점의 다른 브랜치)
    others = sorted(t for t in tag_names if t != target_tag)
    print("\n" + "=" * 60)
    print(f"  [2] 같은 접두어 '{prefix}_' 를 가진 다른 태그")
    print("=" * 60)
    if others:
        print(f"  총 {len(others)}개:")
        for t in others:
            # PREFIX_ 뒷부분(브랜치명 추정)만 강조해서 표시
            suffix = t[len(prefix) + 1:] if t.startswith(prefix + "_") else t
            print(f"     - {t}")
    else:
        print("  다른 태그는 없어요. (이 접두어로는 이 브랜치 태그만 존재)")

if __name__ == "__main__":
    main()
