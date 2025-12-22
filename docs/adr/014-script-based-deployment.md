# ADR 014: 스크립트 기반 배포 (PyInstaller 제거)

**상태**: 승인됨
**날짜**: 2024-12-21
**대체**: ADR 013 (PyInstaller 단일 실행 파일)

## 배경

ADR 013은 배포 단순화를 위해 PyInstaller 기반 단일 실행 파일 배포를 도입했습니다. 그러나 이 접근 방식은 상당한 복잡성을 초래했습니다:

- **PyInstaller 의존성**: 코드베이스 전체에 `sys.frozen`과 `sys.executable` 체크가 산재
- **느린 테스트**: 통합 테스트에서 PyInstaller 빌드 필요 (6-7분 소요)
- **유연성 부족**: 빌드 시점에 작업 디렉토리가 하드코딩됨
- **재빌드 오버헤드**: 코드 변경 시마다 전체 PyInstaller 재빌드 필요
- **경로 해결 복잡성**: frozen 모드와 개발 모드에서 다른 로직 사용

## 결정

모든 PyInstaller 의존성을 제거하고 스크립트 기반 배포를 사용합니다:

### 1. CLI 인터페이스 변경

모든 명령어에 위치 인자로 디렉토리 추가:

```bash
# 이전 (PyInstaller 바이너리)
./coupang_coupon_issuer install --access-key KEY ...
./coupang_coupon_issuer issue

# 이후 (Python 스크립트)
python3 main.py install . --access-key KEY ...
python3 main.py issue .
python3 main.py verify .
python3 main.py uninstall .
```

**기본 동작**: 디렉토리가 지정되지 않으면 `pwd` (현재 작업 디렉토리) 사용

### 2. 경로 해결

PyInstaller 의존적인 경로 해결을 단순한 함수 기반 접근 방식으로 대체:

```python
# 이전 (config.py)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent.resolve()
else:
    BASE_DIR = Path(__file__).parent.parent.parent.resolve()

CONFIG_FILE = BASE_DIR / "config.json"

# 이후 (config.py)
def get_base_dir(work_dir: Optional[Path] = None) -> Path:
    if work_dir is None:
        return Path.cwd().resolve()
    return Path(work_dir).resolve()

def get_config_file(base_dir: Path) -> Path:
    return base_dir / "config.json"
```

이제 모든 모듈은 `base_dir` 파라미터를 명시적으로 받습니다.

### 3. Cron 작업 형식

바이너리 실행에서 Python 스크립트 실행으로 변경:

```bash
# 이전 (PyInstaller)
0 0 * * * /path/to/coupang_coupon_issuer issue >> /path/to/issuer.log 2>&1

# 이후 (스크립트)
0 0 * * * python3 /path/to/main.py issue /work/dir >> /work/dir/issuer.log 2>&1
```

### 4. 모듈 업데이트

**ConfigManager** (`config.py`):
- 모든 메서드가 이제 첫 번째 파라미터로 `base_dir: Path`를 받음
- `save_config(base_dir, ...)`
- `load_config(base_dir)`
- `load_credentials(base_dir)`
- `get_installation_id(base_dir)`
- `load_credentials_to_env(base_dir)`

**CouponIssuer** (`issuer.py`):
- 생성자가 `base_dir: Optional[Path] = None`을 받음
- 입력 파일로 `get_excel_file(base_dir)` 사용

**CrontabService** (`service.py`):
- `install(base_dir, ...)` - 첫 번째 파라미터로 base_dir 받음
- `uninstall(base_dir)` - base_dir 파라미터 받음
- Cron 명령어는 `python3 main.py issue {base_dir}` 사용

**CLI** (`main.py`):
- 모든 서브명령어가 디렉토리 인자를 받음 (위치 인자, install을 제외하고 선택적)
- `verify [directory] [file]`
- `issue [directory] [--jitter-max N]`
- `install directory --access-key ... `
- `uninstall [directory]`

### 5. 테스트 인프라

**유닛 테스트**:
- `mock_frozen` fixture 제거 (더 이상 불필요)
- `mock_config_paths`를 `tmp_path`를 직접 반환하도록 단순화
- 모든 테스트가 `base_dir`를 명시적으로 전달

**통합 테스트** (향후):
- PyInstaller 빌드 단계 제거
- Docker에서 `python3 main.py` 직접 실행
- 예상 속도 향상: 6-7분 → ~1-2분

## 결과

### 긍정적

1. **더 단순한 코드베이스**: PyInstaller 관련 코드 ~100줄 제거
2. **빠른 개발**: 코드 변경 시 재빌드 불필요
3. **빠른 테스트**: 통합 테스트 3-5배 빠름 (PyInstaller 빌드 불필요)
4. **더 유연함**: 작업 디렉토리를 런타임에 지정 가능
5. **표준 Python**: 개발 시 `pip install -e .` 사용 가능
6. **쉬운 디버깅**: Python 직접 실행, 전체 스택 트레이스 확인 가능

### 부정적

1. **Python 필요**: 대상 시스템에 Python 3.10+ 설치 필요
2. **의존성 필요**: `pip install requests openpyxl` 필요
3. **독립 실행 파일 아님**: 단일 실행 파일이 아님

### 마이그레이션

**마이그레이션 불필요** - 프로젝트가 프로덕션에 배포된 적 없음.

향후 배포 시:
1. Python 3.10+ 설치 확인
2. `pip install -e .` 실행 또는 의존성 수동 설치
3. `python3 main.py install . --access-key ...` 사용

## 구현

### 수정된 파일

1. **config.py**: `sys.frozen` 체크 제거, 경로 함수 추가
2. **main.py**: CLI에 디렉토리 인자 추가, PyInstaller 체크 제거
3. **service.py**: Cron 형식을 Python 스크립트 실행으로 변경
4. **issuer.py**: 생성자에 `base_dir` 파라미터 추가
5. **conftest.py**: PyInstaller mock fixture 제거
6. **tests/unit/*.py**: 모든 테스트가 `base_dir`를 전달하도록 업데이트

### UUID 추적 (변경 없음)

UUID 기반 cron 작업 추적은 여전히 동일하게 작동:
- `config.json` 형식 변경 없음
- UUID가 설치를 식별
- Uninstall은 여전히 UUID를 사용하여 cron 작업 검색 및 제거
- 디렉토리 이동 시 재설치 필요 (UUID 불일치 시 자동 정리)

## 고려된 대안

1. **PyInstaller를 `--dir` 옵션과 함께 유지**: 여전히 `sys.frozen` 체크 필요, 테스트 속도 문제 해결 안 됨
2. **패키지 설치만 사용**: 사용자가 `pip install` 실행 필요, 양쪽 모두 허용하는 것보다 유연성 떨어짐
3. **Docker 기반 배포**: 단순한 cron 작업에는 과도함

## 참조

- ADR 013: PyInstaller 단일 실행 파일 (대체됨)
- 이슈: 느린 통합 테스트 (6-7분)
- 목표: PyInstaller(선택적)와 스크립트 실행 모두 지원
