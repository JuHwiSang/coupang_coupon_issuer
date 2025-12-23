# 테스트 가이드

## 개요

프로젝트는 pytest를 기반으로 유닛 테스트와 통합 테스트로 구성됩니다.

## 테스트 구조

```
tests/
├── conftest.py                   # 공통 fixture
├── fixtures/                     # 테스트용 파일
│   ├── sample_valid.xlsx
│   ├── sample_invalid_columns.xlsx
│   ├── sample_invalid_rates.xlsx
│   └── sample_invalid_prices.xlsx
├── unit/                         # 유닛 테스트 (105개, 27개 skipped)
│   ├── test_config.py            # ConfigManager 테스트 (25개)
│   ├── test_coupang_api.py       # API 클라이언트 + HMAC (15개)
│   ├── test_issuer.py            # 쿠폰 발급 로직 (31개)
│   ├── test_jitter.py            # Jitter 스케줄러 (14개)
│   ├── test_service.py           # Cron 관리 (27개, Linux only)
│   └── test_cli.py               # CLI 명령어 (20개)
├── integration/                  # 통합 테스트 (7개, 외부 API 모킹)
│   ├── conftest.py               # Mock fixtures
│   └── test_issue.py            # issue 기능 통합 테스트
└── e2e/                         # E2E 테스트 (24개, Docker 필요)
    ├── conftest.py               # Docker 인프라
    ├── test_verify.py
    ├── test_install.py
    ├── test_issue.py
    └── test_uninstall.py
```

## 실행 방법

### 전체 테스트 실행

```bash
# 기본 실행
uv run pytest

# 상세 출력
uv run pytest -v

# 특정 디렉토리만
uv run pytest tests/unit -v
```

### 커버리지 확인

```bash
# 터미널에 표시
uv run pytest --cov=src/coupang_coupon_issuer --cov-report=term-missing

# HTML 리포트 생성
uv run pytest --cov=src/coupang_coupon_issuer --cov-report=html
# htmlcov/index.html 열기
```

### 특정 테스트만 실행

```bash
# 파일 단위
uv run pytest tests/unit/test_config.py

# 클래스 단위
uv run pytest tests/unit/test_config.py::TestCredentialManagerSave

# 함수 단위
uv run pytest tests/unit/test_config.py::TestCredentialManagerSave::test_save_credentials_writes_json

# 패턴 매칭
uv run pytest -k "credential"
```

### 마커 사용

```bash
# 유닛 테스트만
uv run pytest -m unit

# 느린 테스트 제외
uv run pytest -m "not slow"
```

## 플랫폼별 테스트

### Windows 환경

**유닛 테스트:**
- service.py 테스트는 자동 스킵 (Linux 전용)
- 예상 결과: 105/105 (27개 스킵)

```bash
uv run pytest tests/unit -v
```

**통합 테스트:**
- Docker Desktop 필요 (WSL2 backend)
- 예상 결과: 20/20 통과 (103초)

```bash
uv run pytest tests/integration -v -m integration
```

### Linux 환경

**유닛 테스트:**
- 모든 테스트 실행 가능
- 예상 결과: 132/132 통과 (105 unit + 27 service)

```bash
uv run pytest tests/unit -v
```

**통합 테스트:**
- Docker만 필요
- 예상 결과: 20/20 통과

```bash
uv run pytest tests/integration -v -m integration
```

## 주요 Fixture

### conftest.py에 정의된 공통 fixture

```python
@pytest.fixture
def temp_credentials(tmp_path):
    """임시 credentials.json 파일"""
    # 테스트용 API 키 포함

@pytest.fixture
def valid_excel(tmp_path):
    """유효한 6컬럼 엑셀 파일"""
    # 테스트용 쿠폰 데이터 포함 (ADR 009)

@pytest.fixture
def mock_coupang_api(requests_mock):
    """Coupang API 응답 모킹"""
    # 즉시할인/다운로드쿠폰 API 모킹
```

## 테스트 작성 규칙

### 1. Mock 사용

```python
# HTTP API 호출 모킹
def test_api_call(requests_mock):
    requests_mock.post("https://api.example.com", json={"result": "ok"})
    # 테스트 코드

# 일반 객체 모킹
def test_function(mocker):
    mocker.patch('module.function', return_value="mocked")
    # 테스트 코드
```

### 2. 임시 파일 사용

```python
def test_file_operation(tmp_path):
    # tmp_path는 자동으로 정리되는 임시 디렉토리
    test_file = tmp_path / "test.xlsx"
    # 파일 작업
```

### 3. Windows/Linux 호환성

```python
# 파일 경로 비교 시 Path 객체 사용
from pathlib import Path

def test_path():
    expected = Path("/etc/config.json")
    assert actual == expected or actual.as_posix() == "/etc/config.json"

# Linux 전용 테스트
import pytest
import os

pytestmark = pytest.mark.skipif(os.name == 'nt', reason="Linux only")
```

## 통합 테스트 (testcontainers)

### 환경

- Ubuntu 22.04 + cron in Docker container
- testcontainers-python 라이브러리 사용
- privileged mode 불필요 (cron 기반)

### Fixture 구조

1. **cron_container** (session scope)
   - Ubuntu 22.04 컨테이너 생성
   - cron, Python 3, pip 자동 설치
   - 프로젝트 코드 /app에 마운트

2. **clean_container** (function scope)
   - 각 테스트 전 정리 (crontab, 파일)

3. **container_exec**
   - `["bash", "-c", "command"]` 형식으로 쉘 기능 지원
   - exit code와 stdout 반환

4. **installed_service**
   - 서비스 설치 상태 제공

5. **test_excel_file**
   - 테스트용 6컬럼 엑셀 생성

### 실행 결과 (2024-12-19)

- **테스트 개수**: 20개
- **통과율**: 100%
- **실행 시간**: 103초
- **환경**: Docker Desktop (WSL2 backend on Windows)

## 커버리지 목표

### 현재 커버리지

| 모듈 | 유닛 테스트 | 통합 테스트 | 상태 |
|------|------------|------------|------|
| config.py | 94% | - | ✅ |
| coupang_api.py | 85% | - | ✅ |
| issuer.py | 80% | - | ✅ |
| jitter.py | 100% | - | ✅ |
| cli (main.py) | - | 간접 검증 | ✅ |
| service.py | Linux만 | 100% | ✅ |

### 목표

- 유닛 테스트: 80% 이상
- 핵심 모듈 (config, api, issuer): 90% 이상
- 통합 테스트: 주요 워크플로우 커버

## 문제 해결

### 테스트 실패 시

1. **Import 오류**
   ```bash
   # sys.path 확인
   python -c "import sys; print('\n'.join(sys.path))"
   ```

2. **Mock 설정 오류**
   ```python
   # patch 경로 확인: 사용되는 곳을 패치
   # ❌ mocker.patch('os.path.exists')
   # ✅ mocker.patch('mymodule.os.path.exists')
   ```

3. **Windows에서 service 테스트 실패**
   - 정상 동작: service.py는 Linux 전용
   - pytestmark로 자동 스킵됨

### 디버깅

```bash
# 실패한 테스트만 재실행
uv run pytest --lf

# 첫 번째 실패에서 중단
uv run pytest -x

# 상세 오류 출력
uv run pytest -vv --tb=long

# pdb 디버거 사용
uv run pytest --pdb
```

## CI/CD 통합

### GitHub Actions 예시

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync --extra test
      - name: Run tests
        run: uv run pytest --cov=src/coupang_coupon_issuer
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## 추가 리소스

- [pytest 공식 문서](https://docs.pytest.org/)
- [requests-mock 문서](https://requests-mock.readthedocs.io/)
- [freezegun 문서](https://github.com/spulec/freezegun)
- [pytest-cov 문서](https://pytest-cov.readthedocs.io/)
