"""
Gerrit SSH 인터페이스로 특정 브랜치 HEAD에 달린 태그 조회

============================================================
[사전 준비] SSH 키 생성 및 등록 (PC마다 최초 1회만)
============================================================
이 스크립트는 SSH 키 인증을 사용합니다. 개인키는 실행하는 PC의
~/.ssh 폴더에 있어야 하므로, PC를 옮길 때마다 아래 절차를 1회 수행하세요.

1) 키 생성 (물어보는 항목은 전부 엔터 = 기본값/암호없음)
     ssh-keygen -t ed25519 -C "twitch.kim.partner.samsung.com"
   생성 결과:
     ~/.ssh/id_ed25519      (개인키 - 절대 외부 공유 금지)
     ~/.ssh/id_ed25519.pub  (공개키 - Gerrit에 등록할 값)

2) 공개키 내용 확인 후 전체 복사
     cat ~/.ssh/id_ed25519.pub

3) Gerrit 웹 UI에 등록
     Settings > SSH Keys > 복사한 공개키 붙여넣기 > Add New SSH Key

4) 연결 테스트 (버전이 뜨면 성공. 처음이면 yes 입력)
     ssh -p 29414 twitch.kim.partner.samsung.com@10.166.211.148 gerrit version

※ Gerrit은 계정 하나에 여러 PC의 공개키를 등록할 수 있습니다.
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
HISTORY_TAG_LIMIT = 10  # 브랜치 이력에서 보여줄 최근 태그 개수
# ==========================

REMOTE = f"ssh://{USERNAME}@{GERRIT_HOST}:{GERRIT_SSH_PORT}/{REPO_PATH}"

def check_connection():
    """1단계: SSH 연결/인증 확인"""
    print("=" * 60)
    print("[1] Gerrit SSH 연결 확인")
    print("=" * 60)
    cmd = ["ssh", "-p", str(GERRIT_SSH_PORT), f"{USERNAME}@{GERRIT_HOST}", "gerrit", "version"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            print(f"✅ 연결 성공! {r.stdout.strip()}")
            return True
        print(f"❌ 연결 실패: {r.stderr.strip()}")
        return False
    except Exception as e:
        print(f"❌ 오류: {e}")
        return False

def get_branch_head_sha(branch_name):
    """2단계: 브랜치 HEAD 커밋 SHA 조회"""
    print("\n" + "=" * 60)
    print(f"[2] 브랜치 HEAD 커밋 조회: {branch_name}")
    print("=" * 60)
    cmd = ["git", "ls-remote", REMOTE, f"refs/heads/{branch_name}"]
    print(f"[실행] {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0 or not r.stdout.strip():
        print(f"  ❌ 브랜치를 찾을 수 없어요. 이름을 확인해 주세요.\n  {r.stderr.strip()}")
        return None
    sha = r.stdout.split("\t")[0].strip()
    print(f"  HEAD SHA: {sha}")
    return sha

def get_all_tags():
    """전체 태그와 각 태그가 가리키는 SHA 조회.

    [핵심 처리 - annotated tag 문제]
    git 태그에는 두 종류가 있어요:
      1) 경량(lightweight) 태그: 커밋을 직접 가리킴. SHA = 커밋 SHA
      2) 주석(annotated) 태그: 태그 객체(메시지/작성자 포함)를 별도로 만들고,
         그 태그 객체가 커밋을 가리킴.

    ls-remote 결과에서 annotated 태그는 두 줄로 나옵니다:
      <태그객체_SHA>   refs/tags/v1.0
      <실제_커밋_SHA>  refs/tags/v1.0^{}     <- ^{} 가 "실제 가리키는 커밋"

    브랜치 HEAD는 '커밋 SHA'이므로, 태그의 태그객체 SHA와 비교하면
    annotated 태그는 절대 안 맞습니다. 따라서 ^{}(peeled) 가 있으면
    그 커밋 SHA를 우선 사용해야 정확히 매칭됩니다.
    """
    cmd = ["git", "ls-remote", "--tags", REMOTE]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"  [태그 조회 오류] {r.stderr.strip()}")
        return {}

    # tag_name -> 가리키는 커밋 SHA
    tag_to_commit = {}
    peeled = {}  # ^{} 로 끝나는 참조 = annotated 태그가 실제로 가리키는 커밋
    plain = {}   # 일반 참조 = 경량 태그의 커밋 SHA, 또는 annotated 태그의 태그객체 SHA
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
            peeled[name[:-3]] = sha  # ^{} 3글자를 떼어 원래 태그명으로 저장
        else:
            plain[name] = sha

    # 최종 매핑: peeled(실제 커밋)가 있으면 우선, 없으면(경량 태그) plain 사용
    for name, sha in plain.items():
        tag_to_commit[name] = peeled.get(name, sha)
    return tag_to_commit

def get_recent_tags_grouped(limit=10):
    """최근 태그를 순서대로 출력하되, 같은 커밋을 가리키는 태그는 묶어서 표시.

    [방식] git ls-remote --tags 로 태그와 SHA를 가져옴.
    annotated 태그는 ^{} 참조(실제 커밋 SHA)를 우선 사용해,
    같은 커밋에 달린 여러 태그를 정확히 같은 그룹으로 묶음.
    정렬은 태그명 버전 기준(-v:refname)으로 최신순.
    """
    print("\n" + "=" * 60)
    print(f"[4] 최근 태그 목록 (최대 {limit}개, 같은 커밋끼리 묶음)")
    print("=" * 60)

    # 태그명 -> 실제 커밋 SHA 매핑 (annotated 태그 ^{} 우선)
    tag_to_commit = get_all_tags()
    if not tag_to_commit:
        print("  태그가 없어요.")
        return

    # 최신순 정렬을 위해 ls-remote 를 버전 정렬로 다시 호출해 순서 확보
    cmd = ["git", "ls-remote", "--tags", "--sort=-v:refname", REMOTE]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    ordered_tags = []
    if r.returncode == 0:
        seen = set()
        for line in r.stdout.splitlines():
            m = re.search(r"refs/tags/(\S+)", line)
            if not m:
                continue
            name = m.group(1)
            if name.endswith("^{}"):
                continue
            if name not in seen:
                seen.add(name)
                ordered_tags.append(name)
    else:
        ordered_tags = list(tag_to_commit.keys())

    # 커밋 SHA 기준으로 그룹핑 (순서 유지)
    groups = []          # [(commit_sha, [tag, ...]), ...]
    commit_index = {}    # commit_sha -> groups 내 인덱스
    for name in ordered_tags:
        sha = tag_to_commit.get(name)
        if sha is None:
            continue
        if sha in commit_index:
            groups[commit_index[sha]][1].append(name)
        else:
            commit_index[sha] = len(groups)
            groups.append((sha, [name]))

    # 최대 limit 개 그룹만 출력
    groups = groups[:limit]
    print(f"\n  ✅ 최근 태그 {sum(len(g[1]) for g in groups)}개 (커밋 {len(groups)}개):\n")
    for sha, names in groups:
        if len(names) == 1:
            print(f"   - {names[0]}   ({sha[:10]})")
        else:
            # 같은 커밋에 태그 여러 개
            print(f"   - {names[0]}   ({sha[:10]})  ← 같은 커밋 태그 {len(names)}개")
            for extra in names[1:]:
                print(f"       └ {extra}")


def main():
    if not check_connection():
        return

    head_sha = get_branch_head_sha(BRANCH_NAME)
    if not head_sha:
        return

    print("\n" + "=" * 60)
    print("[3] HEAD 커밋에 달린 태그 확인")
    print("=" * 60)
    tag_to_commit = get_all_tags()
    print(f"  전체 태그 {len(tag_to_commit)}개 조회 완료")

    matched = [tag for tag, sha in tag_to_commit.items() if sha == head_sha]

    if matched:
        print(f"\n✅ 브랜치 '{BRANCH_NAME}' HEAD에 달린 태그 {len(matched)}개:")
        for t in matched:
            print(f"   - {t}")
    else:
        print(f"\n❌ 브랜치 '{BRANCH_NAME}' HEAD({head_sha[:10]})에 달린 태그가 없어요.")
        print("   (아직 태깅되지 않았거나, HEAD 이전 커밋에만 태그가 있을 수 있어요.)")

    # HEAD 아래(이력)에 속한 최근 태그도 함께 조회
    get_recent_tags_grouped(limit=HISTORY_TAG_LIMIT)

if __name__ == "__main__":
    main()
