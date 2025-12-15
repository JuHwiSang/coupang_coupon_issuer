# Coupang API: 다운로드쿠폰 요청상태 확인

> **출처**: Coupang WING API 공식 문서

## 개요

API 적용 가능한 구매자 사용자 지역: **한국**

`requestTransactionId`를 이용하여 쿠폰아이템 생성 API 요청 결과를 확인합니다.

## API 엔드포인트

```
GET /v2/providers/marketplace_openapi/apis/api/v1/coupons/transactionStatus
```

**Example Endpoint:**
```
https://api-gateway.coupang.com/v2/providers/marketplace_openapi/apis/api/v1/coupons/transactionStatus?requestTransactionId=et5_154210571558673553106
```

## Request Parameters

### Query String Parameters

| Name | Required | Type | Description |
|------|----------|------|-------------|
| `requestTransactionId` | O | Number | 결과를 조회할 ID |

## Request Example

```
not require body
```

## Response Message

| Name | Type | Description |
|------|------|-------------|
| `transactionStatusResponse` | Object | 호출응답 상세 |
| `transactionStatusResponse.type` | String | 상태 확인 대상 API |
| `transactionStatusResponse.total` | Number | 요청 vendoritem 수 |
| `transactionStatusResponse.succeeded` | Number | 호출 성공 vendoritem 수 |
| `transactionStatusResponse.status` | String | 호출 결과 |
| `transactionStatusResponse.requestedId` | String | 응답 조회 Key |
| `transactionStatusResponse.couponFailedVendorItemIdResponses` | Array | 등록실패 vendoritemId 상세 사유 |
| `transactionStatusResponse.couponFailedVendorItemIdResponses[].vendorItemId` | Number | API 호출에 사용한 옵션ID |
| `transactionStatusResponse.couponFailedVendorItemIdResponses[].failureReason` | String | 호출 실패 사유 |
| `transactionStatusResponse.failed` | Number | 호출 실패 vendoritem 수 |
| `transactionStatusResponse.couponId` | Number | 해당 쿠폰ID |

## Response Example

```json
{
  "transactionStatusResponse": {
    "type": "COUPON_ITEM_PUBLISH",
    "total": 1,
    "succeeded": 0,
    "status": "FAIL",
    "requestedId": "et5_154210571558673553106",
    "couponFailedVendorItemIdResponses": [
      {
        "vendorItemId": 4712512759,
        "failureReason": "[CIR14] 해당 옵션은 이미 다른 쿠폰(14434486 외 2건)에 발행되어져 있습니다."
      }
    ],
    "failed": 1,
    "couponId": 15421057
  }
}
```

## Error Spec

| HTTP 상태 코드 (오류 유형) | 오류 메시지 | 해결 방법 |
|---------------------------|------------|----------|
| 500 (요청변수확인) | `시스템 오류` | requestTransactionId 값을 올바로 입력했는지 확인합니다. |

## URL API Name

**GET_REQUEST_STATUS_BY_TRANSACTION_ID**
