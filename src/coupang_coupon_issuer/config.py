"""설정 및 API 키 관리 모듈"""

import os
import json
from pathlib import Path
from typing import Optional


# 서비스 설정
SERVICE_NAME = "coupang_coupon_issuer"
CHECK_INTERVAL = 30  # 초 단위 - 0시 체크 주기

# API 키 저장 경로 (systemd 서비스가 접근 가능한 위치)
CONFIG_DIR = Path("/etc") / SERVICE_NAME
CONFIG_FILE = CONFIG_DIR / "credentials.json"


class CredentialManager:
    """API 키 관리 클래스"""

    @staticmethod
    def save_credentials(access_key: str, secret_key: str) -> None:
        """
        API 키를 파일에 안전하게 저장합니다.

        Args:
            access_key: Coupang Access Key
            secret_key: Coupang Secret Key
        """
        print(f"API 키 저장 중: {CONFIG_FILE}")

        # 디렉토리 생성 (없으면)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # 키 저장
        credentials = {
            "access_key": access_key,
            "secret_key": secret_key,
        }

        with open(CONFIG_FILE, "w") as f:
            json.dump(credentials, f, indent=2)

        # 파일 권한 설정 (root만 읽기 가능)
        os.chmod(CONFIG_FILE, 0o600)

        print(f"API 키가 저장되었습니다: {CONFIG_FILE}")
        print(f"파일 권한: 600 (root만 읽기 가능)")

    @staticmethod
    def load_credentials() -> tuple[str, str]:
        """
        저장된 API 키를 불러옵니다.

        Returns:
            (access_key, secret_key) 튜플

        Raises:
            FileNotFoundError: 키 파일이 없는 경우
            ValueError: 키 파일이 손상된 경우
        """
        if not CONFIG_FILE.exists():
            raise FileNotFoundError(
                f"API 키 파일이 없습니다: {CONFIG_FILE}\n"
                f"먼저 'install' 명령으로 서비스를 설치하고 API 키를 등록하세요."
            )

        with open(CONFIG_FILE, "r") as f:
            credentials = json.load(f)

        access_key = credentials.get("access_key")
        secret_key = credentials.get("secret_key")

        if not access_key or not secret_key:
            raise ValueError(f"API 키 파일이 손상되었습니다: {CONFIG_FILE}")

        return access_key, secret_key

    @staticmethod
    def load_credentials_to_env() -> None:
        """
        저장된 API 키를 환경 변수로 로드합니다.

        환경 변수:
            COUPANG_ACCESS_KEY: Access Key
            COUPANG_SECRET_KEY: Secret Key
        """
        access_key, secret_key = CredentialManager.load_credentials()

        os.environ["COUPANG_ACCESS_KEY"] = access_key
        os.environ["COUPANG_SECRET_KEY"] = secret_key

        print(f"API 키를 환경 변수로 로드했습니다 (COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY)")

    @staticmethod
    def get_from_env() -> tuple[str, str]:
        """
        환경 변수에서 API 키를 가져옵니다.

        Returns:
            (access_key, secret_key) 튜플

        Raises:
            ValueError: 환경 변수가 설정되지 않은 경우
        """
        access_key = os.environ.get("COUPANG_ACCESS_KEY")
        secret_key = os.environ.get("COUPANG_SECRET_KEY")

        if not access_key or not secret_key:
            raise ValueError(
                "환경 변수에 API 키가 설정되지 않았습니다.\n"
                "COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY를 설정하세요."
            )

        return access_key, secret_key
