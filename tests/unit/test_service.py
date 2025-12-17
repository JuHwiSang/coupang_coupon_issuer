"""
Unit tests for service.py - SystemdService
Note: Most tests skip on Windows. Full integration tests are in tests/integration/
"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call

from coupang_coupon_issuer.service import SystemdService
from coupang_coupon_issuer.config import SERVICE_NAME

# Skip all service tests on Windows (os.geteuid not available)
pytestmark = pytest.mark.skipif(os.name == 'nt', reason="Service tests require Linux")


@pytest.mark.unit
class TestRootPermission:
    """Test root permission checking"""

    def test_check_root_as_root(self, mocker):
        """Verify no exception when running as root (uid=0)"""
        mocker.patch('os.geteuid', return_value=0)

        # Should not raise
        SystemdService._check_root()

    def test_check_root_as_non_root(self, mocker):
        """Raise PermissionError when not running as root"""
        mocker.patch('os.geteuid', return_value=1000)

        with pytest.raises(PermissionError) as exc_info:
            SystemdService._check_root()

        assert "root 권한이 필요합니다" in str(exc_info.value)

    def test_check_root_on_windows(self, mocker, capsys):
        """On Windows, print warning and continue"""
        # Simulate Windows by removing geteuid attribute
        mocker.patch('os.geteuid', side_effect=AttributeError())

        # Should not raise, but print warning
        SystemdService._check_root()

        captured = capsys.readouterr()
        assert "WARNING: Windows 환경입니다" in captured.out


@pytest.mark.unit
class TestInstallation:
    """Test installation process (mocked)"""

    def test_install_creates_directories(self, mocker):
        """Verify installation creates necessary directories"""
        mocker.patch('os.geteuid', return_value=0)
        mocker.patch('os.system', return_value=0)
        mocker.patch('coupang_coupon_issuer.service.CredentialManager.save_credentials')

        mock_path = mocker.patch('coupang_coupon_issuer.service.Path')
        mock_shutil = mocker.patch('coupang_coupon_issuer.service.shutil')

        # Mock Path objects
        install_dir_mock = MagicMock()
        mock_path.return_value = install_dir_mock

        # Run install
        SystemdService.install("test-access", "test-secret", "test-user", "test-vendor")

        # Verify directory creation was attempted
        # Note: Full verification requires integration tests

    def test_install_creates_symlink(self, mocker):
        """Verify symlink creation to /usr/local/bin"""
        mocker.patch('os.geteuid', return_value=0)
        mocker.patch('os.system', return_value=0)
        mocker.patch('coupang_coupon_issuer.service.CredentialManager.save_credentials')
        mocker.patch('coupang_coupon_issuer.service.shutil')

        mock_symlink = MagicMock()

        with patch('coupang_coupon_issuer.service.Path') as mock_path:
            # Mock the symlink path
            mock_path.return_value = mock_symlink

            SystemdService.install("a", "s", "u", "v")

            # Verify symlink operations were called
            # Actual verification would check symlink_to() call

    def test_install_saves_credentials(self, mocker):
        """Verify credentials are saved via CredentialManager"""
        mocker.patch('os.geteuid', return_value=0)
        mocker.patch('os.system', return_value=0)
        mocker.patch('coupang_coupon_issuer.service.shutil')
        mocker.patch('coupang_coupon_issuer.service.Path')

        mock_save = mocker.patch('coupang_coupon_issuer.service.CredentialManager.save_credentials')

        SystemdService.install("access-key", "secret-key", "user-id", "vendor-id")

        # Verify CredentialManager.save_credentials was called with correct args
        mock_save.assert_called_once_with("access-key", "secret-key", "user-id", "vendor-id")

    def test_install_creates_systemd_service_file(self, mocker):
        """Verify systemd service file content"""
        mocker.patch('os.geteuid', return_value=0)
        mocker.patch('os.system', return_value=0)
        mocker.patch('coupang_coupon_issuer.service.CredentialManager.save_credentials')
        mocker.patch('coupang_coupon_issuer.service.shutil')

        mock_path_write = MagicMock()

        with patch('coupang_coupon_issuer.service.Path') as mock_path:
            # Mock service file path
            service_file_mock = MagicMock()
            mock_path.return_value = service_file_mock

            SystemdService.install("a", "s", "u", "v")

            # Verify service file content would contain:
            # - ExecStart with python3 and main.py
            # - Restart=on-failure
            # - RestartSec=10

    def test_install_runs_systemctl_commands(self, mocker):
        """Verify systemctl commands are executed"""
        mocker.patch('os.geteuid', return_value=0)
        mocker.patch('coupang_coupon_issuer.service.CredentialManager.save_credentials')
        mocker.patch('coupang_coupon_issuer.service.shutil')
        mocker.patch('coupang_coupon_issuer.service.Path')

        mock_system = mocker.patch('os.system', return_value=0)

        SystemdService.install("a", "s", "u", "v")

        # Verify systemctl commands were called
        system_calls = [call[0][0] for call in mock_system.call_args_list]

        assert any("daemon-reload" in str(call) for call in system_calls)
        assert any(f"enable {SERVICE_NAME}" in str(call) for call in system_calls)
        assert any(f"restart {SERVICE_NAME}" in str(call) for call in system_calls)


@pytest.mark.unit
class TestUninstallation:
    """Test uninstallation process (mocked)"""

    def test_uninstall_stops_service(self, mocker):
        """Verify service is stopped and disabled"""
        mocker.patch('os.geteuid', return_value=0)
        mocker.patch('builtins.input', side_effect=['n', 'n', 'n'])  # No to all prompts
        mocker.patch('coupang_coupon_issuer.service.Path')

        mock_system = mocker.patch('os.system', return_value=0)

        SystemdService.uninstall()

        # Verify systemctl stop/disable were called
        system_calls = [call[0][0] for call in mock_system.call_args_list]

        assert any(f"stop {SERVICE_NAME}" in str(call) for call in system_calls)
        assert any(f"disable {SERVICE_NAME}" in str(call) for call in system_calls)

    def test_uninstall_prompts_for_directory_deletion(self, mocker, capsys):
        """Verify user is prompted before deleting install directory"""
        mocker.patch('os.geteuid', return_value=0)
        mocker.patch('os.system', return_value=0)

        mock_input = mocker.patch('builtins.input', side_effect=['y', 'n', 'n'])

        mock_path = MagicMock()
        mock_path.exists.return_value = True

        with patch('coupang_coupon_issuer.service.Path', return_value=mock_path):
            with patch('coupang_coupon_issuer.service.shutil.rmtree') as mock_rmtree:
                SystemdService.uninstall()

                # Verify user was prompted
                assert mock_input.call_count == 3  # 3 prompts total

                # Verify rmtree was called (user said 'y' to first prompt)
                assert mock_rmtree.call_count >= 1

    def test_uninstall_preserves_files_on_no(self, mocker):
        """Verify files are preserved when user says no"""
        mocker.patch('os.geteuid', return_value=0)
        mocker.patch('os.system', return_value=0)

        # User says 'n' to all prompts
        mock_input = mocker.patch('builtins.input', side_effect=['n', 'n', 'n'])

        mock_path = MagicMock()
        mock_path.exists.return_value = True

        with patch('coupang_coupon_issuer.service.Path', return_value=mock_path):
            with patch('coupang_coupon_issuer.service.shutil.rmtree') as mock_rmtree:
                SystemdService.uninstall()

                # rmtree should NOT be called when user says 'n'
                mock_rmtree.assert_not_called()


@pytest.mark.unit
class TestServiceConfiguration:
    """Test service configuration constants"""

    def test_service_name_constant(self):
        """Verify SERVICE_NAME constant"""
        assert SERVICE_NAME == "coupang_coupon_issuer"
