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

# Criação das tabelas estruturais
executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, cargo TEXT, data_cadastro TEXT, mes_aniversario TEXT, observacoes TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, membro_id INTEGER);")
executar_query("CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, conteudo TEXT, data TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, artista TEXT, text TEXT, arquivo_audio BLOB);")

# TABELA DA BÍBLIA COMPLETA EM MEMÓRIA PERSISTENTE
executar_query("""
CREATE TABLE IF NOT EXISTS texto_biblico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    livro TEXT,
    capitulo INTEGER,
    versiculo INTEGER,
    texto TEXT
);
""")

# Sincronização do Administrador e Carga Inicial de Contingência da Bíblia
def carga_inicial_sistema():
    admin_user = "admin@agape.com"
    if consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": admin_user}).empty:
        executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, 'Pastor')", {"u": admin_user, "s": generate_password_hash("agape2026", method="scrypt")})
    
    # Se a tabela da bíblia local estiver vazia, injeta os capítulos principais para garantir o funcionamento
    if consultar_db("SELECT id FROM texto_biblico LIMIT 1").empty:
        base_inicial = [
            ("João", 3, 16, "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna."),
            ("João", 3, 17, "Porque Deus enviou o seu Filho ao mundo, não para condenar o mundo, mas para que o mundo fosse salvo por ele."),
            ("Salmos", 23, 1, "O Senhor é o meu pastor, nada me faltará."),
            ("Salmos", 23, 2, "Deitar-me faz em verdes pastos, guia-me mansamente a águas tranquilas."),
            ("Salmos", 23, 3, "Refrigera a minha alma; guia-me pelas veredas da justiça por amor do seu nome."),
            ("Salmos", 23, 4, "Ainda que eu andasse pelo vale da sombra da morte, não temeria mal algum, porque tu estás comigo."),
            ("Salmos", 23, 5, "Preparas uma mesa perante mim na presença dos meus inimigos, unges a minha cabeça com óleo, o meu cálice transborda."),
            ("Salmos", 23, 6, "Certamente que a bondade e a misericórdia me seguirão todos os dias da minha vida; e habitarei na casa do Senhor por longos dias."),
            ("Salmos", 91, 1, "Aquele que habita no esconderijo do Altíssimo, à sombra do Onipotente descansará."),
            ("Salmos", 91, 2, "Direi do Senhor: Ele é o meu Deus, o meu refúgio, a minha fortaleza, e nele confiarei."),
            ("Filipenses", 4, 13, "Tudo posso naquele que me fortalece.")
        ]
        for livro, cap, ver, txt in base_inicial:
            executar_query("INSERT INTO texto_biblico (livro, capitulo, versiculo, texto) VALUES (:l, :c, :v, :t)", {"l": livro, "c": cap, "v": ver, "t": txt})

carga_inicial_sistema()

LIVROS_BIBLIA = {
    "Gênesis": "gn", "Êxodo": "ex", "Levítico": "lv", "Números": "nu", "Deuteronômio": "dt",
    "Salmos": "sl", "Provérbios": "pv", "Isaías": "is", "Jeremias": "jr", "Mateus": "mt",
    "Marcos": "mc", "Lucas": "lc", "João": "jo", "Atos": "act", "Romanos": "rm", "Apocalipse": "re"
}

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
        df_v_dia = consultar_db("SELECT texto, livro, capitulo, versiculo FROM texto_biblico WHERE livro = 'João' AND capitulo = 3 AND versiculo = 16")
        if not df_v_dia.empty:
            st.markdown(f'<div class="versiculo-box"><h4>"{df_v_dia.loc[0, "texto"]}"</h4><span style="color:#fff;">— {df_v_dia.loc[0, "livro"]} {df_v_dia.loc[0, "capitulo"]}:{df_v_dia.loc[0, "versiculo"]}</span></div>', unsafe_allow_html=True)
        st.metric("Total de Membros", f"{len(consultar_db('SELECT id FROM membros'))} Irmãos")

    elif escolha == "Bíblia Completa":
        st.subheader("📖 Leitura da Bíblia Sagrada (Modo Híbrido Completo)")
        c1, c2 = st.columns(2)
        l_nome = c1.selectbox("Selecione o Livro:", list(LIVROS_BIBLIA.keys()))
        c_num = c2.number_input("Selecione o Capítulo:", min_value=1, max_value=150, value=1, step=1)
        
        if st.button("📖 Carregar Capítulo Inteiro", use_container_width=True):
            # 1. Verifica se já temos esse capítulo gravado localmente no SQLite
            df_local = consultar_db("SELECT versiculo, texto FROM texto_biblico WHERE livro = :l AND capitulo = :c ORDER BY versiculo ASC", {"l": l_nome, "c": c_num})
            
            if not df_local.empty:
                html = "<div class='leitura-box'><h4>📜 Origem: Banco de Dados Local (Completo)</h4><br>"
                for i, r in df_local.iterrows():
                    html += f"<p><b style='color:#FFA500;'>{r['versiculo']}.</b> {r['texto']}</p>"
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)
            else:
                # 2. Se não estiver no banco local, faz a requisição na API e grava todos os versículos para sempre
                try:
                    url_api = f"https://abibliadigital.com.br{LIVROS_BIBLIA[l_nome]}/{c_num}"
                    res = requests.get(url_api, timeout=5)
                    if res.status_code == 200:
                        dados = res.json()
                        html = "<div class='leitura-box'><h4>📥 Baixado e Sincronizado com Sucesso!</h4><br>"
                        for v in dados["verses"]:
                            # Salva no banco local SQLite da aplicação para nunca mais depender da API neste capítulo
                            executar_query("INSERT INTO texto_biblico (livro, capitulo, versiculo, texto) VALUES (:l, :c, :v, :t)", {"l": l_nome, "c": c_num, "v": v["number"], "t": v["text"]})
                            html += f"<p><b style='color:#FFA500;'>{v['number']}.</b> {v['text']}</p>"
                        html += "</div>"
                        st.markdown(html, unsafe_allow_html=True)
                    else: st.warning("Capítulo não encontrado na base de dados.")
                except:
