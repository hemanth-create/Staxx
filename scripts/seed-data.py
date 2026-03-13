#!/usr/bin/env python3
"""
Seed Development Data for Staxx Intelligence
============================================

Generates realistic mock data for local development:
- Organizations
- Users
- Model versions
- Production calls (cost events)
- Evaluation runs

Usage:
    python scripts/seed-data.py
    # or via Docker:
    docker compose exec backend python scripts/seed-data.py

Environment:
    DATABASE_URL or POSTGRES_* env vars
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from random import choice, gauss, randint, random, uniform

import psycopg
from psycopg import sql


async def main():
    # Database connection
    db_host = os.getenv("POSTGRES_SERVER", "localhost")
    db_user = os.getenv("POSTGRES_USER", "staxx")
    db_pass = os.getenv("POSTGRES_PASSWORD", "staxx_dev_password")
    db_name = os.getenv("POSTGRES_DB", "staxx")
    db_port = os.getenv("POSTGRES_PORT", "5432")

    connstr = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

    print("🌱 Seeding Staxx Intelligence development data...")
    print(f"   Database: {db_name} @ {db_host}:{db_port}")

    async with await psycopg.AsyncConnection.connect(connstr) as conn:
        async with conn.cursor() as cur:
            # ─────────────────────────────────────────────────────────────────
            # Organizations
            # ─────────────────────────────────────────────────────────────────
            orgs = [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Acme Corp",
                    "slug": "acme-corp",
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Techno Labs",
                    "slug": "techno-labs",
                },
            ]

            for org in orgs:
                await cur.execute(
                    """
                    INSERT INTO organizations (id, name, slug, plan)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (org["id"], org["name"], org["slug"], "growth"),
                )

            print(f"✓ Inserted {len(orgs)} organizations")

            # ─────────────────────────────────────────────────────────────────
            # Users (one per org)
            # ─────────────────────────────────────────────────────────────────
            users = []
            for org in orgs:
                user_id = str(uuid.uuid4())
                users.append(
                    {
                        "id": user_id,
                        "org_id": org["id"],
                        "email": f"admin@{org['slug']}.com",
                    }
                )

            for user in users:
                await cur.execute(
                    """
                    INSERT INTO users (id, org_id, email, hashed_password, role, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        user["id"],
                        user["org_id"],
                        user["email"],
                        "$2b$12$abcdef1234567890",  # Mock hashed password
                        "owner",
                        True,
                    ),
                )

            print(f"✓ Inserted {len(users)} users")

            # ─────────────────────────────────────────────────────────────────
            # Model Versions
            # ─────────────────────────────────────────────────────────────────
            models = [
                {
                    "id": str(uuid.uuid4()),
                    "provider_model_id": "gpt-4o",
                    "pricing": {"input": 2.50, "output": 10.00},
                },
                {
                    "id": str(uuid.uuid4()),
                    "provider_model_id": "claude-3-5-sonnet-20240620",
                    "pricing": {"input": 3.00, "output": 15.00},
                },
                {
                    "id": str(uuid.uuid4()),
                    "provider_model_id": "claude-3-haiku-20240307",
                    "pricing": {"input": 0.25, "output": 1.25},
                },
                {
                    "id": str(uuid.uuid4()),
                    "provider_model_id": "gpt-4-turbo",
                    "pricing": {"input": 10.00, "output": 30.00},
                },
            ]

            for model in models:
                await cur.execute(
                    """
                    INSERT INTO model_versions (id, provider_model_id, pricing)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (model["id"], model["provider_model_id"], model["pricing"]),
                )

            print(f"✓ Inserted {len(models)} model versions")

            # ─────────────────────────────────────────────────────────────────
            # Production Calls (Cost Events)
            # ─────────────────────────────────────────────────────────────────
            task_types = [
                "summarization",
                "classification",
                "extraction",
                "code_generation",
                "qa",
            ]

            call_count = 0
            now = datetime.now(timezone.utc)
            start_date = now - timedelta(days=30)

            for day_offset in range(30):
                current_date = start_date + timedelta(days=day_offset)
                calls_per_day = randint(10, 30)

                for _ in range(calls_per_day):
                    call_id = str(uuid.uuid4())
                    model = choice(models)
                    task_type = choice(task_types)

                    # Realistic token counts
                    input_tokens = int(gauss(300, 100))
                    output_tokens = int(gauss(150, 50))

                    # Calculate realistic cost
                    input_cost = (input_tokens / 1_000_000) * model["pricing"]["input"]
                    output_cost = (output_tokens / 1_000_000) * model["pricing"][
                        "output"
                    ]
                    cost = input_cost + output_cost

                    # Realistic latency (ms)
                    latency = max(50, int(gauss(500, 200)))

                    # Random timestamp within the day
                    ts = current_date + timedelta(hours=random() * 24)

                    await cur.execute(
                        """
                        INSERT INTO production_calls (id, ts, model_version_id, task_type, cost_usd, latency_ms)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (call_id, ts, model["id"], task_type, cost, latency),
                    )

                    call_count += 1

            print(f"✓ Inserted {call_count} production calls")

            # ─────────────────────────────────────────────────────────────────
            # Evaluation Runs (Shadow Evals)
            # ─────────────────────────────────────────────────────────────────
            eval_count = 0

            # For each pair of models and task type, create N=20 eval runs
            model_pairs = [
                (models[0], models[2]),  # GPT-4o vs Claude Haiku
                (models[1], models[2]),  # Claude Opus vs Claude Haiku
            ]

            for model_a, model_b in model_pairs:
                for task_type in task_types[:2]:  # Just 2 task types for brevity
                    for run_num in range(20):
                        eval_id = str(uuid.uuid4())
                        prompt_hash = f"{task_type}_{run_num}"

                        # Model B metrics (the candidate)
                        input_toks = int(gauss(250, 80))
                        output_toks = int(gauss(120, 40))

                        await cur.execute(
                            """
                            INSERT INTO eval_runs (
                                id, model_version_id, task_type, prompt_hash,
                                input_tokens, output_tokens, latency_ms, cost_usd,
                                json_valid, n_run
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                eval_id,
                                model_b["id"],
                                task_type,
                                prompt_hash,
                                input_toks,
                                output_toks,
                                int(gauss(300, 100)),  # latency
                                (input_toks / 1e6) * model_b["pricing"]["input"]
                                + (output_toks / 1e6) * model_b["pricing"]["output"],
                                True,  # json_valid
                                run_num + 1,
                            ),
                        )

                        eval_count += 1

            print(f"✓ Inserted {eval_count} evaluation runs")

            # Commit transaction
            await conn.commit()

    print("\n✨ Seed data loaded successfully!")
    print(f"   Organizations: {len(orgs)}")
    print(f"   Users: {len(users)}")
    print(f"   Models: {len(models)}")
    print(f"   Production calls: {call_count}")
    print(f"   Eval runs: {eval_count}")
    print("\n🚀 Ready for development. Start with: make up")


if __name__ == "__main__":
    asyncio.run(main())
