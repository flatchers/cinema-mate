#!/usr/bin/env bash

echo "Run apply migration.."
alembic upgrade head
echo "Migrations applied!"

exec "$@"