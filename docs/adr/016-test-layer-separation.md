# ADR 016: 테스트 계층 분리 (Unit / Integration / E2E)

**상태**: 제안됨  
**날짜**: 2024-12-22  

## 배경

현재 테스트 구조는 다음과 같습니다:

```
tests/
├── unit/           # 유닛 테스트 (~115개)
└── integration/    # "통합 테스트" (24개 × 4 배포판 = 96개)
```

그러나 `tests/integration/`의 실제 내용을 보면:
- Docker 컨테이너에서 전체 애플리케이션 실행
- 실제 Coupang API 호출 (`.env`에서 credentials 로드)
- 전체 시스템 플로우 검증 (verify/install/issue/uninstall)
- 실제 파일 시스템, cron, 로그 파일 검증

이는 **E2E(End-to-End) 테스트**의 정의에 부합하며, 진짜 **통합 테스트**가 부재한 상황입니다.

### 문제점

1. **테스트 계층 혼란**: "integration"이라는 이름이 실제 테스트 범위와 불일치
2. **통합 테스트 부재**: 외부 의존성을 모킹한 기능 단위 테스트가 없음
3. **테스트 갭**: Unit과 E2E 사이의 중간 계층이 없어 디버깅 어려움

### 통합 테스트의 필요성

특히 `issue` 기능은 다음과 같은 복잡한 플로우를 가집니다:

```
cmd_issue() 
  → ConfigManager.load_credentials()
  → CouponIssuer.__init__()
  → CouponIssuer.issue()
    → _fetch_coupons_from_excel()
    → _issue_single_coupon() (각 쿠폰마다)
      → CoupangAPIClient.issue_instant_coupon() 또는
      → CoupangAPIClient.issue_download_coupon()
```

이 플로우를 검증하려면:
- **Unit 테스트**: 각 함수를 독립적으로 테스트 (이미 존재)
- **통합 테스트**: 전체 플로우를 모킹된 외부 의존성과 함께 테스트 (**부재**)
- **E2E 테스트**: 실제 API와 함께 전체 시스템 테스트 (현재 "integration"으로 잘못 명명됨)

## 결정

테스트를 3계층으로 명확히 분리합니다:

### 1. Unit Tests (`tests/unit/`)

**범위**: 개별 함수/클래스 단위 테스트  
**의존성**: 모든 외부 의존성 모킹  
**실행 환경**: 로컬 (Windows/Linux 모두)  
**속도**: 매우 빠름 (~1초)  

**변경 사항**: 없음 (기존 유지)

### 2. Integration Tests (`tests/integration/`) - **신규**

**범위**: 기능 단위 통합 테스트  
**의존성**: 외부 API만 모킹, 내부 모듈은 실제 사용  
**실행 환경**: 로컬 (Windows/Linux 모두)  
**속도**: 빠름 (~5초)  

**테스트 대상**:
- `issue` 기능의 전체 플로우
  - `cmd_issue()` 호출
  - Excel 파싱 → 쿠폰 발급 로직 → API 호출 (모킹)
  - 에러 처리, Jitter 기능 등

**모킹 대상**:
- `CoupangAPIClient.issue_instant_coupon()` - 예상 응답 반환
- `CoupangAPIClient.issue_download_coupon()` - 예상 응답 반환
- `ConfigManager.load_credentials()` - 테스트용 credentials 반환
- Excel 파일 - 실제 테스트 Excel 파일 사용 또는 `_fetch_coupons_from_excel()` 모킹

**테스트 케이스** (예상 ~5개):
1. `test_issue_instant_coupon_success`: 즉시할인 쿠폰 발급 성공
2. `test_issue_download_coupon_success`: 다운로드 쿠폰 발급 성공
3. `test_issue_mixed_coupons`: 여러 쿠폰 타입 혼합 발급
4. `test_issue_api_error_handling`: API 에러 시 적절한 처리
5. `test_issue_with_jitter`: Jitter 기능 포함 테스트

### 3. E2E Tests (`tests/e2e/`) - **이름 변경**

**범위**: 전체 시스템 E2E 테스트  
**의존성**: 실제 Coupang API, 실제 파일 시스템, 실제 cron  
**실행 환경**: Docker (4개 배포판)  
**속도**: 느림 (~2-3분, Docker 빌드 포함)  

**변경 사항**:
- `tests/integration/` → `tests/e2e/`로 디렉토리 이름 변경
- 모든 테스트 파일에서 `@pytest.mark.integration` → `@pytest.mark.e2e`
- `pytest.ini`에서 마커 업데이트

**테스트 내용**: 변경 없음 (기존 유지)

## 구현

### 디렉토리 구조

```
tests/
├── unit/                        # 유닛 테스트 (~115개)
│   ├── test_config.py
│   ├── test_coupang_api.py
│   ├── test_issuer.py
│   ├── test_service.py
│   └── test_cli.py
├── integration/                 # 통합 테스트 (~5개) - 신규
│   ├── conftest.py             # Mock fixtures
│   └── test_issue.py           # issue 기능 통합 테스트
└── e2e/                        # E2E 테스트 (24개 × 4 = 96개) - 이름 변경
    ├── conftest.py             # Docker fixtures
    ├── test_verify.py
    ├── test_install.py
    ├── test_issue.py           # 실제 API 호출
    └── test_uninstall.py
```

### pytest.ini 업데이트

```ini
[pytest]
markers =
    unit: Unit tests
    integration: Integration tests with mocked external dependencies
    e2e: E2E tests requiring Docker and real API credentials
    slow: Slow tests (> 1 second)
```

### 테스트 실행 명령어

```bash
# Unit 테스트 (빠름, 로컬)
uv run pytest tests/unit -v

# Integration 테스트 (빠름, 로컬)
uv run pytest tests/integration -v -m integration

# E2E 테스트 (느림, Docker 필요)
uv run pytest tests/e2e -v -m e2e

# 전체 테스트
uv run pytest -v
```

## 결과

### 긍정적

1. **명확한 테스트 계층**: Unit → Integration → E2E 순서로 명확한 분리
2. **빠른 피드백**: Integration 테스트로 외부 API 없이 기능 검증 가능
3. **디버깅 용이**: 문제 발생 시 어느 계층에서 실패했는지 명확
4. **CI/CD 최적화**: 빠른 테스트(Unit + Integration)를 먼저 실행, E2E는 선택적
5. **개발 생산성**: 로컬에서 외부 API 없이 기능 개발 및 검증 가능

### 부정적

1. **테스트 코드 증가**: Integration 테스트 추가로 유지보수 대상 증가
2. **모킹 복잡성**: 적절한 모킹 전략 필요

### 마이그레이션

1. `tests/integration/` → `tests/e2e/` 이름 변경
2. 모든 e2e 테스트 파일에서 마커 변경
3. `pytest.ini` 업데이트
4. 새로운 `tests/integration/` 생성 및 테스트 작성
5. `CLAUDE.md` 문서 업데이트

## 고려된 대안

### 1. 현재 구조 유지
- **장점**: 변경 없음
- **단점**: 테스트 계층 혼란 지속, 통합 테스트 부재

### 2. Integration 테스트만 추가 (이름 변경 없음)
- **장점**: 기존 테스트 영향 최소화
- **단점**: "integration"이 두 가지 의미로 사용되어 혼란

### 3. E2E 테스트를 "system" 또는 "acceptance"로 명명
- **장점**: 다른 명명 규칙
- **단점**: E2E가 업계 표준 용어

## 참조

- [Testing Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- ADR 014: 스크립트 기반 배포 (통합 테스트 간소화 관련)
- 현재 테스트 구조: `tests/unit/`, `tests/integration/` (실제로는 E2E)
