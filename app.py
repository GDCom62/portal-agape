import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import requests
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

executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, cargo TEXT, data_cadastro TEXT, mes_aniversario TEXT, observacoes TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, membro_id INTEGER);")
executar_query("CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, conteudo TEXT, data TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, artista TEXT, text TEXT, arquivo_audio BLOB);")
executar_query("CREATE TABLE IF NOT EXISTS texto_biblico (id INTEGER PRIMARY KEY AUTOINCREMENT, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT);")

@st.cache_resource
def baixar_e_instalar_biblia():
    if consultar_db("SELECT id FROM texto_biblico LIMIT 1").empty:
        try:
            res = requests.get("https://githubusercontent.com", timeout=10)
            if res.status_code == 200:
                with engine.begin() as conn:
                    for l in res.json():
                        for c_idx, cap in enumerate(l["chapters"]):
                            for v_idx, txt in enumerate(cap):
                                conn.execute(text("INSERT INTO texto_biblico (livro, capitulo, versiculo, texto) VALUES (:l, :c, :v, :t)"), {"l": l["name"], "c": c_idx + 1, "v": v_idx + 1, "t": txt})
        except: pass
    return True

baixar_e_instalar_biblia()

admin_user = "admin@agape.com"
if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
    executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": generate_password_hash("agape2026", method="scrypt")})

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

    menu = ["Início & Versículos", "Bíblia Completa", "Membros", "Financeiro", "Avisos", "Louvores"]
    escolha = st.selectbox("Selecione a seção do Portal:", menu, key="nav_main")
    st.divider()

    if escolha == "Início & Versículos":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        df_v_dia = consultar_db("SELECT texto, livro, capitulo, versiculo FROM texto_biblico WHERE livro LIKE '%João%' AND capitulo = 3 AND versiculo = 16")
        if not df_v_dia.empty:
            st.markdown(f'<div class="versiculo-box"><h4>"{df_v_dia.loc[0, "texto"]}"</h4><span style="color:#fff;">— {df_v_dia.loc[0, "livro"]} {df_v_dia.loc[0, "capitulo"]}:{df_v_dia.loc[0, "versiculo"]}</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="versiculo-box"><h4>"Porque Deus amou o mundo de tal maneira..."</h4><span style="color:#fff;">— João 3:16 (Configurando Base...)</span></div>', unsafe_allow_html=True)
        st.metric("Total de Membros", f"{len(consultar_db('SELECT id FROM membros'))} Irmãos")

    elif escolha == "Bíblia Completa":
        st.subheader("📖 Bíblia Sagrada Offline & Pesquisa")
        modo = st.radio("Escolha o modo:", ["Leitura por Capítulo", "Pesquisar por Palavra-Chave"], horizontal=True)
        
        if modo == "Leitura por Capítulo":
            df_livros = consultar_db("SELECT DISTINCT livro FROM texto_biblico ORDER BY id ASC")
            lista_livros = df_livros["livro"].tolist() if not df_livros.empty else ["Gênesis", "Êxodo", "Salmos", "João", "Apocalipse"]
            c1, c2 = st.columns(2)
            l_nome = c1.selectbox("Selecione o Livro:", lista_livros)
            c_num = c2.number_input("Selecione o Capítulo:", min_value=1, max_value=150, value=1, step=1)
            
            if st.button("📖 Abrir Capítulo Completo", use_container_width=True):
                df_local = consultar_db("SELECT versiculo, texto FROM texto_biblico WHERE livro = :l AND capitulo = :c ORDER BY versiculo ASC", {"l": l_nome, "c": c_num})
                if not df_local.empty:
                    html = f"<div class='leitura-box'><h4>📜 {l_nome} — Capítulo {c_num}</h4><br>"
                    for i, r in df_local.iterrows(): html += f"<p><b style='color:#FFA500;'>{r['versiculo']}.</b> {r['texto']}</p>"
                    html += "</div>"
                    st.markdown(html, unsafe_allow_html=True)
                else: st.warning("Sincronizando banco de dados... Aguarde uns instantes e tente carregar novamente.")
                    
        else:
            termo = st.text_input("Digite a palavra ou frase que deseja encontrar na Bíblia:").strip()
            if termo:
                df_busca = consultar_db("SELECT livro, capitulo, versiculo, texto FROM texto_biblico WHERE texto LIKE :t LIMIT 50", {"t": f"%{termo}%"})
                if not df_busca.empty:
                    st.success(f"Resultados encontrados para '{termo}':")
                    for i, r in df_busca.iterrows():
                        st.markdown(f"<div class='leitura-box'><b style='color:#FFA500;'>📖 {r['livro']} {r['capitulo']}:{r['versiculo']}</b><br><p style='margin-top:5px; font-style:italic;'>\"{r['texto']}\"</p></div>", unsafe_allow_html=True)
                else: st.warning(f"Nenhum versículo contendo '{termo}' foi localizado.")

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
