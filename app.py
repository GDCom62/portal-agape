import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json, os, base64, re

# --- 1. CONFIGURAÇÕES E ESTILO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    h1, h2, h3 { color: #1e3a8a !important; text-align: center; }
    .card-flutuante {
        background-color: white; padding: 20px; border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 15px;
        border-left: 8px solid #1e3a8a;
    }
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-weight: bold; }
    .pix-box { background-color: #eef2ff; padding: 15px; border-radius: 15px; border: 2px dashed #1e3a8a; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS (v48) ---
engine = create_engine("sqlite:///agape_v48.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT, img_data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS recados (id INTEGER PRIMARY KEY, de_nome TEXT, para_nome TEXT, mensagem TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY, titulo TEXT, link TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    
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
                if st.form_submit_button("Acessar Portal"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                        st.rerun()
                    st.error("Credenciais incorretas.")
        with t_c:
            with st.form("cad", clear_on_submit=True):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Minha Conta"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n, :e, :c, :p, 0)", {"n":n,"e":em,"c":c,"p":generate_password_hash(se)})
                    st.success(f"Conta criada! Código: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    with st.sidebar:
        logo_central(100)
        st.markdown(f"<p style='text-align: center;'>🙏 Olá, <b>{u['nome']}</b></p>", unsafe_allow_html=True)
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎶 Louvores", "🎥 Bate-papo", "💰 Financeiro", "🎁 Doações"])
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.logado = False; st.rerun()

    if admin_mode:
        st.title("⚙️ Painel Administrador")
        t1, t2, t3, t4, t5 = st.tabs(["📢 Mural", "📖 Bíblia", "🎶 Louvores", "💰 Finanças", "🎁 Config Pix"])
        
        with t1:
            with st.form("f_aviso", clear_on_submit=True):
                tit, cont = st.text_input("Título"), st.text_area("Conteúdo")
                foto = st.file_uploader("Foto", type=['png','jpg','jpeg'])
                if st.form_submit_button("Publicar"):
                    img_b64 = base64.b64encode(foto.read()).decode() if foto else ""
                    executar_query("INSERT INTO avisos (titulo, conteudo, data, img_data) VALUES (:t, :c, :d, :i)", 
                                  {"t":tit, "c":cont, "d":datetime.now().strftime("%d/%m/%Y"), "i":img_b64})
                    st.success("Postado!")
        with t3:
            with st.form("f_louvor", clear_on_submit=True):
                tit_l, link_l = st.text_input("Título do Louvor"), st.text_input("Link YouTube")
                if st.form_submit_button("Adicionar Louvor"):
                    executar_query("INSERT INTO louvores (titulo, link) VALUES (:t, :l)", {"t":tit_l, "l":link_l})
                    st.success("Adicionado!")
        with t5:
            with st.form("f_pix"):
                chave = st.text_input("Chave PIX da Igreja")
                banco = st.text_input("Banco/Favorecido")
                qr = st.file_uploader("Upload do QR Code (Imagem)", type=['png','jpg'])
                if st.form_submit_button("Salvar Dados PIX"):
                    qr_b64 = base64.b64encode(qr.read()).decode() if qr else ""
                    executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('pix_chave', :v)", {"v": chave})
                    executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('pix_banco', :v)", {"v": banco})
                    executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('pix_qr', :v)", {"v": qr_b64})
                    st.success("Dados de doação atualizados!")

    else:
        if menu == "📢 Mural":
            st.title("📢 Mural Ágape")
            for _, a in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
                st.markdown(f'<div class="card-flutuante"><h3>{a["titulo"]}</h3><p>{a["conteudo"]}</p></div>', unsafe_allow_html=True)
                if a['img_data']: st.image(f"data:image/png;base64,{a['img_data']}", use_container_width=True)

        elif menu == "🎁 Doações":
            st.title("🎁 Dízimos e Ofertas")
            pix_c = consultar_db("SELECT valor FROM configuracoes WHERE chave='pix_chave'")
            pix_b = consultar_db("SELECT valor FROM configuracoes WHERE chave='pix_banco'")
            pix_q = consultar_db("SELECT valor FROM configuracoes WHERE chave='pix_qr'")
            
            if not pix_c.empty:
                st.markdown(f"""
                <div class="pix-box">
                    <h4>Escaneie ou Copie a Chave PIX</h4>
                    <p><b>Chave:</b> {pix_c.iloc[0]['valor']}</p>
                    <p><b>Favorecido:</b> {pix_b.iloc[0]['valor']}</p>
                </div>
                """, unsafe_allow_html=True)
                if not pix_q.empty and pix_q.iloc[0]['valor']:
                    st.image(f"data:image/png;base64,{pix_q.iloc[0]['valor']}", width=300)
            else: st.info("Dados de doação não configurados pelo administrador.")

        elif menu == "🎶 Louvores":
            st.title("🎶 Momentos de Louvor")
            louvores = consultar_db("SELECT * FROM louvores ORDER BY id DESC")
            for _, l in louvores.iterrows():
                with st.container():
                    st.markdown(f'<div class="card-flutuante"><b>{l["titulo"]}</b></div>', unsafe_allow_html=True)
                    st.video(l['link'])

        elif menu == "💰 Financeiro":
            st.title("💰 Transparência")
            df = consultar_db("SELECT * FROM financeiro")
            if not df.empty:
                rec = df[df['tipo'] == 'Entrada']['valor'].sum()
                pas = df[df['tipo'] == 'Saída']['valor'].sum()
                st.metric("Saldo Atual", f"R$ {rec - pas:,.2f}", delta=f"Rec: R$ {rec:,.2f}")
                st.table(df)

        elif menu == "📖 Bíblia":
            # (Mantido o código de bíblia em colunas conforme versões anteriores)
            st.title("📖 Bíblia")
            livros = consultar_db("SELECT DISTINCT livro FROM biblia")
            if not livros.empty:
                l = st.selectbox("Livro", livros['livro'])
                c = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l})['capitulo'])
                for _, v in consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l, "c":c}).iterrows():
                    st.markdown(f'<div class="card-flutuante"><b>{v["versiculo"]}.</b> {v["texto"]}</div>', unsafe_allow_html=True)
