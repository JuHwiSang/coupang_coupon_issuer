"""
Unit tests for jitter.py - JitterScheduler

ADR 011 참조: docs/adr/011-jitter-thundering-herd.md

주의: sleep과 randint를 모킹할 때 모듈 전체가 아닌 특정 함수만 패치합니다.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from coupang_coupon_issuer.jitter import JitterScheduler


@pytest.mark.unit
class TestJitterSchedulerInit:
    """Test JitterScheduler initialization"""

    def test_init_valid_range_min(self):
        """Accept minimum valid jitter_max (1 minute)"""
        scheduler = JitterScheduler(max_jitter_minutes=1)
        assert scheduler.max_jitter_minutes == 1

    def test_init_valid_range_mid(self):
        """Accept middle range jitter_max (60 minutes)"""
        scheduler = JitterScheduler(max_jitter_minutes=60)
        assert scheduler.max_jitter_minutes == 60

    def test_init_valid_range_max(self):
        """Accept maximum valid jitter_max (120 minutes)"""
        scheduler = JitterScheduler(max_jitter_minutes=120)
        assert scheduler.max_jitter_minutes == 120

    def test_init_invalid_zero(self):
        """Reject jitter_max = 0"""
        with pytest.raises(ValueError) as exc_info:
            JitterScheduler(max_jitter_minutes=0)

        assert "1-120 범위여야 합니다" in str(exc_info.value)
        assert "0" in str(exc_info.value)

    def test_init_invalid_negative(self):
        """Reject negative jitter_max"""
        with pytest.raises(ValueError) as exc_info:
            JitterScheduler(max_jitter_minutes=-10)

        assert "1-120 범위여야 합니다" in str(exc_info.value)

    def test_init_invalid_too_high(self):
        """Reject jitter_max > 120"""
        with pytest.raises(ValueError) as exc_info:
            JitterScheduler(max_jitter_minutes=121)

        assert "1-120 범위여야 합니다" in str(exc_info.value)
        assert "121" in str(exc_info.value)


@pytest.mark.unit
class TestJitterWaitZeroJitter:
    """Test wait_with_jitter() with zero jitter (no sleep)"""

    @patch('coupang_coupon_issuer.jitter.randint')
    def test_wait_zero_jitter_immediate_return(self, mock_randint, caplog):
        """Immediate return when jitter is 0 minutes (no sleep needed)"""
        mock_randint.return_value = 0

        scheduler = JitterScheduler(max_jitter_minutes=60)
        scheduler.wait_with_jitter()

        # Check log output
        assert "Jitter가 0분입니다" in caplog.text
        assert "즉시 실행" in caplog.text
        assert "Jitter 대기 시작" in caplog.text


@pytest.mark.unit
class TestJitterWaitWithMocking:
    """Test wait_with_jitter() with careful mocking to avoid infinite loops"""

    @patch('coupang_coupon_issuer.jitter.randint')
    @patch('coupang_coupon_issuer.jitter.sleep')
    @patch('coupang_coupon_issuer.jitter.datetime')
    def test_wait_exits_when_target_reached(
        self, mock_datetime, mock_sleep, mock_randint, caplog
    ):
        """Polling loop exits when target time is reached"""
        mock_randint.return_value = 1  # 1 minute jitter

        start_time = datetime(2024, 1, 1, 0, 0, 0)
        target_time = start_time + timedelta(minutes=1)

        # Simulate time progression: 시작 -> 2회 루프 -> 목표 도달
        call_count = [0]

        def mock_now():
            call_count[0] += 1
            if call_count[0] <= 3:  # target_time calc + 2 log timestamps
                return start_time
            elif call_count[0] <= 5:  # 2 loop iterations
                return start_time + timedelta(seconds=call_count[0] - 3)
            else:  # exit condition
                return target_time + timedelta(seconds=1)

        mock_datetime.now.side_effect = mock_now

        scheduler = JitterScheduler(max_jitter_minutes=60)
        scheduler.wait_with_jitter()

        # Should have slept at least once
        assert mock_sleep.call_count >= 1

        # Verify sleep(1) was called
        for call in mock_sleep.call_args_list:
            assert call[0][0] == 1

        # Check logs
        assert "Jitter 대기 시작" in caplog.text
        assert "Jitter 대기 완료" in caplog.text

    @patch('coupang_coupon_issuer.jitter.randint')
    @patch('coupang_coupon_issuer.jitter.sleep')
    def test_wait_keyboard_interrupt_handled(self, mock_sleep, mock_randint, caplog):
        """Handle KeyboardInterrupt gracefully during sleep"""
        mock_randint.return_value = 5  # 5 minutes
        mock_sleep.side_effect = KeyboardInterrupt  # Interrupt on first sleep

        scheduler = JitterScheduler(max_jitter_minutes=60)

        with pytest.raises(KeyboardInterrupt):
            scheduler.wait_with_jitter()

        # Check interrupt message
        assert "중단되었습니다" in caplog.text

    @patch('coupang_coupon_issuer.jitter.randint')
    @patch('coupang_coupon_issuer.jitter.sleep')
    @patch('coupang_coupon_issuer.jitter.datetime')
    def test_wait_random_range_called_correctly(
        self, mock_datetime, mock_sleep, mock_randint
    ):
        """Verify randint called with correct range (0, max)"""
        mock_randint.return_value = 15

        # Mock datetime to exit immediately (target already passed)
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        target_time = start_time + timedelta(minutes=15)

        # Sequence: calculation, logs, exit (already past target)
        mock_datetime.now.side_effect = [
            start_time,  # target_time calculation
            start_time,  # start log timestamp
            start_time,  # start log timestamp again
            target_time + timedelta(seconds=1),  # loop check (exit immediately)
            target_time + timedelta(seconds=1),  # completion log
        ]

        scheduler = JitterScheduler(max_jitter_minutes=30)
        scheduler.wait_with_jitter()

        # Verify randint called with (0, 30)
        mock_randint.assert_called_once_with(0, 30)

    @patch('coupang_coupon_issuer.jitter.randint')
    @patch('coupang_coupon_issuer.jitter.sleep')
    @patch('coupang_coupon_issuer.jitter.datetime')
    def test_wait_logs_start_and_completion(
        self, mock_datetime, mock_sleep, mock_randint, caplog
    ):
        """Verify start and completion logs are printed"""
        mock_randint.return_value = 5

        start_time = datetime(2024, 12, 20, 0, 0, 0)
        target_time = start_time + timedelta(minutes=5)

        # Exit immediately (already past target)
        mock_datetime.now.side_effect = [
            start_time,  # calculation
            start_time,  # log timestamp
            start_time,  # log timestamp again
            target_time + timedelta(seconds=1),  # exit
            target_time + timedelta(seconds=1),  # completion log
        ]

        scheduler = JitterScheduler(max_jitter_minutes=60)
        scheduler.wait_with_jitter()

        # Check start log
        assert "Jitter 대기 시작" in caplog.text
        assert "목표:" in caplog.text
        assert "지연: +5분" in caplog.text

        # Check completion log
        assert "Jitter 대기 완료" in caplog.text
        assert "쿠폰 발급을 시작합니다" in caplog.text

    @patch('coupang_coupon_issuer.jitter.randint')
    @patch('coupang_coupon_issuer.jitter.sleep')
    @patch('coupang_coupon_issuer.jitter.datetime')
    def test_wait_max_jitter_boundary_120(
        self, mock_datetime, mock_sleep, mock_randint
    ):
        """Test with maximum jitter value (120 minutes)"""
        mock_randint.return_value = 120

        start_time = datetime(2024, 1, 1, 0, 0, 0)
        target_time = start_time + timedelta(minutes=120)

        # Exit immediately (already past target)
        mock_datetime.now.side_effect = [
            start_time,  # calculation
            start_time,  # log timestamp
            start_time,  # log timestamp again
            target_time + timedelta(seconds=1),  # exit
            target_time + timedelta(seconds=1),  # completion log
        ]

        scheduler = JitterScheduler(max_jitter_minutes=120)
        scheduler.wait_with_jitter()

        # Verify randint called with (0, 120)
        mock_randint.assert_called_once_with(0, 120)
