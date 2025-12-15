# ADR 003: Coupang API 인증 (HMAC-SHA256)

**상태**: 승인됨
**날짜**: 2024-12-16
**결정자**: Coupang API 공식 규격

## 컨텍스트

Coupang WING API는 HMAC-SHA256 기반 서명 인증을 요구합니다. Access Key와 Secret Key를 사용하여 각 API 요청마다 서명을 생성해야 합니다.

## 결정사항

### HMAC 서명 생성 알고리즘

```python
# 1. GMT+0 타임존 설정
os.environ['TZ'] = 'GMT+0'
time.tzset()

# 2. GMT+0 기준 현재 시각 생성
datetime_str = time.strftime('%y%m%d') + 'T' + time.strftime('%H%M%S') + 'Z'
# 예: 241216T123045Z

# 3. 메시지 생성
message = datetime_str + method + path + query
# 예: 241216T123045ZPOST/v2/providers/fms/apis/api/v2/vendors/A00012345/coupon

# 4. HMAC-SHA256 서명
signature = hmac.new(
    secret_key.encode('utf-8'),
    message.encode('utf-8'),
    hashlib.sha256
).hexdigest()

# 5. Authorization 헤더 생성
authorization = f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={datetime_str}, signature={signature}"
```

### 헤더 구성

```python
headers = {
    "Content-Type": "application/json;charset=UTF-8",
    "Authorization": authorization
}
```

### 타임존 처리

- **중요**: Coupang API는 GMT+0 (UTC) 타임존을 요구
- Linux/Unix에서만 `time.tzset()` 지원
- Windows에서는 무시 (`hasattr(time, 'tzset')` 체크)

## 근거

1. **공식 규격 준수**: Coupang API 문서에 명시된 표준
2. **보안**: Secret Key가 네트워크로 전송되지 않음
3. **재현 가능성**: 동일한 시간에 동일한 요청은 동일한 서명 생성

## 영향

- coupang_api.py의 `_generate_hmac()` 메서드에 구현
- 모든 API 요청 전에 HMAC 서명 생성 필수
- GMT+0 타임존 설정이 필요 (모듈 import 시 자동 설정)
- Windows 환경에서는 타임존 설정 생략 (type: ignore 처리)
