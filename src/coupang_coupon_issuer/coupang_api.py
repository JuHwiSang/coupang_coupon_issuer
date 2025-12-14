"""Coupang API 클라이언트 모듈"""

import os
import hmac
import hashlib
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

import requests

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

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] API 요청: {method} {path}", flush=True)

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                headers=headers,
                timeout=timeout
            )

            # HTTP 오류 체크
            response.raise_for_status()

            result = response.json()

            # API 응답 코드 체크
            if result.get('code') != 200:
                error_msg = result.get('errorMessage') or result.get('message', 'Unknown error')
                raise ValueError(f"API Error (code {result.get('code')}): {error_msg}")

            print(f"[{timestamp}] API 응답: 성공 (HTTP {response.status_code})", flush=True)
            return result

        except requests.Timeout:
            print(f"[{timestamp}] ERROR: API 타임아웃 ({timeout}초 초과)", flush=True)
            raise
        except requests.RequestException as e:
            print(f"[{timestamp}] ERROR: API 요청 실패: {e}", flush=True)
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
        coupon_type: str = "PRICE",
        wow_exclusive: bool = False
    ) -> Dict[str, Any]:
        """
        즉시할인쿠폰 생성

        Args:
            vendor_id: 판매자 ID (예: A00012345)
            contract_id: 계약서 ID
            name: 프로모션명 (최대 45자)
            max_discount_price: 최대 할인금액 (최소 10원)
            discount: 할인률 또는 할인금액
            start_at: 유효 시작일 (YYYY-MM-DD HH:MM:SS)
            end_at: 유효 종료일 (YYYY-MM-DD HH:MM:SS)
            coupon_type: 할인 방식 (RATE/FIXED_WITH_QUANTITY/PRICE)
            wow_exclusive: 로켓와우 회원 전용 (기본값: False)

        Returns:
            API 응답 데이터 (requestedId 포함)
        """
        path = f"/v2/providers/fms/apis/api/v2/vendors/{vendor_id}/coupon"

        payload = {
            "contractId": str(contract_id),
            "name": name,
            "maxDiscountPrice": str(max_discount_price),
            "discount": str(discount),
            "startAt": start_at,
            "endAt": end_at,
            "type": coupon_type,
            "wowExclusive": str(wow_exclusive).lower()
        }

        return self._request("POST", path, json_data=payload)

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
        다운로드쿠폰 생성

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
            API 응답 데이터 (couponId 포함)
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
