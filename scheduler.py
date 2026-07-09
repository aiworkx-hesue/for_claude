"""
QA_TestManager 스케줄러 설정

Flask 앱(단일 프로세스)에 넣어서 매일 아침 8시(월~금)에
get_testbinary.get_binary() 를 자동 실행한다.

[사전 설치]
    pip install APScheduler tzdata
    (tzdata 는 윈도우에서 Asia/Seoul 타임존을 올바로 처리하기 위해 필요)

[사용법] Flask 앱 초기화 부분에서 아래처럼 호출:
    from flask import Flask
    from scheduler import init_scheduler

    app = Flask(__name__)
    init_scheduler()
    ...
    # 개발 중 debug 모드로 켤 때는 리로더 때문에 스케줄러가
    # 두 번 뜨는 것을 막기 위해 use_reloader=False 를 권장:
    #   app.run(debug=True, use_reloader=False)
"""

import atexit
from apscheduler.schedulers.background import BackgroundScheduler

from get_testbinary import get_binary

# 개발 중 테스트할 때 True 로 바꾸면 매 분 실행됨 (동작 확인용).
# 확인 후 반드시 False 로 되돌릴 것.
TEST_MODE = False


def scheduled_job():
    """매일 아침 8시에 트리거되는 작업"""
    print("[스케줄러] 자동 실행 시작")
    try:
        result = get_binary()
        print(f"[스케줄러] 완료: {result}")
    except Exception as e:
        print(f"[스케줄러] 실행 중 오류: {e}")


def init_scheduler():
    """스케줄러를 생성/시작하고 종료 시 정리하도록 등록"""
    scheduler = BackgroundScheduler(timezone="Asia/Seoul")

    if TEST_MODE:
        # 테스트: 매 분 실행
        scheduler.add_job(scheduled_job, trigger="cron", minute="*")
        print("[스케줄러] TEST_MODE - 매 분 실행으로 등록됨")
    else:
        # 운영: 월~금 08:00 실행
        scheduler.add_job(
            scheduled_job,
            trigger="cron",
            day_of_week="mon-fri",
            hour=8,
            minute=0,
        )
        print("[스케줄러] 월~금 08:00 실행으로 등록됨")

    scheduler.start()

    # 앱 종료 시 스케줄러도 깔끔하게 종료
    atexit.register(lambda: scheduler.shutdown())

    return scheduler


if __name__ == "__main__":
    # 단독 실행 시 스케줄러만 띄워서 동작 확인 (Ctrl+C 로 종료)
    import time
    init_scheduler()
    print("스케줄러 단독 실행 중... (Ctrl+C 로 종료)")
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("\n종료합니다.")
