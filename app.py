import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, base64, json

# --- 1. CONFIGURAÇÕES E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

def aplicar_estilo_facebook():
    st.markdown("""
        <style>
        html, body, [class*="st-"] { font-family: Arial, sans-serif !important; }
        .stApp { background-color: #f0f2f5; }
        p, span, label { color: #000000 !important; font-size: 18px !important; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; }
        [data-testid="stSidebar"] * { color: #ffffff !important; }
        .card-post { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 15px; border: 1px solid #ced0d4; height: 100%; }
        .palavra-destaque { background: linear-gradient(135deg, #1877f2, #0054ca); color: white !important; padding: 20px; border-radius: 10px; text-align: center; }
        </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, conteudo TEXT, img_data TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT, usuario TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome TEXT, pedido TEXT, status TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS eventos (id INTEGER PRIMARY KEY, titulo TEXT, dia_semana TEXT, hora TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    aplicar_estilo_facebook()
    _, col_l, _ = st.columns([1, 1.2, 1])
    with col_l:
        st.markdown("<h1 style='color:#1877f2; text-align:center;'>facebook</h1>", unsafe_allow_html=True)
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()

else:
    u = st.session_state.user
    aplicar_estilo_facebook()
    
    with st.sidebar:
        st.markdown(f"### 👤 {u['nome']}")
        menu = st.radio("Menu", ["🏠 Feed", "📅 Agenda", "📖 Bíblia", "🙏 Orações", "🤝 Ofertas", "💰 Financeiro"])
        adm = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # --- FEED / MURAL ---
    if menu == "🏠 Feed":
        st.title("Mural da Igreja")
        if adm:
            with st.expander("📝 Nova Publicação"):
                with st.form("post_admin", clear_on_submit=True):
                    txt = st.text_area("Texto do recado")
                    foto = st.file_uploader("Foto", type=['jpg', 'png', 'jpeg'])
                    if st.form_submit_button("Publicar"):
                        img = base64.b64encode(foto.read()).decode() if foto else ""
                        executar_query("INSERT INTO avisos (conteudo, img_data, data) VALUES (:c,:i,:d)", 
                                       {"c":txt, "i":img, "d":datetime.now().strftime("%d/%m/%Y %H:%M")})
                        st.rerun()

        posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        # Lógica para 3 colunas (horizontal)
        for i in range(0, len(posts), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(posts):
                    p = posts.iloc[i + j]
                    with cols[j]:
                        st.markdown(f'<div class="card-post"><b>Igreja Ágape</b><br><small>{p["data"]}</small><br><p>{p["conteudo"]}</p></div>', unsafe_allow_html=True)
                        if p['img_data']:
                            st.image(base64.b64decode(p['img_data']), use_container_width=True)
                        if adm:
                            if st.button(f"🗑️ Excluir #{p['id']}", key=f"del_{p['id']}"):
                                executar_query("DELETE FROM avisos WHERE id=:id", {"id":p['id']}); st.rerun()

    # --- ORAÇÕES ---
    elif menu == "🙏 Orações":
        st.title("🙏 Pedidos de Oração")
        with st.form("ped_or"):
            p_txt = st.text_area("Seu pedido de oração (Enviado para os pastores)")
            if st.form_submit_button("Enviar Pedido"):
                executar_query("INSERT INTO oracoes (nome, pedido, status, data) VALUES (:n,:p,'Pendente',:d)",
                               {"n":u['nome'], "p":p_txt, "d":datetime.now().strftime("%d/%m/%Y")})
                st.success("Pedido enviado! Estaremos orando por você.")

        if adm:
            st.subheader("📋 Pedidos Recebidos (Admin)")
            lista_or = consultar_db("SELECT * FROM oracoes ORDER BY id DESC")
            for _, o in lista_or.iterrows():
                cor = "green" if o['status'] == 'Orado' else "red"
                st.markdown(f"**De: {o['nome']}** - {o['data']} <span style='color:{cor}'>[{o['status']}]</span>", unsafe_allow_html=True)
                st.write(o['pedido'])
                if o['status'] == 'Pendente' and st.button(f"Marcar como Orado #{o['id']}"):
                    executar_query("UPDATE oracoes SET status='Orado' WHERE id=:id", {"id":o['id']}); st.rerun()
                st.divider()

    # --- FINANCEIRO ---
    elif menu == "💰 Financeiro":
        st.title("💰 Financeiro")
        if adm:
            with st.expander("Lançar"):
                with st.form("fin"):
                    desc, v, t = st.text_input("Descrição"), st.number_input("Valor", 0.0), st.selectbox("Tipo", ["Entrada", "Saída", "Ativo", "Passivo"])
                    if st.form_submit_button("Gravar"):
                        executar_query("INSERT INTO financeiro (descricao, valor, tipo, data, usuario) VALUES (:d,:v,:t,:dt,:u)",
                                       {"d":desc, "v":v, "t":t, "dt":datetime.now().strftime("%d/%m/%Y"), "u":"Admin"})
                        st.rerun()
        df = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
        st.table(df)
