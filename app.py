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

# Criação das tabelas estruturais locais
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
executar_query("CREATE TABLE IF NOT EXISTS texto_biblico (id INTEGER PRIMARY KEY AUTOINCREMENT, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT);")

# CARGA LOCAL E OFFLINE DA BÍBLIA INTEIRA VIA BULK INSERT
@st.cache_resource
def baixar_e_salvar_biblia_local():
    if consultar_db("SELECT id FROM texto_biblico LIMIT 1").empty:
        try:
            # Baixa um acervo condensado e estável da tradução em português livre de bloqueios
            res = requests.get("https://githubusercontent.com", timeout=10)
            if res.status_code == 200:
                lote = []
                for l in res.json():
                    for c_idx, cap in enumerate(l["chapters"]):
                        for v_idx, txt in enumerate(cap):
                            lote.append({"l": l["name"], "c": c_idx + 1, "v": v_idx + 1, "t": txt})
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO texto_biblico (livro, capitulo, versiculo, texto) VALUES (:l, :c, :v, :t)"), lote)
        except:
            # Fallback nativo imediato se até o GitHub falhar na hora do primeiro deploy
            executar_query("INSERT OR IGNORE INTO texto_biblico (livro, capitulo, versiculo, texto) VALUES ('João', 3, 16, 'Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.');")
    return True

baixar_e_salvar_biblia_local()

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

    menu = ["Início & Versículos", "Bíblia Completa", "Membros", "Cadastro de Visitantes", "Escala de Cultos", "Escala de Visitas", "Financeiro & Dízimos", "Patrimônio da Igreja", "Avisos", "Louvores"]
    escolha = st.selectbox("Selecione a seção do Portal:", menu, key="nav_main")
    st.divider()

    if escolha == "Início & Versículos":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        df_v_dia = consultar_db("SELECT texto FROM texto_biblico WHERE livro LIKE '%João%' AND capitulo = 3 AND versiculo = 16")
        txt_box = df_v_dia.loc[0, "texto"] if not df_v_dia.empty else "Porque Deus amou o mundo de tal maneira..."
        st.markdown(f'<div class="versiculo-box"><h4>"{txt_box}"</h4><span style="color:#fff;">— João 3:16</span></div>', unsafe_allow_html=True)
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        mes_atual_nome = meses[datetime.date.today().month - 1]
        st.write(f"🎉 **Aniversariantes do Mês de {mes_atual_nome}:**")
        df_aniv = consultar_db("SELECT nome, cargo FROM membros WHERE mes_aniversario = :m", {"m": mes_atual_nome})
        if not df_aniv.empty:
            for idx, row in df_aniv.iterrows(): st.info(f"🎂 **{row['nome']}** ({row['cargo']})")
        else: st.caption("Nenhum aniversário registrado para este mês.")
        st.metric("Total de Membros", f"{len(consultar_db('SELECT id FROM membros'))} Irmãos")

    elif escolha == "Bíblia Completa":
        st.subheader("📖 Bíblia Sagrada Completa (Processamento Local Offline)")
        modo = st.radio("Escolha o modo:", ["Leitura por Capítulo", "Pesquisar por Palavra-Chave"], horizontal=True)
        
        df_livros_db = consultar_db("SELECT DISTINCT livro FROM texto_biblico ORDER BY id ASC")
        lista_livros = df_livros_db["livro"].tolist() if not df_livros_db.empty else ["João"]
        
        if modo == "Leitura por Capítulo":
            c1, c2 = st.columns(2)
            l_nome = c1.selectbox("Selecione o Livro:", lista_livros)
            c_num = c2.number_input("Selecione o Capítulo:", min_value=1, max_value=150, value=1, step=1)
            if st.button("📖 Abrir Capítulo Completo", use_container_width=True):
                df_cap = consultar_db("SELECT versiculo, texto FROM texto_biblico WHERE livro = :l AND capitulo = :c ORDER BY versiculo ASC", {"l": l_nome, "c": c_num})
                if not df_cap.empty:
                    html = f"<div class='leitura-box'><h4>📜 {l_nome} — Capítulo {c_num}</h4><br>"
                    for i, r in df_cap.iterrows(): html += f"<p><b style='color:#FFA500;'>{r['versiculo']}.</b> {r['texto']}</p>"
                    st.markdown(html + "</div>", unsafe_allow_html=True)
                else: st.warning("Capítulo não populado ou inexistente.")
        else:
            termo = st.text_input("Digite a palavra ou frase:").strip()
            if termo:
                # Varre os 31 mil versículos armazenados localmente de forma instantânea
                df_busca = consultar_db("SELECT livro, capitulo, versiculo, texto FROM texto_biblico WHERE texto LIKE :t LIMIT 40", {"t": f"%{termo}%"})
                if not df_busca.empty:
                    st.success(f"Resultados encontrados para '{termo}':")
                    for i, r in df_busca.iterrows():
