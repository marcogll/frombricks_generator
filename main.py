#!/usr/bin/env python3
import argparse
import json
import os
import sys
import shutil
import csv
import io
from rich.prompt import Prompt

from client.formbricks import FormbricksClient, FormbricksError
import shared.config as shconfig
from shared.config import load_config, save_config, env_defaults, ensure_config, validate_config
from ui.tui import (
    console,
    show_header,
    show_menu,
    manage_environments_menu,
    select_env,
    show_surveys,
    show_json,
    prompt_survey_create,
    prompt_question,
    prompt_response,
    select_survey,
    select_status,
    prompt_load_json_file,
    validate_survey_draft,
    log_error,
    log_ok,
    log_warn,
)


def get_client(config: dict, env_name: str = None) -> tuple:
    envs = config.get("environments", [])
    if not envs:
        console.print("[red]No environments configured[/red]")
        console.print("[yellow]Use: python main.py manage-envs[/yellow]")
        console.print("[yellow]Or set FORMBRICKS_BASE_URL + FORMBRICKS_API_KEY in .env[/yellow]")
        sys.exit(1)
    if env_name:
        env = next((e for e in envs if e["name"] == env_name), None)
        if not env:
            console.print(f"[red]Environment '{env_name}' not found[/red]")
            sys.exit(1)
    else:
        env = envs[0]
    client = FormbricksClient(
        env["base_url"], env["api_key"], env.get("environment_id", "")
    )
    return client, env


# ---- Headless commands ----

def cmd_list(client, env):
    surveys = client.list_surveys()
    show_surveys(surveys)


def cmd_view(client, env, survey_id):
    survey = client.get_survey(survey_id)
    show_json(survey)


def cmd_create_interactive(client, env):
    data = prompt_survey_create()
    data["environmentId"] = env["environment_id"]
    data = validate_survey_draft(data)
    console.print("[yellow]JSON to send:[/yellow]")
    show_json(data)
    if Prompt.ask("[bold]Send?", choices=["y", "n"], default="y") == "y":
        result = client.create_survey(data)
        log_ok("Survey created!")
        show_json(result)


def cmd_create_stdin(client, env):
    raw = sys.stdin.read()
    try:
        data = FormbricksClient.validate_json(raw)
    except FormbricksError as e:
        log_error("Invalid JSON input", str(e))
        sys.exit(1)
    data.setdefault("environmentId", env["environment_id"])
    if "name" not in data:
        log_error("JSON must include a 'name' field")
        sys.exit(1)
    data = validate_survey_draft(data)
    result = client.create_survey(data)
    log_ok("Survey created!")
    show_json(result)


def cmd_add_question(client, env, survey_id):
    survey = client.get_survey(survey_id)
    q = prompt_question()
    questions = survey.get("questions", [])
    questions.append(q)
    client.update_survey(survey_id, {"questions": questions})
    console.print("[green]Question added![/green]")


def cmd_send_response_interactive(client, env, survey_id=None):
    if survey_id:
        survey = client.get_survey(survey_id)
    else:
        surveys = client.list_surveys()
        survey = select_survey(surveys)
        if not survey:
            return
        survey_id = survey["id"]
    survey = client.get_survey(survey_id)
    result = prompt_response(survey)
    body = {
        "surveyId": survey_id,
        "data": result["data"],
        "finished": True,
    }
    if result.get("personId"):
        body["personId"] = result["personId"]
    console.print("[yellow]Response JSON:[/yellow]")
    show_json(body)
    if Prompt.ask("[bold]Send?", choices=["y", "n"], default="y") == "y":
        resp = client.send_response(
            survey_id=survey_id,
            data=result["data"],
            finished=True,
            person_id=result.get("personId"),
        )
        console.print("[green]Response sent![/green]")
        show_json(resp)


def cmd_send_response_stdin(client, env, survey_id):
    raw = sys.stdin.read()
    data = FormbricksClient.validate_json(raw)
    resp = client.send_response(
        survey_id=survey_id,
        data=data.get("data", data),
        finished=data.get("finished", True),
        person_id=data.get("personId"),
    )
    console.print("[green]Response sent![/green]")
    show_json(resp)


def cmd_set_status(client, env, survey_id, status):
    if status not in ("draft", "inProgress", "paused", "completed"):
        console.print("[red]Invalid status. Use: draft, inProgress, paused, completed[/red]")
        sys.exit(1)
    client.update_survey(survey_id, {"status": status})
    console.print(f"[green]Status set to '{status}'[/green]")


def cmd_export_survey(client, env, survey_id, output):
    survey = client.get_survey(survey_id)
    if not output:
        name = survey.get("name", "survey").replace(" ", "_")
        output = f"{name}.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(survey, f, indent=2, ensure_ascii=False)
    log_ok(f"Survey exported to {output}")


# ---- Evaluation commands ----

def cmd_eval_template(client, env, survey_id, output):
    from eval.grader import load_answer_key, grade_response
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
        if qtype in ("multipleChoiceSingle",):
            choices = q.get("choices", [])
            entry["correct"] = choices[0]["id"] if choices else None
            entry["choices"] = {c["id"]: (c.get("label", {}) or {}).get("default", c["id"]) for c in choices}
        elif qtype in ("multipleChoiceMulti",):
            choices = q.get("choices", [])
            entry["correct"] = [choices[0]["id"]] if choices else []
            entry["choices"] = {c["id"]: (c.get("label", {}) or {}).get("default", c["id"]) for c in choices}
        elif qtype in ("nps", "rating"):
            entry["correct"] = None
        else:
            entry["type"] = "review"
            entry["correct"] = None
        template[qid] = entry
    with open(output, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    log_ok(f"Template saved to {output}")
    console.print(f"  Questions: {len(template)}")
    show_json(template)


def cmd_eval_grade(client, env, survey_id, answer_key_path, fmt, output):
    from eval.grader import load_answer_key, grade_all, export_csv, export_json
    log_ok("Loading answer key")
    answer_key = load_answer_key(answer_key_path)
    log_ok(f"Fetching responses for survey {survey_id}")
    responses = client.get_responses(survey_id)
    log_ok(f"Grading {len(responses)} responses")
    results = grade_all(responses, answer_key)
    if fmt == "csv":
        survey = client.get_survey(survey_id)
        out = export_csv(results, survey.get("name", "evaluation"))
    else:
        out = export_json(results)
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(out)
        log_ok(f"Results saved to {output}")
    else:
        console.print(out)


def cmd_eval_export(client, env, survey_id, output):
    import csv, io
    log_ok(f"Fetching responses for survey {survey_id}")
    responses = client.get_responses(survey_id)
    log_ok(f"Exporting {len(responses)} responses")
    if not responses:
        log_error("No responses found")
        return
    # Build CSV from raw response data
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
    out = buf.getvalue()
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(out)
        log_ok(f"Exported to {output}")
    else:
        console.print(out)


# ---- Environment management ----

def cmd_list_envs(config):
    envs = config.get("environments", [])
    if not envs:
        log_warn("No environments configured")
        return
    table_data = []
    for env in envs:
        url = env.get("base_url", "")
        eid = env.get("environment_id", "")
        label = env.get("label") or env.get("name", "")
        env_type = env.get("env_type", "")
        group = env.get("group", "")
        table_data.append({"name": env["name"], "label": label,
                           "type": env_type, "group": group,
                           "url": url, "env_id": eid})
    show_envs_table(table_data)


def show_envs_table(envs: list[dict]):
    from rich.table import Table
    from rich import box
    table = Table(title="Environments", box=box.ROUNDED)
    table.add_column("Name", style="cyan")
    table.add_column("Label")
    table.add_column("Type", style="yellow")
    table.add_column("Group")
    table.add_column("Base URL", style="blue")
    table.add_column("Env ID")
    for e in envs:
        table.add_row(e["name"], e["label"], e["type"],
                      e["group"], e["url"], e["env_id"])
    console.print(table)


def cmd_add_env(config, config_path):
    from ui.tui import prompt_env_config
    env = prompt_env_config()
    if env:
        config["environments"].append(env)
        save_config(config, config_path)
        log_ok(f"Environment '{env['name']}' added")


def cmd_edit_env(config, config_path, env_name):
    envs = config.get("environments", [])
    env = next((e for e in envs if e["name"] == env_name), None)
    if not env:
        log_error(f"Environment '{env_name}' not found")
        return
    from ui.tui import prompt_env_config
    updated = prompt_env_config(existing=env)
    if updated:
        env.update(updated)
        save_config(config, config_path)
        log_ok(f"Environment '{env_name}' updated")


def cmd_delete_env(config, config_path, env_name):
    envs = config.get("environments", [])
    env = next((e for e in envs if e["name"] == env_name), None)
    if not env:
        log_error(f"Environment '{env_name}' not found")
        return
    label = env.get("label") or env["name"]
    if Prompt.ask(f"[bold red]Delete '{label}'?[/bold red]", choices=["y", "n"], default="n") != "y":
        return
    config["environments"] = [e for e in envs if e["name"] != env_name]
    save_config(config, config_path)
    log_ok(f"Environment '{label}' deleted")


def cmd_discover(config, config_path):
    defaults = env_defaults()
    base_url = defaults.get("base_url") or Prompt.ask("[bold]Formbricks base URL")
    api_key = defaults.get("api_key") or Prompt.ask("[bold]API key")
    if not base_url or not api_key:
        log_error("Base URL and API key are required")
        return
    log_ok(f"Connecting to {base_url}...")
    discovered = FormbricksClient.discover_environments(base_url, api_key)
    if not discovered:
        log_error("Could not connect or no environments found")
        log_warn("Add environments manually with: python main.py manage-envs")
        return
    existing_names = {e["name"] for e in config.get("environments", [])}
    added = 0
    for env in discovered:
        name = env.get("name", "default")
        if name in existing_names:
            log_warn(f"Environment '{name}' already exists, skipping")
            continue
        env.setdefault("label", name.capitalize())
        env.setdefault("env_type", "prod")
        env.setdefault("group", "Default")
        config.setdefault("environments", []).append(env)
        added += 1
    if added:
        save_config(config, config_path)
        log_ok(f"Discovered and added {added} environment(s)")
    else:
        log_warn("No new environments to add")


# ---- Interactive mode ----

def interactive_mode(config, config_path):
    envs = config.get("environments", [])
    if not envs:
        console.print("[red]No environments configured[/red]")
        console.print("[yellow]Options:[/yellow]")
        console.print("  1. Auto-discover from API key")
        console.print("  2. Add environment manually")
        console.print("  3. Exit")
        choice = Prompt.ask("[bold]Choose", choices=["1", "2", "3"], default="1")
        if choice == "1":
            cmd_discover(config, config_path)
            return interactive_mode(load_config(config_path), config_path)
        elif choice == "2":
            cmd_add_env(config, config_path)
            return interactive_mode(load_config(config_path), config_path)
        return

    current_env = envs[0]
    client = FormbricksClient(
        current_env["base_url"],
        current_env["api_key"],
        current_env.get("environment_id", ""),
    )

    while True:
        show_header(current_env)
        choice = show_menu()

        try:
            if choice == 1:
                cmd_list(client, current_env)
            elif choice == 2:
                surveys = client.list_surveys()
                s = select_survey(surveys)
                if s:
                    full = client.get_survey(s["id"])
                    show_json(full)
            elif choice == 3:
                cmd_create_interactive(client, current_env)
            elif choice == 4:
                surveys = client.list_surveys()
                s = select_survey(surveys)
                if s:
                    cmd_add_question(client, current_env, s["id"])
            elif choice == 5:
                cmd_send_response_interactive(client, current_env)
            elif choice == 6:
                surveys = client.list_surveys()
                s = select_survey(surveys)
                if s:
                    status = select_status()
                    client.update_survey(s["id"], {"status": status})
                    log_ok(f"Survey '{s['name']}' status set to '{status}'")
            elif choice == 7:
                sel = select_env(envs)
                if sel:
                    current_env = sel
                    client = FormbricksClient(
                        sel["base_url"],
                        sel["api_key"],
                        sel.get("environment_id", ""),
                    )
            elif choice == 8:
                data = prompt_load_json_file()
                if data:
                    data["environmentId"] = current_env.get("environment_id", "")
                    data = validate_survey_draft(data)
                    show_json(data)
                    if Prompt.ask("[bold]Send to API?", choices=["y", "n"], default="n") == "y":
                        result = client.create_survey(data)
                        log_ok("Survey created from file!")
                        show_json(result)
            elif choice == 9:
                surveys = client.list_surveys()
                s = select_survey(surveys)
                if s:
                    output = Prompt.ask("[bold]Output file", default=f"{s['name'].replace(' ', '_')}.json")
                    cmd_export_survey(client, current_env, s["id"], output)
            elif choice == 10:
                result = manage_environments_menu(config, config_path)
                if result == "reload":
                    config = load_config(config_path)
                    envs = config.get("environments", [])
                    if current_env and not any(e["name"] == current_env["name"] for e in envs):
                        current_env = envs[0] if envs else None
                        if current_env:
                            client = FormbricksClient(
                                current_env["base_url"],
                                current_env["api_key"],
                                current_env.get("environment_id", ""),
                            )
            elif choice == 11:
                console.print("[cyan]Goodbye![/cyan]")
                break
        except FormbricksError as e:
            log_error("API request failed", str(e))

        if choice != 11:
            Prompt.ask("\n[dim]Press Enter to continue...[/dim]", default="")


def main():
    parser = argparse.ArgumentParser(
        description="Formbricks Studio - Survey manager for Formbricks"
    )
    parser.add_argument(
        "--config", "-c", default=None, help="Config file path (default: auto-detect)"
    )
    parser.add_argument("--env", "-e", default=None, help="Environment name")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("interactive", help="Run in interactive TUI mode")

    sub.add_parser("list", help="List surveys")

    sub.add_parser("list-envs", help="List configured environments")

    p_discover = sub.add_parser("discover", help="Auto-discover environments from API")
    p_discover.add_argument("--url", help="Formbricks base URL")
    p_discover.add_argument("--api-key", help="Formbricks API key")

    sub_me = sub.add_parser("manage-envs", help="Manage environments")
    me_sub = sub_me.add_subparsers(dest="me_command")
    me_sub.add_parser("list", help="List environments")
    me_sub.add_parser("add", help="Add environment (interactive)")
    p_me_edit = me_sub.add_parser("edit", help="Edit environment")
    p_me_edit.add_argument("env_name")
    p_me_delete = me_sub.add_parser("delete", help="Delete environment")
    p_me_delete.add_argument("env_name")

    p_view = sub.add_parser("view", help="View survey raw JSON")
    p_view.add_argument("survey_id")

    p_create = sub.add_parser("create", help="Create survey (reads JSON from stdin)")
    p_create.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    p_add = sub.add_parser("add-question", help="Add question to survey (interactive)")
    p_add.add_argument("survey_id")

    p_resp = sub.add_parser("send-response", help="Send test response")
    p_resp.add_argument("survey_id", nargs="?", help="Survey ID (omit for interactive pick)")
    p_resp.add_argument("--data", "-d", help="JSON response data (omit for interactive fill)")

    p_status = sub.add_parser("set-status", help="Change survey status")
    p_status.add_argument("survey_id")
    p_status.add_argument("status", choices=["draft", "inProgress", "paused", "completed"])

    p_export = sub.add_parser("export", help="Export survey as JSON file")
    p_export.add_argument("survey_id")
    p_export.add_argument("--output", "-o", help="Output JSON file path")

    p_responses = sub.add_parser("responses", help="List responses for a survey")
    p_responses.add_argument("survey_id")

    p_serve = sub.add_parser("serve", help="Start Web UI (Flask server)")

    # Evaluation subcommands
    p_eval = sub.add_parser("eval", help="Evaluation commands")
    eval_sub = p_eval.add_subparsers(dest="eval_command")

    p_et = eval_sub.add_parser("template", help="Generate answer key template from survey")
    p_et.add_argument("survey_id")
    p_et.add_argument("--output", "-o", default="answer_key.json")

    p_eg = eval_sub.add_parser("grade", help="Grade responses against answer key")
    p_eg.add_argument("survey_id")
    p_eg.add_argument("answer_key")
    p_eg.add_argument("--format", choices=["json", "csv"], default="json")
    p_eg.add_argument("--output", "-o", help="Output file")

    p_ee = eval_sub.add_parser("export", help="Export responses as CSV")
    p_ee.add_argument("survey_id")
    p_ee.add_argument("--output", "-o", help="Output CSV file")

    args = parser.parse_args()
    config_path = args.config
    config_path_used = config_path or shconfig.find_config()

    if args.command != "serve":
        config_path_used = ensure_config(config_path)

    config = load_config(config_path_used)

    warnings = validate_config(config)
    for w in warnings:
        log_warn(w)

    if not args.command or args.command == "interactive":
        interactive_mode(config, config_path_used)
        return

    if args.command == "list-envs":
        cmd_list_envs(config)
        return

    if args.command == "manage-envs":
        if not args.me_command or args.me_command == "list":
            cmd_list_envs(config)
        elif args.me_command == "add":
            cmd_add_env(config, config_path_used)
        elif args.me_command == "edit":
            cmd_edit_env(config, config_path_used, args.env_name)
        elif args.me_command == "delete":
            cmd_delete_env(config, config_path_used, args.env_name)
        return

    if args.command == "discover":
        if args.url:
            os.environ["FORMBRICKS_BASE_URL"] = args.url
        if args.api_key:
            os.environ["FORMBRICKS_API_KEY"] = args.api_key
        cmd_discover(config, config_path_used)
        return

    client, env = get_client(config, args.env)

    try:
        if args.command == "list":
            cmd_list(client, env)
        elif args.command == "view":
            cmd_view(client, env, args.survey_id)
        elif args.command == "create":
            if args.interactive:
                cmd_create_interactive(client, env)
            else:
                cmd_create_stdin(client, env)
        elif args.command == "add-question":
            cmd_add_question(client, env, args.survey_id)
        elif args.command == "send-response":
            if not sys.stdin.isatty():
                raw = sys.stdin.read()
                data = FormbricksClient.validate_json(raw)
                sid = args.survey_id or data.get("surveyId")
                if not sid:
                    console.print("[red]surveyId required (pass as arg or in JSON)[/red]")
                    sys.exit(1)
                resp = client.send_response(
                    survey_id=sid,
                    data=data.get("data", data),
                    finished=data.get("finished", True),
                    person_id=data.get("personId"),
                )
                console.print("[green]Response sent![/green]")
                show_json(resp)
            elif args.survey_id:
                cmd_send_response_interactive(client, env, args.survey_id)
            else:
                cmd_send_response_interactive(client, env)
        elif args.command == "export":
            cmd_export_survey(client, env, args.survey_id, args.output)
        elif args.command == "set-status":
            cmd_set_status(client, env, args.survey_id, args.status)
        elif args.command == "responses":
            responses = client.get_responses(args.survey_id)
            show_json({"data": responses})
        elif args.command == "serve":
            import subprocess
            try:
                subprocess.run(["pkill", "-f", "python web/app.py"], capture_output=True)
            except Exception:
                pass
            from web.app import main as web_main
            web_main()
        elif args.command == "eval":
            if args.eval_command == "template":
                cmd_eval_template(client, env, args.survey_id, args.output)
            elif args.eval_command == "grade":
                cmd_eval_grade(client, env, args.survey_id, args.answer_key, args.format, args.output)
            elif args.eval_command == "export":
                cmd_eval_export(client, env, args.survey_id, args.output)
            else:
                console.print("[red]Usage: eval {template|grade|export}[/red]")
    except FormbricksError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
