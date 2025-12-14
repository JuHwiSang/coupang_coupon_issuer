"""systemd 서비스 관리 모듈"""

import os
import sys
from pathlib import Path

from .config import SERVICE_NAME


class SystemdService:
    """systemd 서비스 설치/제거 관리 클래스"""

    @staticmethod
    def _check_root() -> None:
        """root 권한 확인 (Linux 전용)"""
        # Windows에서는 os.geteuid()가 없으므로 체크
        if not hasattr(os, "geteuid"):
            print("WARNING: Windows 환경입니다. Linux 서버에서 실행하세요.", flush=True)
            return

        if os.geteuid() != 0:  # type: ignore  # Windows 환경에서는 이 함수가 없음
            raise PermissionError(
                "root 권한이 필요합니다.\n"
                f"다음 명령어로 실행하세요: sudo python3 {sys.argv[0]} {sys.argv[1]}"
            )

    @staticmethod
    def install(access_key: str, secret_key: str) -> None:
        """
        systemd 서비스로 설치

        Args:
            access_key: Coupang Access Key
            secret_key: Coupang Secret Key
        """
        SystemdService._check_root()

        # API 키 먼저 저장
        from .config import CredentialManager
        CredentialManager.save_credentials(access_key, secret_key)

        # 서비스 파일 생성
        script_path = Path(__file__).parent.parent.parent.parent / "main.py"
        script_path = script_path.resolve()
        python_path = sys.executable
        service_path = Path(f"/etc/systemd/system/{SERVICE_NAME}.service")
        working_dir = script_path.parent

        print(f"\n서비스 설치 중: {SERVICE_NAME}")
        print(f"스크립트 경로: {script_path}")
        print(f"Python 경로: {python_path}")
        print(f"작업 디렉토리: {working_dir}")

        service_content = f"""[Unit]
Description=Coupang Coupon Issuer - Daily Midnight Service
After=network.target

[Service]
Type=simple
ExecStart={python_path} -u {script_path} run
WorkingDirectory={working_dir}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 보안 강화 옵션 (필요시 주석 해제)
# User=nobody
# NoNewPrivileges=true
# PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""

        # 서비스 파일 생성
        try:
            service_path.write_text(service_content)
            print(f"서비스 파일 생성: {service_path}")
        except Exception as e:
            print(f"ERROR: 서비스 파일 생성 실패: {e}")
            sys.exit(1)

        # systemd 설정
        commands = [
            ("systemctl daemon-reload", "데몬 리로드"),
            (f"systemctl enable {SERVICE_NAME}", "부팅 시 자동 시작 활성화"),
            (f"systemctl restart {SERVICE_NAME}", "서비스 시작/재시작"),
        ]

        for cmd, desc in commands:
            print(f"{desc}...")
            ret = os.system(cmd)
            if ret != 0:
                print(f"WARNING: '{cmd}' 실행 중 오류 발생 (코드: {ret})")

        print("\n설치 완료!")
        print(f"상태 확인: systemctl status {SERVICE_NAME}")
        print(f"로그 확인: journalctl -u {SERVICE_NAME} -f")
        print(f"서비스 중지: systemctl stop {SERVICE_NAME}")

    @staticmethod
    def uninstall() -> None:
        """systemd 서비스 제거"""
        SystemdService._check_root()

        print(f"서비스 제거 중: {SERVICE_NAME}")

        commands = [
            (f"systemctl stop {SERVICE_NAME}", "서비스 중지"),
            (f"systemctl disable {SERVICE_NAME}", "자동 시작 비활성화"),
        ]

        for cmd, desc in commands:
            print(f"{desc}...")
            os.system(cmd)

        service_path = Path(f"/etc/systemd/system/{SERVICE_NAME}.service")
        if service_path.exists():
            try:
                service_path.unlink()
                print(f"서비스 파일 삭제: {service_path}")
            except Exception as e:
                print(f"ERROR: 파일 삭제 실패: {e}")

        os.system("systemctl daemon-reload")

        # API 키 파일 삭제 여부 확인
        from .config import CONFIG_FILE
        if CONFIG_FILE.exists():
            response = input(f"\nAPI 키 파일도 삭제하시겠습니까? ({CONFIG_FILE}) [y/N]: ")
            if response.lower() == 'y':
                try:
                    CONFIG_FILE.unlink()
                    print(f"API 키 파일 삭제: {CONFIG_FILE}")
                except Exception as e:
                    print(f"ERROR: API 키 파일 삭제 실패: {e}")
            else:
                print("API 키 파일은 유지됩니다.")

        print("제거 완료!")
