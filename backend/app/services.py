import json
from statistics import mean

from fastapi import HTTPException
from openai import OpenAI, OpenAIError

from .config import setting


def summarize(rows):
    rows = sorted(rows, key=lambda row: row["date"])
    if not rows:
        return {
            "period": None,
            "count": 0,
            "unit": "분",
            "metrics": None,
            "trend": "데이터 없음",
            "change_percent": None,
        }

    values = [float(row["value"]) for row in rows]
    daily = {}
    for row in rows:
        daily[row["date"]] = daily.get(row["date"], 0) + float(row["value"])

    days = sorted(daily)
    totals = [daily[day] for day in days]
    trend = "판단 보류 (14개 기록일 필요)"
    change_percent = None
    if len(days) >= 14:
        previous = mean(totals[-14:-7])
        recent = mean(totals[-7:])
        if previous == 0:
            trend = "유지" if recent == 0 else "증가"
        else:
            change_percent = round((recent - previous) / previous * 100, 1)
            trend = (
                "증가"
                if change_percent > 5
                else "감소"
                if change_percent < -5
                else "유지"
            )

    best_day = max(days, key=lambda day: daily[day])
    return {
        "period": f"{days[0]} ~ {days[-1]}",
        "count": len(rows),
        "unit": "분",
        "metrics": {
            "total": round(sum(values), 1),
            "average": round(mean(values), 1),
            "max": max(values),
            "min": min(values),
        },
        "best_day": {"date": best_day, "value": round(daily[best_day], 1)},
        "trend": trend,
        "change_percent": change_percent,
        "trend_basis": "최근 7개 기록일과 직전 7개 기록일의 일별 합계 평균 비교",
    }


def _compact_summary(summary):
    """AI에는 원본 100개가 아니라 이 작은 요약만 보낸다."""
    return {
        "기간": summary.get("period"),
        "개수": summary.get("count"),
        "통계": summary.get("metrics"),
        "최고일": summary.get("best_day"),
        "추세": summary.get("trend"),
        "변화율": summary.get("change_percent"),
        "단위": "분",
    }


def _mock_answer(question, summary):
    if not summary.get("count"):
        return "아직 학습 기록이 없습니다. 먼저 날짜와 학습 시간을 추가해주세요."
    metrics = summary["metrics"]
    change = summary.get("change_percent")
    change_text = ""
    if change is not None:
        change_text = f" 변화율은 {change:+.1f}%입니다."
    return (
        f"현재 {summary['count']}개 기록의 평균은 {metrics['average']}분이고, "
        f"최근 흐름은 {summary['trend']}입니다.{change_text} "
        "지금은 토큰을 쓰지 않는 연습 모드이며, 제출 전 OpenAI 모드로 확인할 수 있어요."
    )


def answer(question, messages, summary):
    if setting("AI_MODE", "mock") == "mock":
        return _mock_answer(question, summary), {"mode": "mock", "total_tokens": 0}

    api_key = setting("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(503, "OPENAI_API_KEY가 설정되지 않았습니다.")

    instructions = (
        "당신은 학습시간 데이터 분석 비서입니다. 한국어로 4문장 이내로 답하세요. "
        "제공된 요약 수치만 사용하고, 없는 정보는 알 수 없다고 말하세요. "
        "단위는 분입니다.\n[요약]"
        + json.dumps(_compact_summary(summary), ensure_ascii=False, separators=(",", ":"))
    )
    recent_messages = [
        {"role": message["role"], "content": message["content"][:500]}
        for message in messages[-4:]
    ]
    model = setting("OPENAI_MODEL", "gpt-5.4-mini")
    base_url = setting("OPENAI_BASE_URL") or None
    request = {
        "model": model,
        "messages": (
            [{"role": "system", "content": instructions}]
            + recent_messages
            + [{"role": "user", "content": question}]
        ),
        "max_completion_tokens": min(
            400, max(100, int(setting("MAX_OUTPUT_TOKENS", "220")))
        ),
    }

    try:
        with OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=35.0,
            max_retries=0,
        ) as client:
            response = client.chat.completions.create(**request)
        text = response.choices[0].message.content or ""
        if not text.strip():
            raise HTTPException(502, "AI 응답이 비어 있습니다.")
        usage = response.usage.model_dump() if response.usage else None
        return text, usage
    except OpenAIError as error:
        provider_status = getattr(error, "status_code", None)
        status = 429 if provider_status == 429 else 502
        message = str(error).replace(api_key, "[API_KEY]")[:350]
        raise HTTPException(
            status,
            f"AI 호출 실패"
            f"{f' (제공자 상태 {provider_status})' if provider_status else ''}: {message}",
        ) from error
