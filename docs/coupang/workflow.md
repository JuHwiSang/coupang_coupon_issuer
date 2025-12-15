# Coupang 쿠폰 발급 워크플로우

Coupang API를 통한 쿠폰 발급의 전체 프로세스를 설명합니다.

## 개요

Coupang 쿠폰 발급은 **다단계 비동기 프로세스**입니다:

1. **쿠폰 생성** (Coupon Creation)
2. **아이템 적용** (Item Assignment)
3. **상태 확인** (Status Check)

각 단계마다 API 호출이 필요하며, 비동기 처리를 위해 `requestedId`를 사용하여 결과를 확인해야 합니다.

---

## 즉시할인쿠폰 워크플로우

### 1단계: 쿠폰 생성

```
POST /v2/providers/fms/apis/api/v2/vendors/{vendorId}/coupon
```

**요청**:
```json
{
  "contractId": "-1",
  "name": "신규 쿠폰",
  "maxDiscountPrice": "1000",
  "discount": "10",
  "startAt": "2024-12-16 00:00:00",
  "endAt": "2024-12-18 23:59:59",
  "type": "PRICE",
  "wowExclusive": "false"
}
```

**응답**:
```json
{
  "code": 200,
  "data": {
    "content": {
      "requestedId": "123543582159745830895",  // ← 1단계 상태 확인용
      "success": true
    }
  }
}
```

### 2단계: 쿠폰 생성 상태 확인

```
GET /v2/providers/fms/apis/api/v1/vendors/{vendorId}/requested/{requestedId}
```

**응답** (성공):
```json
{
  "data": {
    "content": {
      "couponId": 778,  // ← 쿠폰 ID (다음 단계에서 사용)
      "requestedId": "123543582159745830895",
      "type": "COUPON_PUBLISH",
      "status": "DONE",  // ← DONE이면 성공
      "succeeded": 1,
      "failed": 0
    }
  }
}
```

**응답** (실패):
```json
{
  "data": {
    "content": {
      "status": "FAIL",  // ← FAIL이면 실패 → 1단계부터 재시도
      "failed": 1
    }
  }
}
```

### 3단계: 아이템 적용

```
POST /v2/providers/fms/apis/api/v1/vendors/{vendorId}/coupons/{couponId}/items
```

**요청**:
```json
{
  "vendorItems": [3226138951, 3226138847]  // 쿠폰을 적용할 상품 옵션 ID
}
```

**응답**:
```json
{
  "data": {
    "content": {
      "requestedId": "17258005702255081464",  // ← 3단계 상태 확인용
      "success": true
    }
  }
}
```

### 4단계: 아이템 적용 상태 확인

```
GET /v2/providers/fms/apis/api/v1/vendors/{vendorId}/requested/{requestedId}
```

**응답** (성공):
```json
{
  "data": {
    "content": {
      "couponId": 778,
      "type": "COUPON_ITEM_PUBLISH",
      "status": "DONE",  // ← DONE이면 성공
      "total": 2,
      "succeeded": 2,
      "failed": 0,
      "failedVendorItems": []
    }
  }
}
```

**응답** (실패):
```json
{
  "data": {
    "content": {
      "status": "FAIL",  // ← FAIL이면 실패 → 1단계부터 재시도
      "total": 2,
      "succeeded": 0,
      "failed": 2,
      "failedVendorItems": [
        {
          "vendorItemId": 3226138951,
          "reason": "[CIR08] 해당 옵션은 이미 다른 쿠폰에 발행되어져 있습니다."
        }
      ]
    }
  }
}
```

---

## 다운로드쿠폰 워크플로우

### 1단계: 쿠폰 생성

```
POST /v2/providers/marketplace_openapi/apis/api/v1/coupons
```

**요청**:
```json
{
  "title": "다운로드 쿠폰",
  "contractId": "-1",
  "couponType": "DOWNLOAD",
  "startDate": "2024-12-16 00:00:00",
  "endDate": "2024-12-18 23:59:59",
  "userId": "testaccount1",
  "policies": [
    {
      "title": "1만원 이상 1천원 할인",
      "typeOfDiscount": "PRICE",
      "description": "10,000원 이상 구매시",
      "minimumPrice": 10000,
      "discount": 1000,
      "maximumDiscountPrice": 1000,
      "maximumPerDaily": 1
    }
  ]
}
```

**응답**:
```json
{
  "couponId": 15354534,  // ← 쿠폰 ID (다음 단계에서 사용)
  "couponStatus": "STANDBY"  // ← 생성 직후 상태
}
```

**참고**: 다운로드쿠폰 생성은 동기 API이므로 즉시 couponId를 반환합니다.

### 2단계: 아이템 적용

```
PUT /v2/providers/marketplace_openapi/apis/api/v1/coupon-items
```

**요청**:
```json
{
  "couponItems": [
    {
      "couponId": "15354534",
      "userId": "testaccount1",
      "vendorItemIds": [2306264997, 4802314648]
    }
  ]
}
```

**응답** (성공):
```json
{
  "requestResultStatus": "SUCCESS",
  "body": {
    "couponId": 15354534
  }
}
```

**응답** (실패):
```json
{
  "requestResultStatus": "FAIL",
  "errorCode": "...",
  "errorMessage": "삭제된 프로모션 입니다."  // ← 아이템 적용 실패 시 쿠폰 삭제됨
}
```

**⚠️ 중요**: 다운로드쿠폰의 경우 **아이템 적용에 실패하면 쿠폰이 파기**됩니다. 실패 시 1단계부터 재시도해야 합니다.

---

## 본 프로젝트의 구현 전략

### 워크플로우 구현

각 쿠폰 발급 시 다음 순서로 진행:

1. **쿠폰 생성 API 호출**
2. **상태 확인** (즉시할인쿠폰만, 폴링 또는 재시도)
   - `status == "DONE"`: 성공 → 다음 단계
   - `status == "FAIL"`: 실패 → **1단계부터 재시도**
   - `status == "REQUESTED"`: 대기 중 → 재확인
3. **아이템 적용 API 호출** (vendorItemIds 전달)
4. **아이템 적용 상태 확인** (즉시할인쿠폰만)
   - `status == "DONE"`: 성공 → 완료
   - `status == "FAIL"`: 실패 → **1단계부터 재시도**

### 재시도 정책

- 각 단계에서 실패 시 **전체 프로세스를 처음부터 재시도**
- 최대 재시도 횟수 설정 (예: 3회)
- 재시도 간격: 지수 백오프 또는 고정 간격 (예: 5초)

### 상태 확인 폴링

- 비동기 API의 경우 상태 확인을 주기적으로 수행
- 폴링 간격: 2~5초
- 최대 대기 시간: 60초 (타임아웃)

### 에러 처리

- 각 단계의 실패 이유를 로그에 기록
- 엑셀 결과 파일에 실패 사유 포함
- `failedVendorItems`의 상세 오류 메시지 저장

---

## 상태 코드 정리

### 즉시할인쿠폰 상태 (status)

| 코드 | 의미 | 조치 |
|------|------|------|
| `REQUESTED` | 요청됨 (처리 중) | 재확인 필요 |
| `DONE` | 성공 | 다음 단계 진행 |
| `FAIL` | 실패 | 재시도 (1단계부터) |

### 다운로드쿠폰 상태 (requestResultStatus)

| 코드 | 의미 | 조치 |
|------|------|------|
| `SUCCESS` | 성공 | 완료 |
| `FAIL` | 실패 | 재시도 (1단계부터) |

---

## 관련 문서

- [즉시할인쿠폰 생성 API](instant-coupon-api.md)
- [즉시할인쿠폰 아이템 생성 API](instant-coupon-item-api.md)
- [즉시할인쿠폰 상태 확인 API](instant-coupon-status-api.md)
- [다운로드쿠폰 생성 API](download-coupon-api.md)
- [다운로드쿠폰 아이템 생성 API](download-coupon-item-api.md)
- [ADR 007: 쿠폰 발급 워크플로우](../adr/007-coupon-issuance-workflow.md)
