# ADR 007: 쿠폰 발급 워크플로우 (다단계 비동기 처리)

**상태**: 승인됨
**날짜**: 2024-12-16
**결정자**: Coupang API 공식 규격

## 컨텍스트

Coupang API를 통한 쿠폰 발급은 단순한 단일 API 호출이 아닌, **다단계 비동기 프로세스**입니다.

### Coupang API의 제약사항

1. **쿠폰 생성과 아이템 적용은 별도 API**
   - 쿠폰을 생성한 후, 어느 상품(vendorItemId)에 적용할지 별도로 지정해야 함
   - 쿠폰 생성만으로는 실제 사용 불가

2. **비동기 처리**
   - 즉시할인쿠폰의 경우 대부분의 API가 비동기로 동작
   - API 호출 즉시 `requestedId`만 반환
   - 실제 성공/실패는 별도 상태 확인 API로 폴링 필요

3. **실패 시 쿠폰 파기**
   - 다운로드쿠폰: 아이템 적용 실패 시 생성된 쿠폰 자동 삭제
   - 즉시할인쿠폰: 아이템 적용 실패 시 쿠폰은 남지만 사용 불가

4. **원자성(Atomicity) 부재**
   - 쿠폰 생성 성공 → 아이템 적용 실패 가능
   - 부분 성공 상태 발생 가능
   - 트랜잭션 롤백 불가

## 결정사항

### 워크플로우 구조

각 쿠폰 발급은 다음 **4단계 프로세스**로 구현:

```
1. 쿠폰 생성 API 호출
   ↓
2. 쿠폰 생성 상태 확인 (즉시할인만, 폴링)
   ↓ (성공 시)
3. 아이템 적용 API 호출
   ↓
4. 아이템 적용 상태 확인 (즉시할인만, 폴링)
   ↓ (성공 시)
완료
```

**실패 시**: 어느 단계에서든 실패하면 **1단계부터 전체 재시도**

### 즉시할인쿠폰 상세 플로우

```python
# 1. 쿠폰 생성
response = api.create_instant_coupon(...)
requested_id_1 = response['data']['content']['requestedId']

# 2. 쿠폰 생성 상태 확인 (폴링)
while True:
    status = api.check_status(vendor_id, requested_id_1)
    if status['status'] == 'DONE':
        coupon_id = status['couponId']
        break  # 성공 → 다음 단계
    elif status['status'] == 'FAIL':
        raise Exception("쿠폰 생성 실패")  # → 1단계부터 재시도
    else:  # REQUESTED
        time.sleep(2)  # 2초 대기 후 재확인

# 3. 아이템 적용
response = api.create_instant_coupon_items(vendor_id, coupon_id, vendor_item_ids)
requested_id_2 = response['data']['content']['requestedId']

# 4. 아이템 적용 상태 확인 (폴링)
while True:
    status = api.check_status(vendor_id, requested_id_2)
    if status['status'] == 'DONE':
        return "성공"  # 완료
    elif status['status'] == 'FAIL':
        raise Exception("아이템 적용 실패")  # → 1단계부터 재시도
    else:  # REQUESTED
        time.sleep(2)  # 2초 대기 후 재확인
```

### 다운로드쿠폰 상세 플로우

```python
# 1. 쿠폰 생성 (동기 API)
response = api.create_download_coupon(...)
coupon_id = response['couponId']  # 즉시 반환

# 2. 아이템 적용
response = api.create_download_coupon_items(coupon_id, user_id, vendor_item_ids)

if response['requestResultStatus'] == 'SUCCESS':
    return "성공"  # 완료
else:
    # 실패 시 쿠폰 자동 삭제됨 → 1단계부터 재시도
    raise Exception("아이템 적용 실패 (쿠폰 파기됨)")
```

### 재시도 정책

```python
MAX_RETRIES = 3  # 최대 재시도 횟수
RETRY_DELAY = 5  # 재시도 간격 (초)

for attempt in range(1, MAX_RETRIES + 1):
    try:
        # 1~4단계 전체 실행
        result = issue_coupon_with_items(...)
        return result  # 성공
    except Exception as e:
        if attempt == MAX_RETRIES:
            return {
                'status': '실패',
                'message': f'최대 재시도 횟수 초과: {e}'
            }
        else:
            print(f"재시도 {attempt}/{MAX_RETRIES}: {e}")
            time.sleep(RETRY_DELAY)
```

### 폴링 설정

```python
POLL_INTERVAL = 2      # 폴링 간격 (초)
POLL_TIMEOUT = 60      # 최대 대기 시간 (초)
POLL_MAX_ATTEMPTS = POLL_TIMEOUT // POLL_INTERVAL  # 30회
```

## 근거

### 1. API 규격 준수
- Coupang API가 다단계 비동기 처리를 요구
- 공식 워크플로우를 따라야 정상 동작 보장

### 2. 원자성 확보
- 쿠폰 생성과 아이템 적용을 하나의 트랜잭션처럼 처리
- 부분 성공 상태를 재시도로 해결

### 3. 안정성
- 각 단계의 성공 여부를 명확히 확인
- 실패 시 전체 재시도로 일관성 유지

### 4. 사용자 경험
- 실패한 쿠폰을 엑셀에 명확히 기록
- 재시도 로직으로 일시적 오류 자동 복구

## 대안

### 대안 1: 쿠폰 생성만 수행 (아이템 적용 생략)
- **장점**: 구현 단순
- **단점**: 쿠폰이 실제로 사용 불가능 (치명적)
- **결정**: 거부됨

### 대안 2: 수동 롤백 구현
- **장점**: 부분 성공 상태 정리 가능
- **단점**:
  - Coupang API에 쿠폰 삭제 API가 없을 수 있음
  - 복잡도 증가
  - 롤백 자체도 실패할 수 있음
- **결정**: 거부됨 (재시도로 충분)

### 대안 3: 폴링 대신 Webhook 사용
- **장점**: 실시간 응답
- **단점**:
  - Coupang API가 Webhook을 지원하지 않음
  - 서버 구축 필요 (복잡도 증가)
- **결정**: 거부됨 (불가능)

### 대안 4: 재시도 없이 실패 즉시 보고
- **장점**: 구현 단순
- **단점**:
  - 일시적 네트워크 오류도 실패 처리
  - 사용자가 수동으로 재실행해야 함
- **결정**: 거부됨 (자동화 목적에 부합하지 않음)

## 영향

### 긍정적 영향

1. **안정성 향상**
   - 부분 성공 상태 방지
   - 일시적 오류 자동 복구

2. **명확한 상태 관리**
   - 각 쿠폰의 성공/실패를 확실히 판단
   - 엑셀 결과에 정확한 상태 기록

3. **자동화 친화적**
   - 매일 0시 자동 실행 시 안정적으로 동작
   - 사람 개입 최소화

### 부정적 영향

1. **처리 시간 증가**
   - 폴링으로 인한 대기 시간 발생
   - 재시도 시 추가 시간 소요
   - **완화 방법**: 병렬 처리로 전체 시간 단축

2. **복잡도 증가**
   - 4단계 프로세스 구현 필요
   - 재시도 로직 추가
   - **완화 방법**: 명확한 함수 분리로 가독성 유지

3. **API 호출 횟수 증가**
   - 상태 확인 폴링으로 추가 API 호출
   - **완화 방법**: 적절한 폴링 간격 설정 (2초)

## 구현 요구사항

### coupang_api.py에 추가 필요

```python
def check_instant_coupon_status(
    self,
    vendor_id: str,
    requested_id: str
) -> Dict[str, Any]:
    """즉시할인쿠폰 요청 상태 확인"""
    path = f"/v2/providers/fms/apis/api/v1/vendors/{vendor_id}/requested/{requested_id}"
    return self._request("GET", path)
```

### issuer.py에 구현 필요

```python
def _issue_instant_coupon_with_retry(
    self,
    coupon_data: Dict[str, Any],
    vendor_item_ids: List[int]
) -> Dict[str, Any]:
    """즉시할인쿠폰 발급 (재시도 포함)"""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # 1. 쿠폰 생성
            # 2. 생성 상태 확인 (폴링)
            # 3. 아이템 적용
            # 4. 적용 상태 확인 (폴링)
            return {'status': '성공', ...}
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                return {'status': '실패', 'message': str(e)}
```

## 참고 문서

- [Coupang 쿠폰 발급 워크플로우](../coupang/workflow.md)
- [즉시할인쿠폰 생성 API](../coupang/instant-coupon-api.md)
- [즉시할인쿠폰 아이템 생성 API](../coupang/instant-coupon-item-api.md)
- [즉시할인쿠폰 상태 확인 API](../coupang/instant-coupon-status-api.md)
- [다운로드쿠폰 생성 API](../coupang/download-coupon-api.md)
- [다운로드쿠폰 아이템 생성 API](../coupang/download-coupon-item-api.md)
