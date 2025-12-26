# ADR 022: 다운로드쿠폰 시작일 및 최소구매금액 수정

**상태**: 승인됨  
**날짜**: 2025-12-26  
**결정자**: 프로젝트 오너  

## 컨텍스트

다운로드쿠폰 발급 시 다음 두 가지 API 에러가 발생했습니다:

### 1. "Please check the promotion period."

**기존 로직**:
```python
# issuer.py:208
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
start_date = today.strftime('%Y-%m-%d %H:%M:%S')  # 오늘 0시
```

**문제**:
- 현재 시각이 오늘 0시를 지난 경우 (예: 오후 2시), `start_date`가 과거 시각이 됨
- Coupang API는 과거 시작일을 거부

**테스트 케이스**:
```json
{
  "startDate": "2025-12-26 00:00:00",  // 오늘 0시
  "endDate": "2025-12-27 00:00:00"
}
// 현재 시각: 2025-12-26 14:01:18
// → 에러: "Please check the promotion period."
```

### 2. "policies[0] Invalid Amount Unit."

**기존 로직**:
```python
# reader.py:144
min_purchase_price = 1  # 기본값
```

**문제**:
- 다운로드쿠폰 API는 **10원 단위**만 허용 (최소 10원)
- API 문서 (`download-coupon-api.md:60`): "PRICE: 10원 단위 금액 (최소 10원 이상)"

**테스트 케이스**:
```json
{
  "policies": [{
    "minimumPrice": 1,  // ❌ 10원 단위 위반
    "discount": 1000
  }]
}
// → 에러: "policies[0] Invalid Amount Unit."
```

## 결정사항

### 1. 다운로드쿠폰 시작일/종료일 계산

**변경 위치**: `issuer.py:206-224` (`_issue_single_coupon` 메서드)

**변경 후**:
```python
# 쿠폰 타입별로 시작일 설정
if coupon_type == '즉시할인':
    # 즉시할인: 오늘 0시 (기존 로직 유지)
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = today.strftime('%Y-%m-%d %H:%M:%S')
    end_date = (today + timedelta(days=validity_days)).strftime('%Y-%m-%d %H:%M:%S')
elif coupon_type == '다운로드쿠폰':
    # 다운로드쿠폰: 현재시각 + 1시간 10분 (API 처리 시간 + 안정성 마진)
    now = datetime.now()
    start_date = (now + timedelta(hours=1, minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
    # 유효 종료일: 오늘 자정 + validity_days일 (그날 자정에 만료)
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = (today_midnight + timedelta(days=validity_days)).strftime('%Y-%m-%d %H:%M:%S')
```

**근거**:
- **시작일 (+1시간 10분)**:
  - 초기 시도 (+10초)로는 API 에러 발생 확인
  - 다운로드쿠폰 API 문서: "생성 후 최소 1시간 이후부터 프론트에 반영" (`download-coupon-api.md:16-17`)
  - 1시간 10분으로 충분한 여유 확보
  - 즉시할인쿠폰은 기존 로직 유지 (정상 작동 중)
- **종료일 (자정 기준)**:
  - 원래 스펙: 유효기간 N일 = 오늘 자정부터 N일 후 자정까지
  - 기존 구현 오류: 현재시각 기준으로 계산되어 스펙 위반
  - 수정: 자정 기준으로 계산하여 원래 스펙대로 복원

### 2. 최소구매금액 기본값: 10원

**변경 위치**: `reader.py:144` (`fetch_coupons_from_excel` 함수)

**변경 후**:
```python
else:
    min_purchase_price = 10  # 기본값 (API 최소값: 10원)
```

**근거**:
- API 문서 명시: "10원 단위 금액 (최소 10원 이상)" (`download-coupon-api.md:60`)
- 사용자 입력값 검증은 이미 존재 (`reader.py:191-195`)
- 10원은 실질적으로 "제한 없음"과 동일한 효과

## 근거

### 1. 쿠폰 타입별 차별화

즉시할인쿠폰과 다운로드쿠폰은 API 동작이 다릅니다:

| 항목 | 즉시할인쿠폰 | 다운로드쿠폰 |
|------|-------------|-------------|
| 시작일 | 오늘 0시 (정상 작동) | 현재시각 + 1시간 10분 (수정) |
| 종료일 | 오늘 0시 + N일 | 오늘 자정 + N일 (수정) |
| 최소구매금액 | 사용 안함 | 10원 기본값 (수정) |
| API 타입 | 비동기 | 동기 |

### 2. API 요구사항 준수

- **시작일**: 과거 시각 거부 → 미래 시각 사용
- **최소구매금액**: 10원 단위만 허용 → 10원 기본값 사용

### 3. 하위 호환성

기존 사용자 영향:
- 시작일: 자동 계산되므로 영향 없음
- 최소구매금액: 빈 값이 1원 → 10원으로 변경 (API 요구사항 충족)

## 대안

### 대안 1: 다운로드쿠폰도 오늘 0시 사용 (거부됨)

즉시할인쿠폰과 동일하게 오늘 0시 사용

- **장점**: 로직 단순화
- **단점**: 오늘 0시 이후 발급 시 API 에러
- **거부 이유**: 실제 에러 발생 확인됨

### 대안 2: 최소구매금액 기본값 1원 유지 (거부됨)

기본값 1원 유지, 사용자가 명시적으로 10원 이상 입력

- **장점**: 기존 로직 유지
- **단점**: API 에러 발생, 사용자 혼란
- **거부 이유**: API 요구사항 위반

### 대안 3: 현재시각 + 1시간 또는 + 10초 사용 (거부됨)

API 문서에 명시된 "최소 1시간" 정확히 사용하거나, 최소한의 10초만 사용

- **장점**: 
  - +1시간: API 문서 정확히 준수
  - +10초: 최소한의 지연
- **단점**: 
  - +1시간: 안정성 마진 부족
  - +10초: API 처리 시간 부족 가능성
- **거부 이유**: 1시간 10분이 안정성과 대기 시간의 균형점

## 영향

### 코드 변경

1. **issuer.py**: 쿠폰 타입별 시작일 계산 로직 추가 (18줄)
2. **reader.py**: 최소구매금액 기본값 변경 (1줄)

### 테스트 변경

1. **test_issuer.py**: 다운로드쿠폰 시작일 검증 로직 수정 필요
2. **test_reader.py**: 최소구매금액 기본값 검증 수정 필요

### 문서 변경

1. **ADR 022**: 본 문서
2. **DEV_LOG.md**: 변경사항 간단 기록

## 검증

### 수정 전 (에러 발생)

```json
{
  "title": "다운로드쿠폰1",
  "contractId": 162749,
  "couponType": "DOWNLOAD",
  "startDate": "2025-12-26 00:00:00",  // ❌ 과거 시각
  "endDate": "2025-12-27 00:00:00",
  "userId": "14maker",
  "policies": [{
    "minimumPrice": 1,  // ❌ 10원 단위 위반
    "discount": 1000
  }]
}
// → 에러: "Please check the promotion period., policies[0] Invalid Amount Unit."
```

### 수정 후 (정상 동작 예상)

```json
{
  "title": "다운로드쿠폰1",
  "contractId": 162749,
  "couponType": "DOWNLOAD",
  "startDate": "2025-12-26 16:35:24",  // ✅ 현재시각(15:25) + 1시간 10분
  "endDate": "2025-12-27 00:00:00",     // ✅ 내일 자정 (유효기간 1일)
  "userId": "14maker",
  "policies": [{
    "minimumPrice": 10,  // ✅ 10원 단위
    "discount": 1000
  }]
}
// → 성공 예상
```

## 참조

- [ADR 021: Excel 9컬럼 구조](021-excel-9-column-structure.md) - 최소구매금액 컬럼 정의
- [다운로드쿠폰 API 문서](../coupang/download-coupon-api.md) - API 규격
- [DEV_LOG.md](../DEV_LOG.md) - 변경사항 기록

## 변경 이력

### 2025-12-26 15:25 - 시작일/종료일 계산 로직 수정

**변경 사항**:
1. **시작일**: `현재시각 + 10초` → `현재시각 + 1시간 10분`
   - 이유: +10초로는 API 에러 발생 확인
   - 1시간 10분으로 충분한 여유 확보

2. **종료일**: `현재시각 + N일` → `오늘 자정 + N일`
   - 이유: 원래 스펙은 자정 기준이었으나 구현 오류로 현재시각 기준으로 계산됨
   - 자정 기준으로 수정하여 원래 스펙대로 복원

**근거**: 실제 API 테스트 결과 및 원래 스펙 준수

