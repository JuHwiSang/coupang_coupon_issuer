"""
Integration test fixtures for issue functionality.

Provides fixtures for testing the issue command with mocked external dependencies.
All external APIs (Coupang API) are mocked, but internal modules use real implementations.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import openpyxl


@pytest.fixture
def test_base_dir(tmp_path):
    """
    Create a temporary base directory for integration tests.
    
    Returns:
        Path: Temporary directory path
    """
    return tmp_path


@pytest.fixture
def mock_config(test_base_dir):
    """
    Mock ConfigManager.load_credentials to return test credentials.
    
    Returns:
        tuple: (access_key, secret_key, user_id, vendor_id)
    """
    test_credentials = (
        "test_access_key",
        "test_secret_key",
        "test_user_id",
        "test_vendor_id"
    )
    
    with patch('coupang_coupon_issuer.config.ConfigManager.load_credentials') as mock:
        mock.return_value = test_credentials
        yield test_credentials


@pytest.fixture
def test_excel_file(test_base_dir):
    """
    Create a test Excel file with sample coupon data.
    
    Returns:
        Path: Path to the created Excel file
    """
    excel_path = test_base_dir / "coupons.xlsx"
    
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # Headers
    ws.append(['쿠폰이름', '쿠폰타입', '쿠폰유효기간', '할인방식', '할인금액/비율', '발급개수', '옵션ID'])
    
    # Sample data
    ws.append(['테스트즉시할인', '즉시할인', 30, 'RATE', 10, '', '3226138951, 3226138847'])
    ws.append(['테스트다운로드', '다운로드쿠폰', 15, 'PRICE', 500, 100, '2306264997, 4802314648'])
    ws.append(['테스트고정할인', '다운로드쿠폰', 30, 'FIXED_WITH_QUANTITY', 1000, 50, '4230264914'])
    
    wb.save(excel_path)
    
    return excel_path


@pytest.fixture
def mock_coupang_api():
    """
    Mock CoupangAPIClient methods to return successful responses.
    
    Mocks the actual API methods called by CouponIssuer:
    - create_instant_coupon, get_instant_coupon_status, apply_instant_coupon
    - create_download_coupon, apply_download_coupon
    
    Yields:
        Mock: Mocked API client with predefined responses
    """
    # Patch where CoupangAPIClient is USED, not where it's defined
    with patch('coupang_coupon_issuer.issuer.CoupangAPIClient') as MockClient:
        # Create mock instance
        mock_instance = Mock()
        MockClient.return_value = mock_instance
        
        # Mock instant coupon workflow
        # Step 1: create_instant_coupon returns requestedId
        mock_instance.create_instant_coupon.return_value = {
            'data': {
                'content': {
                    'requestedId': 'REQ_INSTANT_12345'
                }
            }
        }
        
        # Step 2 & 4: get_instant_coupon_status returns DONE status
        mock_instance.get_instant_coupon_status.return_value = {
            'data': {
                'content': {
                    'status': 'DONE',
                    'couponId': 'INSTANT_COUPON_67890'
                }
            }
        }
        
        # Step 3: apply_instant_coupon returns requestedId
        mock_instance.apply_instant_coupon.return_value = {
            'data': {
                'content': {
                    'requestedId': 'REQ_APPLY_54321'
                }
            }
        }
        
        # Mock download coupon workflow
        # Step 1: create_download_coupon returns couponId directly
        mock_instance.create_download_coupon.return_value = {
            'couponId': 'DOWNLOAD_COUPON_11111'
        }
        
        # Step 2: apply_download_coupon returns SUCCESS
        mock_instance.apply_download_coupon.return_value = {
            'requestResultStatus': 'SUCCESS'
        }
        
        yield mock_instance


@pytest.fixture
def mock_coupang_api_with_error():
    """
    Mock CoupangAPIClient to return error responses.
    
    Yields:
        Mock: Mocked API client that returns errors
    """
    with patch('coupang_coupon_issuer.issuer.CoupangAPIClient') as MockClient:
        mock_instance = Mock()
        MockClient.return_value = mock_instance
        
        # Mock API error
        mock_instance.issue_instant_coupon.return_value = {
            'code': 'ERROR',
            'message': 'API 호출 실패',
            'data': None
        }
        
        mock_instance.issue_download_coupon.return_value = {
            'code': 'ERROR',
            'message': 'API 호출 실패',
            'data': None
        }
        
        yield mock_instance
