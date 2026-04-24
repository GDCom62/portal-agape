import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string
import json

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Portal Ágape", layout="centered", page_icon="⛪")

# --- 2. BANCO DE DADOS (Versão estável) ---
engine = create_engine("sqlite:///agape_final_v5.db", pool_pre_ping=True)

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
    
    # Criar Admin inicial
    try:
        check = consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'")
        if check.empty:
            pw = generate_password_hash('Agape2026')
            executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})
    except: pass

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'user' not in st.session_state: st.session_state.user = None

# --- 4. TELA DE ACESSO ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    t_log, t_cad = st.tabs(["🔐 Login", "📝 Cadastro"])
    
    with t_log:
        with st.form("login_form"):
            e = st.text_input("E-mail")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                if not res.empty:
                    u_data = res.iloc[0].to_dict()
                    if check_password_hash(u_data['senha'], s):
                        st.session_state.logado = True
                        st.session_state.user = u_data
                        st.rerun()
                    else: st.error("Senha incorreta.")
                else: st.error("E-mail não cadastrado.")

    with t_cad:
        with st.form("cad_form"):
            n_c = st.text_input("Nome Completo")
            e_c = st.text_input("E-mail")
            s_c = st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                if n_c and e_c and s_c:
                    cod = "AG-" + "".join(random.choices(string.digits, k=4))
                    try:
                        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                                       {"n": n_c, "e": e_c, "c": cod, "p": generate_password_hash(s_c)})
                        st.success(f"Sucesso! Código: {cod}")
                    except: st.error("E-mail já existe.")

# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    st.sidebar.title(f"🙏 Olá, {u['nome']}")
    menu_op = ["📖 Bíblia", "📢 Mural"]
    if u['is_admin'] == 1: menu_op.append("⚙️ Admin")
    escolha = st.sidebar.radio("Navegação", menu_op)
    
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- ABA ADMIN (IMPORTAÇÃO INTELIGENTE) ---
    if escolha == "⚙️ Admin":
        st.header("⚙️ Painel Administrativo")
        
        if st.button("🗑️ Limpar Bíblia (Apagar Erros/Desconhecidos)", type="secondary"):
            executar_query("DELETE FROM biblia")
            st.warning("Banco da Bíblia resetado!")
            st.rerun()

        st.subheader("📥 Importar Bíblia (JSON)")
        f = st.file_uploader("Selecione o arquivo acf.json", type=['json'])
        
        if f and st.button("🚀 Iniciar Importação Inteligente"):
            try:
                dados = json.load(f)
                total = len(dados)
                prog = st.progress(0)
                st_txt = st.empty()
                
                for i in range(0, total, 500):
                    bloco = dados[i:i+500]
                    with engine.begin() as conn:
                        for v in bloco:
                            # Tenta mapear qualquer nome de campo (Inglês ou Português)
                            livro = v.get('book') or v.get('livro') or v.get('nome') or v.get('abbrev') or v.get('name')
                            cap = v.get('chapter') or v.get('capitulo') or v.get('cap') or v.get('c')
                            num = v.get('number') or v.get('versiculo') or v.get('ver') or v.get('v') or v.get('n')
                            txt = v.get('text') or v.get('texto') or v.get('txt') or v.get('t')
                            
                            if livro and txt:
                                conn.execute(text("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)"),
                                             {"l": str(livro).strip(), "c": cap, "v": num, "t": txt})
                    
                    prog.progress(min((i+500)/total, 1.0))
                    st_txt.text(f"Salvando versículos: {i+len(bloco)} de {total}...")
                
                st.success("✅ Concluído! Verifique a aba Bíblia.")
            except Exception as e:
                st.error(f"Erro no processamento: {e}")

    # --- ABA BÍBLIA ---
    elif escolha == "📖 Bíblia":
        st.header("📖 Bíblia Sagrada")
        livros_df = consultar_db("SELECT DISTINCT livro FROM biblia WHERE livro != 'Desconhecido' ORDER BY id")
        
        if not livros_df.empty:
            l_sel = st.selectbox("Livro", livros_df['livro'].tolist())
            caps_df = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l ORDER BY capitulo", {"l": l_sel})
            c_sel = st.selectbox("Capítulo", caps_df['capitulo'].tolist())
            versos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c ORDER BY versiculo", {"l": l_sel, "c": c_sel})
            
            st.divider()
            for _, v in versos.iterrows():
                st.markdown(f"**{v['versiculo']}** {v['texto']}")
        else:
            st.warning("⚠️ Bíblia não encontrada. Vá em Admin e realize a importação.")

    elif escolha == "📢 Mural":
        st.header("📢 Mural Ágape")
        st.write("Bem-vindo ao Portal da nossa comunidade!")
