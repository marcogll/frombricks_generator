# Lazy — Formbricks Studio

Visual survey builder & CLI manager for **Formbricks** via the Management API.

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3a3a3a?style=flat-square)
![Formbricks API](https://img.shields.io/badge/Formbricks-API-3a3a3a?style=flat-square)
![Rich TUI](https://img.shields.io/badge/Rich-TUI-3a3a3a?style=flat-square)
![Flask Web UI](https://img.shields.io/badge/Flask-Web_UI-3a3a3a?style=flat-square)
![Dark Theme](https://img.shields.io/badge/Dark_%2FLight-Theme-3a3a3a?style=flat-square)
![Docker Ready](https://img.shields.io/badge/Docker-Ready-3a3a3a?style=flat-square)

---

*made by & for lazy people who don't like repetitive tasks*

## Features

- **Web UI** — visual survey builder with dark/light themes, collapsible sidebar, live JSON preview, template gallery, JSON import with auto-fix
- **Interactive TUI** — menu-driven interface using Rich
- **Headless CLI** — direct commands for scripting/automation
- **Multi-environment** — manage multiple Formbricks environments across projects
- **Environment auto-discovery** — detect environments from your API key
- **Survey management** — list, create, view, edit, clone
- **All question types** — openText, multipleChoiceSingle/Multi, NPS, rating, date, consent, fileUpload, matrix
- **Response management** — send test responses interactively or via stdin
- **Status control** — draft, inProgress, paused, completed
- **JSON import/fix** — paste or upload JSON, auto-fills missing fields
- **JSON export** — download any survey as a `.json` file
- **Survey links** — view response/preview and edit URLs after saving
- **Evaluation module** — grade responses against an answer key with CSV/JSON export
- **TOML/YAML/JSON config** — flexible configuration format with integrity check
- **Environment manager** — add, edit, delete environments from TUI or Web UI

## Quick Start

```bash
# Clone and setup
git clone https://github.com/marcogll/frombricks_generator
cd formbricks-studio

# Virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp config.example.toml config.toml
# Edit config.toml with your Formbricks environments
# Or set defaults in .env:
#   FORMBRICKS_BASE_URL=https://app.formbricks.com
#   FORMBRICKS_API_KEY=fbk_...

# Run (easiest way)
./start.sh tui   # Interactive terminal UI
./start.sh web   # Web UI (opens browser automatically)

# Or run directly
python main.py        # TUI
python main.py serve  # Web UI
```

## Configuration

### Config file (recommended)

Formbricks Studio supports `config.toml` (preferred), `config.yaml`, or `config.json`:

```toml
[[environments]]
name = "production"
label = "Production"
env_type = "prod"
group = "My App"
base_url = "https://app.formbricks.com"
api_key = "fbk_YOUR_API_KEY"
environment_id = "env_YOUR_ENV_ID"

[[environments]]
name = "staging"
label = "Staging"
env_type = "staging"
group = "My App"
base_url = "https://staging.formbricks.com"
api_key = "fbk_YOUR_API_KEY"
environment_id = "env_YOUR_ENV_ID"
```

### Environment variables

Set defaults used by all environments:

| Variable | Description |
|----------|-------------|
| `FORMBRICKS_BASE_URL` | Default Formbricks instance URL |
| `FORMBRICKS_API_KEY` | Default API key |
| `FORMBRICKS_CONFIG` | Path to config file (auto-detected if not set) |
| `PORT` | Web UI port (default `23457`) |
| `FLASK_DEBUG` | Set to `1` for debug mode |
| `SECRET_KEY` | Flask session secret (auto-generated if not set) |

### Managing environments

**TUI:** Run `python main.py`, select option 10 "Manage environments"

**CLI:**
```bash
python main.py manage-envs list
python main.py manage-envs add
python main.py manage-envs edit my-env
python main.py manage-envs delete my-env
```

**Auto-discover:**
```bash
python main.py discover --url https://app.formbricks.com --api-key fbk_...
```

**Web UI:** Click the ⚙️ Envs button in the toolbar.

## Docker

```bash
# Build
docker build -t formbricks-studio .

# Run with config mounted
docker run -d \
  --name formbricks-studio \
  -p 8080:23457 \
  -v /path/to/config.toml:/app/config.toml \
  -e FORMBRICKS_BASE_URL=https://app.formbricks.com \
  -e FORMBRICKS_API_KEY=fbk_... \
  formbricks-studio

# Or with docker-compose
cp .env.example .env
# Edit .env with your settings
docker compose up -d
```

Open [http://localhost:8080](http://localhost:8080).

## Web UI

```bash
./start.sh web
# Open http://localhost:23457
```

Credentials are set via environment variables (`FORMBRICKS_USERNAME` / `FORMBRICKS_PASSWORD`) or `auth.json`.

### Builder panels

| Panel | Description |
|-------|-------------|
| Left (sidebar) | Collapsible survey list |
| Center | Full builder: settings, welcome card, questions, endings, advanced |
| Right | Live JSON preview |

## CLI Reference

### Interactive mode

```bash
python main.py
```

Menu:
1. List surveys
2. View survey JSON
3. Create survey
4. Add question to survey
5. Send test response
6. Change survey status
7. Switch environment
8. Load JSON from file
9. Export survey as JSON file
10. Manage environments
11. Exit

### Headless commands

```bash
python main.py list                          # List surveys
python main.py list-envs                     # List environments
python main.py discover                      # Auto-discover environments
python main.py view <survey-id>              # View survey JSON
python main.py create < survey.json          # Create from stdin
python main.py create --interactive          # Create interactively
python main.py export <survey-id> -o out.json
python main.py set-status <survey-id> inProgress
python main.py send-response <survey-id>
python main.py responses <survey-id>
python main.py manage-envs list              # List environments
python main.py manage-envs add               # Add environment interactively
```

### Evaluation

```bash
python main.py eval template <survey-id>                      # Generate answer key
python main.py eval grade <survey-id> answer_key.json         # Grade responses
python main.py eval export <survey-id>                        # Export as CSV
```

## Project Structure

```
├── main.py                 # CLI entry point
├── shared/config.py        # Shared config (TOML/YAML/JSON)
├── client/formbricks.py    # API client
├── ui/tui.py               # Rich TUI components
├── web/
│   ├── app.py              # Flask server
│   ├── static/             # JS + CSS
│   └── templates/          # HTML templates
├── eval/grader.py          # Answer key grading
├── start.sh                # Launcher (tui/web)
├── config.toml             # Environment config (gitignored)
├── config.example.toml     # Example config
├── pyproject.toml          # Project metadata
└── Dockerfile
```

## License

MIT
