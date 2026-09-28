"""120일치 학습시간 예시 데이터를 중복 없이 추가한다."""
from datetime import date, timedelta

from fastapi import HTTPException

from app.storage import get_store


def seed():
    store = get_store()
    start = date(2026, 5, 1)
    added = 0
    for index in range(120):
        day = start + timedelta(days=index)
        item_id = f"sample-{day.isoformat()}"
        item = {
            "date": day.isoformat(),
            "value": 35 + (index % 7) * 8 + (index // 30) * 4,
            "memo": "예시 학습 기록",
        }
        try:
            store.get("data", item_id)
        except HTTPException as error:
            if error.status_code != 404:
                raise
            store.save("data", item, item_id)
            added += 1
    print(f"{added}개를 추가했습니다. 전체 예시 데이터는 120개입니다.")


if __name__ == "__main__":
    seed()

