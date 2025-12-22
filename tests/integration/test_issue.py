"""
Integration tests for issue functionality.

Tests the complete issue flow with mocked external dependencies:
- Coupang API calls are mocked
- Config loading is mocked
- Excel file is a real test file
- Internal modules (CouponIssuer, etc.) use real implementations

This tests the integration between internal modules without external API calls.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, Mock
import argparse

# Add project root to path to import main
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import main


@pytest.mark.integration
class TestIssueIntegration:
    """Integration tests for issue command with mocked external dependencies"""

    def test_issue_instant_coupon_success(self, test_base_dir, test_excel_file, mock_config, mock_coupang_api, capsys):
        """Test successful instant coupon issuance with mocked API"""
        # Create args object
        args = argparse.Namespace(
            directory=str(test_base_dir),
            jitter_max=None
        )
        
        # Run issue command
        main.cmd_issue(args)
        
        # Verify API was called
        assert mock_coupang_api.create_instant_coupon.called
        assert mock_coupang_api.get_instant_coupon_status.called
        assert mock_coupang_api.apply_instant_coupon.called
        
        # Verify output contains success message
        captured = capsys.readouterr()
        assert "쿠폰 발급 시작" in captured.out
        assert "쿠폰 발급 완료" in captured.out
        assert "성공: 3" in captured.out

    def test_issue_download_coupon_success(self, test_base_dir, test_excel_file, mock_config, mock_coupang_api, capsys):
        """Test successful download coupon issuance with mocked API"""
        args = argparse.Namespace(
            directory=str(test_base_dir),
            jitter_max=None
        )
        
        main.cmd_issue(args)
        
        # Verify download coupon API was called
        assert mock_coupang_api.create_download_coupon.called
        assert mock_coupang_api.apply_download_coupon.called
        
        # Verify output
        captured = capsys.readouterr()
        assert "쿠폰 발급 시작" in captured.out
        assert "성공: 3" in captured.out

    def test_issue_mixed_coupons(self, test_base_dir, test_excel_file, mock_config, mock_coupang_api, capsys):
        """Test issuing multiple coupon types (instant + download)"""
        args = argparse.Namespace(
            directory=str(test_base_dir),
            jitter_max=None
        )
        
        main.cmd_issue(args)
        
        # Verify both API methods were called
        assert mock_coupang_api.create_instant_coupon.called
        assert mock_coupang_api.create_download_coupon.called
        
        # Check call counts (1 instant, 2 download from test Excel)
        assert mock_coupang_api.create_instant_coupon.call_count == 1
        assert mock_coupang_api.create_download_coupon.call_count == 2

    def test_issue_api_error_handling(self, test_base_dir, test_excel_file, mock_config, mock_coupang_api_with_error, capsys):
        """Test that API errors are handled gracefully"""
        args = argparse.Namespace(
            directory=str(test_base_dir),
            jitter_max=None
        )
        
        # This should not raise an exception, but log errors
        main.cmd_issue(args)
        
        # Verify error was logged
        captured = capsys.readouterr()
        # The issuer should continue even if some coupons fail
        assert "쿠폰 발급 시작" in captured.out

    def test_issue_with_jitter(self, test_base_dir, test_excel_file, mock_config, mock_coupang_api, capsys):
        """Test issue command with jitter enabled"""
        args = argparse.Namespace(
            directory=str(test_base_dir),
            jitter_max=1  # Very short jitter for testing (1 minute max)
        )
        
        # Mock the jitter scheduler to avoid actual waiting
        with patch('coupang_coupon_issuer.jitter.JitterScheduler') as MockJitter:
            mock_scheduler = Mock()
            MockJitter.return_value = mock_scheduler
            
            main.cmd_issue(args)
            
            # Verify jitter was initialized
            MockJitter.assert_called_once_with(max_jitter_minutes=1)
            mock_scheduler.wait_with_jitter.assert_called_once()
        
        # Verify coupons were issued after jitter
        assert mock_coupang_api.create_instant_coupon.called

    def test_issue_fails_without_config(self, test_base_dir, test_excel_file, capsys):
        """Test that issue fails gracefully when config is missing"""
        args = argparse.Namespace(
            directory=str(test_base_dir),
            jitter_max=None
        )
        
        # Don't mock config - let it fail naturally
        with pytest.raises(SystemExit) as exc_info:
            main.cmd_issue(args)
        
        # Should exit with error code
        assert exc_info.value.code == 1
        
        # Verify error message
        captured = capsys.readouterr()
        assert "ERROR" in captured.out
        assert "config.json" in captured.out or "설정" in captured.out

    def test_issue_fails_with_missing_excel(self, test_base_dir, mock_config, capsys):
        """Test that issue fails when Excel file is missing"""
        args = argparse.Namespace(
            directory=str(test_base_dir),
            jitter_max=None
        )
        
        # No Excel file created - should fail
        with pytest.raises(SystemExit) as exc_info:
            main.cmd_issue(args)
        
        # Should exit with error code
        assert exc_info.value.code == 1
        
        # Verify error message
        captured = capsys.readouterr()
        assert "ERROR" in captured.out
