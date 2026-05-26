import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import random

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

# --- BANCO DE DADOS LOCAL DE TEXTOS SAGRADOS (100% OFFLINE) ---
BIBLIA_LOCAL = {
    "Gênesis": {
        1: ["1. No princípio criou Deus os céus e a terra.", "2. E a terra era sem forma e vazia; e havia trevas sobre a face do abismo.", "3. E disse Deus: Haja luz; e houve luz.", "4. Vit Deus que a luz era boa; e fez separação entre a luz e as trevas."],
        2: ["1. Assim os céus, a terra e todo o seu exército foram acabados.", "2. E havendo Deus acabado no dia sétimo a sua obra, descansou."]
    },
    "Salmos": {
        23: ["1. O Senhor é o meu pastor, nada me faltará.", "2. Deitar-me faz em verdes pastos, guia-me mansamente a águas tranquilas.", "3. Refrigera a minha alma; guia-me pelas veredas da justiça por amor do seu nome.", "4. Ainda que eu andasse pelo vale da sombra da morte, não temeria mal algum, porque tu estás comigo.", "5. Preparas uma mesa perante mim na presença dos meus inimigos, unges a minha cabeça com óleo, o meu cálice transborda.", "6. Certamente que a bondade e a misericórdia me seguirão todos os dias da minha vida; e habitarei na casa do Senhor por longos dias."],
        91: ["1. Aquele que habita no esconderijo do Altíssimo, à sombra do Onipotente descansará.", "2. Direi do Senhor: Ele é o meu Deus, o meu refúgio, a minha fortaleza, e nele confiarei.", "3. Porque ele te livrará do laço do passarinheiro, e da peste perniciosa.", "4. Ele te cobrirá com as suas penas, e debaixo das suas asas te confiarás; a sua verdade será o teu escudo e broquel.", "5. Não terás medo dos terrores da noite, nem da seta que voa de dia."]
    },
    "Mateus": {
        6: ["9. Portanto, vós orareis assim: Pai nosso, que estás nos céus, santificado seja o teu nome;", "10. Venha o teu reino, seja feita a tua vontade, assim na terra como no céu;", "11. O pão nosso de cada dia nos dá hoje;", "12. E perdoa-me as nossas dívidas, assim como nós perdoamos aos nossos devedores;", "13. E não nos induzas à tentação; mas livra-nos do mal; porque teu é o reino, e o poder, e a glória, para sempre. Amém."]
    },
    "João": {
        3: ["16. Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.", "17. Porque Deus enviou o seu Filho ao mundo, não para condenar o mundo, mas para que o mundo fosse salvo por ele."]
    },
    "Romanos": {
        8: ["1. Portanto, agora nenhuma condenação há para os que estão em Cristo Jesus, que não andam segundo a carne, mas segundo o Espírito.", "28. E sabemos que todas as coisas contribuem juntamente para o bem daqueles que amam a Deus."]
    },
    "Filipenses": {
        4: ["13. Tudo posso naquele que me fortalece.", "19. O meu Deus, segundo as suas riquezas, suprirá todas as vossas necessidades em glória, por Cristo Jesus."]
    }
}

executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, cargo TEXT, data_cadastro TEXT, mes_aniversario TEXT, observacoes TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, membro_id INTEGER);")
executar_query("CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, conteudo TEXT, data TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, artista TEXT, text TEXT, arquivo_audio BLOB);")

admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": generate_password_hash("agape2026", method="scrypt")})

st.markdown("""
    <style>
    .stAppViewContainer { background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important; }
    .versiculo-box { background: linear-gradient(135deg, #212529 0%, #0d0d0d 100%) !important; color: #FFD700 !important; padding: 25px !important; border-radius: 15px !important; border: 2px solid #FFD700 !important; text-align: center !important; }
    .leitura-box { background-color: #ffffff !important; padding: 25px; border-radius: 12px; border: 1px solid #e0a800; color: #212529 !important; }
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

    menu = ["Início & Versículos", "Bíblia Completa", "Membros", "Financeiro", "Avisos", "Louvores"]
    escolha = st.selectbox("Selecione a seção do Portal:", menu, key="nav_main")
    st.divider()

    if escolha == "Início & Versículos":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        # Versículo do dia puxado instantaneamente do banco em memória
        txt_v = BIBLIA_LOCAL["João"][3][0]
        st.markdown(f'<div class="versiculo-box"><h4>{txt_v}</h4><span style="color:#fff;">— João 3:16</span></div>', unsafe_allow_html=True)
        st.metric("Total de Membros", f"{len(consultar_db('SELECT id FROM membros'))} Irmãos")

    elif escolha == "Bíblia Completa":
        st.subheader("📖 Leitura da Bíblia Sagrada (Módulo Local)")
        c1, c2 = st.columns(2)
        l_nome = c1.selectbox("Selecione o Livro:", list(BIBLIA_LOCAL.keys()))
        c_num = c2.selectbox("Selecione o Capítulo:", list(BIBLIA_LOCAL[l_nome].keys()))
        
        if st.button("📖 Ler Capítulo", use_container_width=True):
            html = "<div class='leitura-box'><h4>📜 Tradução: Almeida Corrigida Fiel</h4><br>"
            for versiculo in BIBLIA_LOCAL[l_nome][c_num]:
                html += f"<p>{versiculo}</p>"
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

    elif escolha == "Membros":
        st.subheader("👥 Gestão de Membros")
        a1, a2 = st.tabs(["Ver", "Cadastrar"])
        with a2:
            with st.form("f_memb", clear_on_submit=True):
                m_nome = st.text_input("Nome")
                m_tel = st.text_input("Telefone")
                m_cargo = st.selectbox("Cargo", ["Membro", "Diácono", "Presbítero", "Pastor"])
                if st.form_submit_button("Salvar"):
                    if m_nome:
                        executar_query("INSERT INTO membros (nome, telefone, cargo, data_cadastro) VALUES (:n, :t, :c, :d)", {"n": m_nome, "t": m_tel, "c": m_cargo, "d": datetime.date.today().strftime('%d/%m/%Y')})
                        st.success("Salvo!")
        with a1:
            df_m = consultar_db("SELECT * FROM membros")
            if not df_m.empty:
                for i, r in df_m.iterrows():
                    st.write(f"**👤 {r['nome']}** - {r['cargo']}")
                    if st.button("Excluir", key=f"del_m_{r['id']}"):
                        executar_query("DELETE FROM membros WHERE id = :id", {"id": r['id']})
                        st.rerun()
                    st.divider()
            else: st.info("Nenhum membro.")

    elif escolha == "Financeiro":
        st.subheader("💰 Controle Financeiro")
        if st.session_state.nivel_atual == "Pastor":
            f1, f2 = st.tabs(["Lançar", "Livro Caixa"])
            with f1:
                with st.form("f_fin", clear_on_submit=True):
                    t_f = st.radio("Tipo", ["Entrada", "Saída"])
                    d_f = st.text_input("Descrição")
