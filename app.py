import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import urllib.request
import json

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- CONEXÃO BANCO DE DADOS LOCAL ---
@st.cache_resource
def inicializar_conexoes():
    return create_engine("sqlite:///agape_v70.db", connect_args={"check_same_thread": False, "timeout": 30})

engine = inicializar_conexoes()

def executar_query(sql, params=None):
    with engine.begin() as conn: 
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try: 
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except: 
            return pd.DataFrame()

# Inicialização das tabelas essenciais do sistema e da Bíblia interna
executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cargo TEXT, data_cadastro TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS tabela_biblia (id INTEGER PRIMARY KEY AUTOINCREMENT, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT);")

admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    senha_hash = generate_password_hash("agape2026", method="pbkdf2:sha256")
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": senha_hash})

# --- POPULADOR AUTOMÁTICO DE BANCO DE DADOS (RODA SÓ UMA VEZ) ---
def sincronizar_biblia_no_banco():
    verificar = consultar_db("SELECT id FROM tabela_biblia LIMIT 1")
    if verificar.empty:
        url_fonte = "https://githubusercontent.com"
        try:
            req = urllib.request.Request(url_fonte, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                dados_originais = json.loads(response.read().decode('utf-8'))
            
            with engine.begin() as conn:
                for livro in dados_originais:
                    nome_livro = livro["name"]
                    for idx_cap, capitulo in enumerate(livro["chapters"], start=1):
                        for idx_ver, texto_verso in enumerate(capitulo, start=1):
                            conn.execute(
                                text("INSERT INTO tabela_biblia (livro, capitulo, versiculo, texto) VALUES (:l, :c, :v, :t)"),
                                {"l": nome_livro, "c": idx_cap, "v": idx_ver, "t": texto_verso}
                            )
            return True
        except:
            return False
    return True

# --- ESTILIZAÇÃO VISUAL ---
st.markdown("""
    <style>
    .stAppViewContainer { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important; }
    .versiculo-box { background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important; color: #FFD700 !important; padding: 25px !important; border-radius: 15px !important; border: 2px solid #FFD700 !important; text-align: center !important; }
    .leitura-box { background-color: #ffffff !important; padding: 15px; border-radius: 8px; color: #212529 !important; margin-bottom: 8px; border-left: 5px solid #FFA500; }
    </style>
""", unsafe_allow_html=True)

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

st.sidebar.title("🔐 Login Portal")
if not st.session_state.autenticado:
    u = st.sidebar.text_input("Usuário").strip()
    p = st.sidebar.text_input("Senha", type="password")
    if st.sidebar.button("Entrar", use_container_width=True):
        df = consultar_db("SELECT senha FROM usuarios WHERE usuario = :u", {"u": u})
        if not df.empty and check_password_hash(str(df.loc[0, 'senha']), p):
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.sidebar.error("Dados incorretos.")

if st.session_state.autenticado:
    st.sidebar.success("Conectado!")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

    menu = ["Início", "Bíblia", "Membros", "Financeiro"]
    escolha = st.selectbox("Selecione a Seção:", menu)
    st.divider()

    if escolha == "Início":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        st.markdown('<div class="versiculo-box"><h4>"Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna."</h4><span>— João 3:16</span></div>', unsafe_allow_html=True)

    elif escolha == "Bíblia":
        st.subheader("📖 Leitura da Bíblia Sagrada")
        
        # Garante a carga inicial no banco SQLite local
        base_pronta = sincronizar_biblia_no_banco()
        
        if base_pronta:
            df_livros = consultar_db("SELECT DISTINCT livro FROM tabela_biblia ORDER BY id ASC")
            if not df_livros.empty:
                lista_livros = df_livros['livro'].tolist()
                col_l, col_c = st.columns(2)
                with col_l:
                    livro_sel = st.selectbox("Livro:", lista_livros)
                
                df_caps = consultar_db("SELECT DISTINCT capitulo FROM tabela_biblia WHERE livro = :l ORDER BY capitulo ASC", {"l": livro_sel})
                lista_caps = df_caps['capitulo'].tolist()
                with col_c:
                    cap_sel = st.selectbox("Capítulo:", lista_caps)
                
                st.write(f"### {livro_sel} - Capítulo {cap_sel}")
                st.divider()
                
                df_versos = consultar_db("SELECT versiculo, texto FROM tabela_biblia WHERE livro = :l AND capitulo = :c ORDER BY versiculo ASC", {"l": livro_sel, "c": cap_sel})
                for idx, r in df_versos.iterrows():
                    st.markdown(f'<div class="leitura-box"><b>{r["versiculo"]}.</b> {r["texto"]}</div>', unsafe_allow_html=True)
            else:
                st.info("Configurando a base de dados pela primeira vez. Atualize a página em instantes.")
        else:
            st.error("Erro ao inicializar os textos. O servidor está sem conexão estável.")

    elif escolha == "Membros":
        st.subheader("👥 Gestão de Membros")
        with st.form("form_membro"):
            nome = st.text_input("Nome")
            cargo = st.text_input("Função")
            if st.form_submit_button("Cadastrar"):
                if nome:
                    executar_query("INSERT INTO membros (nome, cargo, data_cadastro) VALUES (:n, :c, :d)", {"n": nome, "c": cargo, "d": str(datetime.date.today())})
                    st.success("Cadastrado com sucesso!")
                    st.rerun()
        
        df_m = consultar_db("SELECT nome as Nome, cargo as Cargo, data_cadastro as [Data Cadastro] FROM membros")
        st.dataframe(df_m, use_container_width=True, hide_index=True)

    elif escolha == "Financeiro":
        st.subheader("💰 Livro Caixa")
        with st.form("form_fin"):
            tipo = st.selectbox("Movimento", ["Entrada", "Saída"])
            desc = st.text_input("Descrição")
            valor = st.number_input("Valor", min_value=0.0, format="%.2f")
            if st.form_submit_button("Lançar"):
                if desc and valor > 0:
                    executar_query("INSERT INTO financeiro (tipo, descricao, valor, data) VALUES (:t, :desc, :v, :d)", {"t": tipo, "desc": desc, "v": valor, "d": str(datetime.date.today())})
                    st.success("Lançado!")
                    st.rerun()

        df_f = consultar_db("SELECT tipo as Tipo, descricao as Descrição, valor as Valor, data as Data FROM financeiro")
        st.dataframe(df_f, use_container_width=True, hide_index=True)
else:
    st.info("Digite suas credenciais na barra lateral para liberar o acesso.")
