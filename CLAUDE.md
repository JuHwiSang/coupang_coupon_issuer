# Claude 개발 가이드

매일 0시에 자동으로 쿠폰을 발급하는 Linux cron 서비스

## 문서 구조

프로젝트의 모든 결정사항과 규칙은 `docs/` 디렉토리에 문서화되어 있습니다:

### 📋 DEV_LOG.md
작은 결정사항, 코딩 규칙, 관례를 기록합니다.

- 로깅 규칙
- 예외 처리 관례
- 타입 체커 처리 방법
- 코딩 스타일

**위치**: [docs/DEV_LOG.md](docs/DEV_LOG.md)

### 📐 ADR (Architecture Decision Records)

중요한 아키텍처 결정사항을 문서화합니다. 각 ADR은 독립적인 문서로 관리됩니다.

**위치**: `docs/adr/NNN-title.md`

현재 ADR 목록:
- [ADR 001: 엑셀 입력 구조](docs/adr/001-excel-structure.md) - ~~5개 컬럼 구조~~ (대체됨, ADR 009 참조)
- [ADR 002: 입력 정규화](docs/adr/002-input-normalization.md) - 사용자 입력 오류 용인 로직
- [ADR 003: API 인증](docs/adr/003-api-authentication.md) - HMAC-SHA256 서명 생성
- [ADR 004: 고정 설정값](docs/adr/004-fixed-configuration-values.md) - contract_id, 예산 등
- [ADR 005: systemd 서비스](docs/adr/005-systemd-service.md) - ~~스케줄링 전략, 로깅~~ (대체됨, ADR 010 참조)
- [ADR 006: contract_id=-1 무료 예산](docs/adr/006-contract-id-negative-one.md) - 무료 예산 사용
- [ADR 007: 쿠폰 발급 워크플로우](docs/adr/007-coupon-issuance-workflow.md) - 다단계 비동기 처리
- [ADR 008: CLI 구조 재설계](docs/adr/008-cli-restructuring.md) - ~~5개 명령어~~, 4개 명령어, 전역 명령어, 로그 중심 운영
- [ADR 009: 엑셀 6컬럼 구조](docs/adr/009-excel-6-column-structure.md) - 할인금액/비율과 발급개수 분리
- [ADR 010: Crontab 기반 스케줄링](docs/adr/010-crontab-service.md) - Cron 스케줄링, 사용자 수준 로그

### 📝 문서 작성 규칙

1. **기존 문서는 수정하지 않음**
   - 결정이 변경되면 새 ADR 작성
   - 기존 문서에는 deprecation warning만 추가

2. **DEV_LOG vs ADR 구분**
   - 작은 규칙/관례 → DEV_LOG.md
   - 중요한 아키텍처 결정 → 새 ADR

3. **ADR 번호**
   - 001, 002, 003... 순차 증가
   - 결번 없음 (삭제 시에도 번호 유지)

## 환경

- **OS**: Linux (cron 자동 설치)
- **Python**: 3.10+
- **패키지**: requests, openpyxl
- **로깅**: ~/.local/state/coupang_coupon_issuer/issuer.log

## 프로젝트 구조

```
# 설치 후 구조
/opt/coupang_coupon_issuer/
├── main.py                          # CLI 진입점
├── src/coupang_coupon_issuer/
│   ├── config.py                    # API 키 관리, 고정값 설정
│   ├── coupang_api.py               # Coupang API 클라이언트 (HMAC-SHA256)
│   ├── issuer.py                    # 쿠폰 발급 로직 (로그 출력만)
│   └── service.py                   # Cron 설치/제거
└── pyproject.toml

/usr/local/bin/
└── coupang_coupon_issuer            # 심볼릭 링크 → /opt/.../main.py

/etc/coupang_coupon_issuer/
├── credentials.json                 # API 키 (600 권한)
└── coupons.xlsx                     # 쿠폰 정의 (600 권한)

~/.local/state/coupang_coupon_issuer/
└── issuer.log                       # 로그 파일 (사용자 수준)

# 개발 디렉토리 구조
docs/
├── DEV_LOG.md                       # 작은 결정사항, 관례
├── adr/                             # 아키텍처 결정 기록
│   ├── 001-excel-structure.md      # (대체됨)
│   ├── 002-input-normalization.md
│   ├── 003-api-authentication.md
│   ├── 004-fixed-configuration-values.md
│   ├── 005-systemd-service.md      # (대체됨)
│   ├── 006-contract-id-negative-one.md
│   ├── 007-coupon-issuance-workflow.md
│   ├── 008-cli-restructuring.md
│   ├── 009-excel-6-column-structure.md
│   └── 010-crontab-service.md      # 현재 사용
└── coupang/                         # Coupang API 규격 문서
    ├── workflow.md
    ├── parameters-explained.md
    └── (각종 API 문서)
```

## Claude에게 작업 요청

### 제약사항 (항상 명시)

- Python 3.10 호환
- Linux 서버 전용 (cron 기반)
- 패키지: requests, openpyxl만 사용
- 로그에 이모지 사용 금지 (텍스트만)
- 예외 처리 필수 (로깅 후 상위로 전파)
- **Python 실행 시 uv 사용**: `uv run python script.py` 또는 `uv run pytest`
- **cd 명령어 사용 금지**: 절대 경로만 사용

### 구현 가이드

1. **새로운 기능 구현 전**: 관련 ADR 문서를 먼저 읽어보세요
2. **아키텍처 결정 필요 시**: 새 ADR 작성 후 사용자 승인 받기
3. **작은 변경사항**: DEV_LOG.md에 기록

### CLI 명령어

설치 후 전역 명령어로 실행 가능:

```bash
# 1. 엑셀 파일 검증 및 적용
sudo coupang_coupon_issuer apply ./coupons.xlsx

# 2. 단발성 쿠폰 발급 (테스트용)
coupang_coupon_issuer issue

# 3. 서비스 설치
sudo coupang_coupon_issuer install \
  --access-key YOUR_KEY \
  --secret-key YOUR_SECRET \
  --user-id YOUR_USER_ID \
  --vendor-id YOUR_VENDOR_ID

# 4. 서비스 제거
sudo coupang_coupon_issuer uninstall

# 서비스 관리
crontab -l                                              # 스케줄 확인
tail -f ~/.local/state/coupang_coupon_issuer/issuer.log # 로그 확인
```

### 다음 구현 작업

- [x] CLI 구조 재설계 (4개 명령어)
- [x] 엑셀 결과 출력 제거 (로그로만)
- [x] 전역 명령어 구현 (심볼릭 링크)
- [x] install 4개 파라미터 확장
- [x] Docker 테스트 환경 구성
- [x] 테스트 작성 (pytest + requests-mock + testcontainers)
- [x] Crontab 기반 스케줄링으로 전환
- [ ] 성능 최적화 (병렬 처리, 선택사항)

## 디버깅

로그 확인 시:
```bash
tail -f ~/.local/state/coupang_coupon_issuer/issuer.log
# 또는
cat ~/.local/state/coupang_coupon_issuer/issuer.log | grep ERROR
```

에러 스택 트레이스와 함께 파일명:라인번호 포함하여 요청

## 완료 체크리스트

### 핵심 기능
- [x] API 클라이언트 (coupang_api.py)
- [x] HMAC-SHA256 인증 구현
- [x] 엑셀 I/O (5개 컬럼 + 입력 정규화)
- [x] issue() 메서드 실제 로직
- [x] 고정값 설정 (예산, 유효기간, contract_id 등)
- [x] 사용자 입력 오류 용인 로직

### CLI 및 배포
- [x] CLI 구조 재설계 (apply/issue/install/uninstall - 4개 명령어)
- [x] 전역 명령어 (심볼릭 링크)
- [x] install 4개 파라미터 확장
- [x] 엑셀 결과 출력 제거 (로그 중심)
- [x] Docker 테스트 환경 (docker-compose.test.yml)
- [x] Cron 기반 스케줄링 (systemd 제거)

### 문서화
- [x] DEV_LOG (로깅 규칙, 검증 규칙 등)
- [x] ADR 001-010 (아키텍처 결정 기록)
- [x] Coupang API 문서 (workflow, parameters 등)

### 테스트
- [x] 유닛 테스트 작성 (pytest + requests-mock)
  - **유닛 테스트**: 95개 (scheduler 삭제 -14개, service 재작성 +8개)
  - **Windows 테스트 결과** (2024-12-19 - Cron 마이그레이션 완료):
    - ✅ test_config.py: 18/18 통과 (100%, LOG_DIR/LOG_FILE 추가)
    - ✅ test_coupang_api.py: 12/12 통과 (100%)
    - ✅ test_cli.py: 18/18 통과 (100%, serve 테스트 제거)
    - ✅ test_issuer.py: 32/32 통과 (100%)
    - ✅ test_service.py: 28/28 재작성 완료 (CrontabService, Linux only)
  - **커버리지**: config/api/issuer 94%+
  - **테스트 실행**: `uv run pytest tests/unit -v`
  - **커버리지 확인**: `uv run pytest --cov=src/coupang_coupon_issuer`

- [x] 통합 테스트 재작성 완료 (cron 기반)
  - **통합 테스트**: 21개 (systemd 35개 → cron 21개로 단순화)
    - test_service_install.py: 11개 테스트 (cron job, 파일, credentials)
    - test_service_uninstall.py: 7개 테스트 (cron job 제거, 파일 삭제 프롬프트)
    - test_end_to_end.py: 3개 테스트 (E2E 워크플로우, 스케줄 정확성)
  - **testcontainers 인프라**: Ubuntu 22.04 + cron (privileged mode 불필요)
  - **conftest.py**: 200 라인 (기존 348 라인에서 단순화)
  - **실행 환경**: Docker Desktop 필요 (WSL2 backend)
  - **테스트 실행**: `uv run pytest tests/integration -v -m integration`

### 향후 작업
- [ ] 통합 테스트 실제 실행 및 검증 (Linux/Docker 환경)
- [ ] 성능 최적화 (병렬 처리, 선택사항)

## 테스트 가이드

### 테스트 구조

```
tests/
├── conftest.py                   # 공통 fixture (credentials, excel, mock API)
├── fixtures/                     # 테스트용 엑셀 파일
│   ├── sample_valid.xlsx
│   ├── sample_invalid_columns.xlsx
│   ├── sample_invalid_rates.xlsx
│   └── sample_invalid_prices.xlsx
├── unit/                         # 유닛 테스트 (109개)
│   ├── test_config.py            # CredentialManager 테스트 (17개)
│   ├── test_coupang_api.py       # API 클라이언트 + HMAC (12개)
│   ├── test_issuer.py            # 쿠폰 발급 로직 (32개, 12개 엣지 케이스 추가)
│   ├── test_service.py           # Cron 관리 (재작성 필요, Linux only)
│   └── test_cli.py               # CLI 명령어 (20개)
└── integration/                  # 통합 테스트 (35개, Docker 필요)
    ├── conftest.py               # testcontainers 인프라 (250 라인)
    ├── test_service_install.py   # 설치 프로세스 (14개)
    ├── test_service_uninstall.py # 제거 프로세스 (18개)
    └── test_end_to_end.py        # E2E 워크플로우 (3개)
```

### 테스트 실행 명령어

```bash
# 유닛 테스트 (Windows 호환, 빠름)
uv run pytest tests/unit -v

# 통합 테스트 (Docker Desktop 필요, 느림)
uv run pytest tests/integration -v -m integration

# 전체 테스트
uv run pytest -v

# 커버리지 포함
uv run pytest tests/unit --cov=src/coupang_coupon_issuer --cov-report=html

# 특정 파일만
uv run pytest tests/unit/test_issuer.py -v
```

### Windows vs Linux 테스트

- **유닛 테스트**:
  - Windows 환경: 95개 중 83개 실행 (service.py 12개 스킵, scheduler.py 삭제)
  - Linux 환경: 95개 전부 실행 가능
- **통합 테스트**:
  - Windows: Docker Desktop(WSL2) 필요
  - Linux: Docker만 필요
  - testcontainers로 Ubuntu 22.04 + cron 컨테이너 실행 (privileged mode 불필요)

### 테스트 작성 규칙

1. **Mock 사용**
   - requests-mock: HTTP API 호출
   - pytest-mock: 일반 객체 모킹

2. **Fixture 활용**
   - `temp_credentials`: 임시 credentials.json
   - `valid_excel`: 유효한 5컬럼 엑셀
   - `mock_coupang_api`: Coupang API 응답 모킹

3. **테스트 마커**
   - `@pytest.mark.unit`: 유닛 테스트
   - `@pytest.mark.integration`: 통합 테스트
   - `@pytest.mark.slow`: 느린 테스트 (> 1초)
   - Windows 스킵: `pytestmark = pytest.mark.skipif(os.name == 'nt', ...)` 사용
