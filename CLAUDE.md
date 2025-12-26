# Claude 개발 가이드

매일 0시에 자동으로 쿠폰을 발급하는 Linux cron 서비스

## 문서 구조

프로젝트의 모든 결정사항과 규칙은 `docs/` 디렉토리에 문서화되어 있습니다:

### 📖 USER_GUIDE.md (비개발자용)

**비개발자를 위한 간단한 사용설명서**입니다. 프로그래밍 지식이 없는 사용자도 쉽게 프로그램을 사용할 수 있도록 작성되었습니다.

- 엑셀 파일 작성부터 설치, 관리까지 단계별 가이드
- 명령어 최소화 (setup, install, verify, uninstall만 설명)
- 중요 주의사항 강조 (폴더 이동 금지, 엑셀 형식 엄수, 예산 차감 등)
- 문제 해결 방법 포함

**위치**: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

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
- [ADR 001: 엑셀 입력 구조](docs/adr/001-excel-structure.md) - ~~5개 컴럼 구조~~ (대체됨, ADR 009 참조)
- [ADR 002: 입력 정규화](docs/adr/002-input-normalization.md) - 사용자 입력 오류 용인 로직
- [ADR 003: API 인증](docs/adr/003-api-authentication.md) - HMAC-SHA256 서명 생성
- [ADR 004: 고정 설정값](docs/adr/004-fixed-configuration-values.md) - ~~contract_id~~, 예산 등
- [ADR 005: systemd 서비스](docs/adr/005-systemd-service.md) - ~~스케줄링 전략, 로깅~~ (대체됨, ADR 010 참조)
- [ADR 006: contract_id=-1 무료 예산](docs/adr/006-contract-id-negative-one.md) - ~~무료 예산 사용~~ (업데이트됨: 동적 조회 방식으로 변경)
- [ADR 007: 쿠폰 발급 워크플로우](docs/adr/007-coupon-issuance-workflow.md) - 다단계 비동기 처리
- [ADR 008: CLI 구조 재설계](docs/adr/008-cli-restructuring.md) - ~~4개 명령어, 전역 명령어~~ (대체됨, ADR 014 참조)
- [ADR 009: 엑셀 6컴럼 구조](docs/adr/009-excel-6-column-structure.md) - ~~할인금액/비율과 발급개수 분리~~ (대체됨, ADR 015 참조)
- [ADR 010: Crontab 기반 스케줄링](docs/adr/010-crontab-service.md) - ~~Cron 스케줄링, 사용자 수준 로그~~ (대체됨, ADR 014 참조)
- [ADR 011: Jitter 기능](docs/adr/011-jitter-thundering-herd.md) - Thundering herd 방지
- [ADR 012: XDG Base Directory](docs/adr/012-xdg-base-directory.md) - ~~XDG 표준 준수~~ (대체됨, ADR 014 참조)
- [ADR 013: PyInstaller 단일 실행 파일 배포](docs/adr/013-pyinstaller-single-binary.md) - ~~PyInstaller 배포~~ (대체됨, ADR 014 참조)
- [ADR 014: 스크립트 기반 배포](docs/adr/014-script-based-deployment.md) - **현재 구조**, Python 스크립트 배포, 런타임 경로 지정
- [ADR 015: 옵션ID 컴럼 추가](docs/adr/015-option-id-column.md) - **현재 구조**, 7컴럼 엑셀 구조, vendor_items 필드
- [ADR 016: 테스트 레이어 분리](docs/adr/016-test-layer-separation.md) - unit/integration/e2e 분리 전략
- [ADR 017: 쿠폰 타입별 할인 검증 규칙 분리](docs/adr/017-coupon-type-specific-validation.md) - 다운로드/즉시할인 쿠폰 검증 분리
- [ADR 018: 할인방식 한글 입력 지원](docs/adr/018-korean-discount-type-names.md) - 정률할인/수량별 정액할인/정액할인 한글 입력
- [ADR 019: setup/install 명령어 분리](docs/adr/019-setup-install-separation.md) - **현재 구조**, 시스템/사용자 레벨 작업 분리, 파일 권한 정상화
- [ADR 020: 즉시할인쿠폰 REQUESTED 상태 간단 폴링](docs/adr/020-instant-coupon-simple-polling.md) - **덕테이프 솔루션**, 5회 × 2초 폴링, 향후 async 리팩토링 필요
- [ADR 021: Excel 9컬럼 구조](docs/adr/021-excel-9-column-structure.md) - **현재 구조**, 최소구매금액/최대할인금액 Excel 설정
- [ADR 022: 다운로드쿠폰 타이밍 수정](docs/adr/022-download-coupon-timing-fix.md) - KST timezone, 시작일/종료일 계산 로직

## ⚠️ 중요: Coupang API 공식 문서 오류

**다운로드쿠폰 아이템 적용 API 응답 형식이 공식 문서와 다릅니다!**

- **API**: `PUT /v2/providers/marketplace_openapi/apis/api/v1/coupon-items`
- **공식 문서**: 단일 객체 `{...}` (잘못됨)
- **실제 응답**: 배열 `[{...}]` (올바름)

**반드시 배열의 첫 번째 요소에서 데이터를 추출해야 합니다:**
```python
response = api_client.apply_download_coupon(...)
result = response[0]  # 배열의 첫 번째 요소
status = result.get('requestResultStatus')
```

**자세한 내용**: [download-coupon-item-api.md](docs/coupang/download-coupon-item-api.md), [DEV_LOG.md](docs/DEV_LOG.md) (2025-12-26 저녁)

## 계약 타입 (Contract Types)

본 시스템은 **자유계약기반(NON_CONTRACT_BASED)** 계약만을 사용하여 쿠폰을 발급합니다.

### 자유계약기반 (NON_CONTRACT_BASED)
- `vendorContractId`가 `-1`인 계약
- 별도의 계약서 없이 자유롭게 쿠폰을 발급할 수 있는 계약
- 일반적으로 종료일이 먼 미래(`2999-12-31 23:59:59`)로 설정됨
- **시스템 시작 시 API를 통해 자동으로 조회하여 사용**

### 계약기반 (CONTRACT_BASED)
- `vendorContractId`가 양수인 계약
- 특정 계약서에 기반한 쿠폰 발급
- 계약 기간이 명확하게 정의됨
- **본 시스템에서는 사용하지 않음**

### contractId 조회 프로세스
1. `CouponIssuer` 초기화 시 계약 목록 API 호출 (`GET /v2/providers/fms/apis/api/v2/vendors/{vendorId}/contract/list`)
2. 응답에서 `type`이 `NON_CONTRACT_BASED`이고 `vendorContractId`가 `-1`인 계약 필터링
3. 첫 번째 자유계약기반 계약의 `contractId`를 사용
4. 자유계약기반 계약이 없으면 오류 발생

자세한 API 규격은 [계약 목록 조회 API](docs/coupang/contract-list-api.md)를 참조하세요.

### 📝 문서 작성 규칙

1. **기존 문서는 수정하지 않음**
   - 결정이 변경되면 새 ADR 작성

2. **DEV_LOG vs ADR 구분**
   - 작은 규칙/관례 → DEV_LOG.md
   - 중요한 아키텍처 결정 → 새 ADR

3. **ADR 번호**
   - 001, 002, 003... 순차 증가
   - 결번 없음 (삭제 시에도 번호 유지)

## 환경

### 개발 환경
- **OS**: Linux (cron 자동 설치)
- **Python**: 3.10+
- **패키지**: requests, openpyxl
- **개발 도구**: uv (패키지 관리)

### 배포 환경 (하이브리드)
- **OS**: Linux (cron 필요)
- **Python**: 3.10+ 필수
- **의존성**: requests, openpyxl 필요
- **배포 방식**: Python 스크립트 또는 PyInstaller 바이너리 (자동 감지)

### CI/CD 환경
- **GitHub Actions**: 자동 빌드 워크플로우
- **빌드 도구**: uv + PyInstaller
- **타겟 플랫폼**: Linux (ubuntu-latest)
- **Artifact**: `coupang_coupon_issuer` 바이너리 (30일 보관)
- **실행 모드 감지**: `is_pyinstaller()` 유틸리티로 자동 감지

### 지원 배포판

Python 3.10+ 요구사항으로 인해 다음 버전 이상에서만 동작합니다:

- **Ubuntu**: 22.04 (Jammy, Python 3.10) 이상
- **Debian**: 12 (Bookworm, Python 3.11) 이상

> ⚠️ Ubuntu 20.04 (Python 3.8), Debian 11 (Python 3.9)는 지원되지 않습니다.

## 프로젝트 구조

### 배포 후 구조 (9컬럼 엑셀)

```
# 사용자 작업 디렉토리 (사용자가 원하는 위치)
~/my-coupons/
├── config.json                  # API 키 + UUID (600 권한)
├── coupons.xlsx                 # 쿠폰 정의 (사용자 배치)
└── issuer.log                   # 실행 로그 (자동 생성)

# 프로젝트 소스 (별도 위치, 예: /opt/coupang_coupon_issuer)
/opt/coupang_coupon_issuer/
├── main.py                      # CLI 진입점
├── src/                         # 소스코드
└── ...
```

**특징**:
- 작업 디렉토리와 소스코드 분리
- 작업 디렉토리는 런타임에 지정 (CLI 인자)
- 디렉토리 이동 시 재설치 필요 (UUID 기반 자동 처리)
- Python 3.10+ 필수

### 개발 디렉토리 구조

```
# 소스코드
main.py                          # CLI 진입점
src/coupang_coupon_issuer/
├── config.py                    # ConfigManager, 경로 해결 함수들
├── coupang_api.py               # Coupang API 클라이언트 (HMAC-SHA256)
├── reader.py                    # 엑셀 파일 읽기 및 검증 (공통 모듈)
├── utils.py                     # 한글 정렬 + PyInstaller 감지 유틸리티
├── issuer.py                    # 쿠폰 발급 로직
├── jitter.py                    # Jitter 스케줄러
└── service.py                   # Cron 설치/제거 (PyInstaller 자동 감지)

# 스크립트
scripts/
└── generate_example.py          # 엑셀 예시 파일 생성 스크립트

# 문서
docs/
├── DEV_LOG.md                   # 작은 결정사항, 관례
├── adr/                         # 아키텍처 결정 기록
│   ├── 001-excel-structure.md  # (대체됨)
│   ├── 002-input-normalization.md
│   ├── 003-api-authentication.md
│   ├── 004-fixed-configuration-values.md
│   ├── 005-systemd-service.md  # (대체됨)
│   ├── 006-contract-id-negative-one.md
│   ├── 007-coupon-issuance-workflow.md
│   ├── 008-cli-restructuring.md  # (대체됨)
│   ├── 009-excel-6-column-structure.md  # (대체됨)
│   ├── 010-crontab-service.md  # (대체됨)
│   ├── 011-jitter-thundering-herd.md
│   ├── 012-xdg-base-directory.md  # (대체됨)
│   ├── 013-pyinstaller-single-binary.md  # (대체됨)
│   ├── 014-script-based-deployment.md  # **현재 구조**
│   ├── 015-option-id-column.md  # **현재 구조**
│   ├── 016-test-layer-separation.md
│   ├── 017-coupon-type-specific-validation.md
│   └── 018-korean-discount-type-names.md
└── coupang/                     # Coupang API 규격 문서
    ├── workflow.md
    ├── parameters-explained.md
    ├── contract-list-api.md     # 계약 목록 조회 API
    └── (각종 API 문서)

# 예시 파일 (9컬럼 구조)
examples/                        # 엑셀 예시 파일 (자동 생성)
├── basic.xlsx                   # 기본 예제
├── comprehensive.xlsx           # 전체 예제
└── edge_cases.xlsx              # 엣지 케이스

# 테스트
tests/
├── conftest.py                  # 공통 fixture (간소화됨)
├── unit/                        # 유닛 테스트 (~147개)
│   ├── test_config.py           # ConfigManager (26개)
│   ├── test_coupang_api.py      # API 클라이언트 (12개)
│   ├── test_reader.py           # 엑셀 읽기/검증 (20개)
│   ├── test_utils.py            # 한글 정렬 + PyInstaller 감지 (21개)
│   ├── test_issuer.py           # 쿠폰 발급 로직 (32개)
│   ├── test_service.py          # Cron 관리 (23개, Linux only)
│   └── test_cli.py              # CLI 명령어 (21개)
├── integration/                 # 통합 테스트 (7개, 신규)
│   ├── conftest.py              # Mock fixtures (Coupang API 모킹)
│   └── test_issue.py            # issue 기능 통합 테스트
├── e2e/                         # E2E 테스트 (24개 × 4 배포판 = 96개)
│   ├── conftest.py              # Docker 인프라
│   ├── test_verify.py
│   ├── test_install.py
│   ├── test_issue.py            # 실제 API 호출
│   └── test_uninstall.py
└── fixtures/                    # 테스트 엑셀 파일
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
- **경로 해결 전략**: base_dir 파라미터 명시적 전달, 기본값은 pwd (Path.cwd())

### 구현 가이드

1. **새로운 기능 구현 전**: 관련 ADR 문서를 먼저 읽어보세요
2. **아키텍처 결정 필요 시**: 새 ADR 작성 후 사용자 승인 받기
3. **작은 변경사항**: DEV_LOG.md에 기록

### CLI 명령어

Python 스크립트 형태로 실행:

```bash
# 0. 시스템 준비 (최초 1회, sudo 필요)
sudo python3 main.py setup
# → Cron 데몬 설치 및 활성화
# → 시스템 전체에 한 번만 실행하면 됨

# 1. 엑셀 파일 검증 및 미리보기 (테이블 형식, coupons.xlsx 고정)
python3 main.py verify [디렉토리]
# 예시:
python3 main.py verify .              # 현재 디렉토리의 coupons.xlsx
python3 main.py verify ~/my-coupons   # ~/my-coupons/coupons.xlsx

# 1-1. 특정 파일 검증 (--file 옵션)
python3 main.py verify --file [파일경로]
# 예시:
python3 main.py verify --file ~/my-coupons/custom.xlsx  # 특정 파일 지정
python3 main.py verify --file ./test.xlsx                # 현재 디렉토리의 test.xlsx
# 주의: --file 옵션은 directory보다 우선함
python3 main.py verify ~/my-coupons --file ./custom.xlsx  # custom.xlsx 사용
# → 9개 컬럼 (쿠폰이름, 쿠폰타입, 유효기간, 할인방식, 할인금액, 할인비율, 발급개수, 총 예산) 출력

# 2. 단발성 쿠폰 발급 (테스트용)
python3 main.py issue [디렉토리]
python3 main.py issue .               # 현재 디렉토리
python3 main.py issue ~/my-coupons    # 특정 디렉토리

# 2-1. Jitter 적용 (Thundering herd 방지)
python3 main.py issue . --jitter-max 60  # 0-60분 랜덤 지연

# 3. 서비스 설치 (cron 등록, sudo 불필요)
python3 main.py install [디렉토리]
# 예시:
python3 main.py install .               # 현재 디렉토리
python3 main.py install ~/my-coupons    # 특정 디렉토리

# 3-1. 옵션으로 인증 정보 제공 (대화형 입력 생략)
python3 main.py install ~/my-coupons \
  --access-key YOUR_KEY \
  --secret-key YOUR_SECRET \
  --user-id YOUR_USER_ID \
  --vendor-id YOUR_VENDOR_ID

# 3-2. 옵션 없이 실행 시 대화형 입력
python3 main.py install ~/my-coupons
# → access key: [입력]
# → secret key: [입력]
# → user id: [입력]
# → vendor id: [입력]

# 3-3. 서비스 설치 (Jitter 활성화)
python3 main.py install ~/my-coupons \
  --jitter-max 60  # 선택사항: 0-60분 랜덤 지연
# → 인증 정보는 대화형으로 입력받음

# 4. 서비스 제거 (cron 제거)
python3 main.py uninstall [디렉토리]
python3 main.py uninstall .           # 현재 디렉토리
python3 main.py uninstall ~/my-coupons

# 서비스 관리
crontab -l                            # 스케줄 확인
tail -f ~/my-coupons/issuer.log       # 로그 확인
```

**주요 변경사항 (ADR 019)**:
- **setup/install 분리**: 시스템 준비(sudo)와 서비스 설치(일반 사용자) 분리
- **파일 권한 정상화**: config.json, 로그 파일이 일반 사용자 소유로 생성
- **명확한 책임 분리**: 시스템 레벨 작업(setup)과 사용자 레벨 작업(install) 구분

**이전 변경사항 (ADR 014)**:
- Python 스크립트 실행: `python3 main.py` (PyInstaller 제거)
- 디렉토리 인자 추가: 작업 디렉토리를 런타임에 지정
- 기본값 pwd: 디렉토리 미지정 시 현재 디렉토리 사용 (기본값: `"."`)
- UUID 기반 추적: 디렉토리 이동 시 재설치 자동 처리
- 로그 위치: 작업 디렉토리 내 issuer.log
- **대화형 입력**: install 시 옵션 미지정 시 대화형으로 입력받음
- **자동 제거**: uninstall 시 config.json 자동 삭제

**Jitter 기능 (ADR 011)**:
- 여러 인스턴스 동시 실행 시 API 부하 분산 (Thundering herd 방지)
- 0-N분 랜덤 지연 (1-120 범위)
- 안전한 폴링 루프 (1초 간격, KeyboardInterrupt 처리)
- 시작/종료 시점만 로그 출력

**PyInstaller 하이브리드 지원 (2024-12-24)**:
- **자동 감지**: `is_pyinstaller()` 유틸리티로 실행 환경 자동 감지
- **이중 모드**: Python 스크립트 또는 PyInstaller 바이너리 모두 지원
- **감지 로직**: `sys.frozen` AND `sys._MEIPASS` 체크 (더 정확한 감지)
- **Cron 등록**:
  - PyInstaller 모드: `/path/to/coupang_coupon_issuer issue /work/dir`
  - 스크립트 모드: `python3 /path/to/main.py issue /work/dir`
- **투명성**: 사용자는 실행 방식을 신경 쓸 필요 없음

### 경로 해결 전략 (base_dir 파라미터 전달)

**ADR 014**: 함수 기반 경로 해결, base_dir를 명시적으로 전달

```python
# config.py
from pathlib import Path
from typing import Optional

def get_base_dir(work_dir: Optional[Path] = None) -> Path:
    """작업 디렉토리 경로 반환 (기본: 현재 디렉토리)"""
    if work_dir is None:
        return Path.cwd().resolve()
    return Path(work_dir).resolve()

def get_config_file(base_dir: Path) -> Path:
    return base_dir / "config.json"

def get_excel_file(base_dir: Path) -> Path:
    return base_dir / "coupons.xlsx"

def get_log_file(base_dir: Path) -> Path:
    return base_dir / "issuer.log"

# ConfigManager 메서드들은 base_dir를 첫 번째 파라미터로 받음
class ConfigManager:
    @staticmethod
    def save_config(base_dir: Path, access_key: str, ...) -> str:
        config_file = get_config_file(base_dir)
        # ...

    @staticmethod
    def load_config(base_dir: Path) -> dict:
        config_file = get_config_file(base_dir)
        # ...
```

**중요**:
- 모든 모듈이 `base_dir` 파라미터를 명시적으로 받음
- 기본값은 `Path.cwd()` (현재 작업 디렉토리)
- PyInstaller 의존성 완전 제거

### config.json 구조 (UUID 포함)

```json
{
  "access_key": "...",
  "secret_key": "...",
  "user_id": "...",
  "vendor_id": "...",
  "installation_id": "a3f8d9c2-4b1e-4a7c-9d3f-8e2b1a5c7d9e"
}
```

**UUID 용도**:
- install 시 생성 (첫 설치 시)
- crontab 주석에 포함: `# coupang_coupon_issuer_job:<uuid>`
- uninstall 시 이 UUID로 항목 검색/삭제
- 재설치 시 기존 UUID 항목 자동 제거 → 새 경로로 재등록

### 디버깅

로그 확인 시:
```bash
# 작업 디렉토리에서 로그 확인
tail -f ~/my-coupons/issuer.log
# 또는
cat ~/my-coupons/issuer.log | grep ERROR
```

에러 스택 트레이스와 함께 파일명:라인번호 포함하여 요청

## 완료 체크리스트

### 핵심 기능
- [x] API 클라이언트 (coupang_api.py)
- [x] HMAC-SHA256 인증 구현
- [x] 엑셀 I/O (7개 컴럼 + 입력 정규화)
- [x] issue() 메서드 실제 로직
- [x] 고정값 설정 (예산, 유효기간, contract_id 등)
- [x] 사용자 입력 오류 용인 로직

### CLI 및 배포
- [x] CLI 구조 재설계 (verify/issue/install/uninstall - 4개 명령어)
- [x] 스크립트 기반 배포 (PyInstaller 제거, ADR 014)
- [x] 런타임 경로 지정 (base_dir 파라미터)
- [x] UUID 기반 cron 추적
- [x] apply → verify 변경 (테이블 형식 출력)
- [x] Cron 기반 스케줄링
- [x] Jitter 기능 (Thundering herd 방지)
- [x] 설치 단순화 (7단계 → 3단계)
- [x] 대화형 입력 (install 시 옵션 미지정 시)
- [x] 제거 시 config.json 자동 삭제
- [x] CredentialManager 레거시 제거

### 문서화
- [x] DEV_LOG (로깅 규칙, 검증 규칙 등)
- [x] ADR 001-014 (아키텍처 결정 기록)
- [x] Coupang API 문서 (workflow, parameters 등)

### 테스트
- [x] 유닛 테스트 재작성 (pytest + requests-mock)
  - **유닛 테스트**: 151개 (27개 skipped - Linux 전용)
  - **테스트 결과** (2024-12-24 - PyInstaller 감지 유틸리티 추가):
    - ✅ test_config.py: 26개 - ConfigManager + UUID + base_dir (100%) **[ADR 014 완료]**
    - ✅ test_coupang_api.py: 12개 - HMAC 인증 (100%)
    - ✅ test_reader.py: 20개 - 엑셀 읽기/검증 (100%)
    - ✅ test_utils.py: 21개 - 한글 정렬 + **PyInstaller 감지** (100%) **[신규]**
    - ✅ test_issuer.py: 32개 - 쿠폰 발급 로직 (100%) **[ADR 015 완료]**
    - ✅ test_jitter.py: 14개 - Jitter 스케줄러 (100%)
    - ✅ test_cli.py: 21개 - verify/issue/install/uninstall 명령어 (100%) **[ADR 014, 015 완료]**
    - ⏸️ test_service.py: 27개 - UUID 기반 cron 관리 (Linux only, skipped on Windows)
  - **커버리지**: 68% (전체), config 94%, api 85%, issuer 80%, jitter 100%, **utils 100%**
  - **테스트 실행**: `uv run pytest tests/unit -v`
  - **커버리지 확인**: `uv run pytest --cov=src/coupang_coupon_issuer`

- [ ] 통합 테스트 재작성 (Docker + Python 스크립트)
  - **통합 테스트**: 24개 기본 테스트 × 4개 배포판 = **96개 자동 실행** (목표)
  - **테스트 파일**:
    - test_verify.py: 6개 - verify 명령어 (엑셀 검증, 출력 형식)
    - test_install.py: 11개 - install 명령어 (config, cron, UUID, jitter)
    - test_uninstall.py: 7개 - uninstall 명령어 (UUID 기반 제거, 파일 보존)
  - **다중 배포판 자동 테스트** (pytest parametrize):
    - Ubuntu 24.04 (Noble, Python 3.12)
    - Ubuntu 22.04 (Jammy, Python 3.10)
    - Debian 13 (Trixie, Python 3.12)
    - Debian 12 (Bookworm, Python 3.11)
  - **핵심 기능** (예정):
    - ~~PyInstaller 빌드 자동화~~ → Python 스크립트 직접 실행
    - PEP 668 대응: 배포판별 `--break-system-packages` 자동 처리
    - Read-only 마운트 (/mnt/src → /app 복사, 보안 강화)
    - 사전 빌드 이미지 재사용 (빌드 1회, 재사용으로 속도 대폭 개선)
  - **테스트 환경**: Docker Desktop 필요 (WSL2 backend)
  - **테스트 실행**: `uv run pytest tests/integration -v -m integration`
  - **테스트 시간 (예상)**:
    - ~~첫 실행 (PyInstaller 빌드): 약 6-7분~~ → 첫 실행: 약 1-2분
    - 이후 실행: 약 1-2분 (96개 테스트)
  - **E2E 검증**: 수동 테스트로 대체 (Ubuntu 22.04)
  - ⚠️ **알려진 이슈**: verify/issue 명령어 integration/e2e 테스트 오류 (향후 수정 예정)

### 향후 작업
- [x] 핵심 코드 PyInstaller 제거 (config, main, service, issuer)
- [x] test_config.py 업데이트 (26개)
- [x] test_utils.py 업데이트 (21개) - **PyInstaller 감지 유틸리티 추가**
- [x] ADR 014 문서화
- [x] ADR 015 문서화 (옵션ID 컴럼)
- [x] ADR 016 문서화 (테스트 레이어 분리)
- [x] test_issuer.py 업데이트 (32개) - ADR 015 반영
- [x] test_cli.py 업데이트 (21개) - ADR 014, 015 반영
- [x] test_jitter.py 업데이트 (14개)
- [x] test_reader.py 업데이트 (20개)
- [x] CLAUDE.md 업데이트
- [x] **PyInstaller 하이브리드 지원** - `is_pyinstaller()` 유틸리티 (2024-12-24)
- [ ] test_service.py 업데이트 (~27개, Linux 환경 필요)
- [ ] 통합 테스트 간소화 (PyInstaller 빌드 제거)
- [ ] **verify/issue 통합/E2E 테스트 오류 수정** (향후 작업)
- [ ] 수동 E2E 검증 (Ubuntu 22.04)
- [ ] 성능 최적화 (병렬 처리, 선택사항)

## 테스트 가이드

### 테스트 구조

```
tests/
├── conftest.py                  # 공통 fixture (PyInstaller mock 포함)
├── fixtures/                    # 테스트용 엑셀 파일
│   ├── sample_valid.xlsx
│   ├── sample_invalid_columns.xlsx
│   ├── sample_invalid_rates.xlsx
│   └── sample_invalid_prices.xlsx
├── unit/                        # 유닛 테스트 (121개)
│   ├── test_config.py           # ConfigManager + UUID 테스트 (33개)
│   ├── test_coupang_api.py      # API 클라이언트 + HMAC (12개)
│   ├── test_issuer.py           # 쿠폰 발급 로직 (32개)
│   ├── test_service.py          # Cron 관리 (UUID 기반, 23개, Linux only)
│   └── test_cli.py              # CLI 명령어 (21개 - verify/issue/install/uninstall)
└── integration/                 # 통합 테스트 (24개 × 4 배포판 = 96개)
    ├── conftest.py              # Docker + PyInstaller 인프라
    ├── test_verify.py           # verify 명령어 (6개)
    ├── test_install.py          # install 명령어 (11개)
    └── test_uninstall.py        # uninstall 명령어 (7개)
```

### 테스트 실행 명령어

```bash
# 유닛 테스트 (Windows 호환, 빠름)
uv run pytest tests/unit -v

# 통합 테스트 (Windows 호환, 빠름, 외부 API 모킹)
uv run pytest tests/integration -v -m integration

# E2E 테스트 (Docker Desktop 필요, 느림, 실제 API 호출)
uv run pytest tests/e2e -v -m e2e

# 전체 테스트
uv run pytest -v

# 커버리지 포함
uv run pytest tests/unit tests/integration --cov=src/coupang_coupon_issuer --cov-report=html

# 특정 파일만
uv run pytest tests/unit/test_issuer.py -v
```

### Windows vs Linux 테스트

- **유닛 테스트**:
  - Windows 환경: 121개 중 98개 실행 (service.py 23개 스킵)
  - Linux 환경: 121개 전부 실행 가능
- **통합 테스트**:
  - Windows/Linux: 7개 모두 실행 가능 (외부 API 모킹)
- **E2E 테스트**:
  - Windows: Docker Desktop(WSL2) 필요
  - Linux: Docker만 필요
  - **다중 배포판 테스트**: 24개 × 4개 배포판 = 96개 자동 실행
  - **테스트 시간**: 약 2-3분 (사전 빌드 이미지 재사용 시)

### 테스트 Fixture

**유닛 테스트 Fixture** (tests/conftest.py):
```python
@pytest.fixture
def mock_config_paths(tmp_path):
    """작업 디렉토리 (더 이상 PyInstaller 모킹 불필요)"""
    return tmp_path

# ADR 014: PyInstaller 관련 fixture 제거됨
# - mock_frozen 삭제 (더 이상 sys.frozen 체크 없음)
# - 경로 모킹 불필요 (base_dir 직접 전달)
```

**통합 테스트 Fixture** (tests/integration/conftest.py) - **업데이트 필요**:
```python
@pytest.fixture(scope="session", params=[
    "ubuntu:24.04",  # Noble Numbat, Python 3.12
    "ubuntu:22.04",  # Jammy Jellyfish, Python 3.10
    "debian:13",     # Trixie, Python 3.12
    "debian:12",     # Bookworm, Python 3.11
])
def test_image(request):
    """다중 배포판 자동 테스트 (pytest parametrize)"""
    base_image = request.param
    return get_or_build_image(base_image)  # 사전 빌드 이미지 재사용

@pytest.fixture
def test_container(test_image):
    """Docker 컨테이너 + Python 환경"""
    container = DockerContainer(test_image)
    # Read-only mount (보안 강화)
    container.with_volume_mapping(str(project_root), "/app", mode="ro")
    container.start()

    # 의존성 설치 (pip install -e .)
    container.exec(["bash", "-c", "cd /app && pip3 install -e ."])

    # Start cron service
    container.exec(["service", "cron", "start"])
    return container

# ADR 014: PyInstaller 빌드 fixture 제거
# - built_binary 삭제 (더 이상 PyInstaller 빌드 불필요)
# - python3 /app/main.py 직접 실행
```

### 테스트 작성 규칙

1. **Mock 사용**
   - requests-mock: HTTP API 호출
   - pytest-mock: 일반 객체 모킹
   - ~~monkeypatch: PyInstaller 환경 시뮬레이션~~ (ADR 014에서 제거)

2. **Fixture 활용** (유닛 테스트)
   - `mock_config_paths`: 작업 디렉토리 (tmp_path 반환)
   - ~~`mock_frozen`: PyInstaller 환경 시뮬레이션~~ (제거됨)
   - `valid_excel`: 유효한 6컬럼 엑셀
   - `mock_coupang_api`: Coupang API 응답 모킹

3. **Fixture 활용** (통합 테스트)
   - `test_image`: 다중 배포판 자동 테스트 (pytest parametrize)
   - `test_container`: Docker 컨테이너 + Python 환경
   - ~~`built_binary`: PyInstaller 빌드 자동화~~ (제거 예정)
   - `clean_install_dir`: 깨끗한 설치 디렉토리
   - `container_exec`: 컨테이너 명령어 실행 헬퍼
   - `sample_excel`: 샘플 엑셀 파일 생성

4. **테스트 마커**
   - `@pytest.mark.unit`: 유닛 테스트
   - `@pytest.mark.integration`: 통합 테스트 (Docker 필요)
   - `@pytest.mark.slow`: 느린 테스트 (> 1초)
   - Windows 스킵: `pytestmark = pytest.mark.skipif(os.name == 'nt', ...)` 사용

5. **Docker 통합 테스트 특징** (업데이트 예정)
   - **사전 빌드 이미지 재사용**: 한 번 빌드하면 재사용 (빌드 시간 대폭 단축)
   - **PEP 668 자동 처리**: 배포판별로 적절한 pip 명령어 사용
   - **Read-only 마운트**: 소스코드 보안 강화 (직접 /app 마운트)
   - ~~**PyInstaller 빌드 자동화**~~ → Python 스크립트 직접 실행
   - **Cron 서비스 자동 시작**: 각 컨테이너마다 cron 서비스 실행
   - **UUID 기반 테스트**: installation_id 검증, 재설치 시나리오

## CI/CD (GitHub Actions)

### 자동 빌드 워크플로우

GitHub Actions를 통해 PyInstaller 기반 단일 실행 파일을 자동으로 빌드합니다.

**워크플로우 파일**: `.github/workflows/build.yml`

**트리거**:
- `main` 브랜치에 push 시
- 수동 실행 (workflow_dispatch)

**빌드 과정**:
```yaml
1. Checkout code
2. Install uv (latest)
3. Install dependencies (uv sync --group build)
4. Build executable (uv run pyinstaller --paths src --name coupang_coupon_issuer --onefile main.py)
5. Upload artifact (dist/coupang_coupon_issuer)
```

**Artifact 다운로드**:
- GitHub Actions 페이지 → 워크플로우 실행 → Artifacts
- 파일명: `coupang_coupon_issuer-linux`
- 보관 기간: 30일

**의존성 그룹** (`pyproject.toml`):
```toml
[dependency-groups]
build = ["pyinstaller"]
dev = ["pytest", "pytest-cov", ...]
```

**빌드 명령어** (로컬):
```bash
# 의존성 설치
uv sync --group build

# 빌드 실행
uv run pyinstaller --paths src --name coupang_coupon_issuer --onefile main.py

# 결과물 확인
ls -lh dist/coupang_coupon_issuer
```

## 배포 가이드 (스크립트 기반)

**ADR 014**: Python 스크립트로 직접 실행

```bash
# 1. Clone repository
git clone <repository-url>
cd coupang_coupon_issuer

# 2. Install dependencies (uv)
uv sync

# 3. 개발 모드 실행
uv run python main.py verify tests/fixtures/
uv run python main.py issue tests/fixtures/

# 4. 엑셀 예시 생성 (선택사항)
uv run python scripts/generate_example.py
# → examples/ 디렉토리에 3개 예제 파일 생성
#    - basic.xlsx: 기본 예제 (2개 쿠폰)
#    - comprehensive.xlsx: 전체 예제 (6개 쿠폰)
#    - edge_cases.xlsx: 엣지 케이스 (7개 쿠폰)
```

### 엑셀 예시 파일 생성

프로젝트에는 엑셀 포맷 예시를 생성하는 스크립트가 포함되어 있습니다:

```bash
# 예제 파일 생성
uv run python scripts/generate_example.py
```

생성되는 파일 (`examples/` 디렉토리):
- **basic.xlsx**: 즉시할인/다운로드쿠폰 기본 예제 2개
- **comprehensive.xlsx**: 모든 쿠폰 타입과 할인 방식 조합 6개
- **edge_cases.xlsx**: 최소/최대값, 다중 옵션 등 7개

**비전문가 사용자를 위한 기능**:
- **헤더 주석**: 각 컬럼에 마우스 오버 시 상세 설명 표시
  - "10% 할인 → 10 입력 (% 기호 없이)"
  - "1000원 할인 → 1000 입력 (원 없이)"
  - 쿠폰 타입별 차이점 명시
- **데이터 유효성 검사**: 드롭다운, 숫자 범위 제한
  - 쿠폰타입/할인방식: 드롭다운 선택
  - 쿠폰유효기간: 1~365 정수
  - 공통 제약만 적용 (세부 검증은 실행 시)

각 Excel 파일은 9개 컬럼 구조를 따릅니다 (ADR 021):
1. 쿠폰이름
2. 쿠폰타입 (즉시할인 / 다운로드쿠폰)
3. 쿠폰유효기간 (일 단위)
4. 할인방식 (정률할인 / 정액할인 / 수량별 정액할인) - **한글 입력**
5. 할인금액/비율
6. **최소구매금액** (다운로드쿠폰 전용, 비어있으면 기본값 1원)
7. **최대할인금액** (필수, 정률할인 시 최대 할인 금액)
8. 발급개수 (다운로드쿠폰 전용)
9. 옵션ID (쉼표로 구분)

# 3. 작업 디렉토리 생성
mkdir ~/my-coupons
cp coupons.xlsx ~/my-coupons/

# 4. 서비스 설치 (대화형 입력)
python3 main.py install ~/my-coupons
# → access key: [입력]
# → secret key: [입력]
# → user id: [입력]
# → vendor id: [입력]

# 5. 로그 확인
tail -f ~/my-coupons/issuer.log
```
