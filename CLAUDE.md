# Claude 개발 가이드

매일 0시에 자동으로 쿠폰을 발급하는 Linux systemd 서비스

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
- [ADR 001: 엑셀 입력 구조](docs/adr/001-excel-structure.md) - 5개 컬럼 구조, 파일 위치, 고정값
- [ADR 002: 입력 정규화](docs/adr/002-input-normalization.md) - 사용자 입력 오류 용인 로직
- [ADR 003: API 인증](docs/adr/003-api-authentication.md) - HMAC-SHA256 서명 생성
- [ADR 004: 고정 설정값](docs/adr/004-fixed-configuration-values.md) - contract_id, 예산 등
- [ADR 005: systemd 서비스](docs/adr/005-systemd-service.md) - 스케줄링 전략, 로깅
- [ADR 006: contract_id=-1 무료 예산](docs/adr/006-contract-id-negative-one.md) - 무료 예산 사용
- [ADR 007: 쿠폰 발급 워크플로우](docs/adr/007-coupon-issuance-workflow.md) - 다단계 비동기 처리
- [ADR 008: CLI 구조 재설계](docs/adr/008-cli-restructuring.md) - 5개 명령어, 전역 명령어, 로그 중심 운영

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

- **OS**: Linux (systemd 필수)
- **Python**: 3.10+
- **패키지**: requests, openpyxl
- **로깅**: journalctl (systemd)

## 프로젝트 구조

```
# 설치 후 구조
/opt/coupang_coupon_issuer/
├── main.py                          # CLI 진입점
├── src/coupang_coupon_issuer/
│   ├── config.py                    # API 키 관리, 고정값 설정
│   ├── coupang_api.py               # Coupang API 클라이언트 (HMAC-SHA256)
│   ├── issuer.py                    # 쿠폰 발급 로직 (로그 출력만)
│   ├── scheduler.py                 # 0시 감지 스케줄러
│   └── service.py                   # systemd 설치/제거
└── pyproject.toml

/usr/local/bin/
└── coupang_coupon_issuer            # 심볼릭 링크 → /opt/.../main.py

/etc/coupang_coupon_issuer/
├── credentials.json                 # API 키 (600 권한)
└── coupons.xlsx                     # 쿠폰 정의 (600 권한)

# 개발 디렉토리 구조
docs/
├── DEV_LOG.md                       # 작은 결정사항, 관례
├── adr/                             # 아키텍처 결정 기록
│   ├── 001-excel-structure.md
│   ├── 002-input-normalization.md
│   ├── 003-api-authentication.md
│   ├── 004-fixed-configuration-values.md
│   ├── 005-systemd-service.md
│   ├── 006-contract-id-negative-one.md
│   ├── 007-coupon-issuance-workflow.md
│   └── 008-cli-restructuring.md
└── coupang/                         # Coupang API 규격 문서
    ├── workflow.md
    ├── parameters-explained.md
    └── (각종 API 문서)
```

## Claude에게 작업 요청

### 제약사항 (항상 명시)

- Python 3.10 호환
- Linux 서버 전용 (systemd, journalctl)
- 패키지: requests, openpyxl만 사용
- 로그에 이모지 사용 금지 (텍스트만)
- 예외 처리 필수 (로깅 후 상위로 전파)

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

# 4. 스케줄러 실행 (systemd가 자동 실행)
coupang_coupon_issuer serve

# 5. 서비스 제거
sudo coupang_coupon_issuer uninstall
```

### 다음 구현 작업

- [x] CLI 구조 재설계 (5개 명령어)
- [x] 엑셀 결과 출력 제거 (로그로만)
- [x] 전역 명령어 구현 (심볼릭 링크)
- [x] install 4개 파라미터 확장
- [x] Docker 테스트 환경 구성
- [ ] 테스트 작성 (pytest + requests-mock)
- [ ] 성능 최적화 (병렬 처리, 선택사항)

## 디버깅

journalctl 로그 공유 시:
```bash
journalctl -u coupang_coupon_issuer --since "1 hour ago"
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
- [x] CLI 구조 재설계 (apply/issue/serve/install/uninstall)
- [x] 전역 명령어 (심볼릭 링크)
- [x] install 4개 파라미터 확장
- [x] 엑셀 결과 출력 제거 (로그 중심)
- [x] Docker 테스트 환경 (docker-compose.test.yml)

### 문서화
- [x] DEV_LOG (로깅 규칙, 검증 규칙 등)
- [x] ADR 001-008 (아키텍처 결정 기록)
- [x] Coupang API 문서 (workflow, parameters 등)

### 향후 작업
- [ ] 테스트 작성 (pytest + requests-mock)
- [ ] 성능 최적화 (병렬 처리, 선택사항)
