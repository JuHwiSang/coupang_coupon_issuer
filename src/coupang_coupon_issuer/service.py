"""systemd 서비스 관리 모듈"""

import os
import sys
import shutil
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
    def install(access_key: str, secret_key: str, user_id: str, vendor_id: str) -> None:
        """
        systemd 서비스로 설치

        Args:
            access_key: Coupang Access Key
            secret_key: Coupang Secret Key
            user_id: WING 사용자 ID
            vendor_id: 판매자 ID
        """
        SystemdService._check_root()

        print(f"\n서비스 설치 중: {SERVICE_NAME}")

        # 1. 파일 복사
        print("\n파일 복사 중...")
        project_root = Path(__file__).parent.parent.parent
        install_dir = Path("/opt/coupang_coupon_issuer")

        install_dir.mkdir(parents=True, exist_ok=True)

        # main.py, src/, pyproject.toml 복사
        shutil.copy2(project_root.parent / "main.py", install_dir / "main.py")
        print(f"복사: main.py")

        if (install_dir / "src").exists():
            shutil.rmtree(install_dir / "src")
        shutil.copytree(project_root, install_dir / "src")
        print(f"복사: src/")

        if (project_root.parent / "pyproject.toml").exists():
            shutil.copy2(project_root.parent / "pyproject.toml", install_dir / "pyproject.toml")
            print(f"복사: pyproject.toml")

        # 실행 권한 설정
        (install_dir / "main.py").chmod(0o755)
        print(f"실행 권한 설정: main.py (755)")

        # 2. 심볼릭 링크 생성
        print("\n심볼릭 링크 생성 중...")
        symlink_path = Path("/usr/local/bin/coupang_coupon_issuer")
        script_path = install_dir / "main.py"

        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()
            print(f"기존 심볼릭 링크 제거: {symlink_path}")

        symlink_path.symlink_to(script_path)
        print(f"심볼릭 링크 생성: {symlink_path} -> {script_path}")

        # 3. Python 의존성 설치
        print("\nPython 의존성 설치 중...")
        python_path = "/usr/bin/python3"
        ret = os.system(f"{python_path} -m pip install requests openpyxl")
        if ret != 0:
            print("WARNING: 의존성 설치 실패. 수동으로 설치하세요:")
            print(f"  {python_path} -m pip install requests openpyxl")
        else:
            print("의존성 설치 완료")

        # 4. API 키 및 쿠폰 정보 저장
        print("\nAPI 키 및 쿠폰 정보 저장 중...")
        from .config import CredentialManager
        CredentialManager.save_credentials(access_key, secret_key, user_id, vendor_id)

        # 5. systemd 서비스 파일 생성
        print("\nsystemd 서비스 파일 생성 중...")
        service_path = Path(f"/etc/systemd/system/{SERVICE_NAME}.service")
        working_dir = install_dir

        print(f"스크립트 경로: {script_path}")
        print(f"Python 경로: {python_path}")
        print(f"작업 디렉토리: {working_dir}")

        service_content = f"""[Unit]
Description=Coupang Coupon Issuer Service
After=network.target

[Service]
Type=simple
ExecStart={python_path} {script_path} serve
WorkingDirectory={working_dir}
Restart=on-failure
RestartSec=10

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

        # 6. systemd 설정
        print("\nsystemd 설정 중...")
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
        print(f"전역 명령어: coupang_coupon_issuer")
        print(f"상태 확인: systemctl status {SERVICE_NAME}")
        print(f"로그 확인: journalctl -u {SERVICE_NAME} -f")
        print(f"서비스 중지: systemctl stop {SERVICE_NAME}")

    @staticmethod
    def uninstall() -> None:
        """systemd 서비스 제거"""
        SystemdService._check_root()

        print(f"서비스 제거 중: {SERVICE_NAME}")

        # 1. systemd 서비스 중지 및 비활성화
        commands = [
            (f"systemctl stop {SERVICE_NAME}", "서비스 중지"),
            (f"systemctl disable {SERVICE_NAME}", "자동 시작 비활성화"),
        ]

        for cmd, desc in commands:
            print(f"{desc}...")
            os.system(cmd)

        # 2. 서비스 파일 삭제
        service_path = Path(f"/etc/systemd/system/{SERVICE_NAME}.service")
        if service_path.exists():
            try:
                service_path.unlink()
                print(f"서비스 파일 삭제: {service_path}")
            except Exception as e:
                print(f"ERROR: 파일 삭제 실패: {e}")

        os.system("systemctl daemon-reload")

        # 3. 심볼릭 링크 삭제
        symlink_path = Path("/usr/local/bin/coupang_coupon_issuer")
        if symlink_path.exists() or symlink_path.is_symlink():
            try:
                symlink_path.unlink()
                print(f"심볼릭 링크 삭제: {symlink_path}")
            except Exception as e:
                print(f"ERROR: 심볼릭 링크 삭제 실패: {e}")

        # 4. 설치 디렉토리 삭제 확인
        install_dir = Path("/opt/coupang_coupon_issuer")
        if install_dir.exists():
            response = input(f"\n설치 디렉토리도 삭제하시겠습니까? ({install_dir}) [y/N]: ")
            if response.lower() == 'y':
                try:
                    shutil.rmtree(install_dir)
                    print(f"설치 디렉토리 삭제: {install_dir}")
                except Exception as e:
                    print(f"ERROR: 설치 디렉토리 삭제 실패: {e}")
            else:
                print("설치 디렉토리는 유지됩니다.")

        # 5. API 키 파일 삭제 여부 확인
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

        # 6. 엑셀 파일 삭제 확인
        coupons_file = Path("/etc/coupang_coupon_issuer/coupons.xlsx")
        if coupons_file.exists():
            response = input(f"\n엑셀 파일도 삭제하시겠습니까? ({coupons_file}) [y/N]: ")
            if response.lower() == 'y':
                try:
                    coupons_file.unlink()
                    print(f"엑셀 파일 삭제: {coupons_file}")
                except Exception as e:
                    print(f"ERROR: 엑셀 파일 삭제 실패: {e}")

        print("\n제거 완료!")
