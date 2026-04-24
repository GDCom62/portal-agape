import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import string
import json

# --- 1. CONFIGURAÇÃO INICIAL E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
    h1, h2, h3 { color: #1e3a8a !important; font-family: 'Segoe UI', sans-serif; }
    
    /* Estilo dos Cards do Mural */
    .mural-card {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        border-top: 5px solid #1e3a8a;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    
    /* Estilo dos Cards da Bíblia */
    .bible-card {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #3b82f6;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .verse-num { color: #3b82f6; font-weight: bold; margin-right: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v6.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('''CREATE TABLE IF NOT EXISTS membros 
        (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)''')
    executar_query('''CREATE TABLE IF NOT EXISTS biblia 
        (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))''')
    executar_query('''CREATE TABLE IF NOT EXISTS avisos 
        (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)''')
    
    try:
        if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
            pw = generate_password_hash('Agape2026')
            executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})
    except: pass

init_db()

# --- 3. CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False

# --- 4. TELA DE ACESSO ---
if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try: st.image("logo.png", use_container_width=True)
        except: st.markdown("<h1 style='text-align: center;'>⛪ Portal Ágape</h1>", unsafe_allow_html=True)
        
        t_log, t_cad = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_log:
            with st.form("login"):
                e = st.text_input("E-mail")
                s = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty:
                        u_data = res.iloc[0].to_dict()
                        if check_password_hash(u_data['senha'], s):
                            st.session_state.update({"logado": True, "user": u_data})
                            st.rerun()
                    st.error("Dados incorretos.")
        with t_cad:
            with st.form("cad"):
                n = st.text_input("Nome Completo")
                em = st.text_input("E-mail")
                se = st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar"):
                    if n and em and se:
                        c = "AG-" + "".join(random.choices(string.digits, k=4))
                        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                                       {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                        st.success(f"Cadastrado! Seu código: {c}")

# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    try: st.sidebar.image("logo.png", use_container_width=True)
    except: pass
    st.sidebar.markdown(f"### 🙏 Olá, **{u['nome']}**")
    
    menu = ["📢 Mural Ágape", "📖 Ler a Bíblia"]
    if u['is_admin'] == 1: menu.append("⚙️ Administração")
    
    escolha = st.sidebar.radio("Navegação", menu)
    if st.sidebar.button("🚪 Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- MURAL ---
    if escolha == "📢 Mural Ágape":
        st.markdown("<h1>📢 Mural da Comunidade</h1>", unsafe_allow_html=True)
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        if df_a.empty:
            st.info("Nenhum aviso no momento.")
        else:
            for _, r in df_a.iterrows():
                st.markdown(f"""
                    <div class="mural-card">
                        <h3 style="margin-top:0;">{r['titulo']}</h3>
                        <p style="color: #475569;">{r['conteudo']}</p>
                        <small style="color: #94a3b8;">📅 {r['data']}</small>
                    </div>
                """, unsafe_allow_html=True)

    # --- BÍBLIA ---
    elif escolha == "📖 Ler a Bíblia":
        st.markdown("<h1>📖 Bíblia Sagrada</h1>", unsafe_allow_html=True)
        livros_df = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not livros_df.empty:
            c1, c2 = st.columns(2)
            l_sel = c1.selectbox("Livro", livros_df['livro'].tolist())
            caps_df = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l ORDER BY capitulo", {"l": l_sel})
            c_sel = c2.selectbox("Capítulo", caps_df['capitulo'].tolist())
            versos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c ORDER BY versiculo", {"l": l_sel, "c": c_sel})
            st.markdown(f"### {l_sel} - Capítulo {c_sel}")
            for _, v in versos.iterrows():
                st.markdown(f"<div class='bible-card'><span class='verse-num'>{v['versiculo']}</span>{v['texto']}</div>", unsafe_allow_html=True)

    # --- ADMINISTRAÇÃO ---
    elif escolha == "⚙️ Administração":
        st.markdown("<h1>⚙️ Painel do Administrador</h1>", unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["📢 Postar Aviso", "📥 Importar Bíblia", "👥 Membros"])
        
        with tab1:
            st.subheader("Criar Comunicado para a Comunidade")
            with st.form("form_aviso", clear_on_submit=True):
                titulo_aviso = st.text_input("Título do Aviso (Ex: Culto de Domingo)")
                texto_aviso = st.text_area("Mensagem completa")
                data_aviso = datetime.now().strftime("%d/%m/%Y %H:%M")
                if st.form_submit_button("🚀 Publicar no Mural"):
                    if titulo_aviso and texto_aviso:
                        executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)",
                                       {"t": titulo_aviso, "c": texto_aviso, "d": data_aviso})
                        st.success("✅ Aviso publicado com sucesso!")
                    else:
                        st.error("Preencha o título e a mensagem.")

        with tab2:
            st.subheader("Importar Bíblia (acf.json)")
            f = st.file_uploader("Selecione o arquivo", type=['json'])
            if f and st.button("Iniciar Processamento"):
                dados = json.load(f)
                prog = st.progress(0)
                for idx, livro_obj in enumerate(dados):
                    nome_l = livro_obj.get('name') or livro_obj.get('nome')
                    capitulos = livro_obj.get('chapters') or []
                    for idx_cap, cap_lista in enumerate(capitulos):
                        for idx_ver, texto_ver in enumerate(cap_lista):
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)",
                                           {"l": str(nome_l).strip(), "c": idx_cap+1, "v": idx_ver+1, "t": str(texto_ver)})
                    prog.progress((idx + 1) / len(dados))
                st.success("✅ Bíblia Carregada!")

        with tab3:
            st.subheader("Membros do Portal")
            df_m = consultar_db("SELECT id, nome, email, codigo, ativo FROM membros")
            st.dataframe(df_m, use_container_width=True)
