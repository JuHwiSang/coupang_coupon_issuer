"""
Integration tests for CrontabService installation process.

Tests the CrontabService.install() method in a real Ubuntu 22.04 + cron environment.
"""

import json
import pytest


@pytest.mark.integration
class TestInstallBasic:
    """Basic installation tests"""

    def test_install_creates_cron_job(self, installed_service):
        """Verify cron job is created"""
        exec_fn = installed_service["exec"]

        # Check crontab
        exit_code, output = exec_fn("crontab -l")
        assert exit_code == 0

        # Verify job exists with marker
        assert "# coupang_coupon_issuer_job" in output
        assert "main.py issue" in output
        assert "0 0 * * *" in output  # Daily at midnight

    def test_install_creates_log_directory(self, installed_service):
        """Verify log directory is created"""
        exec_fn = installed_service["exec"]

        # Check log directory
        exit_code, output = exec_fn("test -d /root/.local/state/coupang_coupon_issuer && echo EXISTS")
        assert exit_code == 0
        assert "EXISTS" in output

        # Check log file
        exit_code, output = exec_fn("test -f /root/.local/state/coupang_coupon_issuer/issuer.log && echo EXISTS")
        assert exit_code == 0
        assert "EXISTS" in output

    def test_install_ensures_cron_is_running(self, installed_service):
        """Verify cron service is running"""
        exec_fn = installed_service["exec"]

        # Check cron status
        exit_code, output = exec_fn("service cron status")
        assert exit_code == 0
        assert ("running" in output.lower() or "active" in output.lower())


@pytest.mark.integration
class TestInstallFiles:
    """Test file creation during installation"""

    def test_install_copies_all_required_files(self, installed_service):
        """Verify all files are copied to /opt"""
        exec_fn = installed_service["exec"]

        # Check main.py
        exit_code, output = exec_fn("test -f /opt/coupang_coupon_issuer/main.py && echo EXISTS")
        assert exit_code == 0
        assert "EXISTS" in output

        # Check src directory
        exit_code, output = exec_fn("test -d /opt/coupang_coupon_issuer/src && echo EXISTS")
        assert exit_code == 0
        assert "EXISTS" in output

    def test_install_creates_symlink(self, installed_service):
        """Verify symlink is created in /usr/local/bin"""
        exec_fn = installed_service["exec"]

        # Check symlink exists
        exit_code, output = exec_fn("test -L /usr/local/bin/coupang_coupon_issuer && echo EXISTS")
        assert exit_code == 0
        assert "EXISTS" in output

        # Check symlink target
        exit_code, output = exec_fn("readlink /usr/local/bin/coupang_coupon_issuer")
        assert exit_code == 0
        assert "/opt/coupang_coupon_issuer/main.py" in output

    def test_install_sets_executable_permissions(self, installed_service):
        """Verify main.py has executable permissions"""
        exec_fn = installed_service["exec"]

        # Check permissions
        exit_code, output = exec_fn("stat -c '%a' /opt/coupang_coupon_issuer/main.py")
        assert exit_code == 0
        assert "755" in output


@pytest.mark.integration
class TestInstallCredentials:
    """Test credentials storage"""

    def test_install_saves_credentials_file(self, installed_service):
        """Verify credentials.json is created in ~/.config"""
        exec_fn = installed_service["exec"]

        # Check file exists (container runs as root, so ~/.config = /root/.config)
        exit_code, output = exec_fn("test -f /root/.config/coupang_coupon_issuer/credentials.json && echo EXISTS")
        assert exit_code == 0
        assert "EXISTS" in output

    def test_install_credentials_have_correct_permissions(self, installed_service):
        """Verify credentials.json has 600 permissions"""
        exec_fn = installed_service["exec"]

        # Check permissions
        exit_code, output = exec_fn("stat -c '%a' /root/.config/coupang_coupon_issuer/credentials.json")
        assert exit_code == 0
        assert "600" in output

    def test_install_credentials_contain_correct_data(self, installed_service):
        """Verify credentials contain correct data"""
        exec_fn = installed_service["exec"]
        creds = installed_service["credentials"]

        # Read credentials file
        exit_code, output = exec_fn("cat /root/.config/coupang_coupon_issuer/credentials.json")
        assert exit_code == 0

        # Parse JSON
        data = json.loads(output)
        assert data["access_key"] == creds["access_key"]
        assert data["secret_key"] == creds["secret_key"]
        assert data["user_id"] == creds["user_id"]
        assert data["vendor_id"] == creds["vendor_id"]


@pytest.mark.integration
class TestInstallDuplicateInstall:
    """Test duplicate installation (update scenario)"""

    def test_install_twice_updates_cron_job(self, clean_container, container_exec):
        """Installing twice should update the cron job"""
        # First install
        install_cmd1 = (
            "cd /app && "
            "python3 main.py install "
            "--access-key key1 "
            "--secret-key secret1 "
            "--user-id user1 "
            "--vendor-id vendor1"
        )
        container_exec(install_cmd1, check=True)

        # Check crontab has one job
        exit_code, output1 = container_exec("crontab -l")
        assert exit_code == 0
        job_count1 = output1.count("# coupang_coupon_issuer_job")
        assert job_count1 == 1

        # Second install with different credentials
        install_cmd2 = (
            "cd /app && "
            "python3 main.py install "
            "--access-key key2 "
            "--secret-key secret2 "
            "--user-id user2 "
            "--vendor-id vendor2"
        )
        container_exec(install_cmd2, check=True)

        # Check crontab still has only one job (updated, not duplicated)
        exit_code, output2 = container_exec("crontab -l")
        assert exit_code == 0
        job_count2 = output2.count("# coupang_coupon_issuer_job")
        assert job_count2 == 1

        # Verify credentials were updated
        exit_code, creds_output = container_exec("cat /root/.config/coupang_coupon_issuer/credentials.json")
        assert exit_code == 0
        data = json.loads(creds_output)
        assert data["access_key"] == "key2"
