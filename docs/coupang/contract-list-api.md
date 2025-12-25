# 계약 목록 조회 API

현재 설정된 모든 계약의 목록을 조회하기 위한 API로 자유계약기반(NON_CONTRACT_BASED)과 계약기반(CONTRACT_BASED) 타입 계약서 모두 조회 가능합니다.

## API 정보

**적용 가능한 구매자 사용자 지역**: 한국

**Endpoint**:
```
GET /v2/providers/fms/apis/api/v2/vendors/{vendorId}/contract/list
```

**Example URL**:
```
https://api-gateway.coupang.com/v2/providers/fms/apis/api/v2/vendors/A00012345/contract/list
```

## Request Parameters

### Path Segment Parameter

| Name | Required | Type | Description |
|------|----------|------|-------------|
| vendorId | O | String | 판매자ID<br>쿠팡에서 업체에게 발급한 고유 코드<br>예) A00012345 |

### Request Example

```
not require body
```

## Response Message

| Name | Type | Description |
|------|------|-------------|
| code | Number | 서버 응답 코드 |
| message | String | 서버 응답 메세지 |
| httpStatus | Number | HTTP Status Code(서버 응답 코드와 동일한 값) |
| httpStatusMessage | String | HTTP Status Message (서버 응답 메세지와 동일한 값) |
| errorMessage | String | HTTP Status 200을 제외한 나머지 Status에서 서버 내 상세한 실패 이유 메세지가 담깁니다. |
| data | Array | 계약서 목록 데이터 |
| ㄴ success | Boolean | 성공 여부<br>true or false |
| ㄴ content | Array | 계약서 목록 |
| ㄴㄴ contractId | Number | 업체의 계약서 아이디<br>예) 1, 2 |
| ㄴㄴ vendorContractId | Number | 업체의 계약서 코드(쿠팡 관리 코드)<br>예) -1, 1, 2 |
| ㄴㄴ sellerId | String | 판매자ID<br>예)A00012345 |
| ㄴㄴ sellerShareRatio | Number | 해당 계약서에 명시된 업체 분담율(%)<br>예) 100.0 |
| ㄴㄴ coupangShareRatio | Number | 해당 계약서에 명시된 쿠팡 분담율(%)<br>예) 100.0 |
| ㄴㄴ gmvRatio | Number | 월별 매출 비율, 월별 예산을 쿠팡에서의 매출을 기반으로 자동 생성<br>예) 100.0 |
| ㄴㄴ start | String | 시작일시<br>예) 2018-01-22 00:00:00 |
| ㄴㄴ end | String | 종료일시<br>예) 2018-12-31 23:59:59 |
| ㄴㄴ type | String | 계약 유형<br>예) CONTRACT_BASED, NON_CONTRACT_BASED |
| ㄴㄴ usedBudget | Boolean | 예산제한 사용 여부<br>예) true, false<br>현재는 사용되지 않는 필드이며 true가 기본값입니다. |
| ㄴㄴ modifiedAt | String | 최종 수정 일시<br>예) 2017-09-25 11:40:01 |
| ㄴㄴ modifiedBy | String | 최종 수정자ID |
| ㄴ Pagination | Array | 페이징 |
| ㄴㄴ countPerPage | Number | 페이지 별 데이터 Count<br>예) 10, 20, 30 |
| ㄴㄴ currentPage | Number | 현재 페이지<br>예) 1 |
| ㄴㄴ totalPages | Number | 전체 페이지 Count<br>예) 1000 |
| ㄴㄴ totalElements | Number | 전체 데이터 Count<br>예) 1000 |

## Response Example

```json
{
  "code": 200,
  "message": "OK",
  "httpStatus": 200,
  "httpStatusMessage": "OK",
  "errorMessage": "",
  "data": {
    "success": true,
    "content": [
      {
        "contractId": 1,
        "vendorContractId": 2,
        "sellerId": "A00012345",
        "sellerShareRatio": 100,
        "coupangShareRatio": 0,
        "gmvRatio": 10,
        "start": "2017-03-01 00:00:00",
        "end": "2017-12-31 23:59:59",
        "type": "CONTRACT_BASED",
        "useBudget": true,
        "modifiedAt": "2017-09-21 10:57:07",
        "modifiedBy": "pronimance"
      },
      {
        "contractId": 15,
        "vendorContractId": -1,
        "sellerId": "A00013264",
        "sellerShareRatio": 100,
        "coupangShareRatio": 0,
        "gmvRatio": 0,
        "start": "2017-09-25 11:40:01",
        "end": "2999-12-31 23:59:59",
        "type": "NON_CONTRACT_BASED",
        "useBudget": true,
        "modifiedAt": "2017-09-25 11:40:01",
        "modifiedBy": "bcho"
      },
      {
        "contractId": 9962,
        "vendorContractId": 7,
        "sellerId": "A00012345",
        "sellerShareRatio": 100,
        "coupangShareRatio": 0,
        "gmvRatio": 100,
        "start": "2018-01-22 00:00:00",
        "end": "2018-12-31 23:59:59",
        "type": "CONTRACT_BASED",
        "useBudget": true,
        "modifiedAt": "2018-01-22 16:07:10",
        "modifiedBy": "allie"
      }
    ],
    "pagination": null
  }
}
```

## Error Spec

| HTTP 상태 코드 (오류 유형) | 오류 메시지 | 해결 방법 |
|---------------------------|------------|----------|
| 401 (요청변수확인) | 업체정보의 권한을 확인하세요. | 판매자ID(vendorId) 값을 올바로 입력했는지 확인합니다. |

## 계약 타입 설명

### NON_CONTRACT_BASED (자유계약기반)
- `vendorContractId`가 `-1`인 계약
- 별도의 계약서 없이 자유롭게 쿠폰을 발급할 수 있는 계약
- 일반적으로 종료일이 먼 미래(`2999-12-31 23:59:59`)로 설정됨
- **본 시스템에서 사용하는 계약 타입**

### CONTRACT_BASED (계약기반)
- `vendorContractId`가 양수인 계약
- 특정 계약서에 기반한 쿠폰 발급
- 계약 기간이 명확하게 정의됨

## 사용 예시

본 시스템에서는 자유계약기반(NON_CONTRACT_BASED) 계약만을 사용하여 쿠폰을 발급합니다:

1. 계약 목록 API를 호출하여 모든 계약 조회
2. `type`이 `NON_CONTRACT_BASED`이고 `vendorContractId`가 `-1`인 계약 필터링
3. 해당 계약의 `contractId`를 사용하여 쿠폰 생성
