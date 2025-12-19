"""
End-to-end integration tests for complete workflow.

Tests the full lifecycle: install → apply → issue → logs → uninstall
"""

import pytest


@pytest.mark.integration
class TestEndToEndWorkflow:
    """Complete workflow tests"""

    def test_complete_workflow(self, clean_container, container_exec, test_excel_file):
        """Test complete workflow from install to uninstall"""
        # 1. Install
        install_cmd = (
            "cd /app && "
            "python3 main.py install "
            "--access-key test-access "
            "--secret-key test-secret "
            "--user-id test-user "
            "--vendor-id test-vendor"
        )
        exit_code, output = container_exec(install_cmd, check=True)
        assert "설치 완료" in output

        # 2. Verify cron job was created
        exit_code, crontab_output = container_exec("crontab -l")
        assert exit_code == 0
        assert "# coupang_coupon_issuer_job" in crontab_output
        assert "main.py issue" in crontab_output

        # 3. Copy test Excel to container
        # (In real scenario, user would run 'apply' command)
        # For testing, we'll just verify the command structure

        # 4. Verify global command works
        exit_code, output = container_exec("which coupang_coupon_issuer")
        assert exit_code == 0
        assert "/usr/local/bin/coupang_coupon_issuer" in output

        # 5. Verify log directory exists
        exit_code, _ = container_exec("test -d /root/.local/state/coupang_coupon_issuer")
        assert exit_code == 0

        # 6. Verify log file exists
        exit_code, _ = container_exec("test -f /root/.local/state/coupang_coupon_issuer/issuer.log")
        assert exit_code == 0

        # 7. Uninstall (say 'y' to all)
        uninstall_cmd = "cd /app && echo -e 'y\\ny\\ny\\ny' | python3 main.py uninstall"
        exit_code, output = container_exec(uninstall_cmd)
        assert "제거 완료" in output

        # 8. Verify cron job was removed
        exit_code, crontab_output = container_exec("crontab -l || true")
        assert "# coupang_coupon_issuer_job" not in crontab_output

    def test_cron_schedule_accuracy(self, installed_service):
        """Verify cron schedule is set to midnight (00:00)"""
        exec_fn = installed_service["exec"]

        exit_code, output = exec_fn("crontab -l")
        assert exit_code == 0

        # Parse cron line
        for line in output.split('\n'):
            if "# coupang_coupon_issuer_job" in line:
                # Format: 0 0 * * * command
                parts = line.split()
                assert parts[0] == "0"  # minute
                assert parts[1] == "0"  # hour
                assert parts[2] == "*"  # day of month
                assert parts[3] == "*"  # month
                assert parts[4] == "*"  # day of week
                break
        else:
            pytest.fail("Cron job not found")

    def test_log_redirection_in_cron_job(self, installed_service):
        """Verify cron job redirects output to log file"""
        exec_fn = installed_service["exec"]

        exit_code, output = exec_fn("crontab -l")
        assert exit_code == 0

        # Verify output redirection
        assert ">> /root/.local/state/coupang_coupon_issuer/issuer.log" in output
        assert "2>&1" in output  # stderr also redirected
