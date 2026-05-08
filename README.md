<p align="center">
  <img src="https://raw.githubusercontent.com/marcogll/mg_data_storage/refs/heads/main/soul23/logo/soul23_logo.svg" width="110" alt="Soul23">
</p>
<h1 align="center">Formbricks CLI Manager</h1>
<p align="center">
  TUI/CLI tool to manage a Formbricks instance via the Management API v1/v2 🔧
</p>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3a3a3a?style=flat-square" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Formbricks-API-3a3a3a?style=flat-square" alt="Formbricks API">
  <img src="https://img.shields.io/badge/Rich-TUI-3a3a3a?style=flat-square" alt="Rich TUI">
  <img src="https://img.shields.io/badge/Flask-Web_UI-3a3a3a?style=flat-square" alt="Flask Web UI">
  <img src="https://img.shields.io/badge/CLI-Headless-3a3a3a?style=flat-square" alt="CLI Headless">
</p>

## Features

- **Interactive TUI** — menu-driven interface using Rich
- **Headless mode** — direct commands for scripting/automation
- **Multi-environment** — switch between envs (prod/staging/dev)
- **Survey management** — list, create, view, edit
- **Question management** — add questions via JSON or interactively, all types and fields
- **Response management** — send test responses
- **Status control** — draft, inProgress, paused, completed
- **Web UI** — visual survey builder with live JSON preview

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

```json
{
  "environments": [
    {
      "name": "production",
      "base_url": "https://feedback.soul23.cloud",
      "api_key": "fbk_your_key",
      "environment_id": "env-id"
    }
  ]
}
```

---

## CLI Reference: Creating & Editing Surveys

### Create a survey with questions

Build a JSON file and pipe it in:

```bash
cat survey.json | python main.py create
```

Or create interactively:

```bash
python main.py create --interactive
```

### Add a question to an existing survey

```bash
python main.py add-question <survey-id>
```

Interactive prompts will ask for question type, ID, headline, choices (if applicable), button labels, etc.

### View survey JSON

```bash
python main.py view <survey-id>
```

### Change survey status

```bash
python main.py set-status <survey-id> inProgress
```

Statuses: `draft`, `inProgress`, `paused`, `completed`

### Switch environment

```bash
python main.py --env test list
python main.py --env production create -i
```

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

**CLI add:**
```bash
cat <<'EOF' | python main.py add-question <survey-id>
{"id":"nombre","type":"openText","headline":{"default":"¿Nombre?"},"required":true,"inputType":"text","buttonLabel":{"default":"Next"}}
EOF
```

---

### multipleChoiceSingle

```json
{
  "id": "sucursal",
  "type": "multipleChoiceSingle",
  "headline": { "default": "¿A qué sucursal perteneces?" },
  "required": true,
  "choices": [
    { "id": "c1", "label": { "default": "Plaza O" } },
    { "id": "c2", "label": { "default": "Los Pinos" } },
    { "id": "c3", "label": { "default": "Plaza CIMA" } }
  ],
  "shuffleOption": "none",
  "buttonLabel": { "default": "Siguiente" },
  "backButtonLabel": { "default": "Atrás" }
}
```

**With "Other" option:**
```json
{
  "id": "ciudad",
  "type": "multipleChoiceSingle",
  "headline": { "default": "¿Ciudad?" },
  "required": true,
  "choices": [
    { "id": "saltillo", "label": { "default": "Saltillo" } },
    { "id": "other", "label": { "default": "Otra" } }
  ],
  "shuffleOption": "none",
  "otherOptionPlaceholder": { "default": "¿Cuál?" },
  "buttonLabel": { "default": "Siguiente" }
}
```

---

### multipleChoiceMulti

```json
{
  "id": "intereses",
  "type": "multipleChoiceMulti",
  "headline": { "default": "Selecciona tus áreas de interés:" },
  "required": false,
  "choices": [
    { "id": "a1", "label": { "default": "Uñas" } },
    { "id": "a2", "label": { "default": "SPA" } },
    { "id": "a3", "label": { "default": "Maquillaje" } }
  ],
  "shuffleOption": "none",
  "buttonLabel": { "default": "Siguiente" },
  "backButtonLabel": { "default": "Atrás" }
}
```

---

### nps (Net Promoter Score)

```json
{
  "id": "nps_score",
  "type": "nps",
  "headline": { "default": "¿Qué tan probable es que nos recomiendes?" },
  "required": true,
  "buttonLabel": { "default": "Siguiente" },
  "lowerLabel": { "default": "Nada probable" },
  "upperLabel": { "default": "Extremadamente probable" }
}
```

Scale 0–10. Lower/upper labels are optional but recommended.

---

### rating

```json
{
  "id": "satisfaccion",
  "type": "rating",
  "headline": { "default": "Califica tu experiencia:" },
  "required": true,
  "rate": 5,
  "buttonLabel": { "default": "Siguiente" },
  "lowerLabel": { "default": "Malo" },
  "upperLabel": { "default": "Excelente" }
}
```

`rate` = max stars (2–10).

---

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

---

### consent

```json
{
  "id": "consent",
  "type": "consent",
  "headline": { "default": "Aceptas los términos y condiciones?" },
  "required": true,
  "label": { "default": "He leído y acepto el aviso de privacidad" },
  "subheader": { "default": "<p>Tu información será tratada con confidencialidad.</p>" },
  "buttonLabel": { "default": "Aceptar" }
}
```

The checkbox text is in `label`. The `headline` is the title shown above.

---

### fileUpload

```json
{
  "id": "ine_frontal",
  "type": "fileUpload",
  "headline": { "default": "Sube una foto de tu INE (frontal)" },
  "required": true,
  "subheader": { "default": "La foto debe ser legible, sin reflejos" },
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

---

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
    { "id": "atencion", "label": { "default": "Atención al cliente" } },
    { "id": "instalaciones", "label": { "default": "Instalaciones" } }
  ],
  "buttonLabel": { "default": "Siguiente" }
}
```

Each row gets a radio-button group with the columns as options.

---

## Real-World Survey Examples

### Minimal survey with welcome card + 2 questions

```json
{
  "name": "Feedback Rápido",
  "type": "link",
  "status": "draft",
  "welcomeCard": {
    "enabled": true,
    "headline": { "default": "¡Gracias por tu tiempo!" },
    "buttonLabel": { "default": "Comenzar" }
  },
  "questions": [
    {
      "id": "nombre",
      "type": "openText",
      "headline": { "default": "¿Cómo te llamas?" },
      "required": true,
      "inputType": "text",
      "buttonLabel": { "default": "Siguiente" }
    },
    {
      "id": "nps",
      "type": "nps",
      "headline": { "default": "¿Qué tan probable es que nos recomiendes?" },
      "required": true,
      "buttonLabel": { "default": "Finalizar" }
    }
  ],
  "displayOption": "displayOnce",
  "thankYouCard": { "enabled": false }
}
```

```bash
cat feedback.json | python main.py create
```

### Full survey with all question types

```bash
# Download a full template
curl -s http://localhost:8080/api/templates/full-survey | python main.py create
```

### Update survey status

```bash
python main.py set-status <survey-id> inProgress
python main.py set-status <survey-id> completed
```

### Add a question to an existing survey via stdin

```bash
cat <<'EOF' | python main.py add-question <survey-id>
{"id":"comentarios","type":"openText","headline":{"default":"Comentarios adicionales"},"required":false,"inputType":"text","longAnswer":true,"placeholder":{"default":"Escribe aquí..."},"buttonLabel":{"default":"Enviar"}}
EOF
```

---

## Interactive TUI (Rich menu)

```bash
python main.py
```

Menu options:
1. List surveys
2. View survey JSON
3. Create survey (interactive — all fields)
4. Add question to survey (interactive — choose type, all fields)
5. Send test response
6. Change survey status
7. Switch environment
8. Exit

The interactive mode prompts for every field — IDs, headlines, subheaders, choices, button labels, back buttons, validation rules, etc.

---

## Web UI

```bash
python main.py serve
# Open http://localhost:8080
```

Browser-based visual builder with:
- Live JSON preview
- Template gallery (one-click add any question type)
- Full question editor with all fields
- Download JSON / Save to API

---

## Project Structure

```
├── main.py                 # CLI entry point
├── client/
│   └── formbricks.py       # API client (v1 + v2)
├── ui/
│   └── tui.py              # Rich TUI components
├── web/
│   ├── app.py              # Flask server
│   ├── static/
│   │   ├── app.js
│   │   └── style.css
│   └── templates/
│       └── index.html
├── config.example.json
└── README.md
```
