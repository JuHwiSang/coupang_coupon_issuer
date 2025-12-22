"""
Integration tests for verify command with Python script.

Tests the script-based verify command in a real Docker environment.
"""

import pytest


@pytest.mark.e2e
class TestVerifyCommand:
    """Test verify command with Python script"""

    def test_verify_displays_table_output(self, python_script, clean_install_dir, sample_excel, container_exec):
        """Verify command should display table with all coupon details"""
        # Run verify (no file argument - always uses coupons.xlsx)
        exit_code, output = container_exec(
            f"python3 {python_script} verify {clean_install_dir}"
        )

        assert exit_code == 0
        assert "엑셀 파일 검증 중" in output
        assert "3개 쿠폰 로드 완료" in output
        assert "테스트쿠폰1" in output
        assert "테스트쿠폰2" in output
        assert "테스트쿠폰3" in output
        assert "검증 완료" in output

    def test_verify_shows_rate_discount(self, python_script, clean_install_dir, sample_excel, container_exec):
        """Verify should show RATE discount as percentage"""
        exit_code, output = container_exec(
            f"python3 {python_script} verify {clean_install_dir}"
        )

        assert exit_code == 0
        # Should show rate (10%) for 테스트쿠폰1
        assert "10" in output and "%" in output

    def test_verify_shows_price_discount_and_budget(self, python_script, clean_install_dir, sample_excel, container_exec):
        """Verify should show PRICE discount amount and calculate budget"""
        exit_code, output = container_exec(
            f"python3 {python_script} verify {clean_install_dir}"
        )

        assert exit_code == 0
        # Should show 500원 discount for 테스트쿠폰2
        assert "500" in output
        # Should show budget: 500 × 100 = 50,000
        assert "50,000" in output

    def test_verify_uses_default_excel_path(self, python_script, clean_install_dir, sample_excel, container_exec):
        """Verify should use ./coupons.xlsx by default"""
        # Run without specifying file
        exit_code, output = container_exec(
            f"python3 {python_script} verify {clean_install_dir}"
        )

        assert exit_code == 0
        assert "3개 쿠폰 로드 완료" in output

    def test_verify_fails_on_missing_file(self, python_script, clean_install_dir, container_exec):
        """Verify should fail when coupons.xlsx doesn't exist"""
        # Don't create any Excel file
        exit_code, output = container_exec(
            f"python3 {python_script} verify {clean_install_dir}"
        )

        assert exit_code != 0
        assert "ERROR" in output
        assert "찾을 수 없습니다" in output

    def test_verify_fails_on_invalid_excel(self, python_script, clean_install_dir, container_exec):
        """Verify should fail on Excel with missing columns"""
        # Create invalid coupons.xlsx (missing columns)
        create_invalid_excel = f"""
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.append(['쿠폰이름', '쿠폰타입'])  # Missing 5 columns
ws.append(['쿠폰1', '즉시할인'])
wb.save('{clean_install_dir}/coupons.xlsx')
"""
        container_exec(f"python3 -c \"{create_invalid_excel}\"", check=True)

        exit_code, output = container_exec(
            f"python3 {python_script} verify {clean_install_dir}"
        )

        assert exit_code != 0
        assert "ERROR" in output
        assert "필수 컬럼이 없습니다" in output
