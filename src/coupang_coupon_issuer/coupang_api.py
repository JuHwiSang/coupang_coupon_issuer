"""Coupang API 클라이언트 모듈"""

import logging
import os
import hmac
import hashlib
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)

# GMT+0 타임존 설정 (HMAC 서명 생성용)
os.environ['TZ'] = 'GMT+0'
if hasattr(time, 'tzset'):  # Linux/Unix만 지원
    time.tzset()  # type: ignore  # Windows에서는 없음


class CoupangAPIClient:
    """Coupang API 호출 클라이언트"""

    BASE_URL = "https://api-gateway.coupang.com"

    def __init__(self, access_key: str, secret_key: str):
        """
        Args:
            access_key: Coupang Access Key
            secret_key: Coupang Secret Key
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.session = requests.Session()

    def _generate_hmac(self, method: str, path: str, query: str = "") -> str:
        """
        HMAC-SHA256 서명 생성 (Coupang API 규격)

        Args:
            method: HTTP 메서드 (GET, POST 등)
            path: API 경로
            query: 쿼리 스트링 (옵션, 빈 문자열이면 무시)

        Returns:
            HMAC-SHA256 Authorization 헤더 문자열
        """
        # GMT+0 기준 현재 시각
        datetime_str = time.strftime('%y%m%d') + 'T' + time.strftime('%H%M%S') + 'Z'

        # 메시지 생성: datetime + method + path + query
        message = datetime_str + method + path + query

        # HMAC-SHA256 서명 생성
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Authorization 헤더 포맷
        return f"CEA algorithm=HmacSHA256, access-key={self.access_key}, signed-date={datetime_str}, signature={signature}"

    def _request(
        self,
        method: str,
        path: str,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        API 요청 전송

        Args:
            method: HTTP 메서드
            path: API 경로
            json_data: 요청 본문 (JSON)
            timeout: 타임아웃 (초)

        Returns:
            응답 JSON 데이터

        Raises:
            requests.RequestException: 네트워크 오류
            ValueError: API 오류 응답
        """
        url = urljoin(self.BASE_URL, path)

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "Authorization": self._generate_hmac(method, path),
        }
        
        # ===== 요청 로깅 (HTTP RAW 형식) =====
        logger.debug(f"\n{'='*80}")
        logger.debug(f"HTTP REQUEST")
        logger.debug(f"{'='*80}")
        logger.debug(f"{method} {path}")
        logger.debug(f"Full URL: {url}")
        logger.debug(f"\n--- Request Headers ---")
        for header_name, header_value in headers.items():
            logger.debug(f"{header_name}: {header_value}")
        
        if json_data:
            logger.debug(f"\n--- Request Body (JSON) ---")
            logger.debug(json.dumps(json_data, indent=2, ensure_ascii=False))
        else:
            logger.debug(f"\n--- Request Body ---")
            logger.debug("(empty)")
        logger.debug(f"{'='*80}\n")

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                headers=headers,
                timeout=timeout
            )

            # ===== 응답 로깅 (HTTP RAW 형식) =====
            logger.debug(f"\n{'='*80}")
            logger.debug(f"HTTP RESPONSE")
            logger.debug(f"{'='*80}")
            logger.debug(f"Status Code: {response.status_code} {response.reason}")
            logger.debug(f"\n--- Response Headers ---")
            for header_name, header_value in response.headers.items():
                logger.debug(f"{header_name}: {header_value}")
            
            logger.debug(f"\n--- Response Body (Raw) ---")
            logger.debug(response.text)
            logger.debug(f"{'='*80}\n")

            # HTTP 오류 체크: 4xx, 5xx만 에러로 처리
            if response.status_code >= 400:
                error_msg = f"HTTP {response.status_code} {response.reason}"
                try:
                    error_data = response.json()
                    if 'errorMessage' in error_data:
                        error_msg += f": {error_data['errorMessage']}"
                    elif 'message' in error_data:
                        error_msg += f": {error_data['message']}"
                except Exception:
                    pass  # JSON 파싱 실패 시 기본 메시지 사용
                raise ValueError(error_msg)

            result = response.json()

            # API 응답 코드 체크 (JSON body의 code 필드)
            if 'code' in result and result['code'] >= 400:
                error_msg = result.get('errorMessage') or result.get('message', 'Unknown error')
                raise ValueError(f"API Error (code {result['code']}): {error_msg}")

            logger.debug(f"API 응답: 성공 (HTTP {response.status_code})")
            return result

        except requests.Timeout:
            logger.error(f"API 타임아웃 ({timeout}초 초과)")
            raise
        except requests.RequestException as e:
            logger.error(f"API 요청 실패: {e}")
            raise

    def create_instant_coupon(
        self,
        vendor_id: str,
        contract_id: int,
        name: str,
        max_discount_price: int,
        discount: int,
        start_at: str,
        end_at: str,
        coupon_type: str = "PRICE"
    ) -> Dict[str, Any]:
        """
        즉시할인쿠폰 생성 (비동기 API)

        Args:
            vendor_id: 판매자 ID (예: A00012345)
            contract_id: 계약서 ID
            name: 프로모션명 (최대 45자)
            max_discount_price: 최대 할인금액 (최소 10원)
            discount: 할인률 또는 할인금액
            start_at: 유효 시작일 (YYYY-MM-DD HH:MM:SS)
            end_at: 유효 종료일 (YYYY-MM-DD HH:MM:SS)
            coupon_type: 할인 방식 (RATE/FIXED_WITH_QUANTITY/PRICE)

        Returns:
            API 응답 전체 (dict)
            - data.content.requestedId: 상태 확인용 요청 ID
            - data.content.success: 요청 성공 여부
        """
        path = f"/v2/providers/fms/apis/api/v2/vendors/{vendor_id}/coupon"

        payload = {
            "contractId": contract_id,
            "name": name,
            "maxDiscountPrice": max_discount_price,
            "discount": discount,
            "startAt": start_at,
            "endAt": end_at,
            "type": coupon_type
        }

        return self._request("POST", path, json_data=payload)

    def apply_instant_coupon(
        self,
        vendor_id: str,
        coupon_id: int,
        vendor_items: List[int]
    ) -> Dict[str, Any]:
        """
        즉시할인쿠폰 아이템 적용 (비동기 API)

        Args:
            vendor_id: 판매자 ID (예: A00012345)
            coupon_id: 쿠폰 ID (create_instant_coupon의 상태 확인 후 획득)
            vendor_items: 쿠폰을 적용할 옵션ID 리스트 (최대 10,000개)

        Returns:
            API 응답 전체 (dict)
            - data.content.requestedId: 상태 확인용 요청 ID
            - data.content.success: 요청 성공 여부
        """
        path = f"/v2/providers/fms/apis/api/v1/vendors/{vendor_id}/coupons/{coupon_id}/items"

        payload = {
            "vendorItems": vendor_items
        }

        return self._request("POST", path, json_data=payload)
    
    def get_instant_coupon_status(
        self,
        vendor_id: str,
        requested_id: str
    ) -> Dict[str, Any]:
        """
        즉시할인쿠폰 요청 상태 확인 (쿠폰 생성/아이템 적용 공통)

        Args:
            vendor_id: 판매자 ID (예: A00012345)
            requested_id: 요청 ID (create_instant_coupon 또는 apply_instant_coupon에서 획득)

        Returns:
            API 응답 전체 (dict)
            - data.content.status: REQUESTED/DONE/FAIL
            - data.content.couponId: 쿠폰 ID (쿠폰 생성 시)
            - data.content.failedVendorItems: 실패한 옵션ID 리스트 (아이템 적용 시)
        """
        path = f"/v2/providers/fms/apis/api/v1/vendors/{vendor_id}/requested/{requested_id}"

        return self._request("GET", path)
    

    def create_download_coupon(
        self,
        contract_id: int,
        title: str,
        start_date: str,
        end_date: str,
        user_id: str,
        policies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        다운로드쿠폰 생성 (동기 API - 즉시 couponId 반환)

        Args:
            contract_id: 계약서 ID
            title: 쿠폰 명칭
            start_date: 쿠폰 적용 시작일 (YYYY-MM-DD HH:MM:SS)
            end_date: 쿠폰 적용 종료일 (YYYY-MM-DD HH:MM:SS)
            user_id: 사용자 계정 (WING 로그인 ID)
            policies: 쿠폰 세부 정책 리스트 (최대 3개)
                [
                    {
                        "title": "정책 명칭",
                        "typeOfDiscount": "PRICE" or "RATE",
                        "description": "정책 설명",
                        "minimumPrice": 10000,
                        "discount": 1000,
                        "maximumDiscountPrice": 1000,
                        "maximumPerDaily": 1
                    },
                    ...
                ]

        Returns:
            API 응답 전체 (dict)
            - couponId: 쿠폰 ID (바로 사용 가능)
            - couponStatus: 쿠폰 상태 (STANDBY)
        """
        path = "/v2/providers/marketplace_openapi/apis/api/v1/coupons"

        payload = {
            "title": title,
            "contractId": contract_id,
            "couponType": "DOWNLOAD",
            "startDate": start_date,
            "endDate": end_date,
            "userId": user_id,
            "policies": policies
        }

        return self._request("POST", path, json_data=payload)

    def apply_download_coupon(
        self,
        coupon_id: int,
        user_id: str,
        vendor_items: List[int]
    ) -> Dict[str, Any]:
        """
        다운로드쿠폰 아이템 적용 (동기 API)

        Args:
            coupon_id: 쿠폰 ID (create_download_coupon에서 획득)
            user_id: 사용자 계정 (WING 로그인 ID)
            vendor_items: 쿠폰을 적용할 옵션ID 리스트 (최대 100개)

        Returns:
            API 응답 전체 (dict)
            - requestResultStatus: SUCCESS/FAIL
            - body.couponId: 쿠폰 ID
            - errorMessage: 실패 시 오류 메시지

        Note:
            아이템 적용 실패 시 쿠폰이 자동으로 파기됩니다.
        """
        path = "/v2/providers/marketplace_openapi/apis/api/v1/coupon-items"

        payload = {
            "couponItems": [
                {
                    "couponId": coupon_id,
                    "userId": user_id,
                    "vendorItemIds": vendor_items
                }
            ]
        }

        return self._request("PUT", path, json_data=payload)

    def get_contract_list(self, vendor_id: str) -> Dict[str, Any]:
        """
        계약 목록 조회
        
        Args:
            vendor_id: 판매자 ID (예: A00012345)
        
        Returns:
            API 응답 전체 (dict)
            - data.success: 성공 여부
            - data.content: 계약서 목록
              - contractId: 업체의 계약서 아이디
              - vendorContractId: 업체의 계약서 코드 (-1은 자유계약기반)
              - type: CONTRACT_BASED 또는 NON_CONTRACT_BASED
              - sellerId: 판매자ID
              - start: 시작일시
              - end: 종료일시
        """
        path = f"/v2/providers/fms/apis/api/v2/vendors/{vendor_id}/contract/list"
        
        return self._request("GET", path)

    def expire_download_coupons(
        self,
        expire_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        다운로드쿠폰 파기 (만료 처리)
        
        Args:
            expire_list: 파기할 쿠폰 목록
                [
                    {
                        "couponId": 16513129,
                        "reason": "expired",
                        "userId": "testId123"
                    },
                    ...
                ]
        
        Returns:
            API 응답 전체 (list)
            [
                {
                    "requestResultStatus": "SUCCESS",
                    "body": {
                        "couponId": 16513129,
                        "requestTransactionId": "et5_165131291561017478962"
                    },
                    "errorCode": null,
                    "errorMessage": null
                },
                ...
            ]
        
        Raises:
            requests.RequestException: 네트워크 오류
            ValueError: API 오류 응답
        """
        path = "/v2/providers/marketplace_openapi/apis/api/v1/coupons/expire"
        
        payload = {
            "expireCouponList": expire_list
        }
        
        return self._request("POST", path, json_data=payload)
