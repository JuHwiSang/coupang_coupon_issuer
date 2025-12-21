# ADR 014: Script-based Deployment (Remove PyInstaller)

**Status**: Approved
**Date**: 2024-12-21
**Replaces**: ADR 013 (PyInstaller Single Binary)

## Context

ADR 013 introduced PyInstaller-based single binary deployment to simplify distribution. However, this approach introduced significant complexity:

- **PyInstaller dependency**: `sys.frozen` and `sys.executable` checks scattered throughout codebase
- **Slow tests**: Integration tests required PyInstaller builds (6-7 minutes)
- **Inflexibility**: Working directory hardcoded at build time
- **Rebuild overhead**: Any code change required full PyInstaller rebuild
- **Path resolution complexity**: Different logic for frozen vs development modes

## Decision

Remove all PyInstaller dependencies and use script-based deployment:

### 1. CLI Interface Changes

Add positional directory argument to all commands:

```bash
# Before (PyInstaller binary)
./coupang_coupon_issuer install --access-key KEY ...
./coupang_coupon_issuer issue

# After (Python script)
python3 main.py install . --access-key KEY ...
python3 main.py issue .
python3 main.py verify .
python3 main.py uninstall .
```

**Default behavior**: When directory not specified, use `pwd` (current working directory)

### 2. Path Resolution

Replace PyInstaller-aware path resolution with simple function-based approach:

```python
# Before (config.py)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent.resolve()
else:
    BASE_DIR = Path(__file__).parent.parent.parent.resolve()

CONFIG_FILE = BASE_DIR / "config.json"

# After (config.py)
def get_base_dir(work_dir: Optional[Path] = None) -> Path:
    if work_dir is None:
        return Path.cwd().resolve()
    return Path(work_dir).resolve()

def get_config_file(base_dir: Path) -> Path:
    return base_dir / "config.json"
```

All modules now accept `base_dir` parameter explicitly.

### 3. Cron Job Format

Change from binary execution to Python script execution:

```bash
# Before (PyInstaller)
0 0 * * * /path/to/coupang_coupon_issuer issue >> /path/to/issuer.log 2>&1

# After (Script)
0 0 * * * python3 /path/to/main.py issue /work/dir >> /work/dir/issuer.log 2>&1
```

### 4. Module Updates

**ConfigManager** (`config.py`):
- All methods now accept `base_dir: Path` as first parameter
- `save_config(base_dir, ...)`
- `load_config(base_dir)`
- `load_credentials(base_dir)`
- `get_installation_id(base_dir)`
- `load_credentials_to_env(base_dir)`

**CouponIssuer** (`issuer.py`):
- Constructor accepts `base_dir: Optional[Path] = None`
- Uses `get_excel_file(base_dir)` for input file

**CrontabService** (`service.py`):
- `install(base_dir, ...)` - accepts base_dir as first parameter
- `uninstall(base_dir)` - accepts base_dir parameter
- Cron command uses `python3 main.py issue {base_dir}`

**CLI** (`main.py`):
- All subcommands accept directory argument (positional, optional except for install)
- `verify [directory] [file]`
- `issue [directory] [--jitter-max N]`
- `install directory --access-key ... `
- `uninstall [directory]`

### 5. Test Infrastructure

**Unit tests**:
- Removed `mock_frozen` fixture (no longer needed)
- Simplified `mock_config_paths` to return `tmp_path` directly
- All tests pass `base_dir` explicitly

**Integration tests** (future):
- Remove PyInstaller build step
- Execute `python3 main.py` directly in Docker
- Expected speedup: 6-7 minutes → ~1-2 minutes

## Consequences

### Positive

1. **Simpler codebase**: ~100 lines of PyInstaller-specific code removed
2. **Faster development**: No rebuild needed for code changes
3. **Faster tests**: Integration tests 3-5x faster (no PyInstaller builds)
4. **More flexible**: Working directory specified at runtime
5. **Standard Python**: Can use `pip install -e .` for development
6. **Easier debugging**: Direct Python execution, full stack traces

### Negative

1. **Requires Python**: Target system must have Python 3.10+ installed
2. **Requires dependencies**: Must `pip install requests openpyxl`
3. **Not standalone**: Not a single executable file

### Migration

**No migration needed** - Project has never been deployed to production.

For future deployments:
1. Ensure Python 3.10+ installed
2. Run `pip install -e .` or install dependencies manually
3. Use `python3 main.py install . --access-key ...`

## Implementation

### Files Modified

1. **config.py**: Removed `sys.frozen` checks, added path functions
2. **main.py**: Added directory arguments to CLI, removed PyInstaller check
3. **service.py**: Changed cron format to Python script execution
4. **issuer.py**: Added `base_dir` parameter to constructor
5. **conftest.py**: Removed PyInstaller mock fixtures
6. **tests/unit/*.py**: Updated all tests to pass `base_dir`

### UUID Tracking (Unchanged)

UUID-based cron job tracking still works identically:
- `config.json` format unchanged
- UUID still identifies installations
- Uninstall still uses UUID to find and remove cron jobs
- Directory movement requires reinstall (UUID mismatch triggers cleanup)

## Alternatives Considered

1. **Keep PyInstaller with `--dir` option**: Still requires `sys.frozen` checks, doesn't solve test speed
2. **Use package installation only**: Requires users to run `pip install`, less flexible than allowing both
3. **Docker-based deployment**: Overkill for simple cron job

## References

- ADR 013: PyInstaller Single Binary (superseded)
- Issue: Slow integration tests (6-7 minutes)
- Goal: Support both PyInstaller (optional) and script execution
