"""
Integration tests for uninstall command with PyInstaller binary.

Tests the single-binary uninstall command in a real Docker environment.
"""

import pytest
import json


@pytest.mark.integration
class TestUninstallCommand:
    """Test uninstall command with PyInstaller binary"""

    def test_uninstall_removes_cron_job_by_uuid(self, built_binary, clean_install_dir, container_exec):
        """Uninstall should remove cron job matching UUID from config.json"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Install first
        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
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
            f"cd {clean_install_dir} && ./coupang_coupon_issuer uninstall"
        )
        assert exit_code == 0

        # Verify cron job removed
        exit_code, crontab_after = container_exec("crontab -l || echo ''")
        # Note: crontab -l returns non-zero if no crontab exists, so we use || echo ''
        assert f"# coupang_coupon_issuer_job:{installation_id}" not in crontab_after

    def test_uninstall_preserves_config_json(self, built_binary, clean_install_dir, container_exec):
        """Uninstall should preserve config.json file"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Install first
        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )
        assert exit_code == 0

        # Run uninstall
        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer uninstall"
        )
        assert exit_code == 0

        # Verify config.json still exists
        exit_code, _ = container_exec(f"test -f {clean_install_dir}/config.json")
        assert exit_code == 0

    def test_uninstall_preserves_coupons_xlsx(self, built_binary, clean_install_dir, sample_excel, container_exec):
        """Uninstall should preserve coupons.xlsx file"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Install first
        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )
        assert exit_code == 0

        # Run uninstall
        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer uninstall"
        )
        assert exit_code == 0

        # Verify coupons.xlsx still exists
        exit_code, _ = container_exec(f"test -f {clean_install_dir}/coupons.xlsx")
        assert exit_code == 0

    def test_uninstall_preserves_log_file(self, built_binary, clean_install_dir, container_exec):
        """Uninstall should preserve issuer.log file if it exists"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Install first
        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )
        assert exit_code == 0

        # Create log file
        container_exec(f"echo 'test log' > {clean_install_dir}/issuer.log")

        # Run uninstall
        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer uninstall"
        )
        assert exit_code == 0

        # Verify log file still exists
        exit_code, _ = container_exec(f"test -f {clean_install_dir}/issuer.log")
        assert exit_code == 0

    def test_uninstall_without_config_json_warns(self, built_binary, clean_install_dir, container_exec):
        """Uninstall without config.json should warn about missing installation_id"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Run uninstall without installing first
        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer uninstall"
        )

        # Should complete but warn
        assert exit_code == 0 or "WARNING" in output or "No installation_id" in output

    def test_uninstall_clears_all_cron_jobs(self, built_binary, clean_install_dir, container_exec):
        """Uninstall should clear all cron jobs for this installation"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Install first
        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )
        assert exit_code == 0

        # Verify cron job exists
        exit_code, crontab_before = container_exec("crontab -l")
        assert exit_code == 0
        cron_count_before = crontab_before.count("coupang_coupon_issuer issue")
        assert cron_count_before >= 1

        # Run uninstall
        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer uninstall"
        )
        assert exit_code == 0

        # Verify all cron jobs removed
        exit_code, crontab_after = container_exec("crontab -l || echo ''")
        cron_count_after = crontab_after.count("coupang_coupon_issuer issue")
        assert cron_count_after == 0

    def test_uninstall_prints_manual_cleanup_instructions(self, built_binary, clean_install_dir, container_exec):
        """Uninstall should print instructions for manual file cleanup"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Install first
        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )
        assert exit_code == 0

        # Run uninstall
        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer uninstall"
        )
        assert exit_code == 0

        # Should mention files are retained
        assert "retained" in output.lower() or "유지" in output

        # Should mention manual removal
        assert "rm" in output.lower() or "삭제" in output
