"""
Unit tests for service.py - CrontabService

Tests the CrontabService class for cron-based scheduling.
Note: Most tests skip on Windows. Full integration tests are in tests/integration/
"""
import pytest
import os
from unittest.mock import MagicMock

from coupang_coupon_issuer.service import CrontabService
from coupang_coupon_issuer.config import SERVICE_NAME

# Skip all service tests on Windows (os.geteuid not available)
pytestmark = pytest.mark.skipif(os.name == 'nt', reason="Service tests require Linux")


@pytest.mark.unit
class TestRootPermission:
    """Test root permission checking"""

    def test_check_root_with_root_access(self, mocker):
        """Root access should pass without error"""
        mocker.patch('os.geteuid', return_value=0)

        # Should not raise
        CrontabService._check_root()

    def test_check_root_without_root_access(self, mocker):
        """Non-root should raise PermissionError"""
        mocker.patch('os.geteuid', return_value=1000)
        mocker.patch('sys.argv', ['main.py', 'install'])

        with pytest.raises(PermissionError) as exc_info:
            CrontabService._check_root()

        assert "root 권한이 필요합니다" in str(exc_info.value)
        assert "sudo" in str(exc_info.value)


@pytest.mark.unit
class TestCronDetection:
    """Test cron installation detection"""

    def test_detect_cron_when_installed(self, mocker):
        """Should return 'cron' when crontab exists"""
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(returncode=0)

        result = CrontabService._detect_cron_system()

        assert result == "cron"
        mock_run.assert_called_once_with(
            ["which", "crontab"],
            capture_output=True,
            text=True
        )

    def test_detect_cron_when_not_installed(self, mocker):
        """Should return None when crontab doesn't exist"""
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(returncode=1)

        result = CrontabService._detect_cron_system()

        assert result is None


@pytest.mark.unit
class TestPackageManagerDetection:
    """Test package manager detection"""

    def test_detect_apt(self, mocker):
        """Should detect apt-get (Ubuntu/Debian)"""
        mocker.patch('shutil.which', side_effect=lambda x: "/usr/bin/apt-get" if x == "apt-get" else None)

        result = CrontabService._get_package_manager()

        assert result == "apt"

    def test_detect_dnf(self, mocker):
        """Should detect dnf (RHEL 8+)"""
        mocker.patch('shutil.which', side_effect=lambda x: "/usr/bin/dnf" if x == "dnf" else None)

        result = CrontabService._get_package_manager()

        assert result == "dnf"

    def test_detect_yum(self, mocker):
        """Should detect yum (RHEL 7)"""
        mocker.patch('shutil.which', side_effect=lambda x: "/usr/bin/yum" if x == "yum" else None)

        result = CrontabService._get_package_manager()

        assert result == "yum"

    def test_detect_unsupported(self, mocker):
        """Should return None for unsupported systems"""
        mocker.patch('shutil.which', return_value=None)

        result = CrontabService._get_package_manager()

        assert result is None


@pytest.mark.unit
class TestCronInstallation:
    """Test cron installation"""

    def test_install_cron_on_ubuntu(self, mocker):
        """Should install cron using apt on Ubuntu/Debian"""
        mocker.patch.object(CrontabService, '_get_package_manager', return_value="apt")
        mock_system = mocker.patch('os.system', return_value=0)

        CrontabService._install_cron()

        # Verify apt commands were called
        assert mock_system.call_count == 2
        calls = [str(call) for call in mock_system.call_args_list]
        assert any("apt-get update" in str(c) for c in calls)
        assert any("apt-get install" in str(c) and "cron" in str(c) for c in calls)

    def test_install_cron_on_rhel8(self, mocker):
        """Should install cron using dnf on RHEL 8+"""
        mocker.patch.object(CrontabService, '_get_package_manager', return_value="dnf")
        mock_system = mocker.patch('os.system', return_value=0)

        CrontabService._install_cron()

        mock_system.assert_called_once()
        assert "dnf install" in str(mock_system.call_args)
        assert "cronie" in str(mock_system.call_args)

    def test_install_cron_on_unsupported_system(self, mocker):
        """Should raise RuntimeError on unsupported systems"""
        mocker.patch.object(CrontabService, '_get_package_manager', return_value=None)

        with pytest.raises(RuntimeError) as exc_info:
            CrontabService._install_cron()

        assert "지원하지 않는 배포판" in str(exc_info.value)

    def test_install_cron_failure(self, mocker):
        """Should raise RuntimeError when installation fails"""
        mocker.patch.object(CrontabService, '_get_package_manager', return_value="apt")
        mocker.patch('os.system', return_value=1)  # Non-zero exit code

        with pytest.raises(RuntimeError) as exc_info:
            CrontabService._install_cron()

        assert "설치 실패" in str(exc_info.value)


@pytest.mark.unit
class TestCronServiceEnable:
    """Test cron service enablement"""

    def test_enable_with_systemctl(self, mocker):
        """Should use systemctl when available"""
        mocker.patch('shutil.which', side_effect=lambda x: "/usr/bin/systemctl" if x == "systemctl" else None)
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(returncode=0, stdout="cron.service")
        mock_system = mocker.patch('os.system', return_value=0)

        CrontabService._enable_cron_service()

        # Should call systemctl commands
        assert mock_system.call_count >= 1
        calls_str = [str(call) for call in mock_system.call_args_list]
        assert any("systemctl" in str(c) for c in calls_str)

    def test_enable_with_service_command(self, mocker):
        """Should use service command when systemctl unavailable"""
        def which_side_effect(cmd):
            if cmd == "systemctl":
                return None
            elif cmd == "service":
                return "/usr/sbin/service"
            return None

        mocker.patch('shutil.which', side_effect=which_side_effect)
        mock_system = mocker.patch('os.system', return_value=0)

        CrontabService._enable_cron_service()

        # Should call service command
        mock_system.assert_called_once()
        assert "service cron start" in str(mock_system.call_args)


@pytest.mark.unit
class TestCrontabOperations:
    """Test crontab read/write operations"""

    def test_get_current_crontab_with_existing_crontab(self, mocker):
        """Should read existing crontab"""
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="0 0 * * * /some/command\n"
        )

        result = CrontabService._get_current_crontab()

        assert result == "0 0 * * * /some/command\n"

    def test_get_current_crontab_with_no_crontab(self, mocker):
        """Should return empty string when no crontab exists"""
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(returncode=1)

        result = CrontabService._get_current_crontab()

        assert result == ""

    def test_add_cron_job_to_empty_crontab(self, mocker):
        """Should add job to empty crontab"""
        mocker.patch.object(CrontabService, '_get_current_crontab', return_value="")
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(returncode=0)

        job_line = f"0 0 * * * /path/to/command  {CrontabService.CRON_MARKER}"
        CrontabService._add_cron_job(job_line)

        # Verify crontab was updated
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["crontab", "-"]
        assert job_line in mock_run.call_args[1]['input']

    def test_add_cron_job_updates_existing_job(self, mocker):
        """Should update existing job with same marker"""
        existing_crontab = f"0 0 * * * /old/command  {CrontabService.CRON_MARKER}\n"
        mocker.patch.object(CrontabService, '_get_current_crontab', return_value=existing_crontab)
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(returncode=0)

        new_job = f"0 0 * * * /new/command  {CrontabService.CRON_MARKER}"
        CrontabService._add_cron_job(new_job)

        # Verify old job was removed and new one added
        mock_run.assert_called_once()
        new_crontab = mock_run.call_args[1]['input']
        assert "/old/command" not in new_crontab
        assert new_job in new_crontab

    def test_add_cron_job_preserves_other_jobs(self, mocker):
        """Should preserve other cron jobs"""
        existing_crontab = "0 0 * * * /other/command\n"
        mocker.patch.object(CrontabService, '_get_current_crontab', return_value=existing_crontab)
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(returncode=0)

        new_job = f"0 0 * * * /my/command  {CrontabService.CRON_MARKER}"
        CrontabService._add_cron_job(new_job)

        # Verify other job was preserved
        new_crontab = mock_run.call_args[1]['input']
        assert "/other/command" in new_crontab
        assert new_job in new_crontab

    def test_add_cron_job_failure(self, mocker):
        """Should raise RuntimeError when crontab update fails"""
        mocker.patch.object(CrontabService, '_get_current_crontab', return_value="")
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")

        with pytest.raises(RuntimeError) as exc_info:
            CrontabService._add_cron_job("0 0 * * * /command")

        assert "Crontab 업데이트 실패" in str(exc_info.value)

    def test_remove_cron_job_when_exists(self, mocker):
        """Should remove job when it exists"""
        existing_crontab = f"0 0 * * * /command  {CrontabService.CRON_MARKER}\n"
        mocker.patch.object(CrontabService, '_get_current_crontab', return_value=existing_crontab)
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(returncode=0)

        CrontabService._remove_cron_job()

        # Verify job was removed
        mock_run.assert_called_once()
        new_crontab = mock_run.call_args[1]['input']
        assert CrontabService.CRON_MARKER not in new_crontab

    def test_remove_cron_job_when_not_exists(self, mocker):
        """Should do nothing when job doesn't exist"""
        mocker.patch.object(CrontabService, '_get_current_crontab', return_value="")

        CrontabService._remove_cron_job()

        # Should just print message and return


@pytest.mark.unit
class TestInstall:
    """Test install() method"""

    def test_install_saves_credentials(self, mocker):
        """Verify credentials are saved"""
        # Mock all dependencies
        mocker.patch('os.geteuid', return_value=0)
        mocker.patch.object(CrontabService, '_detect_cron_system', return_value="cron")
        mocker.patch.object(CrontabService, '_enable_cron_service')
        mocker.patch.object(CrontabService, '_add_cron_job')
        mocker.patch('shutil.copy2')
        mocker.patch('shutil.copytree')
        mocker.patch('pathlib.Path.mkdir')
        mocker.patch('pathlib.Path.chmod')
        mocker.patch('pathlib.Path.touch')
        mocker.patch('pathlib.Path.symlink_to')
        mocker.patch('pathlib.Path.unlink')
        mocker.patch('pathlib.Path.exists', return_value=False)
        mocker.patch('pathlib.Path.is_symlink', return_value=False)
        mocker.patch('os.system', return_value=0)

        mock_save_creds = mocker.patch('coupang_coupon_issuer.service.CredentialManager.save_credentials')

        # Run install
        CrontabService.install("access-key", "secret-key", "user-id", "vendor-id")

        # Verify credentials were saved
        mock_save_creds.assert_called_once_with("access-key", "secret-key", "user-id", "vendor-id")


@pytest.mark.unit
class TestUninstall:
    """Test uninstall() method"""

    def test_uninstall_removes_cron_job(self, mocker):
        """Verify cron job is removed"""
        mocker.patch('os.geteuid', return_value=0)
        mock_remove_job = mocker.patch.object(CrontabService, '_remove_cron_job')
        mocker.patch('pathlib.Path.exists', return_value=False)
        mocker.patch('pathlib.Path.is_symlink', return_value=False)

        CrontabService.uninstall()

        # Verify cron job removal was called
        mock_remove_job.assert_called_once()


@pytest.mark.unit
class TestServiceConfiguration:
    """Test service configuration constants"""

    def test_cron_marker_constant(self):
        """Verify CRON_MARKER constant"""
        assert CrontabService.CRON_MARKER == "# coupang_coupon_issuer_job"

    def test_service_name_constant(self):
        """Verify SERVICE_NAME constant"""
        assert SERVICE_NAME == "coupang_coupon_issuer"
