#!/usr/bin/env python3
"""
Coupang Coupon Issuer - 매일 0시에 쿠폰을 발급하는 서비스

사용법:
    python3 main.py run
    sudo python3 main.py install --access-key YOUR_KEY --secret-key YOUR_SECRET
    sudo python3 main.py uninstall
"""

import sys
import argparse
import shutil
import re
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from src.coupang_coupon_issuer.config import CredentialManager
from src.coupang_coupon_issuer.issuer import CouponIssuer
from src.coupang_coupon_issuer.scheduler import MidnightScheduler
from src.coupang_coupon_issuer.service import SystemdService


def cmd_apply(args) -> None:
    """엑셀 파일 검증 및 /etc로 복사"""
    excel_file = args.excel_file

    if not Path(excel_file).exists():
        print(f"ERROR: 파일이 존재하지 않습니다: {excel_file}", flush=True)
        sys.exit(1)

    print(f"엑셀 파일 검증 중: {excel_file}", flush=True)

    # 무결성 검증
    try:
        wb = load_workbook(excel_file, read_only=True)
        sheet = wb.active

        if sheet is None:
            raise ValueError("엑셀 시트를 찾을 수 없습니다")

        # 헤더 확인
        headers = [cell.value for cell in sheet[1]]
        required = ['쿠폰이름', '쿠폰타입', '쿠폰유효기간', '할인방식', '할인금액/비율', '발급개수']

        for col in required:
            if col not in headers:
                raise ValueError(f"필수 컬럼 누락: {col}")

        # 각 행 검증
        col_indices = {header: idx for idx, header in enumerate(headers)}

        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            # 빈 행 건너뛰기
            if not any(row):
                continue

            # 1. 쿠폰이름 검증
            coupon_name = str(row[col_indices['쿠폰이름']]).strip()
            if not coupon_name:
                raise ValueError(f"행 {row_idx}: 쿠폰이름이 비어있습니다")

            # 2. 쿠폰타입 검증
            coupon_type_raw = str(row[col_indices['쿠폰타입']]).strip()
            coupon_type_normalized = re.sub(r'\s+', '', coupon_type_raw)

            if '즉시할인' not in coupon_type_normalized and '다운로드쿠폰' not in coupon_type_normalized:
                raise ValueError(f"행 {row_idx}: 잘못된 쿠폰 타입 '{coupon_type_raw}' (즉시할인 또는 다운로드쿠폰만 가능)")

            # 3. 쿠폰유효기간 검증
            validity_days_raw = str(row[col_indices['쿠폰유효기간']])
            validity_days_digits = re.sub(r'[^\d.]', '', validity_days_raw)
            try:
                validity_days = int(float(validity_days_digits))
                if validity_days <= 0:
                    raise ValueError(f"행 {row_idx}: 쿠폰유효기간은 1 이상이어야 합니다")
            except (ValueError, TypeError):
                raise ValueError(f"행 {row_idx}: 쿠폰유효기간은 숫자여야 합니다 (현재값: {validity_days_raw})")

            # 4. 할인방식 검증
            discount_type_raw = str(row[col_indices['할인방식']]).strip()
            discount_type_normalized = discount_type_raw.upper().replace('-', '_')

            if 'RATE' in discount_type_normalized:
                discount_type = 'RATE'
            elif 'FIXED_WITH_QUANTITY' in discount_type_normalized or 'FIXED WITH QUANTITY' in discount_type_normalized.replace('_', ' '):
                discount_type = 'FIXED_WITH_QUANTITY'
            elif 'PRICE' in discount_type_normalized:
                discount_type = 'PRICE'
            else:
                raise ValueError(f"행 {row_idx}: 잘못된 할인방식 '{discount_type_raw}' (RATE/FIXED_WITH_QUANTITY/PRICE만 가능)")

            # 5. 할인금액/비율 검증 (Column E - 필수)
            discount_raw = str(row[col_indices['할인금액/비율']])
            discount_digits = re.sub(r'[^\d.]', '', discount_raw)
            try:
                discount = int(float(discount_digits)) if discount_digits else 0
                if discount <= 0:
                    raise ValueError(f"행 {row_idx}: 할인금액/비율은 0보다 커야 합니다")
            except (ValueError, TypeError):
                raise ValueError(f"행 {row_idx}: 할인금액/비율은 숫자여야 합니다 (현재값: {discount_raw})")

            # 6. 발급개수 검증 (Column F - 선택적, 쿠폰 타입에 따라 다름)
            coupon_type_normalized = re.sub(r'\s+', '', coupon_type_raw)
            if '즉시할인' in coupon_type_normalized:
                coupon_type = '즉시할인'
            else:
                coupon_type = '다운로드쿠폰'

            issue_count_raw = str(row[col_indices['발급개수']]).strip()

            # 다운로드쿠폰인 경우, 발급개수 검증 (비어있으면 기본값 1 사용 예정)
            if coupon_type == '다운로드쿠폰':
                if issue_count_raw and issue_count_raw != 'None':
                    issue_count_digits = re.sub(r'[^\d.]', '', issue_count_raw)
                    try:
                        issue_count = int(float(issue_count_digits)) if issue_count_digits else 1
                        if issue_count < 1:
                            raise ValueError(f"행 {row_idx}: 발급개수는 1 이상이어야 합니다 (현재: {issue_count})")
                    except (ValueError, TypeError):
                        raise ValueError(f"행 {row_idx}: 발급개수는 숫자여야 합니다 (현재값: {issue_count_raw})")

            # 7. 할인방식별 추가 검증 (Column E 기준)
            if discount_type == 'RATE':
                if not (1 <= discount <= 99):
                    raise ValueError(f"행 {row_idx}: RATE 할인율은 1~99 사이여야 합니다 (현재: {discount})")
            elif discount_type == 'PRICE':
                if discount < 10:
                    raise ValueError(f"행 {row_idx}: PRICE 할인금액은 최소 10원 이상이어야 합니다 (현재: {discount})")
                if discount % 10 != 0:
                    raise ValueError(f"행 {row_idx}: PRICE 할인금액은 10원 단위여야 합니다 (현재: {discount})")
            elif discount_type == 'FIXED_WITH_QUANTITY':
                if discount < 1:
                    raise ValueError(f"행 {row_idx}: FIXED_WITH_QUANTITY 할인은 1 이상이어야 합니다 (현재: {discount})")

        wb.close()
        print("검증 완료", flush=True)

    except Exception as e:
        print(f"ERROR: 검증 실패: {e}", flush=True)
        sys.exit(1)

    # /etc로 복사
    dest = Path("/etc/coupang_coupon_issuer/coupons.xlsx")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(excel_file, dest)
    dest.chmod(0o600)

    print(f"복사 완료: {dest}", flush=True)


def cmd_issue() -> None:
    """단발성 쿠폰 발급 (즉시 실행)"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] 쿠폰 발급 시작...", flush=True)

    # credentials.json에서 API 키 로드
    try:
        CredentialManager.load_credentials_to_env()
    except Exception as e:
        print(f"ERROR: API 키 로드 실패: {e}", flush=True)
        sys.exit(1)

    # 쿠폰 발급 실행
    try:
        issuer = CouponIssuer()
        issuer.issue()
    except Exception as e:
        print(f"ERROR: 쿠폰 발급 실패: {e}", flush=True)
        sys.exit(1)


def cmd_serve() -> None:
    """스케줄러 실행 (서비스 모드)"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 서비스 시작 중...", flush=True)

    # API 키를 파일에서 로드하여 환경 변수로 설정
    try:
        CredentialManager.load_credentials_to_env()
    except Exception as e:
        print(f"ERROR: API 키 로드 실패: {e}", flush=True)
        sys.exit(1)

    # 쿠폰 발급 함수 정의
    def issue_task():
        issuer = CouponIssuer()
        issuer.issue()

    # 스케줄러 시작
    scheduler = MidnightScheduler(issue_task)
    scheduler.run()


def cmd_install(args) -> None:
    """systemd 서비스 설치"""
    # 4개 파라미터 모두 필수
    if not all([args.access_key, args.secret_key, args.user_id, args.vendor_id]):
        print("ERROR: 모든 인자가 필요합니다.", flush=True)
        print("필수 인자:", flush=True)
        print("  --access-key  : Coupang Access Key", flush=True)
        print("  --secret-key  : Coupang Secret Key", flush=True)
        print("  --user-id     : WING 사용자 ID", flush=True)
        print("  --vendor-id   : 판매자 ID", flush=True)
        sys.exit(1)

    SystemdService.install(args.access_key, args.secret_key, args.user_id, args.vendor_id)


def cmd_uninstall() -> None:
    """systemd 서비스 제거"""
    SystemdService.uninstall()


def main() -> None:
    """메인 진입점"""
    parser = argparse.ArgumentParser(
        description="Coupang Coupon Issuer - 매일 0시 쿠폰 발급 서비스",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 1. 엑셀 파일 검증 및 적용
  sudo coupang_coupon_issuer apply ./coupons.xlsx

  # 2. 단발성 쿠폰 발급 (테스트용)
  coupang_coupon_issuer issue

  # 3. 서비스 설치 (4개 파라미터 필수)
  sudo coupang_coupon_issuer install \\
    --access-key YOUR_KEY \\
    --secret-key YOUR_SECRET \\
    --user-id YOUR_USER_ID \\
    --vendor-id YOUR_VENDOR_ID

  # 4. 스케줄러 실행 (일반적으로 systemd가 자동 실행)
  coupang_coupon_issuer serve

  # 5. 서비스 제거
  sudo coupang_coupon_issuer uninstall

서비스 관리:
  systemctl status coupang_coupon_issuer   # 상태 확인
  journalctl -u coupang_coupon_issuer -f   # 로그 확인
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # apply 서브파서 (excel_file 위치 인자)
    apply_parser = subparsers.add_parser("apply", help="엑셀 파일 검증 및 복사")
    apply_parser.add_argument("excel_file", type=str, help="엑셀 파일 경로")

    # issue 서브파서
    subparsers.add_parser("issue", help="단발성 쿠폰 발급 (즉시 실행)")

    # serve 서브파서 (기존 run 대체)
    subparsers.add_parser("serve", help="스케줄러 실행 (systemd용)")

    # install 파서에 user_id, vendor_id 추가
    install_parser = subparsers.add_parser("install", help="systemd 서비스 설치")
    install_parser.add_argument("--access-key", required=True, help="Coupang Access Key")
    install_parser.add_argument("--secret-key", required=True, help="Coupang Secret Key")
    install_parser.add_argument("--user-id", required=True, help="WING 사용자 ID")
    install_parser.add_argument("--vendor-id", required=True, help="판매자 ID")

    # uninstall 파서 (변경 없음)
    subparsers.add_parser("uninstall", help="systemd 서비스 제거")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 명령어 실행
    if args.command == "apply":
        cmd_apply(args)
    elif args.command == "issue":
        cmd_issue()
    elif args.command == "serve":
        cmd_serve()
    elif args.command == "install":
        cmd_install(args)
    elif args.command == "uninstall":
        cmd_uninstall()
    else:
        print(f"ERROR: 알 수 없는 명령어: {args.command}")
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
