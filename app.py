import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import string
import json
import base64
import io

# --- 1. CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS (FORÇANDO NOVA VERSÃO V10) ---
engine = create_engine("sqlite:///agape_v10.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT, img_url TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS palavra_dia (id INTEGER PRIMARY KEY, versiculo TEXT, referencia TEXT, devocional TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome_membro TEXT, pedido TEXT, data TEXT, status TEXT DEFAULT "Pendente")')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS chat_live (id INTEGER PRIMARY KEY, nome TEXT, mensagem TEXT, hora TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financas (id INTEGER PRIMARY KEY, data TEXT, codigo_membro TEXT, valor REAL, tipo TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False

# --- 4. TELA DE ACESSO ---
if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.title("⛪ Portal Ágape")
        t_log, t_cad = st.tabs(["Entrar", "Cadastro"])
        with t_log:
            with st.form("login_f"):
                e = st.text_input("E-mail")
                s = st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty:
                        u_data = res.iloc[0].to_dict()
                        if check_password_hash(u_data['senha'], s):
                            st.session_state.update({"logado": True, "user": u_data})
                            st.rerun()
                    st.error("Dados incorretos.")
        with t_cad:
            with st.form("cad_f"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)", {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Código: {c}")

# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    st.sidebar.markdown(f"### 🙏 Olá, **{u['nome']}**")
    
    # MENU SEMPRE VISÍVEL
    menu = ["📢 Mural", "📖 Bíblia", "📊 Transparência", "📻 Rádio", "📺 Live", "🙏 Orações"]
    if u['is_admin'] == 1: menu.append("⚙️ Admin")
    
    escolha = st.sidebar.radio("Navegação", menu)
    if st.sidebar.button("Sair"): 
        st.session_state.logado = False
        st.rerun()

    # --- MURAL ---
    if escolha == "📢 Mural":
        st.header("Mural da Comunidade")
        pd_data = consultar_db("SELECT * FROM palavra_dia ORDER BY id DESC LIMIT 1")
        if not pd_data.empty:
            p = pd_data.iloc[0]
            st.markdown(f'<div class="palavra-dia-card" style="background:#1e3a8a;color:white;padding:20px;border-radius:15px;"><h2>📖 Palavra do Dia</h2><p>"{p["versiculo"]}"</p><strong>— {p["referencia"]}</strong></div>', unsafe_allow_html=True)
        
        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in avisos.iterrows():
            st.markdown(f'<div style="background:white;padding:15px;margin-top:10px;border-radius:10px;border-left:5px solid #1e3a8a;"><h3>{r["titulo"]}</h3><p>{r["conteudo"]}</p></div>', unsafe_allow_html=True)

    # --- BÍBLIA ---
    elif escolha == "📖 Bíblia":
        st.header("Bíblia Sagrada")
        try:
            livros_df = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
            if not livros_df.empty:
                l_sel = st.selectbox("Livro", livros_df['livro'].tolist())
                cap_df = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l_sel})
                c_sel = st.selectbox("Capítulo", cap_df['capitulo'].tolist())
                versos = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l_sel, "c":c_sel})
                for _, v in versos.iterrows():
                    st.write(f"**{v['versiculo']}** {v['texto']}")
            else:
                st.info("Nenhum livro carregado. Vá em Admin e importe a Bíblia.")
        except:
            st.error("Erro ao carregar a Bíblia.")

    # --- ADMIN ---
    elif escolha == "⚙️ Admin":
        st.title("Painel Administrativo")
        t1, t2, t3, t4 = st.tabs(["📖 Importar Bíblia", "💰 Finanças", "📻 Rádio/Live", "👥 Membros"])
        
        with t1:
            st.subheader("Subir arquivo acf.json")
            f_bib = st.file_uploader("Selecione o arquivo da Bíblia", type=['json'])
            if f_bib and st.button("🚀 Iniciar Importação"):
                dados = json.load(f_bib)
                p = st.progress(0)
                for idx, liv_obj in enumerate(dados):
                    nm = liv_obj.get('name') or liv_obj.get('nome')
                    for ic, cl in enumerate(liv_obj.get('chapters', [])):
                        for iv, tv in enumerate(cl):
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)", 
                                           {"l": str(nm), "c": ic+1, "v": iv+1, "t": str(tv)})
                    p.progress((idx+1)/len(dados))
                st.success("Bíblia Importada com Sucesso!")

        with t2:
            st.subheader("Lançamentos")
            membros = consultar_db("SELECT nome, codigo FROM membros WHERE is_admin=0")
            if not membros.empty:
                with st.form("fin_f"):
                    n_s = st.selectbox("Membro", membros['nome'].tolist())
                    v_s = st.number_input("Valor", 0.0)
                    t_s = st.selectbox("Tipo", ["Dízimo", "Oferta", "Despesa"])
                    if st.form_submit_button("Salvar"):
                        c_s = membros[membros['nome'] == n_s]['codigo'].values[0]
                        v_f = v_s if t_s != "Despesa" else -v_s
                        executar_query("INSERT INTO financas (data, codigo_membro, valor, tipo) VALUES (:d,:c,:v,:t)", 
                                       {"d":datetime.now().strftime("%d/%m/%Y"), "c":c_s, "v":v_f, "t":t_s})
                        st.success("Lançado!")

        with t3:
            rl = st.text_input("URL Rádio (Stream)")
            ll = st.text_input("URL Live (YouTube)")
            la = st.selectbox("Live Ativa?", ["Não", "Sim"])
            if st.button("Salvar Configurações"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('radio_url', :v)", {"v":rl})
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_url', :v)", {"v":ll})
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_ativa', :v)", {"v":la})
                st.success("Salvo!")

    # --- OUTRAS ABAS (SIMPLIFICADAS PARA TESTE) ---
    elif escolha == "📊 Transparência":
        df = consultar_db("SELECT * FROM financas ORDER BY id DESC")
        st.metric("Saldo", f"R$ {df['valor'].sum() if not df.empty else 0:.2f}")
        st.dataframe(df)

    elif escolha == "📻 Rádio":
        conf = consultar_db("SELECT valor FROM configuracoes WHERE chave='radio_url'")
        if not conf.empty: st.audio(conf.iloc[0]['valor'])
        else: st.warning("Configure a rádio no Admin.")
