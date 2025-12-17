"""
Unit tests for coupang_api.py - CoupangAPIClient
"""
import pytest
import time
from datetime import datetime
from unittest.mock import patch, MagicMock
import requests

from coupang_coupon_issuer.coupang_api import CoupangAPIClient


@pytest.mark.unit
class TestHMACSignature:
    """Test HMAC-SHA256 signature generation"""

    def test_generate_hmac_format(self):
        """Verify CEA algorithm format in Authorization header"""
        client = CoupangAPIClient("test-access-key", "test-secret-key")

        # Freeze time for deterministic output
        with patch('time.strftime') as mock_strftime:
            mock_strftime.side_effect = lambda fmt: {
                '%y%m%d': '241217',
                '%H%M%S': '120000'
            }[fmt]

            auth_header = client._generate_hmac("POST", "/v2/test/path")

            # Verify format
            assert auth_header.startswith("CEA algorithm=HmacSHA256")
            assert "access-key=test-access-key" in auth_header
            assert "signed-date=241217T120000Z" in auth_header
            assert "signature=" in auth_header

    def test_generate_hmac_deterministic(self):
        """Same input should produce same signature"""
        client = CoupangAPIClient("access", "secret")

        with patch('time.strftime') as mock_strftime:
            mock_strftime.side_effect = lambda fmt: {
                '%y%m%d': '241217',
                '%H%M%S': '120000'
            }[fmt]

            sig1 = client._generate_hmac("GET", "/api/test")
            sig2 = client._generate_hmac("GET", "/api/test")

            assert sig1 == sig2

    def test_generate_hmac_with_query_string(self):
        """Verify query string is included in HMAC calculation"""
        client = CoupangAPIClient("access", "secret")

        with patch('time.strftime') as mock_strftime:
            mock_strftime.side_effect = lambda fmt: {
                '%y%m%d': '241217',
                '%H%M%S': '120000'
            }[fmt]

            sig_without = client._generate_hmac("GET", "/api/test", query="")
            sig_with = client._generate_hmac("GET", "/api/test", query="?foo=bar")

            # Signatures should be different
            assert sig_without != sig_with


@pytest.mark.unit
class TestAPIRequest:
    """Test _request() method"""

    def test_request_success(self, requests_mock):
        """Mock successful HTTP 200 response"""
        client = CoupangAPIClient("test-access", "test-secret")

        requests_mock.post(
            "https://api-gateway.coupang.com/v2/test/path",
            status_code=200,
            json={"code": 200, "data": "success"}
        )

        result = client._request("POST", "/v2/test/path", json_data={"foo": "bar"})

        assert result["code"] == 200
        assert result["data"] == "success"

    def test_request_timeout(self, requests_mock):
        """Mock timeout exception"""
        client = CoupangAPIClient("test-access", "test-secret")

        requests_mock.post(
            "https://api-gateway.coupang.com/v2/test/path",
            exc=requests.Timeout("Connection timeout")
        )

        with pytest.raises(requests.Timeout):
            client._request("POST", "/v2/test/path", timeout=5)

    def test_request_network_error(self, requests_mock):
        """Mock general RequestException"""
        client = CoupangAPIClient("test-access", "test-secret")

        requests_mock.post(
            "https://api-gateway.coupang.com/v2/test/path",
            exc=requests.ConnectionError("Network error")
        )

        with pytest.raises(requests.ConnectionError):
            client._request("POST", "/v2/test/path")

    def test_request_http_error_400(self, requests_mock):
        """Mock 400 Bad Request response"""
        client = CoupangAPIClient("test-access", "test-secret")

        requests_mock.post(
            "https://api-gateway.coupang.com/v2/test/path",
            status_code=400,
            json={"error": "Bad Request"}
        )

        with pytest.raises(requests.HTTPError):
            client._request("POST", "/v2/test/path")

    def test_request_api_error_code(self, requests_mock):
        """Mock HTTP 200 but API code != 200 (API-level error)"""
        client = CoupangAPIClient("test-access", "test-secret")

        requests_mock.post(
            "https://api-gateway.coupang.com/v2/test/path",
            status_code=200,
            json={"code": 500, "errorMessage": "Internal API error"}
        )

        with pytest.raises(ValueError) as exc_info:
            client._request("POST", "/v2/test/path")

        assert "API Error (code 500)" in str(exc_info.value)
        assert "Internal API error" in str(exc_info.value)


@pytest.mark.unit
class TestInstantCoupon:
    """Test create_instant_coupon()"""

    def test_create_instant_coupon_success(self, requests_mock):
        """Mock successful instant coupon creation"""
        client = CoupangAPIClient("test-access", "test-secret")

        vendor_id = "A00012345"
        requests_mock.post(
            f"https://api-gateway.coupang.com/v2/providers/fms/apis/api/v2/vendors/{vendor_id}/coupon",
            status_code=200,
            json={"code": 200, "requestedId": "instant-123"}
        )

        result = client.create_instant_coupon(
            vendor_id=vendor_id,
            contract_id=-1,
            name="Test Coupon",
            max_discount_price=100000,
            discount=1000,
            start_at="2024-01-01 00:00:00",
            end_at="2024-01-31 23:59:59",
            coupon_type="PRICE"
        )

        assert result["code"] == 200
        assert result["requestedId"] == "instant-123"

        # Verify request payload
        request_body = requests_mock.last_request.json()
        assert request_body["contractId"] == "-1"  # String conversion
        assert request_body["name"] == "Test Coupon"
        assert request_body["maxDiscountPrice"] == "100000"
        assert request_body["discount"] == "1000"
        assert request_body["type"] == "PRICE"

    def test_create_instant_coupon_rate_discount(self, requests_mock):
        """Test RATE type discount"""
        client = CoupangAPIClient("test-access", "test-secret")

        vendor_id = "A00012345"
        requests_mock.post(
            f"https://api-gateway.coupang.com/v2/providers/fms/apis/api/v2/vendors/{vendor_id}/coupon",
            status_code=200,
            json={"code": 200, "requestedId": "rate-456"}
        )

        result = client.create_instant_coupon(
            vendor_id=vendor_id,
            contract_id=-1,
            name="Rate Discount",
            max_discount_price=100000,
            discount=50,  # 50% off
            start_at="2024-01-01 00:00:00",
            end_at="2024-01-31 23:59:59",
            coupon_type="RATE"
        )

        assert result["requestedId"] == "rate-456"

        # Verify RATE type
        request_body = requests_mock.last_request.json()
        assert request_body["type"] == "RATE"
        assert request_body["discount"] == "50"


@pytest.mark.unit
class TestDownloadCoupon:
    """Test create_download_coupon()"""

    def test_create_download_coupon_success(self, requests_mock):
        """Mock successful download coupon creation"""
        client = CoupangAPIClient("test-access", "test-secret")

        requests_mock.post(
            "https://api-gateway.coupang.com/v2/providers/marketplace_openapi/apis/api/v1/coupons",
            status_code=200,
            json={"code": 200, "couponId": "download-789"}
        )

        policies = [
            {
                "title": "Policy 1",
                "typeOfDiscount": "PRICE",
                "description": "Description",
                "minimumPrice": 10000,
                "discount": 1000,
                "maximumDiscountPrice": 1000,
                "maximumPerDaily": 1
            }
        ]

        result = client.create_download_coupon(
            contract_id=-1,
            title="Download Test Coupon",
            start_date="2024-01-01 00:00:00",
            end_date="2024-01-31 23:59:59",
            user_id="test-user-id",
            policies=policies
        )

        assert result["code"] == 200
        assert result["couponId"] == "download-789"

        # Verify request payload
        request_body = requests_mock.last_request.json()
        assert request_body["title"] == "Download Test Coupon"
        assert request_body["contractId"] == -1
        assert request_body["couponType"] == "DOWNLOAD"
        assert request_body["userId"] == "test-user-id"
        assert len(request_body["policies"]) == 1
        assert request_body["policies"][0]["typeOfDiscount"] == "PRICE"

    def test_create_download_coupon_multiple_policies(self, requests_mock):
        """Test with multiple policies (max 3)"""
        client = CoupangAPIClient("test-access", "test-secret")

        requests_mock.post(
            "https://api-gateway.coupang.com/v2/providers/marketplace_openapi/apis/api/v1/coupons",
            status_code=200,
            json={"code": 200, "couponId": "multi-policy-123"}
        )

        policies = [
            {
                "title": "Policy 1",
                "typeOfDiscount": "PRICE",
                "description": "Desc 1",
                "minimumPrice": 10000,
                "discount": 1000,
                "maximumDiscountPrice": 1000,
                "maximumPerDaily": 1
            },
            {
                "title": "Policy 2",
                "typeOfDiscount": "RATE",
                "description": "Desc 2",
                "minimumPrice": 20000,
                "discount": 10,
                "maximumDiscountPrice": 5000,
                "maximumPerDaily": 2
            },
            {
                "title": "Policy 3",
                "typeOfDiscount": "PRICE",
                "description": "Desc 3",
                "minimumPrice": 30000,
                "discount": 3000,
                "maximumDiscountPrice": 3000,
                "maximumPerDaily": 1
            }
        ]

        result = client.create_download_coupon(
            contract_id=-1,
            title="Multi Policy Coupon",
            start_date="2024-01-01 00:00:00",
            end_date="2024-01-31 23:59:59",
            user_id="test-user",
            policies=policies
        )

        assert result["couponId"] == "multi-policy-123"

        # Verify 3 policies
        request_body = requests_mock.last_request.json()
        assert len(request_body["policies"]) == 3


@pytest.mark.unit
class TestParameterHandling:
    """Test parameter encoding and fixed values"""

    def test_contract_id_negative_one(self, requests_mock):
        """Verify contractId = -1 is properly sent"""
        client = CoupangAPIClient("test-access", "test-secret")

        vendor_id = "A00012345"
        requests_mock.post(
            f"https://api-gateway.coupang.com/v2/providers/fms/apis/api/v2/vendors/{vendor_id}/coupon",
            status_code=200,
            json={"code": 200, "requestedId": "test"}
        )

        client.create_instant_coupon(
            vendor_id=vendor_id,
            contract_id=-1,
            name="Test",
            max_discount_price=100000,
            discount=1000,
            start_at="2024-01-01 00:00:00",
            end_at="2024-01-31 23:59:59",
            coupon_type="PRICE"
        )

        # Verify contractId in request
        request_body = requests_mock.last_request.json()
        assert request_body["contractId"] == "-1"

    def test_string_conversion_of_numbers(self, requests_mock):
        """Verify numeric values are converted to strings"""
        client = CoupangAPIClient("test-access", "test-secret")

        vendor_id = "A00012345"
        requests_mock.post(
            f"https://api-gateway.coupang.com/v2/providers/fms/apis/api/v2/vendors/{vendor_id}/coupon",
            status_code=200,
            json={"code": 200}
        )

        client.create_instant_coupon(
            vendor_id=vendor_id,
            contract_id=-1,
            name="Test",
            max_discount_price=100000,
            discount=1000,
            start_at="2024-01-01 00:00:00",
            end_at="2024-01-31 23:59:59"
        )

        request_body = requests_mock.last_request.json()

        # All numeric fields should be strings
        assert isinstance(request_body["contractId"], str)
        assert isinstance(request_body["maxDiscountPrice"], str)
        assert isinstance(request_body["discount"], str)

    def test_content_type_header(self, requests_mock):
        """Verify Content-Type header is set correctly"""
        client = CoupangAPIClient("test-access", "test-secret")

        requests_mock.post(
            "https://api-gateway.coupang.com/v2/test",
            status_code=200,
            json={"code": 200}
        )

        client._request("POST", "/v2/test", json_data={"test": "data"})

        # Verify headers
        headers = requests_mock.last_request.headers
        assert headers["Content-Type"] == "application/json;charset=UTF-8"
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("CEA algorithm=HmacSHA256")
