"""Cron 기반 서비스 관리 모듈"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from .config import SERVICE_NAME, ConfigManager, get_log_file


class CrontabService:
    """Cron 기반 서비스 설치/제거 관리 클래스"""

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
        현재 사용자 crontab 읽기

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
        사용자 crontab에 cron job 추가 (UUID 기반 업데이트)

        Args:
            job_line: UUID 마커 주석이 포함된 cron job 라인
        """
        current = CrontabService._get_current_crontab()

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
    def _remove_crontab_by_uuid(uuid_str: str) -> None:
        """
        UUID 주석 포함 라인 제거

        Args:
            uuid_str: 제거할 설치의 UUID
        """
        current = CrontabService._get_current_crontab()
        marker = f"# coupang_coupon_issuer_job:{uuid_str}"

        if marker not in current:
            print(f"제거할 cron job이 없습니다 (UUID: {uuid_str})", flush=True)
            return

        # UUID 마커가 포함된 라인만 필터링
        lines = current.split('\n')
        filtered = [line for line in lines if marker not in line]

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

        print(f"Cron job이 성공적으로 제거되었습니다 (UUID: {uuid_str})", flush=True)

    @staticmethod
    def install(
        base_dir: Path,
        access_key: str,
        secret_key: str,
        user_id: str,
        vendor_id: str,
        jitter_max: Optional[int] = None
    ) -> None:
        """
        Cron 기반 서비스 설치

        절차:
        1. config.json 로드/생성 (UUID 관리)
        2. Cron 감지/설치/활성화
        3. Cron job 추가 (절대경로 + UUID 주석)

        Args:
            base_dir: 작업 디렉토리
            access_key: Coupang Access Key
            secret_key: Coupang Secret Key
            user_id: WING 사용자 ID
            vendor_id: 판매자 ID
            jitter_max: 최대 Jitter 시간 (분 단위, None이면 jitter 미사용)
        """
        print(f"\n서비스 설치 중: {SERVICE_NAME}")

        # 1. config.json 로드/생성 (UUID 관리)
        existing_uuid = ConfigManager.get_installation_id(base_dir)
        if existing_uuid:
            # 기존 설치 존재 → 먼저 제거
            print(f"\n기존 설치 발견 (UUID: {existing_uuid}), 기존 cron job 제거 중...", flush=True)
            CrontabService._remove_crontab_by_uuid(existing_uuid)

        # 새 UUID 생성 및 저장
        print("\nAPI 키 및 쿠폰 정보 저장 중...", flush=True)
        new_uuid = ConfigManager.save_config(
            base_dir, access_key, secret_key, user_id, vendor_id
        )

        # 2. Cron 감지/설치/활성화
        cron_system = CrontabService._detect_cron_system()

        if cron_system is None:
            CrontabService._install_cron()
        else:
            print(f"\nCron이 감지되었습니다: {cron_system}", flush=True)

        CrontabService._enable_cron_service()

        # 3. Cron job 추가 (Python 스크립트 경로 + UUID 주석)
        print("\nCron job 추가 중...", flush=True)

        # main.py 스크립트 경로
        main_script = Path(__file__).parent.parent.parent / "main.py"
        if not main_script.exists():
            raise FileNotFoundError(f"main.py not found: {main_script}")

        python_exe = sys.executable or "python3"
        log_path = get_log_file(base_dir)

        # Cron 명령어 구성
        cron_cmd = f"{python_exe} {main_script.resolve()} issue {base_dir.resolve()}"

        # Jitter 옵션 포함
        if jitter_max is not None and jitter_max > 0:
            cron_cmd += f" --jitter-max {jitter_max}"
            print(f"Jitter 설정: 최대 {jitter_max}분 랜덤 지연", flush=True)

        cron_job = (
            f"0 0 * * * {cron_cmd} >> {log_path} 2>&1  "
            f"# coupang_coupon_issuer_job:{new_uuid}"
        )
        CrontabService._add_cron_job(cron_job)

        print("\n설치 완료!")
        print(f"Python 실행: {python_exe}")
        print(f"스크립트: {main_script}")
        print(f"작업 디렉토리: {base_dir}")
        print(f"설정 파일: {base_dir / 'config.json'}")
        print(f"Cron 스케줄: 매일 00:00{' (Jitter 활성화)' if jitter_max else ''}")
        if jitter_max:
            print(f"  → 실제 실행: 00:00 ~ {jitter_max//60:02d}:{jitter_max%60:02d} 사이")
        print(f"로그 확인: tail -f {log_path}")
        print(f"Cron 확인: crontab -l")

    @staticmethod
    def uninstall(base_dir: Path) -> None:
        """Cron 기반 서비스 제거

        Args:
            base_dir: 작업 디렉토리
        """
        print(f"서비스 제거 중: {SERVICE_NAME}")

        # config.json에서 UUID 읽기
        installation_id = ConfigManager.get_installation_id(base_dir)
        if not installation_id:
            print("\nWARNING: config.json에 installation_id가 없습니다", flush=True)
            print("수동으로 crontab을 확인하세요: crontab -l", flush=True)
            return

        # UUID로 crontab 검색/삭제
        print("\nCron job 제거 중...", flush=True)
        CrontabService._remove_crontab_by_uuid(installation_id)
        
        print("\n설정 파일 제거 중...", flush=True)
        ConfigManager.remove(base_dir)

        print("\n제거 완료!")
