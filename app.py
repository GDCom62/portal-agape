import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import random
import string

# --- 1. CONFIGURAÇÃO E DESIGN ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stButton>button { border-radius: 12px; width: 100%; height: 3em; background-color: #1E3A8A; color: white; }
    .stTextInput>div>div>input { border-radius: 10px; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #ddd; }
    .aviso-card { padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 15px; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_portal.db", pool_size=10, max_overflow=20)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    # Tabela membros atualizada com coluna 'ativo'
    executar_query('''CREATE TABLE IF NOT EXISTS membros 
        (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)''')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS config_geral (id INTEGER PRIMARY KEY, chave_pix TEXT, url_qrcode TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome_membro TEXT, pedido TEXT, data TEXT, status TEXT)')

    if consultar_db("SELECT * FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM001', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'user_nome' not in st.session_state: st.session_state.user_nome = ""
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

# --- 4. TELA INICIAL (LOGIN / RECUPERAÇÃO / CADASTRO) ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        tab_login, tab_cadastro, tab_recuperar = st.tabs(["🔐 Entrar", "📝 Novo Cadastro", "🔑 Esqueci Senha"])
        
        with tab_login:
            with st.form("login_agape"):
                email_l = st.text_input("E-mail")
                senha_l = st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar Portal"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": email_l})
                    if not res.empty:
                        if res.iloc[0]['ativo'] == 0:
                            st.error("Sua conta está desativada. Entre em contato com o administrador.")
                        elif check_password_hash(res.iloc[0]['senha'], senha_l):
                            st.session_state.update({"logado": True, "user_nome": res.iloc[0]['nome'], "is_admin": bool(res.iloc[0]['is_admin'])})
                            st.rerun()
                        else: st.error("Senha incorreta.")
                    else: st.error("E-mail não cadastrado.")
        
        with tab_cadastro:
            with st.form("cadastro_membro"):
                novo_nome = st.text_input("Nome Completo")
                novo_email = st.text_input("E-mail")
                nova_senha = st.text_input("Crie uma Senha", type="password")
                if st.form_submit_button("Finalizar Cadastro"):
                    if novo_nome and novo_email and nova_senha:
                        existe = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": novo_email})
                        if existe.empty:
                            cod = "AG-" + ''.join(random.choices(string.digits, k=4))
                            hash_pw = generate_password_hash(nova_senha)
                            executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                                           {"n": novo_nome, "e": novo_email, "c": cod, "p": hash_pw})
                            st.success(f"Cadastro realizado! Guarde seu código: {cod}")
                        else: st.error("E-mail já cadastrado.")
                    else: st.warning("Preencha todos os campos.")

        with tab_recuperar:
            st.info("Informe seu e-mail e código de membro para resetar a senha.")
            with st.form("recuperar_senha"):
                rec_email = st.text_input("E-mail cadastrado")
                rec_codigo = st.text_input("Código de Membro (AG-XXXX)")
                nova_senha_rec = st.text_input("Nova Senha", type="password")
                if st.form_submit_button("Redefinir Senha"):
                    user = consultar_db("SELECT * FROM membros WHERE email=:e AND codigo=:c", {"e": rec_email, "c": rec_codigo})
                    if not user.empty:
                        new_hash = generate_password_hash(nova_senha_rec)
                        executar_query("UPDATE membros SET senha=:p WHERE email=:e", {"p": new_hash, "e": rec_email})
                        st.success("Senha alterada com sucesso! Já pode fazer login.")
                    else: st.error("Dados não conferem.")

    with col2:
        st.subheader("📢 Avisos da Comunidade")
        df_avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC LIMIT 5")
        for _, row in df_avisos.iterrows():
            st.markdown(f"""<div class='aviso-card'><b>{row['titulo']}</b><br><small>{row['data']}</small></div>""", unsafe_allow_html=True)

# --- 5. ÁREA LOGADA ---
else:
    st.sidebar.title(f"🙏 Olá, {st.session_state.user_nome}")
    menus = ["🏠 Mural", "📖 Estudos", "🙏 Orações", "💰 Ofertas"]
    if st.session_state.is_admin: menus.append("⚙️ Administração")
    
    escolha = st.sidebar.radio("Navegação", menus)
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # (As outras páginas permanecem conforme o código anterior...)

    if escolha == "⚙️ Administração":
        st.title("⚙️ Painel Gestor")
        aba1, aba2, aba3 = st.tabs(["📢 Novo Aviso", "👥 Gerenciar Membros", "📂 Restaurar Dados"])
        
        with aba1:
            with st.form("aviso_adm"):
                t = st.text_input("Título")
                c = st.text_area("Conteúdo")
                if st.form_submit_button("Publicar Aviso"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)",
                                   {"t": t, "c": c, "d": datetime.now().strftime("%d/%m/%Y")})
                    st.rerun()

        with aba2:
            st.subheader("Lista de Membros")
            membros = consultar_db("SELECT id, nome, email, codigo, ativo FROM membros WHERE is_admin=0")
            for _, m in membros.iterrows():
                col_m1, col_m2 = st.columns([3, 1])
                status_txt = "✅ Ativo" if m['ativo'] == 1 else "🚫 Bloqueado"
                col_m1.write(f"**{m['nome']}** ({m['email']}) - Código: {m['codigo']} | Status: {status_txt}")
                
                label_btn = "Bloquear" if m['ativo'] == 1 else "Desbloquear"
                novo_status = 0 if m['ativo'] == 1 else 1
                if col_m2.button(label_btn, key=f"btn_m_{m['id']}"):
                    executar_query("UPDATE membros SET ativo=:s WHERE id=:id", {"s": novo_status, "id": int(m['id'])})
                    st.rerun()

        with aba3:
            up = st.file_uploader("Upload backup_agape.json", type=['json'])
            if up and st.button("Restaurar Agora"):
                try:
                    dados = json.loads(up.read().decode("utf-8"))
                    for m in dados.get('membros', []):
                        pw = generate_password_hash('Agape2026')
                        executar_query("INSERT OR IGNORE INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                                       {"n": m['nome'], "e": m['email'], "c": m['codigo'], "p": pw})
                    st.success("Dados restaurados!")
                except Exception as e: st.error(f"Erro: {e}")

