import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import datetime

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. CONEXÃO BANCO DE DADOS LOCAL ---
@st.cache_resource
def inicializar_conexoes():
    return create_engine("sqlite:///agape_v60.db", connect_args={"check_same_thread": False, "timeout": 30})

engine = inicializar_conexoes()

# FUNÇÕES DE BANCO DECLARADAS NO TOPO (CORRIGE O NAMEERROR)
def executar_query(sql, params=None):
    with engine.begin() as conn: 
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try: 
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except: 
            return pd.DataFrame()

# Criação segura de todas as tabelas estruturais
executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telephone TEXT, cargo TEXT, data_cadastro TEXT, mes_aniversario TEXT, observacoes TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, membro_id INTEGER);")
executar_query("CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, conteudo TEXT, data TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, artista TEXT, text TEXT, arquivo_audio BLOB);")
executar_query("CREATE TABLE IF NOT EXISTS texto_biblico (id INTEGER PRIMARY KEY AUTOINCREMENT, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS escalas (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, ministerio TEXT, voluntario TEXT, periodo TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS escalas_visitas (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, irmao_visitado TEXT, endereço TEXT, responsavel TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS visitantes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telephone TEXT, data_visita TEXT, observacoes TEXT, precisa_visita TEXT DEFAULT 'Não');")

# Rotina de Carga e Sincronização em Lote da Bíblia ACF
def sincronizar_biblia_acf_lote():
    try:
        url_acf = "https://githubusercontent.com"
        res = requests.get(url_acf, timeout=15)
        if res.status_code == 200:
            lista_versiculos = []
            for l in res.json():
                for c_idx, cap in enumerate(l["chapters"]):
                    for v_idx, txt in enumerate(cap):
                        lista_versiculos.append({"l": l["name"], "c": c_idx + 1, "v": v_idx + 1, "t": txt})
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM texto_biblico;"))
                conn.execute(text("INSERT INTO texto_biblico (livro, capitulo, versiculo, texto) VALUES (:l, :c, :v, :t)"), lista_versiculos)
            return True
    except:
        pass
    return False

@st.cache_resource
def carga_inicial_sistema():
    admin_user = "admin@agape.com"
    if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
        executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": generate_password_hash("agape2026", method="scrypt")})
    
    if consultar_db("SELECT id FROM texto_biblico LIMIT 1").empty:
        sincronizar_biblia_acf_lote()

carga_inicial_sistema()

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

    menu = ["Início & Versículos", "Bíblia Completa", "Membros", "Cadastro de Visitantes", "Escala de Cultos", "Escala de Visitas", "Financeiro & Dízimos", "Avisos", "Louvores"]
    escolha = st.selectbox("Selecione a seção do Portal:", menu, key="nav_main")
    st.divider()

    if escolha == "Início & Versículos":
        st.subheader("⛪ Bem-vindo ao Portal Ágape")
        df_v_dia = consultar_db("SELECT texto, livro, capitulo, versiculo FROM texto_biblico WHERE livro LIKE '%João%' AND capitulo = 3 AND versiculo = 16")
        if not df_v_dia.empty:
            st.markdown(f'<div class="versiculo-box"><h4>"{df_v_dia.loc[0, "texto"]}"</h4><span style="color:#fff;">— {df_v_dia.loc[0, "livro"]} {df_v_dia.loc[0, "capitulo"]}:{df_v_dia.loc[0, "versiculo"]} (Tradução ACF)</span></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="versiculo-box"><h4>"Porque Deus amou o mundo de tal maneira..."</h4><span style="color:#fff;">— João 3:16</span></div>', unsafe_allow_html=True)
        
        # BLOCO DE ANIVERSARIANTES DO MÊS ATUAL
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        mes_atual_nome = meses[datetime.date.today().month - 1]
        st.write(f"🎉 **Aniversariantes do Mês de {mes_atual_nome}:**")
        df_aniv = consultar_db("SELECT nome, cargo, mes_aniversario FROM membros WHERE mes_aniversario = :m", {"m": mes_atual_nome})
        if not df_aniv.empty:
            for idx, row in df_aniv.iterrows():
                st.info(f"🎂 **{row['nome']}** ({row['cargo']})")
        else:
            st.caption("Nenhum aniversário de membro registrado para este mês.")
        st.metric("Total de Membros", f"{len(consultar_db('SELECT id FROM membros'))} Irmãos")

    elif escolha == "Bíblia Completa":
        st.subheader("📖 Bíblia Sagrada Completa — Tradução ACF")
        if st.session_state.nivel_atual == "Pastor":
            with st.expander("⚙️ Painel de Controle da Bíblia (Exclusivo Administrador)"):
                if st.button("🔄 Forçar Recarga Completa da Bíblia ACF", use_container_width=True):
                    with st.spinner("Atualizando acervo..."):
                        if sincronizar_biblia_acf_lote():
                            st.success("Bíblia ACF reinstalada com sucesso!")
                            st.rerun()
                        else: st.error("Erro na comunicação com o servidor JSON.")

        modo = st.radio("Escolha o modo:", ["Leitura por Capítulo", "Pesquisar por Palavra-Chave"], horizontal=True)
        if modo == "Leitura por Capítulo":
            df_livros = consultar_db("SELECT DISTINCT livro FROM texto_biblico ORDER BY id ASC")
            lista_livros = df_livros["livro"].tolist() if not df_livros.empty else ["Gênesis", "Salmos", "João"]
            c1, c2 = st.columns(2)
            l_nome = c1.selectbox("Selecione o Livro:", lista_livros)
            c_num = c2.number_input("Selecione o Capítulo:", min_value=1, max_value=150, value=1, step=1)
            if st.button("📖 Abrir Capítulo Completo", use_container_width=True):
                df_local = consultar_db("SELECT versiculo, texto FROM texto_biblico WHERE livro = :l AND capitulo = :c ORDER BY versiculo ASC", {"l": l_nome, "c": c_num})
                if not df_local.empty:
                    html = f"<div class='leitura-box'><h4>📜 {l_nome} — Capítulo {c_num} (ACF)</h4><br>"
                    for i, r in df_local.iterrows(): html += f"<p><b style='color:#FFA500;'>{r['versiculo']}.</b> {r['texto']}</p>"
                    html += "</div>"
                    st.markdown(html, unsafe_allow_html=True)
        else:
            termo = st.text_input("Digite a palavra ou frase:").strip()
