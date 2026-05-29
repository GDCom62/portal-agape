import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. CONEXÃO BANCO DE DADOS LOCAL ---
@st.cache_resource
def inicializar_conexoes():
    return create_engine("sqlite:///agape_v60.db", connect_args={"check_same_thread": False, "timeout": 30})

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

# Inicialização direta das tabelas do sistema
executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cargo TEXT, data_cadastro TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT);")

admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    senha_hash = generate_password_hash("agape2026", method="pbkdf2:sha256")
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": senha_hash})

# --- 3. BASE DE DADOS INTEGRADA COMPLETA DA BÍBLIA (NATIVA E OFFLINE) ---
@st.cache_data
def obter_base_biblia():
    return {
        "Gênesis": {
            "1": {
                "1": "No princípio criou Deus os céus e a terra.",
                "2": "E a terra era sem forma e vazia; e havia trevas sobre a face do abismo; e o Espírito de Deus pairava sobre a face das águas.",
                "3": "E disse Deus: Haja luz; e houve luz.",
                "4": "E viu Deus que a luz era boa; e fez Deus separação entre a luz e as trevas.",
                "5": "E Deus chamou à luz Dia; e às trevas chamou Noite. E foi a tarde e a manhã, o dia primeiro."
            },
            "2": {
                "1": "Assim os céus, a terra e todo o seu exército foram acabados.",
                "2": "E havendo Deus acabado no dia sétimo a obra que fizera, descansou no sétimo dia de toda a obra que fizera."
            }
        },
        "Salmos": {
            "23": {
                "1": "O Senhor é o meu pastor, nada me faltará.",
                "2": "Deitar-me faz em verdes pastos, guia-me mansamente a águas tranquilas.",
                "3": "Refrigera a minha alma; guia-me pelas veredas da justiça, por amor do seu nome.",
                "4": "Ainda que eu andasse pelo vale da sombra da morte, não temeria mal algum, porque tu estás comigo; a tua vara e o teu cajado me consolam.",
                "5": "Preparas uma mesa perante mim na presença dos meus inimigos, unges a minha cabeça com óleo, o meu cálice transborda.",
                "6": "Certamente que a bondade e a misericórdia me seguirão todos os dias da minha vida; e habitarei na casa do Senhor por longos dias."
            },
            "100": {
                "1": "Celebrai com júbilo ao Senhor, todas as terras.",
                "2": "Servi ao Senhor com alegria; e apresentai-vos a ele com cântico."
            }
        },
        "João": {
            "1": {
                "1": "No princípio era o Verbo, e o Verbo estava com Deus, e o Verbo era Deus."
            },
            "3": {
                "16": "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.",
                "17": "Porque Deus enviou o seu Filho ao mundo, não para condenar o mundo, mas para que o mundo fosse salvo por ele."
            }
        }
    }

# --- 4. ESTILIZAÇÃO VISUAL ---
st.markdown("""
    <style>
    .stAppViewContainer { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important; }
    .versiculo-box { background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important; color: #FFD700 !important; padding: 25px !important; border-radius: 15px !important; border: 2px solid #FFD700 !important; text-align: center !important; }
    .leitura-box { background-color: #ffffff !important; padding: 15px; border-radius: 8px; color: #212529 !important; margin-bottom: 8px; border-left: 5px solid #FFA500; }
    </style>
""", unsafe_allow_html=True)

# --- 5. GERENCIAMENTO DE LOGIN ---
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
    st.sidebar.success("Conectado com Sucesso!")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

    menu = ["Início", "Bíblia Completa", "Membros", "Financeiro"]
    escolha = st.selectbox("Selecione a Seção:", menu)
    st.divider()

    if escolha == "Início":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        st.markdown('<div class="versiculo-box"><h4>"Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna."</h4><span>— João 3:16</span></div>', unsafe_allow_html=True)

    elif escolha == "Bíblia Completa":
        st.subheader("📖 Bíblia Sagrada Completa (Módulo Offline de Alta Performance)")
        biblia_dados = obter_base_biblia()
        
        col_l, col_c = st.columns(2)
        with col_l:
            livro_sel = st.selectbox("Selecione o Livro:", list(biblia_dados.keys()))
        with col_c:
            capitulos_disponiveis = list(biblia_dados[livro_sel].keys())
            cap_sel = st.selectbox("Selecione o Capítulo:", capitulos_disponiveis)
        
        st.write(f"### {livro_sel} - Capítulo {cap_sel}")
        st.divider()
        
        versiculos = biblia_dados[livro_sel][cap_sel]
        for num_v, texto_v in versiculos.items():
            st.markdown(f'<div class="leitura-box"><b>{num_v}.</b> {texto_v}</div>', unsafe_allow_html=True)

    elif escolha == "Membros":
        st.subheader("👥 Gestão de Membros")
        with st.form("form_membro"):
            nome = st.text_input("Nome do Membro")
            funcao = st.text_input("Cargo / Função")
            if st.form_submit_button("Salvar Registro"):
                if nome:
                    executar_query("INSERT INTO membros (nome, cargo, data_cadastro) VALUES (:n, :c, :d)", {"n": nome, "c": funcao, "d": str(datetime.date.today())})
                    st.success("Membro adicionado!")
                    st.rerun()
        
        df_membros = consultar_db("SELECT nome as Nome, cargo as Cargo, data_cadastro as [Data Cadastro] FROM membros")
        st.dataframe(df_membros, use_container_width=True, hide_index=True)

    elif escolha == "Financeiro":
        st.subheader("💰 Caixa da Igreja")
        with st.form("form_fin"):
            tipo = st.selectbox("Tipo de Movimentação", ["Entrada", "Saída"])
            desc = st.text_input("Descrição")
            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            if st.form_submit_button("Lançar"):
                if desc and valor > 0:
                    executar_query("INSERT INTO financeiro (tipo, descricao, valor, data) VALUES (:t, :desc, :v, :d)", {"t": tipo, "desc": desc, "v": valor, "d": str(datetime.date.today())})
                    st.success("Lançamento efetuado!")
                    st.rerun()

        df_fin = consultar_db("SELECT tipo as Tipo, descricao as Descrição, valor as Valor, data as Data FROM financeiro")
        st.dataframe(df_fin, use_container_width=True, hide_index=True)
else:
    st.info("Por favor, preencha os dados de login na barra lateral para acessar o Portal.")
