# 다운로드쿠폰 파기 API

## API 정보

- **경로**: `POST /v2/providers/marketplace_openapi/apis/api/v1/coupons/expire`
- **URL API Name**: `EXPIRE_COUPONS`
- **적용 가능한 구매자 사용자 지역**: 한국
- **설명**: 생성된 다운로드 쿠폰을 파기(만료)합니다.

실제 API 수행 결과값은 응답으로 받은 `requestTransactionId`를 이용하여 '다운로드 쿠폰 요청상태 확인 API'를 조회하면 확인 가능합니다.

## Example Endpoint

```
https://api-gateway.coupang.com/v2/providers/marketplace_openapi/apis/api/v1/coupons/expire
```

## Request Parameters

### Body Parameter

| Name | Required | Type | Description |
|------|----------|------|-------------|
| expireCouponList | O | Array | 다운로드 쿠폰 파기를 위한 데이터 |
| ↳ couponId | O | Integer | 쿠폰ID (쿠폰생성 Response에서 확인 가능) |
| ↳ reason | O | String | `expired` 입력 |
| ↳ userId | O | String | 사용자 계정 (WING 로그인 ID) |

### Request Example

```json
{  
   "expireCouponList":[  
      {  
         "couponId": 16513129,
         "reason": "expired",
         "userId": "testId123"
      }
   ]
}
```

## Response Message

| Name | Type | Description |
|------|------|-------------|
| requestResultStatus | String | 호출 결과 (`SUCCESS` / `FAIL`) |
| body | Object | 응답 본문 |
| ↳ couponId | Long | 쿠폰ID (쿠폰생성 Response 에서 확인 가능) |
| ↳ requestTransactionId | String | 호출결과 확인 토큰 값 |
| errorCode | String | 에러발생 시 분류 |
| errorMessage | String | 에러 상세내용 |

### Response Example

```json
[
  {
    "requestResultStatus": "SUCCESS",
    "body": {
      "couponId": 16513129,
      "requestTransactionId": "et5_165131291561017478962"
    },
    "errorCode": null,
    "errorMessage": null
  }
]
```

## Error Spec

| HTTP 상태 코드 (오류 유형) | 오류 메시지 | 해결 방법 |
|---------------------------|------------|----------|
| 500 (요청변수확인) | expire할 쿠폰이 존재하지 않습니다. | 쿠폰ID(couponId) 값을 올바로 입력했는지 확인합니다. |

## 구현 참고사항

### Python 구현 예시

```python
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
    """
    path = "/v2/providers/marketplace_openapi/apis/api/v1/coupons/expire"
    
    payload = {
        "expireCouponList": expire_list
    }
    
    return self._request("POST", path, json_data=payload)
```

### 응답 처리

응답은 **배열 형식**으로 반환됩니다:

```python
response = api_client.expire_download_coupons(expire_list)

for result in response:
    status = result.get('requestResultStatus')
    coupon_id = result.get('body', {}).get('couponId')
    
    if status == 'SUCCESS':
        print(f"쿠폰 파기 성공: {coupon_id}")
    else:
        error_msg = result.get('errorMessage')
        print(f"쿠폰 파기 실패: {coupon_id}, {error_msg}")
```

## 관련 API

- [다운로드쿠폰 생성 API](download-coupon-api.md)
- [다운로드쿠폰 아이템 적용 API](download-coupon-item-api.md)
- [다운로드쿠폰 요청상태 확인 API](download-coupon-status-api.md)
