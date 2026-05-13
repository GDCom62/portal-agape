#!/bin/bash

# 1. Inicia o Gunicorn na porta interna 8000 em segundo plano (&)
gunicorn -k gevent -w 1 --bind 0.0.0.0:8000 main:app &

# 2. Inicia o Streamlit na porta oficial pública fornecida pelo Railway ($PORT)
streamlit run seu_arquivo_portal.py --server.port $PORT --server.address 0.0.0.0
