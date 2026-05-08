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
        p, span, label { color: #000000 !important; font-size: 19px !important; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; }
        [data-testid="stSidebar"] * { color: #ffffff !important; }
        .card-post { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #ced0d4; }
        .aviso-urgente { background-color: #fa3e3e; color: white !important; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; margin-bottom: 20px; }
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
    
    # Garantir coluna img_data em avisos
    try: consultar_db("SELECT img_data FROM avisos LIMIT 1")
    except: executar_query("ALTER TABLE avisos ADD COLUMN img_data TEXT")

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
else:
    u = st.session_state.user
    aplicar_estilo_facebook()
    
    with st.sidebar:
        st.markdown(f"### 👤 {u['nome']}")
        menu = st.radio("Menu", ["🏠 Feed", "📖 Bíblia", "🤝 Ofertas PIX", "💰 Financeiro"])
        adm = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # --- FEED / MURAL ---
    if menu == "🏠 Feed":
        st.title("Mural da Igreja")
        if adm:
            with st.container():
                st.markdown('<div class="card-post">', unsafe_allow_html=True)
                with st.form("post_mural", clear_on_submit=True):
                    txt = st.text_area("Recado aos membros")
                    foto = st.file_uploader("Anexar Imagem", type=['jpg', 'png', 'jpeg'])
                    urg = st.checkbox("Aviso Urgente")
                    if st.form_submit_button("Publicar"):
                        img_str = base64.b64encode(foto.read()).decode() if foto else ""
                        executar_query("INSERT INTO avisos (conteudo, img_data, urgente, data) VALUES (:c,:i,:u,:d)",
                                       {"c":txt, "i":img_str, "u":1 if urg else 0, "d":datetime.now().strftime("%d/%m/%Y %H:%M")})
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, p in posts.iterrows():
            st.markdown(f'<div class="card-post">', unsafe_allow_html=True)
            if p['urgente']: st.markdown('<span style="color:red">🚨 URGENTE</span>', unsafe_allow_html=True)
            st.markdown(f"<b>Igreja Ágape</b> • <small>{p['data']}</small><br><br>{p['conteudo']}", unsafe_allow_html=True)
            if p['img_data']:
                st.image(base64.b64decode(p['img_data']), use_container_width=True)
            if adm:
                if st.button(f"🗑️ Excluir #{p['id']}", key=f"del_{p['id']}"):
                    executar_query("DELETE FROM avisos WHERE id=:id", {"id":p['id']}); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # --- OFERTAS PIX ---
    elif menu == "🤝 Ofertas PIX":
        st.title("🤝 Ofertas e Dízimos")
        st.markdown('<div class="card-post">', unsafe_allow_html=True)
        st.info("Chave PIX: **financeiro@igrejaagape.com** (Exemplo)")
        with st.form("pix_form"):
            valor = st.number_input("Valor da Doação (R$)", min_value=1.0, step=10.0)
            tipo_d = st.selectbox("Tipo", ["Oferta", "Dízimo", "Missões"])
            if st.form_submit_button("Confirmar Doação Realizada"):
                executar_query("INSERT INTO financeiro (descricao, valor, tipo, data, usuario) VALUES (:d,:v,:t,:dt,:u)",
                               {"d":f"{tipo_d} de {u['nome']}", "v":valor, "t":"Entrada", "dt":datetime.now().strftime("%d/%m/%Y"), "u":u['nome']})
                st.success("Obrigado! Sua oferta foi registrada no sistema.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- FINANCEIRO ---
    elif menu == "💰 Financeiro":
        st.title("💰 Gestão Financeira")
        if adm:
            with st.expander("Lançar Ativos / Passivos / Despesas"):
                with st.form("fin_adm"):
                    desc = st.text_input("Descrição do Item")
                    val = st.number_input("Valor", 0.0)
                    tipo = st.selectbox("Tipo de Lançamento", ["Entrada", "Saída", "Ativo (Patrimônio)", "Passivo (Dívida)"])
                    dt_f = st.text_input("Data", datetime.now().strftime("%d/%m/%Y"))
                    if st.form_submit_button("Gravar"):
                        executar_query("INSERT INTO financeiro (descricao, valor, tipo, data, usuario) VALUES (:d,:v,:t,:dt,'Admin')",
                                       {"d":desc, "v":val, "t":tipo, "dt":dt_f})
                        st.rerun()
        
        df = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
        st.table(df)
        
        # Resumo
        ent = df[df['tipo']=='Entrada']['valor'].sum()
        sai = df[df['tipo']=='Saída']['valor'].sum()
        st.metric("Saldo em Caixa", f"R$ {ent - sai:,.2f}")

    elif menu == "📖 Bíblia":
        # (Lógica da Bíblia mantida como nos turnos anteriores)
        st.title("📖 Bíblia Sagrada")
        # ... (código da bíblia)
