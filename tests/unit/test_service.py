"""
Unit tests for service.py - CrontabService (UUID-based)

Tests the CrontabService class for cron-based scheduling with UUID tracking.
Note: Most tests skip on Windows. Full integration tests are in tests/integration/
"""
import pytest
import os
from unittest.mock import MagicMock

from coupang_coupon_issuer.service import CrontabService
from coupang_coupon_issuer.config import SERVICE_NAME

# Skip all service tests on Windows (cron not available)
pytestmark = pytest.mark.skipif(os.name == 'nt', reason="Service tests require Linux")


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

    def test_install_cron_on_ubuntu(self, tmp_path, mocker):
        """Should install cron using apt on Ubuntu/Debian"""
        mocker.patch.object(CrontabService, '_get_package_manager', return_value="apt")
        mock_system = mocker.patch('os.system', return_value=0)

        CrontabService._install_cron()

        # Verify apt commands were called
        assert mock_system.call_count == 2
        calls = [str(call) for call in mock_system.call_args_list]
        assert any("apt-get update" in str(c) for c in calls)
        assert any("apt-get install" in str(c) and "cron" in str(c) for c in calls)

    def test_install_cron_on_rhel8(self, tmp_path, mocker):
        """Should install cron using dnf on RHEL 8+"""
        mocker.patch.object(CrontabService, '_get_package_manager', return_value="dnf")
        mock_system = mocker.patch('os.system', return_value=0)

        CrontabService._install_cron()

        mock_system.assert_called_once()
        assert "dnf install" in str(mock_system.call_args)
        assert "cronie" in str(mock_system.call_args)

    def test_install_cron_on_unsupported_system(self, tmp_path, mocker):
        """Should raise RuntimeError on unsupported systems"""
        mocker.patch.object(CrontabService, '_get_package_manager', return_value=None)

        with pytest.raises(RuntimeError) as exc_info:
            CrontabService._install_cron()

        assert "지원하지 않는 배포판" in str(exc_info.value)

    def test_install_cron_failure(self, tmp_path, mocker):
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
    """Test crontab read/write operations (UUID-based)"""

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
        """Should add job with UUID marker to empty crontab"""
        mocker.patch.object(CrontabService, '_get_current_crontab', return_value="")
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(returncode=0)

        job_line = "0 0 * * * /path/to/command  # coupang_coupon_issuer_job:test-uuid-1234"
        CrontabService._add_cron_job(job_line)

        # Verify crontab was updated
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == ["crontab", "-"]
        assert job_line in mock_run.call_args[1]['input']

    def test_add_cron_job_preserves_other_jobs(self, mocker):
        """Should preserve other cron jobs"""
        existing_crontab = "0 0 * * * /other/command\n"
        mocker.patch.object(CrontabService, '_get_current_crontab', return_value=existing_crontab)
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(returncode=0)

        new_job = "0 0 * * * /my/command  # coupang_coupon_issuer_job:new-uuid"
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

    def test_remove_crontab_by_uuid_when_exists(self, mocker):
        """Should remove job matching UUID"""
        existing_crontab = (
            "0 0 * * * /other/command\n"
            "0 0 * * * /my/command  # coupang_coupon_issuer_job:test-uuid-1234\n"
        )
        mocker.patch.object(CrontabService, '_get_current_crontab', return_value=existing_crontab)
        mock_run = mocker.patch('subprocess.run')
        mock_run.return_value = MagicMock(returncode=0)

        CrontabService._remove_crontab_by_uuid("test-uuid-1234")

        # Verify job with UUID was removed, other preserved
        mock_run.assert_called_once()
        new_crontab = mock_run.call_args[1]['input']
        assert "coupang_coupon_issuer_job:test-uuid-1234" not in new_crontab
        assert "/other/command" in new_crontab

    def test_remove_crontab_by_uuid_when_not_exists(self, mocker, capsys):
        """Should print message when UUID not found"""
        mocker.patch.object(CrontabService, '_get_current_crontab', return_value="0 0 * * * /other/command\n")
        mock_run = mocker.patch('subprocess.run')

        CrontabService._remove_crontab_by_uuid("nonexistent-uuid")

        # Should not call crontab update
        mock_run.assert_not_called()

        # Should print message
        captured = capsys.readouterr()
        assert "제거할 cron job이 없습니다" in captured.out


@pytest.mark.unit
class TestInstall:
    """Test install() method with UUID-based cron management"""

    def test_install_saves_config_with_new_uuid(self, tmp_path, mocker, capsys):
        """Install should save config with new UUID"""
        # Mock all dependencies
        mocker.patch.object(CrontabService, '_detect_cron_system', return_value="cron")
        mocker.patch.object(CrontabService, '_enable_cron_service')
        mocker.patch.object(CrontabService, '_add_cron_job')
        mocker.patch('sys.executable', '/fake/path/coupang_coupon_issuer')

        # Mock ConfigManager
        mocker.patch('coupang_coupon_issuer.service.ConfigManager.get_installation_id', return_value=None)
        mock_save = mocker.patch('coupang_coupon_issuer.service.ConfigManager.save_config', return_value="new-uuid-1234")

        # Run install
        CrontabService.install(tmp_path, "access-key", "secret-key", "user-id", "vendor-id")

        # Verify config was saved
        mock_save.assert_called_once_with("access-key", "secret-key", "user-id", "vendor-id")

    def test_install_removes_old_cron_job_when_uuid_exists(self, tmp_path, mocker):
        """Install should remove old cron job if UUID exists"""
        # Mock dependencies
        mocker.patch.object(CrontabService, '_detect_cron_system', return_value="cron")
        mocker.patch.object(CrontabService, '_enable_cron_service')
        mocker.patch.object(CrontabService, '_add_cron_job')
        mocker.patch('sys.executable', '/fake/path/coupang_coupon_issuer')

        # Mock existing UUID
        mocker.patch('coupang_coupon_issuer.service.ConfigManager.get_installation_id', return_value="old-uuid-5678")
        mock_remove = mocker.patch.object(CrontabService, '_remove_crontab_by_uuid')
        mocker.patch('coupang_coupon_issuer.service.ConfigManager.save_config', return_value="new-uuid-1234")

        # Run install
        CrontabService.install(tmp_path, "access-key", "secret-key", "user-id", "vendor-id")

        # Verify old cron job was removed
        mock_remove.assert_called_once_with("old-uuid-5678")

    def test_install_creates_cron_job_with_uuid_marker(self, tmp_path, mocker):
        """Install should create cron job with UUID in comment"""
        # Mock dependencies
        mocker.patch.object(CrontabService, '_detect_cron_system', return_value="cron")
        mocker.patch.object(CrontabService, '_enable_cron_service')
        mocker.patch('sys.executable', '/fake/bin/coupang_coupon_issuer')
        mocker.patch('coupang_coupon_issuer.service.ConfigManager.get_installation_id', return_value=None)
        mocker.patch('coupang_coupon_issuer.service.ConfigManager.save_config', return_value="test-uuid-9999")

        # Mock add_cron_job
        mock_add = mocker.patch.object(CrontabService, '_add_cron_job')

        # Run install
        CrontabService.install(tmp_path, "access-key", "secret-key", "user-id", "vendor-id")

        # Verify cron job was added with UUID marker
        mock_add.assert_called_once()
        job_line = mock_add.call_args[0][0]
        assert "# coupang_coupon_issuer_job:test-uuid-9999" in job_line
        assert "/fake/bin/coupang_coupon_issuer issue" in job_line

    def test_install_with_jitter_adds_jitter_flag(self, tmp_path, mocker):
        """Install with jitter should add --jitter-max flag to cron job"""
        # Mock dependencies
        mocker.patch.object(CrontabService, '_detect_cron_system', return_value="cron")
        mocker.patch.object(CrontabService, '_enable_cron_service')
        mocker.patch('sys.executable', '/fake/bin/coupang_coupon_issuer')
        mocker.patch('coupang_coupon_issuer.service.ConfigManager.get_installation_id', return_value=None)
        mocker.patch('coupang_coupon_issuer.service.ConfigManager.save_config', return_value="test-uuid")

        mock_add = mocker.patch.object(CrontabService, '_add_cron_job')

        # Run install with jitter
        CrontabService.install(tmp_path, "access-key", "secret-key", "user-id", "vendor-id", jitter_max=60)

        # Verify jitter flag in cron job
        job_line = mock_add.call_args[0][0]
        assert "--jitter-max 60" in job_line

    def test_install_installs_cron_when_not_detected(self, tmp_path, mocker):
        """Install should install cron if not detected"""
        # Mock cron not detected
        mocker.patch.object(CrontabService, '_detect_cron_system', return_value=None)
        mock_install_cron = mocker.patch.object(CrontabService, '_install_cron')
        mocker.patch.object(CrontabService, '_enable_cron_service')
        mocker.patch.object(CrontabService, '_add_cron_job')
        mocker.patch('sys.executable', '/fake/path/coupang_coupon_issuer')
        mocker.patch('coupang_coupon_issuer.service.ConfigManager.get_installation_id', return_value=None)
        mocker.patch('coupang_coupon_issuer.service.ConfigManager.save_config', return_value="test-uuid")

        # Run install
        CrontabService.install(tmp_path, "access-key", "secret-key", "user-id", "vendor-id")

        # Verify cron was installed
        mock_install_cron.assert_called_once()


@pytest.mark.unit
class TestUninstall:
    """Test uninstall() method with UUID-based removal"""

    def test_uninstall_removes_cron_job_by_uuid(self, tmp_path, mocker):
        """Uninstall should remove cron job using UUID from config"""
        # Mock UUID exists
        mocker.patch('coupang_coupon_issuer.service.ConfigManager.get_installation_id', return_value="my-uuid-1234")
        mock_remove = mocker.patch.object(CrontabService, '_remove_crontab_by_uuid')

        CrontabService.uninstall(tmp_path)

        # Verify cron job removal with correct UUID
        mock_remove.assert_called_once_with("my-uuid-1234")

    def test_uninstall_warns_when_no_uuid(self, tmp_path, mocker, capsys):
        """Uninstall should warn if no UUID found in config"""
        # Mock no UUID
        mocker.patch('coupang_coupon_issuer.service.ConfigManager.get_installation_id', return_value=None)
        mock_remove = mocker.patch.object(CrontabService, '_remove_crontab_by_uuid')

        CrontabService.uninstall(tmp_path)

        # Should not call remove
        mock_remove.assert_not_called()

        # Should print warning
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "installation_id가 없습니다" in captured.out


@pytest.mark.unit
class TestServiceConfiguration:
    """Test service configuration constants"""

    def test_service_name_constant(self):
        """Verify SERVICE_NAME constant"""
        assert SERVICE_NAME == "coupang_coupon_issuer"
