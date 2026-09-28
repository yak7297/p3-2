import json
import threading
from copy import deepcopy
from uuid import uuid4

from fastapi import HTTPException

from .config import ROOT, setting


class LocalStore:
    """개발용 JSON 저장소. 배포 제출은 Firestore 모드를 사용한다."""

    def __init__(self, path=None):
        self.path = path or ROOT / "local-demo.json"
        self.lock = threading.RLock()

    def _read(self):
        if not self.path.exists():
            return {"data": {}, "conversations": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, database):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(database, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self.path)

    def list(self, collection):
        with self.lock:
            return list(self._read()[collection].values())

    def get(self, collection, item_id):
        with self.lock:
            item = self._read()[collection].get(item_id)
            if item is None:
                raise HTTPException(404, "해당 항목이 없습니다.")
            return deepcopy(item)

    def save(self, collection, item, item_id=None):
        with self.lock:
            database = self._read()
            item_id = item_id or uuid4().hex
            database[collection][item_id] = dict(item, id=item_id)
            self._write(database)
            return deepcopy(database[collection][item_id])

    def delete(self, collection, item_id):
        with self.lock:
            database = self._read()
            if item_id not in database[collection]:
                raise HTTPException(404, "해당 항목이 없습니다.")
            del database[collection][item_id]
            self._write(database)


class FirestoreStore:
    def __init__(self):
        import firebase_admin
        from firebase_admin import credentials, firestore

        raw_json = setting("FIREBASE_SERVICE_ACCOUNT_JSON")
        credential = (
            credentials.Certificate(json.loads(raw_json))
            if raw_json
            else credentials.ApplicationDefault()
        )
        try:
            firebase_app = firebase_admin.get_app()
        except ValueError:
            firebase_app = firebase_admin.initialize_app(credential)
        self.database = firestore.client(firebase_app)

    def list(self, collection):
        return [
            dict(document.to_dict(), id=document.id)
            for document in self.database.collection(collection).stream()
        ]

    def get(self, collection, item_id):
        document = self.database.collection(collection).document(item_id).get()
        if not document.exists:
            raise HTTPException(404, "해당 항목이 없습니다.")
        return dict(document.to_dict(), id=document.id)

    def save(self, collection, item, item_id=None):
        collection_ref = self.database.collection(collection)
        reference = (
            collection_ref.document(item_id)
            if item_id is not None
            else collection_ref.document()
        )
        reference.set(item)
        return dict(item, id=reference.id)

    def delete(self, collection, item_id):
        self.get(collection, item_id)
        self.database.collection(collection).document(item_id).delete()


_store = None


def get_store():
    global _store
    if _store is None:
        mode = setting("STORAGE_BACKEND", "local")
        if mode not in {"local", "firestore"}:
            raise RuntimeError("STORAGE_BACKEND must be local or firestore")
        _store = LocalStore() if mode == "local" else FirestoreStore()
    return _store
