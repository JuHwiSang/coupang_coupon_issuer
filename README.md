# Coupang Coupon Issuer

Automated coupon issuance service running on Linux with cron scheduling.

## Features

- Daily coupon issuance at midnight (cron-based)
- Secure API key storage (600 permissions)
- Simple cron job management
- User-friendly logging (no sudo required)
- Auto-installation of cron on major distributions

## Requirements

- Python 3.10+
- Linux OS (cron will be auto-installed if missing)
- root access (for service installation)

## Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd coupang_coupon_issuer

# 2. Install dependencies
uv sync

# 3. Install cron-based service
sudo python3 main.py install \
  --access-key YOUR_ACCESS_KEY \
  --secret-key YOUR_SECRET_KEY \
  --user-id YOUR_USER_ID \
  --vendor-id YOUR_VENDOR_ID
```

## Usage

### Service Management

```bash
# View cron schedule
crontab -l

# View logs
tail -f ~/.local/state/coupang_coupon_issuer/issuer.log

# Manual execution (for testing)
coupang_coupon_issuer issue

# Edit cron schedule manually
crontab -e
```

### Uninstall Service

```bash
sudo python3 main.py uninstall
```

## Development

### Running Tests

```bash
# Run unit tests only
uv run pytest tests/unit -v

# Run integration tests (requires Docker Desktop)
uv run pytest tests/integration -v -m integration

# Run all tests
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/coupang_coupon_issuer
```

### Test Statistics

- **Unit Tests**: 108 tests
  - Windows: 80/108 (service.py tests skipped)
  - Linux: 108/108 (all tests run)
- **Integration Tests**: 20 tests (Docker required)
  - 100% pass rate (103 seconds)
  - Tests cron installation, uninstallation, and E2E workflows
  - Ubuntu 22.04 container with cron service

## License

MIT
