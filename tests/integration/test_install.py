"""
Integration tests for install command with PyInstaller binary.

Tests the single-binary install command in a real Docker environment.
"""

import pytest
import json


@pytest.mark.integration
class TestInstallCommand:
    """Test install command with PyInstaller binary"""

    def test_install_creates_config_json(self, built_binary, clean_install_dir, container_exec):
        """Install should create config.json with credentials and UUID"""
        # Copy binary to install directory
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Run install
        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )

        assert exit_code == 0

        # Verify config.json exists
        exit_code, _ = container_exec(f"test -f {clean_install_dir}/config.json")
        assert exit_code == 0

        # Verify config.json content
        exit_code, config_content = container_exec(f"cat {clean_install_dir}/config.json")
        assert exit_code == 0

        config = json.loads(config_content)
        assert config["access_key"] == "test-access"
        assert config["secret_key"] == "test-secret"
        assert config["user_id"] == "test-user"
        assert config["vendor_id"] == "test-vendor"
        assert "installation_id" in config
        assert len(config["installation_id"]) == 36  # UUID format

    def test_install_creates_cron_job_with_uuid(self, built_binary, clean_install_dir, container_exec):
        """Install should create cron job with UUID marker in comment"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Run install
        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )

        assert exit_code == 0

        # Get UUID from config.json
        exit_code, config_content = container_exec(f"cat {clean_install_dir}/config.json")
        config = json.loads(config_content)
        installation_id = config["installation_id"]

        # Verify crontab contains UUID marker
        exit_code, crontab_content = container_exec("crontab -l")
        assert exit_code == 0
        assert f"# coupang_coupon_issuer_job:{installation_id}" in crontab_content

    def test_install_creates_correct_cron_schedule(self, built_binary, clean_install_dir, container_exec):
        """Install should create cron job with daily schedule (0 0 * * *)"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )

        assert exit_code == 0

        # Verify crontab schedule
        exit_code, crontab_content = container_exec("crontab -l")
        assert exit_code == 0
        assert "0 0 * * *" in crontab_content  # Daily at midnight

    def test_install_cron_job_points_to_correct_binary(self, built_binary, clean_install_dir, container_exec):
        """Install should create cron job pointing to absolute path of binary"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )

        assert exit_code == 0

        # Verify crontab contains absolute path
        exit_code, crontab_content = container_exec("crontab -l")
        assert exit_code == 0
        assert f"{clean_install_dir}/coupang_coupon_issuer issue" in crontab_content

    def test_install_with_jitter_adds_jitter_flag(self, built_binary, clean_install_dir, container_exec):
        """Install with --jitter-max should add flag to cron command"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor "
            f"--jitter-max 60"
        )

        assert exit_code == 0

        # Verify crontab contains jitter flag
        exit_code, crontab_content = container_exec("crontab -l")
        assert exit_code == 0
        assert "--jitter-max 60" in crontab_content

    def test_install_validates_jitter_range(self, built_binary, clean_install_dir, container_exec):
        """Install should reject jitter_max outside 1-120 range"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Try with invalid jitter (150 > 120)
        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor "
            f"--jitter-max 150"
        )

        assert exit_code != 0
        assert "ERROR" in output
        assert "1-120 범위" in output

    def test_reinstall_removes_old_cron_job(self, built_binary, clean_install_dir, container_exec):
        """Reinstalling should remove old cron job and create new one"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # First install
        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )
        assert exit_code == 0

        # Get first UUID
        exit_code, config_content = container_exec(f"cat {clean_install_dir}/config.json")
        first_config = json.loads(config_content)
        first_uuid = first_config["installation_id"]

        # Second install (reinstall)
        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key new-access --secret-key new-secret "
            f"--user-id new-user --vendor-id new-vendor"
        )
        assert exit_code == 0

        # Get second UUID
        exit_code, config_content = container_exec(f"cat {clean_install_dir}/config.json")
        second_config = json.loads(config_content)
        second_uuid = second_config["installation_id"]

        # UUIDs should be different
        assert first_uuid != second_uuid

        # Verify only new UUID in crontab
        exit_code, crontab_content = container_exec("crontab -l")
        assert exit_code == 0
        assert f"# coupang_coupon_issuer_job:{second_uuid}" in crontab_content
        assert f"# coupang_coupon_issuer_job:{first_uuid}" not in crontab_content

        # Count cron job entries (should be exactly 1)
        exit_code, count_output = container_exec(
            "crontab -l | grep -c 'coupang_coupon_issuer issue' || true"
        )
        count = int(count_output.strip())
        assert count == 1

    def test_install_requires_all_4_parameters(self, built_binary, clean_install_dir, container_exec):
        """Install should fail if any of the 4 required parameters is missing"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Missing --user-id
        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--vendor-id test-vendor"
        )

        assert exit_code != 0
        assert "error" in output.lower()
        assert "--user-id" in output

    def test_install_enables_cron_service(self, built_binary, clean_install_dir, container_exec):
        """Install should ensure cron service is running"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Kill all cron processes (CMD will restart cron -f, but we test if install also starts it)
        container_exec("pkill -9 cron || true")
        container_exec("sleep 1")  # Wait for process to die

        # Verify cron is actually stopped
        exit_code, _ = container_exec("pgrep -x cron || pgrep -x crond")
        assert exit_code != 0, "Cron should be stopped before test"

        # Run install (should start cron via service cron start)
        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )

        assert exit_code == 0

        # Verify cron service is now running (install should have started it)
        container_exec("sleep 2")  # Wait for service to start
        exit_code, output = container_exec("pgrep -x cron || pgrep -x crond")
        assert exit_code == 0, f"Cron not running after install: {output}"

    def test_install_sets_correct_config_permissions(self, built_binary, clean_install_dir, container_exec):
        """Install should set config.json permissions to 600 (owner read/write only)"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        exit_code, _ = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer install "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )

        assert exit_code == 0

        # Check permissions (should be 600)
        exit_code, perms = container_exec(f"stat -c '%a' {clean_install_dir}/config.json")
        assert exit_code == 0
        assert perms.strip() == "600"
