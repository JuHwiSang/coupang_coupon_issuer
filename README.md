# Coupang Coupon Issuer

PyInstaller 단일 실행 파일로 배포하는 쿠폰 자동 발급 서비스

## 특징

- **단일 실행 파일**: Python 설치 불필요 (PyInstaller --onefile)
- **간단한 구조**: 실행 파일 + 설정 + 로그 모두 한 디렉토리
- **UUID 기반 추적**: 디렉토리 이동 시 재설치 자동 처리
- **Cron 스케줄링**: 매일 0시 자동 실행
- **Jitter 지원**: Thundering herd 방지 (0-120분 랜덤 지연)
- **자동 Cron 설치**: Ubuntu/Debian 자동 감지 및 설치

## 시스템 요구사항

### 배포 환경 (PyInstaller 빌드 결과)
- Linux OS (cron 지원)
- Python 불필요 (실행 파일에 포함)

### 개발 환경
- Python 3.10+
- Linux OS
- uv (패키지 관리)

### 지원 배포판

- **Ubuntu**: 22.04 (Jammy) 이상
- **Debian**: 12 (Bookworm) 이상

## 설치 및 사용

### 1. 다운로드 (GitHub Release)

```bash
# 실행 파일 다운로드
wget https://github.com/.../coupang_coupon_issuer
chmod +x coupang_coupon_issuer

# 디렉토리 생성 및 이동
mkdir -p ~/coupang_coupon_issuer
mv coupang_coupon_issuer ~/coupang_coupon_issuer/
cd ~/coupang_coupon_issuer
```

### 2. 엑셀 파일 배치

```bash
# coupons.xlsx 파일을 같은 디렉토리에 복사
cp /path/to/coupons.xlsx ./
```

**엑셀 파일 형식** (6개 컬럼):
1. 쿠폰이름
2. 쿠폰타입 (즉시할인 / 다운로드쿠폰)
3. 쿠폰유효기간 (일 단위, 예: 30)
4. 할인방식 (RATE / PRICE / FIXED_WITH_QTY)
5. 할인금액/비율 (예: 10 = 10% 또는 1000 = 1000원)
6. 발급개수 (즉시할인은 빈값, 다운로드쿠폰은 숫자)

### 3. 엑셀 검증

```bash
# 엑셀 파일 검증 및 전체 내용 확인 (테이블 형식)
./coupang_coupon_issuer verify
```

**출력 예시**:
```
엑셀 파일 검증 중: ./coupons.xlsx

✓ 3개 쿠폰 로드 완료

     No         쿠폰이름       쿠폰타입      유효기간      할인방식       할인금액      할인비율      발급개수        총 예산
================================================================================================================================================
     1         테스트쿠폰1      즉시할인         30          RATE           0           10%            0             0원
     2         테스트쿠폰2     다운로드쿠폰       15         PRICE          500           0%          100         50,000원
     3         신규쿠폰       다운로드쿠폰       30    FIXED_WITH_QTY     1,000          0%           50         50,000원

검증 완료. 문제없이 발급 가능합니다.
```

### 4. 서비스 설치 (Cron 등록)

```bash
# 기본 설치
./coupang_coupon_issuer install \
  --access-key YOUR_ACCESS_KEY \
  --secret-key YOUR_SECRET_KEY \
  --user-id YOUR_USER_ID \
  --vendor-id YOUR_VENDOR_ID

# Jitter 활성화 (0-60분 랜덤 지연)
./coupang_coupon_issuer install \
  --access-key YOUR_ACCESS_KEY \
  --secret-key YOUR_SECRET_KEY \
  --user-id YOUR_USER_ID \
  --vendor-id YOUR_VENDOR_ID \
  --jitter-max 60
```

**설치 과정** (3단계):
1. config.json 저장 (API 키 + UUID)
2. Cron 감지/설치/활성화
3. Crontab에 스케줄 추가 (절대경로 + UUID 주석)

### 5. 서비스 관리

```bash
# Crontab 확인
crontab -l

# 로그 확인 (실시간)
tail -f ./issuer.log

# 로그 확인 (에러만)
cat ./issuer.log | grep ERROR

# 단발성 테스트 실행
./coupang_coupon_issuer issue

# 단발성 테스트 (Jitter 포함)
./coupang_coupon_issuer issue --jitter-max 30
```

### 6. 서비스 제거

```bash
# Cron job만 제거 (파일은 유지)
./coupang_coupon_issuer uninstall

# 완전 삭제
rm -rf ~/coupang_coupon_issuer
```

## 디렉토리 이동

디렉토리를 이동한 후 재설치하면 UUID 기반으로 이전 cron job을 자동 제거합니다:

```bash
# 1. 새 위치로 이동
mv ~/coupang_coupon_issuer ~/new_location/

# 2. 재설치 (UUID 자동 처리)
cd ~/new_location/coupang_coupon_issuer
./coupang_coupon_issuer install \
  --access-key $(jq -r .access_key config.json) \
  --secret-key $(jq -r .secret_key config.json) \
  --user-id $(jq -r .user_id config.json) \
  --vendor-id $(jq -r .vendor_id config.json)
```

## 파일 구조

```
~/coupang_coupon_issuer/
├── coupang_coupon_issuer        # 단일 실행 파일 (PyInstaller 빌드)
├── config.json                  # API 키 + UUID (600 권한)
├── coupons.xlsx                 # 쿠폰 정의 (사용자 배치)
└── issuer.log                   # 실행 로그 (자동 생성)
```

**config.json 구조**:
```json
{
  "access_key": "...",
  "secret_key": "...",
  "user_id": "...",
  "vendor_id": "...",
  "installation_id": "a3f8d9c2-4b1e-4a7c-9d3f-8e2b1a5c7d9e"
}
```

## 개발

### 개발 환경 설정

```bash
# 1. Clone repository
git clone <repository-url>
cd coupang_coupon_issuer

# 2. Install dependencies (uv)
uv sync

# 3. 개발 모드 실행
uv run python main.py verify ./tests/fixtures/sample_valid.xlsx
uv run python main.py issue
```

### 테스트 실행

```bash
# 유닛 테스트 (빠름, Windows 호환)
uv run pytest tests/unit -v

# 커버리지 포함
uv run pytest tests/unit --cov=src/coupang_coupon_issuer --cov-report=html

# 특정 파일만
uv run pytest tests/unit/test_issuer.py -v
```

**테스트 현황**:
- **유닛 테스트**: ~43개 (PyInstaller mock 포함)
- **통합 테스트**: 삭제됨 (PyInstaller 단순화로 불필요)
- **커버리지**: config/api/issuer 94%+

### PyInstaller 빌드

```bash
# 단일 실행 파일 빌드
pyinstaller --onefile \
  --name coupang_coupon_issuer \
  main.py

# 결과물: dist/coupang_coupon_issuer
```

## 문서

- [CLAUDE.md](CLAUDE.md) - Claude 개발 가이드
- [docs/DEV_LOG.md](docs/DEV_LOG.md) - 작은 결정사항, 관례
- [docs/adr/](docs/adr/) - 아키텍처 결정 기록 (ADR)
  - [ADR 013: PyInstaller 단일 실행 파일 배포](docs/adr/013-pyinstaller-single-binary.md) - **현재 구조**

## 주요 변경사항 (v2.0)

**ADR 013**: PyInstaller 단일 실행 파일 배포 전략

- ✅ **단순함**: 7단계 설치 → 3단계
- ✅ **경량화**: 코드 17% 감소, 테스트 60% 감소
- ✅ **자급자족**: Python 의존성 제거
- ✅ **유연성**: UUID 기반 디렉토리 이동 대응
- ✅ **가시성**: verify 명령어로 미리보기

**이전 구조와 차이**:
- `/opt`, `/usr/local/bin`, `~/.config`, `~/.local/state` 제거
- 모든 파일이 한 디렉토리에 집중
- `apply` → `verify` 명령어 변경
- 전역 명령어 제거 (`./coupang_coupon_issuer`)
- XDG Base Directory 표준 제거

## License

MIT
