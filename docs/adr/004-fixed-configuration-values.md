# ADR 004: 고정 설정값

**상태**: 승인됨  
**날짜**: 2024-12-16  
**결정자**: 프로젝트 오너

## 컨텍스트

쿠폰 발급 시 일부 파라미터는 모든 쿠폰에 대해 동일하게 사용됩니다. 이러한 값들을 매번 입력받는 것은 비효율적이고 오류 발생 가능성이 높습니다.

## 결정사항

### 고정값 목록

다음 값들은 config.py에 상수로 정의하고 코드에서 직접 사용:

```python
# 쿠폰 발급 고정값
COUPON_MAX_DISCOUNT = 100000    # 최대 할인금액 (10만원)
COUPON_CONTRACT_ID = -1         # 계약서 ID 고정값
```

**참고**:
- 최대할인금액 100,000원: 충분히 큰 값으로 설정하여 대부분의 할인 시나리오 커버
- 비필수 파라미터(minimumPrice, wowExclusive 등)는 API 요청에 포함하지 않음

### 동적 계산값

일부 값은 실행 시점에 자동 계산:

- **유효 시작일**: 실행일 0시 0분 0초
  ```python
  start_datetime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
  start_at = start_datetime.strftime('%Y-%m-%d %H:%M:%S')
  ```

- **유효 종료일**: 시작일 + 쿠폰유효기간(일)
  ```python
  end_datetime = start_datetime + timedelta(days=validity_days)
  end_at = end_datetime.strftime('%Y-%m-%d %H:%M:%S')
  ```

### 설치 시 수집 항목 (credentials.json에 저장)

다음 4개 항목만 설치 시 수집하여 암호화 저장:

1. **access_key**: Coupang API Access Key
2. **secret_key**: Coupang API Secret Key
3. **user_id**: WING 사용자 ID (다운로드쿠폰용)
4. **vendor_id**: 판매자 ID (즉시할인쿠폰용)

**중요**: `contract_id`는 설치 시 수집하지 않음 (고정값 -1 사용)

## 근거

1. **단순성**: 매번 변경되지 않는 값은 하드코딩하여 복잡도 감소
2. **일관성**: 모든 쿠폰이 동일한 정책 적용
3. **오류 방지**: 잘못된 contract_id 입력 방지
4. **자동화 친화적**: 매일 0시 실행 시 자동으로 올바른 시작일 계산

## 대안

1. **모든 값을 설치 시 수집**: contract_id 등을 사용자에게 물어봄 (오류 발생 가능성 높음, 강하게 거부됨)
2. **설정 파일로 분리**: config.ini 등 별도 파일 (불필요한 복잡도, 거부됨)
3. **환경 변수 사용**: 12-factor app 방식 (systemd 환경에서 비효율적)

## 영향

- config.py에 고정값 상수 추가
- service.py의 설치 프로세스에서 4개 항목만 수집
- issuer.py에서 고정값을 직접 참조하여 사용
- CredentialManager는 4개 필드만 저장/로드
