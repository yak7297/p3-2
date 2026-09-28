import re
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from . import services
from .models import ChatInput, ConversationInput, DataInput
from .storage import get_store


router = APIRouter(prefix="/api")
chat_lock = threading.Lock()


def valid_id(item_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", item_id):
        raise HTTPException(422, "잘못된 ID입니다.")
    return item_id


@router.get("/data", tags=["data"])
def list_data(store=Depends(get_store)):
    return sorted(
        store.list("data"), key=lambda row: (row["date"], row["id"]), reverse=True
    )


@router.get("/data/summary", tags=["data"])
def data_summary(store=Depends(get_store)):
    return services.summarize(store.list("data"))


@router.post("/data", status_code=201, tags=["data"])
def add_data(body: DataInput, store=Depends(get_store)):
    return store.save("data", body.model_dump(mode="json"))


@router.put("/data/{item_id}", tags=["data"])
def update_data(item_id: str, body: DataInput, store=Depends(get_store)):
    item_id = valid_id(item_id)
    store.get("data", item_id)
    return store.save("data", body.model_dump(mode="json"), item_id)


@router.delete("/data/{item_id}", status_code=204, tags=["data"])
def delete_data(item_id: str, store=Depends(get_store)):
    store.delete("data", valid_id(item_id))


@router.get("/conversations", tags=["conversations"])
def list_conversations(store=Depends(get_store)):
    items = [
        {key: value for key, value in item.items() if key != "messages"}
        for item in store.list("conversations")
    ]
    return sorted(items, key=lambda item: item["updated_at"], reverse=True)


@router.get("/conversations/{item_id}", tags=["conversations"])
def get_conversation(item_id: str, store=Depends(get_store)):
    return store.get("conversations", valid_id(item_id))


@router.post("/conversations", status_code=201, tags=["conversations"])
def save_conversation(body: ConversationInput, store=Depends(get_store)):
    item = body.model_dump()
    item["updated_at"] = datetime.now(timezone.utc).isoformat()
    return store.save("conversations", item)


@router.delete("/conversations/{item_id}", status_code=204, tags=["conversations"])
def delete_conversation(item_id: str, store=Depends(get_store)):
    store.delete("conversations", valid_id(item_id))


@router.post("/chat", tags=["chat"])
def chat(body: ChatInput, store=Depends(get_store)):
    if not chat_lock.acquire(blocking=False):
        raise HTTPException(429, "다른 답변을 생성 중입니다.")
    try:
        old = (
            store.get("conversations", body.conversation_id)
            if body.conversation_id
            else None
        )
        messages = old["messages"] if old else []
        if len(messages) >= 48:
            raise HTTPException(409, "대화가 길어졌습니다. 새 대화를 시작해주세요.")

        summary = services.summarize(store.list("data"))
        reply, usage = services.answer(body.message, messages, summary)
        messages = messages + [
            {"role": "user", "content": body.message},
            {"role": "assistant", "content": reply},
        ]
        saved = store.save(
            "conversations",
            {
                "title": old["title"] if old else body.message[:60],
                "messages": messages,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            body.conversation_id,
        )
        return {
            "reply": reply,
            "conversation_id": saved["id"],
            "messages": messages,
            "usage": usage,
        }
    finally:
        chat_lock.release()

