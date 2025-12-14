# Claude 개발 가이드

매일 0시에 자동으로 쿠폰을 발급하는 Linux systemd 서비스

## 환경

- **OS**: Linux (systemd 필수)
- **Python**: 3.10+
- **패키지**: requests, openpyxl
- **로깅**: journalctl (systemd)

## 프로젝트 구조

```
src/coupang_coupon_issuer/
├── config.py         # API 키 관리 (/etc/coupang_coupon_issuer/credentials.json)
├── coupang_api.py    # Coupang API 클라이언트 (HMAC-SHA256 인증)
├── issuer.py         # 쿠폰 발급 로직 (TODO: 실제 발급 로직)
├── scheduler.py      # 0시 감지 스케줄러 (30초 체크)
└── service.py        # systemd 설치/제거
```

## 구현 완료

### ✅ Coupang API 클라이언트 (coupang_api.py)

- **HMAC-SHA256 서명**: Coupang 공식 규격 준수
- **즉시할인쿠폰 생성**: `create_instant_coupon()`
- **다운로드쿠폰 생성**: `create_download_coupon()`
- **에러 처리**: HTTP 타임아웃, API 오류 응답 체크

### 사용 예시

```python
# issuer.py에서 API 클라이언트 사용
def issue(self):
    # 즉시할인쿠폰 생성
    result = self.api_client.create_instant_coupon(
        vendor_id="A00012345",
        contract_id=10,
        name="신규 쿠폰",
        max_discount_price=1000,
        discount=10,
        start_at="2024-12-15 00:00:00",
        end_at="2024-12-31 23:59:59",
        coupon_type="PRICE"
    )

    # 다운로드쿠폰 생성
    result = self.api_client.create_download_coupon(
        contract_id=15,
        title="다운로드 쿠폰",
        start_date="2024-12-15 00:00:00",
        end_date="2024-12-31 23:59:59",
        user_id="wing_user_id",
        policies=[{
            "title": "1만원 이상 1천원 할인",
            "typeOfDiscount": "PRICE",
            "description": "10,000원 이상 구매시",
            "minimumPrice": 10000,
            "discount": 1000,
            "maximumDiscountPrice": 1000,
            "maximumPerDaily": 1
        }]
    )
```

## Claude에게 작업 요청

### 제약사항 (항상 명시)

```
- Python 3.10 호환
- Linux 서버 전용 (systemd, journalctl)
- 패키지: requests, openpyxl만 사용
- 로그에 이모지 사용 금지 (텍스트만)
- 예외 처리 필수 (로깅 후 상위로 전파)
```

### 다음 구현 작업

#### 1. 엑셀 I/O
```
issuer.py의 엑셀 처리 구현:
- _fetch_target_users(): /var/coupang/users.xlsx 읽기
- _save_result(): /var/coupang/results/result_YYYYMMDD_HHMMSS.xlsx 저장
- openpyxl 사용, 헤더 포맷팅, 에러 처리
```

#### 2. issue() 메서드 완성
```
실제 쿠폰 발급 로직:
1. 엑셀에서 사용자 목록/쿠폰 설정 읽기
2. self.api_client로 쿠폰 생성
3. 결과를 엑셀로 저장 (성공/실패, 에러메시지 포함)
```

#### 3. 테스트
```
pytest + requests-mock 사용
- 스케줄러 시간 mock 테스트
- API HMAC 서명 검증
- 엑셀 I/O 테스트
```

#### 4. 성능 개선
```
병렬 처리 (concurrent.futures.ThreadPoolExecutor)
- 여러 쿠폰 동시 생성
- 진행률 로깅
```

## 디버깅

journalctl 로그 공유 시:
```bash
journalctl -u coupang_coupon_issuer --since "1 hour ago"
```

에러 스택 트레이스와 함께 파일명:라인번호 포함하여 요청

## 완료 체크리스트

- [x] API 클라이언트 (coupang_api.py)
- [x] HMAC-SHA256 인증 구현
- [ ] 엑셀 I/O
- [ ] issue() 메서드 실제 로직
- [ ] 테스트 (pytest)
- [ ] 성능 최적화
