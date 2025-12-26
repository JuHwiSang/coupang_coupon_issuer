# 개발자 가이드

> 다른 개발자가 프로젝트를 이해하고 유지보수할 수 있도록 작성된 문서입니다.

---

## 프로젝트 개요

매일 자정에 자동으로 쿠팡 쿠폰을 발급하는 Python 기반 cron 서비스입니다.

**핵심 기술 스택**:
- Python 3.10+
- Linux cron
- Coupang Open API
- openpyxl (Excel 처리)

---

## 프로젝트 철학

이 프로젝트의 핵심 가치는 **"심플함"**입니다.

**왜 심플하게?**
- 비개발자가 리눅스 환경에서 사용한다는 전제
- 프로그래밍 지식 없이도 쉽게 설치하고 사용할 수 있어야 함
- 복잡한 설정이나 분산된 파일 관리는 사용자에게 큰 부담

**핵심 원칙**:
- ✅ **비개발자 친화적**: 프로그램 파일 하나 + 엑셀 파일 하나로 간편하게 사용
- ✅ **한 폴더에 모든 것**: 복잡한 설정 없이 모든 파일을 한 곳에 집중
- ✅ **쉬운 설치**: `setup` 명령어로 cron 자동 설치
- ✅ **단일 실행 파일**: PyInstaller로 빌드하여 의존성 걱정 없이 배포
- ✅ **분산되지 않음**: "여기 설치, 저기 복사" 같은 복잡한 과정 없음

---

## 개발 환경 설정

```bash
# 1. 저장소 클론
git clone <repository-url>
cd coupang_coupon_issuer

# 2. 의존성 설치 (개발 도구 포함)
uv sync --group dev

# 3. 테스트 실행
uv run pytest tests/unit -v
```

**필수 도구**:
- Python 3.10+
- uv (패키지 관리)

**선택 도구**:
- Docker (E2E 테스트 실행 시 필요)

---

## 프로젝트 구조

```
src/coupang_coupon_issuer/
├── config.py          # ConfigManager, 경로 관리, UUID 기반 설치 추적
├── coupang_api.py     # Coupang API 클라이언트, HMAC-SHA256 인증
├── reader.py          # 엑셀 파일 읽기 및 검증 (공통 모듈)
├── issuer.py          # 쿠폰 발급 핵심 로직, contractId 조회
├── service.py         # Cron 설치/제거, setup/install/uninstall
├── jitter.py          # Thundering herd 방지 (랜덤 지연)
└── utils.py           # 한글 정렬, PyInstaller 감지 유틸리티

main.py                # CLI 진입점 (verify/issue/setup/install/uninstall)

tests/
├── unit/              # 유닛 테스트 (~151개, 68% 커버리지)
├── integration/       # 통합 테스트 (계획 중)
└── e2e/               # E2E 테스트 (계획 중)

docs/
├── DEV_LOG.md         # 개발 로그, 규칙 (시간순 작성)
├── adr/               # 아키텍처 결정 기록 (ADR 001-022)
└── coupang/           # Coupang API 문서

examples/              # 엑셀 예시 파일 (스크립트로 생성)
scripts/               # 개발 도구 (엑셀 생성 등)
```

### 핵심 파일 설명

- **`config.py`**: 작업 디렉토리 경로 관리, UUID 기반 설치 추적
- **`coupang_api.py`**: HMAC-SHA256 인증, API 호출 래퍼
- **`reader.py`**: 9컬럼 엑셀 읽기/검증, 한글 할인방식 매핑
- **`issuer.py`**: 쿠폰 발급 워크플로우, contractId 동적 조회
- **`service.py`**: Cron 설치/제거, setup/install 명령어 구현

---

## 배포 환경

### PyInstaller 빌드 배포 (권장)

**장점**:
- Python 설치 불필요
- 의존성 걱정 없음
- 모든 Linux 배포판에서 실행 가능

**요구사항**:
- Linux OS (cron 지원)

### Python 스크립트 직접 실행

**요구사항**:
- Linux OS (cron 지원)
- Python 3.10+
- 의존성: requests, openpyxl

**지원 배포판** (Python 3.10+ 요구사항으로 인해):
- Ubuntu 22.04 (Jammy, Python 3.10) 이상
- Debian 12 (Bookworm, Python 3.11) 이상

---

## 테스트

### 유닛 테스트

```bash
# 전체 유닛 테스트
uv run pytest tests/unit -v

# 커버리지 포함
uv run pytest tests/unit --cov=src/coupang_coupon_issuer --cov-report=html

# 특정 파일만
uv run pytest tests/unit/test_issuer.py -v
```

**현재 상태** (2025-12-27):
- 유닛 테스트: ~151개
- 커버리지: 68% (전체), config 94%, api 85%, issuer 80%
- Windows에서 실행 시 27개 스킵 (Linux 전용 test_service.py)

### 통합 테스트 / E2E 테스트

```bash
# 통합 테스트 (일부 오류 있음)
uv run pytest tests/integration -v -m integration

# E2E 테스트 (일부 오류 있음)
uv run pytest tests/e2e -v -m e2e
```

---

## 현재 TODO 및 알려진 이슈

### 🚧 수정 필요

- [ ] **통합 테스트 수정 필요**: verify/issue 명령어 오류
- [ ] **E2E 테스트 수정 필요**: verify/issue 명령어 오류
- [ ] **test_service.py**: Linux 환경에서 실행 필요 (Windows에서 스킵됨)

### 📝 향후 작업

- [ ] **ADR 020**: 즉시할인쿠폰 REQUESTED 상태 폴링 → async 리팩토링
  - 현재: 간단한 5회 × 2초 폴링 (덕테이프 솔루션)
  - 목표: 비동기 처리로 개선

### ✅ 최근 완료

- [x] Excel 9컬럼 구조 (최소구매금액/최대할인금액 추가)
- [x] KST timezone 처리 (다운로드쿠폰 타이밍)
- [x] setup/install 명령어 분리 (시스템/사용자 레벨)
- [x] 한글 할인방식 입력 지원 (정률할인/정액할인/수량별 정액할인)

---

## 핵심 문서

프로젝트의 모든 결정사항과 규칙은 문서화되어 있습니다:

- **[CLAUDE.md](../CLAUDE.md)** - AI 개발 가이드 (매우 상세)
  - 프로젝트 구조, ADR 목록, API 문서
  - 테스트 가이드, 배포 전략, CI/CD
  
- **[docs/DEV_LOG.md](DEV_LOG.md)** - 개발 로그, 규칙
  - ⚠️ 순서가 다소 뒤죽박죽할 수 있음 (시간순 작성이 아님)
  - 작은 결정사항, 코딩 규칙, 관례
  
- **[docs/adr/](adr/)** - 아키텍처 결정 기록
  - ADR 001-022: 중요한 아키텍처 결정사항
  - 각 ADR은 독립적인 문서로 관리
  
- **[docs/coupang/](coupang/)** - Coupang API 문서
  - API 규격, 워크플로우, 파라미터 설명

---

## PyInstaller 빌드 (선택사항)

단일 실행 파일로 배포하려면:

```bash
# 빌드 의존성 설치
uv sync --group build

# PyInstaller 빌드
uv run pyinstaller --paths src --name coupang_coupon_issuer --onefile main.py

# 결과물 확인
./dist/coupang_coupon_issuer --help
```

**GitHub Actions 자동 빌드**:
- `main` 브랜치 push 시 자동 실행
- Artifact: `coupang_coupon_issuer-linux` (30일 보관)
- 수동 실행: Actions 탭 → Build Executable → Run workflow

---

**마지막 업데이트**: 2025-12-27
