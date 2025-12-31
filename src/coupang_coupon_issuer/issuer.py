"""쿠폰 발급 로직 모듈"""

import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

# Korea Standard Time (UTC+9)
# Windows에서는 tzdata 패키지 필요
try:
    from zoneinfo import ZoneInfo
    KST = ZoneInfo("Asia/Seoul")
except Exception:
    # Fallback: UTC+9 offset 사용
    from datetime import timezone
    KST = timezone(timedelta(hours=9))

from .coupang_api import CoupangAPIClient
from .config import (
    get_base_dir,
    get_excel_file,
    get_download_coupons_file,
    COUPON_CONTRACT_ID,
    COUPON_DEFAULT_ISSUE_COUNT,
    POLLING_MAX_RETRIES,
    POLLING_RETRY_INTERVAL,
)
from .reader import fetch_coupons_from_excel, DISCOUNT_TYPE_KR_TO_EN, DISCOUNT_TYPE_EN_TO_KR


# 할인방식 한글-영어 매핑 (reader.py로 이동됨)


class CouponIssuer:
    """쿠폰 발급 담당 클래스"""

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        user_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
    ):
        """
        Args:
            base_dir: 작업 디렉토리 (None이면 현재 디렉토리)
            access_key: Coupang Access Key (필수)
            secret_key: Coupang Secret Key (필수)
            user_id: WING 사용자 ID (필수)
            vendor_id: 판매자 ID (필수)
        """
        self.base_dir = get_base_dir(base_dir)
        self.excel_file = get_excel_file(self.base_dir)
        self.download_coupons_file = get_download_coupons_file(self.base_dir)

        # 모든 인증 정보 필수
        if not access_key or not secret_key:
            raise ValueError("API 키가 설정되지 않았습니다.")

        if not user_id or not vendor_id:
            raise ValueError("쿠폰 정보가 설정되지 않았습니다 (user_id, vendor_id).")

        self.access_key = access_key
        self.secret_key = secret_key
        self.user_id = user_id
        self.vendor_id = vendor_id

        # Coupang API 클라이언트 초기화
        self.api_client = CoupangAPIClient(self.access_key, self.secret_key)

        # 계약 ID 가져오기 (자유계약기반)
        self.contract_id = self._fetch_contract_id()
        print(f"[{self._timestamp()}] 설정 로드 완료 (Vendor: {self.vendor_id}, Contract: {self.contract_id})", flush=True)

    @staticmethod
    def _timestamp() -> str:
        """현재 시각 문자열 반환"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _fetch_contract_id(self) -> int:
        """
        자유계약기반(NON_CONTRACT_BASED) 계약 ID 조회
        
        Returns:
            contractId: 자유계약기반 계약의 ID
        
        Raises:
            ValueError: 자유계약기반 계약을 찾을 수 없는 경우
        """
        timestamp = self._timestamp()
        print(f"[{timestamp}] 계약 목록 조회 중...", flush=True)
        
        try:
            response = self.api_client.get_contract_list(self.vendor_id)
            contracts = response.get('data', {}).get('content', [])
            
            # NON_CONTRACT_BASED 계약 필터링 (vendorContractId == -1)
            non_contract_based = [
                c for c in contracts 
                if c.get('type') == 'NON_CONTRACT_BASED' and c.get('vendorContractId') == -1
            ]
            
            if not non_contract_based:
                raise ValueError(
                    "자유계약기반(NON_CONTRACT_BASED) 계약을 찾을 수 없습니다. "
                    "쿠팡 판매자 센터에서 계약 설정을 확인하세요."
                )
            
            # 첫 번째 자유계약 사용
            contract = non_contract_based[0]
            contract_id = contract.get('contractId')
            
            print(
                f"[{timestamp}] 자유계약기반 계약 발견: contractId={contract_id}, "
                f"기간={contract.get('start')} ~ {contract.get('end')}",
                flush=True
            )
            
            return contract_id
            
        except Exception as e:
            print(f"[{timestamp}] ERROR: 계약 조회 실패: {e}", flush=True)
            raise

    def issue(self) -> None:
        """
        쿠폰 발급 메인 함수

        1. 엑셀에서 쿠폰 정의 읽기
        2. 각 쿠폰에 대해 Coupang API 호출
        3. 결과를 로그로 출력
        """
        timestamp = self._timestamp()
        print(f"[{timestamp}] 쿠폰 발급 작업 시작", flush=True)

        results = []

        try:
            # 1. 엑셀에서 쿠폰 정의 읽기
            coupons = self._fetch_coupons_from_excel()

            if not coupons:
                print(f"[{timestamp}] 발급할 쿠폰이 없습니다", flush=True)
                return

            # 1.5. 이전 다운로드쿠폰 파기 (새로운 단계)
            self._expire_previous_download_coupons()

            # 2. 각 쿠폰 발급 처리
            print(f"[{timestamp}] 쿠폰 발급 처리 중: 총 {len(coupons)}개", flush=True)


            for idx, coupon in enumerate(coupons, start=1):
                result = self._issue_single_coupon(idx, coupon)
                results.append(result)

            # 3. 결과 요약 출력
            success_count = sum(1 for r in results if r['status'] == '성공')
            fail_count = len(results) - success_count

            print(f"[{timestamp}] 쿠폰 발급 완료! (성공: {success_count}, 실패: {fail_count})", flush=True)

            # 4. 상세 결과 로깅
            for result in results:
                status = "OK" if result['status'] == '성공' else "FAIL"
                print(f"[{timestamp}] [{status}] {result['coupon_name']}: {result['message']}", flush=True)

        except Exception as e:
            print(f"[{timestamp}] ERROR: 쿠폰 발급 중 오류 발생: {e}", flush=True)
            raise

    def _issue_single_coupon(self, index: int, coupon: Dict[str, Any]) -> Dict[str, Any]:
        """
        단일 쿠폰 발급

        Args:
            index: 쿠폰 순번 (로그용)
            coupon: 쿠폰 정의 딕셔너리
                {
                    'name': '쿠폰이름',
                    'type': '즉시할인쿠폰' or '다운로드쿠폰',
                    'validity_days': 2,  (유효기간 일수)
                    'discount_type': 'RATE' or 'FIXED_WITH_QUANTITY' or 'PRICE',
                    'discount': 10,  (할인금액/비율, Column E)
                    'issue_count': 100,  (발급개수, Column F, 다운로드쿠폰만 사용)
                    'vendor_items': [3226138951, 3226138847],  (옵션ID 리스트, Column G)
                }

        Returns:
            발급 결과 딕셔너리
        """
        timestamp = self._timestamp()
        coupon_name = coupon.get('name', f'쿠폰{index}')
        coupon_type = coupon.get('type', '').strip()
        validity_days = coupon.get('validity_days', 1)
        discount_type = coupon.get('discount_type', 'PRICE')
        discount = coupon.get('discount', 0)  # Column E: 할인금액/비율 (필수)
        min_purchase_price = coupon.get('min_purchase_price')  # Column F: 최소구매금액 (다운로드쿠폰 전용)
        max_discount_price = coupon.get('max_discount_price', 0)  # Column G: 최대할인금액 (필수)
        issue_count = coupon.get('issue_count')  # Column H: 발급개수 (선택적)
        vendor_items = coupon.get('vendor_items', [])  # Column I: 옵션ID 리스트 (필수)

        # Validate required fields
        if discount <= 0:
            raise ValueError(f"할인금액/비율이 설정되지 않았습니다: {coupon_name}")
        if max_discount_price <= 0:
            raise ValueError(f"최대할인금액이 설정되지 않았습니다: {coupon_name}")
        if not vendor_items:
            raise ValueError(f"옵션ID가 설정되지 않았습니다: {coupon_name}")

        print(f"[{timestamp}] [{index}] {coupon_name} ({coupon_type}) 발급 중...", flush=True)

        result = {
            'coupon_name': coupon_name,
            'coupon_type': coupon_type,
            'status': '실패',
            'message': '',
            'timestamp': timestamp
        }

        try:
            # 쿠폰 타입별로 시작일 설정
            if coupon_type == '즉시할인쿠폰':
                # 즉시할인쿠폰: 오늘 0시 (KST 기준)
                now = datetime.now(KST)
                today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                start_date = today.strftime('%Y-%m-%d %H:%M:%S')
                # 유효 종료일: 오늘 0시 + validity_days일 - 1분 (그날 23:59에 만료)
                end_date = (today + timedelta(days=validity_days) - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
            elif coupon_type == '다운로드쿠폰':
                # 다운로드쿠폰: 현재시각 + 1시간 (KST 기준, API 처리 시간 확보)
                now = datetime.now(KST)
                start_date = (now + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
                # 유효 종료일: 오늘 자정 + validity_days일 - 1분 (그날 23:59에 만료)
                today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = (today_midnight + timedelta(days=validity_days) - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
            else:
                # 알 수 없는 쿠폰 타입 (여기 도달하면 안 됨)
                raise ValueError(f"알 수 없는 쿠폰 타입: {coupon_type}")

            if coupon_type == '즉시할인쿠폰':
                result['message'] = self._issue_instant_coupon(
                    coupon_name=coupon_name,
                    discount_type=discount_type,
                    discount=discount,
                    start_date=start_date,
                    end_date=end_date,
                    vendor_items=vendor_items,
                    max_discount_price=max_discount_price
                )
                result['status'] = '성공'

            elif coupon_type == '다운로드쿠폰':
                result['message'] = self._issue_download_coupon(
                    coupon_name=coupon_name,
                    discount_type=discount_type,
                    discount=discount,
                    issue_count=issue_count,
                    start_date=start_date,
                    end_date=end_date,
                    vendor_items=vendor_items,
                    validity_days=validity_days,
                    min_purchase_price=min_purchase_price,
                    max_discount_price=max_discount_price
                )
                result['status'] = '성공'

            else:
                result['message'] = f"알 수 없는 쿠폰 타입: {coupon_type}"

            print(f"[{timestamp}] [{index}] {result['status']}: {result['message']}", flush=True)

        except Exception as e:
            result['status'] = '실패'
            result['message'] = str(e)
            print(f"[{timestamp}] [{index}] 실패: {e}", flush=True)

        return result

    def _issue_instant_coupon(
        self,
        coupon_name: str,
        discount_type: str,
        discount: int,
        start_date: str,
        end_date: str,
        vendor_items: List[int],
        max_discount_price: int
    ) -> str:
        """
        즉시할인쿠폰 발급 (비동기 워크플로우)

        Args:
            coupon_name: 쿠폰 이름
            discount_type: 할인 방식 (RATE/FIXED_WITH_QUANTITY/PRICE)
            discount: 할인금액/비율
            start_date: 유효 시작일
            end_date: 유효 종료일
            vendor_items: 옵션ID 리스트
            max_discount_price: 최대 할인금액 (Excel 값)

        Returns:
            성공 메시지 문자열

        Raises:
            AssertionError: API 호출 실패 시
        """
        assert self.vendor_id is not None, "vendor_id가 설정되지 않았습니다"

        # 1단계: 쿠폰 생성
        response1 = self.api_client.create_instant_coupon(
            vendor_id=self.vendor_id,
            contract_id=self.contract_id,
            name=coupon_name,
            max_discount_price=max_discount_price,  # Excel 값 사용
            discount=discount,
            start_at=start_date,
            end_at=end_date,
            coupon_type=discount_type
        )

        req_id1 = response1.get('data', {}).get('content', {}).get('requestedId')
        assert req_id1 is not None, "즉시할인쿠폰 생성 실패 (requestedId 없음)"

        # 2단계: 쿠폰 생성 상태 확인 (폴링)
        content2 = self._wait_for_done(req_id1, "즉시할인쿠폰 생성")
        
        coupon_id = content2.get('couponId')
        assert coupon_id is not None, "즉시할인쿠폰 생성 실패 (couponId 없음)"

        # 3단계: 아이템 적용
        response3 = self.api_client.apply_instant_coupon(
            vendor_id=self.vendor_id,
            coupon_id=coupon_id,
            vendor_items=vendor_items
        )

        req_id2 = response3.get('data', {}).get('content', {}).get('requestedId')
        assert req_id2 is not None, "즉시할인쿠폰 아이템 적용 실패 (requestedId 없음)"

        # 4단계: 아이템 적용 상태 확인 (폴링)
        content4 = self._wait_for_done(req_id2, "즉시할인쿠폰 아이템 적용")
        
        # DONE 상태에서도 실패한 아이템이 있을 수 있음
        failed_items = content4.get('failedVendorItems', [])
        if failed_items:
            error_details = ', '.join([f"{item.get('vendorItemId')}: {item.get('reason')}" for item in failed_items])
            raise AssertionError(f"즉시할인쿠폰 아이템 적용 실패 (실패: {error_details})")

        return f"즉시할인쿠폰 생성 완료 (couponId: {coupon_id}, 옵션 {len(vendor_items)}개 적용)"

    def _issue_download_coupon(
        self,
        coupon_name: str,
        discount_type: str,
        discount: int,
        issue_count: Optional[int],
        start_date: str,
        end_date: str,
        vendor_items: List[int],
        validity_days: int,
        min_purchase_price: int,
        max_discount_price: int
    ) -> str:
        """
        다운로드쿠폰 발급 (동기 API)

        Args:
            coupon_name: 쿠폰 이름
            discount_type: 할인 방식 (RATE/FIXED_WITH_QUANTITY/PRICE)
            discount: 할인금액/비율
            issue_count: 발급개수 (일일 최대)
            start_date: 유효 시작일
            end_date: 유효 종료일
            vendor_items: 옵션ID 리스트
            validity_days: 유효기간 (일)
            min_purchase_price: 최소 구매금액 (Excel 값, 기본값 1)
            max_discount_price: 최대 할인금액 (Excel 값)

        Returns:
            성공 메시지 문자열

        Raises:
            AssertionError: API 호출 실패 시
        """
        assert self.user_id is not None, "user_id가 설정되지 않았습니다"
        assert issue_count is not None, "발급개수가 설정되지 않았습니다"

        # 다운로드쿠폰 정책 구성
        policy = {
            "title": coupon_name,
            "typeOfDiscount": discount_type,
            "description": f"{coupon_name} ({validity_days}일간 유효)",
            "minimumPrice": min_purchase_price,  # Excel 값 사용 (기본값 1)
            "discount": discount,
            "maximumDiscountPrice": max_discount_price,  # Excel 값 사용
            "maximumPerDaily": issue_count
        }

        # 1단계: 쿠폰 생성 (동기 API - 바로 couponId 반환)
        response1 = self.api_client.create_download_coupon(
            contract_id=self.contract_id,
            title=coupon_name,
            start_date=start_date,
            end_date=end_date,
            user_id=self.user_id,
            policies=[policy]
        )

        coupon_id = response1.get('couponId')
        assert coupon_id is not None, f"다운로드쿠폰 생성 실패 (couponId 없음): {response1}"

        # 2단계: 아이템 적용 (동기 API)
        response2 = self.api_client.apply_download_coupon(
            coupon_id=coupon_id,
            user_id=self.user_id,
            vendor_items=vendor_items
        )

        # API 응답은 배열 형식 (공식 문서 오류 - 실제로는 list 반환)
        # 예: [{"requestResultStatus":"SUCCESS","body":{"couponId":88385733,...},...}]
        if not isinstance(response2, list) or len(response2) == 0:
            raise AssertionError(f"다운로드쿠폰 아이템 적용 실패: 예상치 못한 응답 형식 {response2}")

        result = response2[0]
        result_status = result.get('requestResultStatus')
        if result_status != 'SUCCESS':
            error_msg = result.get('errorMessage', 'Unknown error')
            raise AssertionError(f"다운로드쿠폰 아이템 적용 실패: {error_msg}")

        # 발급 성공 시 기록 저장
        self._save_download_coupon_record({
            "name": coupon_name,
            "coupon_id": coupon_id,
            "issued_at": self._timestamp()
        })

        return f"다운로드쿠폰 생성 완료 (couponId: {coupon_id}, 옵션 {len(vendor_items)}개 적용)"


    def _fetch_coupons_from_excel(self) -> List[Dict[str, Any]]:
        """엑셀 파일에서 쿠폰 정의 읽기 (reader 모듈 사용)"""
        timestamp = self._timestamp()
        print(f"[{timestamp}] 엑셀 파일 읽기: {self.excel_file}", flush=True)
        
        try:
            coupons = fetch_coupons_from_excel(self.excel_file)
            print(f"[{timestamp}] 쿠폰 {len(coupons)}개 읽기 완료", flush=True)
            return coupons
        except Exception as e:
            print(f"[{timestamp}] ERROR: 엑셀 파일 읽기 실패: {e}", flush=True)
            raise

    def _wait_for_done(
        self,
        request_id: str,
        operation_name: str,
        max_retries: int = POLLING_MAX_RETRIES,
        retry_interval: int = POLLING_RETRY_INTERVAL
    ) -> Dict[str, Any]:
        """
        REQUESTED 상태를 폴링하여 DONE/FAIL 대기 (간단 폴링)
        
        TODO: 향후 async 리팩토링 필요
        - 현재: 동기 폴링 (time.sleep 사용, 순차 처리)
        - 향후: asyncio + httpx 기반 비동기 처리
        - 참조: ADR 020, DEV_LOG.md (2025-12-25)
        
        Args:
            request_id: 요청 ID
            operation_name: 작업 이름 (로깅용)
            max_retries: 최대 재시도 횟수 (기본 5회)
            retry_interval: 재시도 간격 초 (기본 2초)
        
        Returns:
            최종 상태 응답의 content 딕셔너리
        
        Raises:
            AssertionError: FAIL 상태 또는 타임아웃
        """
        timestamp = self._timestamp()
        
        for attempt in range(max_retries + 1):  # 0부터 max_retries까지 (총 max_retries+1회)
            response = self.api_client.get_instant_coupon_status(self.vendor_id, request_id)
            content = response.get('data', {}).get('content', {})
            status = content.get('status')
            
            if status == 'DONE':
                if attempt > 0:
                    print(f"[{timestamp}] {operation_name} 완료 (재시도 {attempt}회)", flush=True)
                return content
            
            elif status == 'FAIL':
                raise AssertionError(f"{operation_name} 실패 (status=FAIL)")
            
            elif status == 'REQUESTED':
                if attempt < max_retries:
                    print(f"[{timestamp}] {operation_name} 대기중... (재시도 {attempt + 1}/{max_retries})", flush=True)
                    time.sleep(retry_interval)
                else:
                    # 최대 재시도 횟수 초과
                    raise AssertionError(
                        f"{operation_name} 타임아웃 "
                        f"(최대 {max_retries}회 재시도, {max_retries * retry_interval}초 대기)"
                    )
            
            else:
                raise AssertionError(f"{operation_name} 알 수 없는 상태 (status={status})")
        
        # 이 코드에는 도달하지 않지만 타입 체커를 위해 추가
        raise AssertionError(f"{operation_name} 예상치 못한 종료")

    def _load_download_coupon_records(self) -> List[Dict[str, Any]]:
        """
        다운로드쿠폰 기록 파일 읽기
        
        Returns:
            쿠폰 기록 리스트 (파일 없으면 빈 리스트)
        
        Note:
            하위 호환성: 파일 없으면 warning 출력하고 빈 리스트 반환
        """
        timestamp = self._timestamp()
        
        if not self.download_coupons_file.exists():
            print(f"[{timestamp}] WARNING: 다운로드쿠폰 기록 파일이 없습니다: {self.download_coupons_file}", flush=True)
            print(f"[{timestamp}] WARNING: 이전 쿠폰 파기를 건너뜁니다 (첫 실행 또는 업그레이드 후)", flush=True)
            return []
        
        try:
            with open(self.download_coupons_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                coupons = data.get('coupons', [])
                print(f"[{timestamp}] 다운로드쿠폰 기록 로드 완료: {len(coupons)}개", flush=True)
                return coupons
        except json.JSONDecodeError as e:
            print(f"[{timestamp}] ERROR: 다운로드쿠폰 기록 파일 파싱 실패: {e}", flush=True)
            print(f"[{timestamp}] WARNING: 이전 쿠폰 파기를 건너뜁니다", flush=True)
            return []
        except Exception as e:
            print(f"[{timestamp}] ERROR: 다운로드쿠폰 기록 파일 읽기 실패: {e}", flush=True)
            print(f"[{timestamp}] WARNING: 이전 쿠폰 파기를 건너뜁니다", flush=True)
            return []

    def _save_download_coupon_records(self, records: List[Dict[str, Any]]) -> None:
        """다운로드쿠폰 기록 파일 저장 (JSON 형식)"""
        timestamp = self._timestamp()
        
        data = {
            "last_updated": timestamp,
            "coupons": records
        }
        
        try:
            with open(self.download_coupons_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[{timestamp}] 다운로드쿠폰 기록 저장 완료: {len(records)}개", flush=True)
        except Exception as e:
            print(f"[{timestamp}] ERROR: 다운로드쿠폰 기록 저장 실패: {e}", flush=True)
            raise

    def _save_download_coupon_record(self, record: Dict[str, Any]) -> None:
        """단일 다운로드쿠폰 기록 추가 (헬퍼 메서드)"""
        # 기존 기록 로드
        records = self._load_download_coupon_records()
        
        # 새 기록 추가
        records.append(record)
        
        # 저장
        self._save_download_coupon_records(records)

    def _expire_previous_download_coupons(self) -> None:
        """
        이전에 발급된 다운로드쿠폰 전체 파기
        
        Note:
            하위 호환성: 기록 파일 없으면 warning만 출력하고 스킵
        """
        timestamp = self._timestamp()
        
        # 기록 로드
        records = self._load_download_coupon_records()
        
        if not records:
            print(f"[{timestamp}] 파기할 이전 다운로드쿠폰이 없습니다", flush=True)
            return
        
        print(f"[{timestamp}] 이전 다운로드쿠폰 파기 시작 (총 {len(records)}개)", flush=True)
        
        # 파기 요청 리스트 생성
        expire_list = []
        for record in records:
            coupon_id = record.get('coupon_id')
            if coupon_id:
                expire_list.append({
                    "couponId": coupon_id,
                    "reason": "expired",
                    "userId": self.user_id
                })
        
        if not expire_list:
            print(f"[{timestamp}] WARNING: 유효한 쿠폰 ID가 없습니다", flush=True)
            return
        
        try:
            # API 호출
            response = self.api_client.expire_download_coupons(expire_list)
            
            # 결과 확인
            success_count = 0
            fail_count = 0
            
            for result in response:
                status = result.get('requestResultStatus')
                coupon_id = result.get('body', {}).get('couponId')
                
                if status == 'SUCCESS':
                    success_count += 1
                    print(f"[{timestamp}] 다운로드쿠폰 파기 완료: couponId={coupon_id}", flush=True)
                else:
                    fail_count += 1
                    error_msg = result.get('errorMessage', 'Unknown error')
                    print(f"[{timestamp}] WARNING: 다운로드쿠폰 파기 실패: couponId={coupon_id}, error={error_msg}", flush=True)
            
            print(f"[{timestamp}] 이전 다운로드쿠폰 파기 완료 (성공: {success_count}, 실패: {fail_count})", flush=True)
            
            # 기록 파일 초기화 (파기 완료 후)
            self._save_download_coupon_records([])
            
        except Exception as e:
            print(f"[{timestamp}] ERROR: 다운로드쿠폰 파기 중 오류 발생: {e}", flush=True)
            print(f"[{timestamp}] WARNING: 이전 쿠폰 파기 실패, 계속 진행합니다", flush=True)
            # 오류 발생 시에도 계속 진행 (하위 호환성)
