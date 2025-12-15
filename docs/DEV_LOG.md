# 개발 로그 (DEV_LOG)

작은 결정사항, 관례, 변경사항을 기록합니다.

---

## 2024-12-16

### 로깅 규칙
- journalctl 호환을 위해 로그에 이모지 사용 금지 (텍스트만)
- 타임스탬프는 `datetime.now().strftime('%Y-%m-%d %H:%M:%S')` 형식 사용
- 모든 로그는 `flush=True` 옵션 사용 (실시간 출력)

### 예외 처리 관례
- 모든 예외는 로깅 후 상위로 전파 (catch-and-suppress 금지)
- 네트워크 오류는 `requests.RequestException` 계층 사용
- API 오류는 `ValueError`로 변환하여 전파

### 엑셀 입력 정규화 규칙
- **쿠폰이름**: `.strip()` 만 적용
- **쿠폰타입**: `re.sub(r'\s+', '', value)` → "즉시할인" 또는 "다운로드쿠폰" 포함 여부 체크
- **쿠폰유효기간**: `re.sub(r'[^\d.]', '', value)` → `float()` → `int()` (숫자만 추출)
- **할인방식**: `.upper().replace('-', '_')` → "RATE", "FIXED_WITH_QUANTITY", "PRICE" 포함 여부 체크
- **발급개수**: `re.sub(r'[^\d.]', '', value)` → `float()` → `int()` (숫자만 추출)

### 타입 체커 관련
- openpyxl의 None 타입 이슈는 `# type: ignore` 주석으로 해결
- 명시적 None 체크를 추가하여 런타임 안정성 확보

### systemd 서비스 설정
- 서비스명: `coupang_coupon_issuer`
- 설정 파일 위치: `/etc/coupang_coupon_issuer/credentials.json`
- 파일 권한: `0o600` (root만 읽기 가능)
- 엑셀 파일 위치: issuer.py와 동일 디렉토리
- 결과 파일 위치: `results/` 서브디렉토리

### 코딩 스타일
- Python 3.10+ 타입 힌트 사용 (`tuple[str, str]` 형식)
- docstring은 Google 스타일
- 패키지 의존성: `requests`, `openpyxl`만 사용 (stdlib 외)

### API 파라미터 정책
- **필수 파라미터만 전송**: 비필수 파라미터는 API 요청에 포함하지 않음
- 제외한 파라미터:
  - 즉시할인쿠폰: `wowExclusive` (기본값 false)
  - 다운로드쿠폰: `minimumPrice` (최소 구매금액 제한 없음)
- **최대할인금액**: 100,000원 고정 (충분히 큰 값으로 대부분 시나리오 커버)
