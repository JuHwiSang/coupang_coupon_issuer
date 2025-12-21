# ADR 012: XDG Base Directory Specification 적용

> **⚠️ DEPRECATED**: 이 ADR은 ADR 013 (PyInstaller 단일 실행 파일)로 완전히 대체되었습니다.
>
> 날짜: 2024-12-21
> 사유: XDG 표준 준수 → 실행 파일 위치 기반 단순 구조로 전환
> 변경사항:
> - XDG_CONFIG_HOME, XDG_STATE_HOME 사용 중단
> - `~/.config/coupang_coupon_issuer/` → `<실행파일위치>/`
> - `~/.local/state/coupang_coupon_issuer/` → `<실행파일위치>/`
>
> 참조: [ADR 013: PyInstaller 단일 실행 파일 배포](./013-pyinstaller-single-binary.md)

**상태**: ~~승인됨~~ **대체됨**
**날짜**: 2024-12-20
**결정자**: 프로젝트 오너

## 컨텍스트

기존 구현은 모든 사용자 설정 파일을 `/etc/coupang_coupon_issuer/`에 저장했습니다. 이는 다음 문제를 야기했습니다:

### 문제점

1. **다중 사용자 불가**: `/etc`는 시스템 전역 디렉토리로, 사용자별 독립 설정 불가능
2. **Root 권한 필요**: `apply` 명령어(엑셀 파일 적용)도 sudo 필요
3. **XDG 비준수**: Linux 표준 디렉토리 구조(XDG Base Directory Specification) 미준수
4. **파일 소유권 문제**: Root 소유 파일로 일반 사용자 수정 불가능

### 기존 구조

```
/etc/coupang_coupon_issuer/          # ❌ 시스템 경로
├── credentials.json                 # API 키 (root 소유, 600)
└── coupons.xlsx                     # 쿠폰 정의 (root 소유, 600)

~/.local/state/coupang_coupon_issuer/ # ✅ 이미 XDG 준수
└── issuer.log

/opt/coupang_coupon_issuer/          # 프로그램 설치
/usr/local/bin/coupang_coupon_issuer # 전역 명령어
```

## 결정사항

### XDG Base Directory Specification 준수

**Configuration files**: `~/.config/coupang_coupon_issuer/`
- credentials.json (API 키)
- coupons.xlsx (쿠폰 정의, 설정으로 취급)

**State files**: `~/.local/state/coupang_coupon_issuer/`
- issuer.log (기존 유지)

**Program files**: `/opt/coupang_coupon_issuer/` (변경 없음)

**Global command**: `/usr/local/bin/coupang_coupon_issuer` (변경 없음)

### 환경 변수 지원

사용자가 XDG 환경 변수로 경로 커스터마이징 가능:

- `XDG_CONFIG_HOME`: 기본 `~/.config` 대신 사용자 정의 경로 사용
- `XDG_STATE_HOME`: 기본 `~/.local/state` 대신 사용자 정의 경로 사용

### 구현 세부사항

```python
# config.py
def _get_xdg_config_home() -> Path:
    """XDG_CONFIG_HOME 환경 변수 또는 기본값 (~/.config) 반환"""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config)
    return Path.home() / ".config"

def _get_xdg_state_home() -> Path:
    """XDG_STATE_HOME 환경 변수 또는 기본값 (~/.local/state) 반환"""
    xdg_state = os.environ.get("XDG_STATE_HOME")
    if xdg_state:
        return Path(xdg_state)
    return Path.home() / ".local" / "state"

# 경로 상수
CONFIG_DIR = _get_xdg_config_home() / SERVICE_NAME
CONFIG_FILE = CONFIG_DIR / "credentials.json"
EXCEL_INPUT_FILE = CONFIG_DIR / "coupons.xlsx"

LOG_DIR = _get_xdg_state_home() / SERVICE_NAME
LOG_FILE = LOG_DIR / "issuer.log"
```

## 근거

### XDG 준수의 장점

1. **다중 사용자 지원**: 각 사용자가 독립적으로 설정 관리 가능
2. **표준 준수**: Linux FHS(Filesystem Hierarchy Standard) 및 XDG 표준 준수
3. **권한 단순화**: `apply` 명령어 sudo 불필요 (사용자 홈 디렉토리 쓰기)
4. **백업 용이**: `~/.config` 백업 시 설정 자동 포함
5. **개발자 친화적**: 표준 경로로 도구 통합 용이

### Permission Matrix

| 명령어 | 이전 | 이후 | 이유 |
|--------|------|------|------|
| `apply` | sudo 필요 | **sudo 불필요** | `~/.config` 쓰기 (사용자 권한) |
| `issue` | sudo 불필요 | sudo 불필요 | 변경 없음 |
| `install` | sudo 필요 | sudo 필요 | `/opt` 설치, pip 의존성 |
| `uninstall` | sudo 필요 | sudo 필요 | `/opt` 삭제 |

## 대안

### 1. `/etc` 유지 + 사용자별 서브디렉토리

```
/etc/coupang_coupon_issuer/users/$USER/
├── credentials.json
└── coupons.xlsx
```

**거부 이유**: 여전히 sudo 필요, 비표준 구조

### 2. ~/. coupang_coupon_issuer/ (dot directory)

```
~/.coupang_coupon_issuer/
├── credentials.json
├── coupons.xlsx
└── issuer.log
```

**거부 이유**: XDG 비준수, 홈 디렉토리 오염 (dot file 증가)

### 3. 환경 변수만 사용 (커스텀 변수)

```bash
export COUPANG_CONFIG_DIR=/custom/path
```

**거부 이유**: 표준 없음, 사용자가 직접 환경 변수 설정 필요 (UX 저하)

## 영향

### 긍정적 영향

✅ **다중 사용자 지원**: 진정한 의미의 멀티 유저 환경
✅ **UX 개선**: `apply` 명령어 sudo 불필요
✅ **표준 준수**: XDG Base Directory Specification 준수
✅ **백업/복원 용이**: `~/.config` 백업 시 설정 자동 포함
✅ **파일 소유권 명확**: user:user (이전에는 root:root)

### 부정적 영향

⚠️ **Breaking change**: 기존 사용자는 파일 경로 변경 필요
- **완화**: 마이그레이션 불필요 (아직 배포 전)

### 코드 변경 사항

**수정된 파일**:
- `src/coupang_coupon_issuer/config.py`: XDG helper 함수 추가 (~30줄)
- `src/coupang_coupon_issuer/config.py`: 경로 상수 변경 (~5줄)

**테스트 추가**:
- `tests/unit/test_config.py`: XDG 환경 변수 override 테스트 (+8개)
- `tests/unit/test_config.py`: 경로 assertion 수정 (~5개)
- `tests/integration/`: `/etc` → `~/.config` 경로 변경 (~11개)

**총 테스트**: 188개 → 196개 (+8개)

### 문서 변경 사항

- **CLAUDE.md**: 프로젝트 구조, 환경 변수 섹션 업데이트
- **DEV_LOG.md**: 파일 경로 규칙 업데이트
- **ADR 012**: 본 문서

### 변경되지 않음

- 쿠폰 발급 로직 (issuer.py)
- API 인증 (coupang_api.py)
- Cron 스케줄링 (service.py 핵심 로직)
- 프로그램 설치 위치 (`/opt`)
- 전역 명령어 (`/usr/local/bin/coupang_coupon_issuer`)

## 결과

### 새 디렉토리 구조

```
~/.config/coupang_coupon_issuer/     # XDG_CONFIG_HOME
├── credentials.json                 # API 키 (user 소유, 600)
└── coupons.xlsx                     # 쿠폰 정의 (user 소유, 600)

~/.local/state/coupang_coupon_issuer/ # XDG_STATE_HOME
└── issuer.log                       # 로그 파일 (user 소유, 644)

/opt/coupang_coupon_issuer/          # 프로그램 설치 (변경 없음)
/usr/local/bin/coupang_coupon_issuer # 전역 명령어 (변경 없음)
```

### 사용자 워크플로우 변경

**이전**:
```bash
# apply 명령어에 sudo 필요
sudo coupang_coupon_issuer apply ./coupons.xlsx

# 파일 위치: /etc/coupang_coupon_issuer/coupons.xlsx
```

**이후**:
```bash
# apply 명령어 sudo 불필요!
coupang_coupon_issuer apply ./coupons.xlsx

# 파일 위치: ~/.config/coupang_coupon_issuer/coupons.xlsx
```

### 환경 변수 Override 예시

```bash
# 커스텀 설정 디렉토리 사용
export XDG_CONFIG_HOME=/custom/config
coupang_coupon_issuer apply ./coupons.xlsx
# → /custom/config/coupang_coupon_issuer/coupons.xlsx

# 커스텀 로그 디렉토리 사용
export XDG_STATE_HOME=/var/log/myapp
coupang_coupon_issuer issue
# → /var/log/myapp/coupang_coupon_issuer/issuer.log
```

## 참고 문서

- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html)
- [Linux Filesystem Hierarchy Standard](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html)
- [ArchWiki: XDG Base Directory](https://wiki.archlinux.org/title/XDG_Base_Directory)
- [ADR 010: Crontab 기반 스케줄링](./010-crontab-service.md)

## 관련 이슈

- 멀티 유저 지원 요구사항
- Linux 표준 준수
- UX 개선 (`apply` 명령어 sudo 제거)
