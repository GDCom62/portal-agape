import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

@st.cache_resource
def inicializar_conexoes():
    return create_engine("sqlite:///agape_v60.db", connect_args={"check_same_thread": False, "timeout": 30})

engine = inicializar_conexoes()

def executar_query(sql, params=None):
    with engine.begin() as conn: conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try: return pd.read_sql_query(text(sql), conn, params=params or {})
        except: return pd.DataFrame()

# Estrutura de Tabelas locais
executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telephone TEXT, cargo TEXT, data_cadastro TEXT, mes_aniversario TEXT, observacoes TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, membro_id INTEGER);")
executar_query("CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, conteudo TEXT, data TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, artista TEXT, text TEXT, arquivo_audio BLOB);")
executar_query("CREATE TABLE IF NOT EXISTS escalas (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ministerio TEXT, voluntario TEXT, periodo TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS escalas_visitas (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, irmao_visitado TEXT, endereço TEXT, responsavel TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS visitantes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telephone TEXT, data_visita TEXT, observacoes TEXT, precisa_visita TEXT DEFAULT 'Não');")
executar_query("CREATE TABLE IF NOT EXISTS patrimonio (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, quantidade INTEGER, valor REAL, estado TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY AUTOINCREMENT, objetivo TEXT, valor_alvo REAL, arrecadado REAL DEFAULT 0.0);")

admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": generate_password_hash("agape2026", method="scrypt")})

# --- ACERVO SAGRADO ALMEIDA CORRIGIDA FIEL (ACF) - 100% SEGURO E EM MEMÓRIA ---
BIBLIA_LOCAL = {
    "Gênesis": {
        1: ["1. No princípio criou Deus os céus e a terra.", "2. E a terra era sem forma e vazia; e havia trevas sobre la face do abismo.", "3. E disse Deus: Haja luz; e houve luz.", "4. E viu Deus que era boa la luz; e fez Deus separação entre la luz e as trevas.", "5. E Deus chamou à luz Dia; e às trevas chamou Noite."],
        12: ["1. Ora, o Senhor disse a Abrão: Sai-te da tua terra e da tua parentela.", "2. E far-te-ei uma grande nação, e abençoar-te-ei.", "3. E abençoarei os que te abençoarem."]
    },
    "Josué": {
        1: ["1. E sucedeu, depois da morte de Moisés, que o Senhor falou a Josué.", "5. Ninguém te poderá resistir, todos os dias da tua vida; como fui com Moisés, assim serei contigo; não te deixarei nem te desampararei.", "9. Não te mandei eu? Sê forte e corajoso; não temas, nem te espantes; porque o Senhor teu Deus é contigo, por onde quer que andares."]
    },
    "Salmos": {
        23: ["1. O Senhor é o meu pastor, nada me faltará.", "2. Deitar-me faz em verdes pastos, guia-me mansamente a águas tranquilas.", "3. Refrigera la minha alma; guia-me pelas veredas da justiça.", "4. Ainda que eu andasse pelo vale da sombra da morte, não temeria mal algum.", "5. Preparas uma mesa perante mim na presença dos meus inimigos.", "6. Certamente que la bondade e la misericórdia me seguirão todos os dias."],
        91: ["1. Aquele que habita no esconderijo do Altíssimo, à sombra do Onipotente descansará.", "2. Direi do Senhor: Ele é o meu refúgio e la minha fortaleza.", "3. Porque ele te livrará do laço do passarinheiro, e da peste perniciosa.", "4. Ele te cobrirá com as suas penas, e debaixo das suas asas te confiarás.", "7. Mil cairão ao teu lado, e dez mil à tua direita, mas não chegará a ti."],
        121: ["1. Levantarei os meus olhos para os montes, de onde vem o meu socorro?", "2. O meu socorro vem do Senhor, que fez os céus e la terra.", "3. Não deixará vacilar o teu pé; aquele que te guarda não tosquenejará."]
    },
    "Provérbios": {
        3: ["5. Confia no Senhor de todo o teu coração, e não te estribes no teu próprio entendimento.", "6. Reconhece-o em todos os teus caminhos, e ele endireitará as tuas veredas."]
    },
    "Isaías": {
        40: ["29. Dá força ao cansado, e multiplica as forças ao que não tem nenhum vigor.", "31. Mas os que esperam no Senhor renovarão as suas forças, subirão com asas como águias; correrão, e não se cansarão; caminharão, e não se fatigarão."],
        41: ["10. Não temas, porque eu sou contigo; não te assombres, porque eu sou o teu Deus; eu te fortaleço, e te ajudo, e te sustento com la destra da minha justiça."]
    },
    "Mateus": {
        6: ["9. Portanto, vós orareis assim: Pai nosso, que estás nos céus.", "10. Venha o teu reino, seja feita la tua vontade.", "33. Mas, buscai primeiro o reino de Deus, e la sua justiça, e todas estas coisas vos serão acrescentadas."]
    },
    "João": {
        3: ["16. Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha la vida eterna.", "17. Porque Deus enviou o seu Filho ao mundo, não para condenar o mundo, mas para que o mundo fosse salvo por ele."],
        14: ["1. Não se turbe o teu coração; credes em Deus, crede também em mim.", "6. Disse-lhe Jesus: Eu sou o caminho, e la verdade, e la vida; ninguém vem ao Pai, senão por mim."]
    },
    "Romanos": {
        8: ["1. Portanto, agora nenhuma condenação há para os que estão em Cristo Jesus.", "28. E sabemos que todas as coisas contribuem juntamente para o bem daqueles que amam a Deus.", "31. Que diremos, pois, a estas coisas? Se Deus é por nós, quem será contra nós?"]
    },
    "Filipenses": {
        4: ["13. Tudo posso naquele que me fortalece.", "19. O meu Deus, segundo as suas riquezas, suprirá todas as vossas necessidades em glória."]
    },
    "Apocalipse": {
        22: ["13. Eu sou o Alfa e o Ômega, o princípio e o fim, o primeiro e o derradeiro.", "20. Aquele que testifica estas coisas diz: Certamente cedo venho. Amém. Ora vem, Senhor Jesus."]
    }
}

st.markdown("""
    <style>
    .stAppViewContainer { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important; }
    .versiculo-box { background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important; color: #FFD700 !important; padding: 25px !important; border-radius: 15px !important; border: 2px solid #FFD700 !important; text-align: center !important; }
    .leitura-box { background-color: #ffffff !important; padding: 20px; border-radius: 12px; border: 1px solid #e0a800; color: #212529 !important; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

if "autenticado" not in st.session_state:
    st.session_state.autenticado, st.session_state.usuario_atual, st.session_state.nivel_atual = False, None, "Membro"

st.sidebar.title("🔐 Acesso ao Portal")
if not st.session_state.autenticado:
    tab_log, tab_new = st.sidebar.tabs(["Entrar", "Novo Acesso"])
    with tab_log:
        u = st.text_input("Usuário", value="admin@agape.com", key="u_log").strip()
        p = st.text_input("Senha", type="password", value="agape2026", key="p_log")
        if st.button("Autenticar", use_container_width=True):
            df = consultar_db("SELECT senha, nivel FROM usuarios WHERE usuario = :u", {"u": u})
            if not df.empty and check_password_hash(str(df.loc[0, 'senha']), p):
                st.session_state.autenticado, st.session_state.usuario_atual, st.session_state.nivel_atual = True, u, df.loc[0, 'nivel']
                st.rerun()
            else: st.error("Dados incorretos.")
    with tab_new:
        nu = st.text_input("E-mail corporativo", key="u_reg").strip()
        np = st.text_input("Senha de acesso", type="password", key="p_reg")
        if st.button("Cadastrar conta", use_container_width=True):
            if nu and len(np) >= 4:
                if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": nu}).empty:
                    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Membro')", {"u": nu, "s": generate_password_hash(np, method="scrypt")})
                    st.success("Conta criada!")

if st.session_state.autenticado:
    st.sidebar.success(f"Conectado: {st.session_state.usuario_atual}")
    if st.sidebar.button("🚪 Desconectar Sistema", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

    menu = ["Início & Versículos", "Bíblia Completa", "Membros", "Cadastro de Visitantes", "Escala de Cultos", "Escala de Visitas", "Financeiro & Dízimos", "Patrimônio da Igreja", "Avisos", "Louvores"]
    escolha = st.selectbox("Selecione a seção do Portal:", menu, key="nav_main")
    st.divider()

    if escolha == "Início & Versículos":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        st.markdown('<div class="versiculo-box"><h4>"Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna."</h4><span style="color:#fff;">— João 3:16 (ACF)</span></div>', unsafe_allow_html=True)
