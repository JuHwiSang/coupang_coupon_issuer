"""
Unit tests for issuer.py - CouponIssuer
"""
import pytest
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from openpyxl import Workbook

from coupang_coupon_issuer.issuer import CouponIssuer
from coupang_coupon_issuer.config import EXCEL_INPUT_FILE, COUPON_MAX_DISCOUNT, COUPON_CONTRACT_ID


@pytest.mark.unit
class TestCouponIssuerInit:
    """Test CouponIssuer initialization"""

    def test_init_with_explicit_credentials(self):
        """Initialize with explicit credential parameters"""
        issuer = CouponIssuer(
            access_key="test-access",
            secret_key="test-secret",
            user_id="test-user",
            vendor_id="test-vendor"
        )

        assert issuer.access_key == "test-access"
        assert issuer.secret_key == "test-secret"
        assert issuer.user_id == "test-user"
        assert issuer.vendor_id == "test-vendor"

    def test_init_from_env_variables(self, monkeypatch):
        """Fallback to environment variables when args not provided"""
        monkeypatch.setenv("COUPANG_ACCESS_KEY", "env-access")
        monkeypatch.setenv("COUPANG_SECRET_KEY", "env-secret")
        monkeypatch.setenv("COUPANG_USER_ID", "env-user")
        monkeypatch.setenv("COUPANG_VENDOR_ID", "env-vendor")

        issuer = CouponIssuer()

        assert issuer.access_key == "env-access"
        assert issuer.secret_key == "env-secret"
        assert issuer.user_id == "env-user"
        assert issuer.vendor_id == "env-vendor"

    def test_init_missing_api_keys(self):
        """Raise ValueError when API keys missing"""
        with pytest.raises(ValueError) as exc_info:
            CouponIssuer(
                access_key=None,
                secret_key=None,
                user_id="user",
                vendor_id="vendor"
            )

        assert "API 키가 설정되지 않았습니다" in str(exc_info.value)

    def test_init_missing_coupon_info(self):
        """Raise ValueError when user_id or vendor_id missing"""
        with pytest.raises(ValueError) as exc_info:
            CouponIssuer(
                access_key="access",
                secret_key="secret",
                user_id=None,
                vendor_id=None
            )

        assert "쿠폰 정보가 설정되지 않았습니다" in str(exc_info.value)


@pytest.mark.unit
class TestExcelParsing:
    """Test _fetch_coupons_from_excel() method"""

    def test_fetch_coupons_valid_file(self, tmp_path):
        """Read valid Excel file with 6 columns"""
        excel_file = tmp_path / "valid.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["테스트쿠폰1", "즉시할인", 30, "RATE", 10, ""])  # 즉시할인: 발급개수 빈값
        ws.append(["테스트쿠폰2", "다운로드쿠폰", 15, "PRICE", 500, 100])  # 다운로드: 할인 + 발급개수
        wb.save(excel_file)

        issuer = CouponIssuer(
            access_key="test-access",
            secret_key="test-secret",
            user_id="test-user",
            vendor_id="test-vendor"
        )

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            coupons = issuer._fetch_coupons_from_excel()

            assert len(coupons) == 2

            assert coupons[0]['name'] == "테스트쿠폰1"
            assert coupons[0]['type'] == "즉시할인"
            assert coupons[0]['validity_days'] == 30
            assert coupons[0]['discount_type'] == "RATE"
            assert coupons[0]['discount'] == 10  # Column E
            assert coupons[0]['issue_count'] is None  # 즉시할인: None

            assert coupons[1]['name'] == "테스트쿠폰2"
            assert coupons[1]['type'] == "다운로드쿠폰"
            assert coupons[1]['validity_days'] == 15
            assert coupons[1]['discount_type'] == "PRICE"
            assert coupons[1]['discount'] == 500  # Column E
            assert coupons[1]['issue_count'] == 100  # Column F

    def test_fetch_coupons_missing_columns(self, tmp_path):
        """Raise ValueError when required columns missing"""
        excel_file = tmp_path / "invalid_columns.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간"])  # Missing 2 columns
        ws.append(["쿠폰1", "즉시할인", 30])
        wb.save(excel_file)

        issuer = CouponIssuer(
            access_key="test-access",
            secret_key="test-secret",
            user_id="test-user",
            vendor_id="test-vendor"
        )

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            with pytest.raises(ValueError) as exc_info:
                issuer._fetch_coupons_from_excel()

            assert "필수 컬럼이 없습니다" in str(exc_info.value)

    def test_fetch_coupons_empty_rows_skipped(self, tmp_path):
        """Verify empty rows are skipped"""
        excel_file = tmp_path / "with_empty_rows.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["쿠폰1", "즉시할인", 30, "RATE", 50, ""])
        ws.append([None, None, None, None, None, None])  # Empty row
        ws.append(["쿠폰2", "다운로드쿠폰", 15, "PRICE", 1000, 100])
        wb.save(excel_file)

        issuer = CouponIssuer(
            access_key="test-access",
            secret_key="test-secret",
            user_id="test-user",
            vendor_id="test-vendor"
        )

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            coupons = issuer._fetch_coupons_from_excel()

            # Only 2 coupons, empty row skipped
            assert len(coupons) == 2

    def test_fetch_coupons_file_not_found(self, tmp_path):
        """Raise FileNotFoundError when Excel file doesn't exist"""
        nonexistent_file = tmp_path / "nonexistent.xlsx"

        issuer = CouponIssuer(
            access_key="test-access",
            secret_key="test-secret",
            user_id="test-user",
            vendor_id="test-vendor"
        )

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', nonexistent_file):
            with pytest.raises(FileNotFoundError) as exc_info:
                issuer._fetch_coupons_from_excel()

            assert "엑셀 파일이 없습니다" in str(exc_info.value)


@pytest.mark.unit
class TestInputNormalization:
    """Test input normalization logic (ADR 002)"""

    def test_normalize_coupon_name_strip(self, tmp_path):
        """Coupon name should be stripped of whitespace"""
        excel_file = tmp_path / "name_strip.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["  테스트쿠폰  ", "즉시할인", 30, "RATE", 50, ""])
        wb.save(excel_file)

        issuer = CouponIssuer("a", "s", "u", "v")

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            coupons = issuer._fetch_coupons_from_excel()

            assert coupons[0]['name'] == "테스트쿠폰"  # Stripped

    def test_normalize_coupon_type_whitespace_removal(self, tmp_path):
        """Coupon type whitespace should be removed"""
        excel_file = tmp_path / "type_normalize.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["쿠폰1", "즉 시 할 인", 30, "RATE", 50, ""])
        ws.append(["쿠폰2", "다운로 드쿠폰", 15, "PRICE", 1000, 100])
        wb.save(excel_file)

        issuer = CouponIssuer("a", "s", "u", "v")

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            coupons = issuer._fetch_coupons_from_excel()

            assert coupons[0]['type'] == "즉시할인"
            assert coupons[1]['type'] == "다운로드쿠폰"

    def test_normalize_validity_period_extract_numbers(self, tmp_path):
        """Extract numbers from validity period strings"""
        excel_file = tmp_path / "validity_normalize.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["쿠폰1", "즉시할인", "30일", "RATE", 50, ""])
        ws.append(["쿠폰2", "다운로드쿠폰", "15 days", "PRICE", 1000, 100])
        wb.save(excel_file)

        issuer = CouponIssuer("a", "s", "u", "v")

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            coupons = issuer._fetch_coupons_from_excel()

            assert coupons[0]['validity_days'] == 30
            assert coupons[1]['validity_days'] == 15

    def test_normalize_discount_method_uppercase(self, tmp_path):
        """Discount method should be normalized to uppercase"""
        excel_file = tmp_path / "discount_normalize.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["쿠폰1", "즉시할인", 30, "rate", 50, ""])
        ws.append(["쿠폰2", "다운로드쿠폰", 15, "fixed-with-quantity", 3, 1000])
        ws.append(["쿠폰3", "즉시할인", 7, "price", 100, ""])
        wb.save(excel_file)

        issuer = CouponIssuer("a", "s", "u", "v")

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            coupons = issuer._fetch_coupons_from_excel()

            assert coupons[0]['discount_type'] == "RATE"
            assert coupons[1]['discount_type'] == "FIXED_WITH_QUANTITY"
            assert coupons[2]['discount_type'] == "PRICE"

    def test_normalize_quantity_extract_numbers(self, tmp_path):
        """Extract numbers from discount and issue count strings"""
        excel_file = tmp_path / "quantity_normalize.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["쿠폰1", "즉시할인", 30, "RATE", "10%", ""])
        ws.append(["쿠폰2", "다운로드쿠폰", 15, "PRICE", "500 원", "100개"])
        wb.save(excel_file)

        issuer = CouponIssuer("a", "s", "u", "v")

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            coupons = issuer._fetch_coupons_from_excel()

            # Column E: 할인금액/비율
            assert coupons[0]['discount'] == 10  # "10%" → 10
            assert coupons[1]['discount'] == 500  # "500 원" → 500

            # Column F: 발급개수
            assert coupons[0]['issue_count'] is None  # 즉시할인: None
            assert coupons[1]['issue_count'] == 100  # "100개" → 100


@pytest.mark.unit
class TestValidation:
    """Test validation rules"""

    def test_validate_rate_range_1_to_99(self, tmp_path):
        """RATE discount must be between 1-99"""
        # Valid cases
        excel_file = tmp_path / "valid_rates.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["쿠폰1", "즉시할인", 30, "RATE", 1, ""])
        ws.append(["쿠폰2", "즉시할인", 30, "RATE", 50, ""])
        ws.append(["쿠폰3", "즉시할인", 30, "RATE", 99, ""])
        wb.save(excel_file)

        issuer = CouponIssuer("a", "s", "u", "v")

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            coupons = issuer._fetch_coupons_from_excel()
            assert len(coupons) == 3  # All valid

        # Invalid: 0%
        excel_file_invalid = tmp_path / "invalid_rate_0.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["쿠폰1", "즉시할인", 30, "RATE", 0, ""])
        wb.save(excel_file_invalid)

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file_invalid):
            with pytest.raises(ValueError) as exc_info:
                issuer._fetch_coupons_from_excel()
            # 0 value triggers the general "> 0" validation before RATE-specific validation
            assert "할인금액/비율은 0보다 커야 합니다" in str(exc_info.value)

        # Invalid: 100%
        excel_file_invalid2 = tmp_path / "invalid_rate_100.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["쿠폰1", "즉시할인", 30, "RATE", 100, ""])
        wb.save(excel_file_invalid2)

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file_invalid2):
            with pytest.raises(ValueError) as exc_info:
                issuer._fetch_coupons_from_excel()
            assert "RATE 할인율은 1~99 사이여야 합니다" in str(exc_info.value)

    def test_validate_price_minimum_10_won(self, tmp_path):
        """PRICE discount must be >= 10 won"""
        # Valid
        excel_file = tmp_path / "valid_price.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["쿠폰1", "즉시할인", 30, "PRICE", 10, ""])
        ws.append(["쿠폰2", "즉시할인", 30, "PRICE", 100, ""])
        wb.save(excel_file)

        issuer = CouponIssuer("a", "s", "u", "v")

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            coupons = issuer._fetch_coupons_from_excel()
            assert len(coupons) == 2

        # Invalid: < 10
        excel_file_invalid = tmp_path / "invalid_price_min.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["쿠폰1", "즉시할인", 30, "PRICE", 5, ""])
        wb.save(excel_file_invalid)

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file_invalid):
            with pytest.raises(ValueError) as exc_info:
                issuer._fetch_coupons_from_excel()
            assert "PRICE 할인금액은 최소 10원 이상이어야 합니다" in str(exc_info.value)

    def test_validate_price_10_won_units(self, tmp_path):
        """PRICE discount must be in 10-won units"""
        # Valid
        excel_file = tmp_path / "valid_price_units.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["쿠폰1", "즉시할인", 30, "PRICE", 10, ""])
        ws.append(["쿠폰2", "즉시할인", 30, "PRICE", 20, ""])
        ws.append(["쿠폰3", "즉시할인", 30, "PRICE", 100, ""])
        wb.save(excel_file)

        issuer = CouponIssuer("a", "s", "u", "v")

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            coupons = issuer._fetch_coupons_from_excel()
            assert len(coupons) == 3

        # Invalid: not 10-won unit
        excel_file_invalid = tmp_path / "invalid_price_units.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["쿠폰1", "즉시할인", 30, "PRICE", 15, ""])
        wb.save(excel_file_invalid)

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file_invalid):
            with pytest.raises(ValueError) as exc_info:
                issuer._fetch_coupons_from_excel()
            assert "PRICE 할인금액은 10원 단위여야 합니다" in str(exc_info.value)


@pytest.mark.unit
class TestIssuanceWorkflow:
    """Test issue() and _issue_single_coupon() methods"""

    def test_issue_single_coupon_instant_discount(self, tmp_path, requests_mock):
        """Test instant discount coupon creation"""
        excel_file = tmp_path / "instant.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["즉시할인쿠폰", "즉시할인", 30, "PRICE", 1000, ""])
        wb.save(excel_file)

        # Mock API
        requests_mock.post(
            "https://api-gateway.coupang.com/v2/providers/fms/apis/api/v2/vendors/test-vendor/coupon",
            status_code=200,
            json={"code": 200, "data": {"requestedId": "instant-123"}}
        )

        issuer = CouponIssuer("a", "s", "u", "test-vendor")

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            issuer.issue()

        # Verify API was called
        assert requests_mock.call_count == 1

        # Verify request payload
        request_body = requests_mock.last_request.json()
        assert request_body["name"] == "즉시할인쿠폰"
        assert request_body["contractId"] == "-1"
        assert request_body["maxDiscountPrice"] == str(COUPON_MAX_DISCOUNT)
        assert request_body["discount"] == "1000"
        assert request_body["type"] == "PRICE"

    def test_issue_single_coupon_download_coupon(self, tmp_path, requests_mock):
        """Test download coupon creation"""
        excel_file = tmp_path / "download.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["다운로드쿠폰", "다운로드쿠폰", 15, "RATE", 50, 100])
        wb.save(excel_file)

        # Mock API
        requests_mock.post(
            "https://api-gateway.coupang.com/v2/providers/marketplace_openapi/apis/api/v1/coupons",
            status_code=200,
            json={"code": 200, "data": {"couponId": "download-456"}}
        )

        issuer = CouponIssuer("a", "s", "test-user", "v")

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            issuer.issue()

        # Verify API was called
        assert requests_mock.call_count == 1

        # Verify request payload
        request_body = requests_mock.last_request.json()
        assert request_body["title"] == "다운로드쿠폰"
        assert request_body["contractId"] == COUPON_CONTRACT_ID
        assert request_body["couponType"] == "DOWNLOAD"
        assert request_body["userId"] == "test-user"
        assert len(request_body["policies"]) == 1
        assert request_body["policies"][0]["discount"] == 50

    def test_issue_handles_api_failure(self, tmp_path, requests_mock, capsys):
        """Test error handling when API call fails"""
        excel_file = tmp_path / "fail.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["실패쿠폰", "즉시할인", 30, "PRICE", 1000, ""])
        wb.save(excel_file)

        # Mock API failure
        requests_mock.post(
            "https://api-gateway.coupang.com/v2/providers/fms/apis/api/v2/vendors/test-vendor/coupon",
            status_code=200,
            json={"code": 500, "errorMessage": "Internal error"}
        )

        issuer = CouponIssuer("a", "s", "u", "test-vendor")

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            issuer.issue()

        # Verify log contains [FAIL] marker
        captured = capsys.readouterr()
        assert "[FAIL]" in captured.out
        assert "실패쿠폰" in captured.out

    def test_issue_mixed_success_failure(self, tmp_path, requests_mock, capsys):
        """Test mixed success and failure scenario"""
        excel_file = tmp_path / "mixed.xlsx"
        wb = Workbook()
        ws = wb.active
        assert ws is not None
        ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
        ws.append(["성공쿠폰1", "즉시할인", 30, "PRICE", 1000, ""])
        ws.append(["성공쿠폰2", "즉시할인", 30, "PRICE", 2000, ""])
        ws.append(["성공쿠폰3", "즉시할인", 30, "PRICE", 3000, ""])
        ws.append(["실패쿠폰", "즉시할인", 30, "PRICE", 4000, ""])
        wb.save(excel_file)

        # Mock API: first 3 succeed, last one fails
        def custom_matcher(request, context):
            body = request.json()
            if body["discount"] == "4000":
                return {"code": 500, "errorMessage": "Error"}
            return {"code": 200, "data": {"requestedId": f"id-{body['discount']}"}}

        requests_mock.post(
            "https://api-gateway.coupang.com/v2/providers/fms/apis/api/v2/vendors/test-vendor/coupon",
            json=custom_matcher
        )

        issuer = CouponIssuer("a", "s", "u", "test-vendor")

        with patch('coupang_coupon_issuer.issuer.EXCEL_INPUT_FILE', excel_file):
            issuer.issue()

        # Verify summary log
        captured = capsys.readouterr()
        assert "성공: 3, 실패: 1" in captured.out
        assert "[OK] 성공쿠폰1" in captured.out
        assert "[OK] 성공쿠폰2" in captured.out
        assert "[OK] 성공쿠폰3" in captured.out
        assert "[FAIL] 실패쿠폰" in captured.out
