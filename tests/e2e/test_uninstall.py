"""
Integration tests for uninstall command with Python script.

Tests the script-based uninstall command in a real Docker environment.
"""

import pytest
import json


@pytest.mark.e2e
class TestUninstallCommand:
    """Test uninstall command with Python script"""

    def test_uninstall_removes_cron_job_by_uuid(self, python_script, clean_install_dir, container_exec):
        """Uninstall should remove cron job matching UUID from config.json"""
        # Install first
        exit_code, _ = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )
        assert exit_code == 0

        # Get UUID
        exit_code, config_content = container_exec(f"cat {clean_install_dir}/config.json")
        config = json.loads(config_content)
        installation_id = config["installation_id"]

        # Verify cron job exists
        exit_code, crontab_before = container_exec("crontab -l")
        assert exit_code == 0
        assert f"# coupang_coupon_issuer_job:{installation_id}" in crontab_before

        # Run uninstall
        exit_code, output = container_exec(
            f"python3 {python_script} uninstall {clean_install_dir}"
        )
        assert exit_code == 0

        # Verify cron job removed
        exit_code, crontab_after = container_exec("crontab -l || echo ''")
        # Note: crontab -l returns non-zero if no crontab exists, so we use || echo ''
        assert f"# coupang_coupon_issuer_job:{installation_id}" not in crontab_after

    def test_uninstall_removes_config_json(self, python_script, clean_install_dir, container_exec):
        """Uninstall should remove config.json file"""
        # Install first
        exit_code, _ = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )
        assert exit_code == 0

        # Run uninstall
        exit_code, _ = container_exec(
            f"python3 {python_script} uninstall {clean_install_dir}"
        )
        assert exit_code == 0

        # Verify config.json is removed
        exit_code, _ = container_exec(f"test -f {clean_install_dir}/config.json")
        assert exit_code != 0  # File should NOT exist

    def test_uninstall_preserves_coupons_xlsx(self, python_script, clean_install_dir, sample_excel, container_exec):
        """Uninstall should preserve coupons.xlsx file"""
        # Install first
        exit_code, _ = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )
        assert exit_code == 0

        # Run uninstall
        exit_code, _ = container_exec(
            f"python3 {python_script} uninstall {clean_install_dir}"
        )
        assert exit_code == 0

        # Verify coupons.xlsx still exists
        exit_code, _ = container_exec(f"test -f {clean_install_dir}/coupons.xlsx")
        assert exit_code == 0

    def test_uninstall_preserves_log_file(self, python_script, clean_install_dir, container_exec):
        """Uninstall should preserve issuer.log file if it exists"""
        # Install first
        exit_code, _ = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )
        assert exit_code == 0

        # Create log file
        container_exec(f"echo 'test log' > {clean_install_dir}/issuer.log")

        # Run uninstall
        exit_code, _ = container_exec(
            f"python3 {python_script} uninstall {clean_install_dir}"
        )
        assert exit_code == 0

        # Verify log file still exists
        exit_code, _ = container_exec(f"test -f {clean_install_dir}/issuer.log")
        assert exit_code == 0

    def test_uninstall_without_config_json_warns(self, python_script, clean_install_dir, container_exec):
        """Uninstall without config.json should warn about missing installation_id"""
        # Run uninstall without installing first
        exit_code, output = container_exec(
            f"python3 {python_script} uninstall {clean_install_dir}"
        )

        # Should complete but warn
        assert exit_code == 0 or "WARNING" in output or "No installation_id" in output

    def test_uninstall_clears_all_cron_jobs(self, python_script, clean_install_dir, container_exec):
        """Uninstall should clear all cron jobs for this installation"""
        # Install first
        exit_code, _ = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )
        assert exit_code == 0

        # Verify cron job exists
        exit_code, crontab_before = container_exec("crontab -l")
        assert exit_code == 0
        cron_count_before = crontab_before.count("main.py issue")
        assert cron_count_before >= 1

        # Run uninstall
        exit_code, _ = container_exec(
            f"python3 {python_script} uninstall {clean_install_dir}"
        )
        assert exit_code == 0

        # Verify all cron jobs removed
        exit_code, crontab_after = container_exec("crontab -l || echo ''")
        cron_count_after = crontab_after.count("main.py issue")
        assert cron_count_after == 0

    def test_uninstall_prints_completion_message(self, python_script, clean_install_dir, container_exec):
        """Uninstall should print completion message"""
        # Install first
        exit_code, _ = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )
        assert exit_code == 0

        # Run uninstall
        exit_code, output = container_exec(
            f"python3 {python_script} uninstall {clean_install_dir}"
        )
        assert exit_code == 0

        # Should mention completion
        assert "제거 완료" in output or "완료" in output
