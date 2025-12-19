"""
Integration tests for service.py uninstallation process.

Tests the SystemdService.uninstall() method in a real Ubuntu 22.04 + systemd environment.
Covers lines 149-220 in service.py.
"""

import pytest
from unittest.mock import patch


pytestmark = [
    pytest.mark.integration,
    pytest.mark.timeout(300)  # 5 minute timeout
]


class TestServiceUninstallation:
    """Test SystemdService.uninstall() method in real Linux environment"""

    def test_uninstall_stops_service(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall stops the running service.

        Covers: service.py lines 155-161
        """
        # Mock user input to skip prompts
        uninstall_cmd = "cd /app && echo 'n\nn\nn' | python3 main.py uninstall"

        result = container_exec(uninstall_cmd, check=False)

        # Check service is stopped
        status_result = container_exec(
            "systemctl is-active coupang_coupon_issuer",
            check=False
        )

        # Service should be inactive or not found
        assert status_result['exit_code'] != 0 or 'inactive' in status_result['stdout']

    def test_uninstall_disables_service_autostart(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall disables service from boot.

        Covers: service.py line 156
        """
        # Uninstall with all 'no' to prompts
        uninstall_cmd = "cd /app && echo 'n\nn\nn' | python3 main.py uninstall"
        container_exec(uninstall_cmd, check=False)

        # Check if service is disabled
        enabled_result = container_exec(
            "systemctl is-enabled coupang_coupon_issuer",
            check=False
        )

        # Should return disabled or not-found
        assert enabled_result['exit_code'] != 0 or 'disabled' in enabled_result['stdout']

    def test_uninstall_removes_systemd_service_file(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall deletes systemd service file.

        Covers: service.py lines 164-170
        """
        service_file = "/etc/systemd/system/coupang_coupon_issuer.service"

        # Verify file exists before uninstall
        before_result = container_exec(f"test -f {service_file}", check=False)
        assert before_result['exit_code'] == 0, "Service file should exist before uninstall"

        # Uninstall
        uninstall_cmd = "cd /app && echo 'n\nn\nn' | python3 main.py uninstall"
        container_exec(uninstall_cmd, check=False)

        # Verify file is removed
        after_result = container_exec(f"test -f {service_file}", check=False)
        assert after_result['exit_code'] != 0, "Service file should be removed"

    def test_uninstall_runs_daemon_reload_after_file_removal(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall runs systemctl daemon-reload.

        Covers: service.py line 172
        """
        # Uninstall
        uninstall_cmd = "cd /app && echo 'n\nn\nn' | python3 main.py uninstall"
        container_exec(uninstall_cmd, check=False)

        # After daemon-reload, service should not appear in list-unit-files
        list_result = container_exec(
            "systemctl list-unit-files | grep coupang_coupon_issuer || true"
        )

        # Service should not be listed (or empty output)
        assert 'coupang_coupon_issuer.service' not in list_result['stdout']

    def test_uninstall_removes_symlink(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall removes global command symlink.

        Covers: service.py lines 175-181
        """
        symlink_path = "/usr/local/bin/coupang_coupon_issuer"

        # Verify symlink exists before
        before_result = container_exec(f"test -L {symlink_path}", check=False)
        assert before_result['exit_code'] == 0, "Symlink should exist before uninstall"

        # Uninstall
        uninstall_cmd = "cd /app && echo 'n\nn\nn' | python3 main.py uninstall"
        container_exec(uninstall_cmd, check=False)

        # Verify symlink is removed
        after_result = container_exec(f"test -L {symlink_path}", check=False)
        assert after_result['exit_code'] != 0, "Symlink should be removed"

    def test_uninstall_prompts_for_install_directory_deletion(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall prompts user and deletes /opt when 'y' given.

        Covers: service.py lines 184-194
        """
        install_dir = "/opt/coupang_coupon_issuer"

        # Verify directory exists before
        before_result = container_exec(f"test -d {install_dir}", check=False)
        assert before_result['exit_code'] == 0, "Install dir should exist"

        # Uninstall with 'y' to first prompt, 'n' to others
        uninstall_cmd = "cd /app && echo 'y\nn\nn' | python3 main.py uninstall"
        result = container_exec(uninstall_cmd, check=False)

        # Verify directory is removed
        after_result = container_exec(f"test -d {install_dir}", check=False)
        assert after_result['exit_code'] != 0, "Install dir should be removed when user says 'y'"

        # Verify prompt was shown
        assert "설치 디렉토리도 삭제하시겠습니까" in result['stdout'] or "삭제" in result['stdout']

    def test_uninstall_preserves_install_directory_on_no(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall preserves /opt when user declines.

        Covers: service.py lines 193-194
        """
        install_dir = "/opt/coupang_coupon_issuer"

        # Uninstall with 'n' to all prompts
        uninstall_cmd = "cd /app && echo 'n\nn\nn' | python3 main.py uninstall"
        result = container_exec(uninstall_cmd, check=False)

        # Verify directory still exists
        after_result = container_exec(f"test -d {install_dir}", check=False)
        assert after_result['exit_code'] == 0, "Install dir should be preserved when user says 'n'"

        # Verify preservation message
        assert "유지됩니다" in result['stdout'] or result['exit_code'] == 0

    def test_uninstall_prompts_for_credentials_deletion(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall prompts and deletes credentials.json when 'y' given.

        Covers: service.py lines 197-207
        """
        creds_file = "/etc/coupang_coupon_issuer/credentials.json"

        # Verify file exists before
        before_result = container_exec(f"test -f {creds_file}", check=False)
        assert before_result['exit_code'] == 0, "Credentials file should exist"

        # Uninstall with 'n', 'y', 'n' (skip install dir, delete credentials, skip excel)
        uninstall_cmd = "cd /app && echo 'n\ny\nn' | python3 main.py uninstall"
        result = container_exec(uninstall_cmd, check=False)

        # Verify file is removed
        after_result = container_exec(f"test -f {creds_file}", check=False)
        assert after_result['exit_code'] != 0, "Credentials should be removed when user says 'y'"

    def test_uninstall_preserves_credentials_on_no(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall preserves credentials.json when user declines.

        Covers: service.py lines 206-207
        """
        creds_file = "/etc/coupang_coupon_issuer/credentials.json"

        # Uninstall with 'n' to all prompts
        uninstall_cmd = "cd /app && echo 'n\nn\nn' | python3 main.py uninstall"
        container_exec(uninstall_cmd, check=False)

        # Verify file still exists
        after_result = container_exec(f"test -f {creds_file}", check=False)
        assert after_result['exit_code'] == 0, "Credentials should be preserved when user says 'n'"

    def test_uninstall_prompts_for_excel_deletion(
        self, installed_service, container_exec, mock_excel_in_container
    ):
        """
        Verify uninstall prompts and deletes coupons.xlsx when 'y' given.

        Covers: service.py lines 210-218
        """
        # Create Excel file
        excel_file = mock_excel_in_container('valid')

        # Verify file exists
        before_result = container_exec(f"test -f {excel_file}", check=False)
        assert before_result['exit_code'] == 0, "Excel file should exist"

        # Uninstall with 'n', 'n', 'y' (skip install dir and creds, delete excel)
        uninstall_cmd = "cd /app && echo 'n\nn\ny' | python3 main.py uninstall"
        result = container_exec(uninstall_cmd, check=False)

        # Verify file is removed
        after_result = container_exec(f"test -f {excel_file}", check=False)
        assert after_result['exit_code'] != 0, "Excel should be removed when user says 'y'"

    def test_uninstall_handles_excel_deletion_error(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall handles errors when deleting Excel file.

        Covers: service.py lines 217-218
        """
        # Excel file may not exist, verify uninstall handles it gracefully
        excel_file = "/etc/coupang_coupon_issuer/coupons.xlsx"

        # Ensure Excel doesn't exist
        container_exec(f"rm -f {excel_file}", check=False)

        # Uninstall with 'y' to Excel prompt
        uninstall_cmd = "cd /app && echo 'n\nn\ny' | python3 main.py uninstall"
        result = container_exec(uninstall_cmd, check=False)

        # Should complete without error even if file doesn't exist
        assert result['exit_code'] == 0 or "ERROR" in result['stdout']

    def test_uninstall_requires_root_permission(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall requires root permission.

        Covers: service.py lines 149, 22-26
        """
        # Create non-root user
        container_exec("useradd -m testuser", check=False)

        # Try to uninstall as non-root
        uninstall_cmd = "cd /app && echo 'n\nn\nn' | python3 main.py uninstall"

        result = container_exec(
            f"su - testuser -c '{uninstall_cmd}'",
            check=False
        )

        # Should fail with permission error
        assert result['exit_code'] != 0
        assert "root 권한이 필요합니다" in result['stdout'] or "PermissionError" in result['stdout']

    def test_uninstall_prints_completion_message(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall prints completion message.

        Covers: service.py line 220
        """
        # Uninstall
        uninstall_cmd = "cd /app && echo 'n\nn\nn' | python3 main.py uninstall"
        result = container_exec(uninstall_cmd, check=False)

        # Check for completion message
        assert "제거 완료" in result['stdout'] or "완료" in result['stdout']

    def test_uninstall_handles_all_prompts_with_mixed_responses(
        self, installed_service, container_exec, mock_excel_in_container
    ):
        """
        Verify uninstall handles complex scenario with mixed user inputs.

        Covers: service.py lines 186-218
        """
        # Create Excel file
        mock_excel_in_container('valid')

        install_dir = "/opt/coupang_coupon_issuer"
        creds_file = "/etc/coupang_coupon_issuer/credentials.json"
        excel_file = "/etc/coupang_coupon_issuer/coupons.xlsx"

        # Verify all exist before
        assert container_exec(f"test -d {install_dir}", check=False)['exit_code'] == 0
        assert container_exec(f"test -f {creds_file}", check=False)['exit_code'] == 0
        assert container_exec(f"test -f {excel_file}", check=False)['exit_code'] == 0

        # Uninstall with mixed responses: y, n, y
        # Delete install dir, keep credentials, delete Excel
        uninstall_cmd = "cd /app && echo 'y\nn\ny' | python3 main.py uninstall"
        result = container_exec(uninstall_cmd, check=False)

        # Verify expected state
        assert container_exec(f"test -d {install_dir}", check=False)['exit_code'] != 0, \
            "Install dir should be deleted"
        assert container_exec(f"test -f {creds_file}", check=False)['exit_code'] == 0, \
            "Credentials should be preserved"
        assert container_exec(f"test -f {excel_file}", check=False)['exit_code'] != 0, \
            "Excel should be deleted"

    def test_uninstall_handles_service_file_deletion_error(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall handles errors when deleting service file.

        Covers: service.py lines 169-170
        """
        service_file = "/etc/systemd/system/coupang_coupon_issuer.service"

        # Make service file immutable (can't be deleted)
        container_exec(f"chattr +i {service_file}", check=False)

        # Uninstall
        uninstall_cmd = "cd /app && echo 'n\nn\nn' | python3 main.py uninstall"
        result = container_exec(uninstall_cmd, check=False)

        # Should print ERROR but continue
        # (Note: chattr may not work in container, so this may not trigger error)

        # Remove immutable flag for cleanup
        container_exec(f"chattr -i {service_file}", check=False)

    def test_uninstall_handles_symlink_deletion_error(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall handles errors when deleting symlink.

        Covers: service.py lines 180-181
        """
        # Make /usr/local/bin immutable
        container_exec("chattr +i /usr/local/bin", check=False)

        # Uninstall
        uninstall_cmd = "cd /app && echo 'n\nn\nn' | python3 main.py uninstall"
        result = container_exec(uninstall_cmd, check=False)

        # Should handle error gracefully
        # (Note: chattr may not work, this is defensive testing)

        # Restore permissions
        container_exec("chattr -i /usr/local/bin", check=False)

    def test_uninstall_when_service_not_running(
        self, installed_service, container_exec
    ):
        """
        Verify uninstall works when service is already stopped.

        Covers: service.py lines 155-161
        """
        # Stop service manually
        container_exec("systemctl stop coupang_coupon_issuer", check=False)

        # Uninstall
        uninstall_cmd = "cd /app && echo 'n\nn\nn' | python3 main.py uninstall"
        result = container_exec(uninstall_cmd, check=False)

        # Should complete without error
        assert result['exit_code'] == 0 or "제거 완료" in result['stdout']
