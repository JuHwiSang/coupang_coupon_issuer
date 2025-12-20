"""
Integration tests for CrontabService uninstallation process.

Tests the CrontabService.uninstall() method in a real Ubuntu 22.04 + cron environment.
"""

import pytest


@pytest.mark.integration
class TestUninstallBasic:
    """Basic uninstallation tests"""

    def test_uninstall_removes_cron_job(self, installed_service):
        """Verify cron job is removed"""
        exec_fn = installed_service["exec"]

        # Verify job exists before uninstall
        exit_code, output_before = exec_fn("crontab -l")
        assert exit_code == 0
        assert "# coupang_coupon_issuer_job" in output_before

        # Uninstall (answer 'n' to all prompts)
        uninstall_cmd = "cd /app && echo -e 'n\\nn\\nn\\nn' | python3 main.py uninstall"
        exec_fn(uninstall_cmd)

        # Verify job is removed
        exit_code, output_after = exec_fn("crontab -l || true")
        # Either no crontab exists (exit code 1) or it exists but has no our job
        assert "# coupang_coupon_issuer_job" not in output_after

    def test_uninstall_removes_symlink(self, installed_service):
        """Verify symlink is removed"""
        exec_fn = installed_service["exec"]

        # Verify symlink exists before uninstall
        exit_code, _ = exec_fn("test -L /usr/local/bin/coupang_coupon_issuer")
        assert exit_code == 0

        # Uninstall (answer 'n' to all prompts)
        uninstall_cmd = "cd /app && echo -e 'n\\nn\\nn\\nn' | python3 main.py uninstall"
        exec_fn(uninstall_cmd)

        # Verify symlink is removed
        exit_code, _ = exec_fn("test -L /usr/local/bin/coupang_coupon_issuer")
        assert exit_code != 0  # Should not exist


@pytest.mark.integration
class TestUninstallFileDeletion:
    """Test file deletion prompts and behavior"""

    def test_uninstall_with_all_no_preserves_files(self, installed_service):
        """Answering 'n' to all prompts should preserve files"""
        exec_fn = installed_service["exec"]

        # Uninstall with all 'n'
        uninstall_cmd = "cd /app && echo -e 'n\\nn\\nn\\nn' | python3 main.py uninstall"
        exec_fn(uninstall_cmd)

        # Verify files are preserved
        exit_code, _ = exec_fn("test -d /opt/coupang_coupon_issuer")
        assert exit_code == 0  # Directory still exists

        exit_code, _ = exec_fn("test -f /root/.config/coupang_coupon_issuer/credentials.json")
        assert exit_code == 0  # Credentials still exist

    def test_uninstall_with_yes_to_install_dir(self, installed_service):
        """Answering 'y' to install dir prompt should delete it"""
        exec_fn = installed_service["exec"]

        # Uninstall with 'y' to first prompt (install dir), 'n' to others
        uninstall_cmd = "cd /app && echo -e 'y\\nn\\nn\\nn' | python3 main.py uninstall"
        exec_fn(uninstall_cmd)

        # Verify install dir is removed
        exit_code, _ = exec_fn("test -d /opt/coupang_coupon_issuer")
        assert exit_code != 0  # Directory should not exist

        # Other files still exist
        exit_code, _ = exec_fn("test -f /root/.config/coupang_coupon_issuer/credentials.json")
        assert exit_code == 0

    def test_uninstall_with_yes_to_credentials(self, installed_service):
        """Answering 'y' to credentials prompt should delete it"""
        exec_fn = installed_service["exec"]

        # Uninstall with 'n', 'y', 'n', 'n' (yes to credentials only)
        uninstall_cmd = "cd /app && echo -e 'n\\ny\\nn\\nn' | python3 main.py uninstall"
        exec_fn(uninstall_cmd)

        # Verify credentials are removed
        exit_code, _ = exec_fn("test -f /root/.config/coupang_coupon_issuer/credentials.json")
        assert exit_code != 0  # Credentials should not exist

        # Install dir still exists
        exit_code, _ = exec_fn("test -d /opt/coupang_coupon_issuer")
        assert exit_code == 0

    def test_uninstall_with_yes_to_all_removes_everything(self, installed_service):
        """Answering 'y' to all prompts should remove everything"""
        exec_fn = installed_service["exec"]

        # Uninstall with all 'y'
        uninstall_cmd = "cd /app && echo -e 'y\\ny\\ny\\ny' | python3 main.py uninstall"
        exec_fn(uninstall_cmd)

        # Verify everything is removed
        exit_code, _ = exec_fn("test -d /opt/coupang_coupon_issuer")
        assert exit_code != 0  # Install dir removed

        exit_code, _ = exec_fn("test -f /root/.config/coupang_coupon_issuer/credentials.json")
        assert exit_code != 0  # Credentials removed

        exit_code, _ = exec_fn("test -d /root/.local/state/coupang_coupon_issuer")
        assert exit_code != 0  # Log dir removed


@pytest.mark.integration
class TestUninstallWithoutInstall:
    """Test uninstalling when nothing is installed"""

    def test_uninstall_without_cron_job_succeeds(self, clean_container, container_exec):
        """Uninstalling when no cron job exists should succeed gracefully"""
        # Try to uninstall without installing first
        uninstall_cmd = "cd /app && echo -e 'n\\nn\\nn\\nn' | python3 main.py uninstall"
        exit_code, output = container_exec(uninstall_cmd)

        # Should not crash (exit code 0 or 1 acceptable)
        # Just verify it doesn't crash with an exception
        assert "Traceback" not in output
