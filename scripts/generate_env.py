#!/usr/bin/env python3
"""Generate .env from existing config.json/config.toml for Docker deployment."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.config import load_config, find_config, env_defaults

config_path = find_config()
cfg = load_config(config_path)

envs = cfg.get("environments", [])
defaults = env_defaults()

lines = [
    "# Auto-generated from config file",
    "# Do NOT commit this file - contains API keys",
    "",
    f"PORT={os.environ.get('PORT', '23457')}",
    f"FLASK_DEBUG={os.environ.get('FLASK_DEBUG', '0')}",
]

if defaults.get("base_url") or envs:
    url = defaults.get("base_url") or envs[0].get("base_url", "")
    lines.append(f'FORMBRICKS_BASE_URL={url}')

if defaults.get("api_key") or envs:
    key = defaults.get("api_key") or envs[0].get("api_key", "")
    lines.append(f'FORMBRICKS_API_KEY={key}')

output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
with open(output_path, "w") as f:
    f.write("\n".join(lines) + "\n")

print(f".env generated at: {output_path}")
print("Add .env to your .gitignore if not already done.")
