import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import datetime
import random

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. CONEXÃO BANCO DE DADOS ---
@st.cache_resource
def inicializar_conexoes():
    engine = create_engine("sqlite:///agape_v60.db", connect_args={"check_same_thread": False, "timeout": 30})
    return engine

engine = inicializar_conexoes()

def executar_query(sql, params=None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except Exception:
            return pd.DataFrame()

# --- 3. INTEGRAÇÃO REAL COM A BÍBLIA DIGITAL ---
def buscar_versiculo_api():
    sugestoes = [
        {"slug": "jo", "cap": 3}, {"slug": "sl", "cap": 23},
        {"slug": "fp", "cap": 4}, {"slug": "is", "cap": 41},
        {"slug": "rm", "cap": 8}, {"slug": "mt", "cap": 6}
    ]
    escolha = random.choice(sugestoes)
    try:
        # URL da API Oficial pública com token demonstrativo estável
        url = f"https://abibliadigital.com.br{escolha['slug']}/{escolha['cap']}"
        resposta = requests.get(url, timeout=4)
        if resposta.status_code == 200:
            dados = resposta.json()
            if "verses" in dados and len(dados["verses"]) > 0:
                v_sorteado = random.choice(dados["verses"])
                return v_sorteado.get("text", ""), f"{dados['book']['name']} {dados['chapter']}:{v_sorteado.get('number', 1)}"
    except Exception:
        pass
    return ("Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.", "João 3:16")

# Criar tabelas necessárias de forma segura
executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, cargo TEXT, data_cadastro TEXT, mes_aniversario TEXT, observacoes TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, membro_id INTEGER);")
executar_query("CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, conteudo TEXT, data TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, artista TEXT, letra TEXT, arquivo_audio BLOB);")

# Sincronizar dados do Admin padrão
def verificar_e_criar_admin():
    admin_usuario = "admin@agape.com"
    hash_admin = generate_password_hash("agape2026", method="scrypt")
    existe = consultar_db("SELECT id FROM usuarios WHERE usuario = :user", {"user": admin_usuario})
    if existe.empty:
        executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:user, :senha, 'Pastor')", {"user": admin_usuario, "senha": hash_admin})

verificar_e_criar_admin()

# --- 4. LAYOUT DESIGN CUSTOMIZADO (AMARELO OURO CORRIGIDO) ---
st.markdown("""
    <style>
    .stAppViewContainer {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important;
    }
    .versiculo-box {
        background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important;
        color: #FFD700 !important;
        padding: 25px !important;
        border-radius: 15px !important;
        box-shadow: 0 8px 20px rgba(0,0,0,0.2) !important;
        margin-bottom: 20px !important;
        border: 2px solid #FFD700 !important;
        text-align: center !important;
    }
    .texto-sagrado-grande {
        font-size: 20px !important;
        font-family: 'Georgia', serif !important;
        line-height: 1.5 !important;
    }
    .numero-versiculo {
        color: #ffffff !important;
        font-weight: bold !important;
        display: block;
        margin-top: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. GESTÃO DE ACESSO (SESSÃO DE LOGIN REPARADA) ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario_atual = None
    st.session_state.nivel_atual = "Membro"

st.sidebar.title("🔐 Acesso ao Portal")

if not st.session_state.autenticado:
    tab_log, tab_new = st.sidebar.tabs(["Entrar", "Novo Acesso"])
    
    with tab_log:
        campo_usuario = st.text_input("E-mail/Usuário", value="admin@agape.com", key="u_login").strip()
        campo_senha = st.text_input("Senha", type="password", value="agape2026", key="p_login")
        if st.button("Autenticar", use_container_width=True):
            df_u = consultar_db("SELECT senha, nivel FROM usuarios WHERE usuario = :user", {"user": campo_usuario})
            if not df_u.empty and check_password_hash(str(df_u.loc[0, 'senha']), campo_senha):
                st.session_state.autenticado = True
                st.session_state.usuario_atual = campo_usuario
                st.session_state.nivel_atual = df_u.loc[0, 'nivel']
                st.rerun()
            else:
                st.error("Dados incorretos.")
                
    with tab_new:
        reg_user = st.text_input("E-mail corporativo", key="u_reg").strip()
        reg_pass = st.text_input("Senha de acesso", type="password", key="p_reg")
        if st.button("Cadastrar conta", use_container_width=True):
            if reg_user and len(reg_pass) >= 4:
                check = consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": reg_user})
                if check.empty:
                    h_pass = generate_password_hash(reg_pass, method="scrypt")
                    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Membro')", {"u": reg_user, "s": h_pass})
                    st.success("Conta criada! Acesse pela aba 'Entrar'.")
                else:
                    st.error("Usuário já existe.")
            else:
                st.warning("Preencha os campos (mínimo 4 dígitos).")

# --- 6. PAINEL DO PORTAL (SÓ ABRE COM LOGIN ATIVO) ---
if st.session_state.autenticado:
    st.sidebar.success(f"Conectado: {st.session_state.usuario_atual}")
    if st.sidebar.button("🚪 Desconectar Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None
        st.rerun()

    menu = ["Início & Versículos", "Membros", "Financeiro", "Avisos", "Louvores"]
    escolha = st.selectbox("Selecione a seção do Portal:", menu, key="navigation_box_main")
    st.divider()

    if escolha == "Início & Versículos":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        
        texto_v, ref_v = buscar_versiculo_api()
        st.markdown(f"""
            <div class="versiculo-box">
                <div class="texto-sagrado-grande">
                    "{texto_v}"
                    <span class="numero-versiculo">— {ref_v}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        df_m_total = consultar_db("SELECT id FROM membros")
        st.metric("Total de Membros Cadastrados", f"{len(df_m_total)} Irmãos")

    elif escolha == "Membros":
        st.subheader("👥 Gestão de Membros")
        aba_ver, aba_cadastrar = st.tabs(["Ver Membros", "Cadastrar Novo Membro"])
        
        with aba_cadastrar:
            with st.form("cad_membro_form", clear_on_submit=True):
                nome = st.text_input("Nome do Membro")
                telefone = st.text_input("Telefone / WhatsApp")
                cargo = st.selectbox("Cargo", ["Membro", "Diácono", "Presbítero", "Evangelista", "Pastor", "Missionária"])
                mes_aniv = st.selectbox("Mês Aniversário", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
                obs = st.text_area("Observações")
                if st.form_submit_button("Salvar Membro"):
                    if nome:
                        dt = datetime.date.today().strftime('%d/%m/%Y')
                        executar_query("INSERT INTO membros (nome, telefone, cargo, data_cadastro, mes_aniversario, observacoes) VALUES (:nome, :tel, :cargo, :dt, :mes, :obs)", {"nome": nome, "tel": telefone, "cargo": cargo, "dt": dt, "mes": mes_aniv, "obs": obs})
                        st.success(f"{nome} cadastrado!")
                    else:
                        st.error("Nome obrigatório.")
        with aba_ver:
            busca = st.text_input("Buscar por nome:", key="search_membro_input")
            df_membros = consultar_db("SELECT * FROM membros WHERE nome LIKE :b", {"b": f"%{busca}%"}) if busca else consultar_db("SELECT * FROM membros")
            if not df_membros.empty:
                for idx, row in df_membros.iterrows():
                    st.write(f"**👤 {row['nome']}** - {row['cargo']} | Contato: {row['telefone']}")
                    if st.button(f"Excluir {row['nome']}", key=f"del_m_{row['id']}"):
                        executar_query("DELETE FROM membros WHERE id = :id", {"id": row['id']})
                        st.rerun()
                    st.divider()

    elif escolha == "Financeiro":
        st.subheader("💰 Controle Financeiro")
        if st.session_state.nivel_atual == "Pastor":
            aba_lancar, aba_caixa = st.tabs(["Lançar Movimentação", "Livro Caixa"])
            with aba_lancar:
                with st.form("cad_financeiro_form", clear_on_submit=True):
                    tipo = st.radio("Tipo", ["Entrada (Dízimo/Oferta)", "Saída (Despesa)"])
                    desc = st.text_input("Descrição / Finalidade")
