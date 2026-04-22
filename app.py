import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import random
import string
import io

# --- 1. CONFIGURAÇÃO E DESIGN ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stButton>button { border-radius: 12px; width: 100%; height: 3em; }
    .stTextInput>div>div>input { border-radius: 10px; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #ddd; }
    .aviso-card { padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 15px; background-color: white; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .btn-perigo > div > button { background-color: #ff4b4b !important; color: white !important; border: none; }
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
    executar_query('''CREATE TABLE IF NOT EXISTS membros 
        (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)''')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome_membro TEXT, pedido TEXT, data TEXT, status TEXT)')

    if consultar_db("SELECT * FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM001', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'user_nome' not in st.session_state: st.session_state.user_nome = ""
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

# --- 4. TELA INICIAL ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    t_log, t_cad, t_rec = st.tabs(["🔐 Entrar", "📝 Cadastro", "🔑 Recuperar Acesso"])
    
    with t_log:
        with st.form("login_agape"):
            email_l = st.text_input("E-mail")
            senha_l = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": email_l})
                if not res.empty:
                    user = res.iloc[0]
                    if user['ativo'] == 0: st.error("Conta desativada.")
                    elif check_password_hash(user['senha'], senha_l):
                        st.session_state.update({"logado": True, "user_nome": user['nome'], "is_admin": bool(user['is_admin'])})
                        st.rerun()
                    else: st.error("Senha incorreta.")
                else: st.error("E-mail não cadastrado.")
    
    with t_cad:
        with st.form("cad_membro"):
            n_n = st.text_input("Nome Completo")
            n_e = st.text_input("E-mail")
            n_s = st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                if n_n and n_e and n_s:
                    cod = "AG-" + ''.join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)",
                                   {"n": n_n, "e": n_e, "c": cod, "p": generate_password_hash(n_s)})
                    st.success(f"Cadastrado! SEU CÓDIGO É: {cod}")
    
    with t_rec:
        with st.form("rec_senha"):
            re_e = st.text_input("E-mail")
            re_c = st.text_input("Código de Cadastro")
            re_s = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Redefinir Senha"):
                user = consultar_db("SELECT * FROM membros WHERE email=:e AND codigo=:c", {"e": re_e, "c": re_c})
                if not user.empty:
                    executar_query("UPDATE membros SET senha=:p WHERE email=:e", {"p": generate_password_hash(re_s), "e": re_e})
                    st.success("Senha atualizada!")

# --- 5. ÁREA LOGADA ---
else:
    st.sidebar.title(f"🙏 {st.session_state.user_nome}")
    menu = ["🏠 Mural", "📖 Bíblia", "🙏 Orações"]
    if st.session_state.is_admin: menu.append("⚙️ Administração")
    
    escolha = st.sidebar.radio("Navegação", menu)
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    if escolha == "⚙️ Administração":
        st.title("⚙️ Painel do Administrador")
        tab_m, tab_sup, tab_bak = st.tabs(["👥 Membros", "🛠️ Suporte", "💾 Backup"])
        
        with tab_m:
            df_m = consultar_db("SELECT * FROM membros WHERE is_admin=0")
            for _, m in df_m.iterrows():
                with st.expander(f"👤 {m['nome']} ({m['email']})"):
                    c1, c2, c3 = st.columns(3)
                    if c1.button("BLOQUEAR" if m['ativo']==1 else "ATIVAR", key=f"bl_{m['id']}"):
                        executar_query("UPDATE membros SET ativo=:s WHERE id=:id", {"s": 0 if m['ativo']==1 else 1, "id": int(m['id'])})
                        st.rerun()
                    conf = c2.checkbox("Excluir?", key=f"ch_{m['id']}")
                    st.markdown('<div class="btn-perigo">', unsafe_allow_html=True)
                    if c3.button("EXCLUIR", key=f"ex_{m['id']}", disabled=not conf):
                        executar_query("DELETE FROM membros WHERE id=:id", {"id": int(m['id'])})
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

        with tab_sup:
            m_list = consultar_db("SELECT nome, email, codigo FROM membros WHERE is_admin=0")
            if not m_list.empty:
                sel = st.selectbox("Membro", m_list['nome'].tolist())
                d = m_list[m_list['nome'] == sel].iloc[0]
                st.warning(f"Código: **{d['codigo']}**")
                nv_s = st.text_input("Resetar Senha", type="password")
                if st.button("Trocar Senha"):
                    executar_query("UPDATE membros SET senha=:p WHERE email=:e", {"p": generate_password_hash(nv_s), "e": d['email']})
                    st.success("Senha alterada!")

        with tab_bak:
            st.subheader("Extrair Dados do Sistema")
            if st.button("Gerar Relatórios"):
                # Excel com abas
                df_membros = consultar_db("SELECT nome, email, codigo, ativo FROM membros")
                df_oracoes = consultar_db("SELECT * FROM oracoes")
                df_biblia = consultar_db("SELECT * FROM biblia")
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_membros.to_excel(writer, sheet_name='Membros', index=False)
                    df_oracoes.to_excel(writer, sheet_name='Orações', index=False)
                    df_biblia.to_excel(writer, sheet_name='Bíblia', index=False)
                
                st.download_button(
                    label="📥 Baixar Backup em Excel",
                    data=output.getvalue(),
                    file_name=f"backup_agape_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.ms-excel"
                )

    elif escolha == "🏠 Mural":
        st.title("📢 Mural")
        if st.session_state.is_admin:
            with st.expander("Novo Aviso"):
                with st.form("av"):
                    t, c = st.text_input("Título"), st.text_area("Texto")
                    if st.form_submit_button("Postar"):
                        executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)", {"t":t, "c":c, "d":datetime.now().strftime("%d/%m/%Y")})
                        st.rerun()
        for _, r in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
            st.markdown(f"<div class='aviso-card'><h3>{r['titulo']}</h3><p>{r['conteudo']}</p></div>", unsafe_allow_html=True)

    elif escolha == "📖 Bíblia":
        st.title("📖 Bíblia")
        if st.session_state.is_admin:
            with st.expander("Novo Estudo"):
                with st.form("bib"):
                    l, cp, v = st.text_input("Livro"), st.number_input("Cap", 1), st.number_input("Ver", 1)
                    tx, ex = st.text_area("Texto"), st.text_area("Explicação")
                    if st.form_submit_button("Gravar"):
                        executar_query("INSERT INTO biblia (livro,capitulo,versiculo,texto,explicacao) VALUES (:l,:c,:v,:t,:e)", {"l":l,"c":cp,"v":v,"t":tx,"e":ex})
        df_b = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not df_b.empty:
            l_sel = st.selectbox("Livro", df_b['livro'].tolist())
            for _, r in consultar_db("SELECT * FROM biblia WHERE livro=:l", {"l": l_sel}).iterrows():
                st.info(f"**{r['livro']} {r['capitulo']}:{r['versiculo']}** - {r['texto']}")
                st.write(f"💡 {r['explicacao']}")

    elif escolha == "🙏 Orações":
        st.title("🙏 Orações")
        with st.form("ora"):
            p = st.text_area("Seu pedido")
            if st.form_submit_button("Pedir"):
                executar_query("INSERT INTO oracoes (nome_membro, pedido, data, status) VALUES (:n, :p, :d, 'Pendente')", {"n": st.session_state.user_nome, "p": p, "d": datetime.now().strftime("%d/%m/%Y")})
        for _, r in consultar_db("SELECT * FROM oracoes ORDER BY id DESC").iterrows():
            st.markdown(f"<div class='aviso-card'><b>{r['nome_membro']}</b>: {r['pedido']}</div>", unsafe_allow_html=True)
