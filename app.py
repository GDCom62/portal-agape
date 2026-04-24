import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import json

# --- 1. CONFIGURAÇÃO INICIAL E ESTILO CUSTOMIZADO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    /* Fundo principal suave */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Estilização da Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }

    /* Títulos elegantes */
    h1, h2, h3 {
        color: #1e3a8a !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-weight: 700;
    }

    /* Cards de Versículos e Avisos */
    .bible-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #3b82f6;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 15px;
    }
    
    .verse-num {
        color: #3b82f6;
        font-weight: bold;
        margin-right: 8px;
    }

    /* Botões arredondados */
    .stButton>button {
        border-radius: 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
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
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    
    try:
        check = consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'")
        if check.empty:
            pw = generate_password_hash('Agape2026')
            executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})
    except: pass

init_db()

# --- 3. CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False

# --- 4. TELA DE ACESSO (MODERNA) ---
if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>⛪ Portal Ágape</h1>", unsafe_allow_html=True)
        t_log, t_cad = st.tabs(["🔐 Entrar na Conta", "📝 Novo Cadastro"])
        
        with t_log:
            with st.form("login"):
                e = st.text_input("Seu E-mail")
                s = st.text_input("Sua Senha", type="password")
                if st.form_submit_button("Acessar Portal"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty:
                        u_data = res.iloc[0].to_dict()
                        if check_password_hash(u_data['senha'], s):
                            st.session_state.update({"logado": True, "user": u_data})
                            st.rerun()
                    st.error("Credenciais inválidas. Tente novamente.")
        
        with t_cad:
            with st.form("cad"):
                n = st.text_input("Nome Completo")
                em = st.text_input("E-mail")
                se = st.text_input("Crie uma Senha", type="password")
                if st.form_submit_button("Finalizar Cadastro"):
                    if n and em and se:
                        c = "AG-" + "".join(random.choices(string.digits, k=4))
                        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                                       {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                        st.success(f"Bem-vindo! Seu código é: {c}")
                    else: st.warning("Por favor, preencha todos os campos.")

# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    st.sidebar.markdown(f"### 🙏 Olá, **{u['nome']}**")
    st.sidebar.markdown("---")
    
    menu = ["📖 Ler a Bíblia", "📢 Mural Ágape"]
    if u['is_admin'] == 1: menu.append("⚙️ Administração")
    
    escolha = st.sidebar.radio("Navegação Principal", menu)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair do Portal"):
        st.session_state.logado = False
        st.rerun()

    if escolha == "📖 Ler a Bíblia":
        st.markdown("<h1>📖 Bíblia Sagrada</h1>", unsafe_allow_html=True)
        
        livros_df = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not livros_df.empty:
            c1, c2 = st.columns(2)
            l_sel = c1.selectbox("Selecione o Livro", livros_df['livro'].tolist())
            caps_df = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l ORDER BY capitulo", {"l": l_sel})
            c_sel = c2.selectbox("Capítulo", caps_df['capitulo'].tolist())
            
            versos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c ORDER BY versiculo", {"l": l_sel, "c": c_sel})
            
            st.markdown(f"### {l_sel} - Capítulo {c_sel}")
            st.markdown("---")
            
            # Layout de leitura limpo
            texto_completo = ""
            for _, v in versos.iterrows():
                texto_completo += f"<div class='bible-card'><span class='verse-num'>{v['versiculo']}</span>{v['texto']}</div>"
            st.markdown(texto_completo, unsafe_allow_html=True)
        else:
            st.info("Nenhum conteúdo bíblico carregado. O administrador deve importar o JSON.")

    elif escolha == "📢 Mural Ágape":
        st.markdown("<h1>📢 Avisos da Comunidade</h1>", unsafe_allow_html=True)
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        if df_a.empty:
            st.info("Não há avisos novos por aqui.")
        else:
            for _, r in df_a.iterrows():
                with st.container():
                    st.markdown(f"""
                        <div style='background-color: white; padding: 25px; border-radius: 15px; border-top: 4px solid #1e3a8a; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px;'>
                            <h3 style='margin-top: 0;'>{r['titulo']}</h3>
                            <p style='color: #475569;'>{r['conteudo']}</p>
                            <small style='color: #94a3b8;'>Postado em: {r.get('data', 'Recente')}</small>
                        </div>
                    """, unsafe_allow_html=True)

    elif escolha == "⚙️ Administração":
        st.markdown("<h1>⚙️ Administração</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["📥 Importar Bíblia", "👥 Lista de Membros"])
        
        with tab1:
            st.subheader("Importação Massiva (acf.json)")
            f = st.file_uploader("Selecione o arquivo da Bíblia", type=['json'])
            if f and st.button("Iniciar Processamento"):
                dados = json.load(f)
                prog = st.progress(0)
                sucessos = 0
                for idx, livro_obj in enumerate(dados):
                    nome_livro = livro_obj.get('name') or livro_obj.get('nome')
                    capitulos = livro_obj.get('chapters') or []
                    for idx_cap, cap_lista in enumerate(capitulos):
                        num_cap = idx_cap + 1
                        for idx_ver, texto_ver in enumerate(cap_lista):
                            num_ver = idx_ver + 1
                            if nome_livro and texto_ver:
                                try:
                                    executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)",
                                                   {"l": str(nome_livro).strip(), "c": num_cap, "v": num_ver, "t": str(texto_ver)})
                                    sucessos += 1
                                except: pass
                    prog.progress((idx + 1) / len(dados))
                st.success(f"✅ Importação finalizada! {sucessos} versículos carregados.")

        with tab2:
            st.subheader("Membros Cadastrados")
            df_m = consultar_db("SELECT id, nome, email, codigo, ativo FROM membros")
            st.dataframe(df_m, use_container_width=True)
