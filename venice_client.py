from __future__ import annotations

import logging
import os
from typing import Any, Dict, Mapping, Optional

import requests

from .globals import API_ENDPOINTS, USER_AGENT, VENICEAI_BASE_URL
from .venice_config import config as venice_config

LOG = logging.getLogger(__name__)
if os.environ.get("VENICE_CLIENT_DEBUG", "").lower() in {"1", "true"}:
    LOG.setLevel(logging.DEBUG)


class VeniceAPIError(Exception):
    pass


class DummyResponse:
    def __init__(self, payload: dict | None = None, status_code: int = 200) -> None:
        self._payload = payload or {}
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload

    @property
    def text(self) -> str:
        return ""

    def __getattr__(self, item: str) -> Any:
        return None


class VeniceClient:
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})
        self._dry_run = os.environ.get("VENICE_CLIENT_DRY_RUN", "").lower() in {"1", "true"}

    @property
    def dry_run(self) -> bool:
        return self._dry_run

    def _ensure_api_key(self) -> str:
        key = venice_config.apikey.strip()
        if not key:
            raise VeniceAPIError(
                "VeniceAI API key is missing. Set it via the VeniceAI settings before using the nodes."
            )
        return key

    def _build_headers(self, extra: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
        headers: Dict[str, str] = {"Authorization": f"Bearer {self._ensure_api_key()}"}
        if extra:
            headers.update(extra)
        return headers

    def _friendly_status_hint(self, status_code: int) -> str:
        if status_code == 401:
            return "The API key may be invalid, expired, or lack permissions."
        if status_code == 404:
            return "The requested VeniceAI endpoint was not found. Ensure the node and catalog data are up to date."
        if status_code == 429:
            return "Request rate limits were hit. Wait a moment before retrying."
        if 500 <= status_code < 600:
            return "VeniceAI appears to be experiencing server issues; try again in a bit."
        return "Check your request parameters and ensure your API key is valid."

    def _friendly_network_hint(self) -> str:
        return "Unable to reach VeniceAI. Confirm your internet connection and that api.venice.ai is reachable."

    def request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        if self._dry_run:
            logging.debug("VeniceClient dry run skipping %s %s", method, endpoint)
            return DummyResponse()

        url = VENICEAI_BASE_URL + endpoint
        headers = kwargs.pop("headers", None)
        kwargs.setdefault("timeout", 30)
        try:
            response = self._session.request(method, url, headers=self._build_headers(headers), **kwargs)
            response.raise_for_status()
        except requests.HTTPError as exc:
            self._log_response(method, endpoint, exc.response)
            hint = (
                self._friendly_status_hint(exc.response.status_code)
                if exc.response is not None
                else "Unexpected response from VeniceAI."
            )
            message = f"Venice request failed ({method} {endpoint}): {exc}. \n{hint}"
            LOG.debug("Venice request failed: %s %s %s", method, endpoint, exc)
            raise VeniceAPIError(message) from exc
        except requests.RequestException as exc:
            message = f"{self._friendly_network_hint()} Details: {exc}"
            LOG.debug("Venice network error: %s %s %s", method, endpoint, exc)
            raise VeniceAPIError(message) from exc
        self._log_response(method, endpoint, response)
        return response

    def _log_response(self, method: str, endpoint: str, response: Optional[requests.Response | DummyResponse]) -> None:
        if not LOG.isEnabledFor(logging.DEBUG) or response is None:
            return

        headers = getattr(response, "headers", None)
        header_snapshot: Dict[str, Any] = dict(headers) if headers else {}
        content_type = (header_snapshot.get("Content-Type") or "").lower()

        body = ""
        readable_body = content_type.startswith("application/json") or content_type.startswith("text/")
        if readable_body or not content_type:
            try:
                body = response.text or ""
            except Exception as exc:
                body = f"<unable to read body: {exc}>"
            if len(body) > 2000:
                body = body[:2000] + "...[truncated]"
        else:
            body = f"<{content_type} response body omitted>"

        LOG.debug(
            "Venice response %s %s status=%s headers=%s body=%s",
            method,
            endpoint,
            getattr(response, "status_code", "<?>"),
            header_snapshot,
            body,
        )

    def post_json(self, endpoint: str, payload: Mapping[str, Any], **kwargs: Any) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        headers.update(kwargs.pop("headers", {}))
        response = self.request("POST", endpoint, json=payload, headers=headers, **kwargs)
        return response.json()

    def get_json(self, endpoint: str, params: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        response = self.request("GET", endpoint, params=params)
        return response.json()

    def list_models(self, model_type: Optional[str] = None) -> Dict[str, Any]:
        params = {"type": model_type} if model_type else None
        return self.get_json(API_ENDPOINTS["list_models"], params=params)

    def list_styles(self) -> Dict[str, Any]:
        return self.get_json(API_ENDPOINTS["list_styles"])

    def list_characters(self) -> Dict[str, Any]:
        return self.get_json(API_ENDPOINTS["characters"])


client = VeniceClient()
