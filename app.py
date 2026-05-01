import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64

# --- 1. CONFIGURAÇÕES E ESTILO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    h1, h2, h3 { color: #1e3a8a !important; text-align: center; }
    .card-flutuante {
        background-color: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 15px;
        border-left: 5px solid #1e3a8a;
    }
    .chat-bubble {
        padding: 10px; border-radius: 15px; margin-bottom: 10px; max-width: 75%;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05); font-family: sans-serif;
    }
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
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT, img_data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, codigo_doador TEXT, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, nome TEXT, texto TEXT, data TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

def logo_central(largura):
    if os.path.exists(URL_LOGO):
        with open(URL_LOGO, "rb") as f:
            data = base64.b64encode(f.read()).decode()
            st.markdown(f'<p align="center"><img src="data:image/png;base64,{data}" width="{largura}"></p>', unsafe_allow_html=True)

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    _, col_c, _ = st.columns([1, 1.5, 1])
    with col_c:
        logo_central(180)
        t_l, t_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_l:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar Portal", use_container_width=True):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                        st.rerun()
                    st.error("Credenciais incorretas.")
        with t_c:
            with st.form("cad", clear_on_submit=True):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Conta", use_container_width=True):
                    if n and em and se:
                        c = "AG-" + "".join(random.choices(string.digits, k=4))
                        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n,:e,:c,:p,0)", {"n":n,"e":em,"c":c,"p":generate_password_hash(se)})
                        st.success(f"Conta criada! Código: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    with st.sidebar:
        logo_central(100)
        st.markdown(f"<p style='text-align: center;'>🙏 <b>{u['nome']}</b><br><small>Cód: {u['codigo']}</small></p>", unsafe_allow_html=True)
        menu = st.radio("Menu", ["📢 Mural", "🎥 Bate-papo", "💰 Financeiro", "🎁 Doações"])
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.logado = False; st.rerun()

    if admin_mode:
        st.title("⚙️ Administração")
        t_m, t_f, t_chat = st.tabs(["📢 Mural", "💰 Finanças", "💬 Chat"])
        
        with t_m:
            st.subheader("Novo Aviso no Mural")
            with st.form("mural_form", clear_on_submit=True):
                tit = st.text_input("Título")
                cont = st.text_area("Conteúdo")
                if st.form_submit_button("Publicar"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)", 
                                  {"t": tit, "c": cont, "d": datetime.now().strftime("%d/%m/%Y")})
                    st.success("Publicado!")

        with t_f:
            st.subheader("Registrar Movimentação")
            with st.form("f_fin", clear_on_submit=True):
                cod = st.text_input("Código do Membro")
                desc = st.text_input("Descrição")
                val = st.number_input("Valor", min_value=0.0)
                tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (codigo_doador, descricao, valor, tipo, data) VALUES (:c,:d,:v,:t,:dt)", 
                                  {"c":cod if cod else "IGREJA", "d":desc, "v":val, "t":tipo, "dt":datetime.now().strftime("%Y-%m-%d")})
                    st.success("Lançado!")

        with t_chat:
            if st.button("Limpar Histórico do Chat"):
                executar_query("DELETE FROM mensagens")
                st.rerun()

    else:
        if menu == "📢 Mural":
            st.title("📢 Mural de Avisos")
            avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, av in avisos.iterrows():
                st.markdown(f"""<div class="card-flutuante"><h4>{av['titulo']}</h4><p>{av['conteudo']}</p><small>{av['data']}</small></div>""", unsafe_allow_html=True)

        elif menu == "🎥 Bate-papo":
            st.title("🎥 Bate-papo")
            chat_container = st.container(height=400)
            df_msg = consultar_db("SELECT nome, texto, data FROM mensagens ORDER BY id ASC")
            with chat_container:
                for _, row in df_msg.iterrows():
                    is_me = row['nome'] == u['nome']
                    align, color = ("flex-end", "#dcf8c6") if is_me else ("flex-start", "#ffffff")
                    st.markdown(f'<div style="display: flex; flex-direction: column; align-items: {align};"><div class="chat-bubble" style="background-color: {color};"><b>{row["nome"]}</b><br>{row["texto"]}<br><small style="color:gray">{row["data"]}</small></div></div>', unsafe_allow_html=True)
            
            with st.form("send", clear_on_submit=True):
                c1, c2 = st.columns([0.8, 0.2])
                txt = c1.text_input("Mensagem", label_visibility="collapsed")
                if c2.form_submit_button("Enviar") and txt:
                    executar_query("INSERT INTO mensagens (nome, texto, data) VALUES (:n, :t, :d)", {"n": u['nome'], "t": txt, "d": datetime.now().strftime("%H:%M")})
                    st.rerun()

        elif menu == "💰 Financeiro":
            st.title("💰 Financeiro")
            df = consultar_db("SELECT * FROM financeiro WHERE codigo_doador = :c OR :a = 1", {"c": u['codigo'], "a": u['is_admin']})
            st.dataframe(df, use_container_width=True)
