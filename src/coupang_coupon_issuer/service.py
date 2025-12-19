"""Cron 기반 서비스 관리 모듈"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .config import SERVICE_NAME, LOG_DIR, LOG_FILE


class CrontabService:
    """Cron 기반 서비스 설치/제거 관리 클래스"""

    # Cron job 식별 마커
    CRON_MARKER = "# coupang_coupon_issuer_job"

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
    def _detect_cron_system() -> Optional[str]:
        """
        cron이 설치되어 있는지 확인

        Returns:
            'cron'이면 설치됨, None이면 미설치
        """
        result = subprocess.run(
            ["which", "crontab"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return "cron"

        return None

    @staticmethod
    def _get_package_manager() -> Optional[str]:
        """
        패키지 매니저 감지

        Returns:
            'apt' (Ubuntu/Debian), 'dnf' (RHEL 8+), 'yum' (RHEL 7), None (미지원)
        """
        if shutil.which("apt-get"):
            return "apt"
        elif shutil.which("dnf"):
            return "dnf"
        elif shutil.which("yum"):
            return "yum"

        return None

    @staticmethod
    def _install_cron() -> None:
        """
        cron 데몬 설치

        지원 플랫폼:
        - Ubuntu/Debian (apt)
        - RHEL/CentOS 8+ (dnf)
        - RHEL/CentOS 7 (yum)
        """
        print("\nCron이 설치되어 있지 않습니다. 설치 중...", flush=True)

        pkg_manager = CrontabService._get_package_manager()

        if pkg_manager == "apt":
            # Ubuntu/Debian
            commands = [
                "apt-get update",
                "DEBIAN_FRONTEND=noninteractive apt-get install -y cron"
            ]
        elif pkg_manager == "dnf":
            # RHEL/CentOS 8+
            commands = ["dnf install -y cronie"]
        elif pkg_manager == "yum":
            # RHEL/CentOS 7
            commands = ["yum install -y cronie"]
        else:
            raise RuntimeError(
                "지원하지 않는 배포판입니다. cron을 수동으로 설치하세요:\n"
                "  Ubuntu/Debian: sudo apt-get install cron\n"
                "  RHEL/CentOS: sudo yum install cronie"
            )

        for cmd in commands:
            print(f"실행 중: {cmd}", flush=True)
            ret = os.system(cmd)
            if ret != 0:
                raise RuntimeError(f"Cron 설치 실패 (종료 코드: {ret})")

        print("Cron 설치 완료", flush=True)

    @staticmethod
    def _enable_cron_service() -> None:
        """
        cron 데몬 활성화 및 시작

        systemctl이 있으면 사용, 없으면 service 명령어 사용
        """
        print("\nCron 서비스 활성화 중...", flush=True)

        # systemctl 우선 시도 (대부분의 최신 시스템)
        if shutil.which("systemctl"):
            # cron 또는 crond 서비스명 시도
            for service_name in ["cron", "crond"]:
                # 서비스 존재 여부 확인
                result = subprocess.run(
                    ["systemctl", "list-unit-files", f"{service_name}.service"],
                    capture_output=True,
                    text=True
                )

                if service_name in result.stdout:
                    # 이 서비스명이 존재함
                    commands = [
                        (f"systemctl enable {service_name}", "부팅 시 자동 시작 활성화"),
                        (f"systemctl start {service_name}", "서비스 시작"),
                    ]

                    for cmd, desc in commands:
                        print(f"{desc}...", flush=True)
                        ret = os.system(cmd)
                        if ret != 0:
                            print(f"WARNING: '{cmd}' 실행 중 오류 발생 (코드: {ret})", flush=True)

                    return

        # service 명령어 fallback
        elif shutil.which("service"):
            cmd = "service cron start"
            desc = "Cron 서비스 시작"
            print(f"{desc}...", flush=True)
            ret = os.system(cmd)
            if ret != 0:
                print(f"WARNING: '{cmd}' 실행 중 오류 발생 (코드: {ret})", flush=True)
            return

        print("WARNING: 서비스 매니저를 찾을 수 없습니다. Cron이 자동으로 시작되지 않을 수 있습니다.", flush=True)

    @staticmethod
    def _get_current_crontab() -> str:
        """
        현재 root crontab 읽기

        Returns:
            현재 crontab 내용 (없으면 빈 문자열)
        """
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True
        )

        # 종료 코드 1은 "crontab 없음"을 의미 (에러 아님)
        if result.returncode == 0:
            return result.stdout
        else:
            return ""

    @staticmethod
    def _add_cron_job(job_line: str) -> None:
        """
        root crontab에 cron job 추가

        Args:
            job_line: 마커 주석이 포함된 cron job 라인
        """
        current = CrontabService._get_current_crontab()

        # 기존 job이 있는지 확인
        if CrontabService.CRON_MARKER in current:
            print("기존 cron job을 발견했습니다. 업데이트 중...", flush=True)
            # 기존 job 제거 (마커로만 판단)
            lines = current.split('\n')
            filtered = [line for line in lines if CrontabService.CRON_MARKER not in line]
            current = '\n'.join(filtered)

        # 새 job 추가
        new_crontab = current.rstrip() + '\n' + job_line + '\n'

        # crontab 업데이트 (stdin으로 입력)
        result = subprocess.run(
            ["crontab", "-"],
            input=new_crontab,
            text=True,
            capture_output=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Crontab 업데이트 실패: {result.stderr}")

        print(f"Cron job이 성공적으로 추가되었습니다", flush=True)

    @staticmethod
    def _remove_cron_job() -> None:
        """root crontab에서 cron job 제거"""
        current = CrontabService._get_current_crontab()

        if CrontabService.CRON_MARKER not in current:
            print("제거할 cron job이 없습니다", flush=True)
            return

        # 우리의 job만 필터링
        lines = current.split('\n')
        filtered = [line for line in lines
                   if CrontabService.CRON_MARKER not in line]

        new_crontab = '\n'.join(filtered).strip() + '\n'

        # crontab 업데이트
        result = subprocess.run(
            ["crontab", "-"],
            input=new_crontab,
            text=True,
            capture_output=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Crontab 업데이트 실패: {result.stderr}")

        print("Cron job이 성공적으로 제거되었습니다", flush=True)

    @staticmethod
    def install(access_key: str, secret_key: str, user_id: str, vendor_id: str) -> None:
        """
        Cron 기반 서비스 설치

        절차:
        1. 파일 복사 (/opt)
        2. 심볼릭 링크 생성
        3. Python 의존성 설치
        4. Credentials 저장
        5. Cron 감지/설치/활성화
        6. 로그 디렉토리 생성
        7. Cron job 추가

        Args:
            access_key: Coupang Access Key
            secret_key: Coupang Secret Key
            user_id: WING 사용자 ID
            vendor_id: 판매자 ID
        """
        CrontabService._check_root()

        print(f"\n서비스 설치 중: {SERVICE_NAME}")

        # 1. 파일 복사
        print("\n파일 복사 중...", flush=True)
        # __file__ = /app/src/coupang_coupon_issuer/service.py
        # src_package_dir = /app/src/coupang_coupon_issuer
        # src_dir = /app/src
        # project_root = /app
        src_package_dir = Path(__file__).parent
        src_dir = src_package_dir.parent
        project_root = src_dir.parent
        install_dir = Path("/opt/coupang_coupon_issuer")

        install_dir.mkdir(parents=True, exist_ok=True)

        # main.py, src/, pyproject.toml 복사
        shutil.copy2(project_root / "main.py", install_dir / "main.py")
        print(f"복사: main.py")

        if (install_dir / "src").exists():
            shutil.rmtree(install_dir / "src")
        shutil.copytree(src_dir, install_dir / "src")
        print(f"복사: src/")

        if (project_root / "pyproject.toml").exists():
            shutil.copy2(project_root / "pyproject.toml", install_dir / "pyproject.toml")
            print(f"복사: pyproject.toml")

        # 실행 권한 설정
        (install_dir / "main.py").chmod(0o755)
        print(f"실행 권한 설정: main.py (755)")

        # 2. 심볼릭 링크 생성
        print("\n심볼릭 링크 생성 중...", flush=True)
        symlink_path = Path("/usr/local/bin/coupang_coupon_issuer")
        script_path = install_dir / "main.py"

        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()
            print(f"기존 심볼릭 링크 제거: {symlink_path}")

        symlink_path.symlink_to(script_path)
        print(f"심볼릭 링크 생성: {symlink_path} -> {script_path}")

        # 3. Python 의존성 설치
        print("\nPython 의존성 설치 중...", flush=True)
        python_path = "/usr/bin/python3"
        ret = os.system(f"{python_path} -m pip install requests openpyxl")
        if ret != 0:
            print("WARNING: 의존성 설치 실패. 수동으로 설치하세요:")
            print(f"  {python_path} -m pip install requests openpyxl")
        else:
            print("의존성 설치 완료")

        # 4. API 키 및 쿠폰 정보 저장
        print("\nAPI 키 및 쿠폰 정보 저장 중...", flush=True)
        from .config import CredentialManager
        CredentialManager.save_credentials(access_key, secret_key, user_id, vendor_id)

        # 5. Cron 감지/설치/활성화
        cron_system = CrontabService._detect_cron_system()

        if cron_system is None:
            CrontabService._install_cron()
        else:
            print(f"\nCron이 감지되었습니다: {cron_system}", flush=True)

        CrontabService._enable_cron_service()

        # 6. 로그 디렉토리 생성
        print(f"\n로그 디렉토리 생성 중: {LOG_DIR}", flush=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.chmod(0o755)

        # 로그 파일 생성
        LOG_FILE.touch(exist_ok=True)
        LOG_FILE.chmod(0o644)
        print(f"로그 파일 생성: {LOG_FILE}")

        # 7. Cron job 추가
        print("\nCron job 추가 중...", flush=True)
        cron_job = f"0 0 * * * {python_path} {script_path} issue >> {LOG_FILE} 2>&1  {CrontabService.CRON_MARKER}"
        CrontabService._add_cron_job(cron_job)

        print("\n설치 완료!")
        print(f"전역 명령어: coupang_coupon_issuer")
        print(f"Cron 스케줄: 매일 00:00")
        print(f"로그 확인: tail -f {LOG_FILE}")
        print(f"Cron 확인: crontab -l")
        print(f"수동 실행: coupang_coupon_issuer issue")

    @staticmethod
    def uninstall() -> None:
        """Cron 기반 서비스 제거"""
        CrontabService._check_root()

        print(f"서비스 제거 중: {SERVICE_NAME}")

        # 1. Cron job 제거
        print("\nCron job 제거 중...", flush=True)
        CrontabService._remove_cron_job()

        # 2. 심볼릭 링크 삭제
        symlink_path = Path("/usr/local/bin/coupang_coupon_issuer")
        if symlink_path.exists() or symlink_path.is_symlink():
            try:
                symlink_path.unlink()
                print(f"심볼릭 링크 삭제: {symlink_path}")
            except Exception as e:
                print(f"ERROR: 심볼릭 링크 삭제 실패: {e}")

        # 3. 설치 디렉토리 삭제 확인
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

        # 4. API 키 파일 삭제 여부 확인
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

        # 5. 엑셀 파일 삭제 확인
        coupons_file = Path("/etc/coupang_coupon_issuer/coupons.xlsx")
        if coupons_file.exists():
            response = input(f"\n엑셀 파일도 삭제하시겠습니까? ({coupons_file}) [y/N]: ")
            if response.lower() == 'y':
                try:
                    coupons_file.unlink()
                    print(f"엑셀 파일 삭제: {coupons_file}")
                except Exception as e:
                    print(f"ERROR: 엑셀 파일 삭제 실패: {e}")

        # 6. 로그 디렉토리 삭제 확인
        if LOG_DIR.exists():
            response = input(f"\n로그 디렉토리도 삭제하시겠습니까? ({LOG_DIR}) [y/N]: ")
            if response.lower() == 'y':
                try:
                    shutil.rmtree(LOG_DIR)
                    print(f"로그 디렉토리 삭제: {LOG_DIR}")
                except Exception as e:
                    print(f"ERROR: 로그 디렉토리 삭제 실패: {e}")
            else:
                print("로그 디렉토리는 유지됩니다.")

        print("\n제거 완료!")
