"""
Integration test fixtures using Docker + PyInstaller.

Provides fixtures for building and testing PyInstaller binaries in Docker containers.
Tests verify the single-binary deployment model with UUID-based cron tracking.

Key features:
- PyInstaller build inside Docker
- Multi-distro testing via pytest parametrize
- Pre-built images for faster test execution
- PEP 668 compatibility (--break-system-packages for newer distros)
- UUID-based cron job tracking validation
"""

import pytest
import docker
import io
from pathlib import Path
from testcontainers.core.container import DockerContainer


def get_or_build_image(base_image):
    """
    Get or build a Docker image with PyInstaller and cron pre-installed.

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
    tag = f"coupang-coupon-issuer-pyinstaller-test:{base_image.replace(':', '-')}"

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
            pip_cmd = "python3 -m pip install --break-system-packages pyinstaller requests openpyxl"
        else:
            # Ubuntu 22.04 doesn't need the flag
            pip_cmd = "python3 -m pip install pyinstaller requests openpyxl"

        dockerfile_content = f"""FROM {base_image}

# Install system dependencies
RUN apt-get update && \\
    DEBIAN_FRONTEND=noninteractive apt-get install -y \\
    python3 \\
    python3-pip \\
    sudo \\
    cron \\
    procps \\
    jq && \\
    rm -rf /var/lib/apt/lists/*

# Install PyInstaller and dependencies
RUN {pip_cmd}

# Set working directory (project code will be mounted here)
WORKDIR /app

# Start cron in foreground (systemd not available in Docker)
CMD ["bash", "-c", "cron -f"]
"""

        # Build image from in-memory Dockerfile
        f = io.BytesIO(dockerfile_content.encode('utf-8'))
        client.images.build(fileobj=f, tag=tag, rm=True)
        print(f"Successfully built test image: {tag}", flush=True)

        return tag


@pytest.fixture(
    scope="session",
    params=[
        "ubuntu:24.04",  # Noble Numbat, Python 3.12
        "ubuntu:22.04",  # Jammy Jellyfish, Python 3.10
        "debian:13",     # Trixie, Python 3.12
        "debian:12",     # Bookworm, Python 3.11
    ]
)
def test_image(request):
    """
    Get or build test Docker image for multiple distributions.

    Tests automatically run on 4 different images via parametrize.
    This ensures compatibility across Ubuntu 22.04+, Debian 12+.

    Returns:
        str: Tag of the built/existing image
    """
    base_image = request.param
    return get_or_build_image(base_image)


@pytest.fixture
def test_container(test_image):
    """
    Create Docker container with PyInstaller and cron.

    Returns:
        DockerContainer: Running container
    """
    project_root = Path(__file__).parent.parent.parent

    container = DockerContainer(test_image)
    # container.with_command("/bin/bash")
    container.with_kwargs(stdin_open=True, tty=True)

    # Mount project code as READ-ONLY to /mnt/src
    # Then copy to /app for building (security best practice)
    container.with_volume_mapping(
        str(project_root.resolve()),
        "/mnt/src",
        mode="ro"
    )

    print(f"Starting container...", flush=True)
    container.start()
    print(f"Container started: {container.get_wrapped_container().id}", flush=True)

    # Copy source to /app (writable)
    print("Copying source code to /app...", flush=True)
    container.exec(["bash", "-c", "cp -r /mnt/src/* /app/"])

    # Note: cron is already running via CMD (cron && tail -f /var/log/cron.log)
    print("Container ready (cron running in foreground)", flush=True)

    yield container

    print("Stopping container...", flush=True)
    container.stop()


@pytest.fixture
def built_binary(test_container):
    """
    Build PyInstaller binary inside container.

    Returns:
        str: Path to built binary inside container
    """
    print("Building PyInstaller binary...", flush=True)

    # Build with PyInstaller (add --paths to include src directory)
    exit_code, output = test_container.exec([
        "bash", "-c",
        "cd /app/src && pyinstaller --onefile --name coupang_coupon_issuer "
        "--paths /app/src ../main.py" # --paths 없으면 coupang_coupon_issuer 모듈을 못 찾음
    ])

    if exit_code != 0:
        output_str = output.decode('utf-8') if output else ""
        pytest.fail(f"PyInstaller build failed: {output_str}")

    # Verify binary exists
    exit_code, _ = test_container.exec(["test", "-f", "/app/src/dist/coupang_coupon_issuer"])
    if exit_code != 0:
        pytest.fail("Binary not found after build")

    print("Binary built successfully", flush=True)
    return "/app/src/dist/coupang_coupon_issuer"


@pytest.fixture
def clean_install_dir(test_container):
    """
    Clean up test installation directory before each test.

    Returns:
        str: Test installation directory path
    """
    test_dir = "/root/test_install"

    # Clean up
    test_container.exec(["bash", "-c", f"rm -rf {test_dir}"])
    test_container.exec(["bash", "-c", "crontab -r || true"])

    # Create directory
    test_container.exec(["bash", "-c", f"mkdir -p {test_dir}"])

    return test_dir


@pytest.fixture
def container_exec(test_container):
    """
    Helper to execute commands in container.

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
        exit_code, output = test_container.exec(["bash", "-c", command])
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
def sample_excel(test_container, clean_install_dir):
    """
    Create sample Excel file in container.

    Returns:
        str: Path to Excel file inside container
    """
    # Create Excel file using Python (escape quotes properly)
    excel_path = f"{clean_install_dir}/coupons.xlsx"

    create_excel_script = f"""
import openpyxl

wb = openpyxl.Workbook()
ws = wb.active

ws.append(['쿠폰이름', '쿠폰타입', '쿠폰유효기간', '할인방식', '할인금액/비율', '발급개수'])
ws.append(['테스트쿠폰1', '즉시할인', 30, 'RATE', 10, ''])
ws.append(['테스트쿠폰2', '다운로드쿠폰', 15, 'PRICE', 500, 100])
ws.append(['테스트쿠폰3', '다운로드쿠폰', 30, 'FIXED_WITH_QUANTITY', 1000, 50])

wb.save('{excel_path}')
"""

    # Use heredoc to avoid quoting issues
    exit_code, output = test_container.exec([
        "bash", "-c",
        f"python3 -c \"{create_excel_script}\""
    ])

    if exit_code != 0:
        output_str = output.decode('utf-8') if output else ""
        pytest.fail(f"Failed to create Excel file: {output_str}")

    # Verify file exists
    exit_code, _ = test_container.exec(["test", "-f", excel_path])
    if exit_code != 0:
        pytest.fail(f"Failed to create Excel file at {excel_path}")

    return excel_path
