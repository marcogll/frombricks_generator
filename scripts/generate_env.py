#!/usr/bin/env python3
import json
import os
import sys

config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

if not os.path.exists(config_path):
    print("Error: config.json no encontrado")
    sys.exit(1)

with open(config_path) as f:
    config = json.load(f)

envs_json = json.dumps(config.get("environments", []), ensure_ascii=False)

env_content = f"""# Auto-generado desde config.json
# NO comprometer este archivo - contiene API keys

PORT=23457
FLASK_DEBUG=0
FORMBRICKS_ENVIRONMENTS='{env_json}'
"""

with open(output_path, "w") as f:
    f.write(env_content)

print(f".env generado en: {output_path}")
print("Recuerda agregar .env a .gitignore si no lo tienes")