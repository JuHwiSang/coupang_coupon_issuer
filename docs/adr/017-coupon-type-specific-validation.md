# ADR 017: 쿠폰 타입별 할인 검증 규칙 분리

## Status
Accepted

## Context

현재 시스템은 다운로드 쿠폰과 즉시할인 쿠폰의 discount 검증을 동일하게 처리하고 있었으나, Coupang API 문서를 재검토한 결과 두 쿠폰 타입의 요구사항이 다른 것으로 확인되었습니다.

### API 요구사항 차이

**다운로드 쿠폰** (`download-coupon-api.md:60`):
- **RATE**: 1~99 정수입력
- **PRICE**: 10원 단위 금액

**즉시할인 쿠폰** (`instant-coupon-api.md:116`):
- **RATE**: 1~100 (에러 메시지: "정률은 1~100, 정액은 1이상")
- **PRICE**: 1 이상 (에러 메시지: "정률은 1~100, 정액은 1이상")
- **FIXED_WITH_QUANTITY**: 1 이상

### 문제점

기존 구현은 모든 쿠폰 타입에 대해 동일한 검증을 적용:
- RATE: 1~99 범위
- PRICE: 10원 이상, 10원 단위
- FIXED_WITH_QUANTITY: 1 이상

이로 인해 즉시할인 쿠폰에서 유효한 값들(RATE 100%, PRICE 15원 등)이 거부되는 문제가 있었습니다.

## Decision

`issuer.py`의 `_fetch_coupons_from_excel()` 메서드에서 할인 검증 로직을 쿠폰 타입별로 분리합니다.

### 검증 로직 구조

```python
if coupon_type == '다운로드쿠폰':
    # 다운로드 쿠폰 검증
    if discount_type == 'RATE':
        # 1~99 (100% 불가)
        if not (1 <= discount <= 99):
            raise ValueError(...)
    elif discount_type == 'PRICE':
        # 10원 단위, 최소 10원
        if discount < 10 or discount % 10 != 0:
            raise ValueError(...)
            
elif coupon_type == '즉시할인':
    # 즉시할인 쿠폰 검증
    if discount_type == 'RATE':
        # 1~100 (100% 허용)
        if not (1 <= discount <= 100):
            raise ValueError(...)
    elif discount_type == 'PRICE':
        # 1원 이상 (단위 제약 없음)
        if discount < 1:
            raise ValueError(...)
    elif discount_type == 'FIXED_WITH_QUANTITY':
        # 1 이상
        if discount < 1:
            raise ValueError(...)
```

### 에러 메시지 변경

쿠폰 타입을 에러 메시지에 포함하여 명확성을 높입니다:

**변경 전**:
```
행 X: RATE 할인율은 1~99 사이여야 합니다
```

**변경 후**:
```
행 X: 다운로드쿠폰 RATE 할인율은 1~99 사이여야 합니다
행 X: 즉시할인쿠폰 RATE 할인율은 1~100 사이여야 합니다
```

## Consequences

### Positive
- ✅ API 요구사항과 정확히 일치
- ✅ 즉시할인 쿠폰에서 100% 할인 사용 가능
- ✅ 즉시할인 쿠폰 PRICE 타입의 유연성 향상 (1원 단위 할인 가능)
- ✅ 에러 메시지에 쿠폰 타입 명시로 사용자 이해도 향상

### Negative
- ⚠️ 기존 검증을 통과하지 못했던 값들이 허용됨 (Breaking Change)
- ⚠️ 쿠폰 타입별로 검증 로직이 분리되어 코드 복잡도 증가

### Breaking Changes

1. **즉시할인 RATE 100% 허용**
   - 기존: 100% 입력 시 에러 `"RATE 할인율은 1~99 사이여야 합니다"`
   - 변경 후: 100% 허용

2. **즉시할인 PRICE 1원 단위 허용**
   - 기존: 15원, 123원 등 입력 시 에러 `"PRICE 할인금액은 10원 단위여야 합니다"`
   - 변경 후: 1원 이상이면 모두 허용

## Implementation

### Code Changes

**파일**: `src/coupang_coupon_issuer/issuer.py`
**위치**: 라인 475-489
**변경**: 할인방식별 검증 → 쿠폰타입+할인방식별 검증

### Test Changes

**파일**: `tests/unit/test_issuer.py`
**추가 테스트**:
- `test_fetch_instant_coupon_rate_100_allowed`: 즉시할인 RATE 100% 허용
- `test_fetch_download_coupon_rate_100_rejected`: 다운로드 RATE 100% 거부
- `test_fetch_instant_coupon_price_non_ten_units`: 즉시할인 PRICE 1원 단위 허용
- `test_fetch_download_coupon_price_requires_ten_units`: 다운로드 PRICE 10원 단위 필수
- `test_fetch_instant_coupon_price_minimum`: 즉시할인 PRICE 최소 1원
- `test_fetch_download_coupon_price_minimum`: 다운로드 PRICE 최소 10원

### Documentation Updates

1. **ADR 017**: 본 문서 작성
2. **CLAUDE.md**: ADR 목록에 ADR 017 추가
3. **DEV_LOG.md**: 쿠폰 타입별 검증 규칙 섹션 추가
4. **instant-coupon-api.md**: discount 파라미터 설명 명확화
5. **download-coupon-api.md**: discount 파라미터 설명 명확화

## Validation

### Unit Tests
```bash
uv run pytest tests/unit/test_issuer.py -v -k "rate\|price\|discount"
```

### Manual Testing
1. 엑셀 파일 생성 (즉시할인 RATE 100%)
2. `python main.py verify .` 실행 → 성공 확인
3. 엑셀 파일 생성 (즉시할인 PRICE 15원)
4. `python main.py verify .` 실행 → 성공 확인
5. 엑셀 파일 생성 (다운로드 RATE 100%)
6. `python main.py verify .` 실행 → 실패 확인

## References

- [다운로드 쿠폰 API 문서](../coupang/download-coupon-api.md)
- [즉시할인 쿠폰 API 문서](../coupang/instant-coupon-api.md)
- [ADR 002: 입력 정규화](002-input-normalization.md)
- [ADR 015: 옵션ID 컬럼 추가](015-option-id-column.md)

## History

- 2024-12-23: 초안 작성 및 승인
- 2024-12-23: 구현 완료
