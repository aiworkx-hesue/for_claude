"""
Gerrit SSH로 특정 태그가 가리키는 커밋에 달린 '다른 태그' 조회

기준 태그 = PREFIX + "_" + (브랜치명에서 exynosauto9_ 제거)
  예) IR260707_125629_sop28_stable_scarthgap_6.6-b_15-6.6
이 태그가 가리키는 커밋 SHA를 구한 뒤,
같은 커밋을 가리키는 다른 태그(이름 무관)가 있는지 확인함.

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
BRANCH_NAME = "exynosauto9_sop28_stable_scarthgap_6.6-b_15-6.6"  # 브랜치명(전체)
BRANCH_TAG_STRIP = "exynosauto9_"  # 태그명 조합 시 브랜치명 맨 앞에서 제거할 접두어
# ==========================

REMOTE = f"ssh://{USERNAME}@{GERRIT_HOST}:{GERRIT_SSH_PORT}/{REPO_PATH}"

def branch_to_tag_suffix(branch):
    """브랜치명 맨 앞 exynosauto9_ 제거 -> 태그 접미사"""
    if BRANCH_TAG_STRIP and branch.startswith(BRANCH_TAG_STRIP):
        return branch[len(BRANCH_TAG_STRIP):]
    return branch

def get_commit_of_tag(tag):
    """기준 태그 하나가 가리키는 실제 커밋 SHA 조회.
    annotated 태그면 ^{} 참조(실제 커밋)를 우선 사용.
    태그만 지정해 조회하므로 전체 태그를 받지 않아 빠름.
    """
    cmd = ["git", "ls-remote", REMOTE, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"[오류] {r.stderr.strip()}")
        return None

    plain_sha = None
    peeled_sha = None
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        sha, ref = parts[0].strip(), parts[1].strip()
        if ref.endswith("^{}"):
            peeled_sha = sha
        else:
            plain_sha = sha
    return peeled_sha or plain_sha

def get_all_tag_commit_map():
    """전체 태그 -> 커밋 SHA 매핑 (커밋 기준으로 다른 태그를 찾기 위해 필요).
    annotated 태그는 ^{}(실제 커밋) 우선.
    """
    cmd = ["git", "ls-remote", "--tags", REMOTE]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        print(f"[오류] 태그 목록 조회 실패: {r.stderr.strip()}")
        return {}

    peeled, plain = {}, {}
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        sha, ref = parts[0].strip(), parts[1].strip()
        m = re.match(r"refs/tags/(.+)", ref)
        if not m:
            continue
        name = m.group(1)
        if name.endswith("^{}"):
            peeled[name[:-3]] = sha
        else:
            plain[name] = sha

    tag_commit = {}
    for name, sha in plain.items():
        tag_commit[name] = peeled.get(name, sha)
    return tag_commit

def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else PREFIX
    branch = sys.argv[2] if len(sys.argv) > 2 else BRANCH_NAME

    tag_suffix = branch_to_tag_suffix(branch)
    target_tag = f"{prefix}_{tag_suffix}"

    print("=" * 60)
    print(f"  기준 태그: {target_tag}")
    print(f"  레포     : {REPO_PATH}")
    print("=" * 60)

    # 1) 기준 태그가 가리키는 커밋 SHA 조회
    target_sha = get_commit_of_tag(target_tag)
    if not target_sha:
        print(f"\n❌ 태그 '{target_tag}' 을 찾을 수 없어요. PREFIX/브랜치명을 확인해 주세요.")
        return
    print(f"\n  '{target_tag}' 이 가리키는 커밋: {target_sha}")

    # 2) 같은 커밋을 가리키는 다른 태그 찾기
    tag_commit = get_all_tag_commit_map()
    same_commit = [t for t, sha in tag_commit.items()
                   if sha == target_sha and t != target_tag]

    print("\n" + "=" * 60)
    print("  같은 커밋에 달린 다른 태그")
    print("=" * 60)
    if same_commit:
        print(f"\n  ⚠️ 같은 커밋({target_sha[:10]})에 다른 태그 {len(same_commit)}개가 더 있어요:")
        for t in sorted(same_commit):
            print(f"     - {t}")
    else:
        print(f"\n  ✅ 이 커밋에는 '{target_tag}' 태그 하나만 달려 있어요.")

if __name__ == "__main__":
    main()
