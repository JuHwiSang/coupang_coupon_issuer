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
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/coupang_coupon_issuer
```

## License

MIT
