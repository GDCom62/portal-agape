import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, base64, json

# --- 1. CONFIGURAÇÕES E ESTILO FACEBOOK UI ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

def aplicar_estilo_facebook():
    st.markdown("""
        <style>
        html, body, [class*="st-"] { font-family: Arial, sans-serif !important; }
        .stApp { background-color: #f0f2f5; }
        p, span, label { color: #000000 !important; font-size: 19px !important; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; }
        [data-testid="stSidebar"] * { color: #ffffff !important; font-size: 18px !important; }
        .card-post { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #ced0d4; min-height: 250px; }
        .palavra-destaque { background: linear-gradient(135deg, #1877f2, #0054ca); color: white !important; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
        .texto-biblico { font-size: 28px !important; color: #000000 !important; line-height: 1.6; }
        .event-card { border-left: 8px solid #1877f2; padding-left: 20px; }
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
                st.error("Credenciais incorretas.")
else:
    u = st.session_state.user
    aplicar_estilo_facebook()
    
    with st.sidebar:
        if os.path.exists("logo.png"):
            with open("logo.png", "rb") as f:
                data_img = base64.b64encode(f.read()).decode()
                st.markdown(f'<p align="center"><img src="data:image/png;base64,{data_img}" width="120"></p>', unsafe_allow_html=True)
        st.markdown(f"### 👤 {u['nome']}")
        
        # Notificação de Orações para Admin
        label_or = "🙏 Orações"
        if u['is_admin']:
            pendentes = consultar_db("SELECT COUNT(*) as total FROM oracoes WHERE status='Pendente'").iloc[0]['total']
            if pendentes > 0: label_or = f"🙏 Orações ({pendentes} 🔴)"

        menu = st.radio("Menu", ["🏠 Feed", "📅 Agenda", "📖 Bíblia", label_or, "🤝 Ofertas", "💰 Financeiro"])
        adm = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        
        if adm:
            if st.button("📥 Importar acf.json"):
                if os.path.exists("acf.json"):
                    with open("acf.json", "r", encoding="utf-8") as f:
                        data_bib = json.load(f); executar_query("DELETE FROM biblia")
                        for livro in data_bib:
                            for i, cap in enumerate(livro['chapters']):
                                for j, txt in enumerate(cap):
                                    executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l,:c,:v,:t)", {"l":livro['name'], "c":i+1, "v":j+1, "t":txt})
                    st.success("Bíblia carregada!")
            
            csv = consultar_db("SELECT nome, email FROM membros").to_csv(index=False).encode('utf-8')
            st.download_button("👥 Exportar Membros", csv, "membros.csv", "text/csv")
        
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # --- MENU: FEED ---
    if menu == "🏠 Feed":
        st.title("Mural da Igreja")
        col_f, col_d = st.columns([0.7, 0.3])
        with col_f:
            if adm:
                with st.expander("📝 Nova Publicação Admin"):
                    with st.form("f_post", clear_on_submit=True):
                        txt = st.text_area("Texto")
                        pic = st.file_uploader("Foto", type=['jpg','png','jpeg'])
                        if st.form_submit_button("Publicar"):
                            img_s = base64.b64encode(pic.read()).decode() if pic else ""
                            executar_query("INSERT INTO avisos (conteudo, img_data, data) VALUES (:c,:i,:d)", {"c":txt,"i":img_s,"d":datetime.now().strftime("%d/%m %H:%M")})
                            st.rerun()
            posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for i in range(0, len(posts), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i+j < len(posts):
                        p = posts.iloc[i+j]
                        with cols[j]:
                            st.markdown(f'<div class="card-post"><b>Igreja Ágape</b><br><small>{p["data"]}</small><br><p>{p["conteudo"]}</p></div>', unsafe_allow_html=True)
                            if p['img_data']: st.image(base64.b64decode(p['img_data']), use_container_width=True)
                            if adm: 
                                if st.button(f"🗑️ #{p['id']}", key=f"d_{p['id']}"): executar_query("DELETE FROM avisos WHERE id=:id",{"id":p['id']}); st.rerun()
        with col_d:
            st.markdown("### ✨ Palavra do Dia")
            res_b = consultar_db("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not res_b.empty:
                b = res_b.iloc[0]
                st.markdown(f'<div class="palavra-destaque"><p>"{b["texto"]}"</p><b>{b["livro"]} {b["cap"]}:{b["ver"]}</b></div>', unsafe_allow_html=True)

    # --- MENU: AGENDA ---
    elif menu == "📅 Agenda":
        st.title("📅 Programação")
        if adm:
            with st.form("f_ag"):
                t, d = st.text_input("Evento"), st.selectbox("Dia", ["Domingo","Segunda","Terça","Quarta","Quinta","Sexta","Sábado"])
                h = st.text_input("Hora")
                if st.form_submit_button("Salvar"):
                    executar_query("INSERT INTO eventos (titulo, dia_semana, hora) VALUES (:t,:d,:h)", {"t":t,"d":d,"h":h}); st.rerun()
        for _, ev in consultar_db("SELECT * FROM eventos").iterrows():
            st.markdown(f'<div class="card-post event-card"><b>{ev["dia_semana"]} às {ev["hora"]}</b><br>{ev["titulo"]}</div>', unsafe_allow_html=True)

    # --- MENU: BÍBLIA ---
    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        livros = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not livros.empty:
            l = st.selectbox("Livro", livros['livro'].tolist())
            caps = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":l})
            c = st.selectbox("Capítulo", caps['cap'].tolist())
            st.markdown('<div class="card-post">', unsafe_allow_html=True)
            for _, v in consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c", {"l":l,"c":c}).iterrows():
                st.markdown(f'<p class="texto-biblico"><b>{v["ver"]}</b> {v["texto"]}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- MENU: ORAÇÕES ---
    elif "Orações" in menu:
        st.title("🙏 Orações")
        with st.form("f_or"):
            p = st.text_area("Pedido")
            if st.form_submit_button("Enviar"):
                executar_query("INSERT INTO oracoes (nome, pedido, status, data) VALUES (:n,:p,'Pendente',:d)", {"n":u['nome'],"p":p,"d":datetime.now().strftime("%d/%m")}); st.rerun()
        if adm:
            for _, o in consultar_db("SELECT * FROM oracoes ORDER BY id DESC").iterrows():
                st.markdown(f'<div class="card-post"><b>{o["nome"]}</b>: {o["pedido"]} ({o["status"]})</div>', unsafe_allow_html=True)
                if o['status']=='Pendente' and st.button(f"✅ Orado #{o['id']}"): executar_query("UPDATE oracoes SET status='Orado' WHERE id=:id", {"id":o['id']}); st.rerun()

    # --- MENU: FINANCEIRO ---
    elif menu == "💰 Financeiro":
        st.title("💰 Financeiro")
        if adm:
            with st.form("f_fin"):
                de, va, ti = st.text_input("Descrição"), st.number_input("Valor", 0.0), st.selectbox("Tipo", ["Entrada","Saída","Ativo","Passivo"])
                if st.form_submit_button("Gravar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data, usuario) VALUES (:d,:v,:t,:dt,'Admin')", {"d":de,"v":va,"t":ti,"dt":datetime.now().strftime("%d/%m")}); st.rerun()
        df = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
        st.table(df)
