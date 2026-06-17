import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    import yaml
except ImportError:
    yaml = None


CONFIG_ENV_VAR = "FORMBRICKS_CONFIG"
DEFAULT_BASE_URL_ENV_VARS = ["FORMBRICKS_BASE_URL", "FORMBRICKS_URL"]
DEFAULT_API_KEY_ENV_VARS = ["FORMBRICKS_API_KEY", "FORMBRICKS_APIKEY"]

CONFIG_FILES = ["config.toml", "config.yaml", "config.yml", "config.json"]

INTEGRITY_KEY = "_integrity"


def project_root() -> Path:
    return Path(__file__).parent.parent.resolve()


def find_config(path: Optional[str] = None) -> str:
    if path:
        p = Path(path)
        if p.is_absolute():
            return str(p)
        return str(project_root() / p)
    env_path = os.environ.get(CONFIG_ENV_VAR)
    if env_path and os.path.exists(env_path):
        return env_path
    base = project_root()
    for name in CONFIG_FILES:
        p = base / name
        if p.exists():
            return str(p)
    return str(base / "config.toml")


def env_defaults() -> dict:
    defaults = {}
    for var in DEFAULT_BASE_URL_ENV_VARS:
        val = os.environ.get(var)
        if val:
            defaults["base_url"] = val.rstrip("/")
            break
    for var in DEFAULT_API_KEY_ENV_VARS:
        val = os.environ.get(var)
        if val:
            defaults["api_key"] = val
            break
    return defaults


def apply_env_defaults(cfg: dict) -> dict:
    env_def = env_defaults()
    if env_def:
        for env in cfg.get("environments", []):
            if not env.get("base_url") and env_def.get("base_url"):
                env["base_url"] = env_def["base_url"]
            if not env.get("api_key") and env_def.get("api_key"):
                env["api_key"] = env_def["api_key"]
    return cfg


def canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)


def compute_checksum(data: dict) -> str:
    canonical = canonical_json(data)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_config(path: Optional[str] = None) -> dict:
    config_path = find_config(path)

    if not os.path.exists(config_path):
        cfg = {"environments": []}
        defaults = env_defaults()
        if defaults.get("base_url") or defaults.get("api_key"):
            if defaults.get("base_url") and defaults.get("api_key"):
                log(f"Using env defaults: {defaults['base_url']}")
        return cfg

    with open(config_path) as f:
        raw = f.read()

    ext = Path(config_path).suffix.lower()
    try:
        if ext == ".toml":
            if tomllib is None:
                log("TOML support requires Python 3.11+ or: pip install tomli", err=True)
                sys.exit(1)
            cfg = tomllib.loads(raw)
        elif ext in (".yaml", ".yml"):
            if yaml is None:
                log("YAML support requires: pip install pyyaml", err=True)
                sys.exit(1)
            cfg = yaml.safe_load(raw)
        else:
            cfg = json.loads(raw)
    except (tomllib.TOMLDecodeError, json.JSONDecodeError, yaml.YAMLError) as e:
        log(f"Error parsing {config_path}: {e}", err=True)
        sys.exit(1)

    if not isinstance(cfg, dict):
        cfg = {"environments": []}
    cfg.setdefault("environments", [])

    needs_migration = INTEGRITY_KEY not in cfg

    cfg = verify_integrity(cfg, config_path)
    cfg = apply_env_defaults(cfg)

    if needs_migration and cfg.get("environments"):
        log(f"Migrating {config_path} to add integrity checksum...")
        save_config(cfg, config_path)

    return cfg


def verify_integrity(cfg: dict, config_path: str) -> dict:
    stored = cfg.get(INTEGRITY_KEY)
    if not stored:
        return cfg

    expected = stored.get("sha256", "")
    if not expected:
        return cfg

    # Compute hash excluding the integrity key itself
    check_data = {k: v for k, v in cfg.items() if k != INTEGRITY_KEY}
    current = compute_checksum(check_data)
    if current != expected:
        generated = stored.get("generated", "unknown")
        log(f"⚠ Config file changed since it was generated ({generated})!", err=True)
        log(f"  Expected hash: {expected}", err=True)
        log(f"  Current hash:  {current}", err=True)
        log(f"  If you edited it intentionally, save again to update the checksum.", err=True)
    return cfg


def save_config(cfg: dict, path: Optional[str] = None):
    if path:
        p = Path(path)
        config_path = str(p) if p.is_absolute() else str(project_root() / p)
    else:
        config_path = find_config()

    cfg_copy = {k: v for k, v in cfg.items() if k != "_defaults"}
    cfg_copy.pop(INTEGRITY_KEY, None)

    cfg_copy[INTEGRITY_KEY] = {
        "sha256": compute_checksum(cfg_copy),
        "generated": datetime.now(timezone.utc).isoformat(),
    }

    ext = Path(config_path).suffix.lower()
    with open(config_path, "w") as f:
        if ext == ".toml":
            f.write(dict_to_toml(cfg_copy))
        elif ext in (".yaml", ".yml"):
            if yaml is None:
                log("YAML support requires: pip install pyyaml", err=True)
                sys.exit(1)
            yaml.dump(cfg_copy, f, default_flow_style=False, allow_unicode=True)
        else:
            json.dump(cfg_copy, f, indent=2, ensure_ascii=False)
            f.write("\n")


def dict_to_toml(d: dict) -> str:
    lines = []
    integrity = d.get(INTEGRITY_KEY)
    if integrity:
        lines.append(f'[{INTEGRITY_KEY}]')
        lines.append(f'sha256 = "{integrity["sha256"]}"')
        lines.append(f'generated = "{integrity["generated"]}"')
        lines.append("")

    for env in d.get("environments", []):
        lines.append("[[environments]]")
        for key in ("name", "label", "env_type", "group", "base_url", "api_key", "environment_id"):
            val = env.get(key)
            if val:
                lines.append(f'{key} = "{val}"')
        lines.append("")
    return "\n".join(lines) + "\n"


def validate_config(cfg: dict) -> list[str]:
    warnings = []
    for i, env in enumerate(cfg.get("environments", [])):
        if not env.get("name"):
            warnings.append(f"Environment #{i + 1}: missing 'name'")
        if not env.get("base_url"):
            warnings.append(f"Environment '{env.get('name', '?')}': missing 'base_url'")
        if not env.get("api_key"):
            warnings.append(f"Environment '{env.get('name', '?')}': missing 'api_key'")
    return warnings


def ensure_config(path: Optional[str] = None) -> str:
    if path and os.path.exists(path):
        cfg = load_config(path)
        warnings = validate_config(cfg)
        for w in warnings:
            log(f"⚠ {w}", err=True)
        return path

    config_path = path if path else find_config()
    if os.path.exists(config_path):
        cfg = load_config(config_path)
        warnings = validate_config(cfg)
        for w in warnings:
            log(f"⚠ {w}", err=True)
        return config_path

    defaults = env_defaults()
    url = defaults.get("base_url")
    key = defaults.get("api_key")

    if not url or not key:
        log("No config found and no FORMBRICKS_BASE_URL/FORMBRICKS_API_KEY set", err=True)
        log("Create config.toml manually or set env vars and re-run", err=True)
        return config_path

    log("No config found — attempting auto-discovery...")
    try:
        from client.formbricks import FormbricksClient
        discovered = FormbricksClient.discover_environments(url, key)
    except Exception as e:
        log(f"Auto-discovery failed: {e}", err=True)
        discovered = []

    if discovered:
        cfg = {"environments": []}
        existing = set()
        for env in discovered:
            name = env.get("name", "default")
            if name in existing:
                continue
            existing.add(name)
            env.setdefault("label", name.capitalize())
            env.setdefault("env_type", "prod")
            env.setdefault("group", "Default")
            cfg["environments"].append(env)
        save_config(cfg, config_path)
        log(f"Config generated: {config_path} ({len(cfg['environments'])} environments)")
    else:
        log("Auto-discovery returned no environments.", err=True)
        log(f"Creating empty config at {config_path} — add environments via the app.", err=True)
        empty = {"environments": []}
        save_config(empty, config_path)

    return config_path


def log(msg: str, err: bool = False):
    out = sys.stderr if err else sys.stdout
    print(f"[config] {msg}", file=out)
