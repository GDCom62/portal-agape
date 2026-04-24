import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import random
import string

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS OTIMIZADO ---
engine = create_engine("sqlite:///agape_portal.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS comentarios (id INTEGER PRIMARY KEY, biblia_id INTEGER, nome_membro TEXT, comentario TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS config_geral (id INTEGER PRIMARY KEY, chave_pix TEXT, url_qrcode TEXT)')
    
    if consultar_db("SELECT * FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'user_email' not in st.session_state: st.session_state.user_email = ""

# --- 4. TELA DE ACESSO ---
if not st.session_state.logado:
    st.title("⛪ Portal Ágape")
    t_log, t_cad = st.tabs(["🔐 Entrar", "📝 Novo Cadastro"])
    
    with t_log:
        with st.form("login_form"):
            u = st.text_input("E-mail")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar"):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": u})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({
                        "logado": True, 
                        "user_nome": res.iloc[0]['nome'], 
                        "user_email": res.iloc[0]['email'],
                        "is_admin": bool(res.iloc[0]['is_admin'])
                    })
                    st.rerun()
                else: st.error("E-mail ou senha incorretos.")

    with t_cad:
        with st.form("cad_form"):
            n, e, s1 = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                if n and e and s1:
                    cod = "AG-" + "".join(random.choices(string.digits, k=5))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n, :e, :c, :p, 0)",
                                   {"n": n, "e": e, "c": cod, "p": generate_password_hash(s1)})
                    st.success(f"Cadastrado! Código: {cod}")
                else: st.warning("Preencha todos os campos.")

# --- 5. ÁREA LOGADA ---
else:
    st.sidebar.title(f"🙏 {st.session_state.user_nome}")
    
    # Lógica de Menu: Garante que admin@agape.com sempre veja o menu Admin
    menu_options = ["Mural", "Bíblia", "Ofertas"]
    if st.session_state.is_admin or st.session_state.user_email == 'admin@agape.com':
        menu_options.append("Admin")
    
    menu = st.sidebar.radio("Navegação", menu_options)
    
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- PÁGINAS ---
    if menu == "Mural":
        st.title("📢 Mural de Avisos")
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in df_a.iterrows():
            with st.container(border=True):
                st.subheader(r['titulo'])
                st.write(r['conteudo'])

    elif menu == "Bíblia":
        st.title("📖 Bíblia e Estudos")
        livros_df = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros_df.empty:
            l_sel = st.selectbox("Selecione o Livro", livros_df['livro'].tolist())
            cap_df = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l": l_sel})
            c_sel = st.selectbox("Capítulo", cap_df['capitulo'].tolist())
            
            versiculos = consultar_db("SELECT * FROM biblia WHERE livro=:l AND capitulo=:c", {"l": l_sel, "c": c_sel})
            for _, v in versiculos.iterrows():
                with st.expander(f"Versículo {v['versiculo']}"):
                    st.write(v['texto'])
        else: st.info("Bíblia ainda não disponível. Aguarde a importação pelo administrador.")

    elif menu == "Ofertas":
        st.title("💰 Ofertas e Dízimos")
        conf = consultar_db("SELECT * FROM config_geral LIMIT 1")
        if not conf.empty:
            st.success(f"Chave PIX: **{conf.iloc[0]['chave_pix']}**")
            if conf.iloc[0]['url_qrcode']: st.image(conf.iloc[0]['url_qrcode'], width=250)
        else: st.warning("Dados de PIX não configurados.")

    elif menu == "Admin":
        st.title("⚙️ Painel do Administrador")
        tab_p, tab_b, tab_m = st.tabs(["Avisos/PIX", "📥 Importar Bíblia", "Membros"])
        
        with tab_p:
            with st.form("pix_admin"):
                px = st.text_input("Chave PIX")
                qr = st.text_input("URL da imagem do QR Code")
                if st.form_submit_button("Salvar Configuração"):
                    executar_query("DELETE FROM config_geral")
                    executar_query("INSERT INTO config_geral (chave_pix, url_qrcode) VALUES (:p, :q)", {"p":px, "q":qr})
                    st.success("Dados de PIX salvos!")

            with st.form("aviso_admin"):
                t = st.text_input("Título do Aviso")
                c = st.text_area("Mensagem")
                if st.form_submit_button("Publicar Aviso"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)", 
                                   {"t":t, "c":c, "d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Aviso publicado!")

        with tab_b:
            st.subheader("Importação Massiva (Arquivo JSON)")
            file = st.file_uploader("Upload do arquivo acf.json", type=['json'])
            if file and st.button("🚀 Iniciar Importação em Blocos"):
                try:
                    dados = json.load(file)
                    prog = st.progress(0)
                    total = len(dados)
                    for i in range(0, total, 500):
                        bloco = dados[i:i+500]
                        with engine.begin() as conn:
                            for v in bloco:
                                conn.execute(text("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)"),
                                             {"l":v['book'], "c":v['chapter'], "v":v['number'], "t":v['text']})
                        prog.progress(min((i+500)/total, 1.0))
                    st.success("Bíblia importada com sucesso!")
                except Exception as e: st.error(f"Erro no arquivo: {e}")

        with tab_m:
            df_m = consultar_db("SELECT nome, email, codigo, ativo FROM membros")
            st.dataframe(df_m, use_container_width=True)
