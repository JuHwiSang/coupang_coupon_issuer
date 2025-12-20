"""
Unit tests for config.py - CredentialManager and constants
"""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from coupang_coupon_issuer.config import (
    CredentialManager,
    SERVICE_NAME,
    CONFIG_FILE,
    EXCEL_INPUT_FILE,
    COUPON_MAX_DISCOUNT,
    COUPON_CONTRACT_ID,
    LOG_DIR,
    LOG_FILE,
    _get_xdg_config_home,
    _get_xdg_state_home,
)


@pytest.mark.unit
class TestXDGHelpers:
    """Test XDG Base Directory helper functions"""

    def test_xdg_config_home_default(self, monkeypatch):
        """XDG_CONFIG_HOME not set, should return ~/.config"""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)

        result = _get_xdg_config_home()

        assert result == Path.home() / ".config"

    def test_xdg_config_home_custom(self, monkeypatch):
        """XDG_CONFIG_HOME set to custom path"""
        monkeypatch.setenv("XDG_CONFIG_HOME", "/custom/config")

        result = _get_xdg_config_home()

        assert result == Path("/custom/config")

    def test_xdg_config_home_empty_string(self, monkeypatch):
        """XDG_CONFIG_HOME set to empty string, should fallback to default"""
        monkeypatch.setenv("XDG_CONFIG_HOME", "")

        result = _get_xdg_config_home()

        assert result == Path.home() / ".config"

    def test_xdg_state_home_default(self, monkeypatch):
        """XDG_STATE_HOME not set, should return ~/.local/state"""
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)

        result = _get_xdg_state_home()

        assert result == Path.home() / ".local" / "state"

    def test_xdg_state_home_custom(self, monkeypatch):
        """XDG_STATE_HOME set to custom path"""
        monkeypatch.setenv("XDG_STATE_HOME", "/custom/state")

        result = _get_xdg_state_home()

        assert result == Path("/custom/state")

    def test_xdg_state_home_empty_string(self, monkeypatch):
        """XDG_STATE_HOME set to empty string, should fallback to default"""
        monkeypatch.setenv("XDG_STATE_HOME", "")

        result = _get_xdg_state_home()

        assert result == Path.home() / ".local" / "state"

    def test_config_dir_respects_xdg_config_home(self, monkeypatch):
        """CONFIG_DIR should use custom XDG_CONFIG_HOME if set"""
        monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/test_config")

        # Reload module to pick up environment change
        import importlib
        import coupang_coupon_issuer.config as config
        importlib.reload(config)

        # Use Path comparison or posix path for cross-platform compatibility
        assert "test_config" in str(config.CONFIG_DIR)
        assert "coupang_coupon_issuer" in str(config.CONFIG_DIR)
        assert config.CONFIG_DIR == Path("/tmp/test_config/coupang_coupon_issuer")

        # Restore
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        importlib.reload(config)

    def test_log_dir_respects_xdg_state_home(self, monkeypatch):
        """LOG_DIR should use custom XDG_STATE_HOME if set"""
        monkeypatch.setenv("XDG_STATE_HOME", "/tmp/test_state")

        # Reload module to pick up environment change
        import importlib
        import coupang_coupon_issuer.config as config
        importlib.reload(config)

        # Use Path comparison or posix path for cross-platform compatibility
        assert "test_state" in str(config.LOG_DIR)
        assert "coupang_coupon_issuer" in str(config.LOG_DIR)
        assert config.LOG_DIR == Path("/tmp/test_state/coupang_coupon_issuer")

        # Restore
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        importlib.reload(config)


@pytest.mark.unit
class TestConstants:
    """Test constant values"""

    def test_service_name(self):
        assert SERVICE_NAME == "coupang_coupon_issuer"

    def test_log_dir(self):
        """Test log directory constant"""
        assert "coupang_coupon_issuer" in str(LOG_DIR)
        assert ".local" in str(LOG_DIR)
        assert "state" in str(LOG_DIR)

    def test_log_file(self):
        """Test log file constant"""
        assert str(LOG_FILE).endswith("issuer.log")
        assert "coupang_coupon_issuer" in str(LOG_FILE)

    def test_config_file_path(self):
        """Test config file path uses XDG_CONFIG_HOME"""
        assert "coupang_coupon_issuer" in str(CONFIG_FILE)
        assert ".config" in str(CONFIG_FILE)
        assert str(CONFIG_FILE).endswith("credentials.json")

    def test_excel_input_file_path(self):
        """Test Excel input file path uses XDG_CONFIG_HOME"""
        assert "coupang_coupon_issuer" in str(EXCEL_INPUT_FILE)
        assert ".config" in str(EXCEL_INPUT_FILE)
        assert str(EXCEL_INPUT_FILE).endswith("coupons.xlsx")

    def test_coupon_max_discount(self):
        assert COUPON_MAX_DISCOUNT == 100000

    def test_coupon_contract_id(self):
        assert COUPON_CONTRACT_ID == -1


@pytest.mark.unit
class TestCredentialManagerSave:
    """Test CredentialManager.save_credentials()"""

    def test_save_credentials_creates_directory(self, tmp_path, monkeypatch):
        """Verify directory creation with proper permissions"""
        # Mock CONFIG_DIR and CONFIG_FILE to use tmp_path
        config_dir = tmp_path / "coupang_coupon_issuer"
        config_file = config_dir / "credentials.json"

        with patch('coupang_coupon_issuer.config.CONFIG_DIR', config_dir):
            with patch('coupang_coupon_issuer.config.CONFIG_FILE', config_file):
                CredentialManager.save_credentials(
                    access_key="test-access",
                    secret_key="test-secret",
                    user_id="test-user",
                    vendor_id="test-vendor"
                )

                # Verify directory was created
                assert config_dir.exists()
                assert config_dir.is_dir()

    def test_save_credentials_writes_json(self, tmp_path, capsys):
        """Validate JSON structure with 4 required keys"""
        config_dir = tmp_path / "coupang_coupon_issuer"
        config_file = config_dir / "credentials.json"

        with patch('coupang_coupon_issuer.config.CONFIG_DIR', config_dir):
            with patch('coupang_coupon_issuer.config.CONFIG_FILE', config_file):
                CredentialManager.save_credentials(
                    access_key="test-access",
                    secret_key="test-secret",
                    user_id="test-user",
                    vendor_id="test-vendor"
                )

                # Read and verify JSON content
                with open(config_file, 'r') as f:
                    data = json.load(f)

                assert data["access_key"] == "test-access"
                assert data["secret_key"] == "test-secret"
                assert data["user_id"] == "test-user"
                assert data["vendor_id"] == "test-vendor"
                assert len(data) == 4  # Only 4 keys

                # Verify log output
                captured = capsys.readouterr()
                assert "API 키 및 쿠폰 정보 저장 중" in captured.out
                assert "설정이 저장되었습니다" in captured.out

    def test_save_credentials_sets_permissions(self, tmp_path):
        """Check file permissions are set to 0o600"""
        config_dir = tmp_path / "coupang_coupon_issuer"
        config_file = config_dir / "credentials.json"

        with patch('coupang_coupon_issuer.config.CONFIG_DIR', config_dir):
            with patch('coupang_coupon_issuer.config.CONFIG_FILE', config_file):
                CredentialManager.save_credentials(
                    access_key="test-access",
                    secret_key="test-secret",
                    user_id="test-user",
                    vendor_id="test-vendor"
                )

                # Verify file permissions (on Unix-like systems)
                if os.name != 'nt':  # Skip on Windows
                    file_stat = config_file.stat()
                    file_mode = oct(file_stat.st_mode)[-3:]
                    assert file_mode == '600'


@pytest.mark.unit
class TestCredentialManagerLoad:
    """Test CredentialManager.load_credentials()"""

    def test_load_credentials_success(self, tmp_path):
        """Mock credentials.json read and verify returned tuple format"""
        config_dir = tmp_path / "coupang_coupon_issuer"
        config_file = config_dir / "credentials.json"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create credentials file
        creds = {
            "access_key": "loaded-access",
            "secret_key": "loaded-secret",
            "user_id": "loaded-user",
            "vendor_id": "loaded-vendor"
        }
        with open(config_file, 'w') as f:
            json.dump(creds, f)

        with patch('coupang_coupon_issuer.config.CONFIG_FILE', config_file):
            result = CredentialManager.load_credentials()

            assert result == ("loaded-access", "loaded-secret", "loaded-user", "loaded-vendor")
            assert isinstance(result, tuple)
            assert len(result) == 4

    def test_load_credentials_file_not_found(self, tmp_path):
        """Assert FileNotFoundError raised with appropriate message"""
        config_file = tmp_path / "nonexistent.json"

        with patch('coupang_coupon_issuer.config.CONFIG_FILE', config_file):
            with pytest.raises(FileNotFoundError) as exc_info:
                CredentialManager.load_credentials()

            assert "설정 파일이 없습니다" in str(exc_info.value)
            assert "install" in str(exc_info.value)

    def test_load_credentials_missing_api_keys(self, tmp_path):
        """Verify ValueError when access_key or secret_key missing"""
        config_dir = tmp_path / "coupang_coupon_issuer"
        config_file = config_dir / "credentials.json"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Missing secret_key
        creds = {
            "access_key": "test",
            "user_id": "user",
            "vendor_id": "vendor"
        }
        with open(config_file, 'w') as f:
            json.dump(creds, f)

        with patch('coupang_coupon_issuer.config.CONFIG_FILE', config_file):
            with pytest.raises(ValueError) as exc_info:
                CredentialManager.load_credentials()

            assert "API 키가 없습니다" in str(exc_info.value)

    def test_load_credentials_missing_coupon_info(self, tmp_path):
        """Verify ValueError when user_id or vendor_id missing"""
        config_dir = tmp_path / "coupang_coupon_issuer"
        config_file = config_dir / "credentials.json"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Missing vendor_id
        creds = {
            "access_key": "test-access",
            "secret_key": "test-secret",
            "user_id": "user"
        }
        with open(config_file, 'w') as f:
            json.dump(creds, f)

        with patch('coupang_coupon_issuer.config.CONFIG_FILE', config_file):
            with pytest.raises(ValueError) as exc_info:
                CredentialManager.load_credentials()

            assert "쿠폰 정보가 없습니다" in str(exc_info.value)
            assert "user_id, vendor_id 필수" in str(exc_info.value)


@pytest.mark.unit
class TestCredentialManagerEnv:
    """Test environment variable operations"""

    def test_load_credentials_to_env(self, tmp_path, capsys):
        """Mock file read and verify environment variables set"""
        config_dir = tmp_path / "coupang_coupon_issuer"
        config_file = config_dir / "credentials.json"
        config_dir.mkdir(parents=True, exist_ok=True)

        creds = {
            "access_key": "env-access",
            "secret_key": "env-secret",
            "user_id": "env-user",
            "vendor_id": "env-vendor"
        }
        with open(config_file, 'w') as f:
            json.dump(creds, f)

        with patch('coupang_coupon_issuer.config.CONFIG_FILE', config_file):
            CredentialManager.load_credentials_to_env()

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
        """Set environment variables and verify tuple returned"""
        monkeypatch.setenv("COUPANG_ACCESS_KEY", "get-access")
        monkeypatch.setenv("COUPANG_SECRET_KEY", "get-secret")
        monkeypatch.setenv("COUPANG_USER_ID", "get-user")
        monkeypatch.setenv("COUPANG_VENDOR_ID", "get-vendor")

        result = CredentialManager.get_from_env()

        assert result == ("get-access", "get-secret", "get-user", "get-vendor")
        assert isinstance(result, tuple)

    def test_get_from_env_missing_api_keys(self, monkeypatch):
        """Unset API key environment variables and assert ValueError"""
        # Ensure env vars are not set
        monkeypatch.delenv("COUPANG_ACCESS_KEY", raising=False)
        monkeypatch.delenv("COUPANG_SECRET_KEY", raising=False)
        monkeypatch.delenv("COUPANG_USER_ID", raising=False)
        monkeypatch.delenv("COUPANG_VENDOR_ID", raising=False)

        with pytest.raises(ValueError) as exc_info:
            CredentialManager.get_from_env()

        assert "API 키가 설정되지 않았습니다" in str(exc_info.value)

    def test_get_from_env_missing_coupon_info(self, monkeypatch):
        """Set only API keys, missing user_id/vendor_id"""
        monkeypatch.setenv("COUPANG_ACCESS_KEY", "test-access")
        monkeypatch.setenv("COUPANG_SECRET_KEY", "test-secret")
        monkeypatch.delenv("COUPANG_USER_ID", raising=False)
        monkeypatch.delenv("COUPANG_VENDOR_ID", raising=False)

        with pytest.raises(ValueError) as exc_info:
            CredentialManager.get_from_env()

        assert "쿠폰 정보가 설정되지 않았습니다" in str(exc_info.value)
        assert "COUPANG_USER_ID, COUPANG_VENDOR_ID" in str(exc_info.value)
