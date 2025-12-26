# Coupang API: 다운로드쿠폰 아이템 생성

> **출처**: Coupang WING API 공식 문서

## 개요

API 적용 가능한 구매자 사용자 지역: **한국**

옵션상품(vendorItemId)에 생성된 다운로드 쿠폰을 적용하기 위한 API입니다.

## ⚠️ 중요 제약사항

**상품 추가에 실패하면 해당 쿠폰은 파기됩니다.**

쿠폰 생성 후 아이템 적용에 실패하면 쿠폰 자체가 삭제되므로, 반드시 유효한 vendorItemId를 사용해야 합니다.

## API 엔드포인트

```
PUT /v2/providers/marketplace_openapi/apis/api/v1/coupon-items
```

**Example Endpoint:**
```
https://api-gateway.coupang.com/v2/providers/marketplace_openapi/apis/api/v1/coupon-items
```

## Request Parameters

### Body Parameters

| Name | Required | Type | Description |
|------|----------|------|-------------|
| `couponItems` | O | Array | 상품 쿠폰적용을 위한 데이터 |
| `couponItems[].couponId` | O | Number | 쿠폰ID<br/>쿠폰생성 Response에서 확인 가능 |
| `couponItems[].userId` | O | String | 사용자 계정 (WING 로그인 ID) |
| `couponItems[].vendorItemIds` | O | Array | 쿠폰 적용하고자 하는 옵션ID(s)<br/>**한 번에 적용할 옵션ID 수는 100개를 초과할 수 없음** |

## Request Example

```json
{
  "couponItems": [
    {
      "couponId": 15350660,
      "userId": "testaccount1",
      "vendorItemIds": [
        2306264997,
        4802314648,
        4230264914
      ]
    }
  ]
}
```

## Response Message

> [!CAUTION]
> **공식 문서 오류 발견 (2025-12-26)**
> 
> Coupang 공식 API 문서에는 응답이 단일 객체로 표기되어 있으나, **실제로는 배열(Array)로 반환됩니다.**
> 
> 이 문서는 실제 API 동작에 맞춰 수정되었습니다.

**응답 형식**: Array (배열)

각 배열 요소는 다음 필드를 포함합니다:

| Name | Type | Description |
|------|------|-------------|
| `requestResultStatus` | String | 호출 결과<br/>`SUCCESS` / `FAIL` |
| `body` | Object | 응답 본문 |
| `body.couponId` | Integer | 해당 쿠폰 ID |
| `body.requestTransactionId` | String | 요청 트랜잭션 ID |
| `errorCode` | String | 에러발생 시 분류 |
| `errorMessage` | String | 에러 상세내용 |

## Response Example

**실제 응답 (배열 형식)**:
```json
[{
  "requestResultStatus": "SUCCESS",
  "body": {
    "couponId": 88385733,
    "requestTransactionId": "usersomeid_883857331766744556994"
  },
  "errorCode": null,
  "errorMessage": null
}]
```

**공식 문서 예시 (잘못됨)**:
```json
{
  "requestResultStatus": "SUCCESS",
  "body": {
    "couponId": 15350660
  },
  "errorCode": null,
  "errorMessage": null
}
```

> [!WARNING]
> **중요**: 응답 처리 시 반드시 배열의 첫 번째 요소(`response[0]`)에서 데이터를 추출해야 합니다.


## Error Spec

| HTTP 상태 코드 (오류 유형) | 오류 메시지 | 해결 방법 |
|---------------------------|------------|----------|
| 400 (요청변수확인) | `삭제된 프로모션 입니다.` | 쿠폰ID(couponId) 값을 올바로 입력했는지 확인합니다.<br/>옵션에 쿠폰 적용이 실패하여 쿠폰ID가 삭제되었는지 확인합니다. |

## URL API Name

**Add_VENDOR_ITEMS_TO_COUPON**
