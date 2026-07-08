"""
Gerrit SSH 인터페이스로 특정 태그와 '같은 커밋'에 달린 다른 태그 조회

============================================================
[사전 준비] SSH 키 생성 및 등록 (PC마다 최초 1회만)
============================================================
1) 키 생성 (물어보는 항목은 전부 엔터 = 기본값/암호없음)
     ssh-keygen -t ed25519 -C "twitch.kim.partner.samsung.com"
2) 공개키 확인 후 전체 복사
     cat ~/.ssh/id_ed25519.pub
3) Gerrit 웹 UI에 등록
     Settings > SSH Keys > 붙여넣기 > Add New SSH Key
4) 연결 테스트 (버전 뜨면 성공. 처음이면 yes)
     ssh -p 29414 twitch.kim.partner.samsung.com@10.166.211.148 gerrit version
※ 개인키는 실행 PC의 ~/.ssh 에 있어야 함. PC 옮기면 재등록.
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
TARGET_TAG = "IR260707_125629"   # 확인할 기준 태그 (실행 시 인자로도 받음)
# ==========================

REMOTE = f"ssh://{USERNAME}@{GERRIT_HOST}:{GERRIT_SSH_PORT}/{REPO_PATH}"

def get_tag_commit_map():
    """전체 태그 -> 실제 커밋 SHA 매핑.

    [annotated 태그 처리]
    ls-remote 결과에서 annotated 태그는 두 줄로 나옴:
      <태그객체_SHA>   refs/tags/TAG
      <실제_커밋_SHA>  refs/tags/TAG^{}   <- ^{} 가 진짜 커밋
    커밋 비교가 목적이므로 ^{}(peeled)가 있으면 그 값을 우선 사용.
    """
    cmd = ["git", "ls-remote", "--tags", REMOTE]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        print(f"[오류] 태그 조회 실패: {r.stderr.strip()}")
        return {}

    peeled = {}  # TAG -> 실제 커밋 SHA (annotated)
    plain = {}   # TAG -> SHA (경량 태그이거나 annotated 태그객체 SHA)
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
    # 실행 시 인자로 태그를 주면 그걸 우선 사용: python gerrit_ssh_tags.py <태그명>
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_TAG

    print("=" * 60)
    print(f"  기준 태그: {target}")
    print(f"  레포: {REPO_PATH}")
    print("=" * 60)

    tag_commit = get_tag_commit_map()
    if not tag_commit:
        return

    if target not in tag_commit:
        print(f"\n❌ 태그 '{target}' 을 레포에서 찾을 수 없어요. 이름을 확인해 주세요.")
        # 비슷한 태그 몇 개 힌트로 제시
        similar = [t for t in tag_commit if target[:6] in t][:5]
        if similar:
            print("   혹시 이런 태그인가요?")
            for s in similar:
                print(f"     - {s}")
        return

    target_sha = tag_commit[target]
    print(f"\n  '{target}' 이 가리키는 커밋: {target_sha}")

    # 같은 커밋을 가리키는 다른 태그 찾기
    same_commit = [t for t, sha in tag_commit.items() if sha == target_sha and t != target]

    print("\n" + "=" * 60)
    print("  같은 커밋에 달린 다른 태그")
    print("=" * 60)
    if same_commit:
        print(f"\n  ✅ 같은 커밋({target_sha[:10]})에 달린 다른 태그 {len(same_commit)}개:")
        for t in sorted(same_commit):
            print(f"     - {t}")
        print(f"\n  (기준 태그 포함 총 {len(same_commit) + 1}개가 같은 커밋을 가리켜요)")
    else:
        print(f"\n  이 커밋에는 '{target}' 태그 하나만 달려 있어요.")

if __name__ == "__main__":
    main()
