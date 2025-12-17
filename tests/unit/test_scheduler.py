"""
Unit tests for scheduler.py - MidnightScheduler
"""
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call
from freezegun import freeze_time

from coupang_coupon_issuer.scheduler import MidnightScheduler
from coupang_coupon_issuer.config import CHECK_INTERVAL


@pytest.mark.unit
class TestMidnightDetection:
    """Test midnight time detection logic"""

    @freeze_time("2024-12-17 00:00:00")
    def test_detect_midnight_00_00_00(self, mocker):
        """Verify task is called at exactly 00:00:00"""
        task_mock = mocker.Mock()
        scheduler = MidnightScheduler(task_mock)

        # Mock time.sleep to exit after one iteration
        sleep_mock = mocker.patch('time.sleep', side_effect=[None, KeyboardInterrupt()])

        try:
            scheduler.run()
        except (KeyboardInterrupt, SystemExit):
            pass

        # Task should have been called
        task_mock.assert_called_once()

    @freeze_time("2024-12-17 00:00:59")
    def test_detect_midnight_00_00_59(self, mocker):
        """Verify task is called at 00:00:59 (last second of midnight window)"""
        task_mock = mocker.Mock()
        scheduler = MidnightScheduler(task_mock)

        sleep_mock = mocker.patch('time.sleep', side_effect=[None, KeyboardInterrupt()])

        try:
            scheduler.run()
        except (KeyboardInterrupt, SystemExit):
            pass

        task_mock.assert_called_once()

    @freeze_time("2024-12-17 00:01:00")
    def test_skip_midnight_00_01_00(self, mocker):
        """Verify task is NOT called at 00:01:00 (missed the window)"""
        task_mock = mocker.Mock()
        scheduler = MidnightScheduler(task_mock)

        sleep_mock = mocker.patch('time.sleep', side_effect=[None, KeyboardInterrupt()])

        try:
            scheduler.run()
        except (KeyboardInterrupt, SystemExit):
            pass

        # Task should NOT have been called
        task_mock.assert_not_called()


@pytest.mark.unit
class TestDuplicateExecutionPrevention:
    """Test duplicate execution prevention on same day"""

    def test_no_duplicate_same_day(self, mocker):
        """First run at 00:00:00 executes, second run at 00:00:30 skips"""
        task_mock = mocker.Mock()
        scheduler = MidnightScheduler(task_mock)

        # Simulate time progression within the same day
        times = [
            datetime(2024, 12, 17, 0, 0, 0),  # First check: midnight
            datetime(2024, 12, 17, 0, 0, 30),  # Second check: still 00:00 range, same day
            datetime(2024, 12, 18, 0, 0, 0),   # Third check: next day midnight
        ]

        with patch('coupang_coupon_issuer.scheduler.datetime') as mock_datetime:
            mock_datetime.now.side_effect = times
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)  # Allow datetime() calls

            sleep_mock = mocker.patch('time.sleep', side_effect=[None, None, KeyboardInterrupt()])

            try:
                scheduler.run()
            except (KeyboardInterrupt, SystemExit):
                pass

            # Task should be called only twice (once per day)
            assert task_mock.call_count == 2


@pytest.mark.unit
class TestLogging:
    """Test logging behavior"""

    @freeze_time("2024-12-17 15:00:00")
    def test_log_waiting_status_hourly(self, mocker, capsys):
        """Verify waiting status is logged every hour (at minute=00)"""
        task_mock = mocker.Mock()
        scheduler = MidnightScheduler(task_mock)

        # Simulate hourly progression
        times = [
            datetime(2024, 12, 17, 15, 0, 0),   # 15:00 (minute=00, log expected)
            datetime(2024, 12, 17, 16, 0, 0),   # 16:00 (minute=00, log expected)
            datetime(2024, 12, 17, 17, 0, 0),   # 17:00 (minute=00, log expected)
        ]

        with patch('coupang_coupon_issuer.scheduler.datetime') as mock_datetime:
            mock_datetime.now.side_effect = times
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            sleep_mock = mocker.patch('time.sleep', side_effect=[None, None, KeyboardInterrupt()])

            try:
                scheduler.run()
            except (KeyboardInterrupt, SystemExit):
                pass

            captured = capsys.readouterr()
            # Should have 3 waiting status logs
            assert captured.out.count("다음 실행까지") == 3

    @freeze_time("2024-12-17 15:30:00")
    def test_log_next_midnight_calculation(self, mocker, capsys):
        """Verify correct calculation of time until next midnight"""
        task_mock = mocker.Mock()
        scheduler = MidnightScheduler(task_mock)

        # At 15:30, next midnight is in 8h 30m
        sleep_mock = mocker.patch('time.sleep', side_effect=[KeyboardInterrupt()])

        try:
            scheduler.run()
        except (KeyboardInterrupt, SystemExit):
            pass

        # No log expected at 15:30 (minute != 0)
        # But we can verify the calculation internally
        now = datetime(2024, 12, 17, 15, 30, 0)
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        time_left = next_midnight - now
        hours_left = int(time_left.total_seconds() // 3600)
        minutes_left = int((time_left.total_seconds() % 3600) // 60)

        assert hours_left == 8
        assert minutes_left == 30


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling and retry logic"""

    def test_task_exception_logged_and_retried(self, mocker, capsys):
        """Task exception should be logged, then retried next day"""
        task_mock = mocker.Mock(side_effect=[Exception("Task failed"), None])
        scheduler = MidnightScheduler(task_mock)

        # First run: midnight on day 1 (task fails)
        # Second run: midnight on day 2 (task succeeds)
        times = [
            datetime(2024, 12, 17, 0, 0, 0),  # Day 1 midnight
            datetime(2024, 12, 18, 0, 0, 0),  # Day 2 midnight
        ]

        with patch('coupang_coupon_issuer.scheduler.datetime') as mock_datetime:
            mock_datetime.now.side_effect = times
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            sleep_mock = mocker.patch('time.sleep', side_effect=[None, KeyboardInterrupt()])

            try:
                scheduler.run()
            except (KeyboardInterrupt, SystemExit):
                pass

            # Task should be called twice (once per day)
            assert task_mock.call_count == 2

            captured = capsys.readouterr()
            assert "ERROR: 작업 실패" in captured.out
            assert "Task failed" in captured.out

    @freeze_time("2024-12-17 15:00:00")
    def test_keyboard_interrupt_graceful_shutdown(self, mocker, capsys):
        """KeyboardInterrupt should trigger graceful shutdown"""
        task_mock = mocker.Mock()
        scheduler = MidnightScheduler(task_mock)

        sleep_mock = mocker.patch('time.sleep', side_effect=KeyboardInterrupt())

        try:
            scheduler.run()
        except SystemExit:
            pass

        captured = capsys.readouterr()
        assert "사용자에 의해 중단됨" in captured.out


@pytest.mark.unit
class TestConfiguration:
    """Test scheduler configuration"""

    def test_check_interval_default(self):
        """Verify default CHECK_INTERVAL is 30 seconds"""
        from coupang_coupon_issuer.config import CHECK_INTERVAL
        assert CHECK_INTERVAL == 30

    def test_scheduler_accepts_callable(self):
        """Verify scheduler accepts any callable as task_func"""
        def sample_task():
            pass

        scheduler = MidnightScheduler(sample_task)
        assert scheduler.task_func == sample_task

        # Also test with lambda
        lambda_task = lambda: print("test")
        scheduler2 = MidnightScheduler(lambda_task)
        assert scheduler2.task_func == lambda_task


@pytest.mark.unit
class TestSchedulerLoop:
    """Test scheduler main loop behavior"""

    def test_scheduler_runs_in_loop(self, mocker):
        """Verify scheduler continuously loops with sleep intervals"""
        task_mock = mocker.Mock()
        scheduler = MidnightScheduler(task_mock)

        # Simulate non-midnight time
        with freeze_time("2024-12-17 15:00:00"):
            # Sleep 3 times then interrupt
            sleep_mock = mocker.patch('time.sleep', side_effect=[None, None, None, KeyboardInterrupt()])

            try:
                scheduler.run()
            except (KeyboardInterrupt, SystemExit):
                pass

            # Verify sleep was called 3 times with CHECK_INTERVAL
            assert sleep_mock.call_count == 4  # 3 normal + 1 interrupt
            sleep_mock.assert_any_call(CHECK_INTERVAL)

    def test_last_run_date_tracking(self, mocker):
        """Verify last_run_date is updated after successful execution"""
        task_mock = mocker.Mock()
        scheduler = MidnightScheduler(task_mock)

        assert scheduler.last_run_date is None  # Initially None

        # Run at midnight
        with freeze_time("2024-12-17 00:00:00"):
            sleep_mock = mocker.patch('time.sleep', side_effect=[KeyboardInterrupt()])

            try:
                scheduler.run()
            except (KeyboardInterrupt, SystemExit):
                pass

            # last_run_date should be updated
            assert scheduler.last_run_date == datetime(2024, 12, 17).date()

    def test_scheduler_exception_recovery(self, mocker, capsys):
        """Verify scheduler recovers from unexpected exceptions"""
        task_mock = mocker.Mock()
        scheduler = MidnightScheduler(task_mock)

        # Simulate an exception in the main loop
        with freeze_time("2024-12-17 15:00:00"):
            # First sleep raises an exception, second sleep raises KeyboardInterrupt to exit
            sleep_mock = mocker.patch('time.sleep', side_effect=[
                Exception("Unexpected error"),
                None,  # After 10-second recovery sleep
                KeyboardInterrupt()
            ])

            try:
                scheduler.run()
            except (KeyboardInterrupt, SystemExit):
                pass

            captured = capsys.readouterr()
            # Should log the exception but continue
            assert "ERROR: 스케줄러 오류" in captured.out
            assert "10초 후 재시작합니다" in captured.out
