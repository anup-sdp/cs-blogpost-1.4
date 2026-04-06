# populate_db.py, my custom / make needed changes for (class PasswordResetToken added in models) ... await db.execute(delete(models.PasswordResetToken))
import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import delete, select
from sqlalchemy.exc import NoResultFound

# importing common names used in tutorials
import models


from database import AsyncSessionLocal, engine

# Config
USERNAMES = ["anup30", "kasem", "ramu"]
DEFAULT_PASSWORD = "aB@12345"  # all users use this password
CLEAR_EXISTING_POSTS = True
NUM_POSTS = 40

# Simple post templates (will be combined programmatically to produce NUM_POSTS)
BASE_TITLES = [
    "Why I Love FastAPI",
    "Async Tips and Tricks",
    "Debugging 101",
    "Database Design Thoughts",
    "Deployment Notes",
    "Testing FastAPI Apps",
    "Security Best Practices",
    "Caching Strategies",
    "Background Tasks Explained",
    "Pydantic Validation Tips",
]
BASE_CONTENT = [
    "This is a seed post created by populate_db.py. Use it for testing and demo.",
    "Small notes about async and how it interacts with databases and I/O.",
    "A few reminders about logging, tracing and how to reproduce bugs reliably.",
    "Thoughts on schema design and when to use an ORM vs raw SQL.",
    "How I containerize small apps and common pitfalls to avoid.",
    "Using TestClient and integration tests for endpoints and dependencies.",
    "Never hardcode secrets; environment variables and proper config are essential.",
    "When to introduce caching and how it can change the app’s behavior.",
    "Using background tasks to keep endpoints snappy and responsive.",
    "Pydantic validators help you keep your API inputs clean and predictable.",
]


def _make_post_text(i: int) -> tuple[str, str]:
    title = BASE_TITLES[i % len(BASE_TITLES)]
    content = BASE_CONTENT[i % len(BASE_CONTENT)]
    # make titles unique
    title = f"{title} — Seed #{i+1}"
    content = f"{content}\n\n(Seed post #{i+1})"
    return title, content


async def _ensure_users(session) -> List[models.User]:
    """
    Ensure the USERNAMES exist in the DB. Return list of user ORM objects in same order as USERNAMES.
    If a user is missing, create it with a simple hashed password (note: hashing method may differ
    from your app's auth; if so, replace the hashing below to match).
    """
    found_users = {}
    q = await session.execute(select(models.User).where(models.User.username.in_(USERNAMES)))
    for u in q.scalars().all():
        found_users[u.username] = u

    users = []
    for username in USERNAMES:
        if username in found_users:
            users.append(found_users[username])
        else:
            # create a minimal user record
            # password hashing here uses sha256 just to create a stable value.
            # If your app uses bcrypt/argonaut/passlib, adjust accordingly.
            pw_hash = hashlib.sha256(DEFAULT_PASSWORD.encode("utf-8")).hexdigest()
            # choose an email pattern if not specified
            email = f"{username}@example.com"
            user = models.User(username=username, email=email, password_hash=pw_hash)
            session.add(user)
            await session.flush()  # populate user.id
            users.append(user)
            print(f"  Created missing user: {username} (email={email})")
    return users


async def populate() -> None:
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        # optionally clear posts only (keeps users intact)
        if CLEAR_EXISTING_POSTS:
            await session.execute(delete(models.Post))
            await session.commit()
            print("Cleared existing posts")

        # ensure users exist (and create missing ones)
        users = await _ensure_users(session)
        await session.commit()  # commit potential new users so posts can FK to them
        if not users:
            print("No users found or created — aborting.")
            return

        print(f"Using users: {[u.username for u in users]}")

        # create NUM_POSTS posts round-robin across users
        posts_to_add = []
        for i in range(NUM_POSTS):
            title, content = _make_post_text(i)
            author = users[i % len(users)]
            # compute a date_posted pattern: oldest ~90 days ago to newest = now
            # Spread posts over ~ (90 days) window similar to tutorial
            days_ago = 90 * (1 - (i / max(1, NUM_POSTS - 1)))  # 90 -> 0
            # add small hour jitter
            hours_offset = (i * 7) % 24
            date_posted = now - timedelta(days=days_ago, hours=hours_offset)
            post = models.Post(
                title=title,
                content=content,
                user_id=author.id,
                date_posted=date_posted,
            )
            posts_to_add.append(post)

        session.add_all(posts_to_add)
        await session.commit()
        print(f"Added {len(posts_to_add)} posts")

    await engine.dispose()
    print("Done. DB connection disposed.")


if __name__ == "__main__":
    asyncio.run(populate())

"""
database seeding script to create test users and posts for development/testing purposes.
-> activate venv
-> python populate_db.py
"""