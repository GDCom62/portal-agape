import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import requests
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

def buscar_versiculo_api():
    sugestoes = [{"slug": "jo", "cap": 3}, {"slug": "sl", "cap": 23}, {"slug": "fp", "cap": 4}]
    escolha = random.choice(sugestoes)
    try:
        url = f"https://abibliadigital.com.br{escolha['slug']}/{escolha['cap']}"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            dados = res.json()
            v = random.choice(dados["verses"])
            return v.get("text", ""), f"{dados['book']['name']} {dados['chapter']}:{v.get('number', 1)}"
    except: pass
    return ("Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito...", "João 3:16")

LIVROS_BIBLIA = {
    "Gênesis": "gn", "Êxodo": "ex", "Levítico": "lv", "Números": "nu", "Deuteronômio": "dt",
    "Salmos": "sl", "Provérbios": "pv", "Isaías": "is", "Jeremias": "jr", "Mateus": "mt",
    "Marcos": "mc", "Lucas": "lc", "João": "jo", "Atos": "act", "Romanos": "rm",
    "1 Coríntios": "1co", "2 Coríntios": "2co", "Efésios": "ep", "Filipenses": "fp",
    "Colossenses": "cl", "Hebreus": "hb", "Tiago": "ja", "Apocalipse": "re"
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
                else: st.error("Usuário já existe.")

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
        txt, ref = buscar_versiculo_api()
        st.markdown(f'<div class="versiculo-box"><h4>"{txt}"</h4><span style="color:#fff;">— {ref}</span></div>', unsafe_allow_html=True)
        st.metric("Total de Membros", f"{len(consultar_db('SELECT id FROM membros'))} Irmãos")

    elif escolha == "Bíblia Completa":
        st.subheader("📖 Leitura da Bíblia Sagrada")
        c1, c2, c3 = st.columns(3)
        l_nome = c1.selectbox("Livro:", list(LIVROS_BIBLIA.keys()))
        c_num = c2.number_input("Capítulo:", min_value=1, max_value=150, value=1, step=1)
        ver = c3.selectbox("Versão:", ["NVI", "ACF"])
        if st.button("📖 Ler Capítulo", use_container_width=True):
            try:
                res = requests.get(f"https://abibliadigital.com.br{ver.lower()}/{LIVROS_BIBLIA[l_nome]}/{c_num}", timeout=4)
                if res.status_code == 200:
                    dados = res.json()
                    html = "<div class='leitura-box'>"
                    for v in dados["verses"]: html += f"<p><b style='color:#FFA500;'>{v['number']}.</b> {v['text']}</p>"
                    html += "</div>"
                    st.markdown(html, unsafe_allow_html=True)
                else: st.warning("Capítulo não localizado.")
            except: st.error("Erro de conexão com o servidor da Bíblia.")

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
            else: st.info("Nenhum membro.")

    elif escolha == "Financeiro":
        st.subheader("💰 Controle Financeiro")
        if st.session_state.nivel_atual == "Pastor":
            f1, f2 = st.tabs(["Lançar", "Livro Caixa"])
            with f1:
                with st.form("f_fin", clear_on_submit=True):
                    t_f = st.radio("Tipo", ["Entrada", "Saída"])
                    d_f = st.text_input("Descrição")
                    v_f = st.number_input("Valor", min_value=0.0)
                    if st.form_submit_button("Registrar"):
                        if d_f and v_f > 0:
                            executar_query("INSERT INTO financeiro (tipo, descricao, valor, data) VALUES (:t, :d, :v, :dt)", {"t": t_f, "d": d_f, "v": v_f, "dt": datetime.date.today().strftime('%d/%m/%Y')})
                            st.success("Registrado!")
            with f2:
                df_f = consultar_db("SELECT * FROM financeiro")
                if not df_f.empty: st.dataframe(df_f, use_container_width=True)
                else: st.info("Sem lançamentos.")
        else: st.error("Acesso restrito.")

    elif escolha == "Avisos":
        st.subheader("📢 Mural de Avisos")
        with st.expander("➕ Novo Aviso"):
            with st.form("f_av", clear_on_submit=True):
                t_a = st.text_input("Título")
                c_a = st.text_area("Conteúdo")
                if st.form_submit_button("Postar"):
                    if t_a and c_a:
                        executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)", {"t": t_a, "c": c_a, "d": datetime.date.today().strftime('%d/%m/%Y')})
                        st.success("Postado!")
                        st.rerun()
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        if not df_a.empty:
