<p align="center">
  <a href="https://soul23.mx" target="_blank">
    <img src="https://raw.githubusercontent.com/marcogll/mg_data_storage/refs/heads/main/soul23/logo/s23_logo.svg" width="80" alt="Soul23">
  </a>
</p>
<h1 align="center">Formbricks Studio</h1>
<p align="center">
  Visual survey builder & CLI manager for <a href="https://formbricks.com">Formbricks</a> via the Management API v1/v2
  <br>
  <a href="https://soul23.mx"><strong>Soul23 · Grupo AlMa del Norte</strong></a>
</p>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3a3a3a?style=flat-square" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Formbricks-API-3a3a3a?style=flat-square" alt="Formbricks API">
  <img src="https://img.shields.io/badge/Rich-TUI-3a3a3a?style=flat-square" alt="Rich TUI">
  <img src="https://img.shields.io/badge/Flask-Web_UI-3a3a3a?style=flat-square" alt="Flask Web UI">
  <img src="https://img.shields.io/badge/Catppuccin-Theme-3a3a3a?style=flat-square" alt="Catppuccin Theme">
  <img src="https://img.shields.io/badge/CLI-Headless-3a3a3a?style=flat-square" alt="CLI Headless">
  <img src="https://img.shields.io/badge/Docker-Ready-3a3a3a?style=flat-square" alt="Docker Ready">
</p>

---

## Features

- **Web UI** — visual survey builder with dark/light themes (Catppuccin Frappe/Latte), collapsible sidebar, live JSON preview, template gallery, JSON import with auto-fix
- **Interactive TUI** — menu-driven interface using Rich
- **Headless CLI** — direct commands for scripting/automation
- **Multi-environment** — grouped by app (Vanity, Soul23, Socia) with prod/dev selectors
- **Survey management** — list, create, view, edit, clone
- **All question types** — openText, multipleChoiceSingle/Multi, NPS, rating, date, consent, fileUpload, matrix — with full field support (IDs, headlines, subheaders, placeholders, button/back labels, shuffle, validation)
- **Response management** — send test responses interactively or via stdin
- **Status control** — draft, inProgress, paused, completed
- **JSON import/fix** — paste or upload JSON, auto-fills missing fields (IDs, headlines, welcome card, endings, etc.)
- **JSON export** — download any survey as a `.json` file from TUI or headless CLI
- **Survey links** — view response/preview and edit URLs after saving
- **Draft validation** — warns when welcome card is missing and prompts to add one
- **Evaluation module** — grade responses against an answer key with CSV/JSON export

## Requirements

- Python 3.10+
- `requests`, `rich`, `flask`

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests rich flask
```

## Configuration

```bash
cp config.example.json config.json
# Edit with your environments
```

Each environment can optionally belong to a **group** (app name) and have an **env_type** (prod/dev):

```json
{
  "environments": [
    {
      "name": "vanity",
      "label": "Vanity",
      "env_type": "prod",
      "group": "Vanity",
      "base_url": "https://feedback.soul23.cloud",
      "api_key": "fbk_your_key",
      "environment_id": "env-id"
    },
    {
      "name": "vanity-dev",
      "label": "Vanity",
      "env_type": "dev",
      "group": "Vanity",
      "base_url": "https://feedback.soul23.cloud",
      "api_key": "fbk_your_key",
      "environment_id": "env-dev-id"
    }
  ]
}
```

The Web UI groups environments by `group` using `<optgroup>` selectors. The TUI shows the group + env_type label.

---

## Docker

```bash
# Build the image
docker build -t formbricks-studio .

# Run with your config mounted
docker run -d \
  --name formbricks-studio \
  -p 8080:8080 \
  -v /path/to/config.json:/app/config.json \
  formbricks-studio
```

Open [http://localhost:8080](http://localhost:8080).

| Env | Description |
|-----|-------------|
| `PORT` | Port (default `8080`) |
| `FLASK_DEBUG` | Set to `1` for debug mode |

> **Note**: The CLI/TUI commands (list, create, etc.) are only available when running outside Docker, since they need a terminal. Docker runs the Web UI only.

---

## Web UI

```bash
python main.py serve
# Open http://localhost:8080
```

### Builder panels

| Panel | Description |
|-------|-------------|
| Left (sidebar) | Collapsible survey list — click to load any survey |
| Center | Full builder: basic settings, welcome card, questions, endings, advanced |
| Right | Live JSON preview |

### Features

- **Theme toggle** — switch between Catppuccin Frappe (dark) and Latte (light), persisted in localStorage
- **Sidebar collapse** — click header to collapse/expand, persisted in localStorage
- **Env selector** — grouped by app (Vanity, Soul23, Socia) with prod/dev options
- **Survey links** — after saving or loading a survey, shows response/preview + edit URLs
- **Save confirmation** — prompts "¿Estás seguro?" before creating a new survey
- **JSON Import** — paste JSON or upload a file, then click "Fix & Load" to auto-fill missing fields and load into the builder
- **Template gallery** — one-click add any question type
- **Full question editor** — all fields: ID, headline, subheader, choices, button labels, back button, shuffle, validation, etc.
- **Download JSON** — save survey as `.json` file

### Save workflow

1. Build or edit your survey
2. Click **Save** (confirm dialog for new surveys)
3. Survey is pushed to the selected Formbricks environment
4. Links appear: **Edit in Formbricks** and **Response / Preview**

---

## CLI Reference

### Interactive mode

```bash
python main.py
```

Menu options:
1. List surveys
2. View survey JSON
3. Create survey (interactive)
4. Add question to survey
5. Send test response
6. Change survey status
7. Switch environment
8. Load JSON from file
9. Export survey as JSON file
10. Exit

### Environment selection

```bash
python main.py --env vanity list
python main.py --env soul23-dev create --interactive
```

### List surveys

```bash
python main.py list
```

### View survey JSON

```bash
python main.py view <survey-id>
```

### Create a survey

From stdin:
```bash
cat survey.json | python main.py create
```

Interactively:
```bash
python main.py create --interactive
```

### Add a question

Interactive prompts for type, ID, headline, choices, button labels, etc.

```bash
python main.py add-question <survey-id>
```

From stdin:
```bash
cat <<'EOF' | python main.py add-question <survey-id>
{"id":"q1","type":"openText","headline":{"default":"Name?"},"required":true,"inputType":"text","buttonLabel":{"default":"Next"}}
EOF
```

### Send test response

```bash
python main.py send-response <survey-id>
```

From stdin:
```bash
cat <<'EOF' | python main.py send-response
{"surveyId":"...","data":{"q1":"test answer"},"finished":true}
EOF
```

### Change status

```bash
python main.py set-status <survey-id> inProgress
```

Statuses: `draft`, `inProgress`, `paused`, `completed`

### Export survey as JSON

```bash
python main.py export <survey-id> -o survey.json
```

If `-o` is omitted, the file is saved as `<survey-name>.json`.

### List responses

```bash
python main.py responses <survey-id>
```

### Start Web UI

```bash
python main.py serve
```

---

## Formbricks Management API Reference

This tool uses the Formbricks **Management API** (v1 and v2). All requests are authenticated via `x-api-key` header.

### v1 Endpoints

| Method | Endpoint | Used by |
|--------|----------|---------|
| `GET` | `/api/v1/management/surveys` | List all surveys |
| `POST` | `/api/v1/management/surveys` | Create a survey |
| `GET` | `/api/v1/management/surveys/{id}` | View / export a survey |
| `PUT` | `/api/v1/management/surveys/{id}` | Update survey (status, questions, etc.) |
| `DELETE` | `/api/v1/management/surveys/{id}` | Delete a survey |
| `GET` | `/api/v1/management/responses?surveyId={id}` | List responses for grading / CSV export |

### v2 Endpoints

| Method | Endpoint | Used by |
|--------|----------|---------|
| `POST` | `/api/v2/management/responses` | Send a test response |

> Note: Responses use **v2** because v1 returns `409 Conflict` on survey creation race conditions. Surveys stay on **v1** — these APIs are stable and match the official Formbricks management spec.

---

## Complete Question Type Reference

Every field is included — IDs, headlines, subheaders, placeholders, button labels, back buttons, choices, etc.

### openText

```json
{
  "id": "nombre",
  "type": "openText",
  "headline": { "default": "¿Cuál es tu nombre completo?" },
  "required": true,
  "inputType": "text",
  "subheader": { "default": "Tal como aparece en tu identificación oficial" },
  "placeholder": { "default": "María García" },
  "longAnswer": false,
  "buttonLabel": { "default": "Siguiente" },
  "backButtonLabel": { "default": "Atrás" }
}
```

| Field | Values |
|-------|--------|
| `inputType` | `text`, `number`, `phone`, `email` |
| `longAnswer` | `true` (textarea) or `false` (single line) |

### multipleChoiceSingle

```json
{
  "id": "sucursal",
  "type": "multipleChoiceSingle",
  "headline": { "default": "¿A qué sucursal perteneces?" },
  "required": true,
  "choices": [
    { "id": "c1", "label": { "default": "Plaza O" } },
    { "id": "c2", "label": { "default": "Los Pinos" } }
  ],
  "shuffleOption": "none",
  "buttonLabel": { "default": "Siguiente" },
  "backButtonLabel": { "default": "Atrás" }
}
```

With "Other" option:
```json
{
  "id": "ciudad",
  "choices": [ ... ],
  "otherOptionPlaceholder": { "default": "¿Cuál?" }
}
```

### multipleChoiceMulti

```json
{
  "id": "intereses",
  "type": "multipleChoiceMulti",
  "headline": { "default": "Selecciona tus áreas de interés:" },
  "required": false,
  "choices": [
    { "id": "a1", "label": { "default": "Uñas" } },
    { "id": "a2", "label": { "default": "SPA" } }
  ],
  "shuffleOption": "none",
  "buttonLabel": { "default": "Siguiente" },
  "backButtonLabel": { "default": "Atrás" }
}
```

### nps

```json
{
  "id": "nps_score",
  "type": "nps",
  "headline": { "default": "¿Qué tan probable es que nos recomiendes?" },
  "required": true,
  "lowerLabel": { "default": "Nada probable" },
  "upperLabel": { "default": "Extremadamente probable" },
  "buttonLabel": { "default": "Siguiente" }
}
```

Scale 0–10. Lower/upper labels are optional.

### rating

```json
{
  "id": "satisfaccion",
  "type": "rating",
  "headline": { "default": "Califica tu experiencia:" },
  "required": true,
  "rate": 5,
  "lowerLabel": { "default": "Malo" },
  "upperLabel": { "default": "Excelente" },
  "buttonLabel": { "default": "Siguiente" }
}
```

`rate` = max stars (2–10).

### date

```json
{
  "id": "fecha_ingreso",
  "type": "date",
  "headline": { "default": "¿Cuál fue tu primer día?" },
  "required": true,
  "format": "d-M-y",
  "buttonLabel": { "default": "Siguiente" },
  "backButtonLabel": { "default": "Atrás" }
}
```

| Format | Example |
|--------|---------|
| `d-M-y` | 7-May-2026 |
| `M-d-y` | May-7-2026 |
| `y-M-d` | 2026-May-7 |

### consent

```json
{
  "id": "consent",
  "type": "consent",
  "headline": { "default": "¿Aceptas los términos y condiciones?" },
  "required": true,
  "label": { "default": "He leído y acepto el aviso de privacidad" },
  "subheader": { "default": "<p>Tu información será tratada con confidencialidad.</p>" },
  "buttonLabel": { "default": "Aceptar" }
}
```

### fileUpload

```json
{
  "id": "ine_frontal",
  "type": "fileUpload",
  "headline": { "default": "Sube una foto de tu INE (frontal)" },
  "required": true,
  "allowMultipleFiles": false,
  "maxSizeInMB": 10,
  "validation": {
    "logic": "and",
    "rules": [
      {
        "type": "fileExtensionIs",
        "params": { "extensions": ["jpg", "png", "heic", "pdf"] }
      }
    ]
  },
  "buttonLabel": { "default": "Siguiente" },
  "backButtonLabel": { "default": "Atrás" }
}
```

### matrix

```json
{
  "id": "evaluacion",
  "type": "matrix",
  "headline": { "default": "Evalúa cada aspecto:" },
  "required": true,
  "columns": [
    { "id": "excelente", "label": { "default": "Excelente" } },
    { "id": "bueno", "label": { "default": "Bueno" } },
    { "id": "regular", "label": { "default": "Regular" } },
    { "id": "malo", "label": { "default": "Malo" } }
  ],
  "rows": [
    { "id": "calidad", "label": { "default": "Calidad del servicio" } },
    { "id": "atencion", "label": { "default": "Atención al cliente" } }
  ],
  "buttonLabel": { "default": "Siguiente" }
}
```

---

## Real-World Examples

### Minimal survey

```json
{
  "name": "Feedback Rápido",
  "type": "link",
  "status": "draft",
  "welcomeCard": { "enabled": true, "headline": { "default": "¡Gracias!" }, "buttonLabel": { "default": "Comenzar" } },
  "questions": [
    { "id": "nombre", "type": "openText", "headline": { "default": "¿Nombre?" }, "required": true, "inputType": "text", "buttonLabel": { "default": "Siguiente" } },
    { "id": "nps", "type": "nps", "headline": { "default": "¿Nos recomiendas?" }, "required": true, "buttonLabel": { "default": "Finalizar" } }
  ],
  "displayOption": "displayOnce",
  "thankYouCard": { "enabled": false }
}
```

### Full survey from template

```bash
curl -s http://localhost:8080/api/templates/full-survey | python main.py create
```

### Load from file

```bash
python main.py load
# Prompts for file path, validates, and shows JSON
```

---

## Project Structure

```
├── main.py                 # CLI entry point (argparse + interactive loop)
├── config.json             # Environment config (gitignored)
├── config.example.json     # Example config template
├── client/
│   └── formbricks.py       # API client (v1 + v2 management endpoints)
├── ui/
│   └── tui.py              # Rich TUI components (menus, prompts, tables)
├── eval/
│   ├── grader.py           # Answer key grading logic
│   └── __init__.py
├── web/
│   ├── app.py              # Flask server (API proxy + survey builder)
│   ├── static/
│   │   ├── app.js          # Builder logic, import/fix, themes, sidebar
│   │   └── style.css       # Catppuccin Frappe/Latte themes
│   └── templates/
│       └── index.html      # Single-page builder UI
└── README.md
```

---

<p align="center">
  <a href="https://soul23.mx"><strong>Soul23 · Grupo AlMa del Norte</strong></a>
  <br>
  <sub>Todos los derechos reservados</sub>
</p>
