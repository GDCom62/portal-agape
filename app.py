import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json, os, base64, re

# --- 1. CONFIGURAÇÕES ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v40.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS recados (id INTEGER PRIMARY KEY, de_nome TEXT, para_nome TEXT, mensagem TEXT, data TEXT, lido INTEGER DEFAULT 0)')
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN / CADASTRO (Simplificado para o código não ficar gigante) ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
    if st.button("Entrar"):
        res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
        if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
            st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
            st.rerun()
        else: st.error("Erro no login.")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    menu = st.sidebar.radio("Navegação", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo", "💰 Financeiro"])
    if st.sidebar.button("Sair"): st.session_state.logado = False; st.rerun()

    if menu == "🎥 Bate-papo":
        st.title("🎥 Vídeo Chamada Direta")
        membros = consultar_db("SELECT nome FROM membros WHERE nome != :eu", {"eu": u['nome']})
        contato = st.selectbox("Com quem deseja falar?", ["Selecione..."] + list(membros['nome']))
        
        if contato != "Selecione...":
            # --- LIMPEZA CRÍTICA DO NOME DA SALA ---
            # Removemos TUDO que não for letra ou número e limitamos o tamanho
            n1 = re.sub(r'[^a-zA-Z0-9]', '', u['nome']).lower()[:10]
            n2 = re.sub(r'[^a-zA-Z0-9]', '', contato).lower()[:10]
            
            # Criamos a sala garantindo a BARRA '/' entre o domínio e o nome
            sala_nome = f"Agape_{min(n1, n2)}_{max(n1, n2)}"
            url_final = f"https://jit.si{sala_nome}"
            
            st.success(f"Sala gerada para: {u['nome']} e {contato}")
            
            # Botão que abre em nova aba (Resolve erro de IP e Câmera)
            st.link_button("🟢 CLIQUE AQUI PARA INICIAR VÍDEO", url_final)
            
            st.info("Ao clicar no botão acima, a chamada abrirá em uma nova aba para funcionar no celular.")
            
            # Iframe apenas como visualização secundária
            st.markdown(f'<iframe src="{url_final}" allow="camera; microphone; fullscreen" style="height:400px; width:100%; border:0;"></iframe>', unsafe_allow_html=True)

    elif menu == "📢 Mural":
        st.title("📢 Mural")
        # Mostra avisos do banco...
        st.write("Avisos e Palavra do dia aparecem aqui.")

    elif menu == "💰 Financeiro":
        st.title("💰 Financeiro")
        df = consultar_db("SELECT * FROM financeiro")
        st.table(df)
