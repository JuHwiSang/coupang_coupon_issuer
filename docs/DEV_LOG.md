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

---

## 2024-12-17

### CLI 명령어 구조 (ADR 008)
- **5개 명령어**: apply, issue, serve, install, uninstall
- **전역 명령어**: `coupang_coupon_issuer` (심볼릭 링크)
- **명령어 역할**:
  - `apply <excel_file>`: 엑셀 검증 및 `/etc`로 복사
  - `issue`: 단발성 쿠폰 발급 (테스트용)
  - `serve`: 스케줄러 실행 (systemd용, 기존 `run` 대체)
  - `install`: 서비스 설치 (4개 파라미터 필수)
  - `uninstall`: 서비스 제거

### 파일 경로 규칙
- **실행 파일**: `/opt/coupang_coupon_issuer/main.py`
- **소스 코드**: `/opt/coupang_coupon_issuer/src/`
- **심볼릭 링크**: `/usr/local/bin/coupang_coupon_issuer`
- **엑셀 파일**: `/etc/coupang_coupon_issuer/coupons.xlsx` (고정 경로)
- **API 키**: `/etc/coupang_coupon_issuer/credentials.json`
- **파일 권한**: 모두 `0o600` (root만 읽기 가능)

### 엑셀 검증 규칙 강화
- **RATE 할인율**: 1~99 범위 체크
- **PRICE 할인금액**:
  - 최소 10원 이상
  - 10원 단위 체크 (10, 20, 30, ... 만 허용)
- **검증 시점**:
  - `apply` 명령어로 사전 검증 (필수)
  - `issue` 실행 시 issuer.py에서 재검증

### 로그 출력 규칙
- **엑셀 결과 파일 제거**: `results/` 디렉토리 미사용
- **로그로만 출력**: journalctl로 모든 이력 추적
- **상세 결과 형식**:
  ```
  [2024-12-17 12:00:00] 쿠폰 발급 완료! (성공: 3, 실패: 1)
  [2024-12-17 12:00:00] [OK] 쿠폰명: 성공 메시지
  [2024-12-17 12:00:00] [FAIL] 쿠폰명: 실패 메시지
  ```

### install 파라미터
- **4개 필수**: `--access-key`, `--secret-key`, `--user-id`, `--vendor-id`
- 모든 파라미터 누락 시 에러 메시지 출력 후 종료
- credentials.json에 4개 필드 모두 저장

### Docker 테스트 환경
- **이미지**: Ubuntu 22.04
- **필수 설정**:
  - `privileged: true` (systemd 필수)
  - cgroup 마운트: `/sys/fs/cgroup:/sys/fs/cgroup:ro`
  - 명령어: `/sbin/init`
- **부팅 대기**: systemd 초기화를 위해 약 5초 대기 필요
- **사용 목적**: Windows 개발 환경에서 Linux systemd 테스트
