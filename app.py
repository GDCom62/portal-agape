import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, io, re, unicodedata

# --- 1. CONFIGURAÇÕES E ESTILO "FACEBOOK" ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

def aplicar_estilo_facebook():
    st.markdown("""
        <style>
        /* Fundo clássico do FB */
        .stApp { background-color: #f0f2f5; }
        
        /* Cabeçalhos */
        h1, h2, h3 { color: #1c1e21; font-family: 'Segoe UI', Helvetica, Arial, sans-serif; text-align: left; }
        
        /* Card de Postagem (Estilo Mural) */
        .card-post { 
            background: white; 
            padding: 16px; 
            border-radius: 8px; 
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1); 
            margin-bottom: 16px;
            border: 1px solid #dddfe2;
        }
        
        /* Input de texto estilo "No que você está pensando?" */
        .stTextArea textarea { border-radius: 20px !important; background-color: #f0f2f5 !important; }
        
        /* Botões Estilo FB */
        .stButton>button { 
            background-color: #1877f2 !important; 
            color: white !important; 
            border-radius: 6px !important;
            font-weight: bold !important;
            border: none !important;
            width: 100%;
        }
        
        /* Sidebar Personalizada */
        [data-testid="stSidebar"] { background-color: white !important; border-right: 1px solid #dddfe2; }
        
        /* Palavra do dia estilo "Destaque" */
        .palavra-destaque {
            background: linear-gradient(135deg, #1877f2, #0054ca);
            color: white !important;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
            font-size: 20px;
            font-weight: 500;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS (Mantido igual) ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, img_data TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

# --- 3. LOGICA DE INTERFACE ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    aplicar_estilo_facebook()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<h1 style='color: #1877f2; text-align: center; font-size: 40px;'>facebook</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center;'>Portal Ágape</h4>", unsafe_allow_html=True)
        with st.container():
            e = st.text_input("Email ou telefone")
            s = st.text_input("Senha", type="password")
            if st.button("Entrar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                else:
                    st.error("Credenciais incorretas.")
            st.markdown("---")
            if st.button("Criar nova conta", key="btn_cad"):
                st.info("Função de cadastro simplificada no banco.")

else:
    u = st.session_state.user
    aplicar_estilo_facebook()
    
    # Sidebar Estilo Menu Lateral do FB
    with st.sidebar:
        st.markdown(f"### 👤 {u['nome']}")
        menu = st.radio("Navegação", ["🏠 Feed de Notícias", "📖 Bíblia Sagrada", "👥 Membros", "⚙️ Configurações"])
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    if menu == "🏠 Feed de Notícias":
        col_feed, col_extra = st.columns([2, 1])
        
        with col_feed:
            # "No que você está pensando?"
            if u['is_admin'] == 1:
                with st.container():
                    st.markdown('<div class="card-post">', unsafe_allow_html=True)
                    with st.form("post_fb", clear_on_submit=True):
                        txt = st.text_area("", placeholder=f"No que você está pensando, {u['nome']}?")
                        foto = st.file_uploader("Adicionar foto", type=['jpg','png'])
                        if st.form_submit_button("Publicar"):
                            img = base64.b64encode(foto.read()).decode() if foto else ""
                            executar_query("INSERT INTO avisos (titulo, conteudo, img_data, data) VALUES ('Post', :c, :i, :d)", 
                                           {"c":txt, "i":img, "d":datetime.now().strftime("%d/%m %H:%M")})
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

            # Lista de Posts
            avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, av in avisos.iterrows():
                st.markdown(f"""
                    <div class="card-post">
                        <b style="color: #1c1e21;">⛪ Ministério Ágape</b><br>
                        <small style="color: #65676b;">{av['data']}</small>
                        <p style="margin-top: 10px; font-size: 15px;">{av['conteudo']}</p>
                    </div>
                """, unsafe_allow_html=True)
                if av['img_data']:
                    st.image(base64.b64decode(av['img_data']), use_container_width=True)
                st.markdown("<br>", unsafe_allow_html=True)

        with col_extra:
            # Palavra do Dia (Widget Lateral)
            p_res = consultar_db("SELECT livro, cap, ver, texto FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not p_res.empty:
                p = p_res.iloc[0]
                st.markdown(f"""
                    <div class="palavra-destaque">
                        <small>VERSÍCULO DO DIA</small><br>
                        "{p['texto']}"<br>
                        <small>— {p['livro']} {p['cap']}:{p['ver']}</small>
                    </div>
                """, unsafe_allow_html=True)

    elif menu == "📖 Bíblia Sagrada":
        st.title("📖 Bíblia Sagrada")
        st.info("Área de leitura bíblica integrada.")
