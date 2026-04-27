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

# --- 2. BANCO DE DADOS (v50) ---
engine = create_engine("sqlite:///agape_v50.db", pool_pre_ping=True)

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
                    if n and em and se:
                        try:
                            c = "AG-" + "".join(random.choices(string.digits, k=4))
                            executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n, :e, :c, :p, 0)", {"n":n,"e":em,"c":c,"p":generate_password_hash(se)})
                            st.success(f"Conta criada! Faça login na aba 'Entrar'.")
                        except: st.error("E-mail já cadastrado.")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    with st.sidebar:
        logo_central(100)
        st.markdown(f"<p style='text-align: center;'>🙏 <b>{u['nome']}</b></p>", unsafe_allow_html=True)
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎶 Louvores", "🎥 Bate-papo", "💰 Financeiro", "🎁 Doações"])
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.logado = False; st.rerun()

    if admin_mode:
        st.title("⚙️ Administração")
        tabs = st.tabs(["📢 Mural", "📖 Bíblia", "🎶 Louvores", "💰 Financeiro", "🎁 Config Pix"])
        
        with tabs[0]: # Mural
            with st.form("f_aviso", clear_on_submit=True):
                tit, cont = st.text_input("Título"), st.text_area("Conteúdo")
                foto = st.file_uploader("Foto", type=['png','jpg','jpeg'])
                if st.form_submit_button("Publicar"):
                    img = base64.b64encode(foto.read()).decode() if foto else ""
                    executar_query("INSERT INTO avisos (titulo, conteudo, data, img_data) VALUES (:t,:c,:d,:i)", {"t":tit,"c":cont,"d":datetime.now().strftime("%d/%m/%Y"),"i":img})
                    st.success("Postado!")
        
        with tabs[2]: # Louvores
            with st.form("f_louvor", clear_on_submit=True):
                t_l, l_l = st.text_input("Título do Louvor"), st.text_input("Link YouTube (http...)")
                if st.form_submit_button("Adicionar Louvor"):
                    if str(l_l).startswith("http"):
                        executar_query("INSERT INTO louvores (titulo, link) VALUES (:t, :l)", {"t":t_l, "l":l_l})
                        st.success("Adicionado!")
                    else: st.error("O link deve começar com http")

        with tabs[4]: # PIX
            with st.form("f_pix"):
                c, b = st.text_input("Chave PIX"), st.text_input("Banco/Favorecido")
                qr = st.file_uploader("QR Code", type=['png','jpg'])
                if st.form_submit_button("Salvar Dados"):
                    qr_b = base64.b64encode(qr.read()).decode() if qr else ""
                    executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('pix_chave', :v)", {"v": c})
                    executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('pix_banco', :v)", {"v": b})
                    executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('pix_qr', :v)", {"v": qr_b})
                    st.success("Dados de doação atualizados!")

    else: # VISÃO DO MEMBRO
        if menu == "📢 Mural":
            st.title("📢 Mural Ágape")
            for _, a in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
                st.markdown(f'<div class="card-flutuante"><h3>{a["titulo"]}</h3><p>{a["conteudo"]}</p></div>', unsafe_allow_html=True)
                if a['img_data']: st.image(f"data:image/png;base64,{a['img_data']}", use_container_width=True)

        elif menu == "🎶 Louvores":
            st.title("🎶 Louvores")
            louvores = consultar_db("SELECT * FROM louvores ORDER BY id DESC")
            for _, l in louvores.iterrows():
                link = str(l['link']).strip()
                if link.startswith("http"):
                    st.markdown(f'<div class="card-flutuante"><b>{l["titulo"]}</b></div>', unsafe_allow_html=True)
                    try: st.video(link)
                    except: st.error(f"Erro ao carregar vídeo: {l['titulo']}")

        elif menu == "🎁 Doações":
            st.title("🎁 Doações")
            p_c = consultar_db("SELECT valor FROM configuracoes WHERE chave='pix_chave'")
            if not p_c.empty:
                st.markdown(f'<div class="pix-box"><b>Chave PIX:</b> {p_c.iloc[0]["valor"]}</div>', unsafe_allow_html=True)
                p_q = consultar_db("SELECT valor FROM configuracoes WHERE chave='pix_qr'")
                if not p_q.empty and p_q.iloc[0]['valor']:
                    st.image(f"data:image/png;base64,{p_q.iloc[0]['valor']}", width=300)
            else: st.info("Dados PIX não configurados.")

        elif menu == "💰 Financeiro":
            st.title("💰 Financeiro")
            df = consultar_db("SELECT * FROM financeiro")
            if not df.empty:
                r = df[df['tipo'] == 'Entrada']['valor'].sum()
                p = df[df['tipo'] == 'Saída']['valor'].sum()
                st.metric("Saldo", f"R$ {r-p:,.2f}", delta=f"Receita: R$ {r:,.2f}")
                st.dataframe(df, use_container_width=True)

        elif menu == "📖 Bíblia":
            st.title("📖 Bíblia")
            livros = consultar_db("SELECT DISTINCT livro FROM biblia")
            if not livros.empty:
                l_s = st.selectbox("Livro", livros['livro'])
                c_s = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l_s})['capitulo'])
                vers = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l_s, "c":c_s})
                for _, v in vers.iterrows():
                    st.markdown(f'<div class="card-flutuante"><b>{v["versiculo"]}.</b> {v["texto"]}</div>', unsafe_allow_html=True)

        elif menu == "🎥 Bate-papo":
            st.title("🎥 Bate-papo")
            membros = consultar_db("SELECT nome FROM membros WHERE nome != :eu", {"eu": u['nome']})
            contato = st.selectbox("Escolha alguém:", ["Selecione..."] + list(membros['nome']))
            if contato != "Selecione...":
                n1 = re.sub(r'[^a-zA-Z0-9]', '', u['nome']).lower()[:10]
                n2 = re.sub(r'[^a-zA-Z0-9]', '', contato).lower()[:10]
                url = f"https://jit.si_{min(n1,n2)}_{max(n1,n2)}"
                st.link_button("🟢 INICIAR CHAMADA", url)
                st.markdown(f'<iframe src="{url}" allow="camera; microphone; fullscreen" style="height:500px; width:100%; border:0; border-radius:20px;"></iframe>', unsafe_allow_html=True)
