import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import json

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS (Nova Versão V6) ---
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
        (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, UNIQUE(livro, capitulo, versiculo))''')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    
    # Criar Admin
    try:
        check = consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'")
        if check.empty:
            pw = generate_password_hash('Agape2026')
            executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})
    except: pass

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False

# --- 4. LOGIN ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
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
                st.error("Dados inválidos.")
    with t_cad:
        with st.form("cad"):
            n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                c = "AG-" + "".join(random.choices(string.digits, k=4))
                executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                               {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                st.success(f"Código: {c}")

# --- 5. ÁREA LOGADA ---
else:
    st.sidebar.title(f"🙏 Olá, {st.session_state.user['nome']}")
    menu = ["📖 Bíblia", "📢 Mural"]
    if st.session_state.user['is_admin'] == 1: menu.append("⚙️ Admin")
    escolha = st.sidebar.radio("Navegação", menu)
    
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    if escolha == "⚙️ Admin":
        st.header("⚙️ Painel Administrador")
        st.subheader("📥 Importação da Bíblia")
        
        f = st.file_uploader("Arquivo acf.json", type=['json'])
        if f and st.button("🚀 Iniciar Importação Blindada"):
            try:
                dados = json.load(f)
                total = len(dados)
                prog = st.progress(0)
                st_txt = st.empty()
                
                # Contador de sucessos
                sucessos = 0
                
                for i, v in enumerate(dados):
                    # TENTA IDENTIFICAR AS CHAVES DINAMICAMENTE
                    livro = v.get('book') or v.get('livro') or v.get('name') or v.get('nome') or v.get('abbrev')
                    cap = v.get('chapter') or v.get('capitulo') or v.get('c')
                    num = v.get('number') or v.get('versiculo') or v.get('v') or v.get('n')
                    txt = v.get('text') or v.get('texto') or v.get('t')

                    if livro and txt:
                        try:
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)",
                                         {"l": str(livro).strip(), "c": int(cap), "v": int(num), "t": str(txt)})
                            sucessos += 1
                        except: pass
                    
                    if i % 100 == 0:
                        prog.progress(i/total)
                        st_txt.text(f"Lido: {i}/{total} | Gravado: {sucessos}")
                
                st.success(f"✅ Fim! {sucessos} versículos prontos no banco.")
            except Exception as e:
                st.error(f"Erro: {e}")

    elif escolha == "📖 Bíblia":
        st.header("📖 Bíblia Sagrada")
        
        # Verifica se há algo no banco
        contagem = consultar_db("SELECT count(*) as total FROM biblia").iloc[0]['total']
        st.caption(f"Versículos no sistema: {contagem}")
        
        livros_df = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not livros_df.empty:
            l_sel = st.selectbox("Livro", livros_df['livro'].tolist())
            caps_df = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l ORDER BY capitulo", {"l": l_sel})
            c_sel = st.selectbox("Capítulo", caps_df['capitulo'].tolist())
            versos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c ORDER BY versiculo", {"l": l_sel, "c": c_sel})
            
            st.divider()
            for _, v in versos.iterrows():
                st.markdown(f"**{v['versiculo']}** {v['texto']}")
        else:
            st.warning("Banco vazio. Vá no menu Admin e carregue o arquivo JSON.")

    elif escolha == "📢 Mural":
        st.write("Bem-vindo ao Mural!")
