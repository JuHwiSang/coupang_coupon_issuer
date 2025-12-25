"""
Unit tests for config.py - ConfigManager and path handling
"""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch

from coupang_coupon_issuer.config import (
    ConfigManager,
    SERVICE_NAME,
    get_base_dir,
    get_config_file,
    get_excel_file,
    get_log_file,
    COUPON_CONTRACT_ID,
)


@pytest.mark.unit
class TestPathFunctions:
    """Test path resolution functions"""

    def test_get_base_dir_with_path(self, tmp_path):
        """get_base_dir() with explicit path should return that path"""
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        result = get_base_dir(test_dir)
        assert result == test_dir.resolve()

    def test_get_base_dir_without_path(self, monkeypatch):
        """get_base_dir() without path should return current directory"""
        test_cwd = Path("/fake/cwd")
        monkeypatch.setattr(Path, 'cwd', lambda: test_cwd)
        result = get_base_dir()
        assert result == test_cwd.resolve()

    def test_get_config_file(self, tmp_path):
        """get_config_file() should return base_dir / config.json"""
        result = get_config_file(tmp_path)
        assert result == tmp_path / "config.json"

    def test_get_excel_file(self, tmp_path):
        """get_excel_file() should return base_dir / coupons.xlsx"""
        result = get_excel_file(tmp_path)
        assert result == tmp_path / "coupons.xlsx"

    def test_get_log_file(self, tmp_path):
        """get_log_file() should return base_dir / issuer.log"""
        result = get_log_file(tmp_path)
        assert result == tmp_path / "issuer.log"


@pytest.mark.unit
class TestConstants:
    """Test constant values"""

    def test_service_name(self):
        assert SERVICE_NAME == "coupang_coupon_issuer"

    def test_coupon_contract_id(self):
        assert COUPON_CONTRACT_ID == -1


@pytest.mark.unit
class TestConfigManagerSave:
    """Test ConfigManager.save_config()"""

    def test_save_config_creates_file(self, mock_config_paths, capsys):
        """save_config should create config.json with all fields"""
        installation_id = ConfigManager.save_config(
            mock_config_paths,
            access_key="test-access",
            secret_key="test-secret",
            user_id="test-user",
            vendor_id="test-vendor"
        )

        # Verify file exists
        config_file = mock_config_paths / "config.json"
        assert config_file.exists()

        # Verify content
        with open(config_file, 'r') as f:
            data = json.load(f)

        assert data["access_key"] == "test-access"
        assert data["secret_key"] == "test-secret"
        assert data["user_id"] == "test-user"
        assert data["vendor_id"] == "test-vendor"
        assert data["installation_id"] == installation_id
        assert len(installation_id) == 36  # UUID format

        # Verify log output
        captured = capsys.readouterr()
        assert "설정 저장 중" in captured.out
        assert "설정이 저장되었습니다" in captured.out

    def test_save_config_generates_uuid_when_not_provided(self, mock_config_paths):
        """save_config should generate UUID if not provided"""
        installation_id = ConfigManager.save_config(
            mock_config_paths,
            access_key="test-access",
            secret_key="test-secret",
            user_id="test-user",
            vendor_id="test-vendor"
        )

        assert len(installation_id) == 36
        assert installation_id.count('-') == 4  # UUID4 format

    def test_save_config_uses_provided_uuid(self, mock_config_paths):
        """save_config should use provided UUID"""
        custom_uuid = "12345678-1234-1234-1234-123456789012"

        installation_id = ConfigManager.save_config(
            mock_config_paths,
            access_key="test-access",
            secret_key="test-secret",
            user_id="test-user",
            vendor_id="test-vendor",
            installation_id=custom_uuid
        )

        assert installation_id == custom_uuid

        # Verify in file
        config_file = mock_config_paths / "config.json"
        with open(config_file, 'r') as f:
            data = json.load(f)

        assert data["installation_id"] == custom_uuid

    def test_save_config_sets_file_permissions(self, mock_config_paths):
        """save_config should set file permissions to 600"""
        ConfigManager.save_config(
            mock_config_paths,
            access_key="test-access",
            secret_key="test-secret",
            user_id="test-user",
            vendor_id="test-vendor"
        )

        config_file = mock_config_paths / "config.json"

        # Verify permissions (Unix only)
        if os.name != 'nt':
            file_stat = config_file.stat()
            file_mode = oct(file_stat.st_mode)[-3:]
            assert file_mode == '600'

    def test_save_config_creates_parent_directory(self, tmp_path):
        """save_config should create parent directory if not exists"""
        base_dir = tmp_path / "deep" / "nested"

        ConfigManager.save_config(
            base_dir,
            access_key="test-access",
            secret_key="test-secret",
            user_id="test-user",
            vendor_id="test-vendor"
        )

        config_file = get_config_file(base_dir)
        assert config_file.exists()
        assert config_file.parent.exists()


@pytest.mark.unit
class TestConfigManagerLoad:
    """Test ConfigManager.load_config()"""

    def test_load_config_success(self, mock_config_paths):
        """load_config should return full config dict"""
        # Create config file
        config_file = mock_config_paths / "config.json"
        config = {
            "access_key": "loaded-access",
            "secret_key": "loaded-secret",
            "user_id": "loaded-user",
            "vendor_id": "loaded-vendor",
            "installation_id": "test-uuid-1234"
        }
        config_file.write_text(json.dumps(config))

        result = ConfigManager.load_config(mock_config_paths)

        assert result == config
        assert result["installation_id"] == "test-uuid-1234"

    def test_load_config_file_not_found(self, mock_config_paths):
        """load_config should raise FileNotFoundError if file doesn't exist"""
        with pytest.raises(FileNotFoundError) as exc_info:
            ConfigManager.load_config(mock_config_paths)

        assert "설정 파일이 없습니다" in str(exc_info.value)
        assert "install" in str(exc_info.value)

    def test_load_credentials_returns_tuple(self, mock_config_paths):
        """load_credentials should return (access_key, secret_key, user_id, vendor_id)"""
        config_file = mock_config_paths / "config.json"
        config = {
            "access_key": "loaded-access",
            "secret_key": "loaded-secret",
            "user_id": "loaded-user",
            "vendor_id": "loaded-vendor",
            "installation_id": "test-uuid"
        }
        config_file.write_text(json.dumps(config))

        result = ConfigManager.load_credentials(mock_config_paths)

        assert result == ("loaded-access", "loaded-secret", "loaded-user", "loaded-vendor")
        assert isinstance(result, tuple)
        assert len(result) == 4

    def test_load_credentials_missing_api_keys(self, mock_config_paths):
        """load_credentials should raise ValueError if API keys missing"""
        config_file = mock_config_paths / "config.json"
        config = {
            "user_id": "user",
            "vendor_id": "vendor",
            "installation_id": "test-uuid"
        }
        config_file.write_text(json.dumps(config))

        with pytest.raises(ValueError) as exc_info:
            ConfigManager.load_credentials(mock_config_paths)

        assert "API 키가 없습니다" in str(exc_info.value)

    def test_load_credentials_missing_coupon_info(self, mock_config_paths):
        """load_credentials should raise ValueError if user_id/vendor_id missing"""
        config_file = mock_config_paths / "config.json"
        config = {
            "access_key": "test-access",
            "secret_key": "test-secret",
            "installation_id": "test-uuid"
        }
        config_file.write_text(json.dumps(config))

        with pytest.raises(ValueError) as exc_info:
            ConfigManager.load_credentials(mock_config_paths)

        assert "쿠폰 정보가 없습니다" in str(exc_info.value)
        assert "user_id, vendor_id" in str(exc_info.value)


@pytest.mark.unit
class TestConfigManagerUUID:
    """Test ConfigManager UUID operations"""

    def test_get_installation_id_success(self, mock_config_paths):
        """get_installation_id should return UUID from config"""
        config_file = mock_config_paths / "config.json"
        config = {
            "access_key": "test",
            "secret_key": "test",
            "user_id": "test",
            "vendor_id": "test",
            "installation_id": "my-test-uuid-1234"
        }
        config_file.write_text(json.dumps(config))

        result = ConfigManager.get_installation_id(mock_config_paths)

        assert result == "my-test-uuid-1234"

    def test_get_installation_id_returns_none_when_file_missing(self, mock_config_paths):
        """get_installation_id should return None if config doesn't exist"""
        result = ConfigManager.get_installation_id(mock_config_paths)

        assert result is None

    def test_get_installation_id_returns_none_when_uuid_missing(self, mock_config_paths):
        """get_installation_id should return None if UUID key missing"""
        config_file = mock_config_paths / "config.json"
        config = {
            "access_key": "test",
            "secret_key": "test",
            "user_id": "test",
            "vendor_id": "test"
            # No installation_id
        }
        config_file.write_text(json.dumps(config))

        result = ConfigManager.get_installation_id(mock_config_paths)

        assert result is None


@pytest.mark.unit
class TestConfigManagerEnv:
    """Test environment variable operations"""

    def test_load_credentials_to_env(self, mock_config_paths, capsys):
        """load_credentials_to_env should set environment variables"""
        config_file = mock_config_paths / "config.json"
        config = {
            "access_key": "env-access",
            "secret_key": "env-secret",
            "user_id": "env-user",
            "vendor_id": "env-vendor",
            "installation_id": "test-uuid"
        }
        config_file.write_text(json.dumps(config))

        ConfigManager.load_credentials_to_env(mock_config_paths)

        # Verify environment variables
        assert os.environ["COUPANG_ACCESS_KEY"] == "env-access"
        assert os.environ["COUPANG_SECRET_KEY"] == "env-secret"
        assert os.environ["COUPANG_USER_ID"] == "env-user"
        assert os.environ["COUPANG_VENDOR_ID"] == "env-vendor"

        # Verify log output
        captured = capsys.readouterr()
        assert "환경 변수로 로드했습니다" in captured.out

        # Cleanup
        del os.environ["COUPANG_ACCESS_KEY"]
        del os.environ["COUPANG_SECRET_KEY"]
        del os.environ["COUPANG_USER_ID"]
        del os.environ["COUPANG_VENDOR_ID"]

    def test_get_from_env_success(self, monkeypatch):
        """get_from_env should return credentials from environment"""
        monkeypatch.setenv("COUPANG_ACCESS_KEY", "get-access")
        monkeypatch.setenv("COUPANG_SECRET_KEY", "get-secret")
        monkeypatch.setenv("COUPANG_USER_ID", "get-user")
        monkeypatch.setenv("COUPANG_VENDOR_ID", "get-vendor")

        result = ConfigManager.get_from_env()

        assert result == ("get-access", "get-secret", "get-user", "get-vendor")
        assert isinstance(result, tuple)

    def test_get_from_env_missing_api_keys(self, monkeypatch):
        """get_from_env should raise ValueError if API keys not set"""
        monkeypatch.delenv("COUPANG_ACCESS_KEY", raising=False)
        monkeypatch.delenv("COUPANG_SECRET_KEY", raising=False)
        monkeypatch.delenv("COUPANG_USER_ID", raising=False)
        monkeypatch.delenv("COUPANG_VENDOR_ID", raising=False)

        with pytest.raises(ValueError) as exc_info:
            ConfigManager.get_from_env()

        assert "API 키가 설정되지 않았습니다" in str(exc_info.value)

    def test_get_from_env_missing_coupon_info(self, monkeypatch):
        """get_from_env should raise ValueError if coupon info not set"""
        monkeypatch.setenv("COUPANG_ACCESS_KEY", "test-access")
        monkeypatch.setenv("COUPANG_SECRET_KEY", "test-secret")
        monkeypatch.delenv("COUPANG_USER_ID", raising=False)
        monkeypatch.delenv("COUPANG_VENDOR_ID", raising=False)

        with pytest.raises(ValueError) as exc_info:
            ConfigManager.get_from_env()

        assert "쿠폰 정보가 설정되지 않았습니다" in str(exc_info.value)
        assert "COUPANG_USER_ID, COUPANG_VENDOR_ID" in str(exc_info.value)
