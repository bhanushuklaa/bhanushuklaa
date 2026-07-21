from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path


GRAPHQL_URL = "https://api.github.com/graphql"
OUTPUT_PATH = Path("assets/contribution-counts.svg")


def github_graphql(query: str, variables: dict) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not available.")

    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "github-profile-contribution-card",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub GraphQL request failed: {exc.code} {details}") from exc

    if result.get("errors"):
        raise RuntimeError(f"GitHub GraphQL errors: {result['errors']}")

    return result["data"]


def get_year_total(username: str, year: int) -> int:
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    """

    variables = {
        "login": username,
        "from": f"{year}-01-01T00:00:00Z",
        "to": f"{year}-12-31T23:59:59Z",
    }
    data = github_graphql(query, variables)

    user = data.get("user")
    if not user:
        raise RuntimeError(f"GitHub user '{username}' was not found.")

    return int(
        user["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    )


def build_svg(current_year: int, current_total: int, previous_total: int) -> str:
    previous_year = current_year - 1

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="300" height="236" viewBox="0 0 300 236" role="img" aria-label="GitHub yearly contribution totals">
  <defs>
    <linearGradient id="border" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#00E5FF"/>
      <stop offset="52%" stop-color="#8B5CF6"/>
      <stop offset="100%" stop-color="#FF006E"/>
    </linearGradient>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <rect x="2" y="2" width="296" height="232" rx="16" fill="#0D1117" stroke="url(#border)" stroke-width="2"/>

  <text x="150" y="31" text-anchor="middle" fill="#C9D1D9"
        font-family="Segoe UI, Ubuntu, sans-serif" font-size="14" font-weight="700">
    YEARLY CONTRIBUTIONS
  </text>

  <line x1="24" y1="47" x2="276" y2="47" stroke="#30363D"/>

  <text x="28" y="78" fill="#8B949E"
        font-family="Segoe UI, Ubuntu, sans-serif" font-size="13">
    CURRENT YEAR
  </text>
  <text x="272" y="78" text-anchor="end" fill="#00E5FF"
        font-family="Segoe UI, Ubuntu, sans-serif" font-size="13" font-weight="700">
    {current_year}
  </text>
  <text x="150" y="125" text-anchor="middle" fill="#00E5FF"
        font-family="Segoe UI, Ubuntu, sans-serif" font-size="43" font-weight="800"
        filter="url(#glow)">
    {current_total:,}
  </text>

  <line x1="24" y1="145" x2="276" y2="145" stroke="#30363D"/>

  <text x="28" y="174" fill="#8B949E"
        font-family="Segoe UI, Ubuntu, sans-serif" font-size="13">
    PREVIOUS YEAR
  </text>
  <text x="272" y="174" text-anchor="end" fill="#8B5CF6"
        font-family="Segoe UI, Ubuntu, sans-serif" font-size="13" font-weight="700">
    {previous_year}
  </text>
  <text x="150" y="215" text-anchor="middle" fill="#C4A7FF"
        font-family="Segoe UI, Ubuntu, sans-serif" font-size="31" font-weight="800">
    {previous_total:,}
  </text>
</svg>
"""


def main() -> int:
    username = os.environ.get("PROFILE_USERNAME", "bhanushuklaa")
    current_year = date.today().year

    current_total = get_year_total(username, current_year)
    previous_total = get_year_total(username, current_year - 1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        build_svg(current_year, current_total, previous_total),
        encoding="utf-8",
    )

    print(
        f"Updated {OUTPUT_PATH}: "
        f"{current_year}={current_total}, {current_year - 1}={previous_total}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)