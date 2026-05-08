import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, base64, json, re, unicodedata

# --- 1. CONFIGURAÇÕES E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

def aplicar_estilo_facebook():
    st.markdown("""
        <style>
        html, body, [class*="st-"], .stMarkdown { font-family: Arial, Helvetica, sans-serif !important; }
        .stApp { background-color: #f0f2f5; }
        p, span, label { color: #000000 !important; font-size: 20px !important; font-weight: 500 !important; }
        .texto-biblico { font-size: 28px !important; color: #000000 !important; line-height: 1.6 !important; margin-bottom: 15px; }
        [data-testid="stSidebar"] { background-color: #1c1e21 !important; }
        [data-testid="stSidebar"] * { color: #ffffff !important; font-size: 19px !important; }
        .card-post { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); margin-bottom: 20px; border: 1px solid #ced0d4; color: black !important; }
        h1, h2, h3 { color: #1877f2 !important; font-weight: bold !important; }
        .palavra-destaque { background: linear-gradient(135deg, #1877f2, #0054ca); color: white !important; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
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
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, conteudo TEXT, img_data TEXT, urgente INTEGER DEFAULT 0, data TEXT)')
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
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown("<h1 style='text-align:center; font-size:45px;'>facebook</h1>", unsafe_allow_html=True)
        with st.form("entrar"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Credenciais incorretas.")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    aplicar_estilo_facebook()
    
    with st.sidebar:
        if os.path.exists("logo.png"):
            with open("logo.png", "rb") as f:
                data = base64.b64encode(f.read()).decode()
                st.markdown(f'<p align="center"><img src="data:image/png;base64,{data}" width="120"></p>', unsafe_allow_html=True)
        st.markdown(f"### 👤 {u['nome']}")
        menu = st.radio("Menu", ["🏠 Feed", "📅 Agenda", "📖 Bíblia", "🙏 Orações", "🤝 Ofertas PIX", "💰 Financeiro"])
        adm = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        
        if adm:
            st.divider()
            if st.button("📥 Importar acf.json"):
                if os.path.exists("acf.json"):
                    with open("acf.json", "r", encoding="utf-8") as f:
                        bib_data = json.load(f); executar_query("DELETE FROM biblia")
                        for livro in bib_data:
                            for i, cap in enumerate(livro['chapters']):
                                for j, texto in enumerate(cap):
                                    executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l, :c, :v, :t)", {"l": livro['name'], "c": i+1, "v": j+1, "t": texto})
                    st.success("Bíblia carregada!")
            
            membros_df = consultar_db("SELECT nome, email, codigo FROM membros")
            csv = membros_df.to_csv(index=False).encode('utf-8')
            st.download_button("👥 Exportar Membros (CSV)", data=csv, file_name="membros_agape.csv", mime="text/csv")
            
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # --- MENU: FEED ---
    if menu == "🏠 Feed":
        st.title("Mural da Igreja")
        col_f, col_d = st.columns([0.7, 0.3])
        with col_f:
            if adm:
                st.markdown('<div class="card-post">', unsafe_allow_html=True)
                with st.form("post_admin", clear_on_submit=True):
                    txt = st.text_area("Novo comunicado oficial")
                    foto = st.file_uploader("Anexar Imagem", type=['jpg', 'png', 'jpeg'])
                    if st.form_submit_button("Publicar no Mural"):
                        img_str = base64.b64encode(foto.read()).decode() if foto else ""
                        executar_query("INSERT INTO avisos (conteudo, img_data, data) VALUES (:c,:i,:d)",
                                       {"c":txt, "i":img_str, "d":datetime.now().strftime("%d/%m/%Y %H:%M")})
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, p in posts.iterrows():
                st.markdown(f'<div class="card-post"><b>Igreja Ágape</b> • <small>{p["data"]}</small><br><br>{p["conteudo"]}</div>', unsafe_allow_html=True)
                if p['img_data']: st.image(base64.b64decode(p['img_data']), use_container_width=True)
                if adm:
                    if st.button(f"🗑️ Excluir Post #{p['id']}", key=f"del_{p['id']}"):
                        executar_query("DELETE FROM avisos WHERE id=:id", {"id":p['id']}); st.rerun()
        with col_d:
            st.markdown("### ✨ Palavra do Dia")
            res_b = consultar_db("SELECT * FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not res_b.empty:
                b = res_b.iloc[0]
                st.markdown(f'<div class="palavra-destaque"><p>"{b["texto"]}"</p><b>{b["livro"]} {b["cap"]}:{b["ver"]}</b></div>', unsafe_allow_html=True)

    # --- MENU: AGENDA (TRAVADA PARA ADMIN) ---
    elif menu == "📅 Agenda":
        st.title("📅 Programação da Igreja")
        if adm:
            st.markdown('<div class="card-post">', unsafe_allow_html=True)
            with st.form("add_ev"):
                tit = st.text_input("Evento")
                dia = st.selectbox("Dia", ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"])
                hor = st.text_input("Hora")
                if st.form_submit_button("Salvar na Agenda"):
                    executar_query("INSERT INTO eventos (titulo, dia_semana, hora) VALUES (:t,:d,:h)", {"t":tit, "d":dia, "h":hor}); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        ordem = "CASE dia_semana WHEN 'Domingo' THEN 1 WHEN 'Segunda' THEN 2 WHEN 'Terça' THEN 3 WHEN 'Quarta' THEN 4 WHEN 'Quinta' THEN 5 WHEN 'Sexta' THEN 6 WHEN 'Sábado' THEN 7 END"
        for _, ev in consultar_db(f"SELECT * FROM eventos ORDER BY {ordem}").iterrows():
            st.markdown(f'<div class="card-post event-card"><b>{ev["dia_semana"]} às {ev["hora"]}</b><br>{ev["titulo"]}</div>', unsafe_allow_html=True)
            if adm:
                if st.button(f"🗑️ Remover Evento #{ev['id']}", key=f"ev_{ev['id']}"):
                    executar_query("DELETE FROM eventos WHERE id=:id", {"id":ev['id']}); st.rerun()

    # --- BÍBLIA ---
    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        res_l = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not res_l.empty:
            l_sel = st.selectbox("Livro", res_l['livro'].tolist())
            c_sel = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":l_sel})['cap'].tolist())
            st.markdown('<div class="card-post">', unsafe_allow_html=True)
            for _, v in consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c", {"l":l_sel, "c":c_sel}).iterrows():
                st.markdown(f'<p class="texto-biblico"><b>{v["ver"]}</b> {v["texto"]}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # --- ORAÇÕES ---
    elif menu == "🙏 Orações":
        st.title("🙏 Pedidos de Oração")
        with st.form("ped"):
            txt_p = st.text_area("Seu pedido")
            if st.form_submit_button("Enviar"):
                executar_query("INSERT INTO oracoes (nome, pedido, status, data) VALUES (:n,:p,'Pendente',:d)", {"n":u['nome'], "p":txt_p, "d":datetime.now().strftime("%d/%m/%Y")}); st.rerun()
        for _, o in consultar_db("SELECT * FROM oracoes ORDER BY id DESC").iterrows():
            st.markdown(f'<div class="card-post"><b>{o["nome"]}</b>: {o["pedido"]} ({o["status"]})</div>', unsafe_allow_html=True)
            if adm and o['status'] == 'Pendente':
                if st.button(f"✅ Marcar Orado #{o['id']}"): executar_query("UPDATE oracoes SET status='Orado' WHERE id=:id", {"id":o['id']}); st.rerun()

    # --- OFERTAS ---
    elif menu == "🤝 Ofertas PIX":
        st.title("🤝 Dízimos e Ofertas")
        st.info("PIX: **financeiro@igrejaagape.com**")
        with st.form("pix"):
            v_pix = st.number_input("Valor", 1.0)
            if st.form_submit_button("Confirmar Doação Realizada"):
                executar_query("INSERT INTO financeiro (descricao, valor, tipo, data, usuario) VALUES (:d,:v,'Entrada',:dt,:u)", {"d":f"Oferta PIX {u['nome']}", "v":v_pix, "dt":datetime.now().strftime("%d/%m/%Y"), "u":u['nome']})
                st.success("Doação registrada! Deus abençoe.")

    # --- FINANCEIRO ---
    elif menu == "💰 Financeiro":
        st.title("💰 Gestão Financeira")
        if adm:
            with st.expander("Lançamentos (Admin)"):
                with st.form("fin"):
                    id_e = st.number_input("ID p/ editar (0=novo)", 0)
                    desc, val = st.text_input("Descrição"), st.number_input("Valor", 0.0)
                    tipo = st.selectbox("Tipo", ["Entrada", "Saída", "Ativo", "Passivo"])
                    if st.form_submit_button("Gravar"):
                        dt_hj = datetime.now().strftime("%d/%m/%Y")
                        if id_e == 0: executar_query("INSERT INTO financeiro (descricao, valor, tipo, data, usuario) VALUES (:d,:v,:t,:dt,'Admin')", {"d":desc,"v":val,"t":tipo,"dt":dt_hj})
                        else: executar_query("UPDATE financeiro SET descricao=:d, valor=:v, tipo=:t WHERE id=:id", {"d":desc,"v":val,"t":tipo,"id":id_e})
                        st.rerun()
        df = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
        st.table(df)
        e, s = df[df['tipo']=='Entrada']['valor'].sum(), df[df['tipo']=='Saída']['valor'].sum()
        st.metric("Saldo em Caixa", f"R$ {e-s:,.2f}")
