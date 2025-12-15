# Coupang API: 즉시할인쿠폰 요청상태 확인

> **출처**: Coupang WING API 공식 문서

## 개요

API 적용 가능한 구매자 사용자 지역: **한국**

`requestedId`를 통해 즉시할인 쿠폰 API의 요청 결과를 확인합니다.

쿠폰생성, 쿠폰파기, 쿠폰아이템 생성, 쿠폰아이템 파기 API 요청 시에 반환되는 `requestedId` 값을 가지고 성공/실패(DONE/FAIL) 결과를 확인할 때 사용합니다.

## API 엔드포인트

```
GET /v2/providers/fms/apis/api/v1/vendors/{vendorId}/requested/{requestedId}
```

**Example Endpoint:**
```
https://api-gateway.coupang.com/v2/providers/fms/apis/api/v1/vendors/A00000001/requested/649102321051192483
```

## Request Parameters

### Path Segment Parameters

| Name | Required | Type | Description |
|------|----------|------|-------------|
| `vendorId` | O | String | 판매자ID<br/>쿠팡에서 업체에게 발급한 고유 코드<br/>예) `A00012345` |
| `requestedId` | O | Number | 결과를 조회할 ID |

## Request Example

```
not require body
```

## Response Message

| Name | Type | Description |
|------|------|-------------|
| `code` | Number | 서버 응답 코드 |
| `message` | String | 서버 응답 메세지 |
| `httpStatus` | Number | HTTP Status Code (서버 응답 코드와 동일한 값) |
| `httpStatusMessage` | String | HTTP Status Message (서버 응답 메세지와 동일한 값) |
| `errorMessage` | String | HTTP Status 200을 제외한 나머지 Status에서 서버 내 상세한 실패 이유 메세지가 담깁니다. |
| `data` | Object | 수행 성공 여부 데이터 |
| `data.success` | Boolean | 성공 여부 (true or false) |
| `data.content` | Object | 처리 상태를 조회할 수 있는 요청ID 데이터 |
| `data.content.couponId` | Number | 쿠폰 ID (Wing의 쿠폰 번호)<br/>예) 70, 85, 778 |
| `data.content.requestedId` | String | 처리 상태 조회를 위한 요청ID<br/>예) `1542675975663862164` |
| `data.content.status` | String | 처리 상태<br/>`REQUESTED`: 요청됨<br/>`FAIL`: 실패<br/>`DONE`: 성공 |
| `data.content.succeeded` | Number | 성공 개수 |
| `data.content.total` | Number | 요청 건수 (쿠폰 아이템생성의 경우 vendorItemId의 전체 갯수) |
| `data.content.type` | String | 요청타입<br/>`COUPON_PUBLISH`: 쿠폰생성<br/>`COUPON_EXPIRE`: 쿠폰파기<br/>`COUPON_ITEM_PUBLISH`: 쿠폰아이템생성<br/>`COUPON_ITEM_EXPIRE`: 쿠폰아이템 파기 |
| `data.content.failed` | Number | 실패 개수 |
| `data.content.failedVendorItems` | Array | 실패한 정보에 대한 상세 데이터 |
| `data.content.failedVendorItems[].reason` | String | 실패 이유 |
| `data.content.failedVendorItems[].vendorItemId` | Long | 실패한 vendorItemId |
| `data.Pagination` | null | 페이징 없음 |

## Response Example

### 성공 예시

```json
{
  "code": 200,
  "message": "OK",
  "httpStatus": 200,
  "httpStatusMessage": "OK",
  "errorMessage": "",
  "data": {
    "success": true,
    "content": {
      "couponId": 778,
      "requestedId": "4080133932843441",
      "type": "COUPON_PUBLISH",
      "status": "DONE",
      "total": 1,
      "succeeded": 1,
      "failed": 0,
      "failedVendorItems": []
    },
    "pagination": null
  }
}
```

## Error Spec

| HTTP 상태 코드 (오류 유형) | 오류 메시지 | 해결 방법 |
|---------------------------|------------|----------|
| 400 (요청변수확인) | `업체정보의 권한을 확인하세요.` | 올바른 판매자ID(vendorId) 값을 입력했는지 확인합니다. |

## 실패한 정보에 대한 상세 데이터 예제

| 오류 메시지 예제 | 해결 방법 |
|----------------|----------|
| `failedVendorItems":[{"vendorItemId":32261389517,"reason":"[CIE00] 유효하지 않은 옵션아이디 입니다.` | 올바른 옵션ID(vendorItemId)를 입력했는지 확인합니다. |
| `failedVendorItems":[{"vendorItemId":32261388477,"reason":"[CIR06] 옵션 상품을 찾지 못했습니다.` | 올바른 옵션ID(vendorItemId)를 입력했는지 확인합니다. |
| `failedVendorItems":[{"vendorItemId":3226138847,"reason":"[CIR08] 해당 옵션은 이미 다른 쿠폰에 발행되어져 있습니다.` | 올바른 옵션ID(vendorItemId)를 입력했는지 확인합니다. |
