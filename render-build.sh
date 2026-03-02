#!/usr/bin/env bash
exit on error
set -o errexit

pip install -r requirements.txt

# Criar as tabelas no banco de dados do servidor
python -c "from app import app, db; with app.app_context(): db.create_all()"
