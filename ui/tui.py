from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich import box
from typing import Optional
import json, os, sys
from pathlib import Path

console = Console()

def log_error(msg: str, detail: str = ""):
    console.print(f"[red]✖ {msg}[/red]")
    if detail:
        console.print(f"  [dim]{detail}[/dim]")


def log_warn(msg: str):
    console.print(f"[yellow]⚠ {msg}[/yellow]")


def log_ok(msg: str):
    console.print(f"[green]✔ {msg}[/green]")


def validate_json_file(path: str) -> dict | None:
    """Load and validate a JSON file. Returns parsed dict or None on error."""
    try:
        with open(path) as f:
            raw = f.read()
    except FileNotFoundError:
        log_error(f"File not found: {path}")
        return None
    except OSError as e:
        log_error(f"Can't read file", str(e))
        return None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log_error(
            f"Invalid JSON in {os.path.basename(path)}",
            f"Line {e.lineno}, col {e.colno}: {e.msg}"
        )
        # Show context around error
        lines = raw.splitlines()
        start = max(0, e.lineno - 3)
        end = min(len(lines), e.lineno + 2)
        console.print("  [dim]Context:[/dim]")
        for i in range(start, end):
            prefix = "→" if i + 1 == e.lineno else " "
            console.print(f"  {prefix} {i+1:3d} | {lines[i]}")
        return None

    if not isinstance(data, dict):
        log_error("JSON root must be an object ({...})")
        return None

    return data


def show_header(env: dict):
    label = env.get("label") or env.get("name", "")
    env_type = env.get("env_type", "")
    header_text = f"{label} ({env_type})" if env_type else label
    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]Formbricks CLI Manager[/bold cyan]\n"
            f"[yellow]Current env:[/yellow] [green]{header_text}[/green]",
            border_style="blue",
        )
    )
    console.print()


def show_menu() -> int:
    console.print("[bold]MENU[/bold]")
    console.print("  [bold cyan]1.[/bold cyan] List surveys")
    console.print("  [bold cyan]2.[/bold cyan] View survey (raw JSON)")
    console.print("  [bold cyan]3.[/bold cyan] Create survey")
    console.print("  [bold cyan]4.[/bold cyan] Add question to survey")
    console.print("  [bold cyan]5.[/bold cyan] Send test response")
    console.print("  [bold cyan]6.[/bold cyan] Change survey status")
    console.print("  [bold cyan]7.[/bold cyan] Switch environment")
    console.print("  [bold cyan]8.[/bold cyan] Load survey from JSON file")
    console.print("  [bold cyan]9.[/bold cyan] Export survey as JSON file")
    console.print("  [bold cyan]10.[/bold cyan] Exit")
    return IntPrompt.ask("\n[bold]Select option", default=10)


def select_env(envs: list[dict]) -> Optional[dict]:
    table = Table(title="Available Environments", box=box.ROUNDED)
    table.add_column("#", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Base URL", style="blue")
    table.add_column("Env ID")
    for i, env in enumerate(envs, 1):
        label = env.get("label") or env["name"]
        table.add_row(str(i), label, env["base_url"], env["environment_id"])
    console.print(table)
    idx = IntPrompt.ask("[bold]Select environment", default=1)
    if 1 <= idx <= len(envs):
        return envs[idx - 1]
    console.print("[red]Invalid selection[/red]")
    return None


def show_surveys(surveys: list[dict]):
    table = Table(title="Surveys", box=box.ROUNDED)
    table.add_column("#", style="cyan")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Questions")
    table.add_column("Updated")
    for i, s in enumerate(surveys, 1):
        qs = s.get("questions", [])
        if not qs:
            qs = [e for b in s.get("blocks", []) for e in b.get("elements", [])]
        table.add_row(
            str(i),
            s.get("id", ""),
            s.get("name", ""),
            s.get("status", "unknown"),
            str(len(qs)),
            s.get("updatedAt", ""),
        )
    console.print(table)
    return surveys


def show_json(data: dict):
    console.print_json(json.dumps(data, indent=2, default=str))


def _yn(prompt_text: str, default: str = "y") -> bool:
    return Prompt.ask(f"[bold]{prompt_text}[/bold]", choices=["y", "n"], default=default) == "y"


def _i18n_field(label: str) -> dict:
    val = Prompt.ask(f"[bold]{label}[/bold]", default="")
    return {"default": val} if val else None


def prompt_welcome_card() -> dict:
    """Prompt for a welcome card configuration."""
    console.print("\n[bold cyan]── Welcome Card ──[/bold cyan]")
    enabled = _yn("Enable welcome card?", "y")
    if not enabled:
        return {"enabled": False}

    card = {"enabled": True}

    card["headline"] = _i18n_field("Headline")
    card["subheader"] = _i18n_field("Subheader (HTML supported)")
    card["buttonLabel"] = _i18n_field("Button label")
    card["timeToFinish"] = _yn("Show estimated time to finish?")
    card["showResponseCount"] = _yn("Show response count?")

    file_url = Prompt.ask("[bold]Image URL (optional)", default="")
    if file_url:
        card["fileUrl"] = file_url

    return card


def prompt_endings() -> list[dict]:
    """Prompt for survey endings (end screens)."""
    endings = []
    console.print("\n[bold cyan]── Thank You / End Screen ──[/bold cyan]")
    if _yn("Add an ending screen?"):
        ending = {
            "type": "endScreen",
        }
        ending["headline"] = _i18n_field("Headline")
        ending["subheader"] = _i18n_field("Subheader (HTML supported)")
        ending["buttonLabel"] = _i18n_field("Button label (optional)")
        btn_link = Prompt.ask("[bold]Button link URL (optional)", default="")
        if btn_link:
            ending["buttonLink"] = btn_link
        endings.append(ending)
    return endings


def prompt_question() -> dict:
    console.print("\n[bold cyan]── Question ──[/bold cyan]")

    types = [
        "openText",
        "multipleChoiceSingle",
        "multipleChoiceMulti",
        "nps",
        "rating",
        "date",
        "consent",
        "fileUpload",
        "matrix",
    ]
    console.print("[bold]Type:[/bold]")
    for i, t in enumerate(types, 1):
        console.print(f"  {i}. {t}")
    t_idx = IntPrompt.ask("[bold]Select type", default=1)
    q_type = types[t_idx - 1]

    q_id = Prompt.ask("[bold]Question ID (e.g. q1, myQuestion)", default=f"q{t_idx}")
    headline = _i18n_field("Headline")

    q = {
        "id": q_id,
        "type": q_type,
        "headline": headline or {"default": q_id},
        "required": _yn("Required?"),
    }

    subheader = _i18n_field("Subheader / description (HTML supported)")
    if subheader:
        q["subheader"] = subheader

    if q_type == "openText":
        input_types = {"1": "text", "2": "number", "3": "phone", "4": "email"}
        console.print("[bold]Input type:[/bold] 1. text  2. number  3. phone  4. email")
        it = Prompt.ask("[bold]Select", default="1")
        q["inputType"] = input_types.get(it, "text")
        q["longAnswer"] = _yn("Long answer (multi-line)?", "n")
        placeholder = _i18n_field("Placeholder")
        if placeholder:
            q["placeholder"] = placeholder
        q["buttonLabel"] = _i18n_field("Next button label") or {"default": "Next"}
        if _yn("Add back button?"):
            q["backButtonLabel"] = _i18n_field("Back button label") or {"default": "Back"}

    elif q_type in ("multipleChoiceSingle", "multipleChoiceMulti"):
        choices = []
        console.print("[bold]Enter choices (empty line to finish):[/bold]")
        i = 1
        while True:
            label = Prompt.ask(f"  Choice {i}", default="")
            if not label:
                break
            choices.append({"id": f"c{i}", "label": {"default": label}})
            i += 1
        q["choices"] = choices
        q["shuffleOption"] = "none"
        q["buttonLabel"] = _i18n_field("Next button label") or {"default": "Next"}
        if _yn("Add 'Other' option?"):
            q["otherOption"] = True
            q["otherOptionPlaceholder"] = _i18n_field('"Other" placeholder')
        if _yn("Add back button?"):
            q["backButtonLabel"] = _i18n_field("Back button label") or {"default": "Back"}

    elif q_type == "nps":
        q["buttonLabel"] = _i18n_field("Next button label") or {"default": "Next"}
        lower = _i18n_field('Lower label (e.g. "Not likely")')
        upper = _i18n_field('Upper label (e.g. "Extremely likely")')
        if lower:
            q["lowerLabel"] = lower
        if upper:
            q["upperLabel"] = upper

    elif q_type == "rating":
        q["rate"] = IntPrompt.ask("[bold]Max rating (e.g. 5)", default=5)
        q["buttonLabel"] = _i18n_field("Next button label") or {"default": "Next"}
        lower = _i18n_field('Lower label (e.g. "Poor")')
        upper = _i18n_field('Upper label (e.g. "Excellent")')
        if lower:
            q["lowerLabel"] = lower
        if upper:
            q["upperLabel"] = upper

    elif q_type == "date":
        formats = {"1": "d-M-y", "2": "M-d-y", "3": "y-M-d"}
        console.print("[bold]Date format:[/bold] 1. d-M-y  2. M-d-y  3. y-M-d")
        df = Prompt.ask("[bold]Select", default="1")
        q["format"] = formats.get(df, "d-M-y")
        q["buttonLabel"] = _i18n_field("Next button label") or {"default": "Next"}
        if _yn("Add back button?"):
            q["backButtonLabel"] = _i18n_field("Back button label") or {"default": "Back"}

    elif q_type == "consent":
        q["label"] = _i18n_field("Consent checkbox label") or {"default": "I agree"}
        q["buttonLabel"] = _i18n_field("Next button label") or {"default": "Next"}

    elif q_type == "fileUpload":
        q["allowMultipleFiles"] = _yn("Allow multiple files?", "n")
        max_mb = Prompt.ask("[bold]Max file size (MB)", default="10")
        q["maxSizeInMB"] = int(max_mb)
        exts = Prompt.ask("[bold]Allowed extensions (comma-sep, e.g. jpg,png,pdf)", default="jpg,png,pdf")
        if exts:
            q["validation"] = {
                "logic": "and",
                "rules": [
                    {
                        "type": "fileExtensionIs",
                        "params": {"extensions": [e.strip() for e in exts.split(",")]},
                    }
                ],
            }
        q["buttonLabel"] = _i18n_field("Next button label") or {"default": "Next"}
        if _yn("Add back button?"):
            q["backButtonLabel"] = _i18n_field("Back button label") or {"default": "Back"}

    elif q_type == "matrix":
        console.print("[bold]Enter columns (empty line to finish):[/bold]")
        columns = []
        i = 1
        while True:
            label = Prompt.ask(f"  Column {i}", default="")
            if not label:
                break
            columns.append({"id": f"col{i}", "label": {"default": label}})
            i += 1
        console.print("[bold]Enter rows (empty line to finish):[/bold]")
        rows = []
        i = 1
        while True:
            label = Prompt.ask(f"  Row {i}", default="")
            if not label:
                break
            rows.append({"id": f"row{i}", "label": {"default": label}})
            i += 1
        q["columns"] = columns
        q["rows"] = rows
        q["buttonLabel"] = _i18n_field("Next button label") or {"default": "Next"}
        if _yn("Add back button?"):
            q["backButtonLabel"] = _i18n_field("Back button label") or {"default": "Back"}

    return q


def prompt_survey_create() -> dict:
    console.print("\n[bold cyan]═══ Create New Survey ═══[/bold cyan]")

    name = Prompt.ask("[bold]Survey name")
    type_choices = ["link", "app"]
    console.print("[bold]Survey type:[/bold] 1. link  2. app")
    st = Prompt.ask("[bold]Select", default="1")
    survey_type = type_choices[int(st) - 1]

    survey = {
        "name": name,
        "type": survey_type,
        "status": "draft",
        "questions": [],
        "displayOption": "displayOnce",
    }

    card = prompt_welcome_card()
    if card.get("enabled"):
        survey["welcomeCard"] = card
    else:
        survey["welcomeCard"] = {"enabled": False}

    console.print("\n[bold cyan]── Questions ──[/bold cyan]")
    while _yn("Add a question?"):
        survey["questions"].append(prompt_question())

    if _yn("Enable hidden fields?"):
        survey["hiddenFields"] = {"enabled": True, "fieldIds": []}

    survey["thankYouCard"] = {"enabled": False}

    return survey


def prompt_response(survey: dict) -> dict:
    response_data = {}
    questions = survey.get("questions", [])
    if not questions:
        for block in survey.get("blocks", []):
            questions.extend(block.get("elements", []))

    console.print("[bold cyan]── Fill in Responses ──[/bold cyan]")
    for q in questions:
        q_id = q.get("id", "?")
        headline = q.get("headline", {})
        if isinstance(headline, dict):
            headline = headline.get("default", q_id)
        q_type = q.get("type", "openText")

        if q_type == "openText":
            val = Prompt.ask(f"  {headline}")
            response_data[q_id] = val
        elif q_type == "nps":
            val = IntPrompt.ask(f"  {headline} (0-10)", default=5)
            response_data[q_id] = val
        elif q_type == "rating":
            max_rate = q.get("rate", 5)
            val = IntPrompt.ask(f"  {headline} (1-{max_rate})", default=5)
            response_data[q_id] = val
        elif q_type in ("multipleChoiceSingle",):
            choices = q.get("choices", [])
            for i, c in enumerate(choices, 1):
                lbl = c.get("label", {})
                if isinstance(lbl, dict):
                    lbl = lbl.get("default", c.get("id", ""))
                console.print(f"    {i}. {lbl}")
            idx = IntPrompt.ask(f"  {headline}", default=1)
            selected = choices[idx - 1] if 1 <= idx <= len(choices) else choices[0]
            response_data[q_id] = selected.get("id", "")
        elif q_type in ("multipleChoiceMulti",):
            choices = q.get("choices", [])
            for i, c in enumerate(choices, 1):
                lbl = c.get("label", {})
                if isinstance(lbl, dict):
                    lbl = lbl.get("default", c.get("id", ""))
                console.print(f"    {i}. {lbl}")
            picks = Prompt.ask(f"  {headline} (comma-separated numbers)", default="1")
            selected_ids = []
            for p in picks.split(","):
                p = p.strip()
                if p:
                    idx = int(p)
                    if 1 <= idx <= len(choices):
                        selected_ids.append(choices[idx - 1].get("id", ""))
            response_data[q_id] = selected_ids
        elif q_type == "consent":
            val = Prompt.ask(f"  {headline} (type 'yes' to accept)", default="yes")
            response_data[q_id] = val == "yes"
        elif q_type == "date":
            val = Prompt.ask(f"  {headline} (YYYY-MM-DD)")
            response_data[q_id] = val
        elif q_type == "matrix":
            rows = q.get("rows", [])
            cols = q.get("columns", [])
            row_data = {}
            for row in rows:
                lbl = row.get("label", {})
                if isinstance(lbl, dict):
                    lbl = lbl.get("default", row.get("id", ""))
                for i, c in enumerate(cols, 1):
                    clbl = c.get("label", {})
                    if isinstance(clbl, dict):
                        clbl = clbl.get("default", c.get("id", ""))
                    console.print(f"    {i}. {clbl}")
                idx = IntPrompt.ask(f"  {lbl}", default=1)
                selected = cols[idx - 1] if 1 <= idx <= len(cols) else cols[0]
                row_data[row.get("id", "")] = selected.get("id", "")
            response_data[q_id] = row_data
        else:
            val = Prompt.ask(f"  {headline}")
            response_data[q_id] = val

    person_id = Prompt.ask("[bold]Person ID (optional)", default="test-user-cli")
    return {
        "personId": person_id,
        "data": response_data,
    }


def select_survey(surveys: list[dict]) -> Optional[dict]:
    show_surveys(surveys)
    idx = IntPrompt.ask("[bold]Select survey number", default=1)
    if 1 <= idx <= len(surveys):
        return surveys[idx - 1]
    return None


def select_status() -> str:
    statuses = ["draft", "inProgress", "paused", "completed"]
    for i, s in enumerate(statuses, 1):
        console.print(f"  {i}. {s}")
    idx = IntPrompt.ask("[bold]Select new status", default=1)
    return statuses[idx - 1]


def prompt_load_json_file() -> dict | None:
    """Prompt user to load a survey from a JSON file."""
    path = Prompt.ask("[bold]Path to JSON file", default="survey.json")
    data = validate_json_file(path)
    if data is None:
        return None

    log_ok(f"Loaded {os.path.basename(path)}")
    console.print(f"  [dim]Name:[/dim] {data.get('name', '(unnamed)')}")
    console.print(f"  [dim]Questions:[/dim] {len(data.get('questions', []))}")
    console.print(f"  [dim]Status:[/dim] {data.get('status', '(not set)')}")

    return data


def validate_survey_draft(survey: dict, silent: bool = False) -> dict:
    """Ensure a draft survey has required fields. Warns/prompts for missing items.
    When silent=True, auto-fixes without interactive prompts."""
    modified = False
    log_ok("Validating survey structure")

    # Check welcome card
    wc = survey.get("welcomeCard")
    if not wc or not wc.get("enabled"):
        log_warn("Welcome card is missing or disabled")
        if silent:
            survey.setdefault("welcomeCard", {"enabled": False})
            modified = True
        elif survey.get("status") in (None, "draft"):
            console.print("  Surveys in [bold]draft[/bold] status typically have a welcome card.")
            if _yn("Add a welcome card now?", "y"):
                survey["welcomeCard"] = prompt_welcome_card()
                modified = True

    # Ensure thankYouCard exists
    if "thankYouCard" not in survey:
        survey["thankYouCard"] = {"enabled": False}

    # Ensure displayOption exists
    if not survey.get("displayOption"):
        survey["displayOption"] = "displayOnce"
        log_warn("Missing displayOption, set to 'displayOnce'")
        modified = True

    # Validate questions
    questions = survey.get("questions", [])
    for i, q in enumerate(questions):
        if not q.get("id"):
            q["id"] = f"q{i+1}"
            log_warn(f"Question {i+1} missing 'id', set to '{q['id']}'")
            modified = True
        if not q.get("type"):
            q["type"] = "openText"
            log_warn(f"Question {i+1} missing 'type', set to 'openText'")
            modified = True
        if not q.get("headline"):
            q["headline"] = {"default": f"Question {i+1}"}
            log_warn(f"Question {i+1} missing 'headline', using placeholder")
            modified = True

    if modified:
        log_ok("Survey was adjusted — review the JSON before sending")

    return survey
