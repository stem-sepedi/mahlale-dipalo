#!/usr/bin/env python3
"""Seed script — creates an admin user and test concept in the database."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.middleware.jwt import hash_password


async def seed():
    import asyncpg

    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)

    # Create admin user
    admin_hash = hash_password("admin123")
    try:
        await pool.execute(
            "INSERT INTO users (username, password_hash, role) VALUES ($1, $2, 'admin') ON CONFLICT (username) DO NOTHING",
            "admin", admin_hash,
        )
        print("Admin user created (username: admin, password: admin123)")
    except Exception as exc:
        print(f"Admin user: {exc}")

    # Create test concepts
    concepts = [
        ("Photosynthesis", "The process by which plants convert light energy into chemical energy.", "Biology", [5, 8, 10]),
        ("Gravity", "The force of attraction between objects with mass.", "Physics", [8, 10, 12]),
        ("Mitosis", "A type of cell division that produces two identical daughter cells.", "Biology", [10, 11, 12]),
        ("Periodic Table", "A tabular arrangement of chemical elements by atomic number.", "Chemistry", [9, 10, 11]),
        ("Ecosystem", "A community of living organisms interacting with their environment.", "Biology", [5, 7, 9]),
    ]

    for name, definition, domain, grades in concepts:
        try:
            await pool.execute(
                """INSERT INTO concepts (name_en, definition_en, domain, grade_levels, status, created_by)
                   VALUES ($1, $2, $3, $4, 'published', NULL)
                   ON CONFLICT DO NOTHING""",
                name, definition, domain, grades,
            )
            print(f"Concept created: {name}")
        except Exception as exc:
            print(f"Concept {name}: {exc}")

    await pool.close()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
