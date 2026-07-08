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
import tempfile
import shutil

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

def get_branch_tags_grouped(branch_name, limit=10):
    """해당 브랜치 이력에 속한 태그만 조회하고, 같은 커밋끼리 묶어서 출력.

    [방식]
    1) 브랜치를 blobless(--filter=blob:none)로 얕게 fetch (파일 내용 제외, 빠름)
    2) git tag --merged FETCH_HEAD 로 그 브랜치 이력에 도달 가능한 태그만 필터
    3) 각 태그가 가리키는 실제 커밋 SHA(annotated는 ^{}) 기준으로 그룹핑
    4) 커밋을 브랜치 이력 최신순으로 정렬해 상위 N개 커밋만 출력
    임시 폴더는 끝나면 삭제.
    """
    print("\n" + "=" * 60)
    print(f"[4] 브랜치 '{branch_name}' 태그 목록 (최대 {limit}개 커밋, 같은 커밋끼리 묶음)")
    print("=" * 60)

    tmpdir = tempfile.mkdtemp(prefix="gerrit_tags_")
    try:
        subprocess.run(["git", "init", "-q"], cwd=tmpdir, timeout=30)

        print("  브랜치 이력 가져오는 중... (blob 제외)")
        fetch = subprocess.run(
            ["git", "fetch", "-q", "--filter=blob:none", "--tags",
             REMOTE, f"refs/heads/{branch_name}"],
            cwd=tmpdir, capture_output=True, text=True, timeout=180
        )
        if fetch.returncode != 0:
            print(f"  ❌ fetch 실패: {fetch.stderr.strip()[:200]}")
            return

        # 이 브랜치 이력에 도달 가능한 태그만 추림
        merged = subprocess.run(
            ["git", "tag", "--merged", "FETCH_HEAD"],
            cwd=tmpdir, capture_output=True, text=True, timeout=60
        )
        branch_tags = set(t.strip() for t in merged.stdout.splitlines() if t.strip())
        if not branch_tags:
            print("  이 브랜치 이력에 속한 태그가 없어요.")
            return

        # 각 태그 -> 실제 커밋 SHA (annotated 태그는 ^{} 로 커밋까지 해석)
        tag_commit = {}
        for tag in branch_tags:
            rev = subprocess.run(
                ["git", "rev-list", "-n", "1", tag],  # 태그가 가리키는 커밋
                cwd=tmpdir, capture_output=True, text=True, timeout=30
            )
            sha = rev.stdout.strip()
            if sha:
                tag_commit[tag] = sha

        # 브랜치 이력 최신순 커밋 순서 확보
        order = subprocess.run(
            ["git", "rev-list", "FETCH_HEAD"],
            cwd=tmpdir, capture_output=True, text=True, timeout=60
        )
        commit_order = {sha: i for i, sha in enumerate(order.stdout.splitlines())}

        # 커밋 SHA -> [태그들] 그룹핑
        groups = {}
        for tag, sha in tag_commit.items():
            groups.setdefault(sha, []).append(tag)

        # 커밋을 브랜치 이력 순서(최신 먼저)로 정렬
        sorted_shas = sorted(
            groups.keys(),
            key=lambda s: commit_order.get(s, float("inf"))
        )[:limit]

        total_tags = sum(len(groups[s]) for s in sorted_shas)
        print(f"\n  ✅ 태그 {total_tags}개 (커밋 {len(sorted_shas)}개):\n")
        for sha in sorted_shas:
            names = sorted(groups[sha])
            if len(names) == 1:
                print(f"   - {names[0]}   ({sha[:10]})")
            else:
                print(f"   - {names[0]}   ({sha[:10]})  ← 같은 커밋 태그 {len(names)}개")
                for extra in names[1:]:
                    print(f"       └ {extra}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


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

    # 이 브랜치 이력에 속한 태그를 커밋별로 묶어서 조회
    get_branch_tags_grouped(BRANCH_NAME, limit=HISTORY_TAG_LIMIT)

if __name__ == "__main__":
    main()
