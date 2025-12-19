"""
Integration test fixtures using testcontainers.

Provides fixtures for running tests in actual Ubuntu 22.04 + systemd container.
"""

import json
import pytest
import time
from pathlib import Path
from testcontainers.core.container import DockerContainer


@pytest.fixture(scope="session")
def systemd_container():
    """
    Create Ubuntu 22.04 container with systemd enabled.

    Features:
    - Privileged mode for systemd support
    - Volume mount for project code at /app
    - cgroup volume for systemd
    - Waits for systemd initialization
    - Pre-installs Python 3, pip, and project dependencies

    Returns:
        DockerContainer: Running container with systemd
    """
    project_root = Path(__file__).parent.parent.parent

    container = DockerContainer("ubuntu:22.04")
    container.with_command("/sbin/init")

    # Enable privileged mode for systemd
    container.with_kwargs(privileged=True)

    # Mount project code
    container.with_volume_mapping(
        str(project_root.resolve()),
        "/app",
        mode="rw"
    )

    # Mount cgroup for systemd
    container.with_volume_mapping(
        "/sys/fs/cgroup",
        "/sys/fs/cgroup",
        mode="ro"
    )

    # Start container
    container.start()

    # Wait for systemd to initialize
    print("Waiting for systemd to initialize...", flush=True)
    time.sleep(5)

    # Install system dependencies
    print("Installing system dependencies...", flush=True)
    exit_code, output = container.exec(
        "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-pip sudo"
    )

    if exit_code != 0:
        print(f"WARNING: apt-get failed with code {exit_code}", flush=True)
        print(f"Output: {output.decode('utf-8') if output else 'N/A'}", flush=True)

    # Install Python packages
    print("Installing Python packages...", flush=True)
    exit_code, output = container.exec(
        "python3 -m pip install requests openpyxl pytest --break-system-packages"
    )

    if exit_code != 0:
        print(f"WARNING: pip install failed with code {exit_code}", flush=True)
        print(f"Output: {output.decode('utf-8') if output else 'N/A'}", flush=True)

    # Verify systemd is running
    exit_code, output = container.exec("systemctl is-system-running")
    print(f"systemd status: {output.decode('utf-8').strip() if output else 'unknown'}", flush=True)

    yield container

    # Cleanup
    container.stop()


@pytest.fixture(scope="function")
def clean_container(systemd_container):
    """
    Ensure clean state before each test.

    Removes:
    - Installed service files
    - /opt/coupang_coupon_issuer directory
    - /etc/coupang_coupon_issuer directory
    - Symlinks in /usr/local/bin

    Args:
        systemd_container: Session-scoped container fixture

    Yields:
        DockerContainer: Cleaned container ready for testing
    """
    cleanup_script = """
    systemctl stop coupang_coupon_issuer 2>/dev/null || true
    systemctl disable coupang_coupon_issuer 2>/dev/null || true
    rm -f /etc/systemd/system/coupang_coupon_issuer.service
    rm -rf /opt/coupang_coupon_issuer
    rm -rf /etc/coupang_coupon_issuer
    rm -f /usr/local/bin/coupang_coupon_issuer
    systemctl daemon-reload 2>/dev/null || true
    """

    systemd_container.exec(f"bash -c '{cleanup_script}'")

    yield systemd_container


@pytest.fixture
def container_exec(clean_container):
    """
    Helper to execute commands in container with better error handling.

    Returns a callable that executes commands and captures output.

    Args:
        clean_container: Function-scoped cleaned container

    Returns:
        Callable[[str, bool], dict]: Function to execute commands
            - command: Shell command to execute
            - check: If True, raises RuntimeError on non-zero exit code

    Example:
        result = container_exec("ls /opt")
        print(result['stdout'])
    """
    def _exec(command, check=True):
        """Execute command in container"""
        exit_code, output = clean_container.exec(f"bash -c '{command}'")

        stdout = output.decode('utf-8') if output else ''

        if check and exit_code != 0:
            raise RuntimeError(
                f"Command failed with exit code {exit_code}\n"
                f"Command: {command}\n"
                f"Output: {stdout}"
            )

        return {
            'exit_code': exit_code,
            'stdout': stdout,
        }

    return _exec


@pytest.fixture
def installed_service(clean_container, container_exec):
    """
    Install service in container and return installation state.

    Executes: python3 main.py install --access-key ... --secret-key ... --user-id ... --vendor-id ...

    Args:
        clean_container: Cleaned container
        container_exec: Command execution helper

    Returns:
        dict: Installation information
            - credentials: dict with access_key, secret_key, user_id, vendor_id
            - install_dir: Path to /opt/coupang_coupon_issuer
            - config_dir: Path to /etc/coupang_coupon_issuer
            - symlink: Path to /usr/local/bin/coupang_coupon_issuer

    Example:
        info = installed_service
        assert Path(info['install_dir']) / 'main.py').exists()
    """
    credentials = {
        'access_key': 'test-access-key',
        'secret_key': 'test-secret-key',
        'user_id': 'test-user-id',
        'vendor_id': 'test-vendor-id'
    }

    install_cmd = (
        f"cd /app && python3 main.py install "
        f"--access-key {credentials['access_key']} "
        f"--secret-key {credentials['secret_key']} "
        f"--user-id {credentials['user_id']} "
        f"--vendor-id {credentials['vendor_id']}"
    )

    container_exec(install_cmd)

    return {
        'credentials': credentials,
        'install_dir': '/opt/coupang_coupon_issuer',
        'config_dir': '/etc/coupang_coupon_issuer',
        'symlink': '/usr/local/bin/coupang_coupon_issuer'
    }


@pytest.fixture
def file_permission_checker(container_exec):
    """
    Helper to check file permissions in container.

    Args:
        container_exec: Command execution helper

    Returns:
        Callable[[str], dict]: Function that returns file permissions
            Returns dict: {'mode': '0755', 'owner': 'root', 'group': 'root'}
            Returns None if file doesn't exist

    Example:
        perms = file_permission_checker('/opt/coupang_coupon_issuer')
        assert perms['mode'] == '755'
        assert perms['owner'] == 'root'
    """
    def _check(file_path):
        """Check file permissions using stat"""
        result = container_exec(f"stat -c '%a %U %G' {file_path}", check=False)

        if result['exit_code'] != 0:
            return None

        parts = result['stdout'].strip().split()

        if len(parts) != 3:
            return None

        mode, owner, group = parts

        return {
            'mode': mode,
            'owner': owner,
            'group': group
        }

    return _check


@pytest.fixture
def verify_systemd_unit(container_exec):
    """
    Helper to verify systemd unit file properties.

    Args:
        container_exec: Command execution helper

    Returns:
        Callable[[str], dict]: Function that returns systemd unit properties
            Returns dict with systemd properties
            Returns {'exists': False} if service doesn't exist

    Example:
        props = verify_systemd_unit('coupang_coupon_issuer')
        assert props['ActiveState'] == 'active'
    """
    def _verify(service_name):
        """Verify systemd unit properties"""
        # Check if service exists
        result = container_exec(
            f"systemctl show {service_name} --no-pager",
            check=False
        )

        if result['exit_code'] != 0:
            return {'exists': False}

        # Parse properties
        properties = {'exists': True}
        for line in result['stdout'].split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                properties[key] = value

        return properties

    return _verify


@pytest.fixture
def mock_user_input(mocker):
    """
    Mock builtins.input for uninstall prompts.

    Args:
        mocker: pytest-mock mocker fixture

    Returns:
        Callable[[list], Mock]: Function to set up input mock
            Takes list of responses (e.g., ['y', 'n', 'y'])

    Example:
        mock_user_input(['y', 'n', 'y'])
        # First call to input() returns 'y'
        # Second call returns 'n'
        # Third call returns 'y'
    """
    def _mock(responses):
        """Set up input mock with given responses"""
        return mocker.patch('builtins.input', side_effect=responses)

    return _mock


@pytest.fixture
def mock_excel_in_container(clean_container, container_exec):
    """
    Create a test Excel file inside the container at /etc/coupang_coupon_issuer/coupons.xlsx

    Args:
        clean_container: Cleaned container
        container_exec: Command execution helper

    Returns:
        Callable[[str], str]: Function to create Excel file
            - content_type: 'valid', 'invalid_columns', 'invalid_rates', 'invalid_prices'
            Returns path to created file

    Example:
        excel_path = mock_excel_in_container('valid')
        # Creates /etc/coupang_coupon_issuer/coupons.xlsx with valid test data
    """
    def _create_excel(content_type='valid'):
        """Copy fixture Excel file to container"""
        # Copy fixture from host to container
        fixture_path = f"/app/tests/fixtures/sample_{content_type}.xlsx"
        target_path = "/etc/coupang_coupon_issuer/coupons.xlsx"

        container_exec("mkdir -p /etc/coupang_coupon_issuer")
        container_exec(f"cp {fixture_path} {target_path}")
        container_exec(f"chmod 600 {target_path}")

        return target_path

    return _create_excel
