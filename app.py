import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, base64, json

# --- 1. ESTILO FACEBOOK / ALTO CONTRASTE ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

def aplicar_estilo_facebook():
    st.markdown("""
        <style>
        html, body, [class*="st-"] { font-family: Arial, sans-serif !important; }
        .stApp { background-color: #f0f2f5; }
        p, span, label { color: #000000 !important; font-size: 20px !important; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; }
        [data-testid="stSidebar"] * { color: #ffffff !important; }
        .card-post { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #ced0d4; }
        .palavra-destaque { background: linear-gradient(135deg, #1877f2, #0054ca); color: white !important; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
        .texto-biblico { font-size: 28px !important; color: #000000 !important; line-height: 1.6; }
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
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, conteudo TEXT, img_data TEXT, urgente INTEGER DEFAULT 0, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT, usuario TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')

init_db()

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    aplicar_estilo_facebook()
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown("<h1 style='color:#1877f2; text-align:center;'>facebook</h1>", unsafe_allow_html=True)
        with st.form("login"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Credenciais inválidas.")
else:
    u = st.session_state.user
    aplicar_estilo_facebook()
    
    with st.sidebar:
        if os.path.exists("logo.png"):
            with open("logo.png", "rb") as f:
                data = base64.b64encode(f.read()).decode()
                st.markdown(f'<p align="center"><img src="data:image/png;base64,{data}" width="120"></p>', unsafe_allow_html=True)
        st.markdown(f"### 👤 {u['nome']}")
        menu = st.radio("Menu", ["🏠 Feed", "📖 Bíblia", "🤝 Ofertas PIX", "💰 Financeiro"])
        adm = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if adm and st.button("📥 Importar acf.json"):
            if os.path.exists("acf.json"):
                with open("acf.json", "r", encoding="utf-8") as f:
                    data = json.load(f); executar_query("DELETE FROM biblia")
                    for livro in data:
                        for i, cap in enumerate(livro['chapters']):
                            for j, texto in enumerate(cap):
                                executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l, :c, :v, :t)", {"l": livro['name'], "c": i+1, "v": j+1, "t": texto})
                st.success("Bíblia Carregada!")
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # --- MENU: FEED (MURAL + PALAVRA DO DIA) ---
    if menu == "🏠 Feed":
        st.title("Mural da Igreja")
        col_f, col_d = st.columns([2, 1])

        with col_f:
            # APENAS ADMIN POSTA
            if adm:
                with st.container():
                    st.markdown('<div class="card-post">', unsafe_allow_html=True)
                    with st.form("post_admin", clear_on_submit=True):
                        txt = st.text_area("No que você está pensando, Admin?")
                        foto = st.file_uploader("Anexar Imagem (Admin)", type=['jpg', 'png', 'jpeg'])
                        if st.form_submit_button("Publicar no Mural"):
                            img_str = base64.b64encode(foto.read()).decode() if foto else ""
                            executar_query("INSERT INTO avisos (conteudo, img_data, data) VALUES (:c,:i,:d)",
                                           {"c":txt, "i":img_str, "d":datetime.now().strftime("%d/%m/%Y %H:%M")})
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

            # LISTA DE RECADOS
            posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, p in posts.iterrows():
                st.markdown(f'<div class="card-post"><b>Igreja Ágape</b> • <small>{p["data"]}</small><br><br>{p["conteudo"]}</div>', unsafe_allow_html=True)
                if p['img_data']:
                    st.image(base64.b64decode(p['img_data']), use_container_width=True)
                if adm:
                    if st.button(f"🗑️ Excluir #{p['id']}", key=f"del_{p['id']}"):
                        executar_query("DELETE FROM avisos WHERE id=:id", {"id":p['id']}); st.rerun()

        with col_d:
            # PALAVRA DO DIA
            st.markdown("### ✨ Palavra do Dia")
            res_b = consultar_db("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not res_b.empty:
                b = res_b.iloc[0]
                st.markdown(f"""
                    <div class="palavra-destaque">
                        <p style='font-style:italic; font-size:22px !important; color:white !important;'>"{b['texto']}"</p>
                        <b style='color:#ffd700'>{b['livro']} {b['cap']}:{b['ver']}</b>
                    </div>
                """, unsafe_allow_html=True)

    # --- MENU: BÍBLIA ---
    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        res_l = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not res_l.empty:
            l_sel = st.selectbox("Selecione o Livro", res_l['livro'].tolist())
            res_c = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l ORDER BY cap", {"l":l_sel})
            c_sel = st.selectbox("Capítulo", res_c['cap'].tolist())
            
            st.markdown('<div class="card-post">', unsafe_allow_html=True)
            versos = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c ORDER BY ver", {"l":l_sel, "c":c_sel})
            for _, v in versos.iterrows():
                st.markdown(f'<p class="texto-biblico"><b>{v["ver"]}</b> {v["texto"]}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else: st.warning("Importe a Bíblia no menu lateral (Modo Admin).")

    # --- MENU: FINANCEIRO ---
    elif menu == "💰 Financeiro":
        st.title("💰 Gestão Financeira")
        if adm:
            with st.expander("Lançar Ativo / Passivo / Entrada / Saída"):
                with st.form("fin_adm"):
                    id_ed = st.number_input("ID p/ editar (0=novo)", 0)
                    desc, val = st.text_input("Descrição"), st.number_input("Valor", 0.0)
                    tipo = st.selectbox("Tipo", ["Entrada", "Saída", "Ativo", "Passivo"])
                    if st.form_submit_button("Salvar"):
                        if id_ed == 0: executar_query("INSERT INTO financeiro (descricao, valor, tipo, data, usuario) VALUES (:d,:v,:t,:dt,'Admin')", {"d":desc,"v":val,"t":tipo,"dt":datetime.now().strftime("%d/%m/%Y")})
                        else: executar_query("UPDATE financeiro SET descricao=:d, valor=:v, tipo=:t WHERE id=:id", {"d":desc,"v":val,"t":tipo,"id":id_ed})
                        st.rerun()
        
        df = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
        st.table(df)
        e, s = df[df['tipo']=='Entrada']['valor'].sum(), df[df['tipo']=='Saída']['valor'].sum()
        st.metric("Saldo em Caixa", f"R$ {e-s:,.2f}")

    # --- MENU: OFERTAS PIX ---
    elif menu == "🤝 Ofertas PIX":
        st.title("🤝 Dízimos e Ofertas")
        st.info("Chave PIX: **financeiro@igrejaagape.com**")
        with st.form("pix"):
            valor = st.number_input("Valor (R$)", 1.0)
            tipo_o = st.selectbox("Tipo", ["Dízimo", "Oferta"])
            if st.form_submit_button("Informar Doação"):
                executar_query("INSERT INTO financeiro (descricao, valor, tipo, data, usuario) VALUES (:d,:v,:t,:dt,:u)",
                               {"d":f"{tipo_o} de {u['nome']}", "v":valor, "t":"Entrada", "dt":datetime.now().strftime("%d/%m/%Y"), "u":u['nome']})
                st.success("Doação registrada com sucesso!")
