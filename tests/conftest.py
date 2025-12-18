import json
import pytest
from pathlib import Path
from openpyxl import Workbook


@pytest.fixture
def temp_credentials(tmp_path):
    """Temporary credentials JSON file"""
    creds = {
        "access_key": "test-access-key",
        "secret_key": "test-secret-key",
        "user_id": "test-user-id",
        "vendor_id": "test-vendor-id"
    }
    file = tmp_path / "credentials.json"
    file.write_text(json.dumps(creds))
    return file


@pytest.fixture
def valid_excel(tmp_path):
    """Valid 6-column Excel file"""
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])
    ws.append(["테스트쿠폰1", "즉시할인", 30, "RATE", 10, ""])  # 즉시할인: 발급개수 빈값
    ws.append(["테스트쿠폰2", "다운로드쿠폰", 15, "PRICE", 500, 100])  # 다운로드: 할인 + 발급개수
    file = tmp_path / "valid.xlsx"
    wb.save(file)
    return file


@pytest.fixture
def mock_coupang_api(requests_mock):
    """Mock Coupang API responses"""
    requests_mock.post(
        "https://api-gateway.coupang.com/v2/providers/promotion_api/apis/api/v4/vendors/test-vendor-id/instant-discount-coupons",
        status_code=201,
        json={"couponId": "instant-123"}
    )
    requests_mock.post(
        "https://api-gateway.coupang.com/v2/providers/promotion_api/apis/api/v4/vendors/test-vendor-id/downloadable-coupons",
        status_code=201,
        json={"couponId": "download-456"}
    )
    return requests_mock


@pytest.fixture
def sample_credentials():
    """Sample credentials tuple"""
    return ("test-access-key", "test-secret-key", "test-user-id", "test-vendor-id")
