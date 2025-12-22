"""
Integration tests for install command with Python script.

Tests the script-based install command in a real Docker environment.
"""

import pytest
import json


@pytest.mark.integration
class TestInstallCommand:
    """Test install command with Python script"""

    def test_install_creates_config_json(self, python_script, clean_install_dir, container_exec):
        """Install should create config.json with credentials and UUID"""
        # Run install
        exit_code, output = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
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

    def test_install_creates_cron_job_with_uuid(self, python_script, clean_install_dir, container_exec):
        """Install should create cron job with UUID marker in comment"""
        # Run install
        exit_code, output = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
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

    def test_install_creates_correct_cron_schedule(self, python_script, clean_install_dir, container_exec):
        """Install should create cron job with daily schedule (0 0 * * *)"""
        exit_code, output = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )

        assert exit_code == 0

        # Verify crontab schedule
        exit_code, crontab_content = container_exec("crontab -l")
        assert exit_code == 0
        assert "0 0 * * *" in crontab_content  # Daily at midnight

    def test_install_cron_job_points_to_correct_script(self, python_script, clean_install_dir, container_exec):
        """Install should create cron job pointing to python3 main.py"""
        exit_code, output = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )

        assert exit_code == 0

        # Verify crontab contains python3 command with work directory
        exit_code, crontab_content = container_exec("crontab -l")
        assert exit_code == 0
        assert "python3" in crontab_content
        assert "main.py issue" in crontab_content
        assert clean_install_dir in crontab_content

    def test_install_with_jitter_adds_jitter_flag(self, python_script, clean_install_dir, container_exec):
        """Install with --jitter-max should add flag to cron command"""
        exit_code, output = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor "
            f"--jitter-max 60"
        )

        assert exit_code == 0

        # Verify crontab contains jitter flag
        exit_code, crontab_content = container_exec("crontab -l")
        assert exit_code == 0
        assert "--jitter-max 60" in crontab_content

    def test_install_validates_jitter_range(self, python_script, clean_install_dir, container_exec):
        """Install should reject jitter_max outside 1-120 range"""
        # Try with invalid jitter (150 > 120)
        exit_code, output = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor "
            f"--jitter-max 150"
        )

        assert exit_code != 0
        assert "ERROR" in output
        assert "1-120 범위" in output

    def test_reinstall_removes_old_cron_job(self, python_script, clean_install_dir, container_exec):
        """Reinstalling should remove old cron job and create new one"""
        # First install
        exit_code, _ = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
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
            f"python3 {python_script} install {clean_install_dir} "
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
            "crontab -l | grep -c 'main.py issue' || true"
        )
        count = int(count_output.strip())
        assert count == 1

    def test_install_sets_correct_config_permissions(self, python_script, clean_install_dir, container_exec):
        """Install should set config.json permissions to 600 (owner read/write only)"""
        exit_code, _ = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key test-access --secret-key test-secret "
            f"--user-id test-user --vendor-id test-vendor"
        )

        assert exit_code == 0

        # Check permissions (should be 600)
        exit_code, perms = container_exec(f"stat -c '%a' {clean_install_dir}/config.json")
        assert exit_code == 0
        assert perms.strip() == "600"
