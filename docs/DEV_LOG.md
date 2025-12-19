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

### 테스트 규칙
- **Python 실행**: `uv run python` 또는 `uv run pytest` 사용
- **테스트 실행**: `uv run pytest tests/unit -v`
- **커버리지**: `uv run pytest --cov=src/coupang_coupon_issuer`
- **플랫폼 스킵**: Windows 전용 스킵은 `pytestmark = pytest.mark.skipif(os.name == 'nt', ...)` 사용
- **Mock 라이브러리**:
  - HTTP API: `requests-mock`
  - 시간: `freezegun`
  - 일반: `pytest-mock` (mocker fixture)
- **Fixture 파일**: `tests/fixtures/` 디렉토리에 테스트용 엑셀 파일 관리
- **테스트 마커**:
  - `@pytest.mark.unit`: 유닛 테스트
  - `@pytest.mark.integration`: 통합 테스트 (Docker 필요)
  - `@pytest.mark.slow`: 느린 테스트 (> 1초)

### 엑셀 구조 변경: 5컬럼 → 6컬럼 (ADR 009)

**변경 이유**: '발급개수' 컬럼이 할인금액/비율과 쿠폰 발급개수를 동시에 표현하여 의미적 혼란 발생

**Before (5컬럼)**:
- 쿠폰이름 | 쿠폰타입 | 쿠폰유효기간 | 할인방식 | **발급개수** (할인 + 발급개수 혼재)

**After (6컬럼)**:
- 쿠폰이름 | 쿠폰타입 | 쿠폰유효기간 | 할인방식 | **할인금액/비율** | **발급개수**

**Column E (할인금액/비율)** - 필수:
- RATE: 1~99 (퍼센트)
- PRICE: ≥10, 10원 단위 (원화)
- FIXED_WITH_QUANTITY: ≥1 (할인방식에 따라 퍼센트 또는 원화)

**Column F (발급개수)** - 선택적:
- 즉시할인: 무시됨 (비어있어도 OK)
- 다운로드쿠폰: 비어있으면 기본값 1 사용 (`COUPON_DEFAULT_ISSUE_COUNT`)
- API `maximumPerDaily` 파라미터로 사용됨

**FIXED_WITH_QUANTITY 의미**:
- "n개 상품 구매 시 n번 할인 적용" 쿠폰
- Column E는 할인금액 또는 할인율 (할인방식에 따라 다름)

**검증 규칙 업데이트**:
- **엑셀 정규화 규칙** 업데이트:
  - **할인금액/비율**: `re.sub(r'[^\d.]', '', value)` → `float()` → `int()` (숫자만 추출)
  - **발급개수**:
    - 즉시할인: 검증 안함 (무시)
    - 다운로드쿠폰: 비어있으면 기본값 1, 있으면 `≥1` 검증

**config.py 추가**:
- `COUPON_DEFAULT_ISSUE_COUNT = 1` (다운로드쿠폰 발급개수 기본값)

**마이그레이션**: 불필요 (프로젝트 미배포)

---

## 2024-12-19

### 통합 테스트 추가 (testcontainers)

- **목적**: service.py의 Linux/systemd 의존 코드 테스트
- **환경**: Ubuntu 22.04 + systemd in Docker container
- **라이브러리**: testcontainers-python
- **실행 환경**: Docker Desktop (WSL2 backend on Windows)

### 통합 테스트 구조

```
tests/integration/
├── conftest.py               # testcontainers 인프라 (250 라인)
├── test_service_install.py   # 설치 프로세스 (14개 테스트)
├── test_service_uninstall.py # 제거 프로세스 (18개 테스트)
└── test_end_to_end.py        # E2E 워크플로우 (3개 테스트)
```

### testcontainers 핵심 픽스처

1. **systemd_container** (session scope)
   - Ubuntu 22.04 컨테이너 생성
   - privileged=True로 systemd 활성화
   - 프로젝트 코드 /app에 마운트
   - Python 3, pip, sudo 자동 설치
   - 5초 systemd 초기화 대기

2. **clean_container** (function scope)
   - 각 테스트 전 서비스/파일 정리
   - systemctl stop/disable
   - /opt, /etc, /usr/local/bin 정리
   - systemctl daemon-reload

3. **container_exec**
   - 컨테이너 내 명령 실행 헬퍼
   - exit code와 stdout 반환
   - 에러 시 자동 예외 발생

4. **installed_service**
   - 서비스 설치 상태 제공
   - credentials, 경로 정보 반환

5. **file_permission_checker**
   - stat로 파일 권한 확인
   - mode, owner, group 반환

6. **verify_systemd_unit**
   - systemctl show로 서비스 속성 검증

### 통합 테스트 실행 방법

```bash
# Docker Desktop 실행 후
uv run pytest tests/integration -v -m integration
```

### 통합 테스트 커버리지 목표

- **service.py**: 9% → 90%+ (180 라인)
- **전체**: 70% → 85%+

### 유닛 테스트 개선

- **issuer.py**: 88% → 94% (+6%)
- **테스트 추가**: 12개 엣지 케이스 테스트
  - 빈 쿠폰 리스트 처리
  - 예외 전파 검증
  - 입력 검증 (잘못된 타입, 할인방식, 발급개수 등)

### 테스트 실행 통계 (2024-12-19)

- **유닛 테스트**: 109개 (97개 → 109개, +12개)
- **통합 테스트**: 35개 (신규)
- **전체**: 144개
- **Windows 통과율**: 97/109 (89%, service.py 12개 스킵)
