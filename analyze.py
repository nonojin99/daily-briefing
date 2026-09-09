ACTIVE_TOPIC = "active"
def is_tracked(repo):
    """추적 대상인가? active 토픽이 붙은 것만."""
    if repo.get("archived"):
        return False
    return ACTIVE_TOPIC in repo.get("topics", [])
    
    # active 토픽 붙은 것만 추적
    relevant = [r for r in all_repos if is_tracked(r)]
    
    "total_tracked": len(relevant),
        "total_repos": len(all_repos),

print(f"\n추적 중 {len(relevant)}개 / 전체 {len(all_repos)}개")
    
# analyze.py
# github.json을 읽고 "오늘 뭘 만질지" 판단.

import json
from pathlib import Path
from datetime import datetime, timezone

RELEVANT_DAYS = 90   # 이보다 오래 방치된 건 "끝난 프로젝트"로 보고 제외

# 방치 구간 정의 (하한, 라벨, 우선순위)
ZONES = [
    (22, "danger",  "되살릴지 접을지 결정할 때"),
    (8,  "warning", "슬슬 잊혀지는 중"),
    (3,  "resting", "잠깐 쉬는 중"),
    (0,  "active",  "진행 중"),
]


def classify(days_idle):
    """방치 일수를 구간으로 변환"""
    for threshold, zone, label in ZONES:
        if days_idle >= threshold:
            return zone, label
    return "active", "진행 중"


def pick_focus(candidates):
    """오늘의 포커스 1개 선정.
    warning 구간(8~21일)을 최우선 - 아직 살릴 수 있는 골든타임.
    없으면 danger 중 가장 최근 것 (기억이 남아있는 쪽).
    """
    warnings = [c for c in candidates if c["zone"] == "warning"]
    if warnings:
        # warning 중 가장 오래된 것 = 가장 급한 것
        return max(warnings, key=lambda x: x["days_idle"])

    dangers = [c for c in candidates if c["zone"] == "danger"]
    if dangers:
        # danger 중 가장 최근 것 = 아직 기억나는 것
        return min(dangers, key=lambda x: x["days_idle"])

    return None


def main():
    with open("data/github.json", encoding="utf-8") as f:
        data = json.load(f)

    all_repos = data["active"] + data["dormant"]

    # 90일 넘게 방치된 건 제외
    relevant = [r for r in all_repos if r["days_idle"] <= RELEVANT_DAYS]

    # 구간 분류
    for repo in relevant:
        zone, label = classify(repo["days_idle"])
        repo["zone"] = zone
        repo["zone_label"] = label

    focus = pick_focus(relevant)

    # 구간별 집계
    buckets = {}
    for repo in relevant:
        buckets.setdefault(repo["zone"], []).append(repo)
    for zone in buckets:
        buckets[zone].sort(key=lambda x: x["days_idle"], reverse=True)

    result = {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "focus": focus,
        "total_relevant": len(relevant),
        "total_archived": len(all_repos) - len(relevant),
        "buckets": buckets,
    }

    Path("data").mkdir(exist_ok=True)
    with open("data/analysis.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 콘솔 출력 (Actions 로그에서 바로 확인용)
    print(f"\n분석 대상 {len(relevant)}개 / 보관 처리 {result['total_archived']}개")
    for zone, _, label in ZONES:
        items = buckets.get(zone, [])
        if items:
            print(f"  [{label}] {len(items)}개: {', '.join(r['name'] for r in items[:5])}")

    if focus:
        print(f"\n💡 오늘의 포커스: {focus['name']} ({focus['days_idle']}일 방치)")
    else:
        print("\n✅ 방치된 프로젝트 없음. 잘하고 계세요.")


if __name__ == "__main__":
    main()
