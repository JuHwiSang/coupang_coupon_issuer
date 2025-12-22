"""
Integration tests for issue command with Python script.

Tests the script-based issue command in a real Docker environment.
Requires .env file with actual Coupang API credentials.
"""

import pytest
import os


@pytest.fixture
def coupang_credentials():
    """
    Get Coupang API credentials from environment variables.

    Returns:
        dict: Credentials with keys: access_key, secret_key, user_id, vendor_id

    Raises:
        pytest.skip: If any credential is missing
    """
    access_key = os.getenv("COUPANG_ACCESS_KEY")
    secret_key = os.getenv("COUPANG_SECRET_KEY")
    user_id = os.getenv("COUPANG_USER_ID")
    vendor_id = os.getenv("COUPANG_VENDOR_ID")

    if not all([access_key, secret_key, user_id, vendor_id]):
        pytest.skip("Coupang API credentials not found in environment variables")

    return {
        "access_key": access_key,
        "secret_key": secret_key,
        "user_id": user_id,
        "vendor_id": vendor_id
    }


@pytest.mark.e2e
class TestIssueCommand:
    """Test issue command with Python script and real API calls"""

    def test_issue_with_real_api(self, python_script, clean_install_dir, sample_excel, container_exec, coupang_credentials):
        """Issue command should call real Coupang API and create coupons"""
        # Install first
        exit_code, _ = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key {coupang_credentials['access_key']} "
            f"--secret-key {coupang_credentials['secret_key']} "
            f"--user-id {coupang_credentials['user_id']} "
            f"--vendor-id {coupang_credentials['vendor_id']}"
        )
        assert exit_code == 0

        # Run issue
        exit_code, output = container_exec(
            f"python3 {python_script} issue {clean_install_dir}"
        )

        # Check exit code and output
        assert exit_code == 0
        assert "쿠폰 발급 시작" in output
        assert "쿠폰 발급 완료" in output

    def test_issue_with_jitter(self, python_script, clean_install_dir, sample_excel, container_exec, coupang_credentials):
        """Issue command with jitter should delay before issuing coupons"""
        # Install first
        exit_code, _ = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key {coupang_credentials['access_key']} "
            f"--secret-key {coupang_credentials['secret_key']} "
            f"--user-id {coupang_credentials['user_id']} "
            f"--vendor-id {coupang_credentials['vendor_id']}"
        )
        assert exit_code == 0

        # Run issue with short jitter (5 seconds for fast testing)
        exit_code, output = container_exec(
            f"python3 {python_script} issue {clean_install_dir} --jitter-max 5",
            timeout=30000  # 30 seconds timeout
        )

        # Check exit code and output
        assert exit_code == 0
        # Should see jitter messages
        assert "Jitter" in output or "대기" in output
        assert "쿠폰 발급 시작" in output

    def test_issue_fails_without_config(self, python_script, clean_install_dir, container_exec):
        """Issue command should fail when config.json doesn't exist"""
        # Run issue without installing first
        exit_code, output = container_exec(
            f"python3 {python_script} issue {clean_install_dir}"
        )

        # Should fail
        assert exit_code != 0
        assert "ERROR" in output
        assert "config.json" in output

    def test_issue_fails_with_missing_excel(self, python_script, clean_install_dir, container_exec, coupang_credentials):
        """Issue command should fail when coupons.xlsx doesn't exist"""
        # Install first
        exit_code, _ = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key {coupang_credentials['access_key']} "
            f"--secret-key {coupang_credentials['secret_key']} "
            f"--user-id {coupang_credentials['user_id']} "
            f"--vendor-id {coupang_credentials['vendor_id']}"
        )
        assert exit_code == 0

        # Remove Excel file (if it exists)
        container_exec(f"rm -f {clean_install_dir}/coupons.xlsx")

        # Run issue
        exit_code, output = container_exec(
            f"python3 {python_script} issue {clean_install_dir}"
        )

        # Should fail
        assert exit_code != 0
        assert "ERROR" in output

    def test_issue_creates_log_file(self, python_script, clean_install_dir, sample_excel, container_exec, coupang_credentials):
        """Issue command should create issuer.log file"""
        # Install first
        exit_code, _ = container_exec(
            f"python3 {python_script} install {clean_install_dir} "
            f"--access-key {coupang_credentials['access_key']} "
            f"--secret-key {coupang_credentials['secret_key']} "
            f"--user-id {coupang_credentials['user_id']} "
            f"--vendor-id {coupang_credentials['vendor_id']}"
        )
        assert exit_code == 0

        # Run issue
        exit_code, _ = container_exec(
            f"python3 {python_script} issue {clean_install_dir}"
        )
        assert exit_code == 0

        # Verify log file exists
        exit_code, _ = container_exec(f"test -f {clean_install_dir}/issuer.log")
        assert exit_code == 0

        # Verify log file contains entries
        exit_code, log_content = container_exec(f"cat {clean_install_dir}/issuer.log")
        assert exit_code == 0
        assert len(log_content.strip()) > 0
