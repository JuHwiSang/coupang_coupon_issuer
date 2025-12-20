# ADR 011: Jitter for Thundering Herd Prevention

**Status**: Approved
**Date**: 2024-12-20
**Decision Maker**: Project Owner

## Context

여러 인스턴스의 쿠폰 발급기가 자정(00:00)에 동시 실행되면 Coupang API에 부하가 집중되는 Thundering herd 현상이 발생할 수 있습니다.

**문제점:**
1. **동시 요청**: 모든 인스턴스가 같은 시각에 API를 호출
2. **API Rate Limiting**: 429 에러 또는 서비스 성능 저하 가능성
3. **리소스 경합**: 데이터베이스/네트워크 병목 현상

**발생 시나리오:**
- 멀티 리전 배포
- 여러 판매자가 동일 인프라 사용
- 수평 확장 환경

## Decision

**안전한 폴링 기반 Jitter 기능 추가**

### 설계 원칙

1. **CLI 기반 설정** (credentials.json 사용 안 함)
2. **안전한 폴링 루프** (1초 간격, 긴 블로킹 sleep 방지)
3. **옵트인 방식** (기본은 jitter 없음, 하위 호환성 유지)
4. **설정 가능한 범위** (1-120분)

### 사용법

```bash
# 수동 실행 (jitter 없음, 기본값)
coupang_coupon_issuer issue

# 수동 실행 (jitter 60분)
coupang_coupon_issuer issue --jitter-max 60

# 서비스 설치 (jitter 활성화)
sudo coupang_coupon_issuer install \
  --access-key YOUR_KEY \
  --secret-key YOUR_SECRET \
  --user-id YOUR_USER_ID \
  --vendor-id YOUR_VENDOR_ID \
  --jitter-max 60
```

### Cron Job 형태

```bash
# Jitter 없음 (기존)
0 0 * * * /usr/bin/python3 /opt/coupang_coupon_issuer/main.py issue >> ...

# Jitter 활성화
0 0 * * * /usr/bin/python3 /opt/coupang_coupon_issuer/main.py issue --jitter-max 60 >> ...
```

## Rationale

### 왜 폴링 루프인가?

**안전성 우선:**
```python
# ❌ 위험: 긴 블로킹 sleep
time.sleep(random_minutes * 60)  # 최대 2시간 동안 중단 불가

# ✅ 안전: 1초 간격 폴링
while datetime.now() < target_time:
    time.sleep(1)  # 1초만 블로킹
```

**장점:**
- **중단 가능성**: KeyboardInterrupt에 최대 1초 내 응답
- **적응성**: 시스템 시계 변경에 대응 (매 루프마다 `datetime.now()` 재확인)
- **모니터링 가능**: 시작/종료 로그로 상태 추적

### 왜 CLI 인자인가?

**투명성:**
- `crontab -l` 명령어로 jitter 설정 확인 가능
- 환경변수보다 명시적

**유연성:**
- 인스턴스마다 다른 jitter 범위 설정 가능
- 재설치 없이 crontab 수정으로 조정 가능

**분리:**
- credentials.json은 인증 전용 (ADR 003 준수)
- 설정과 인증의 명확한 분리

### 왜 1-120분 범위인가?

- **하한 (1분)**: 최소 의미 있는 jitter
- **상한 (120분)**: 일일 쿠폰 발급에 적절한 최대 지연 (2시간 이내)
- **기본값 (없음)**: 하위 호환성, 명시적 opt-in

## Implementation

### 새 파일

**`src/coupang_coupon_issuer/jitter.py`** (~100 lines):
```python
from random import randint
from time import sleep
from datetime import datetime, timedelta

class JitterScheduler:
    POLL_INTERVAL_SECONDS = 1

    def __init__(self, max_jitter_minutes: int):
        if not (1 <= max_jitter_minutes <= 120):
            raise ValueError("1-120 범위여야 합니다")
        self.max_jitter_minutes = max_jitter_minutes

    def wait_with_jitter(self) -> None:
        jitter_minutes = randint(0, self.max_jitter_minutes)
        target_time = datetime.now() + timedelta(minutes=jitter_minutes)

        # 로그: 시작
        print(f"[{timestamp}] Jitter 대기 시작 (목표: {target_time}, 지연: +{jitter_minutes}분)")

        if jitter_minutes == 0:
            print(f"[{timestamp}] Jitter가 0분입니다. 즉시 실행합니다.")
            return

        # 폴링 루프
        try:
            while datetime.now() < target_time:
                sleep(1)
        except KeyboardInterrupt:
            print(f"\n[{timestamp}] Jitter 대기가 중단되었습니다.")
            raise

        # 로그: 완료
        print(f"[{timestamp}] Jitter 대기 완료. 쿠폰 발급을 시작합니다.")
```

### 수정 파일

**`main.py`** (~30 lines):
- `issue` / `install` 서브파서에 `--jitter-max` 옵션 추가
- `cmd_issue()`: args 인자 받아서 JitterScheduler 호출
- `cmd_install()`: jitter_max 검증 및 전달

**`src/coupang_coupon_issuer/service.py`** (~15 lines):
- `install()`: jitter_max 파라미터 추가
- Cron job 생성 시 `--jitter-max` 옵션 포함
- 설치 완료 메시지에 jitter 정보 표시

## Alternatives Considered

### 1. 긴 블로킹 sleep

```python
# ❌ Rejected
time.sleep(random.randint(0, 3600))  # 최대 1시간 블로킹
```

**문제점:**
- KeyboardInterrupt에 응답 불가 (최대 1시간 대기)
- 프로세스 상태 확인 어려움
- 시스템 시계 변경에 적응 불가

### 2. 환경변수 설정

```bash
# ❌ Rejected
export JITTER_MAX_MINUTES=60
coupang_coupon_issuer issue
```

**문제점:**
- crontab에 표시되지 않음 (투명성 부족)
- 환경변수 관리 복잡도 증가
- 디버깅 어려움

### 3. credentials.json 설정

```json
{
  "access_key": "...",
  "jitter_max_minutes": 60
}
```

**문제점:**
- ADR 003 위반 (인증 전용 파일)
- 설정과 인증의 혼재
- 인스턴스별 다른 jitter 설정 어려움

### 4. APScheduler 라이브러리 사용

**문제점:**
- 추가 의존성
- 24/7 백그라운드 프로세스 필요
- 단순한 일일 작업에 과도한 복잡성

## Impact

### Positive

- ✅ Thundering herd 현상 방지
- ✅ API 안정성 향상
- ✅ 하위 호환성 유지 (기본값: jitter 없음)
- ✅ 안전한 폴링으로 중단 가능성 보장
- ✅ 설정 투명성 (crontab에 표시)

### Negative

- ⚠️ 약간의 복잡도 증가 (~150 lines 코드)
- ⚠️ 실행 시간 가변성 (일일 작업이므로 허용 가능)
- ⚠️ 추가 테스트 필요 (~27개 테스트)

### Unchanged

- ✅ 기본 동작 (jitter 옵션 없으면 즉시 실행)
- ✅ 쿠폰 발급 로직
- ✅ Credentials 관리
- ✅ 로깅 인프라

## Monitoring

### Crontab 확인

```bash
crontab -l
# 출력 예시:
# 0 0 * * * /usr/bin/python3 /opt/coupang_coupon_issuer/main.py issue --jitter-max 60 >> ...
```

### 로그 확인

```bash
tail -f ~/.local/state/coupang_coupon_issuer/issuer.log
```

**로그 예시:**
```
[2024-12-20 00:00:00] Jitter 대기 시작 (목표: 00:42:18, 지연: +42분)
[2024-12-20 00:42:18] Jitter 대기 완료. 쿠폰 발급을 시작합니다.
[2024-12-20 00:42:18] 쿠폰 발급 작업 시작
[2024-12-20 00:42:19] [1] 쿠폰A (즉시할인) 발급 중...
[2024-12-20 00:42:20] [1] 성공: 즉시할인쿠폰 생성 완료
```

## Edge Cases

1. **Jitter = 0 (랜덤 결과)**: 즉시 실행 로그 출력
2. **잘못된 범위 (--jitter-max 150)**: 검증 실패, exit(1)
3. **KeyboardInterrupt**: 안전 종료, exit(130)
4. **시스템 시계 변경**: 각 폴링마다 `datetime.now()` 재확인으로 대응
5. **하위 호환**: jitter 옵션 없으면 기존 동작 유지

## Performance

- **CPU**: 1초당 1회 wake-up, ~0.001ms/check → 무시 가능
- **메모리**: JitterScheduler 인스턴스 ~1KB
- **로그**: 시작/종료만 출력 (2 lines)

## Testing

### 유닛 테스트 (14개)
- 초기화 검증 (6개)
- Zero jitter (1개)
- 폴링 로직 (5개)
- Timestamp (2개)

### 통합 테스트 (예정)
- install with/without jitter
- issue command 타이밍 검증
- Crontab 항목 확인

## References

- [Wikipedia: Thundering Herd Problem](https://en.wikipedia.org/wiki/Thundering_herd_problem)
- [AWS Best Practices: Jitter and Backoff](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [Google SRE Book: Load Management](https://sre.google/sre-book/handling-overload/)

## Related ADRs

- ADR 003: API Authentication (credentials.json은 인증 전용)
- ADR 010: Crontab 기반 스케줄링 (Jitter는 이 위에 구현)
