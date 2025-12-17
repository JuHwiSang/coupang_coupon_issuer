"""
Unit tests for main.py - CLI commands
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from openpyxl import Workbook

# Add project root to sys.path to import main module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import main


@pytest.mark.unit
class TestApplyCommand:
    """Test 'apply' command"""

    def test_apply_valid_excel(self, tmp_path, mocker):
        """Valid Excel file should pass validation and be copied"""
        excel_file = tmp_path / "valid.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "발급개수"])
        ws.append(["테스트쿠폰", "즉시할인", 30, "RATE", 50])
        wb.save(excel_file)

        # Mock file operations
        mock_copy = mocker.patch('main.shutil.copy2')
        mock_mkdir = mocker.patch('main.Path.mkdir')
        mock_chmod = mocker.patch('main.Path.chmod')

        # Create args object
        args = MagicMock()
        args.excel_file = str(excel_file)

        # Run command
        main.cmd_apply(args)

        # Verify copy was called
        assert mock_copy.call_count == 1

    def test_apply_file_not_found(self, tmp_path, capsys):
        """Non-existent file should error"""
        args = MagicMock()
        args.excel_file = str(tmp_path / "nonexistent.xlsx")

        with pytest.raises(SystemExit):
            main.cmd_apply(args)

        captured = capsys.readouterr()
        assert "ERROR: 파일이 존재하지 않습니다" in captured.out

    def test_apply_missing_columns(self, tmp_path, capsys):
        """Excel missing required columns should error"""
        excel_file = tmp_path / "missing_cols.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입"])  # Missing 3 columns
        ws.append(["쿠폰1", "즉시할인"])
        wb.save(excel_file)

        args = MagicMock()
        args.excel_file = str(excel_file)

        with pytest.raises(SystemExit):
            main.cmd_apply(args)

        captured = capsys.readouterr()
        assert "ERROR: 검증 실패" in captured.out
        assert "필수 컬럼 누락" in captured.out

    def test_apply_invalid_rate_range(self, tmp_path, capsys):
        """RATE out of 1-99 range should error"""
        excel_file = tmp_path / "invalid_rate.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "발급개수"])
        ws.append(["쿠폰1", "즉시할인", 30, "RATE", 100])  # 100% invalid
        wb.save(excel_file)

        args = MagicMock()
        args.excel_file = str(excel_file)

        with pytest.raises(SystemExit):
            main.cmd_apply(args)

        captured = capsys.readouterr()
        assert "ERROR: 검증 실패" in captured.out
        assert "RATE 할인율은 1~99 사이여야 합니다" in captured.out

    def test_apply_invalid_price_units(self, tmp_path, capsys):
        """PRICE not in 10-won units should error"""
        excel_file = tmp_path / "invalid_price.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "발급개수"])
        ws.append(["쿠폰1", "즉시할인", 30, "PRICE", 15])  # Not 10-won unit
        wb.save(excel_file)

        args = MagicMock()
        args.excel_file = str(excel_file)

        with pytest.raises(SystemExit):
            main.cmd_apply(args)

        captured = capsys.readouterr()
        assert "ERROR: 검증 실패" in captured.out
        assert "PRICE 할인금액은 10원 단위여야 합니다" in captured.out


@pytest.mark.unit
class TestIssueCommand:
    """Test 'issue' command"""

    def test_issue_loads_credentials_from_file(self, mocker):
        """Issue command should load credentials from file"""
        mock_load_env = mocker.patch('main.CredentialManager.load_credentials_to_env')
        mock_issuer_class = mocker.patch('main.CouponIssuer')
        mock_issuer = MagicMock()
        mock_issuer_class.return_value = mock_issuer

        main.cmd_issue()

        # Verify credentials were loaded
        mock_load_env.assert_called_once()

        # Verify issuer was instantiated and issue() called
        mock_issuer_class.assert_called_once()
        mock_issuer.issue.assert_called_once()

    def test_issue_handles_credential_error(self, mocker, capsys):
        """Issue should exit if credentials can't be loaded"""
        mocker.patch('main.CredentialManager.load_credentials_to_env', side_effect=FileNotFoundError("No file"))

        with pytest.raises(SystemExit):
            main.cmd_issue()

        captured = capsys.readouterr()
        assert "ERROR: API 키 로드 실패" in captured.out

    def test_issue_handles_issuer_error(self, mocker, capsys):
        """Issue should exit if issuer.issue() fails"""
        mocker.patch('main.CredentialManager.load_credentials_to_env')
        mock_issuer_class = mocker.patch('main.CouponIssuer')
        mock_issuer = MagicMock()
        mock_issuer.issue.side_effect = Exception("Issuer failed")
        mock_issuer_class.return_value = mock_issuer

        with pytest.raises(SystemExit):
            main.cmd_issue()

        captured = capsys.readouterr()
        assert "ERROR: 쿠폰 발급 실패" in captured.out


@pytest.mark.unit
class TestServeCommand:
    """Test 'serve' command"""

    def test_serve_starts_scheduler(self, mocker):
        """Serve should start the MidnightScheduler"""
        mock_load_env = mocker.patch('main.CredentialManager.load_credentials_to_env')
        mock_scheduler_class = mocker.patch('main.MidnightScheduler')
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler

        # Mock CouponIssuer to avoid real instantiation
        mocker.patch('main.CouponIssuer')

        main.cmd_serve()

        # Verify scheduler was created and run() called
        mock_scheduler_class.assert_called_once()
        mock_scheduler.run.assert_called_once()

    def test_serve_handles_credential_error(self, mocker, capsys):
        """Serve should exit if credentials can't be loaded"""
        mocker.patch('main.CredentialManager.load_credentials_to_env', side_effect=Exception("Failed"))

        with pytest.raises(SystemExit):
            main.cmd_serve()

        captured = capsys.readouterr()
        assert "ERROR: API 키 로드 실패" in captured.out


@pytest.mark.unit
class TestInstallCommand:
    """Test 'install' command"""

    def test_install_requires_all_4_params(self, capsys):
        """Install should require all 4 parameters"""
        args = MagicMock()
        args.access_key = "test"
        args.secret_key = "test"
        args.user_id = None  # Missing
        args.vendor_id = "test"

        with pytest.raises(SystemExit):
            main.cmd_install(args)

        captured = capsys.readouterr()
        assert "ERROR: 모든 인자가 필요합니다" in captured.out
        assert "--user-id" in captured.out

    def test_install_calls_systemd_service(self, mocker):
        """Install should call SystemdService.install with correct args"""
        mock_install = mocker.patch('main.SystemdService.install')

        args = MagicMock()
        args.access_key = "access-key"
        args.secret_key = "secret-key"
        args.user_id = "user-id"
        args.vendor_id = "vendor-id"

        main.cmd_install(args)

        mock_install.assert_called_once_with("access-key", "secret-key", "user-id", "vendor-id")


@pytest.mark.unit
class TestUninstallCommand:
    """Test 'uninstall' command"""

    def test_uninstall_calls_systemd_service(self, mocker):
        """Uninstall should call SystemdService.uninstall"""
        mock_uninstall = mocker.patch('main.SystemdService.uninstall')

        main.cmd_uninstall()

        mock_uninstall.assert_called_once()


@pytest.mark.unit
class TestMainFunction:
    """Test main() entry point and argument parsing"""

    def test_main_no_arguments_shows_help(self, mocker, capsys):
        """Running without arguments should show help and exit"""
        mocker.patch('sys.argv', ['main.py'])

        with pytest.raises(SystemExit):
            main.main()

        captured = capsys.readouterr()
        assert "usage:" in captured.out or "사용 예시:" in captured.out

    def test_main_invalid_command(self, mocker, capsys):
        """Invalid command should show error and help"""
        mocker.patch('sys.argv', ['main.py', 'invalid-cmd'])

        with pytest.raises(SystemExit):
            main.main()

        # argparse will handle unknown subcommand and show error

    def test_main_apply_command_dispatched(self, mocker):
        """Apply command should be dispatched correctly"""
        mock_cmd_apply = mocker.patch('main.cmd_apply')

        # Create valid Excel file
        tmp_path = Path("test.xlsx")
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "발급개수"])
        ws.append(["쿠폰", "즉시할인", 30, "RATE", 50])
        wb.save(tmp_path)

        try:
            mocker.patch('sys.argv', ['main.py', 'apply', str(tmp_path)])
            main.main()

            # Verify cmd_apply was called
            assert mock_cmd_apply.call_count == 1
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_main_issue_command_dispatched(self, mocker):
        """Issue command should be dispatched correctly"""
        mock_cmd_issue = mocker.patch('main.cmd_issue')

        mocker.patch('sys.argv', ['main.py', 'issue'])
        main.main()

        mock_cmd_issue.assert_called_once()

    def test_main_serve_command_dispatched(self, mocker):
        """Serve command should be dispatched correctly"""
        mock_cmd_serve = mocker.patch('main.cmd_serve')

        mocker.patch('sys.argv', ['main.py', 'serve'])
        main.main()

        mock_cmd_serve.assert_called_once()

    def test_main_install_command_dispatched(self, mocker):
        """Install command should be dispatched correctly"""
        mock_cmd_install = mocker.patch('main.cmd_install')

        mocker.patch('sys.argv', [
            'main.py', 'install',
            '--access-key', 'test-access',
            '--secret-key', 'test-secret',
            '--user-id', 'test-user',
            '--vendor-id', 'test-vendor'
        ])
        main.main()

        assert mock_cmd_install.call_count == 1

    def test_main_uninstall_command_dispatched(self, mocker):
        """Uninstall command should be dispatched correctly"""
        mock_cmd_uninstall = mocker.patch('main.cmd_uninstall')

        mocker.patch('sys.argv', ['main.py', 'uninstall'])
        main.main()

        mock_cmd_uninstall.assert_called_once()
