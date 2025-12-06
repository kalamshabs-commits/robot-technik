if ($env:DATABASE_URL -like "postgresql*") {
    alembic -c /app/alembic.ini upgrade head
}
uvicorn cloud_api.ai_main:app --host 0.0.0.0 --port ($env:PORT ?? 8080)
