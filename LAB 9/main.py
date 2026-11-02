"""HTTP API. Валидация и перевод ошибок repository в HTTP-коды."""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse

from config import get_settings
from models import ErrorOut, ItemCreate, ItemOut, ItemUpdate
from repository import (DuplicateError, ItemRepository, NotFoundError,
                        RepositoryError, StorageUnavailableError)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("api")

repo: ItemRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    global repo
    repo = ItemRepository(get_settings())
    yield
    repo.close()


app = FastAPI(title="Lab 9: Items API (MongoDB)", lifespan=lifespan)


# --- маппинг ошибок --------------------------------------------------
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": "Объект не найден"})


@app.exception_handler(DuplicateError)
async def duplicate_handler(request: Request, exc: DuplicateError):
    return JSONResponse(status_code=409, content={"detail": "Объект с таким code уже существует"})


@app.exception_handler(StorageUnavailableError)
async def unavailable_handler(request: Request, exc: StorageUnavailableError):
    return JSONResponse(status_code=503, content={"detail": "Сервис временно недоступен"})


@app.exception_handler(RepositoryError)
async def repository_handler(request: Request, exc: RepositoryError):
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


@app.exception_handler(Exception)
async def unexpected_handler(request: Request, exc: Exception):
    log.exception("Unexpected error")  # подробности только в логе
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


# --- endpoints -------------------------------------------------------
@app.post("/items", response_model=ItemOut, status_code=201,
          responses={409: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def create_item(item: ItemCreate):
    return repo.create(item.model_dump())


@app.get("/items", response_model=list[ItemOut], responses={503: {"model": ErrorOut}})
def list_items(filter: Optional[str] = Query(None, description="Подстрока в name"),
               skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    return repo.list(filter, skip, limit)


@app.get("/items/{item_id}", response_model=ItemOut,
         responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def get_item(item_id: str):
    return repo.get(item_id)


@app.patch("/items/{item_id}", response_model=ItemOut,
           responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}})
@app.put("/items/{item_id}", response_model=ItemOut,
         responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def update_item(item_id: str, item: ItemUpdate):
    changes = item.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Не переданы поля для изменения")
    return repo.update(item_id, changes)


@app.delete("/items/{item_id}", status_code=204,
            responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}})
def delete_item(item_id: str):
    repo.delete(item_id)
    return Response(status_code=204)
