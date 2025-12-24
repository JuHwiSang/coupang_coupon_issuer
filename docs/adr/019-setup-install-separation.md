# ADR 019: setup/install 명령어 분리

**날짜**: 2024-12-24  
**상태**: Accepted  
**결정자**: Development Team

## 컨텍스트

기존 `install` 명령어는 다음 두 가지 작업을 모두 수행했습니다:

1. **시스템 레벨 작업** (sudo 필요):
   - Cron 데몬 감지/설치
   - Cron 서비스 활성화

2. **사용자 레벨 작업** (sudo 불필요):
   - config.json 생성 (API 키 저장)
   - 사용자 crontab에 job 등록

이로 인해 다음과 같은 문제가 발생했습니다:

### 문제점

1. **파일 권한 문제**:
   ```bash
   sudo python3 main.py install ~/my-coupons
   ```
   - config.json이 root 소유로 생성됨
   - crontab이 root 사용자에 등록됨
   - 로그 파일도 root 소유로 생성됨
   - 일반 사용자가 파일 수정/삭제 불가

2. **불명확한 책임**:
   - 하나의 명령어가 시스템/사용자 레벨 작업을 모두 수행
   - sudo가 필요한 부분과 불필요한 부분이 혼재
   - 사용자가 언제 sudo를 사용해야 하는지 불명확

3. **재설치 시 불편함**:
   - 재설치할 때마다 불필요하게 Cron 설치 체크
   - 시스템 준비는 한 번만 하면 되는데 매번 반복

## 결정

`install` 명령어를 두 개로 분리합니다:

### 1. `setup` 명령어 (신규)

**역할**: 시스템 준비 (sudo 필요, 최초 1회만)

```bash
sudo python3 main.py setup
```

**수행 작업**:
- Cron 데몬 감지
- 미설치 시 자동 설치 (apt/dnf/yum)
- Cron 서비스 활성화 및 시작

**특징**:
- 디렉토리 인자 불필요 (시스템 전체 설정)
- 멱등성 보장 (여러 번 실행해도 안전)
- 시스템에 한 번만 실행하면 됨

### 2. `install` 명령어 (수정)

**역할**: 서비스 설치 (sudo 불필요, 디렉토리별)

```bash
python3 main.py install ~/my-coupons
```

**수행 작업**:
- Cron 설치 확인 (미설치 시 에러 + setup 안내)
- config.json 생성 (API 키 저장, UUID 생성)
- 사용자 crontab에 job 추가
- 기존 설치 제거 후 재등록 (UUID 기반)

**변경사항**:
- Cron 설치/활성화 로직 제거
- Cron 미설치 시 친절한 에러 메시지:
  ```
  Cron이 설치되어 있지 않습니다.
  먼저 다음 명령어를 실행하세요:
    sudo python3 main.py setup
  ```

## 구현

### service.py

```python
class CrontabService:
    @staticmethod
    def setup() -> None:
        """시스템 준비: Cron 설치 및 활성화 (sudo 필요)"""
        # Cron 감지
        cron_system = CrontabService._detect_cron_system()
        
        if cron_system is None:
            # 미설치 시 자동 설치
            CrontabService._install_cron()
        else:
            print(f"Cron이 이미 설치되어 있습니다: {cron_system}")
        
        # 서비스 활성화
        CrontabService._enable_cron_service()

    @staticmethod
    def install(...) -> None:
        """서비스 설치: config.json + crontab 등록 (sudo 불필요)"""
        # Cron 설치 확인
        if CrontabService._detect_cron_system() is None:
            raise RuntimeError(
                "Cron이 설치되어 있지 않습니다.\n"
                "먼저 다음 명령어를 실행하세요:\n"
                "  sudo python3 main.py setup"
            )
        
        # config.json 생성 + crontab 등록
        # ...
```

### main.py

```python
def cmd_setup(args) -> None:
    """시스템 준비: Cron 설치 및 활성화 (sudo 필요)"""
    try:
        CrontabService.setup()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

# CLI 파서에 setup 서브커맨드 추가
setup_parser = subparsers.add_parser(
    "setup",
    help="시스템 준비 (Cron 설치, sudo 필요)"
)
```

## 결과

### 장점

1. **파일 권한 정상화**:
   - config.json, 로그 파일이 일반 사용자 소유로 생성
   - 일반 사용자가 파일 수정/삭제 가능

2. **Crontab 정상화**:
   - root가 아닌 일반 사용자 crontab에 등록
   - 사용자별로 독립적인 스케줄 관리

3. **명확한 책임 분리**:
   - setup: 시스템 레벨 작업 (sudo 필요)
   - install: 사용자 레벨 작업 (sudo 불필요)
   - 각 명령어의 역할이 명확함

4. **더 나은 사용자 경험**:
   - sudo가 필요한 부분만 명확히 표시
   - 재설치 시 불필요한 시스템 체크 제거
   - 에러 메시지가 해결 방법 제시

### 단점

1. **설치 단계 증가**:
   - 기존: 1단계 (install)
   - 신규: 2단계 (setup → install)
   - 하지만 setup은 최초 1회만 실행

2. **하위 호환성 깨짐**:
   - 기존 사용자는 새로운 워크플로우 학습 필요
   - 문서 업데이트로 해결

## 사용자 워크플로우

### Before (기존)

```bash
# 문제: sudo로 실행 → 모든 파일이 root 소유
sudo python3 main.py install ~/my-coupons
```

### After (신규)

```bash
# 1단계: 시스템 준비 (최초 1회만)
sudo python3 main.py setup

# 2단계: 서비스 설치 (일반 사용자 권한)
python3 main.py install ~/my-coupons
```

## 관련 문서

- [ADR 014: 스크립트 기반 배포](014-script-based-deployment.md) - 기본 CLI 구조
- [ADR 010: Crontab 기반 스케줄링](010-crontab-service.md) - Cron 관리 전략
