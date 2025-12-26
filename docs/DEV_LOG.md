# 개발 로그 (DEV_LOG)

작은 결정사항, 관례, 변경사항을 기록합니다.

---

## 2025-12-26 (오후)

### 다운로드쿠폰 API 에러 수정 (ADR 022)

**문제**: 다운로드쿠폰 발급 시 두 가지 API 에러 발생
1. "Please check the promotion period." - 시작일이 과거 시각
2. "policies[0] Invalid Amount Unit." - 최소구매금액 10원 단위 위반

**해결**:
1. **시작일 계산 로직 변경** (`issuer.py:206-224`):
   - 즉시할인: 오늘 0시 (기존 유지)
   - 다운로드쿠폰: 현재시각 + 10초 (신규)
   - 근거: API 처리 시간 고려, 과거 시각 거부 방지

2. **최소구매금액 기본값 변경** (`reader.py:144`):
   - 기존: 1원
   - 변경: 10원
   - 근거: 다운로드쿠폰 API는 10원 단위만 허용 (최소 10원)

**참조**: [ADR 022](adr/022-download-coupon-timing-fix.md)

---

## 2025-12-26

### Excel 구조 확장: 7컬럼 → 9컬럼 (ADR 021)

**목적**: 최대할인금액과 최소구매금액을 하드코딩에서 Excel 설정으로 이동

**변경사항**:
- **최대할인금액** (Column G): 정률할인 시 최대 할인 금액 (필수, 모든 쿠폰)
  - 기존: `config.py`의 `COUPON_MAX_DISCOUNT = 100000` 상수
  - 변경: Excel에서 쿠폰별로 지정
  - 검증: 1원 이상 필수
- **최소구매금액** (Column F): 쿠폰 사용 최소 구매 조건 (다운로드쿠폰 전용, 선택적)
  - 기존: `issuer.py`의 `minimumPrice: 0` 하드코딩
  - 변경: Excel에서 지정, 비어있으면 기본값 1원
  - 검증: 1원 이상, 즉시할인쿠폰은 무시

**새로운 컬럼 순서** (9컬럼):
1. 쿠폰이름
2. 쿠폰타입
3. 쿠폰유효기간
4. 할인방식
5. 할인금액/비율
6. **최소구매금액** (신규, 다운로드쿠폰 전용)
7. **최대할인금액** (신규)
8. 발급개수 (다운로드쿠폰 전용)
9. 옵션ID

**config.py 변경**:
```python
# 제거
# COUPON_MAX_DISCOUNT = 100000

# 추가
COUPON_MIN_PURCHASE_PRICE = 1  # 최소 구매금액 기본값
```

**reader.py 변경**:
- 9컬럼 헤더 검증
- 최소구매금액 파싱 로직 추가 (다운로드쿠폰만, 기본값 1)
- 최대할인금액 파싱 로직 추가 (필수, 1 이상)
- 반환 딕셔너리에 `min_purchase_price`, `max_discount_price` 추가

**issuer.py 변경**:
- `COUPON_MAX_DISCOUNT` import 제거
- `_issue_instant_coupon`: `max_discount_price` 파라미터 추가
- `_issue_download_coupon`: `min_purchase_price`, `max_discount_price` 파라미터 추가
- API 호출 시 Excel 값 사용

**main.py 변경**:
- `cmd_verify`: 최소구매금액, 최대할인금액 컬럼 표시 추가
- 헤더: 9개 → 11개 (No, 쿠폰이름, 쿠폰타입, 유효기간, 할인방식, 할인금액, 할인비율, **최소구매**, **최대할인**, 발급개수, 총 예산)

**generate_example.py 변경**:
- 9컬럼 헤더 생성
- 최소구매금액, 최대할인금액 컬럼 주석 추가
  - 다운로드쿠폰 전용 컬럼에 "⚠ 이 컬럼은 다운로드쿠폰일 때만 사용합니다" 명시
- 예제 데이터 업데이트 (basic.xlsx, comprehensive.xlsx, edge_cases.xlsx)

**ADR 업데이트**:
- ADR 021 작성: 9컬럼 구조 결정 문서
- ADR 004 업데이트: `COUPON_MAX_DISCOUNT` 제거 기록
- ADR 015 수정: Deprecated 표시 정정 (ADR 009만 표시)

**참조**: [ADR 021](adr/021-excel-9-column-structure.md)

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

## 2024-12-22

### install 명령어 대화형 입력
- **동작**: `--access-key`, `--secret-key`, `--user-id`, `--vendor-id` 옵션 미지정 시 `input()`으로 대화형 입력받음
- **목적**: 명령줄 히스토리에 인증 정보 노출 방지
- **제한사항**:
  - Non-interactive 환경 (파이프, 백그라운드 실행)에서는 빈 입력으로 성공할 수 있음
  - 완전 자동화 환경에서는 4개 옵션 모두 명시 권장
- **예시**:
  ```bash
  # 대화형 (권장)
  python3 main.py install ~/my-coupons

  # 스크립트/자동화 (4개 옵션 필수)
  python3 main.py install ~/my-coupons \
    --access-key KEY --secret-key SECRET \
    --user-id USER --vendor-id VENDOR
  ```

### 인증 정보 전달 방식 명확화
- **문제**: issuer.py의 `__init__`에서 `or os.environ.get()` 패턴 사용 - 불명확한 fallback 동작
- **해결**: 환경 변수 fallback 완전 제거, 모든 인증 정보는 명시적으로 전달
- **변경 사항**:
  1. **issuer.py**: 환경 변수 fallback 제거, 모든 파라미터 필수
     - `access_key: Optional[str] = None` (필수 검증)
     - `or os.environ.get()` 패턴 삭제
     - `import os` 제거
  2. **main.py**: config.json 로드 후 직접 전달
     - `ConfigManager.load_credentials(base_dir)` 호출
     - `CouponIssuer(base_dir, access_key, secret_key, user_id, vendor_id)` 생성
     - ~~환경 변수 주입 (`load_credentials_to_env()`) 제거~~
- **이유**: 명시적 전달이 더 명확하고 추적 가능함, 환경 변수는 불필요한 간접성 추가
- **참조**: config.py의 `load_credentials_to_env()` 메서드는 레거시로 남아있지만 사용하지 않음

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

### 파일 경로 규칙 (2024-12-20 업데이트: XDG 표준 적용)
- **실행 파일**: `/opt/coupang_coupon_issuer/main.py`
- **소스 코드**: `/opt/coupang_coupon_issuer/src/`
- **심볼릭 링크**: `/usr/local/bin/coupang_coupon_issuer`
- **설정 파일** (XDG_CONFIG_HOME): `~/.config/coupang_coupon_issuer/`
  - `credentials.json` - API 키
  - `coupons.xlsx` - 쿠폰 정의
- **로그 파일** (XDG_STATE_HOME): `~/.local/state/coupang_coupon_issuer/`
  - `issuer.log` - 실행 로그
- **파일 권한**: 설정 파일 `0o600` (사용자만 읽기/쓰기), 로그 `0o644`
- **환경 변수 override**: `XDG_CONFIG_HOME`, `XDG_STATE_HOME` 지원

### 엑셀 검증 규칙 강화
- **RATE 할인율**: 쿠폰 타입별로 범위가 다름 (ADR 017)
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
- RATE: 다운로드쿠폰 1~99, 즉시할인쿠폰 1~100 (퍼센트)
- PRICE: 다운로드쿠폰 ≥10 (10원 단위), 즉시할인쿠폰 ≥1 (원화)
- FIXED_WITH_QUANTITY: ≥1 (즉시할인쿠폰 전용, 할인방식에 따라 퍼센트 또는 원화)

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

- **목적**: service.py의 Linux/cron 의존 코드 테스트
- **환경**: Ubuntu 22.04 + cron in Docker container
- **라이브러리**: testcontainers-python
- **실행 환경**: Docker Desktop (WSL2 backend on Windows)

### 통합 테스트 구조

```
tests/integration/
├── conftest.py               # testcontainers 인프라 (207 라인)
├── test_service_install.py   # 설치 프로세스 (11개 테스트)
├── test_service_uninstall.py # 제거 프로세스 (6개 테스트)
└── test_end_to_end.py        # E2E 워크플로우 (3개 테스트)
```

### testcontainers 핵심 픽스처 (Cron 기반)

1. **cron_container** (session scope)
   - Ubuntu 22.04 컨테이너 생성
   - cron, Python 3, pip 자동 설치
   - 프로젝트 코드 /app에 마운트
   - privileged mode 불필요 (systemd보다 단순)

2. **clean_container** (function scope)
   - 각 테스트 전 서비스/파일 정리
   - crontab -r (cron job 제거)
   - /opt, /etc, /usr/local/bin, ~/.local/state 정리

3. **container_exec**
   - 컨테이너 내 명령 실행 헬퍼
   - `["bash", "-c", "command"]` 형식으로 쉘 기능 지원
   - exit code와 stdout 반환
   - 에러 시 자동 예외 발생

4. **installed_service**
   - 서비스 설치 상태 제공
   - credentials, 경로 정보 반환

5. **test_excel_file**
   - 테스트용 엑셀 파일 생성
   - 6컬럼 구조 (ADR 009)

### 통합 테스트 실행 방법

```bash
# Docker Desktop 실행 후
uv run pytest tests/integration -v -m integration

# 전체 테스트 (유닛 + 통합)
uv run pytest -v
```

### 통합 테스트 결과 (2024-12-19)

- **테스트 개수**: 20개 (100% 통과)
- **실행 시간**: 103초
- **주요 수정사항**:
  - Docker exec를 `["bash", "-c", "command"]` 형식으로 수정 (쉘 기능 지원)
  - service.py 경로 계산 로직 수정 (`project_root` 명확화)

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

### Crontab 마이그레이션 (ADR 010)

**배경**: systemd 기반 통합 테스트가 testcontainers에서 불안정하여 실제 환경 동작 확신 불가. 단순화 필요.

**주요 변경사항**:
- **제거**: scheduler.py (108 라인), serve 명령어
- **대체**: SystemdService → CrontabService (221 → 419 라인)
- **로그 변경**: journalctl → `~/.local/state/coupang_coupon_issuer/issuer.log`
- **스케줄링**: 30초 폴링 루프 → cron 1분 정밀도 (00:00 정확히 실행)

### Cron Job 관리 규칙

**마커 기반 식별**:
- 마커: `# coupang_coupon_issuer_job`
- cron job 추가/제거 시 마커로만 판단
- 복잡한 조건 사용 금지 (마커 존재 여부만 체크)

**Cron Job 형식**:
```bash
0 0 * * * /usr/bin/python3 /opt/coupang_coupon_issuer/main.py issue >> ~/.local/state/coupang_coupon_issuer/issuer.log 2>&1  # coupang_coupon_issuer_job
```

**Crontab 조작**:
- 읽기: `subprocess.run(["crontab", "-l"], ...)`
- 쓰기: `subprocess.run(["crontab", "-"], input=new_crontab, ...)`
- 업데이트: 기존 job 제거 후 새 job 추가
- 제거: 마커 포함 라인만 필터링

### 플랫폼별 Cron 설치

**자동 감지 및 설치**:
- Ubuntu/Debian: `apt-get install cron`
- RHEL/CentOS 8+: `dnf install cronie`
- RHEL/CentOS 7: `yum install cronie`
- 미지원 시스템: 에러 메시지 + 수동 설치 안내

**Cron 활성화**:
- systemctl 우선 시도 (cron, crond 두 서비스명 모두 시도)
- 없으면 service 명령어 사용
- 실패 시 경고만 출력 (치명적이지 않음)

### 로그 디렉토리 규칙

**사용자 수준 로그**:
- 경로: `~/.local/state/coupang_coupon_issuer/` (XDG Base Directory 표준)
- 파일: `issuer.log`
- 권한: 0o755 (디렉토리), 0o644 (파일)
- sudo 불필요 (사용자가 직접 tail -f로 확인 가능)

### 서비스 관리 명령어 변경

**Before (systemd)**:
```bash
systemctl status coupang_coupon_issuer
journalctl -u coupang_coupon_issuer --since "1 hour ago"
```

**After (cron)**:
```bash
crontab -l  # 스케줄 확인
tail -f ~/.local/state/coupang_coupon_issuer/issuer.log  # 로그 확인
```

### 코드 구조 변화

**파일 삭제**:
- scheduler.py (108 라인): 30초 폴링 루프 제거

**config.py 변경**:
- 삭제: `CHECK_INTERVAL = 30` (scheduler 제거로 불필요)
- 추가: `LOG_DIR`, `LOG_FILE` (사용자 수준 로그)

**main.py 변경**:
- serve 명령어 제거 (cron이 스케줄링 담당)
- import 수정: SystemdService → CrontabService
- help 텍스트: systemd → cron 명령어

**service.py 재작성**:
- CrontabService 클래스 (419 라인)
- 주요 메서드:
  - `_detect_cron_system()`: cron 설치 여부 확인
  - `_get_package_manager()`: apt/dnf/yum 감지
  - `_install_cron()`: 플랫폼별 cron 설치
  - `_enable_cron_service()`: cron 데몬 활성화
  - `_get_current_crontab()`: crontab 읽기
  - `_add_cron_job()`: job 추가/업데이트
  - `_remove_cron_job()`: job 제거

### 테스트 변경

**유닛 테스트**:
- test_scheduler.py 삭제 (scheduler 제거)
- test_service.py 완전 재작성 (CrontabService 테스트, 28개)
  - 8개 테스트 클래스: Root permission, Cron detection, Package manager, Installation, Service enable, Crontab operations, Install/Uninstall
- test_cli.py 업데이트 (serve 테스트 제거)
- test_config.py 업데이트 (CHECK_INTERVAL → LOG_DIR/LOG_FILE)

**통합 테스트 재작성** (348 라인 → 520 라인):
- conftest.py 단순화 (200 라인)
  - privileged mode 제거, cgroup 마운트 제거, /sbin/init 제거
  - Fixtures: cron_container, clean_container, container_exec, installed_service, test_excel_file
- test_service_install.py 재작성 (11개 테스트)
  - Cron job 생성, 로그 디렉토리, 파일 복사, symlink, credentials, 중복 설치
- test_service_uninstall.py 재작성 (7개 테스트)
  - Cron job 제거, symlink 제거, 파일 삭제 프롬프트 (y/n 응답별)
- test_end_to_end.py 재작성 (3개 테스트)
  - 완전한 워크플로우, cron 스케줄 정확성, 로그 리다이렉션

**테스트 개수 변화**:
- 유닛 테스트: 109개 → 95개 (scheduler 14개 삭제, service 8개 추가)
- 통합 테스트: 35개 → 21개 (단순화)

### 마이그레이션 가이드

**기존 systemd 사용자**:
1. `sudo coupang_coupon_issuer uninstall` (systemd 제거)
2. `sudo coupang_coupon_issuer install ...` (cron 재설치)
3. 기존 credentials/excel 재사용 가능
4. 로그 위치 변경: journalctl → `~/.local/state/...`

---

## 2024-12-20

### Jitter 기능 추가 (ADR 011)

**목적**: Thundering herd 방지 (여러 인스턴스 동시 실행 시 API 부하 분산)

**구현 방식**:
- **폴링 루프**: 1초마다 목표 시간 체크 (긴 블로킹 sleep 대신)
- **CLI 인자**: `--jitter-max N` (1-120 범위, credentials.json 사용 안 함)
- **기본값**: jitter 없음 (하위 호환, 명시적 opt-in)
- **로그**: 시작/종료 시점만 출력 (진행 로그 없음)

**사용법**:
```bash
# 수동 실행 (jitter 60분)
coupang_coupon_issuer issue --jitter-max 60

# 서비스 설치 (jitter 활성화)
sudo coupang_coupon_issuer install \
  --access-key ... \
  --secret-key ... \
  --user-id ... \
  --vendor-id ... \
  --jitter-max 60
```

**Cron Job 예시**:
```bash
0 0 * * * /usr/bin/python3 /opt/coupang_coupon_issuer/main.py issue --jitter-max 60 >> ~/.local/state/coupang_coupon_issuer/issuer.log 2>&1  # coupang_coupon_issuer_job
```

**로그 예시**:
```
[2024-12-20 00:00:00] Jitter 대기 시작 (목표: 00:37:42, 지연: +37분)
[2024-12-20 00:37:42] Jitter 대기 완료. 쿠폰 발급을 시작합니다.
[2024-12-20 00:37:42] 쿠폰 발급 작업 시작
```

**안전성**:
- KeyboardInterrupt 처리: 최대 1초 내 응답
- 시스템 시계 변경 대응: 매 폴링마다 `datetime.now()` 재확인
- 0분 jitter 처리: 즉시 실행 로그 출력

**테스트 개수 변화**:
- 유닛 테스트: 95개 → 109개 (+14개, test_jitter.py 신규)
- 통합 테스트: 추가 예정

**파일 변경**:
- 신규: `src/coupang_coupon_issuer/jitter.py` (~100 lines)
- 신규: `tests/unit/test_jitter.py` (14개 테스트)
- 수정: `main.py` (argparse + cmd_issue/install, ~30 lines)
- 수정: `src/coupang_coupon_issuer/service.py` (install 메서드, ~15 lines)

### 검증 로직 버그 수정 (2024-12-20)

**버그**: 발급개수 범위 검증 로직의 try-except 순서 오류

**문제**:
```python
# Before (버그)
try:
    issue_count = int(float(issue_count_digits)) if issue_count_digits else DEFAULT
    if issue_count < 1:  # ValueError 발생
        raise ValueError("발급개수는 1 이상이어야 합니다")
except (ValueError, TypeError):
    raise ValueError("발급개수는 숫자여야 합니다")  # 위의 ValueError도 잡아버림!
```

**영향**:
- `issue_count < 1` 체크에서 발생한 ValueError가 except 블록에서 잡혀서 잘못된 에러 메시지 출력
- 예: `issue_count=0` → "발급개수는 숫자여야 합니다 (현재값: 0)" (잘못됨)
- 정확한 메시지: "발급개수는 1 이상이어야 합니다 (현재: 0)"

**수정**:
```python
# After (수정)
try:
    issue_count = int(float(issue_count_digits)) if issue_count_digits else DEFAULT
except (ValueError, TypeError):
    raise ValueError("발급개수는 숫자여야 합니다")

if issue_count < 1:  # try-except 외부로 이동
    raise ValueError("발급개수는 1 이상이어야 합니다")
```

**수정 위치**:
- [issuer.py:318-329](src/coupang_coupon_issuer/issuer.py#L318-L329)
- [main.py:113-123](main.py#L113-L123)

**테스트 개수**:
- 유닛 테스트: 109개 → 104개 (5개 테스트 의도 변경, 1개 삭제)
- 통합 테스트: 80개 (변경 없음)
- **전체**: 184개 (Windows: 103 passed + 26 skipped)

**테스트 수정 사항**:
1. **test_cli.py**: `cmd_issue()`, `cmd_install()` 시그니처 변경 반영
   - `args` 파라미터 추가 (MagicMock 객체)
   - `jitter_max` 속성 추가
2. **test_issuer.py**: 엣지 케이스 테스트 수정
   - `_issue_single_coupon(index, coupon)` 시그니처 반영 (index 파라미터 추가)
   - API 예외 처리: 예외 전파 → 로그 출력로 변경
   - Mock URL 수정: 올바른 엔드포인트 사용
   - Empty workbook: `load_workbook()` mock 사용
   - 에러 메시지 검증: 실제 코드 동작에 맞춰 수정
3. **검증 에러 메시지 변경**:
   - `test_fetch_coupons_non_numeric_discount`: "숫자여야" → "0보다 커야"
   - `test_fetch_coupons_downloadable_with_zero_issue_count`: "숫자여야" → "1 이상이어야"
   - `test_fetch_coupons_downloadable_with_invalid_issue_count`: 예외 발생 → 기본값 사용
   - `test_validate_fixed_with_quantity_minimum`: "FIXED_WITH_QUANTITY 1 이상" → "0보다 커야"

**입력 정규화 정책** (ADR 002):
- 비숫자 문자열 (`"xyz"`)은 빈 문자열로 정규화되어 기본값 사용
- 예: `re.sub(r'[^\d.]', '', "xyz")` → `""` → `COUPON_DEFAULT_ISSUE_COUNT`

---

## 2024-12-22

### CLI 사용성 개선 (커밋 80308b7)

**변경사항**: install 명령어 대화형 입력 지원

**Before**:
```bash
# 4개 옵션 모두 필수
python3 main.py install ~/my-coupons \
  --access-key KEY \
  --secret-key SECRET \
  --user-id USER \
  --vendor-id VENDOR
```

**After**:
```bash
# 옵션 없이 실행 시 대화형 입력
python3 main.py install ~/my-coupons
# → access key: [입력]
# → secret key: [입력]
# → user id: [입력]
# → vendor id: [입력]

# 옵션 제공 시 대화형 입력 생략
python3 main.py install ~/my-coupons --access-key KEY --secret-key SECRET ...
```

**디렉토리 기본값**:
- `issue`, `uninstall`: 기본값 `"."` (현재 디렉토리)
- `install`: 기본값 `"."` (추가됨, 이전에는 필수였음)
- `verify`: 기본값 `"."` (유지)

**주요 파일 변경**:
- [main.py:192-215](main.py#L192-L215) - `cmd_install()`: 4개 파라미터 대화형 입력 처리
- [main.py:303-312](main.py#L303-L312) - argparse: `required=True` → `required=False`
- [main.py:288](main.py#L288) - `issue` 디렉토리 기본값 `"."` 추가
- [main.py:323](main.py#L323) - `uninstall` 디렉토리 기본값 `"."` 추가
- [main.py:305](main.py#L305) - `install` 디렉토리 `nargs="?"` 추가

**테스트 영향**:
- test_cli.py 업데이트 필요 (대화형 입력 mock)

### Uninstall 자동 정리 (커밋 5a21b80)

**변경사항**: uninstall 시 config.json 자동 제거

**Before**:
```bash
coupang_coupon_issuer uninstall
# → Cron job 제거만 수행
# → 설정 파일 유지: ~/.../config.json
# → 완전 삭제: rm -rf ~/my-coupons
```

**After**:
```bash
coupang_coupon_issuer uninstall
# → Cron job 제거
# → 설정 파일 자동 제거 (config.json)
# → coupons.xlsx, issuer.log는 유지 (사용자 데이터)
```

**구현**:
- [config.py:235-242](src/coupang_coupon_issuer/config.py#L235-L242) - `ConfigManager.remove()` 메서드 추가
- [service.py:325-326](src/coupang_coupon_issuer/service.py#L325-L326) - uninstall 시 `ConfigManager.remove()` 호출

**정책**:
- **자동 제거**: config.json (재생성 가능, 민감 정보)
- **유지**: coupons.xlsx, issuer.log (사용자 데이터)

**테스트 영향**:
- test_service.py: uninstall 테스트에 config.json 제거 검증 추가 필요
- test_config.py: `ConfigManager.remove()` 유닛 테스트 추가 필요

### 레거시 코드 제거 (커밋 624b3a8)

**변경사항**: CredentialManager alias 제거

**삭제 항목**:
- [config.py:245-247](src/coupang_coupon_issuer/config.py#L245-L247) - `CredentialManager = ConfigManager` (레거시 alias)
- [test_config.py:374-385](tests/unit/test_config.py#L374-L385) - `TestLegacyCompatibility` 클래스 (11 lines)

**배경**:
- CredentialManager는 초기 네이밍이었으나 ConfigManager로 통일
- Alias를 유지할 필요성 없음 (프로젝트 미배포, 하위 호환성 불필요)

**테스트 개수 변화**:
- 유닛 테스트: 109개 → 108개 (-1개)

---

## 2024-12-23

### 단위 테스트 업데이트 (ADR 015, 016 반영)

**목적**: ADR 015 (옵션ID 컬럼), ADR 016 (테스트 레이어 분리) 반영

**주요 변경사항**:

1. **Excel 구조 변경: 6컬럼 → 7컬럼 (ADR 015)**
   - 새 컬럼: `옵션ID` (Column G, 7번째 컬럼)
   - 값: 쉼표로 구분된 vendor item ID 리스트 (예: "123456789,987654321")
   - 필수 입력, 비어있으면 에러
   - 숫자만 허용, 쉼표로 분리 후 `int()` 변환
   - 최대 10,000개 제한 (Coupang API 제약)

2. **test_issuer.py 업데이트 (31개 테스트)**
   - 모든 Excel 테스트 데이터에 7번째 컬럼 추가
   - `coupon_dict_factory` fixture: `vendor_items` 필드 추가
   - `empty_excel` fixture: 7컬럼 헤더로 업데이트
   - 환경변수 fallback 테스트 제거: `test_init_from_env_variables` 삭제 (ADR 014)
   - 복잡한 테스트 간소화: `test_issue_mixed_success_failure`
     - Before: 4단계 API 모킹 (create, status, apply, status)
     - After: `_issue_single_coupon` 메서드 모킹
     - 이유: 테스트 목적에 집중 (혼합 성공/실패 시나리오), 유지보수성 향상

3. **test_cli.py 업데이트 (20개 테스트)**
   - 모든 Excel 테스트 데이터에 7번째 컬럼 추가
   - verify 명령어 테스트 수정 (5개):
     - 파일명: `valid.xlsx`, `rate.xlsx` 등 → `coupons.xlsx` (ADR 014)
     - 인자: `args.file` → `args.directory` (cmd_verify는 항상 coupons.xlsx 찾음)
   - 대화형 입력 테스트 제거: `test_install_requires_all_4_params` 삭제
     - 이유: pytest에서 `input()` 호출 테스트 불가 (stdin capture 충돌)

4. **test_jitter.py 추가 (14개 테스트)**
   - Jitter 스케줄러 테스트 (ADR 011)
   - 초기화, 대기 로직, 타임스탬프 검증

**테스트 결과** (2024-12-23):
- **유닛 테스트**: 105개 통과, 27개 스킵 (Linux 전용)
- **커버리지**: 68% (전체)
  - config.py: 94%
  - coupang_api.py: 85%
  - issuer.py: 80%
  - jitter.py: 100%
- **Windows 환경**: test_service.py 27개 자동 스킵

**테스트 개수 변화**:
- test_issuer.py: 32개 → 31개 (-1개, env var 테스트 제거)
- test_cli.py: 21개 → 20개 (-1개, interactive input 테스트 제거)
- test_jitter.py: 14개 (신규)
- test_config.py: 26개 → 25개 (-1개, legacy alias 테스트 제거)
- test_coupang_api.py: 12개 → 15개 (+3개)
- **전체**: 108개 → 105개 (27개 skipped)

**Excel 정규화 규칙 추가**:
- **옵션ID**: `str(value).strip()` → 쉼표로 분리 → 각 항목 `int()` 변환
- 빈 값 체크: `if not vendor_items_raw or vendor_items_raw == 'None'`
- 숫자 검증: `int(item.strip())` 실패 시 ValueError

**문서 업데이트**:
- CLAUDE.md: ADR 015, 016 추가, 테스트 현황 업데이트
- TESTING.md: 테스트 개수 및 구조 업데이트 (예정)

### 엑셀 예시 생성 스크립트 추가

**목적**: 사용자가 엑셀 포맷을 쉽게 이해할 수 있도록 예제 파일 제공

**생성된 파일**:
- [scripts/generate_example.py](../scripts/generate_example.py) - 예제 생성 스크립트
- [scripts/__init__.py](../scripts/__init__.py) - 패키지 초기화

**사용법**:
```bash
uv run python scripts/generate_example.py
```

**출력** (`examples/` 디렉토리):
- `basic.xlsx`: 기본 예제 (즉시할인 1개, 다운로드쿠폰 1개)
- `comprehensive.xlsx`: 포괄적 예제 (모든 쿠폰 타입 × 할인 방식 조합 6개)
- `edge_cases.xlsx`: 엣지 케이스 (최소/최대값, 다중 옵션 등 7개)

**Excel 구조** (7컬럼, ADR 015):
1. 쿠폰이름
2. 쿠폰타입 (즉시할인 / 다운로드쿠폰)
3. 쿠폰유효기간 (일 단위)
4. 할인방식 (RATE / PRICE / FIXED_WITH_QUANTITY)
5. 할인금액/비율
6. 발급개수
7. 옵션ID (쉼표로 구분)

**헤더 스타일**: 굵게, 배경색 (#366092), 중앙 정렬, 컬럼 너비 자동 조정

**예제 데이터 특징**:
- 모든 데이터는 validation 규칙 통과
- 옵션ID는 실제 사용 가능한 10자리 숫자 형식
- 정률할인: 1~99% 범위
- 정액할인: 10원 단위, 최소 10원
- 수량할인: 최소 1개

### 쿠폰 타입별 할인 검증 규칙 (ADR 017)

**다운로드 쿠폰**:
- RATE: 1~99 (퍼센트, 100% 불가)
- PRICE: 10원 단위 금액 (최소 10원 이상)

**즉시할인 쿠폰**:
- RATE: 1~100 (퍼센트, 100% 할인 허용)
- PRICE: 1원 이상 (10원 단위 제약 없음)
- FIXED_WITH_QUANTITY: 1 이상

**차이점**:
- 즉시할인은 RATE 100% 허용, 다운로드는 1~99만 허용
- 즉시할인은 PRICE 1원부터 가능, 다운로드는 10원 단위 필수

**참조**: [ADR 017](adr/017-coupon-type-specific-validation.md)

### 할인방식 한글 입력 지원 (ADR 018)

**목적**: 비전문가 사용자를 위한 한글 할인방식 입력 지원

**변경사항**:
- **Excel 입력**: 영어 코드(`RATE`, `PRICE`, `FIXED_WITH_QUANTITY`) → 한글(`정률할인`, `정액할인`, `수량별 정액할인`)
- **내부 처리**: 한글 → 영어 자동 변환 (API 호출 시 영어 사용)
- **에러 메시지**: 영어 → 한글로 변경

**매핑 테이블**:
| 한글 (엑셀 입력) | 영어 (내부 코드) |
|---|---|
| 정률할인 | RATE |
| 수량별 정액할인 | FIXED_WITH_QUANTITY |
| 정액할인 | PRICE |

**구현 위치**:
- [issuer.py:20-31](src/coupang_coupon_issuer/issuer.py#L20-L31) - 매핑 상수
- [issuer.py:441-451](src/coupang_coupon_issuer/issuer.py#L441-L451) - 파싱 로직
- [issuer.py:494,498,500,506,510,514](src/coupang_coupon_issuer/issuer.py) - 에러 메시지

**Breaking Change**: 기존 영어 코드는 더 이상 지원되지 않음. 모든 엑셀 파일을 한글로 변경 필요.

**마이그레이션 방법**:
```bash
# 예제 파일 재생성
uv run python scripts/generate_example.py

# 또는 수동 변경
# RATE → 정률할인
# PRICE → 정액할인
# FIXED_WITH_QUANTITY → 수량별 정액할인
```

**테스트 결과**: 33 passed (유닛 테스트)

**참조**: [ADR 018](adr/018-korean-discount-type-names.md)

### 엑셀 예시 파일 개선 - 헤더 주석 및 데이터 유효성 검사

**목적**: 비전문가 사용자가 엑셀 파일 작성 시 실수를 줄이고 올바른 입력을 유도

**추가된 기능**:

1. **헤더 주석 (Header Comments)**:
   - 각 컬럼 헤더에 마우스 오버 시 상세 설명 표시
   - 비개발자가 실수할 만한 내용 강조 (% 없이 10 입력, 원 없이 1000 입력 등)
   - 쿠폰 타입별 차이점 명시

2. **데이터 유효성 검사 (Data Validation)**:
   - **쿠폰타입** (Column B): 드롭다운 (즉시할인, 다운로드쿠폰)
   - **쿠폰유효기간** (Column C): 1~365 정수
   - **할인방식** (Column D): 드롭다운 (정률할인, 정액할인, 수량별 정액할인)
   - **할인금액/비율** (Column E): 1 이상 정수 (Warning, 공통 제약만)
   - **발급개수** (Column F): 1 이상 정수, 선택적 (Warning)
   - **옵션ID** (Column G): 필수 텍스트

**구현 방식**:
- `openpyxl.comments.Comment`로 헤더 주석 추가
- `openpyxl.worksheet.datavalidation.DataValidation`으로 유효성 검사 추가
- 쿠폰 타입별로 검증 규칙이 다른 컬럼은 **Warning만 표시**하고 실행 시 재검증

**제약 전략 (ADR 017, 018 반영)**:
- 다운로드/즉시할인 여부에 따라 검증 규칙이 다르므로 **공통 제약만 적용**
- 정률할인: 다운로드 1~99, 즉시할인 1~100 → Excel에서는 ≥1로만 제한
- 정액할인: 다운로드 10원 단위, 즉시할인 1원 이상 → Excel에서는 ≥1로만 제한
- 세부 검증은 `issuer.py`에서 수행

**생성된 파일**:
- `examples/basic.xlsx` - 헤더 주석 및 유효성 검사 포함
- `examples/comprehensive.xlsx` - 헤더 주석 및 유효성 검사 포함
- `examples/edge_cases.xlsx` - 헤더 주석 및 유효성 검사 포함

**사용법**:
```bash
uv run python scripts/generate_example.py
```

**검증**:
```bash
# 예제 파일 확인
uv run python main.py verify examples/
```

**주요 주석 내용**:
- 쿠폰이름: 예시 제공 (신규회원 할인쿠폰 등)
- 쿠폰타입: 즉시할인 vs 다운로드쿠폰 차이 설명
- 쿠폰유효기간: 일 단위 설명 (7 → 7일간 유효)
- 할인방식: 쿠폰 타입별 차이 명시 (정률: 다운로드 1~99, 즉시할인 1~100)
- 할인금액/비율: **% 기호 없이**, **원 없이** 입력 강조
- 발급개수: 즉시할인은 비워두기 명시
- 옵션ID: 쉼표 구분, 공백 없이 입력 강조

---
---

## 2024-12-24

### 엑셀 로직 분리 및 테스트 추가

**목적**: `verify` 명령어와 `issue` 명령어가 동일한 엑셀 읽기/검증 로직을 사용하도록 공통 모듈 분리

**변경사항**:

1. **신규 모듈: `reader.py`**
   - 엑셀 파일 읽기 및 검증 로직 중앙화
   - `fetch_coupons_from_excel(excel_path: Path)` 함수 제공
   - `DISCOUNT_TYPE_KR_TO_EN`, `DISCOUNT_TYPE_EN_TO_KR` 상수 이동
   - ADR 002 (입력 정규화), ADR 017 (타입별 검증), ADR 018 (한글 할인방식) 모두 반영

2. **신규 모듈: `utils.py`**
   - 한글 너비 고려 정렬 유틸리티
   - `get_visual_width(text)`: East Asian 문자 너비 계산 (W/F = 2, 나머지 = 1)
   - `kor_align(text, width, align)`: 한글 너비를 고려한 정렬 (우측/좌측/중앙)

3. **`issuer.py` 리팩토링**
   - `_fetch_coupons_from_excel()` 메서드를 `reader.fetch_coupons_from_excel()` 호출로 변경
   - 중복 코드 제거, 로직 단일화

4. **`main.py` 리팩토링**
   - `cmd_verify()` 함수에서 `reader.fetch_coupons_from_excel()` 사용
   - 테이블 출력 개선:
     - 우측 정렬 적용 (`kor_align` 사용)
     - 할인방식 한글 변환 (`DISCOUNT_TYPE_EN_TO_KR`)
     - 컬럼별 너비 차등화: No(4), 쿠폰이름(25), 쿠폰타입(13), 유효기간(10), 할인방식(17), 할인금액(10), 할인비율(10), 발급개수(10), 총 예산(12)
     - 비해당 컬럼 빈 문자열 처리:
       - 정률할인: 할인금액 비움
       - 정액할인/수량할인: 할인비율 비움
       - 즉시할인: 발급개수 비움

5. **단위 테스트 추가**
   - `tests/unit/test_reader.py` (20개 테스트)
     - 엑셀 파싱 검증
     - 한글 할인방식 매핑
     - 타입별 검증 규칙 (ADR 017)
     - 입력 정규화 (ADR 002)
     - 엑셀 헤더 변형 ("옵션 ID" 허용)
   - `tests/unit/test_utils.py` (17개 테스트)
     - `get_visual_width()`: ASCII, 한글, 혼합 문자열 너비 계산
     - `kor_align()`: 우측/좌측/중앙 정렬 검증

**테스트 결과**:
- 유닛 테스트: 115개 → 143개 (+28개)
- 전체 테스트: 143개 통과 (Windows 환경)

**문서 업데이트**:
- CLAUDE.md: 프로젝트 구조에 `reader.py`, `utils.py` 추가
- DEV_LOG.md: 본 항목 추가

**참조**:
- [src/coupang_coupon_issuer/reader.py](../src/coupang_coupon_issuer/reader.py) - 엑셀 읽기 모듈
- [src/coupang_coupon_issuer/utils.py](../src/coupang_coupon_issuer/utils.py) - 정렬 유틸리티
- [tests/unit/test_reader.py](../tests/unit/test_reader.py) - 엑셀 로직 테스트
- [tests/unit/test_utils.py](../tests/unit/test_utils.py) - 정렬 유틸리티 테스트

### Coupang API 타입 오류 수정 (2024-12-25)

**문제**: Coupang API 문서의 예제가 명세와 불일치 (예제는 문자열, 명세는 숫자)

**원인**: Coupang 측 문서 작성 오류 - 명세는 올바르나 예제가 잘못됨

**수정 항목**:

1. **API 문서 예제 수정**:
   - `instant-coupon-api.md`: `contractId`, `maxDiscountPrice`, `discount`, `wowExclusive` → 숫자/불린 타입
   - `download-coupon-api.md`: `contractId` → 숫자 타입
   - `download-coupon-item-api.md`: `couponId` → 숫자 타입

2. **코드 수정** (`coupang_api.py`):
   - `create_instant_coupon()`: `str(contract_id)` → `contract_id` (숫자 전송)
   - `create_instant_coupon()`: `str(max_discount_price)` → `max_discount_price` (숫자 전송)
   - `create_instant_coupon()`: `str(discount)` → `discount` (숫자 전송)
   - `apply_download_coupon()`: `str(coupon_id)` → `coupon_id` (숫자 전송)

**영향**: 문자열로 전송 시 `Bad Request` 오류 발생 → 숫자 타입으로 수정하여 해결

**참조**:
- [docs/coupang/instant-coupon-api.md](../docs/coupang/instant-coupon-api.md)
- [docs/coupang/download-coupon-api.md](../docs/coupang/download-coupon-api.md)
- [docs/coupang/download-coupon-item-api.md](../docs/coupang/download-coupon-item-api.md)
- [src/coupang_coupon_issuer/coupang_api.py](../src/coupang_coupon_issuer/coupang_api.py)

---

## 2025-12-25

### REQUESTED 상태 간단 폴링 구현 (ADR 020)

**TODO: 향후 Async 리팩토링 필요**
- 현재: 간단한 폴링 (5회 × 2초, 최대 10초 대기)
- 향후: asyncio + httpx 기반 비동기 처리로 전환
- 참조: ADR 020
- 검색 키워드: TODO, async, polling, REQUESTED

---

### 다운로드쿠폰 minimumPrice 필드 추가 (2025-12-26)

**문제**: 다운로드쿠폰 생성 시 policy에 `minimumPrice` 필드 누락

**수정**:
- `issuer.py`: policy 딕셔너리에 `minimumPrice: 0` 추가
- 값: 0 (최소 구매금액 제한 없음)
- API 문서에 명시된 필수 필드였으나 구현에서 누락됨

**영향**: 기존 테스트는 이미 `minimumPrice`를 포함하고 있어서 테스트 수정 불필요

**참조**: [download-coupon-api.md](../docs/coupang/download-coupon-api.md#policies-객체-필드)
