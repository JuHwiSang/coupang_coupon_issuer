# ADR 020: 즉시할인쿠폰 REQUESTED 상태 간단 폴링

## 상태

승인됨 (2025-12-25)

## 컨텍스트

즉시할인쿠폰 발급은 비동기 API를 사용하며, 쿠폰 생성 및 아이템 적용 요청 후 상태 확인 API를 통해 결과를 확인해야 합니다.

### 문제점

현재 구현은 상태 확인 시 `DONE`이 아니면 즉시 실패 처리합니다:

```python
response = self.api_client.get_instant_coupon_status(self.vendor_id, request_id)
status = response.get('data', {}).get('content', {}).get('status')
assert status == 'DONE', f"실패 (status={status})"
```

하지만 API는 다음 세 가지 상태를 반환할 수 있습니다:
- `DONE`: 처리 완료
- `FAIL`: 처리 실패
- `REQUESTED`: 처리 중 (시간이 지나면 DONE 또는 FAIL로 변경됨)

`REQUESTED` 상태일 때 즉시 실패 처리하면, 실제로는 성공할 수 있는 요청이 실패로 기록됩니다.

### 제약사항

- 쿠폰 생성이 완료되어야 `couponId`를 얻을 수 있음
- `couponId`가 있어야 아이템 적용 요청 가능
- 따라서 쿠폰 생성 단계에서 `REQUESTED` 상태를 적절히 처리해야 함

## 결정

**간단한 폴링 (Simple Polling)** 방식을 채택합니다.

> [!WARNING]
> **덕테이프 솔루션 (Duct-tape Solution)**
> 
> 이 구현은 의도적으로 단순하게 설계되었습니다:
> - 쿠팡 서버가 대부분의 경우 빠르게 응답한다고 가정
> - 최대 10초 대기 (실무에서는 충분할 것으로 예상)
> - 향후 `asyncio` + `httpx` 기반으로 리팩토링 권장

### 폴링 전략

- **최대 재시도**: 5회
- **재시도 간격**: 2초
- **최대 대기 시간**: 10초 (5회 × 2초)
- **상태 처리**:
  - `DONE`: 성공, 다음 단계 진행
  - `REQUESTED`: 2초 대기 후 재시도 (최대 5회)
  - `FAIL`: 즉시 실패
  - 타임아웃 (5회 초과): 실패 처리

### 구현

`_wait_for_done()` 헬퍼 메서드 추가:

```python
def _wait_for_done(
    self,
    request_id: str,
    operation_name: str,
    max_retries: int = 5,
    retry_interval: int = 2
) -> Dict[str, Any]:
    """REQUESTED 상태를 폴링하여 DONE/FAIL 대기"""
    for attempt in range(max_retries + 1):
        response = self.api_client.get_instant_coupon_status(
            self.vendor_id, request_id
        )
        content = response.get('data', {}).get('content', {})
        status = content.get('status')
        
        if status == 'DONE':
            return content
        elif status == 'FAIL':
            raise AssertionError(f"{operation_name} 실패")
        elif status == 'REQUESTED':
            if attempt < max_retries:
                time.sleep(retry_interval)
            else:
                raise AssertionError(f"{operation_name} 타임아웃")
```

적용 위치:
- 즉시할인쿠폰 생성 상태 확인 (2단계)
- 즉시할인쿠폰 아이템 적용 상태 확인 (4단계)

## 거부된 대안

### 1. 배치 처리 (Batch Processing)

모든 쿠폰 요청을 먼저 보내고, 5초 대기 후 일괄 상태 체크하는 방식.

**거부 이유**:
- 복잡도가 높음 (데이터 구조, 상태 관리)
- 오버엔지니어링
- 디버깅 어려움

### 2. Async/Await 기반 전환

`asyncio` + `httpx`를 사용한 진짜 비동기 처리.

**거부 이유**:
- 현재 단계에서는 과함
- 전체 호출 체인을 async화해야 함
- CLI 진입점 변경 필요
- 향후 리팩토링 시 고려

### 3. 무한 대기

`REQUESTED` 상태가 변경될 때까지 무한 대기.

**거부 이유**:
- 쿠팡 서버 장애 시 무한 대기
- 타임아웃 없음
- Cron 작업이 멈출 위험

## 결과

### 장점

- ✅ 간단하고 이해하기 쉬움
- ✅ 대부분의 경우 잘 작동 (쿠팡 서버가 빠르게 응답)
- ✅ 명확한 타임아웃 (10초)
- ✅ 기존 코드 변경 최소화

### 단점

- ⚠️ 쿠팡 서버가 느리면 타임아웃 발생 가능
- ⚠️ 동기 방식이라 여러 쿠폰 발급 시 순차 처리
- ⚠️ 최대 10초는 임의로 정한 값 (실제 최적값은 모름)

### 향후 개선 방향

1. **모니터링**: 실제 운영 환경에서 타임아웃 발생 빈도 확인
2. **설정 조정**: 필요시 재시도 횟수/간격 조정
3. **Async 전환**: 쿠폰 수가 많아지면 `asyncio` 기반으로 리팩토링
4. **재시도 큐**: 타임아웃된 요청을 별도 큐에 저장하여 나중에 재처리

## 참고 자료

- [즉시할인쿠폰 요청상태 확인 API](../coupang/instant-coupon-status-api.md)
- [ADR 007: 쿠폰 발급 워크플로우](007-coupon-issuance-workflow.md)
