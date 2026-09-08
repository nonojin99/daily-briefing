# collect_github.py
# GitHub Actions에서 실행됨. 내 모든 레포의 최근 7일 활동을 수집.

import os
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone

TOKEN = os.environ["GH_PAT"]        # Secrets에서 주입됨
USER = os.environ.get("GH_USER", "nonojin99")
DAYS = 7

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}


def get_repos():
    """내 레포 전체 (최근 푸시순)"""
    repos = []
    page = 1
    while True:
        r = requests.get(
            "https://api.github.com/user/repos",
            headers=HEADERS,
            params={"per_page": 100, "page": page, "sort": "pushed"},
            timeout=15,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def get_recent_commits(full_name, since_iso):
    """since 이후 내 커밋"""
    r = requests.get(
        f"https://api.github.com/repos/{full_name}/commits",
        headers=HEADERS,
        params={"since": since_iso, "author": USER, "per_page": 100},
        timeout=15,
    )
    return r.json() if r.status_code == 200 else []


def main():
    now = datetime.now(timezone.utc)
    since_iso = (now - timedelta(days=DAYS)).isoformat()

    repos = get_repos()
    print(f"레포 {len(repos)}개 발견")

    result = {
        "collected_at": now.isoformat(),
        "period_days": DAYS,
        "active": [],
        "dormant": [],
    }

    for repo in repos:
        pushed_at = datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))
        days_idle = (now - pushed_at).days
        base = {
            "name": repo["name"],
            "days_idle": days_idle,
            "last_push": pushed_at.strftime("%Y-%m-%d"),
            "description": repo["description"] or "",
            "url": repo["html_url"],
        }

        # 오래 방치된 건 커밋 조회 생략 (API 절약)
        if days_idle > DAYS:
            result["dormant"].append(base)
            continue

        commits = get_recent_commits(repo["full_name"], since_iso)
        if commits:
            base["commit_count"] = len(commits)
            base["recent_messages"] = [
                c["commit"]["message"].split("\n")[0] for c in commits[:5]
            ]
            result["active"].append(base)
            print(f"  ✅ {repo['name']}: {len(commits)}건")
        else:
            result["dormant"].append(base)

    result["active"].sort(key=lambda x: x["commit_count"], reverse=True)
    result["dormant"].sort(key=lambda x: x["days_idle"], reverse=True)

    Path("data").mkdir(exist_ok=True)
    with open("data/github.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n활동 {len(result['active'])}개 / 휴면 {len(result['dormant'])}개")


if __name__ == "__main__":
    main()
