# main.py:
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException as StarletteHTTPException

import models
from config import settings
from database import Base, engine, get_db
from routers import posts, users

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) # this creates tables if they don't exist -----
        # --- run_sync(), create_all() is NOT async, In production should use Alembic migrations instead.
        # run_sync() exists because some ORM operations are inherently synchronous, and async SQLAlchemy provides a safe bridge to run them without breaking the event loop.
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])

app.mount("/static", StaticFiles(directory="static"), name="static") # serving static files with FastAPI app, in production use a dedicated server like Nginx
# app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):  # why Annotated? see get_db()
    count_result = await db.execute(select(func.count()).select_from(models.Post))
    total = count_result.scalar() or 0
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author))  # selectinload(): avoids N+1 queries 
        .order_by(models.Post.date_posted.desc())
        .limit(settings.posts_per_page),
    )
    posts = result.scalars().all()
    has_more = len(posts) < total
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "posts": posts, 
            "title": "Home",
            "limit": settings.posts_per_page,
            "has_more": has_more,
        },
    )


@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(
    request: Request,
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id),
    )
    post = result.scalars().first()
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    count_result = await db.execute(
        select(func.count())
        .select_from(models.Post)
        .where(models.Post.user_id == user_id),
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id).order_by(models.Post.date_posted.desc()).limit(settings.posts_per_page),
    )
    posts = result.scalars().all()
    has_more = len(posts) < total
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {
            "posts": posts, 
            "user": user, 
            "title": f"{user.username}'s Posts", 
            "limit": settings.posts_per_page, 
            "has_more": has_more
        },
    )


@app.get("/login", include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"title": "Login"},
    )


@app.get("/register", include_in_schema=False)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html",
        {"title": "Register"},
    )


@app.get("/account", include_in_schema=False)
async def account_page(request: Request):
    return templates.TemplateResponse(
        request,
        "account.html",
        {"title": "Account"},
    )


@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(
    request: Request,
    exception: StarletteHTTPException,
):
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )

# venv\Scripts\activate
# fastapi dev main.py
# uvicorn main:app --reload

# http://127.0.0.1:8000/
# http://127.0.0.1:8000/docs

# question: how oauth2 is being used instead of just jwt tokens? -----

"""
Base.metadata.create_all(engine):
Creates database tables from your SQLAlchemy models, Only creates what does NOT already exist, Does NOT modify existing tables.
Base is the parent class for all your models, engine is the database connection.
SQLAlchemy registers every model that subclasses Base.

select(models.Post).options(selectinload(models.Post.author)):
Loads all authors in one extra query, Avoids N+1, Avoids async lazy-loading errors, Safe for templates

Eager loading: loading related data at the same time as the main query, instead of loading it later when you access it. the opposite of lazy loading.

If a method touches the database in async SQLAlchemy → you must await it:
await db.execute(), await db.commit(), await db.refresh(), await db.delete()

async SQLAlchemy returns awaitables for I/O, while sync SQLAlchemy blocks the thread and returns results immediately.

Dependency Injection lets FastAPI create, share, and clean up resources (like DB sessions) for you instead of doing it inside your route functions.

SQLAlchemy eager loading methods:
- selectinload(): Loading collections (lists of related objects) - 	Runs a separate SELECT query that loads all related items in one go using an WHERE IN.
- joinedload(): loads related data in the same query using SQL JOINs. Loading a single related object (e.g., a foreign key).
- subqueryload(): Loading collections when a JOIN is problematic.

Starlette: a lightweight, high-performance Python ASGI web framework that FastAPI is built upon. 
FastAPI inherits directly from Starlette's class, which is why it gets high performance and core features like routing and WebSocket support from it.

"""

