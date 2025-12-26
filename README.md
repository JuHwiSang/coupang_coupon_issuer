# Coupang Coupon Issuer

Python 스크립트 기반 쿠폰 자동 발급 서비스

## 특징

- **Python 스크립트 실행**: 간단한 설치 및 실행
- **간단한 구조**: 소스코드와 작업 디렉토리 분리
- **UUID 기반 추적**: 디렉토리 이동 시 재설치 자동 처리
- **Cron 스케줄링**: 매일 0시 자동 실행
- **Jitter 지원**: Thundering herd 방지 (0-120분 랜덤 지연)
- **자동 Cron 설치**: Ubuntu/Debian 자동 감지 및 설치
- **고정 파일명**: 엑셀 파일명은 `coupons.xlsx`로 고정

## 시스템 요구사항

### 배포 환경
- Linux OS (cron 지원)
- Python 3.10+ 필수
- 의존성: requests, openpyxl

### 개발 환경
- Python 3.10+
- Linux OS
- uv (패키지 관리)

### 지원 배포판

Python 3.10+ 요구사항으로 인해:
- **Ubuntu**: 22.04 (Jammy, Python 3.10) 이상
- **Debian**: 12 (Bookworm, Python 3.11) 이상

## 설치 및 사용

### 1. 프로젝트 클론 및 의존성 설치

```bash
# 프로젝트 클론
git clone <repository-url>
cd coupang_coupon_issuer

# 의존성 설치
pip3 install -e .
# 또는
pip3 install requests openpyxl
```

### 2. 엑셀 예시 파일 생성 (선택사항)

엑셀 포맷을 쉽게 이해할 수 있도록 예제 파일을 생성할 수 있습니다:

```bash
# 예제 파일 생성
python3 scripts/generate_example.py
```

생성되는 파일 (`examples/` 디렉토리):
- **basic.xlsx**: 기본 예제 (2개 쿠폰)
- **comprehensive.xlsx**: 전체 예제 (6개 쿠폰)
- **edge_cases.xlsx**: 엣지 케이스 (7개 쿠폰)

**비전문가를 위한 기능**:
- 헤더 주석으로 각 컬럼 설명 제공
- 드롭다운 선택 (쿠폰타입, 할인방식)
- 데이터 유효성 검사 (숫자 범위 제한)

### 3. 작업 디렉토리 생성 및 엑셀 파일 배치

```bash
# 작업 디렉토리 생성
mkdir -p ~/my-coupons

# coupons.xlsx 파일을 작업 디렉토리에 복사
cp /path/to/coupons.xlsx ~/my-coupons/
```

**엑셀 파일 형식** (9개 컬럼):
1. 쿠폰이름
2. 쿠폰타입 (즉시할인 / 다운로드쿠폰)
3. 쿠폰유효기간 (일 단위)
4. 할인방식 (정률할인 / 정액할인 / 수량별 정액할인) - **한글로 입력**
5. 할인금액/비율
6. 최소구매금액 (다운로드쿠폰 전용, 비어있으면 10원)
7. 최대할인금액 (필수, 정률할인 시 최대 할인 금액)
8. 발급개수 (즉시할인은 빈값, 다운로드쿠폰은 숫자)
9. 옵션ID (쉼표로 구분된 vendor item ID)

**중요**: 엑셀 파일명은 반드시 `coupons.xlsx`여야 합니다.

### 4. 엑셀 검증

```bash
# 기본: directory의 coupons.xlsx 검증
python3 main.py verify ~/my-coupons

# 특정 파일 검증 (--file 옵션)
python3 main.py verify --file ~/my-coupons/custom.xlsx

# 현재 디렉토리에서 특정 파일 검증
python3 main.py verify --file ./test.xlsx
```

**출력 예시**:
```
엑셀 파일 검증 중: ./coupons.xlsx

✓ 3개 쿠폰 로드 완료

     No         쿠폰이름       쿠폰타입      유효기간      할인방식       할인금액      할인비율      발급개수        총 예산
================================================================================================================================================
     1         테스트쿠폰1      즉시할인         30         정률할인          0           10%            0             0원
     2         테스트쿠폰2     다운로드쿠폰       15         정액할인         500           0%          100         50,000원
     3         신규쿠폰       다운로드쿠폰       30      수량별 정액할인    1,000          0%           50         50,000원

검증 완료. 문제없이 발급 가능합니다.
```

### 5. 시스템 준비 (최초 1회, sudo 필요)

Cron 데몬을 설치하고 활성화합니다. 시스템 전체에 한 번만 실행하면 됩니다.

```bash
sudo python3 main.py setup
```

**수행 작업**:
- Cron 데몬 감지
- 미설치 시 자동 설치 (Ubuntu/Debian/RHEL 지원)
- Cron 서비스 활성화 및 시작

**참고**: 이미 Cron이 설치되어 있다면 이 단계를 건너뛸 수 있습니다.

### 6. 서비스 설치 (Cron 등록, sudo 불필요)

```bash
# 기본 설치 (대화형 입력)
python3 main.py install ~/my-coupons

# 옵션으로 인증 정보 제공 (대화형 입력 생략)
python3 main.py install ~/my-coupons \
  --access-key YOUR_ACCESS_KEY \
  --secret-key YOUR_SECRET_KEY \
  --user-id YOUR_USER_ID \
  --vendor-id YOUR_VENDOR_ID

# Jitter 활성화 (0-60분 랜덤 지연)
python3 main.py install ~/my-coupons \
  --access-key YOUR_ACCESS_KEY \
  --secret-key YOUR_SECRET_KEY \
  --user-id YOUR_USER_ID \
  --vendor-id YOUR_VENDOR_ID \
  --jitter-max 60
```

**설치 과정** (2단계):
1. config.json 저장 (API 키 + UUID)
2. Crontab에 스케줄 추가 (절대경로 + UUID 주석)

**중요**: 
- `setup` 명령어를 먼저 실행하지 않으면 에러가 발생합니다
- 일반 사용자 권한으로 실행하므로 파일이 올바른 권한으로 생성됩니다

### 5. 서비스 관리

```bash
# Crontab 확인
crontab -l

# 로그 확인 (실시간)
tail -f ~/my-coupons/issuer.log

# 로그 확인 (에러만)
cat ~/my-coupons/issuer.log | grep ERROR

# 단발성 테스트 실행
python3 main.py issue ~/my-coupons

# 단발성 테스트 (Jitter 포함)
python3 main.py issue ~/my-coupons --jitter-max 60
```

### 7. 서비스 제거

```bash
# Cron job 및 config.json 제거 (엑셀 파일과 로그는 유지)
python3 main.py uninstall ~/my-coupons

# 완전 삭제
rm -rf ~/my-coupons
```

## 디렉토리 이동

작업 디렉토리를 이동한 후 재설치하면 UUID 기반으로 이전 cron job을 자동 제거합니다:

```bash
# 1. 새 위치로 이동
mv ~/my-coupons ~/new-location/

# 2. 재설치 (UUID 자동 처리)
python3 main.py install ~/new-location \
  --access-key $(jq -r .access_key ~/new-location/config.json) \
  --secret-key $(jq -r .secret_key ~/new-location/config.json) \
  --user-id $(jq -r .user_id ~/new-location/config.json) \
  --vendor-id $(jq -r .vendor_id ~/new-location/config.json)
```

## 파일 구조

### 배포 후 구조 (스크립트 기반)

```
# 작업 디렉토리 (사용자가 원하는 위치)
~/my-coupons/
├── config.json                  # API 키 + UUID (600 권한)
├── coupons.xlsx                 # 쿠폰 정의 (파일명 고정)
└── issuer.log                   # 실행 로그 (자동 생성)

# 프로젝트 소스 (별도 위치, 예: /opt/coupang_coupon_issuer)
/opt/coupang_coupon_issuer/
├── main.py                      # CLI 진입점
├── src/                         # 소스코드
└── ...
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

## CI/CD

### GitHub Actions 자동 빌드

PyInstaller 기반 단일 실행 파일을 자동으로 빌드합니다.

**트리거**:
- `main` 브랜치 push 시 자동 실행
- 수동 실행 가능 (Actions 탭 → Build Executable → Run workflow)

**Artifact 다운로드**:
1. GitHub 저장소 → Actions 탭
2. 최근 워크플로우 실행 선택
3. Artifacts 섹션에서 `coupang_coupon_issuer-linux` 다운로드

**로컬 빌드**:
```bash
# 빌드 의존성 설치
uv sync --group build

# PyInstaller 빌드
uv run pyinstaller --paths src --name coupang_coupon_issuer --onefile main.py

# 결과물 확인
./dist/coupang_coupon_issuer --help
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
uv run python main.py verify tests/fixtures/
uv run python main.py issue tests/fixtures/
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
- **유닛 테스트**: ~115개 (ADR 014 기준)
- **통합 테스트**: 24개 × 4 배포판 = 96개 (계획 중)
- **커버리지**: config/api/issuer/service 94%+

## 문서

### 사용자 문서

- **[docs/USER_GUIDE.md](docs/USER_GUIDE.md) - 비개발자용 사용설명서** ⭐
  - 엑셀 파일 작성부터 설치, 관리까지 단계별 가이드
  - 명령어 최소화, 이해하기 쉬운 설명
  - 중요 주의사항 및 문제 해결 방법 포함

### 개발자 문서

- [CLAUDE.md](CLAUDE.md) - Claude 개발 가이드
- [docs/DEV_LOG.md](docs/DEV_LOG.md) - 작은 결정사항, 관례
- [docs/adr/](docs/adr/) - 아키텍처 결정 기록 (ADR)
  - [ADR 014: 스크립트 기반 배포](docs/adr/014-script-based-deployment.md) - **현재 구조**
  - [ADR 015: 옵션ID 컬럼 추가](docs/adr/015-option-id-column.md) - 엑셀 7컬럼 구조
  - [ADR 017: 쿠폰 타입별 할인 검증 규칙 분리](docs/adr/017-coupon-type-specific-validation.md) - 쿠폰타입별 검증
  - [ADR 018: 할인방식 한글 입력 지원](docs/adr/018-korean-discount-type-names.md) - 한글 할인방식 입력
  - [ADR 018: 할인방식 한글 입력 지원](docs/adr/018-korean-discount-type-names.md) - 한글 할인방식 입력
- [ADR 019: setup/install 명령어 분리](docs/adr/019-setup-install-separation.md) - **현재 구조**
- [ADR 020: 즉시할인쿠폰 간단 폴링](docs/adr/020-instant-coupon-simple-polling.md)
- [ADR 021: Excel 9컬럼 구조](docs/adr/021-excel-9-column-structure.md) - **현재 구조**
- [ADR 022: 다운로드쿠폰 타이밍 수정](docs/adr/022-download-coupon-timing-fix.md) - KST, 타임존 처리

## 주요 변경사항 (v3.0)

**ADR 014**: 스크립트 기반 배포 전략

- ✅ **단순함**: PyInstaller 의존성 제거
- ✅ **빠른 개발**: 코드 변경 시 재빌드 불필요
- ✅ **빠른 테스트**: 통합 테스트 3-5배 빠름
- ✅ **유연성**: 런타임에 작업 디렉토리 지정
- ✅ **표준 Python**: 개발 시 `pip install -e .` 사용
- ✅ **고정 파일명**: 엑셀 파일명은 `coupons.xlsx`로 고정

**이전 구조와 차이** (v2.0 → v3.0):
- PyInstaller 단일 실행 파일 → Python 스크립트 실행
- Python 설치 필요 (3.10+)
- 작업 디렉토리를 CLI 인자로 지정
- 엑셀 파일명 `coupons.xlsx` 고정 (파일 인자 제거)

## License

MIT
