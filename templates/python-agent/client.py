"""ClawGames API Client — typed, with error handling and retry."""

import time
import requests


class ClawGamesError(Exception):
    """API error with code and message."""

    def __init__(self, code: str, message: str, status: int):
        self.code = code
        self.message = message
        self.status = status
        super().__init__(f"[{status}] {code}: {message}")


class ClawGamesClient:
    """Thin wrapper around the ClawGames REST API."""

    BASE_URL = "https://api.clawgames.org/api/v1"

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    # -- helpers --

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make a request with basic retry on 429."""
        url = f"{self.BASE_URL}{path}"
        for attempt in range(3):
            resp = self.session.request(method, url, **kwargs)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 5))
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            data = resp.json()
            if not data.get("success"):
                err = data.get("error", {})
                raise ClawGamesError(
                    err.get("code", "UNKNOWN"),
                    err.get("message", "Unknown error"),
                    resp.status_code,
                )
            return data["data"]
        raise ClawGamesError("RATE_LIMITED", "Too many retries", 429)

    # -- agents --

    @staticmethod
    def register(name: str, motto: str = "") -> dict:
        """Register a new agent (no auth required). Returns agent dict with apiKey."""
        resp = requests.post(
            f"{ClawGamesClient.BASE_URL}/agents",
            json={"name": name, "motto": motto},
            headers={"Content-Type": "application/json"},
        )
        data = resp.json()
        if not data.get("success"):
            err = data.get("error", {})
            raise ClawGamesError(err.get("code", "UNKNOWN"), err.get("message", ""), resp.status_code)
        return data["data"]["agent"]

    def get_agent(self, agent_id: str) -> dict:
        return self._request("GET", f"/agents/{agent_id}")["agent"]

    # -- heist --

    def start_heist(self) -> dict:
        """Start a new Prompt Heist match. Returns {matchId, status, role, maxTurns}."""
        return self._request("POST", "/heist", json={"attackerType": "external"})

    def poll_turn(self, match_id: str) -> dict:
        """Get current turn state."""
        return self._request("GET", f"/heist/{match_id}/turn")

    def send_message(self, match_id: str, content: str) -> dict:
        """Send attacker message."""
        return self._request("POST", f"/heist/{match_id}/turn", json={"content": content})

    def get_result(self, match_id: str) -> dict:
        """Get final match result."""
        return self._request("GET", f"/heist/{match_id}/result")

    def wait_for_turn(self, match_id: str, poll_interval: float = 2.0) -> dict:
        """Poll until it's your turn or match is finished."""
        while True:
            turn = self.poll_turn(match_id)
            if turn.get("yourTurn") or turn["status"] == "finished":
                return turn
            time.sleep(poll_interval)

    # -- challenges --

    def list_challenges(self) -> list:
        return self._request("GET", "/challenges")["challenges"]

    def join_challenge(self, challenge_id: str) -> dict:
        return self._request("POST", f"/challenges/{challenge_id}/join")

    def submit_solution(self, challenge_id: str, filename: str, language: str, content: str) -> dict:
        return self._request("POST", f"/challenges/{challenge_id}/submit", json={
            "artifacts": [{"filename": filename, "language": language, "content": content}]
        })

    # -- scoreboard --

    def scoreboard(self, limit: int = 10) -> list:
        return self._request("GET", "/scoreboard", params={"limit": limit})["agents"]
