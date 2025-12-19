# ADR 005: Linux systemd 서비스

> **⚠️ DEPRECATED**: 이 ADR은 ADR 010 (crontab-service)로 대체되었습니다.
>
> 날짜: 2024-12-19
> 사유: systemd 복잡도 및 테스트 불안정성
> 참조: [ADR 010: Crontab 기반 스케줄링](./010-crontab-service.md)

**상태**: ~~승인됨~~ **대체됨**
**날짜**: 2024-12-16
**결정자**: 프로젝트 오너

## 컨텍스트

매일 0시에 자동으로 쿠폰을 발급해야 합니다. Linux 서버 환경에서 안정적으로 동작하는 데몬 서비스가 필요합니다.

## 결정사항

### 플랫폼 선택: systemd

Linux systemd를 사용하여 서비스 구현:

- **서비스명**: `coupang_coupon_issuer`
- **설정 위치**: `/etc/coupang_coupon_issuer/credentials.json`
- **로깅**: journalctl 사용

### 스케줄링 전략

cron 대신 자체 스케줄러 구현:

```python
# scheduler.py
CHECK_INTERVAL = 30  # 30초마다 체크

while True:
    now = datetime.now()
    if now.hour == 0 and now.minute == 0:
        # 쿠폰 발급 실행
        issuer.issue()
        time.sleep(60)  # 중복 실행 방지
    time.sleep(CHECK_INTERVAL)
```

**근거**:
- systemd 서비스가 항상 실행 중이므로 cron보다 응답성 좋음
- 로그가 journalctl에 통합되어 관리 편의성 향상
- 30초 간격으로 0시를 감지 (최대 30초 지연)

### 설정 파일 보안

```python
# 파일 위치
CONFIG_DIR = Path("/etc") / SERVICE_NAME
CONFIG_FILE = CONFIG_DIR / "credentials.json"

# 파일 권한 (root만 읽기 가능)
os.chmod(CONFIG_FILE, 0o600)
```

### 서비스 관리 명령어

```bash
# 설치 (service.py에서 자동화)
coupang-coupon-issuer install

# 상태 확인
systemctl status coupang_coupon_issuer

# 로그 확인
journalctl -u coupang_coupon_issuer --since "1 hour ago"

# 재시작
systemctl restart coupang_coupon_issuer

# 제거
coupang-coupon-issuer uninstall
```

## 근거

1. **안정성**: systemd의 자동 재시작, 장애 복구 기능 활용
2. **표준화**: 대부분의 Linux 배포판이 systemd 사용
3. **로깅 통합**: journalctl로 모든 로그 중앙 관리
4. **보안**: credentials.json을 /etc 아래에 저장하고 권한 제한

## 대안

1. **cron**: 매일 0시에 스크립트 실행
   - 단점: 실패 시 재시도 로직 부재, 로그 관리 어려움 (거부됨)

2. **Docker 컨테이너**: Docker + cron
   - 단점: 불필요한 복잡도, 단순 스케줄러에 과도함 (거부됨)

3. **APScheduler**: Python 스케줄링 라이브러리
   - 단점: 추가 의존성, systemd로 충분함 (거부됨)

## 영향

- service.py에 systemd 유닛 파일 생성 로직 구현
- scheduler.py에 0시 감지 루프 구현
- journalctl 호환 로깅 (이모지 금지, 타임스탬프 포함)
- credentials.json을 /etc 아래에 안전하게 저장
