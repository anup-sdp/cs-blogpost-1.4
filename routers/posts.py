# routers/posts.py:
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from auth import CurrentUser
from config import settings
from database import get_db
from schemas import PostCreate, PostResponse, PostUpdate, PaginatedPostsResponse

router = APIRouter()


@router.get("", response_model=PaginatedPostsResponse)
async def get_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0, # query parameters with validation, skip must be >= 0
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page, # limit must be between 1 and 100, default is 10
):    
    # ^ Annotated used (recommended)  # or db: AsyncSession = Depends(get_db) # functionally equivalent, Both inject the DB session
    # meaning: Type is AsyncSession, Dependency provider is get_db
    count_result = await db.execute(select(func.count()).select_from(models.Post))
    total = count_result.scalar() or 0 
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
        .offset(skip)
        .limit(limit),
    )
    posts = result.scalars().all()
    has_more = skip + len(posts) < total

    return PaginatedPostsResponse(
        posts=[PostResponse.model_validate(post) for post in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )

"""
pwsh: curl -X GET "http://127.0.0.1:8000/api/posts?skip=3&limit=2" -H "accept: application/json"
or details: curl -v "http://127.0.0.1:8000/api/posts?skip=3&limit=2"
or: curl.exe -s "http://127.0.0.1:8000/api/posts?skip=3&limit=2" | ConvertFrom-Json
response:
{
  "total": 40,
  "skip": 3,
  "limit": 2,
  "has_more": true,
  "posts": [
    {
      "title": "Security Best Practices — Seed #37",
      "content": "Never hardcode secrets; environment variables and proper config are essential.\n\n(Seed post #37)",
      "id": 37,
      "user_id": 1,
      "date_posted": "2026-03-09T08:45:56.412726",
      "author": {
        "id": 1,
        "username": "anup30",
        "image_file": "a79fe2e387d04d60b8e1daea58806468.jpg",
        "image_path": "/media/profile_pics/a79fe2e387d04d60b8e1daea58806468.jpg"
      }
    },
    {
      "title": "Testing FastAPI Apps — Seed #36",
      "content": "Using TestClient and integration tests for endpoints and dependencies.\n\n(Seed post #36)",
      "id": 36,
      "user_id": 3,
      "date_posted": "2026-03-07T08:22:51.797342",
      "author": {
        "id": 3,
        "username": "ramu",
        "image_file": "83a4354d553242e7b04537898c116f18.jpg",
        "image_path": "/media/profile_pics/83a4354d553242e7b04537898c116f18.jpg"
      }
    }
  ]
}
"""


@router.post(
    "",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(post: PostCreate,current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)],):
    new_post = models.Post(title=post.title, content=post.content, user_id=current_user.id,)    
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])  # --- attribute_names
    return new_post

# get a post by id
@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id),
    )
    post = result.scalars().first()
    if post:
        return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@router.put("/{post_id}", response_model=PostResponse)
async def update_post_full(
    post_id: int,
    post_data: PostCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )        

    post.title = post_data.title
    post.content = post_data.content

    await db.commit()
    await db.refresh(post, attribute_names=["author"])  # attribute_names, to load the author relationship
    return post


@router.patch("/{post_id}", response_model=PostResponse)
async def update_post_partial(
    post_id: int,
    post_data: PostUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )

    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, current_user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post",
        )

    await db.delete(post)
    await db.commit()

    # to do: add get posts sorting by criteria(eg. by a user/ ascending-descending, sort by name/date etc.), and pagination ? -----