# ADR 010: Crontab 기반 스케줄링

**상태**: 승인됨
**날짜**: 2024-12-19
**결정자**: 프로젝트 오너
**대체**: ADR 005 (systemd 서비스)

## 컨텍스트

기존 구현은 systemd와 custom scheduler를 사용하여 매일 0시에 쿠폰을 발급했습니다. Scheduler는 30초마다 폴링하여 자정을 감지했습니다.

이 방식의 문제점:

1. **복잡도**: systemd 서비스 + 30초 폴링 스케줄러 + 로그 관리
2. **리소스 사용**: 24시간 프로세스 실행 (하루 1회 작업을 위해)
3. **테스트 어려움**: testcontainers에서 systemd 실행 불안정 (privileged mode, cgroup 마운트 필요)
4. **로그 접근성**: journalctl은 root/sudo 필요

## 결정사항

### Crontab 기반 스케줄링으로 전환

**아키텍처**:
- **스케줄링**: Cron (매일 00:00 실행)
- **실행**: `issue` 명령어 직접 호출
- **로그**: 사용자 수준 디렉토리 (`~/.local/state/coupang_coupon_issuer/`)
- **데몬 불필요**: 필요할 때만 프로세스 실행

**Cron Job 형식**:
```bash
0 0 * * * /usr/bin/python3 /opt/coupang_coupon_issuer/main.py issue >> ~/.local/state/coupang_coupon_issuer/issuer.log 2>&1  # coupang_coupon_issuer_job
```

**마커 주석**: `# coupang_coupon_issuer_job`으로 job 식별

### 설치 프로세스

1. 파일 복사 (`/opt/coupang_coupon_issuer/`)
2. 심볼릭 링크 생성 (`/usr/local/bin/coupang_coupon_issuer`)
3. Python 의존성 설치 (requests, openpyxl)
4. Credentials 저장 (`/etc/coupang_coupon_issuer/credentials.json`)
5. Cron 감지/설치/활성화
6. 로그 디렉토리 생성
7. Root crontab에 job 추가

### 플랫폼 지원

- **Ubuntu/Debian**: `apt-get install cron` (자동)
- **RHEL/CentOS 7**: `yum install cronie` (자동)
- **RHEL/CentOS 8+**: `dnf install cronie` (자동)

### 서비스 관리

```bash
# Cron 스케줄 확인
crontab -l

# 로그 확인
tail -f ~/.local/state/coupang_coupon_issuer/issuer.log

# 수동 실행 (테스트용)
coupang_coupon_issuer issue

# Cron job 수동 편집
crontab -e
```

## 근거

### Cron의 장점

1. **단순성**: Custom scheduler 불필요, 폴링 루프 제거
2. **표준화**: 모든 Linux 시스템에 기본 포함
3. **리소스 효율**: 필요할 때만 실행 (하루 1분 vs 24시간)
4. **사용자 친화적 로그**: Plain text 파일, sudo 불필요
5. **테스트 용이**: testcontainers에서 privileged mode 불필요

### Systemd vs Cron 비교

| 측면 | systemd (이전) | cron (현재) |
|------|---------------|-------------|
| 복잡도 | 높음 (서비스 + 스케줄러) | 낮음 (cron만) |
| 리소스 | 24/7 프로세스 | 온디맨드 |
| 로그 접근 | journalctl (root) | tail -f (사용자) |
| 플랫폼 | systemd만 | 모든 Linux |
| 디버깅 | 다층 구조 | 직접 실행 |
| 테스트 | 불안정 (privileged) | 안정 |
| 타이밍 정밀도 | 30초 이내 | 1분 정밀도 |

### 타이밍 정밀도

- **이전**: 30초 폴링 → 최대 30초 지연
- **현재**: Cron 1분 정밀도 → 00:00 정확히 실행
- **판단**: 매일 쿠폰 발급은 1분 정밀도로 충분

## 대안

1. **Systemd 유지**
   - 단점: 복잡도, 리소스 낭비, 테스트 불안정
   - 거부 사유: 단순 일일 작업에 과도

2. **APScheduler** (Python 스케줄링 라이브러리)
   - 단점: 추가 의존성, 여전히 24/7 프로세스 필요
   - 거부 사유: Cron으로 충분

3. **at 명령어**
   - 단점: 반복 작업 부적합
   - 거부 사유: 일회성 작업용

4. **Systemd timers**
   - 단점: systemd 의존성 유지
   - 거부 사유: Cron보다 복잡

## 영향

### 코드 변경

- **제거**: `scheduler.py` (108 라인), `serve` 명령어
- **대체**: `SystemdService` → `CrontabService` (~200 라인)
- **순 감소**: 코드 단순화 (-79 라인)

### 테스트 변경

- **유닛 테스트**: test_service.py 재작성, test_scheduler.py 삭제
- **통합 테스트**: testcontainers 단순화 (systemd 불필요)
- **안정성**: privileged mode 제거로 테스트 안정화

### 로그 변경

- **이전**: journalctl (systemd 통합, root 필요)
- **현재**: `~/.local/state/coupang_coupon_issuer/issuer.log` (사용자 접근)
- **로테이션**: 사용자가 필요시 logrotate 설정 가능

### 마이그레이션 경로

기존 systemd 사용자:

1. `sudo coupang_coupon_issuer uninstall` (systemd 제거)
2. `sudo coupang_coupon_issuer install ...` (cron 설치)
3. 기존 credentials/excel 재사용 가능
4. 기존 로그: journalctl에 유지 (읽기 전용)
5. 새 로그: `~/.local/state/coupang_coupon_issuer/issuer.log`

## 결과

### 긍정적

- 코드베이스 단순화 (scheduler 제거)
- 리소스 사용량 감소 (24/7 → 온디맨드)
- 로그 접근성 향상 (sudo 불필요)
- 플랫폼 호환성 향상 (모든 Linux)
- 테스트 안정성 향상 (privileged mode 불필요)
- 디버깅 용이성 (직접 실행)

### 부정적

- Cron 정밀도 1분 (30초 → 1분)
  - 완화: 매일 쿠폰 발급은 1분 정밀도로 충분
- 실패 시 내장 재시도 없음
  - 완화: 로그 확인 및 수동 재시도 가능
- Cron 설치 필요
  - 완화: 주요 배포판 자동 설치 지원

### 변경되지 않음

- 쿠폰 발급 로직 (`issuer.py`)
- API 인증 (`coupang_api.py`)
- Credentials 관리 (`config.py` 일부)
- Excel 검증 (`apply` 명령어)

## 참고 문서

- [ADR 005: systemd 서비스](./005-systemd-service.md) (대체됨)
- Cron 문서: `man 5 crontab`
- XDG Base Directory Specification (로그 위치)
