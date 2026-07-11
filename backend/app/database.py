import json
import os
import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parent.parent / "listing_agent.db"


def get_db_path() -> Path:
    configured_path = os.getenv("LISTING_AGENT_DB_PATH", "").strip()
    return Path(configured_path) if configured_path else DB_PATH


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(get_db_path())
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS listing_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                target_market TEXT NOT NULL,
                target_language TEXT NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_listing_run(request_payload: dict[str, Any], response_payload: dict[str, Any]) -> dict[str, Any]:
    product = request_payload["product"]
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO listing_runs (
                product_name,
                target_market,
                target_language,
                request_json,
                response_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                product.get("name", ""),
                product.get("target_market", ""),
                product.get("target_language", ""),
                json.dumps(request_payload, ensure_ascii=False),
                json.dumps(response_payload, ensure_ascii=False),
            ),
        )
        response_payload["id"] = int(cursor.lastrowid)
        connection.execute(
            "UPDATE listing_runs SET response_json = ? WHERE id = ?",
            (json.dumps(response_payload, ensure_ascii=False), response_payload["id"]),
        )
    return response_payload


def list_runs() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, product_name, target_market, target_language, response_json, created_at
            FROM listing_runs
            ORDER BY id DESC
            LIMIT 50
            """
        ).fetchall()
    return [
        {
            "id": row["id"],
            "product_name": row["product_name"],
            "target_market": row["target_market"],
            "target_language": row["target_language"],
            "response": json.loads(row["response_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def clear_runs() -> dict[str, int]:
    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM listing_runs")
    return {"deleted": cursor.rowcount}
