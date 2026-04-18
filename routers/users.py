# routers/users.py:
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, BackgroundTasks

from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
# from PIL import UnidentifiedImageError  # for pillow error when trying to open a non-image file
from sqlalchemy import delete as sql_delete
from starlette.concurrency import run_in_threadpool
# from image_utils import delete_profile_image, process_profile_image
from fastapi.responses import Response


import models, schemas
from auth import (CurrentUser, create_access_token, hash_password, verify_password, hash_reset_token, generate_reset_token)
from config import settings
from database import get_db
from email_utils import send_password_reset_email
from schemas import PostResponse, Token, UserCreate, UserPrivate, UserPublic, UserUpdate, PaginatedPostsResponse, ChangePasswordRequest, ResetPasswordRequest, ForgotPasswordRequest

router = APIRouter()


@router.post(
    "",  # was "/api/users" when these codes were in main.py
    response_model=UserPrivate,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.User).where(func.lower(models.User.username) == user.username.lower()),  # ----- dont allow 2 users "Anup" and "aNup"
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == user.email.lower()), # ----- not needed? 
    )
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    # we can simplify create_user logic, as for email unique=True, DB will raise an IntegrityError if we try to insert a duplicate email, 
    # but that error is less user-friendly and we want to catch it ourselves to return a 400 with a clear message instead of a 500 error. 
    # So we do the check manually before inserting. if we don't: users gets for duplite email: HTTP status: 500 Internal Server Error,
    # not the friendly 400 Email already registered message currently provided
    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(user.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


# returns access token
@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Look up user by email (case-insensitive)
    # Note: OAuth2PasswordRequestForm uses "username" field, but we treat it as email
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == form_data.username.lower()
            # ^ email to username comparison ----- using email and password for login, in swagger using username field for email -----
        ),
    )
    user = result.scalars().first()

    # Verify user exists and password is correct
    # Don't reveal which one failed (security best practice)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token with user id as subject
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


# returns current logged in user
@router.get("/me", response_model=UserPrivate)
async def get_current_user(current_user: CurrentUser):
    return current_user


@router.get("/{user_id}/posts", response_model=PaginatedPostsResponse)
async def get_user_posts(
    user_id: int, 
    db: Annotated[AsyncSession, Depends(get_db)], 
    skip: Annotated[int, Query(ge=0)] = 0, 
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
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
        .where(models.Post.user_id == user_id)
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


@router.patch("/{user_id}", response_model=UserPrivate)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user_update.username is not None and user_update.username.lower() != user.username.lower():
        result = await db.execute(
            select(models.User).where(func.lower(models.User.username) == user_update.username.lower()), # ----- dont allow 2 users "Anup" and "aNup"
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )
    if user_update.email is not None and user_update.email.lower() != user.email.lower():
        result = await db.execute(
            select(models.User).where(func.lower(models.User.email) == user_update.email.lower()),
        )
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    if user_update.username is not None:
        user.username = user_update.username # ---
    if user_update.email is not None:
        user.email = user_update.email.lower()
    #

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user",
        )
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    # image_data is in DB and deleted automatically via cascade
    await db.delete(user)
    await db.commit()




# new add
@router.get("/{user_id}/picture")
async def get_profile_picture(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user or not user.image_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No profile picture")

    return Response(
        content=user.image_data,
        media_type=user.image_content_type or "image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


@router.patch("/{user_id}/picture", response_model=schemas.UserPublic)
async def update_profile_picture(
    user_id: int,
    file: Annotated[UploadFile, File()],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[models.User, Depends(get_current_user)],
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file.content_type}'. Use JPEG, PNG, GIF, or WebP.",
        )

    # Read and enforce 100 KB limit
    image_bytes = await file.read()
    if len(image_bytes) > settings.max_image_size_bytes:
        sz = settings.max_image_size_bytes
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Image too large ({len(image_bytes) // 1024} KB). "
                f"Maximum size is {sz // 1024} KB. Recommended dimensions: 200x200 px."
            ),
        )

    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.image_data = image_bytes
    user.image_content_type = file.content_type
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}/picture", response_model=UserPrivate)
async def delete_user_picture(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user's picture",
        )

    if current_user.image_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to delete",
        )

    current_user.image_data = None
    current_user.image_content_type = None
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = hash_password(password_data.new_password)

    await db.execute(
        sql_delete(models.PasswordResetToken).where(
            models.PasswordResetToken.user_id == current_user.id,
        ),
    )

    await db.commit()
    return {"message": "Password changed successfully"}


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,  # --- for sending email in background after response is sent
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == request_data.email.lower(),
        ),
    )
    user = result.scalars().first()

    if user:
        await db.execute(
            sql_delete(models.PasswordResetToken).where(
                models.PasswordResetToken.user_id == user.id,
            ),
        )

        token = generate_reset_token()
        token_hash = hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.reset_token_expire_minutes,
        )

        reset_token = models.PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(reset_token)
        await db.commit()

        background_tasks.add_task(
            send_password_reset_email,
            to_email=user.email,
            username=user.username,
            token=token,
        )

    return {
        "message": "If an account exists with this email, you will receive password reset instructions.",
    }
"""
FastAPI BackgroundTasks vs Celery:
BackgroundTasks:
After FastAPI sends the HTTP response to the user, it keeps the connection alive just long enough to run our function in the background.
- Built-in FastAPI feature, no extra dependencies
- Executes tasks after response is sent, within the same process
- If the background task uses 100% CPU, our API will slow down for everyone.
- Suitable for lightweight tasks (e.g., sending an email, logging)
- Not ideal for long-running or resource-intensive tasks, as it can block the main event loop
- if FastAPI app crashes or restarts while the task is running, the task is lost and will never finish.
Celery:
our FastAPI app sends a "message" to a broker (Redis). A completely separate "Worker" process picks up that message and does the work.
- Separate task queue system, requires additional setup (e.g., Redis or RabbitMQ)
- Executes tasks in separate worker processes, allowing for true asynchronous execution
- Suitable for heavy or long-running tasks (e.g., video processing, complex computations)
- More robust features (e.g., retries, scheduling, monitoring) but adds complexity

"""


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request_data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    token_hash = hash_reset_token(request_data.token)

    result = await db.execute(
        select(models.PasswordResetToken).where(
            models.PasswordResetToken.token_hash == token_hash,
        ),
    )
    reset_token = result.scalars().first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if reset_token.expires_at < datetime.now(UTC): # expired token
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    result = await db.execute(
        select(models.User).where(models.User.id == reset_token.user_id),
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.password_hash = hash_password(request_data.new_password)

    await db.execute(
        sql_delete(models.PasswordResetToken).where(
            models.PasswordResetToken.user_id == user.id,
        ),
    )

    await db.commit()
    return {
        "message": "Password reset successfully. You can now log in with your new password.",
    }


# returns public info of any user by user_id
@router.get("/{user_id}", response_model=UserPublic)
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
"""
^
 Router order matters. In your router, /{user_id} (integer) and /{user_id}/picture are both GET routes. 
 FastAPI matches top to bottom, so make sure GET /{user_id}/picture is defined before 
 GET /{user_id} — otherwise the /picture segment gets swallowed as a user_id. - claude sonnet 4.6
"""