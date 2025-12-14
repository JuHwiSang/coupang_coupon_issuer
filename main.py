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
from datetime import datetime

from src.coupang_coupon_issuer.config import CredentialManager
from src.coupang_coupon_issuer.issuer import CouponIssuer
from src.coupang_coupon_issuer.scheduler import MidnightScheduler
from src.coupang_coupon_issuer.service import SystemdService


def cmd_run() -> None:
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
    if not args.access_key or not args.secret_key:
        print("ERROR: --access-key 와 --secret-key 인자가 필요합니다.", flush=True)
        print(f"사용 예시: sudo python3 {sys.argv[0]} install --access-key YOUR_KEY --secret-key YOUR_SECRET", flush=True)
        sys.exit(1)

    SystemdService.install(args.access_key, args.secret_key)


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
  # 서비스 설치
  sudo python3 main.py install --access-key YOUR_ACCESS_KEY --secret-key YOUR_SECRET_KEY

  # 서비스 실행 (일반적으로 systemd가 자동 실행)
  python3 main.py run

  # 서비스 제거
  sudo python3 main.py uninstall

서비스 관리:
  systemctl status coupang_coupon_issuer   # 상태 확인
  journalctl -u coupang_coupon_issuer -f   # 로그 확인
  systemctl stop coupang_coupon_issuer     # 중지
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # run 명령어
    subparsers.add_parser("run", help="스케줄러 실행 (서비스 모드)")

    # install 명령어
    install_parser = subparsers.add_parser("install", help="systemd 서비스로 설치")
    install_parser.add_argument("--access-key", type=str, help="Coupang Access Key")
    install_parser.add_argument("--secret-key", type=str, help="Coupang Secret Key")

    # uninstall 명령어
    subparsers.add_parser("uninstall", help="systemd 서비스 제거")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 명령어 실행
    if args.command == "run":
        cmd_run()
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
