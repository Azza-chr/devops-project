import json
import logging
import sys
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class JsonFormatter(logging.Formatter):
    """Turn every log record into one JSON line."""

    def format(self, record):
        entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        entry.update(getattr(record, "extra_fields", {}))
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

app = FastAPI(title="DevOps Project API")

items: list[dict] = []


class Item(BaseModel):
    name: str
    price: float


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    fields = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
    }
    try:
        response = await call_next(request)
    except Exception:
        fields["status"] = 500
        fields["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
        logger.exception("unhandled error", extra={"extra_fields": fields})
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    fields["status"] = response.status_code
    fields["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
    if response.status_code >= 500:
        level = logging.ERROR
    elif response.status_code >= 400:
        level = logging.WARNING
    else:
        level = logging.INFO
    logger.log(level, "request completed", extra={"extra_fields": fields})
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/items")
def list_items():
    return items


@app.get("/items/{item_id}")
def get_item(item_id: int):
    for item in items:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")


@app.post("/items", status_code=201)
def create_item(item: Item):
    new_item = {"id": len(items) + 1, **item.model_dump()}
    items.append(new_item)
    return new_item


@app.get("/error")
def trigger_error():
    """Simulate a crash, to demonstrate error logging."""
    raise RuntimeError("simulated failure")