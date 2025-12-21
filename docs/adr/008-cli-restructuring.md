# ADR 008: CLI 구조 재설계

> **⚠️ DEPRECATED**: 이 ADR은 ADR 013 (PyInstaller 단일 실행 파일)로 대체되었습니다.
>
> 날짜: 2024-12-21
> 변경사항:
> - `serve` 명령어 제거 (ADR 010)
> - `apply` 명령어 → `verify` 명령어 (ADR 013)
> - 전역 명령어 제거, PyInstaller 단일 실행 파일로 전환
>
> 참조: [ADR 013: PyInstaller 단일 실행 파일 배포](./013-pyinstaller-single-binary.md)

**상태**: 승인됨 (일부 대체됨)
**날짜**: 2024-12-17
**결정자**: 프로젝트 오너

## 컨텍스트

초기 CLI 설계는 `run`, `install`, `uninstall` 3개 명령어로 구성되어 있었습니다. 그러나 실제 운영 환경에서는 다음과 같은 문제점이 발견되었습니다:

### 기존 문제점

1. **엑셀 결과 파일 출력**
   - `results/` 디렉토리에 xlsx 파일 저장
   - 매일 실행 시 불필요한 파일 축적
   - journalctl 로그만으로 충분함

2. **엑셀 파일 경로 불명확**
   - 상대 경로 사용 (`coupons.xlsx`)
   - 실행 위치에 따라 파일을 찾지 못하는 문제

3. **테스트 어려움**
   - 단발성 쿠폰 발급 테스트 불가
   - 스케줄러 없이 즉시 실행하는 방법 부재

4. **설치 파라미터 부족**
   - access_key, secret_key만 수집
   - user_id, vendor_id는 런타임에 환경변수로 별도 설정 필요

5. **전역 명령어 부재**
   - `python3 /path/to/main.py` 형식으로만 실행 가능
   - 사용자 경험 저하

## 결정사항

### 새로운 CLI 구조

5개 명령어로 재설계:

```bash
coupang_coupon_issuer apply <excel_file>   # 엑셀 검증 및 복사
coupang_coupon_issuer issue                # 단발성 발급
coupang_coupon_issuer serve                # 스케줄러 실행
coupang_coupon_issuer install --access-key ... --secret-key ... --user-id ... --vendor-id ...
coupang_coupon_issuer uninstall
```

### 1. apply 명령어 (신규)

**용도**: 엑셀 파일을 검증하고 `/etc/coupang_coupon_issuer/coupons.xlsx`로 복사

**동작**:
1. 엑셀 파일 존재 확인
2. openpyxl로 열기 시도
3. 필수 컬럼 5개 확인
4. 각 행 데이터 정규화 및 유효성 검증
   - 쿠폰타입: "즉시할인" 또는 "다운로드쿠폰"
   - 쿠폰유효기간: 양의 정수
   - 할인방식: RATE/FIXED_WITH_QUANTITY/PRICE
   - 발급개수: 양의 정수
   - RATE: 1~99% 범위
   - PRICE: 10원 단위, 최소 10원
5. 검증 통과 시 복사
6. 파일 권한 600 설정

**예시**:
```bash
sudo coupang_coupon_issuer apply ./my_coupons.xlsx
```

### 2. issue 명령어 (신규)

**용도**: 단발성 쿠폰 발급 (테스트용)

**동작**:
1. `/etc/coupang_coupon_issuer/coupons.xlsx` 읽기
2. `/etc/coupang_coupon_issuer/credentials.json`에서 API 키 로드
3. `CouponIssuer().issue()` 호출
4. 결과를 로그로만 출력 (엑셀 저장 안 함)

**예시**:
```bash
coupang_coupon_issuer issue
```

### 3. serve 명령어 (run 대체)

**용도**: 스케줄러 루프 실행 (systemd용)

**변경사항**:
- `run` → `serve`로 명령어 이름 변경
- 내부 로직은 동일 (MidnightScheduler 실행)

**예시**:
```bash
coupang_coupon_issuer serve
```

### 4. install 명령어 (확장)

**변경사항**:
- 2개 파라미터 → 4개 파라미터
  - 기존: `--access-key`, `--secret-key`
  - 추가: `--user-id`, `--vendor-id`
- 파일 복사 → `/opt/coupang_coupon_issuer/`
- 심볼릭 링크 생성 → `/usr/local/bin/coupang_coupon_issuer`
- Python 의존성 자동 설치

**예시**:
```bash
sudo coupang_coupon_issuer install \
  --access-key YOUR_KEY \
  --secret-key YOUR_SECRET \
  --user-id YOUR_USER_ID \
  --vendor-id YOUR_VENDOR_ID
```

### 5. uninstall 명령어 (확장)

**추가 삭제 항목**:
- `/opt/coupang_coupon_issuer/` (확인 후)
- `/usr/local/bin/coupang_coupon_issuer` (심볼릭 링크)
- `/etc/coupang_coupon_issuer/coupons.xlsx` (확인 후)

### 설치 구조

```
/opt/coupang_coupon_issuer/
├── main.py                    # 실행 파일
├── src/                       # 소스 코드
│   └── coupang_coupon_issuer/
└── pyproject.toml             # 프로젝트 메타데이터

/usr/local/bin/
└── coupang_coupon_issuer      # 심볼릭 링크 → /opt/coupang_coupon_issuer/main.py

/etc/coupang_coupon_issuer/
├── credentials.json           # API 키 (600 권한)
└── coupons.xlsx              # 쿠폰 정의 (600 권한)
```

### 엑셀 결과 출력 제거

**변경사항**:
- `_save_result()` 메서드 완전 제거
- `issue()` 메서드에서 로그로만 출력
- 상세 결과 로깅 형식:
  ```
  [2024-12-17 12:00:00] 쿠폰 발급 완료! (성공: 3, 실패: 1)
  [2024-12-17 12:00:00] [OK] 신규 쿠폰: 즉시할인쿠폰 생성 완료 (requestedId: 123...)
  [2024-12-17 12:00:00] [FAIL] 다운로드 쿠폰: 에러 메시지...
  ```

**근거**:
- journalctl로 모든 로그 확인 가능
- 엑셀 파일 불필요
- 디스크 공간 절약

## 근거

### 1. 사용자 경험 개선

- **전역 명령어**: `coupang_coupon_issuer`로 어디서든 실행 가능
- **명확한 명령어 이름**: `serve` (서비스 실행), `issue` (즉시 발급)
- **일관된 경로**: `/etc`에 모든 설정 파일 집중

### 2. 운영 편의성

- **apply로 엑셀 사전 검증**: 발급 전 오류 사전 차단
- **issue로 즉시 테스트**: 스케줄러 없이 단발성 테스트 가능
- **로그 중심 운영**: journalctl만으로 모든 이력 추적

### 3. 자동화 친화적

- **고정된 경로**: `/etc/coupang_coupon_issuer/coupons.xlsx`
- **환경변수 불필요**: install 시 모든 설정 완료
- **systemd 통합**: serve 명령으로 명확한 역할 구분

### 4. 보안 강화

- **파일 권한 600**: root만 읽기 가능
- **중앙 집중 관리**: `/opt`, `/etc`에만 파일 존재
- **심볼릭 링크**: 실제 파일은 `/opt`에만 존재

## 대안

### 대안 1: 기존 구조 유지 + 환경변수 사용

- **장점**: 변경 최소화
- **단점**:
  - user_id, vendor_id를 매번 환경변수로 설정해야 함
  - 엑셀 파일 경로 여전히 불명확
  - 전역 명령어 부재
- **결정**: 거부됨 (사용자 경험 저하)

### 대안 2: apply 명령어 없이 issue가 직접 검증

- **장점**: 명령어 개수 감소
- **단점**:
  - 매일 0시 실행 시 검증 실패하면 해당 날짜 발급 불가
  - 사전 검증 불가능
- **결정**: 거부됨 (안정성 저하)

### 대안 3: Docker 컨테이너로 배포

- **장점**: 의존성 격리, 이식성
- **단점**:
  - systemd 통합 복잡
  - 리소스 오버헤드
  - 로그 관리 복잡
- **결정**: 거부됨 (단순 Python 스크립트에 과도함)

### 대안 4: /usr/local/share에 설치

- **장점**: FHS 표준 준수
- **단점**:
  - /opt이 독립 애플리케이션 설치에 더 적합
  - /usr/local/share는 아키텍처 독립 데이터용
- **결정**: 거부됨 (/opt이 더 적합)

## 영향

### 긍정적 영향

1. **사용자 경험 향상**
   - 전역 명령어로 편리한 실행
   - 명확한 명령어 구조
   - 일관된 파일 경로

2. **운영 안정성**
   - apply로 사전 검증
   - issue로 즉시 테스트
   - 로그 중심 운영

3. **자동화 효율**
   - 고정된 경로
   - 환경변수 불필요
   - systemd 통합 개선

4. **보안 강화**
   - 파일 권한 600
   - 중앙 집중 관리
   - 최소 권한 원칙

### 부정적 영향

1. **마이그레이션 필요**
   - 기존 설치된 서비스는 재설치 필요
   - 명령어 변경 (run → serve)
   - 설치 파라미터 증가 (2개 → 4개)
   - **완화 방법**: uninstall 후 새 버전으로 install

2. **디스크 사용량 증가**
   - /opt에 파일 복사 (약 100KB)
   - **완화 방법**: 무시 가능한 수준

3. **설치 복잡도 증가**
   - 파일 복사, 심볼릭 링크 생성 등 추가 단계
   - **완화 방법**: install 명령이 자동으로 처리

## 구현 요구사항

### 파일 수정

1. **src/coupang_coupon_issuer/config.py**
   - `EXCEL_INPUT_FILE` 경로 변경: `/etc/coupang_coupon_issuer/coupons.xlsx`

2. **src/coupang_coupon_issuer/issuer.py**
   - `_save_result()` 메서드 제거
   - `issue()` 메서드 로그 출력만 수행
   - 검증 로직 강화 (RATE 1-99, PRICE 10원 단위)

3. **main.py**
   - `cmd_apply()` 함수 추가
   - `cmd_issue()` 함수 추가
   - `cmd_run()` → `cmd_serve()` 이름 변경
   - `cmd_install()` 4개 파라미터로 확장
   - argparse 설정 업데이트

4. **src/coupang_coupon_issuer/service.py**
   - `install()` 메서드: 4개 파라미터, 파일 복사, 심볼릭 링크
   - `uninstall()` 메서드: 파일 삭제 확장

5. **docker-compose.test.yml** (신규)
   - Ubuntu 22.04 기반
   - privileged mode (systemd 지원)
   - cgroup 마운트

### 테스트 시나리오

```bash
# 1. Docker 환경 시작
docker-compose -f docker-compose.test.yml up -d
sleep 5

# 2. 컨테이너 접속
docker-compose -f docker-compose.test.yml exec test-env /bin/bash

# 3. 의존성 설치
apt-get update
apt-get install -y python3 python3-pip

# 4. 서비스 설치
cd /app
python3 main.py install \
  --access-key TEST_KEY \
  --secret-key TEST_SECRET \
  --user-id TEST_USER \
  --vendor-id A00012345

# 5. 검증
systemctl status coupang_coupon_issuer
coupang_coupon_issuer --help
ls -la /opt/coupang_coupon_issuer/
ls -la /usr/local/bin/coupang_coupon_issuer

# 6. 정리
exit
docker-compose -f docker-compose.test.yml down
```

## 참고 문서

- [ADR 001: 엑셀 입력 구조](001-excel-structure.md)
- [ADR 002: 입력 정규화](002-input-normalization.md)
- [ADR 004: 고정 설정값](004-fixed-configuration-values.md)
- [ADR 005: systemd 서비스](005-systemd-service.md)
- [DEV_LOG: 로깅 규칙](../DEV_LOG.md)
