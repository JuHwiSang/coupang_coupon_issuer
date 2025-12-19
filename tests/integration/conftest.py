"""
Integration test fixtures using testcontainers.

Provides fixtures for running tests across multiple Linux distributions with cron.
Tests automatically run on 4 different images (Ubuntu 24.04, 22.04, Debian 13, 12).

Key features:
- Multi-distro testing via pytest parametrize (80 total tests = 20 base × 4 images)
- Pre-built images for faster test execution (build once, reuse many times)
- PEP 668 compatibility: automatic --break-system-packages fallback
- No privileged mode required (simpler than systemd)
- Supported: Python 3.10+ distributions (Ubuntu 22.04+, Debian 12+*)

Note: Debian 12 ships with Python 3.11, so it meets the 3.10+ requirement.
"""

import json
import pytest
import docker
import io
from pathlib import Path
from testcontainers.core.container import DockerContainer


def get_or_build_image(base_image):
    """
    Get or build a Docker image with pre-installed dependencies.

    This function checks if a pre-built test image exists. If not, it builds one
    with all necessary system packages and Python dependencies installed.

    Benefits:
    - Build once, reuse many times (huge speedup for integration tests)
    - Source code excluded from image (mounted via volume instead)
    - PEP 668 compatibility built into image

    Args:
        base_image: Base image name (e.g., "ubuntu:22.04")

    Returns:
        str: Tag of the built/existing image
    """
    client = docker.from_env()
    tag = f"coupang-coupon-issuer-test:{base_image.replace(':', '-')}"

    try:
        # Check if image already exists
        client.images.get(tag)
        print(f"Using existing test image: {tag}", flush=True)
        return tag
    except docker.errors.ImageNotFound:  # type: ignore[attr-defined]
        # Build new image with all dependencies
        print(f"Building test image: {tag}...", flush=True)

        # Determine pip install command based on distro
        # PEP 668 (Externally Managed Environment) requires --break-system-packages
        # Ubuntu 24.04, Debian 13, and Debian 12 all require the flag
        if base_image in ["ubuntu:24.04", "debian:13", "debian:12"]:
            pip_cmd = "python3 -m pip install --break-system-packages requests openpyxl pytest"
        else:
            pip_cmd = "python3 -m pip install requests openpyxl pytest"

        dockerfile_content = f"""FROM {base_image}

# Install system dependencies (including cron)
RUN apt-get update && \\
    DEBIAN_FRONTEND=noninteractive apt-get install -y \\
    python3 \\
    python3-pip \\
    sudo \\
    cron && \\
    rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN {pip_cmd}

# Set working directory (project code will be mounted here)
WORKDIR /app

# Start cron service by default
CMD ["bash"]
"""

        # Build image from in-memory Dockerfile
        f = io.BytesIO(dockerfile_content.encode('utf-8'))
        client.images.build(fileobj=f, tag=tag, rm=True)
        print(f"Successfully built test image: {tag}", flush=True)

        return tag


@pytest.fixture(
    scope="session",
    params=[
        "ubuntu:24.04",
        "ubuntu:22.04",
        # "ubuntu:20.04",
        "debian:13",
        "debian:12",
        # "debian:11",
    ]
)
def cron_container(request):
    """
    Create Linux container with cron installed using pre-built image.
    Tests against multiple distributions to ensure compatibility.

    Tested images (Python 3.10+ only):
    - ubuntu:24.04 (Noble Numbat, Python 3.12)
    - ubuntu:22.04 (Jammy Jellyfish, Python 3.10)
    - debian:13 (Trixie, Python 3.12)
    - debian:12 (Bookworm, Python 3.11)

    Features:
    - Volume mount for project code at /app
    - Uses pre-built image with dependencies (much faster than installing each time)
    - PEP 668 compatibility built into image
    - No privileged mode required (simpler than systemd)

    Returns:
        DockerContainer: Running container with cron and Python 3.10+
    """
    base_image = request.param
    project_root = Path(__file__).parent.parent.parent

    # Get or build pre-configured image
    test_image = get_or_build_image(base_image)

    # Create container from pre-built image
    container = DockerContainer(test_image)
    container.with_command("/bin/bash")
    container.with_kwargs(stdin_open=True, tty=True)

    # Mount project code (source code not baked into image)
    container.with_volume_mapping(
        str(project_root.resolve()),
        "/app",
        mode="rw"
    )

    # Start container
    print(f"Starting container: {base_image}", flush=True)
    container.start()

    # Start cron service (already installed in image)
    print("Starting cron service...", flush=True)
    exit_code, output = container.exec(["bash", "-c", "service cron start"])

    if exit_code != 0:
        print(f"WARNING: cron start failed with code {exit_code}", flush=True)
        print(f"Output: {output.decode('utf-8') if output else 'N/A'}", flush=True)

    print("Container ready", flush=True)

    yield container

    # Cleanup
    print("Stopping container...", flush=True)
    container.stop()


@pytest.fixture(scope="function")
def clean_container(cron_container):
    """
    Clean up container state before each test.

    Removes:
    - Cron jobs (crontab -r)
    - Installed files (/opt, /etc, /usr/local/bin)
    - Log directory

    Args:
        cron_container: The running cron container

    Returns:
        DockerContainer: Cleaned container
    """
    # Remove cron jobs (ignore errors if no crontab exists)
    cron_container.exec(["bash", "-c", "crontab -r || true"])

    # Remove installed files
    cron_container.exec(["bash", "-c", "rm -rf /opt/coupang_coupon_issuer"])
    cron_container.exec(["bash", "-c", "rm -rf /etc/coupang_coupon_issuer"])
    cron_container.exec(["bash", "-c", "rm -f /usr/local/bin/coupang_coupon_issuer"])
    cron_container.exec(["bash", "-c", "rm -rf /root/.local/state/coupang_coupon_issuer"])

    yield cron_container


@pytest.fixture
def container_exec(cron_container):
    """
    Helper to execute commands in container and check results.

    Usage:
        container_exec("ls /opt", check=True)

    Args:
        cron_container: The running cron container

    Returns:
        Function that executes commands
    """
    def _exec(command, check=False):
        """
        Execute command in container.

        Args:
            command: Command to execute
            check: If True, raise exception on non-zero exit code

        Returns:
            Tuple of (exit_code, output_str)
        """
        # Wrap command in bash -c to support shell features (cd, &&, etc.)
        exit_code, output = cron_container.exec(["bash", "-c", command])
        output_str = output.decode('utf-8') if output else ""

        if check and exit_code != 0:
            raise RuntimeError(
                f"Command failed with exit code {exit_code}\n"
                f"Command: {command}\n"
                f"Output: {output_str}"
            )

        return exit_code, output_str

    return _exec


@pytest.fixture
def installed_service(clean_container, container_exec):
    """
    Install coupang_coupon_issuer service in container.

    Returns:
        Dict with installation info:
            - container: DockerContainer
            - exec: container_exec function
            - credentials: dict with access_key, secret_key, user_id, vendor_id
    """
    # Install service
    install_cmd = (
        "cd /app && "
        "python3 main.py install "
        "--access-key test-access "
        "--secret-key test-secret "
        "--user-id test-user "
        "--vendor-id test-vendor"
    )

    container_exec(install_cmd, check=True)

    return {
        "container": clean_container,
        "exec": container_exec,
        "credentials": {
            "access_key": "test-access",
            "secret_key": "test-secret",
            "user_id": "test-user",
            "vendor_id": "test-vendor"
        }
    }


@pytest.fixture
def test_excel_file(tmp_path):
    """
    Create a test Excel file for integration tests.

    Returns:
        Path to test Excel file
    """
    from openpyxl import Workbook

    excel_file = tmp_path / "test_coupons.xlsx"

    wb = Workbook()
    ws = wb.active
    assert ws is not None

    # Add headers
    ws.append(["쿠폰이름", "쿠폰타입", "쿠폰유효기간", "할인방식", "할인금액/비율", "발급개수"])

    # Add test data
    ws.append(["테스트즉시할인", "즉시할인", 30, "RATE", 10, ""])
    ws.append(["테스트다운로드", "다운로드쿠폰", 30, "PRICE", 1000, 100])

    wb.save(excel_file)

    return excel_file
