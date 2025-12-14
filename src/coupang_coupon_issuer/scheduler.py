"""0시 스케줄러 모듈"""

import sys
import time
from datetime import datetime, timedelta
from typing import Callable

from .config import CHECK_INTERVAL


class MidnightScheduler:
    """매일 0시에 작업을 실행하는 스케줄러"""

    def __init__(self, task_func: Callable[[], None]):
        """
        Args:
            task_func: 0시에 실행할 함수
        """
        self.task_func = task_func
        self.last_run_date = None

    @staticmethod
    def _timestamp() -> str:
        """현재 시각 문자열 반환"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def run(self) -> None:
        """
        스케줄러 메인 루프

        - 짧은 주기로 시간을 체크하여 시스템 시간 변경에도 안전
        - 0시 0분대를 감지하면 작업 실행
        - 같은 날짜에 중복 실행 방지
        """
        print(f"[{self._timestamp()}] 쿠폰 발급 스케줄러 서비스 시작", flush=True)
        print(f"[{self._timestamp()}] {CHECK_INTERVAL}초마다 0시 여부를 체크합니다", flush=True)

        while True:
            try:
                now = datetime.now()
                current_date = now.date()
                current_hour = now.hour
                current_minute = now.minute

                # 0시 0분대 감지 (00:00:00 ~ 00:00:59)
                is_midnight = (current_hour == 0 and current_minute == 0)

                # 아직 오늘 실행하지 않았고, 0시 0분대라면 실행
                if is_midnight and self.last_run_date != current_date:
                    timestamp = self._timestamp()
                    print(f"\n[{timestamp}] 0시 감지! 작업 시작", flush=True)

                    try:
                        self.task_func()
                        self.last_run_date = current_date
                        print(f"[{self._timestamp()}] 작업 완료. 다음 0시까지 대기합니다.\n", flush=True)

                    except Exception as e:
                        print(f"[{self._timestamp()}] ERROR: 작업 실패: {e}", flush=True)
                        print(f"[{self._timestamp()}] 다음 0시에 재시도합니다.\n", flush=True)
                        # 실패해도 last_run_date를 업데이트하여 오늘은 더 이상 시도하지 않음
                        # 재시도를 원한다면 이 줄을 주석 처리하세요
                        self.last_run_date = current_date

                else:
                    # 다음 0시까지 남은 시간 계산 및 로깅
                    self._log_waiting_status(now, current_hour, current_minute)

                # CHECK_INTERVAL 초 대기
                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                print(f"\n[{self._timestamp()}] 사용자에 의해 중단됨", flush=True)
                sys.exit(0)

            except Exception as e:
                print(f"[{self._timestamp()}] ERROR: 스케줄러 오류: {e}", flush=True)
                print(f"[{self._timestamp()}] 10초 후 재시작합니다...", flush=True)
                time.sleep(10)

    def _log_waiting_status(self, now: datetime, current_hour: int, current_minute: int) -> None:
        """
        대기 상태 로깅 (1시간마다 한 번씩만 출력하여 로그 spam 방지)

        Args:
            now: 현재 시각
            current_hour: 현재 시
            current_minute: 현재 분
        """
        # 다음 0시까지 남은 시간 계산
        if current_hour == 0 and current_minute == 0:
            # 지금이 0시 0분대지만 이미 실행했다면
            next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            # 오늘의 0시가 지났다면 내일 0시, 아직 안 왔다면 오늘 0시
            if current_hour > 0 or (current_hour == 0 and current_minute > 0):
                next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                next_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

        time_left = next_midnight - now
        hours_left = int(time_left.total_seconds() // 3600)
        minutes_left = int((time_left.total_seconds() % 3600) // 60)

        # 1시간마다 한 번씩만 로그 출력 (정각에만)
        if current_minute == 0:
            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 다음 실행까지 약 {hours_left}시간 {minutes_left}분 남음", flush=True)
