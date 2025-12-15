# ADR 002: 입력 정규화 (Input Normalization)

**상태**: 승인됨
**날짜**: 2024-12-16
**결정자**: 프로젝트 오너

## 컨텍스트

엑셀 파일을 일반 사용자(비개발자)가 작성합니다. 사용자는 다음과 같은 실수를 할 수 있습니다:

- 공백 포함: "즉시 할인", " RATE "
- 대소문자 혼용: "rate", "Rate"
- 구분자 혼용: "FIXED-WITH-QUANTITY" vs "FIXED_WITH_QUANTITY"
- 숫자에 단위 포함: "2일", "100개"
- 불필요한 문자: "(즉시할인)", "할인방식: RATE"

이러한 입력을 모두 거부하면 사용자 경험이 나빠지므로, 관대하게 파싱하는 전략이 필요합니다.

## 결정사항

### 정규화 규칙

각 컬럼별로 다음 규칙 적용:

#### 1. 쿠폰이름
```python
value = raw_value.strip()
```
- 앞뒤 공백만 제거
- 중간 공백은 유지 (쿠폰명의 일부일 수 있음)

#### 2. 쿠폰타입
```python
normalized = re.sub(r'\s+', '', raw_value)  # 모든 공백 제거
if '즉시할인' in normalized:
    coupon_type = '즉시할인'
elif '다운로드쿠폰' in normalized or '다운로드' in normalized:
    coupon_type = '다운로드쿠폰'
```
- 모든 공백 제거
- 부분 매칭으로 유연하게 인식

**예시**:
- "즉시 할인" → "즉시할인"
- "(즉시할인)" → "즉시할인"
- "다운로드" → "다운로드쿠폰"

#### 3. 쿠폰유효기간
```python
digits = re.sub(r'[^\d.]', '', raw_value)  # 숫자와 소수점만 추출
validity_days = int(float(digits))
```
- 숫자와 소수점만 추출
- float → int 변환 (소수점 입력도 허용)

**예시**:
- "2일" → 2
- "30 days" → 30
- "7.5" → 7

#### 4. 할인방식
```python
normalized = raw_value.upper().replace('-', '_')  # 대문자 + 언더스코어
if 'RATE' in normalized:
    discount_type = 'RATE'
elif 'FIXED' in normalized or 'QUANTITY' in normalized:
    discount_type = 'FIXED_WITH_QUANTITY'
elif 'PRICE' in normalized:
    discount_type = 'PRICE'
```
- 대문자 변환
- 하이픈을 언더스코어로 통일
- 부분 매칭으로 인식

**예시**:
- "rate" → "RATE"
- "FIXED-WITH-QUANTITY" → "FIXED_WITH_QUANTITY"
- "price discount" → "PRICE"

#### 5. 발급개수
```python
digits = re.sub(r'[^\d.]', '', raw_value)  # 숫자와 소수점만 추출
issue_count = int(float(digits))
```
- 숫자와 소수점만 추출
- float → int 변환

**예시**:
- "100개" → 100
- "1,000" → 1000
- "50 coupons" → 50

### 오류 처리

정규화 후에도 유효하지 않은 값은 명확한 오류 메시지와 함께 거부:

```python
if coupon_type not in ['즉시할인', '다운로드쿠폰']:
    raise ValueError(f"유효하지 않은 쿠폰타입: {raw_value}")
```

## 근거

1. **사용자 친화성**: 일반 사용자가 엑셀을 작성할 때 실수를 허용
2. **유지보수성**: 사용자 교육 비용 감소
3. **명확한 의도**: 부분 매칭으로 사용자의 의도를 파악
4. **안전성**: 정규화 후 최종 검증으로 잘못된 값 차단

## 대안

1. **엄격한 검증**: 모든 입력을 정확히 입력하도록 강제 (사용자 경험 나쁨, 거부됨)
2. **드롭다운 메뉴**: 엑셀에서 Data Validation 사용 (사용자가 템플릿을 지켜야 함, 유연성 부족)
3. **사전 변환 스크립트**: 별도 스크립트로 전처리 (불필요한 복잡도 증가)

## 영향

- issuer.py의 `_fetch_target_users()` 메서드에 정규화 로직 구현
- 정규화 실패 시 명확한 오류 메시지 제공
- 로그에 원본 값과 정규화된 값을 함께 기록하여 디버깅 지원
