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
└── unit/
    ├── test_config.py            # CredentialManager 테스트 (17개)
    ├── test_coupang_api.py       # API 클라이언트 + HMAC (12개)
    ├── test_issuer.py            # 쿠폰 발급 로직 (23개)
    ├── test_scheduler.py         # 0시 스케줄러 (14개)
    ├── test_service.py           # systemd 관리 (12개, Linux only)
    └── test_cli.py               # CLI 명령어 (20개)
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

- service.py 테스트는 자동 스킵 (Linux 전용)
- 예상 결과: 79 passed, 12 skipped, 6 failed

```bash
uv run pytest tests/unit -v
```

### Linux 환경

- 모든 테스트 실행 가능
- service.py 테스트 포함

```bash
uv run pytest tests/unit -v
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
    """유효한 5컬럼 엑셀 파일"""
    # 테스트용 쿠폰 데이터 포함

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

# 시간 모킹 (scheduler 테스트)
from freezegun import freeze_time

@freeze_time("2024-12-17 00:00:00")
def test_midnight():
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

## 커버리지 목표

### 현재 커버리지 (Windows 기준)

| 모듈 | 커버리지 | 상태 |
|------|----------|------|
| config.py | 100% | ✅ |
| coupang_api.py | 98% | ✅ |
| issuer.py | 92% | ✅ |
| scheduler.py | 91% | ✅ |
| cli (main.py) | - | ✅ |
| service.py | 9% | ⏭️ Linux에서 테스트 |

**전체**: 69%

### 목표

- 유닛 테스트: 80% 이상
- 핵심 모듈 (config, api, issuer): 90% 이상

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
