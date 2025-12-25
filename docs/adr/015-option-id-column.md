# ADR 015: 옵션ID 컬럼 추가 및 비동기 워크플로우 구현

**상태**: 승인됨  
**날짜**: 2024-12-22  
**결정자**: 프로젝트 오너  
**업데이트**: [ADR 009](009-excel-6-column-structure.md) (Deprecated, 6컬럼 → 7컬럼)

## 컨텍스트

ADR 009에서 정의한 6컬럼 구조에서는 **쿠폰을 적용할 상품 옵션ID**를 지정할 방법이 없었습니다. 현재 코드에서는 하드코딩된 더미 값(`[123456789]`)을 사용하고 있어 실제 운영이 불가능합니다.

또한 Coupang API는 **비동기 방식**으로 동작하는데, 현재 구현은 이를 제대로 처리하지 못하고 있습니다:

### Coupang API 비동기 처리 흐름

1. **쿠폰 생성 API 호출** → `requestedId` 반환 (즉시할인/다운로드쿠폰 모두)
2. **상태 확인 API 호출** (`requestedId` 사용) → `couponId` 획득 (즉시할인만, 다운로드쿠폰은 1단계에서 바로 `couponId` 반환)
3. **아이템 적용 API 호출** (`couponId` + `vendorItems` 사용) → 두 번째 `requestedId` 반환
4. **아이템 적용 상태 확인 API 호출** → 최종 성공/실패 확인 (즉시할인만, 다운로드쿠폰은 동기)

**문제점:**
- 엑셀에서 상품 옵션ID를 입력받을 방법이 없음
- API 응답에서 `requestedId`를 받아 상태 확인을 해야 하는데, 현재 코드는 이를 무시하고 바로 리턴함
- `assert` 검증이 누락되어 실패를 감지하지 못함

## 결정사항

### 1. 엑셀 파일 구조 변경: 6컬럼 → 7컬럼

| 컬럼 | 이름 | 목적 | 예시 | 비고 |
|------|------|------|------|------|
| A | 쿠폰이름 | 쿠폰 명칭 | "신규회원 할인" | - |
| B | 쿠폰타입 | 즉시할인 또는 다운로드쿠폰 | "즉시할인" | - |
| C | 쿠폰유효기간 | 발급일로부터 며칠간 유효 | "2" (2일) | - |
| D | 할인방식 | RATE/FIXED_WITH_QUANTITY/PRICE | "RATE" | - |
| E | 할인금액/비율 | 할인 금액 또는 비율 | "10" | 할인방식에 따라 의미 다름 |
| F | 발급개수 | 쿠폰 발급 개수 | "100" | 다운로드쿠폰만 사용 |
| **G** | **옵션ID** | **쿠폰을 적용할 상품 옵션ID** | **"3226138951, 3226138847"** | **쉼표로 구분** |

### 2. Column G: 옵션ID (필수)

**형식:**
- 쉼표(`,`)로 구분된 숫자 리스트
- 예: `"3226138951, 3226138847, 4802314648"`
- 공백은 자동으로 제거 (입력 정규화)

**별칭 지원 (ADR 002 입력 정규화):**
- `"옵션ID"` (기본)
- `"옵션 ID"` (공백 포함, 허용)

**파싱 로직:**
```python
# 예: "3226138951, 3226138847, 4802314648"
vendor_items_raw = str(row[col_indices['옵션ID']]).strip()

# 쉼표로 분리 + strip + int 변환
vendor_items = [
    int(item.strip())
    for item in vendor_items_raw.split(',')
    if item.strip()
]
```

**검증:**
- 비어있으면 에러 (필수 입력)
- 각 항목은 양의 정수여야 함
- 즉시할인: 최대 10,000개 (Coupang API 제한)
- 다운로드쿠폰: 최대 100개 (Coupang API 제한)

### 3. 비동기 워크플로우 구현

#### 3.1. 즉시할인쿠폰 (Instant Coupon)

```python
# 1단계: 쿠폰 생성
response1 = api_client.create_instant_coupon(...)  # 전체 응답 반환
req_id1 = response1.get('data', {}).get('content', {}).get('requestedId')
assert req_id1 is not None, "즉시할인쿠폰 생성 실패 (requestedId 없음)"

# 2단계: 쿠폰 생성 상태 확인
response2 = api_client.get_instant_coupon_status(vendor_id, req_id1)
assert response2.get('data', {}).get('content', {}).get('status') == 'DONE', \
    "즉시할인쿠폰 생성 실패 (status != DONE)"
coupon_id = response2.get('data', {}).get('content', {}).get('couponId')
assert coupon_id is not None, "즉시할인쿠폰 생성 실패 (couponId 없음)"

# 3단계: 아이템 적용
response3 = api_client.apply_instant_coupon(vendor_id, coupon_id, vendor_items)
req_id2 = response3.get('data', {}).get('content', {}).get('requestedId')
assert req_id2 is not None, "즉시할인쿠폰 아이템 적용 실패 (requestedId 없음)"

# 4단계: 아이템 적용 상태 확인
response4 = api_client.get_instant_coupon_status(vendor_id, req_id2)
assert response4.get('data', {}).get('content', {}).get('status') == 'DONE', \
    f"즉시할인쿠폰 아이템 적용 실패: {response4.get('data', {}).get('content', {}).get('failedVendorItems')}"
```

#### 3.2. 다운로드쿠폰 (Download Coupon)

```python
# 1단계: 쿠폰 생성 (동기 API - 바로 couponId 반환)
response1 = api_client.create_download_coupon(...)  # 전체 응답 반환
coupon_id = response1.get('couponId')
assert coupon_id is not None, "다운로드쿠폰 생성 실패 (couponId 없음)"

# 2단계: 아이템 적용 (동기 API)
response2 = api_client.apply_download_coupon(coupon_id, user_id, vendor_items)
assert response2.get('requestResultStatus') == 'SUCCESS', \
    f"다운로드쿠폰 아이템 적용 실패: {response2.get('errorMessage')}"
```

### 4. API 클라이언트 메서드 시그니처 변경

**변경 전 (잘못된 설계):**
```python
def create_instant_coupon(...) -> str:  # requestedId만 리턴
    return response.get('data', {}).get('content', {}).get('requestedId')
```

**변경 후 (올바른 설계):**
```python
def create_instant_coupon(...) -> Dict[str, Any]:  # 전체 응답 리턴
    return result  # 호출자가 필요한 필드를 직접 추출

def get_instant_coupon_status(vendor_id: str, requested_id: str) -> Dict[str, Any]:
    """즉시할인쿠폰 상태 확인 (생성/아이템 적용 공통)"""
    path = f"/v2/providers/fms/apis/api/v1/vendors/{vendor_id}/requested/{requested_id}"
    return self._request("GET", path)

def apply_download_coupon(coupon_id: int, user_id: str, vendor_items: List[int]) -> Dict[str, Any]:
    """다운로드쿠폰 아이템 적용"""
    path = "/v2/providers/marketplace_openapi/apis/api/v1/coupon-items"
    payload = {
        "couponItems": [{
            "couponId": str(coupon_id),
            "userId": user_id,
            "vendorItemIds": vendor_items
        }]
    }
    return self._request("PUT", path, json_data=payload)
```

## 근거

### 1. 상품 지정 필수성

쿠폰은 반드시 특정 상품에 적용되어야 하므로, 옵션ID는 **필수 입력**입니다. 하드코딩된 더미 값으로는 실제 운영이 불가능합니다.

### 2. 비동기 API 처리 정확성

Coupang API는 비동기로 동작하므로, `requestedId`를 받아 상태를 확인해야 합니다. 이를 무시하면:
- 쿠폰 생성 실패를 감지하지 못함
- 아이템 적용 실패를 감지하지 못함
- `failedVendorItems` 오류 메시지를 놓침

### 3. API 응답 전체 반환

메서드가 `requestedId`만 리턴하면:
- 호출자가 다른 필드(예: `success`)를 확인할 수 없음
- 검증 로직을 메서드 내부에 넣어야 하는데, 그러면 재사용성이 떨어짐
- 전체 응답을 반환하면 호출자가 필요한 필드를 유연하게 추출 가능

### 4. 유연한 입력 형식

쉼표로 구분된 ID 리스트는 사용자가 엑셀에서 입력하기 쉽습니다:
- 복사-붙여넣기 용이
- 가독성 좋음
- 공백 허용으로 실수 방지 (ADR 002 입력 정규화)

## 예시

### 즉시할인 엑셀 입력

| 쿠폰이름 | 쿠폰타입 | 쿠폰유효기간 | 할인방식 | 할인금액/비율 | 발급개수 | 옵션ID |
|----------|----------|--------------|----------|---------------|----------|--------|
| 신규회원10%할인 | 즉시할인 | 30 | RATE | 10 | | 3226138951, 3226138847 |
| VIP정액할인 | 즉시할인 | 7 | PRICE | 5000 | | 4802314648 |

### 다운로드쿠폰 엑셀 입력

| 쿠폰이름 | 쿠폰타입 | 쿠폰유효기간 | 할인방식 | 할인금액/비율 | 발급개수 | 옵션ID |
|----------|----------|--------------|----------|---------------|----------|--------|
| 다운로드10%쿠폰 | 다운로드쿠폰 | 30 | RATE | 10 | 500 | 2306264997, 4802314648 |
| 다운로드정액쿠폰 | 다운로드쿠폰 | 7 | PRICE | 2000 | 1000 | 4230264914 |

## 대안

### 대안 1: 별도 엑셀 시트로 옵션ID 관리 (거부됨)

두 번째 시트를 만들어 "쿠폰이름-옵션ID" 매핑 관리

- **장점**: 여러 옵션ID를 관리하기 쉬움
- **단점**: 복잡도 증가, 사용자 혼란
- **거부 이유**: 과도한 복잡성, 단일 시트가 더 직관적

### 대안 2: 줄바꿈으로 구분 (거부됨)

셀 안에서 줄바꿈(`Alt+Enter`)으로 ID 구분

- **장점**: 가독성
- **단점**: 파싱 복잡도, 복사-붙여넣기 어려움
- **거부 이유**: 쉼표가 더 범용적

### 대안 3: 옵션ID를 별도 파일로 관리 (거부됨)

JSON 또는 CSV로 별도 파일 생성

- **장점**: 프로그래밍 친화적
- **단점**: 사용자가 두 파일 관리 필요, 동기화 문제
- **거부 이유**: 사용자 경험 저하

## 영향

### 코드 변경 (Source Code)

1. **issuer.py**:
   - `_fetch_coupons_from_excel()`: 7컬럼 파싱 로직, 옵션ID 파싱
   - `_issue_single_coupon()`: 비동기 워크플로우 구현, assert 검증 추가
   - 선택적: `_issue_instant_coupon()`, `_issue_download_coupon()` 내부 메서드 분리

2. **coupang_api.py**:
   - `create_instant_coupon()`: 전체 응답 반환 (`Dict[str, Any]`)
   - `create_download_coupon()`: 전체 응답 반환 (`Dict[str, Any]`)
   - `apply_download_coupon()`: 새로 추가 (다운로드쿠폰 아이템 적용)
   - 주석 추가: 모든 메서드에 docstring

3. **ADR 009**: "Superseded by ADR 015" 표시

### 테스트 변경 (Tests)

1. **conftest.py**: Fixture를 7컬럼으로 수정
2. **test_issuer.py**: 32개 테스트 업데이트
3. **test_coupang_api.py**: 12개 테스트 업데이트 (리턴값 검증)
4. **test_cli.py**: 21개 테스트 업데이트
5. **tests/fixtures/*.xlsx**: 4개 엑셀 파일 업데이트

### 문서 변경 (Documentation)

1. **ADR 009**: "Updated by ADR 015" 표시
2. **DEV_LOG.md**: 옵션ID 컬럼 추가 결정 기록
3. **CLAUDE.md**: 예시 업데이트

## 참조

- [ADR 002: 입력 정규화](002-input-normalization.md) (옵션ID 파싱에 적용)
- [ADR 007: 쿠폰 발급 워크플로우](007-coupon-issuance-workflow.md) (비동기 처리)
- [ADR 009: 엑셀 6컬럼 구조](009-excel-6-column-structure.md) (Updated)
- [Coupang API 워크플로우](../coupang/workflow.md)
- [즉시할인쿠폰 생성 API](../coupang/instant-coupon-api.md)
- [즉시할인쿠폰 아이템 생성 API](../coupang/instant-coupon-item-api.md)
- [즉시할인쿠폰 상태 확인 API](../coupang/instant-coupon-status-api.md)
- [다운로드쿠폰 생성 API](../coupang/download-coupon-api.md)
- [다운로드쿠폰 아이템 생성 API](../coupang/download-coupon-item-api.md)
