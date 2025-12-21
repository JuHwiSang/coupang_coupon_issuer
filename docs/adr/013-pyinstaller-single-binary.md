# ADR 013: PyInstaller 단일 실행 파일 배포

> **⚠️ SUPERSEDED**: 이 ADR은 ADR 014 (Script-based Deployment)로 대체되었습니다.
>
> PyInstaller 의존성이 제거되고 스크립트 기반 배포로 전환되었습니다.

**상태**: ~~승인됨~~ **대체됨 (ADR 014)**
**날짜**: 2024-12-21
**결정자**: 프로젝트 오너
**대체**: ADR 008 (CLI 구조), ADR 010 (Crontab 서비스), ADR 012 (XDG 경로)
**대체됨**: ADR 014 (Script-based Deployment, 2024-12-21)

## 컨텍스트

기존 구현은 다음과 같은 복잡한 설치 구조를 가지고 있었습니다:

### 기존 문제점

1. **복잡한 설치 프로세스 (7단계)**
   - `/opt/coupang_coupon_issuer/` 파일 복사
   - `/usr/local/bin/` 심볼릭 링크 생성
   - Python 의존성 설치 (`pip install`)
   - `~/.config/` XDG 경로 설정
   - `~/.local/state/` 로그 디렉토리 생성
   - cron 데몬 설치/활성화
   - crontab에 작업 추가

2. **과도한 인프라 코드**
   - 경로 관리: 420줄 (전체의 52%)
   - XDG helper 함수, 플랫폼 감지, 패키지 매니저 자동 선택
   - 통합 테스트 80개 (Docker + testcontainers)

3. **파일 이동 시 깨짐**
   - `/opt` 절대 경로 하드코딩
   - 디렉토리 이동하면 cron job이 깨짐
   - 수동 재설치 필요

4. **Python 의존성**
   - Python 3.10+ 필수
   - requests, openpyxl 설치 필요
   - 배포판별 호환성 문제 (Ubuntu 20.04 미지원)

5. **apply 명령어의 한계**
   - `/etc`로 파일 복사만 수행
   - 실제 발급 미리보기 불가
   - 사용자가 어떻게 인식되었는지 확인 어려움

## 결정사항

### 1. PyInstaller --onefile 단일 실행 파일

**선택 이유**:
- Python 의존성 제거 (requests, openpyxl 포함)
- 단일 바이너리 배포 가능
- 크로스 플랫폼 빌드 지원

**구조**:
```
~/coupang_coupon_issuer/        # 사용자가 원하는 위치
├── coupang_coupon_issuer       # 단일 실행 파일 (PyInstaller 빌드)
├── config.json                 # credentials + UUID
├── coupons.xlsx                # 쿠폰 정의
└── issuer.log                  # 실행 로그
```

### 2. 실행 파일 위치 = 모든 것의 기준

**경로 해결 전략**:
```python
# config.py
if getattr(sys, 'frozen', False):
    # PyInstaller로 빌드된 경우
    BASE_DIR = Path(sys.executable).parent.resolve()
else:
    # 개발 환경 (python main.py)
    BASE_DIR = Path(__file__).parent.parent.parent.resolve()

CONFIG_FILE = BASE_DIR / "config.json"
EXCEL_INPUT_FILE = BASE_DIR / "coupons.xlsx"
LOG_FILE = BASE_DIR / "issuer.log"
```

**장점**:
- XDG 경로 제거 (40줄 감소)
- 모든 파일이 한 디렉토리에 집중
- 디버깅 용이
- 멀티 설치 가능

### 3. UUID 기반 Cron Job 추적

**문제**: 기존에는 마커(`# coupang_coupon_issuer_job`)로만 식별
- 디렉토리 이동 시 깨진 job 제거 불가
- 여러 설치 간 충돌 가능

**해결책**:
```json
{
  "access_key": "...",
  "secret_key": "...",
  "user_id": "...",
  "vendor_id": "...",
  "installation_id": "a3f8d9c2-4b1e-4a7c-9d3f-8e2b1a5c7d9e"
}
```

```bash
# crontab 항목
0 0 * * * /path/to/coupang_coupon_issuer issue >> /path/to/issuer.log 2>&1  # coupang_coupon_issuer_job:a3f8d9c2-4b1e-4a7c-9d3f-8e2b1a5c7d9e
```

**재설치 시 동작**:
1. config.json에서 기존 UUID 읽기
2. 기존 UUID로 crontab에서 항목 제거
3. 새 경로로 cron job 재등록 (같은 UUID 유지 또는 새 UUID 생성)

**장점**:
- 디렉토리 이동 후 재설치 시 자동으로 이전 job 제거
- 여러 설치 간 UUID로 명확히 구분
- UUID 충돌 확률 극히 낮음 (2^122)

### 4. apply → verify 명령어 변경

**기존 apply 명령어**:
- 엑셀 검증 + `/etc`로 복사
- 결과를 눈으로 확인 불가
- 127줄의 복잡한 검증 로직

**새 verify 명령어**:
```bash
./coupang_coupon_issuer verify [./coupons.xlsx]
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

**장점**:
- 사용자가 엑셀이 어떻게 인식되었는지 즉시 확인
- API 변환 결과까지 미리보기
- 예산 계산 (할인금액 × 발급개수)
- 파일 복사 불필요 (같은 디렉토리에 배치)

### 5. 설치 프로세스 단순화

**기존 (7단계)**:
1. `/opt` 파일 복사
2. 심볼릭 링크 생성
3. pip install
4. credentials 저장 (XDG 경로)
5. 로그 디렉토리 생성 (XDG 경로)
6. cron 설치/활성화
7. crontab 작업 추가

**신규 (3단계)**:
1. config.json 저장 (같은 디렉토리)
2. cron 설치/활성화 (기존 로직 유지)
3. crontab 작업 추가 (절대경로 + UUID)

**코드 변화**:
- service.py: 442줄 → 315줄 (-29%, -127줄)
- install() 메서드: 7단계 → 3단계

## 결과

### 파일 구조 비교

**기존**:
```
/opt/coupang_coupon_issuer/
├── main.py
├── src/
└── pyproject.toml

/usr/local/bin/coupang_coupon_issuer  # 심볼릭 링크

~/.config/coupang_coupon_issuer/
├── credentials.json
└── coupons.xlsx

~/.local/state/coupang_coupon_issuer/
└── issuer.log
```

**신규**:
```
~/coupang_coupon_issuer/          # 사용자가 원하는 위치
├── coupang_coupon_issuer         # 단일 실행 파일
├── config.json                   # credentials + UUID
├── coupons.xlsx                  # 사용자가 배치
└── issuer.log                    # 자동 생성
```

### 코드 크기 변화

| 파일 | 변경 전 | 변경 후 | 변화 |
|------|--------|--------|------|
| config.py | 172줄 | 205줄 | +33줄 (UUID 추가) |
| service.py | 442줄 | 315줄 | **-127줄 (-29%)** |
| main.py | 306줄 | 242줄 | **-64줄 (-21%)** |
| **전체** | 920줄 | 762줄 | **-158줄 (-17%)** |

### 테스트 부담 감소

| 테스트 유형 | 변경 전 | 변경 후 | 변화 |
|-----------|--------|--------|------|
| 유닛 테스트 | 108개 | 43개 (예상) | **-60%** |
| 통합 테스트 | 80개 | 0개 | **-100%** |

**통합 테스트 삭제 이유**:
- `/opt` 설치 검증 불필요
- Docker + testcontainers 복잡도 제거
- PyInstaller 빌드는 사용자가 직접 수행

### CLI 명령어 변화

| 변경 전 | 변경 후 | 설명 |
|--------|--------|------|
| `sudo coupang_coupon_issuer apply ./coupons.xlsx` | `./coupang_coupon_issuer verify [./coupons.xlsx]` | sudo 불필요, 미리보기 추가 |
| `coupang_coupon_issuer issue` | `./coupang_coupon_issuer issue [--jitter-max 60]` | 전역 명령어 → 상대경로 |
| `sudo coupang_coupon_issuer install ...` | `./coupang_coupon_issuer install ...` | sudo 불필요 (cron만 필요) |
| `sudo coupang_coupon_issuer uninstall` | `./coupang_coupon_issuer uninstall` | 파일 삭제는 사용자가 직접 |

## 장점

### 1. 사용자 경험 개선
- **설치 간소화**: 3단계로 축소
- **Python 불필요**: 단일 실행 파일만으로 동작
- **sudo 최소화**: cron 설치/활성화 시에만 필요
- **디버깅 용이**: 모든 파일이 한 디렉토리

### 2. 개발자 경험 개선
- **코드 간결화**: 17% 코드 감소
- **테스트 부담 감소**: 통합 테스트 제거
- **유지보수 용이**: 복잡한 경로 로직 제거

### 3. 운영 개선
- **디렉토리 이동 대응**: UUID 기반 자동 재설치
- **멀티 설치 지원**: 여러 디렉토리에 독립 설치 가능
- **로그 접근 편의**: `tail -f ./issuer.log`

## 단점 및 대응

### 1. 전역 명령어 제거
**단점**: `coupang_coupon_issuer` → `./coupang_coupon_issuer` 또는 절대경로

**대응**:
- 사용자가 원하면 alias 설정 가능
  ```bash
  echo "alias coupang='~/coupang_coupon_issuer/coupang_coupon_issuer'" >> ~/.bashrc
  ```

### 2. 실행 파일 크기
**단점**: PyInstaller 단일 파일은 10-20MB

**대응**:
- upx 압축 사용 (약 50% 감소)
- 경량 프로그램이므로 허용 가능한 크기

### 3. 디렉토리 이동 시 crontab 수동 갱신 필요
**단점**: 이동 후 재설치 필요 (`install` 재실행)

**대응**:
- UUID 기반 자동 이전 job 제거
- 재설치 가이드 제공
- README에 "디렉토리 고정" 권장사항 명시

## 구현 상세

### ConfigManager 클래스 (config.py)

```python
class ConfigManager:
    """config.json 읽기/쓰기 + UUID 관리"""

    @staticmethod
    def save_config(access_key, secret_key, user_id, vendor_id, installation_id=None):
        """설정 저장 (UUID 포함)"""
        if installation_id is None:
            installation_id = str(uuid.uuid4())

        config = {
            "access_key": access_key,
            "secret_key": secret_key,
            "user_id": user_id,
            "vendor_id": vendor_id,
            "installation_id": installation_id
        }

        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

        os.chmod(CONFIG_FILE, 0o600)
        return installation_id

    @staticmethod
    def get_installation_id():
        """UUID만 반환"""
        try:
            config = ConfigManager.load_config()
            return config.get("installation_id")
        except FileNotFoundError:
            return None
```

### UUID 기반 Cron 관리 (service.py)

```python
def install(access_key, secret_key, user_id, vendor_id, jitter_max=None):
    """cron 작업 등록 + config 저장"""

    # 1. 기존 UUID 확인 및 제거
    existing_uuid = ConfigManager.get_installation_id()
    if existing_uuid:
        CrontabService._remove_crontab_by_uuid(existing_uuid)

    # 2. 새 UUID 생성 및 저장
    new_uuid = ConfigManager.save_config(access_key, secret_key, user_id, vendor_id)

    # 3. cron 설치/활성화 (기존 로직 유지)
    if not CrontabService._detect_cron_system():
        CrontabService._install_cron()
    CrontabService._enable_cron_service()

    # 4. crontab에 절대경로 + UUID 주석 추가
    exe_path = Path(sys.executable).resolve()
    log_path = exe_path.parent / "issuer.log"

    cmd = f"{exe_path} issue"
    if jitter_max:
        cmd += f" --jitter-max {jitter_max}"
    cmd += f" >> {log_path} 2>&1  # coupang_coupon_issuer_job:{new_uuid}"

    cron_entry = f"0 0 * * * {cmd}"
    CrontabService._add_cron_job(cron_entry)
```

## 참조

- **대체된 ADR**:
  - [ADR 008: CLI 구조 재설계](./008-cli-restructuring.md) - apply → verify 변경
  - [ADR 010: Crontab 기반 스케줄링](./010-crontab-service.md) - UUID 추가
  - [ADR 012: XDG Base Directory](./012-xdg-base-directory.md) - 경로 전략 변경

- **유지되는 ADR**:
  - [ADR 009: 엑셀 6컬럼 구조](./009-excel-6-column-structure.md) - 변경 없음
  - [ADR 011: Jitter 기능](./011-jitter-thundering-herd.md) - 변경 없음

## 결론

PyInstaller 단일 실행 파일 배포 전략은 다음을 달성합니다:

1. ✅ **단순함**: 7단계 설치 → 3단계
2. ✅ **경량화**: 코드 17% 감소, 테스트 60% 감소
3. ✅ **자급자족**: Python 의존성 제거
4. ✅ **유연성**: UUID 기반 디렉토리 이동 대응
5. ✅ **가시성**: verify 명령어로 미리보기

이는 "**Simple is Best**" 철학에 부합하며, 프로젝트의 본질(쿠폰 발급)에 집중할 수 있게 합니다.
