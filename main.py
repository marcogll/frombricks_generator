#!/usr/bin/env python3
import argparse
import json
import os
import sys
import shutil
from rich.prompt import Prompt

from client.formbricks import FormbricksClient, FormbricksError
from ui.tui import (
    console,
    show_header,
    show_menu,
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


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        alt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        if os.path.exists(alt):
            path = alt
        else:
            console.print(f"[red]Config file not found: {path}[/red]")
            console.print("[yellow]Copy config.example.json to config.json and edit it[/yellow]")
            sys.exit(1)
    with open(path) as f:
        return json.load(f)


def get_client(config: dict, env_name: str = None) -> tuple:
    envs = config.get("environments", [])
    if not envs:
        console.print("[red]No environments configured[/red]")
        sys.exit(1)
    if env_name:
        env = next((e for e in envs if e["name"] == env_name), None)
        if not env:
            console.print(f"[red]Environment '{env_name}' not found[/red]")
            sys.exit(1)
    else:
        env = envs[0]
    client = FormbricksClient(
        env["base_url"], env["api_key"], env["environment_id"]
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


# ---- Interactive mode ----

def interactive_mode(config):
    envs = config.get("environments", [])
    if not envs:
        console.print("[red]No environments configured[/red]")
        return

    current_env = envs[0]
    client = FormbricksClient(
        current_env["base_url"],
        current_env["api_key"],
        current_env["environment_id"],
    )

    while True:
        show_header(current_env["name"])
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
                        sel["environment_id"],
                    )
            elif choice == 8:
                data = prompt_load_json_file()
                if data:
                    data["environmentId"] = current_env["environment_id"]
                    data = validate_survey_draft(data)
                    show_json(data)
                    if Prompt.ask("[bold]Send to API?", choices=["y", "n"], default="n") == "y":
                        result = client.create_survey(data)
                        log_ok("Survey created from file!")
                        show_json(result)
            elif choice == 9:
                console.print("[cyan]Goodbye![/cyan]")
                break
        except FormbricksError as e:
            log_error("API request failed", str(e))

        if choice != 9:
            Prompt.ask("\n[dim]Press Enter to continue...[/dim]", default="")


def main():
    parser = argparse.ArgumentParser(
        description="Formbricks CLI Manager - TUI & headless mode"
    )
    parser.add_argument(
        "--config", "-c", default="config.json", help="Config file path"
    )
    parser.add_argument("--env", "-e", default=None, help="Environment name")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("interactive", help="Run in interactive TUI mode")

    sub.add_parser("list", help="List surveys")

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

    p_responses = sub.add_parser("responses", help="List responses for a survey")
    p_responses.add_argument("survey_id")

    p_serve = sub.add_parser("serve", help="Start Web UI (Flask server)")

    args = parser.parse_args()
    config = load_config(args.config)

    if not args.command or args.command == "interactive":
        interactive_mode(config)
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
        elif args.command == "set-status":
            cmd_set_status(client, env, args.survey_id, args.status)
        elif args.command == "responses":
            responses = client.get_responses(args.survey_id)
            show_json({"data": responses})
        elif args.command == "serve":
            # Kill any existing Flask on the same port
            import subprocess
            try:
                subprocess.run(["pkill", "-f", "python web/app.py"], capture_output=True)
            except Exception:
                pass
            from web.app import main as web_main
            web_main()
    except FormbricksError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
