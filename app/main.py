from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="DevOps Project API")

items: list[dict] = []


class Item(BaseModel):
    name: str
    price: float


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