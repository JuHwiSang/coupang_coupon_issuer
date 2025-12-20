"""
Jitter 관리 모듈 - Thundering herd 방지를 위한 랜덤 지연

ADR 011 참조: docs/adr/011-jitter-thundering-herd.md
"""
from random import randint
from time import sleep
from datetime import datetime, timedelta


class JitterScheduler:
    """
    안전한 폴링 기반 Jitter 스케줄러

    여러 인스턴스가 동시에 API를 호출하는 것을 방지하기 위해
    랜덤한 지연 시간을 추가합니다.

    특징:
    - 1초 간격 폴링으로 블로킹 최소화
    - 시작/종료 시점만 로그 출력
    - 목표 시간 도달 시 즉시 반환
    - KeyboardInterrupt 안전 처리

    Example:
        >>> scheduler = JitterScheduler(max_jitter_minutes=60)
        >>> scheduler.wait_with_jitter()
        [2024-12-20 00:00:00] Jitter 대기 시작 (목표: 00:37:00, 지연: +37분)
        [2024-12-20 00:37:00] Jitter 대기 완료. 쿠폰 발급을 시작합니다.
    """

    POLL_INTERVAL_SECONDS = 1  # 폴링 간격 (1초)

    def __init__(self, max_jitter_minutes: int):
        """
        JitterScheduler 초기화

        Args:
            max_jitter_minutes: 최대 jitter 시간 (분 단위, 1-120 범위)

        Raises:
            ValueError: max_jitter_minutes가 1-120 범위 밖일 때
        """
        if not (1 <= max_jitter_minutes <= 120):
            raise ValueError(
                f"max_jitter_minutes는 1-120 범위여야 합니다 (현재: {max_jitter_minutes})"
            )

        self.max_jitter_minutes = max_jitter_minutes

    def wait_with_jitter(self) -> None:
        """
        랜덤 jitter 시간만큼 안전하게 대기

        - 목표 시간 = 현재 시간 + random(0, max_jitter_minutes)
        - 1초마다 폴링하여 목표 시간 도달 확인
        - 시작/종료 시점만 로그 출력

        Raises:
            KeyboardInterrupt: 사용자가 중단한 경우 (전파)
        """
        # 1. 랜덤 jitter 시간 계산 (0 ~ max_jitter_minutes)
        jitter_minutes = randint(0, self.max_jitter_minutes)
        target_time = datetime.now() + timedelta(minutes=jitter_minutes)

        # 2. 시작 로그 출력
        timestamp = self._timestamp()
        target_str = target_time.strftime('%H:%M:%S')
        print(
            f"[{timestamp}] Jitter 대기 시작 (목표: {target_str}, 지연: +{jitter_minutes}분)",
            flush=True
        )

        # 3. jitter가 0이면 즉시 반환
        if jitter_minutes == 0:
            print(f"[{timestamp}] Jitter가 0분입니다. 즉시 실행합니다.", flush=True)
            return

        # 4. 폴링 루프 (조용히 대기)
        try:
            while datetime.now() < target_time:
                sleep(self.POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            timestamp = self._timestamp()
            print(f"\n[{timestamp}] Jitter 대기가 중단되었습니다.", flush=True)
            raise

        # 5. 완료 로그
        timestamp = self._timestamp()
        print(f"[{timestamp}] Jitter 대기 완료. 쿠폰 발급을 시작합니다.", flush=True)

    @staticmethod
    def _timestamp() -> str:
        """현재 시각 문자열 반환 (YYYY-MM-DD HH:MM:SS 형식)"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
