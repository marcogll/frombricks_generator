import json
import requests
from typing import Any, Optional


class FormbricksError(Exception):
    pass


class FormbricksClient:
    def __init__(self, base_url: str, api_key: str, environment_id: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.environment_id = environment_id
        self.session = requests.Session()
        self.session.headers.update({
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs) -> Any:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.request(method, url, **kwargs)
            resp.raise_for_status()
        except requests.HTTPError as e:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text[:500]
            raise FormbricksError(
                f"API {resp.status_code} {e}: {detail}"
            ) from e
        if resp.status_code == 204:
            return None
        body = resp.json()
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body

    def _request_raw(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{self.base_url}{path}"
        return self.session.request(method, url, **kwargs)

    def list_surveys(self) -> list[dict]:
        return self._request("GET", "/api/v1/management/surveys")

    def get_survey(self, survey_id: str) -> dict:
        return self._request("GET", f"/api/v1/management/surveys/{survey_id}")

    def create_survey(self, data: dict) -> dict:
        return self._request("POST", "/api/v1/management/surveys", json=data)

    def update_survey(self, survey_id: str, data: dict) -> dict:
        return self._request(
            "PUT", f"/api/v1/management/surveys/{survey_id}", json=data
        )

    def delete_survey(self, survey_id: str) -> None:
        self._request("DELETE", f"/api/v1/management/surveys/{survey_id}")

    def send_response(self, survey_id: str, data: dict, finished: bool = True, person_id: Optional[str] = None) -> dict:
        body = {
            "surveyId": survey_id,
            "data": data,
            "finished": finished,
        }
        if person_id:
            body["personId"] = person_id
        return self._request("POST", "/api/v2/management/responses", json=body)

    def get_responses(self, survey_id: str) -> list[dict]:
        return self._request(
            "GET", f"/api/v1/management/responses?surveyId={survey_id}"
        )

    def list_environments(self) -> list[dict]:
        resp = self._request_raw("GET", "/api/v1/management/environments")
        if resp.status_code == 404:
            return []
        if resp.status_code in (401, 403):
            return []
        resp.raise_for_status()
        body = resp.json()
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body if isinstance(body, list) else []

    def list_environments_via_me(self) -> dict | None:
        resp = self._request_raw("GET", "/api/v1/management/me")
        if resp.status_code != 200:
            return None
        return resp.json()

    def discover_from_surveys(self) -> list[dict]:
        try:
            surveys = self.list_surveys()
        except FormbricksError:
            return []
        seen = {}
        for s in surveys:
            eid = s.get("environmentId")
            if eid and eid not in seen:
                seen[eid] = {
                    "name": f"env_{eid[:8]}",
                    "label": f"Environment {eid[:8]}",
                    "env_type": "prod",
                    "group": "Discovered",
                    "base_url": self.base_url,
                    "api_key": self.api_key,
                    "environment_id": eid,
                }
        return list(seen.values())

    def verify_connection(self) -> bool:
        try:
            self._request("GET", "/api/v1/management/surveys?limit=1")
            return True
        except FormbricksError:
            return False

    def connection_scope(self) -> str:
        resp = self._request_raw("GET", "/api/v1/management/me")
        if resp.status_code == 200:
            return "organization"
        if resp.status_code == 400:
            return "environment"
        if resp.status_code in (401, 403):
            return "invalid"
        return "unknown"

    @staticmethod
    def discover_environments(base_url: str, api_key: str) -> list[dict]:
        client = FormbricksClient(base_url, api_key)

        envs = client.list_environments()
        if envs:
            return envs

        me_data = client.list_environments_via_me()
        if me_data:
            perms = me_data.get("environmentPermissions") or []
            if perms:
                return [
                    {
                        "name": p["projectName"].lower().replace(" ", "-"),
                        "label": p["projectName"],
                        "env_type": p["environmentType"],
                        "group": p["projectName"],
                        "base_url": base_url,
                        "api_key": api_key,
                        "environment_id": p["environmentId"],
                    }
                    for p in perms
                ]
            project = me_data.get("project")
            if project:
                return [{
                    "name": project["name"].lower().replace(" ", "-"),
                    "label": project["name"],
                    "env_type": me_data.get("type", "production"),
                    "group": project["name"],
                    "base_url": base_url,
                    "api_key": api_key,
                    "environment_id": me_data["id"],
                }]

        envs = client.discover_from_surveys()
        if envs:
            return envs

        connected = client.verify_connection()
        scope = client.connection_scope()
        if connected:
            hint = ""
            if scope == "environment":
                hint = (" (API key is scoped to one environment — "
                        "use an organization-level key to auto-discover all)")
            return [{"name": "default", "label": f"Default{hint}", "env_type": "prod",
                     "base_url": base_url, "api_key": api_key}]
        return []

    @staticmethod
    def validate_json(raw: str) -> dict:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise FormbricksError(f"Invalid JSON: {e}") from e

    @staticmethod
    def extract_questions(survey: dict) -> list[dict]:
        questions = survey.get("questions", [])
        if not questions:
            for block in survey.get("blocks", []):
                questions.extend(block.get("elements", []))
        return questions
