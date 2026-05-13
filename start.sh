#!/bin/bash

# 1. Inicia a API/Gunicorn em segundo plano na porta interna 8000
gunicorn -k gevent -w 1 --bind 0.0.0.0:8000 main:app &

# 2. Inicia o Streamlit na porta pública do Railway
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
