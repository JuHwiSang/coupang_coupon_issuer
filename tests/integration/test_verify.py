"""
Integration tests for verify command with PyInstaller binary.

Tests the single-binary verify command in a real Docker environment.
"""

import pytest


@pytest.mark.integration
class TestVerifyCommand:
    """Test verify command with PyInstaller binary"""

    def test_verify_displays_table_output(self, built_binary, clean_install_dir, sample_excel, container_exec):
        """Verify command should display table with all coupon details"""
        # Copy binary to install directory
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Run verify
        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer verify ./coupons.xlsx"
        )

        assert exit_code == 0
        assert "엑셀 파일 검증 중" in output
        assert "3개 쿠폰 로드 완료" in output
        assert "테스트쿠폰1" in output
        assert "테스트쿠폰2" in output
        assert "테스트쿠폰3" in output
        assert "검증 완료" in output

    def test_verify_shows_rate_discount(self, built_binary, clean_install_dir, sample_excel, container_exec):
        """Verify should show RATE discount as percentage"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer verify"
        )

        assert exit_code == 0
        # Should show rate (10%) for 테스트쿠폰1
        assert "10" in output and "%" in output

    def test_verify_shows_price_discount_and_budget(self, built_binary, clean_install_dir, sample_excel, container_exec):
        """Verify should show PRICE discount amount and calculate budget"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer verify"
        )

        assert exit_code == 0
        # Should show 500원 discount for 테스트쿠폰2
        assert "500" in output
        # Should show budget: 500 × 100 = 50,000
        assert "50,000" in output

    def test_verify_uses_default_excel_path(self, built_binary, clean_install_dir, sample_excel, container_exec):
        """Verify should use ./coupons.xlsx by default"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Run without specifying file
        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer verify"
        )

        assert exit_code == 0
        assert "3개 쿠폰 로드 완료" in output

    def test_verify_fails_on_missing_file(self, built_binary, clean_install_dir, container_exec):
        """Verify should fail when Excel file doesn't exist"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer verify nonexistent.xlsx"
        )

        assert exit_code != 0
        assert "ERROR" in output
        assert "찾을 수 없습니다" in output

    def test_verify_fails_on_invalid_excel(self, built_binary, clean_install_dir, container_exec):
        """Verify should fail on Excel with missing columns"""
        container_exec(f"cp {built_binary} {clean_install_dir}/", check=True)
        container_exec(f"chmod +x {clean_install_dir}/coupang_coupon_issuer", check=True)

        # Create invalid Excel (missing columns)
        create_invalid_excel = f"""
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.append(['쿠폰이름', '쿠폰타입'])  # Missing 4 columns
ws.append(['쿠폰1', '즉시할인'])
wb.save('{clean_install_dir}/invalid.xlsx')
"""
        container_exec(f"python3 -c \"{create_invalid_excel}\"", check=True)

        exit_code, output = container_exec(
            f"cd {clean_install_dir} && ./coupang_coupon_issuer verify invalid.xlsx"
        )

        assert exit_code != 0
        assert "ERROR" in output
        assert "필수 컬럼이 없습니다" in output
