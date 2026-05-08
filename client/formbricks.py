import json
import requests
from typing import Any, Optional


class FormbricksError(Exception):
    pass


class FormbricksClient:
    def __init__(self, base_url: str, api_key: str, environment_id: str):
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
