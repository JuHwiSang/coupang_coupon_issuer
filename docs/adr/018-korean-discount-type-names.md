# ADR 018: 할인방식 한글 입력 지원

## Status
Accepted

## Context

현재 시스템은 엑셀 파일의 '할인방식' 컬럼에 영어 코드(`RATE`, `FIXED_WITH_QUANTITY`, `PRICE`)를 입력하도록 되어 있습니다. 그러나 실제 사용자는 비전문가이며, 영어 코드의 의미를 이해하기 어렵습니다.

### 문제점

1. **사용자 친화성 부족**: 비전문가는 영어 코드를 선호하지 않음
2. **의미 불명확**: `RATE`, `PRICE`, `FIXED_WITH_QUANTITY`의 의미를 매번 확인해야 함
3. **입력 오류 가능성**: 영어 스펠링 실수 발생 가능

### 사용자 요구사항

- 엑셀 작성 시 한글로 입력: `정률할인`, `수량별 정액할인`, `정액할인`
- 시스템 내부에서 자동으로 영어 코드로 변환
- 에러 메시지도 한글 할인방식 이름 사용

## Decision

엑셀 파일의 '할인방식' 컬럼에 한글 입력을 지원하고, 내부적으로 영어 코드로 변환합니다.

### 매핑 테이블

| 한글 (엑셀 입력) | 영어 (내부 코드) | 의미 |
|---|---|---|
| 정률할인 | RATE | 정률 할인 (%) |
| 수량별 정액할인 | FIXED_WITH_QUANTITY | 수량별 정액 할인 |
| 정액할인 | PRICE | 정액 할인 (원) |

### 구현 방법

**1. `issuer.py`에 매핑 상수 추가**:
```python
# 할인방식 한글-영어 매핑
DISCOUNT_TYPE_KR_TO_EN = {
    '정률할인': 'RATE',
    '수량별 정액할인': 'FIXED_WITH_QUANTITY',
    '정액할인': 'PRICE',
}

DISCOUNT_TYPE_EN_TO_KR = {
    'RATE': '정률할인',
    'FIXED_WITH_QUANTITY': '수량별 정액할인',
    'PRICE': '정액할인',
}
```

**2. 파싱 로직 변경** (`_fetch_coupons_from_excel()` 메서드):
```python
# 4. 할인방식: 한글 입력 지원
discount_type_raw = str(row[col_indices['할인방식']]).strip()

# 한글 매핑 시도
if discount_type_raw in DISCOUNT_TYPE_KR_TO_EN:
    discount_type = DISCOUNT_TYPE_KR_TO_EN[discount_type_raw]
else:
    raise ValueError(
        f"행 {row_idx}: 잘못된 할인방식 '{discount_type_raw}' "
        f"(정률할인/수량별 정액할인/정액할인만 가능)"
    )
```

**3. 검증 에러 메시지 한글화** (ADR 017 형식 유지):
```python
# 다운로드쿠폰
raise ValueError(f"행 {row_idx}: 다운로드쿠폰 정률할인은 1~99 사이여야 합니다 (현재: {discount})")
raise ValueError(f"행 {row_idx}: 다운로드쿠폰 정액할인은 최소 10원 이상이어야 합니다 (현재: {discount})")
raise ValueError(f"행 {row_idx}: 다운로드쿠폰 정액할인은 10원 단위여야 합니다 (현재: {discount})")

# 즉시할인쿠폰
raise ValueError(f"행 {row_idx}: 즉시할인쿠폰 정률할인은 1~100 사이여야 합니다 (현재: {discount})")
raise ValueError(f"행 {row_idx}: 즉시할인쿠폰 정액할인은 1원 이상이어야 합니다 (현재: {discount})")
raise ValueError(f"행 {row_idx}: 즉시할인쿠폰 수량별 정액할인은 1 이상이어야 합니다 (현재: {discount})")
```

## Consequences

### Positive

- ✅ **사용자 친화성 향상**: 비전문가가 엑셀 작성 시 직관적으로 이해 가능
- ✅ **입력 오류 감소**: 한글 단어로 명확하게 표현
- ✅ **에러 메시지 명확성**: 한글 할인방식 이름으로 에러 표시
- ✅ **일관성**: ADR 017의 쿠폰타입별 검증 구조 유지

### Negative

- ⚠️ **Breaking Change**: 기존 엑셀 파일을 수정해야 함
- ⚠️ **영어 입력 지원 중단**: 이전에 사용하던 영어 코드는 더 이상 작동하지 않음

### Breaking Changes

**기존 엑셀 파일 업데이트 필요**:

| Before (영어) | After (한글) |
|---|---|
| RATE | 정률할인 |
| FIXED_WITH_QUANTITY | 수량별 정액할인 |
| PRICE | 정액할인 |

**마이그레이션 방법**:
1. 엑셀 파일 열기
2. '할인방식' 컬럼(Column D)의 값을 한글로 변경
3. 저장

또는 `scripts/generate_example.py`를 실행하여 새 템플릿 생성:
```bash
uv run python scripts/generate_example.py
```

## Implementation

### Code Changes

**파일**: `src/coupang_coupon_issuer/issuer.py`
- 라인 20-31: 한글-영어 매핑 상수 추가
- 라인 441-451: 할인방식 파싱 로직 변경
- 라인 494, 498, 500, 506, 510, 514: 검증 에러 메시지 한글화

### Script Changes

**파일**: `scripts/generate_example.py`
- 모든 예제 생성 함수에서 할인방식을 한글로 변경

### Example Files

모든 예제 파일 재생성:
- `examples/basic.xlsx`
- `examples/comprehensive.xlsx`
- `examples/edge_cases.xlsx`

### Test Changes

**파일**: `tests/unit/test_issuer.py`
- 50+ 테스트 케이스의 할인방식 데이터를 한글로 변경
- 에러 메시지 assertion 업데이트
- `test_normalize_discount_method_uppercase()`: 테스트 이름 및 로직 변경

## Validation

### Automated Tests
```bash
uv run pytest tests/unit/test_issuer.py -v
```

**Result**: ✅ 33 passed, 1 warning

모든 유닛 테스트 통과 확인.

### Manual Verification

1. 예제 파일 확인:
```bash
uv run python scripts/generate_example.py
# examples/ 디렉토리의 파일들이 한글 할인방식을 사용하는지 확인
```

2. 검증 명령어 실행:
```bash
python main.py verify examples/
# 출력 결과에서 할인방식이 한글로 표시되는지 확인
```

## Alternatives Considered

### Alternative 1: 영어와 한글 모두 지원

**장점**:
- 기존 엑셀 파일 호환성 유지
- 영어 선호 사용자 지원

**단점**:
- 구현 복잡도 증가
- 어떤 형식을 사용해야 하는지 혼란
- 에러 메시지에서 어떤 형식으로 표시할지 결정 필요

**결론**: 사용자가 비전문가이므로 한글만 지원하는 것이 더 명확함

### Alternative 2: 설정 파일로 언어 선택

**장점**:
- 사용자가 선호하는 언어 선택 가능

**단점**:
- 오버 엔지니어링
- 현재 사용자는 한국인만 대상

**결론**: 불필요한 복잡성 추가, 한글만 지원으로 충분

## References

- [ADR 002: 입력 정규화](002-input-normalization.md) - 사용자 입력 오류 용인 로직
- [ADR 009: 엑셀 6컬럼 구조](009-excel-6-column-structure.md) - 엑셀 입력 구조
- [ADR 015: 옵션ID 컬럼 추가](015-option-id-column.md) - 7컬럼 엑셀 구조
- [ADR 017: 쿠폰 타입별 할인 검증 규칙 분리](017-coupon-type-specific-validation.md) - 쿠폰타입별 검증

## History

- 2024-12-23: 초안 작성 및 승인
- 2024-12-23: 구현 완료 및 테스트 통과
