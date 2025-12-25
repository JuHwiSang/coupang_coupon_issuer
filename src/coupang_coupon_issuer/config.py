"""설정 및 API 키 관리 모듈"""

import os
import sys
import json
import uuid
from pathlib import Path
from typing import Optional


# 서비스 설정
SERVICE_NAME = "coupang_coupon_issuer"


# 경로 해결 함수
def get_base_dir(work_dir: Optional[Path] = None) -> Path:
    """
    작업 디렉토리 경로 반환

    Args:
        work_dir: 명시적으로 지정된 작업 디렉토리 (기본: 현재 디렉토리)

    Returns:
        절대 경로로 변환된 작업 디렉토리
    """
    if work_dir is None:
        return Path.cwd().resolve()
    return Path(work_dir).resolve()


def get_config_file(base_dir: Path) -> Path:
    """config.json 파일 경로 반환"""
    return base_dir / "config.json"


def get_excel_file(base_dir: Path) -> Path:
    """coupons.xlsx 파일 경로 반환"""
    return base_dir / "coupons.xlsx"


def get_log_file(base_dir: Path) -> Path:
    """issuer.log 파일 경로 반환"""
    return base_dir / "issuer.log"

# 레거시 경로 (제거 예정)
EXCEL_RESULT_DIR = "results"  # ADR 009에서 결과 출력 제거로 사용하지 않음

# 쿠폰 발급 기본값
# 최대할인금액은 Excel에서 입력받음 (ADR 021)
COUPON_MIN_PURCHASE_PRICE = 1  # 최소 구매금액 기본값 (다운로드쿠폰 전용, ADR 021)
COUPON_CONTRACT_ID = -1  # 계약서 ID 고정값
COUPON_DEFAULT_ISSUE_COUNT = 1  # 다운로드쿠폰 발급개수 기본값 (Column F가 비어있을 때)

# 폴링 설정 (REQUESTED 상태 처리)
POLLING_MAX_RETRIES = 5  # 최대 재시도 횟수
POLLING_RETRY_INTERVAL = 2  # 재시도 간격 (초)


class ConfigManager:
    """config.json 읽기/쓰기 + UUID 관리"""

    @staticmethod
    def save_config(
        base_dir: Path,
        access_key: str,
        secret_key: str,
        user_id: str,
        vendor_id: str,
        installation_id: Optional[str] = None
    ) -> str:
        """
        설정 저장 (credentials + UUID)

        Args:
            base_dir: 작업 디렉토리
            access_key: Coupang Access Key
            secret_key: Coupang Secret Key
            user_id: WING 사용자 ID (다운로드쿠폰용)
            vendor_id: 판매자 ID (즉시할인쿠폰용)
            installation_id: 설치 UUID (없으면 자동 생성)

        Returns:
            installation_id: 생성/사용된 UUID
        """
        if installation_id is None:
            installation_id = str(uuid.uuid4())

        config = {
            "access_key": access_key,
            "secret_key": secret_key,
            "user_id": user_id,
            "vendor_id": vendor_id,
            "installation_id": installation_id
        }

        config_file = get_config_file(base_dir)
        print(f"설정 저장 중: {config_file}")

        # 디렉토리 생성 (없으면)
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # 설정 저장
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        # 파일 권한 설정 (사용자만 읽기/쓰기 가능)
        os.chmod(config_file, 0o600)

        print(f"설정이 저장되었습니다: {config_file}")
        print(f"Installation ID: {installation_id}")
        print(f"파일 권한: 600 (사용자만 읽기/쓰기 가능)")

        return installation_id

    @staticmethod
    def load_config(base_dir: Path) -> dict:
        """
        설정 로드 (UUID 포함)

        Args:
            base_dir: 작업 디렉토리

        Returns:
            config: 전체 설정 dict

        Raises:
            FileNotFoundError: 설정 파일이 없는 경우
        """
        config_file = get_config_file(base_dir)
        if not config_file.exists():
            raise FileNotFoundError(
                f"설정 파일이 없습니다: {config_file}\n"
                f"먼저 'install' 명령으로 서비스를 설치하고 설정을 등록하세요."
            )

        with open(config_file, 'r') as f:
            return json.load(f)

    @staticmethod
    def load_credentials(base_dir: Path) -> tuple[str, str, str, str]:
        """
        저장된 API 키 및 쿠폰 정보를 불러옵니다.

        Args:
            base_dir: 작업 디렉토리

        Returns:
            (access_key, secret_key, user_id, vendor_id) 튜플

        Raises:
            FileNotFoundError: 설정 파일이 없는 경우
            ValueError: 설정 파일이 손상된 경우
        """
        config = ConfigManager.load_config(base_dir)
        config_file = get_config_file(base_dir)

        access_key = config.get("access_key")
        secret_key = config.get("secret_key")
        user_id = config.get("user_id")
        vendor_id = config.get("vendor_id")

        if not access_key or not secret_key:
            raise ValueError(f"API 키가 없습니다: {config_file}")

        if not user_id or not vendor_id:
            raise ValueError(f"쿠폰 정보가 없습니다 (user_id, vendor_id 필수): {config_file}")

        return access_key, secret_key, user_id, vendor_id

    @staticmethod
    def get_installation_id(base_dir: Path) -> Optional[str]:
        """
        UUID만 반환

        Args:
            base_dir: 작업 디렉토리

        Returns:
            installation_id: 설치 UUID (없으면 None)
        """
        try:
            config = ConfigManager.load_config(base_dir)
            return config.get("installation_id")
        except FileNotFoundError:
            return None

    @staticmethod
    def load_credentials_to_env(base_dir: Path) -> None:
        """
        저장된 설정을 환경 변수로 로드합니다.

        Args:
            base_dir: 작업 디렉토리

        환경 변수:
            COUPANG_ACCESS_KEY: Access Key
            COUPANG_SECRET_KEY: Secret Key
            COUPANG_USER_ID: WING 사용자 ID
            COUPANG_VENDOR_ID: 판매자 ID
        """
        access_key, secret_key, user_id, vendor_id = ConfigManager.load_credentials(base_dir)

        os.environ["COUPANG_ACCESS_KEY"] = access_key
        os.environ["COUPANG_SECRET_KEY"] = secret_key
        os.environ["COUPANG_USER_ID"] = user_id
        os.environ["COUPANG_VENDOR_ID"] = vendor_id

        print(f"설정을 환경 변수로 로드했습니다")

    @staticmethod
    def get_from_env() -> tuple[str, str, str, str]:
        """
        환경 변수에서 설정을 가져옵니다.

        Returns:
            (access_key, secret_key, user_id, vendor_id) 튜플

        Raises:
            ValueError: 환경 변수가 설정되지 않은 경우
        """
        access_key = os.environ.get("COUPANG_ACCESS_KEY")
        secret_key = os.environ.get("COUPANG_SECRET_KEY")
        user_id = os.environ.get("COUPANG_USER_ID")
        vendor_id = os.environ.get("COUPANG_VENDOR_ID")

        if not access_key or not secret_key:
            raise ValueError(
                "환경 변수에 API 키가 설정되지 않았습니다.\n"
                "COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY를 설정하세요."
            )

        if not user_id or not vendor_id:
            raise ValueError(
                "환경 변수에 쿠폰 정보가 설정되지 않았습니다.\n"
                "COUPANG_USER_ID, COUPANG_VENDOR_ID를 설정하세요."
            )

        return access_key, secret_key, user_id, vendor_id

    @staticmethod
    def remove(base_dir: Path) -> None:
        """설정 파일 제거"""
        config_file = get_config_file(base_dir)
        if config_file.exists():
            config_file.unlink()
            print(f"설정 파일이 제거되었습니다: {config_file}")
        else:
            print(f"설정 파일이 존재하지 않습니다: {config_file}")
