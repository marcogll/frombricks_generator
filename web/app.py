#!/usr/bin/env python3
import json
import os
import sys

from flask import Flask, jsonify, render_template, request, Response

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.formbricks import FormbricksClient, FormbricksError

app = Flask(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def get_client(env_name=None):
    cfg = load_config()
    envs = cfg.get("environments", [])
    if not envs:
        raise RuntimeError("No environments configured")
    if env_name:
        env = next((e for e in envs if e["name"] == env_name), None)
        if not env:
            raise RuntimeError(f"Environment '{env_name}' not found")
    else:
        env = envs[0]
    return FormbricksClient(env["base_url"], env["api_key"], env["environment_id"]), env


def fix_survey(data: dict) -> dict:
    from ui.tui import validate_survey_draft
    return validate_survey_draft(data, silent=True)

TEMPLATES = {
    "openText": {
        "id": "q1",
        "type": "openText",
        "headline": {"default": "What is your name?"},
        "required": True,
        "inputType": "text",
        "subheader": {"default": "Please enter your full name"},
        "placeholder": {"default": "Type here..."},
        "longAnswer": False,
        "buttonLabel": {"default": "Next"},
        "backButtonLabel": {"default": "Back"},
    },
    "multipleChoiceSingle": {
        "id": "q1",
        "type": "multipleChoiceSingle",
        "headline": {"default": "Choose one option:"},
        "required": True,
        "choices": [
            {"id": "c1", "label": {"default": "Option A"}},
            {"id": "c2", "label": {"default": "Option B"}},
            {"id": "c3", "label": {"default": "Option C"}},
        ],
        "shuffleOption": "none",
        "buttonLabel": {"default": "Next"},
        "backButtonLabel": {"default": "Back"},
    },
    "multipleChoiceMulti": {
        "id": "q1",
        "type": "multipleChoiceMulti",
        "headline": {"default": "Select all that apply:"},
        "required": True,
        "choices": [
            {"id": "c1", "label": {"default": "Option 1"}},
            {"id": "c2", "label": {"default": "Option 2"}},
            {"id": "c3", "label": {"default": "Option 3"}},
        ],
        "shuffleOption": "none",
        "buttonLabel": {"default": "Next"},
    },
    "nps": {
        "id": "q1",
        "type": "nps",
        "headline": {"default": "How likely are you to recommend us?"},
        "required": True,
        "buttonLabel": {"default": "Next"},
        "lowerLabel": {"default": "Not likely at all"},
        "upperLabel": {"default": "Extremely likely"},
    },
    "rating": {
        "id": "q1",
        "type": "rating",
        "headline": {"default": "Rate your experience:"},
        "required": True,
        "rate": 5,
        "buttonLabel": {"default": "Next"},
        "lowerLabel": {"default": "Poor"},
        "upperLabel": {"default": "Excellent"},
    },
    "date": {
        "id": "q1",
        "type": "date",
        "headline": {"default": "Select a date:"},
        "required": True,
        "format": "d-M-y",
        "buttonLabel": {"default": "Next"},
        "backButtonLabel": {"default": "Back"},
    },
    "consent": {
        "id": "q1",
        "type": "consent",
        "headline": {"default": "Do you agree?"},
        "required": True,
        "label": {"default": "I agree to the terms and conditions"},
        "buttonLabel": {"default": "Submit"},
    },
    "fileUpload": {
        "id": "q1",
        "type": "fileUpload",
        "headline": {"default": "Upload your file"},
        "required": True,
        "allowMultipleFiles": False,
        "maxSizeInMB": 10,
        "validation": {
            "logic": "and",
            "rules": [
                {
                    "type": "fileExtensionIs",
                    "params": {"extensions": ["jpg", "png", "pdf"]},
                }
            ],
        },
        "buttonLabel": {"default": "Next"},
    },
    "matrix": {
        "id": "q1",
        "type": "matrix",
        "headline": {"default": "Please rate each category:"},
        "required": True,
        "columns": [
            {"id": "col1", "label": {"default": "Excellent"}},
            {"id": "col2", "label": {"default": "Good"}},
            {"id": "col3", "label": {"default": "Poor"}},
        ],
        "rows": [
            {"id": "row1", "label": {"default": "Quality"}},
            {"id": "row2", "label": {"default": "Service"}},
            {"id": "row3", "label": {"default": "Value"}},
        ],
        "buttonLabel": {"default": "Next"},
    },
}

FULL_SURVEY_TEMPLATE = {
    "name": "My Survey",
    "type": "link",
    "status": "draft",
    "welcomeCard": {
        "enabled": True,
        "headline": {"default": "Welcome!"},
        "subheader": {"default": "<p>Thank you for participating</p>"},
        "buttonLabel": {"default": "Start"},
        "timeToFinish": True,
        "showResponseCount": False,
    },
    "questions": [],
    "endings": [
        {
            "type": "endScreen",
            "headline": {"default": "Thank you!"},
            "subheader": {"default": "<p>Your response has been recorded.</p>"},
            "buttonLabel": {"default": "Close"},
        }
    ],
    "hiddenFields": {"enabled": False, "fieldIds": []},
    "variables": [],
    "displayOption": "displayOnce",
    "singleUse": {"enabled": False, "isEncrypted": True},
    "recaptcha": {"enabled": False, "threshold": 0.1},
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/envs")
def api_envs():
    cfg = load_config()
    return jsonify(cfg.get("environments", []))


@app.route("/api/surveys")
def api_surveys():
    env = request.args.get("env")
    try:
        client, _ = get_client(env)
        surveys = client.list_surveys()
        return jsonify(surveys)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/surveys/<survey_id>")
def api_survey(survey_id):
    env = request.args.get("env")
    try:
        client, _ = get_client(env)
        survey = client.get_survey(survey_id)
        return jsonify(survey)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/surveys", methods=["POST"])
def api_create_survey():
    env = request.args.get("env")
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    try:
        client, env_obj = get_client(env)
        data["environmentId"] = env_obj["environment_id"]
        result = client.create_survey(data)
        return jsonify(result), 201
    except FormbricksError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/surveys/<survey_id>", methods=["PUT"])
def api_update_survey(survey_id):
    env = request.args.get("env")
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    try:
        client, _ = get_client(env)
        result = client.update_survey(survey_id, data)
        return jsonify(result)
    except FormbricksError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/templates")
def api_templates():
    type_filter = request.args.get("type")
    if type_filter:
        tpl = TEMPLATES.get(type_filter)
        if not tpl:
            return jsonify({"error": f"Unknown type: {type_filter}"}), 404
        return jsonify(tpl)
    return jsonify(TEMPLATES)


@app.route("/api/templates/full-survey")
def api_full_survey_template():
    return jsonify(FULL_SURVEY_TEMPLATE)


SURVEY_DOCS_MD = """# Formbricks Survey Structure

## Top-level fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Survey name |
| `type` | `"link"` / `"app"` | ✅ | Distribution type |
| `status` | `"draft"` / `"inProgress"` / `"paused"` / `"completed"` | ✅ | Survey state |
| `environmentId` | string | ✅ | Injected automatically by the tool |
| `questions` | array | ✅ | List of question objects |
| `welcomeCard` | object | ❌ | Welcome screen before questions |
| `endings` | array | ❌ | Ending screens (add via PUT) |
| `displayOption` | string | ❌ | `displayOnce`, `displayMultiple`, `respondOnce` |
| `hiddenFields` | object | ❌ | `{ enabled, fieldIds }` |
| `variables` | array | ❌ | Survey variables for logic |
| `singleUse` | object | ❌ | `{ enabled, isEncrypted }` |
| `recaptcha` | object | ❌ | `{ enabled, threshold }` |

---

## Welcome Card

```json
{
  "enabled": true,
  "headline": { "default": "Welcome!" },
  "subheader": { "default": "<p>Description</p>" },
  "buttonLabel": { "default": "Start" },
  "fileUrl": "https://...",
  "timeToFinish": true,
  "showResponseCount": false
}
```

---

## Question Types

### openText

Free text input. Supports single-line and multi-line.

```json
{
  "id": "q1",
  "type": "openText",
  "headline": { "default": "Question text" },
  "required": true,
  "inputType": "text",
  "subheader": { "default": "Helper text" },
  "placeholder": { "default": "Type here..." },
  "longAnswer": false,
  "charLimit": { "enabled": false },
  "buttonLabel": { "default": "Next" },
  "backButtonLabel": { "default": "Back" }
}
```

| Field | Values |
|-------|--------|
| `inputType` | `text`, `number`, `phone`, `email` |
| `longAnswer` | `true` = textarea, `false` = single line |

---

### multipleChoiceSingle

Single selection from a list (radio buttons).

```json
{
  "id": "q2",
  "type": "multipleChoiceSingle",
  "headline": { "default": "Choose one:" },
  "required": true,
  "choices": [
    { "id": "c1", "label": { "default": "Option A" } },
    { "id": "c2", "label": { "default": "Option B" } }
  ],
  "shuffleOption": "none",
  "buttonLabel": { "default": "Next" },
  "backButtonLabel": { "default": "Back" }
}
```

Extra fields: `otherOption` (boolean), `otherOptionPlaceholder` (`{ default }`), `displayType` (`"list"` / `"dropdown"`).

---

### multipleChoiceMulti

Multiple selection from a list (checkboxes).

```json
{
  "id": "q3",
  "type": "multipleChoiceMulti",
  "headline": { "default": "Select all:" },
  "required": true,
  "choices": [
    { "id": "c1", "label": { "default": "Option 1" } },
    { "id": "c2", "label": { "default": "Option 2" } }
  ],
  "shuffleOption": "none",
  "buttonLabel": { "default": "Next" }
}
```

---

### nps (Net Promoter Score)

0–10 scale question.

```json
{
  "id": "q4",
  "type": "nps",
  "headline": { "default": "How likely to recommend?" },
  "required": true,
  "buttonLabel": { "default": "Next" },
  "lowerLabel": { "default": "Not likely" },
  "upperLabel": { "default": "Extremely likely" }
}
```

---

### rating

Star / number rating on a configurable scale.

```json
{
  "id": "q5",
  "type": "rating",
  "headline": { "default": "Rate your experience" },
  "required": true,
  "rate": 5,
  "buttonLabel": { "default": "Next" },
  "lowerLabel": { "default": "Poor" },
  "upperLabel": { "default": "Excellent" }
}
```

`rate`: max value (2–10). Lower/upper labels are optional.

---

### date

Date picker question.

```json
{
  "id": "q6",
  "type": "date",
  "headline": { "default": "Select date" },
  "required": true,
  "format": "d-M-y",
  "buttonLabel": { "default": "Next" },
  "backButtonLabel": { "default": "Back" }
}
```

Formats: `d-M-y` (7-May-2026), `M-d-y` (May-7-2026), `y-M-d` (2026-May-7).

---

### consent

Checkbox consent question.

```json
{
  "id": "q7",
  "type": "consent",
  "headline": { "default": "Do you agree?" },
  "required": true,
  "label": { "default": "I agree to the terms" },
  "subheader": { "default": "<p>Description</p>" },
  "buttonLabel": { "default": "Submit" }
}
```

---

### fileUpload

File upload question with validation.

```json
{
  "id": "q8",
  "type": "fileUpload",
  "headline": { "default": "Upload a file" },
  "required": true,
  "allowMultipleFiles": false,
  "maxSizeInMB": 10,
  "validation": {
    "logic": "and",
    "rules": [
      {
        "type": "fileExtensionIs",
        "params": { "extensions": ["jpg", "png", "pdf"] }
      }
    ]
  },
  "buttonLabel": { "default": "Next" },
  "backButtonLabel": { "default": "Back" }
}
```

---

### matrix

Grid with rows and columns (radio button per row).

```json
{
  "id": "q9",
  "type": "matrix",
  "headline": { "default": "Rate each category" },
  "required": true,
  "columns": [
    { "id": "col1", "label": { "default": "Excellent" } },
    { "id": "col2", "label": { "default": "Good" } },
    { "id": "col3", "label": { "default": "Poor" } }
  ],
  "rows": [
    { "id": "row1", "label": { "default": "Quality" } },
    { "id": "row2", "label": { "default": "Service" } }
  ],
  "buttonLabel": { "default": "Next" }
}
```

---

## Endings (End Screen)

```json
{
  "type": "endScreen",
  "headline": { "default": "Thank you!" },
  "subheader": { "default": "<p>Your response was saved.</p>" },
  "buttonLabel": { "default": "Close" },
  "buttonLink": "https://example.com"
}
```

---

## Minimal Complete Example

```json
{
  "name": "Customer Feedback",
  "type": "link",
  "status": "draft",
  "welcomeCard": {
    "enabled": true,
    "headline": { "default": "Welcome!" },
    "buttonLabel": { "default": "Start" }
  },
  "questions": [
    {
      "id": "q1",
      "type": "openText",
      "headline": { "default": "Your name?" },
      "required": true,
      "inputType": "text",
      "buttonLabel": { "default": "Next" }
    },
    {
      "id": "q2",
      "type": "nps",
      "headline": { "default": "Recommend us?" },
      "required": true,
      "buttonLabel": { "default": "Submit" }
    }
  ],
  "displayOption": "displayOnce"
}
```

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/management/surveys` | List surveys |
| GET | `/api/v1/management/surveys/:id` | Get survey |
| POST | `/api/v1/management/surveys` | Create survey |
| PUT | `/api/v1/management/surveys/:id` | Update survey |
| POST | `/api/v2/management/responses` | Create response |
| GET | `/api/v1/management/responses?surveyId=` | List responses |

Auth: `x-api-key` header.
"""


@app.route("/api/templates/docs/survey-structure")
def api_survey_docs():
    fmt = request.args.get("format", "md")
    if fmt == "md":
        return SURVEY_DOCS_MD, 200, {"Content-Type": "text/markdown"}
    return jsonify({"markdown": SURVEY_DOCS_MD})


@app.route("/api/responses/<survey_id>", methods=["POST"])
def api_send_response(survey_id):
    env = request.args.get("env")
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    try:
        client, _ = get_client(env)
        result = client.send_response(
            survey_id=survey_id,
            data=data.get("data", data),
            finished=data.get("finished", True),
            person_id=data.get("personId"),
        )
        return jsonify(result), 201
    except FormbricksError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/fix-survey", methods=["POST"])
def api_fix_survey():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    try:
        from ui.tui import validate_survey_draft
        fixed = validate_survey_draft(data, silent=True)
        return jsonify(fixed)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/eval/template/<survey_id>")
def api_eval_template(survey_id):
    env = request.args.get("env")
    try:
        client, _ = get_client(env)
        survey = client.get_survey(survey_id)
        questions = survey.get("questions", [])
        if not questions:
            for block in survey.get("blocks", []):
                questions.extend(block.get("elements", []))
        template = {}
        for q in questions:
            qid = q.get("id", "")
            if not qid:
                continue
            qtype = q.get("type", "openText")
            entry = {"correct": None, "points": 1, "explanation": ""}
            choices = q.get("choices", [])
            if choices:
                entry["choices"] = {c["id"]: (c.get("label", {}) or {}).get("default", c["id"]) for c in choices}
            if qtype in ("multipleChoiceSingle",):
                entry["correct"] = choices[0]["id"] if choices else None
            elif qtype in ("multipleChoiceMulti",):
                entry["correct"] = [choices[0]["id"]] if choices else []
            elif qtype in ("openText",):
                entry["type"] = "review"
            template[qid] = entry
        return jsonify(template)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/eval/grade/<survey_id>", methods=["POST"])
def api_eval_grade(survey_id):
    env = request.args.get("env")
    fmt = request.args.get("format", "json")
    body = request.get_json()
    if not body or "answer_key" not in body:
        return jsonify({"error": "answer_key required in body"}), 400
    try:
        from eval.grader import load_answer_key, grade_all, export_csv, export_json
        client, _ = get_client(env)
        answer_key = body["answer_key"]
        responses = client.get_responses(survey_id)
        results = grade_all(responses, answer_key)
        if fmt == "csv":
            survey = client.get_survey(survey_id)
            out = export_csv(results, survey.get("name", "evaluation"))
            return Response(out, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=evaluation.csv"})
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/eval/export/<survey_id>")
def api_eval_export(survey_id):
    env = request.args.get("env")
    try:
        import csv, io
        client, _ = get_client(env)
        responses = client.get_responses(survey_id)
        all_keys = set()
        for r in responses:
            data = r.get("data", {})
            if isinstance(data, dict) and "data" in data:
                data = data["data"]
            all_keys.update(data.keys())
        sorted_keys = sorted(all_keys)
        fieldnames = ["response_id", "person_id"] + sorted_keys
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        for r in responses:
            data = r.get("data", {})
            if isinstance(data, dict) and "data" in data:
                data = data["data"]
            row = {"response_id": r.get("id", ""), "person_id": r.get("personId", "") or (r.get("person", {}) or {}).get("id", "")}
            row.update({k: data.get(k, "") for k in sorted_keys})
            writer.writerow(row)
        return Response(buf.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=responses.csv"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def main():
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print(f"Web UI at http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
