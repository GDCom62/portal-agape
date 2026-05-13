#!/bin/bash

# 1. Inicia sua API/Chat na porta interna 8000 (em segundo plano)
gunicorn -k gevent -w 1 --bind 0.0.0.0:8000 main:app &

# 2. Inicia o Portal Streamlit na porta pública obrigatória do Railway ($PORT)
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
