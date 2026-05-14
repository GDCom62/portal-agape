import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import redis
import requests
import datetime

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. CONFIGURAÇÕES DE AMBIENTE ---
URL_CHAT_RAILWAY = "railway.app" 
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

# --- 3. CONEXÕES COM BANCO DE DADOS CORRIGIDA (Caminho Persistente Local) ---
@st.cache_resource
def inicializar_conexoes():
    # Removido /tmp/ para evitar apagamentos automáticos do sistema operacional
    engine = create_engine(
        "sqlite:///agape_v60.db", 
        connect_args={"check_same_thread": False, "timeout": 30}
    )
    try:
        r_db = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        r_db = None
    return engine, r_db

engine, r_db = inicializar_conexoes()

# Definição das funções de manipulação do banco
def executar_query(sql, params=None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except Exception:
            return pd.DataFrame()

# Criação das tabelas relacionais do sistema
executar_query("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    senha TEXT
);
""")

try:
    executar_query("ALTER TABLE usuarios ADD COLUMN nivel TEXT DEFAULT 'Membro';")
except Exception:
    pass 

executar_query("""
CREATE TABLE IF NOT EXISTS membros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    telefone TEXT,
    cargo TEXT,
    data_cadastro TEXT,
    mes_aniversario TEXT
);
""")

executar_query("""
CREATE TABLE IF NOT EXISTS financeiro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo TEXT,
    descricao TEXT,
    valor REAL,
    data TEXT,
    mes_ano TEXT,
    membro_id INTEGER
);
""")

executar_query("""
CREATE TABLE IF NOT EXISTS avisos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT,
    conteudo TEXT,
    data TEXT
);
""")

executar_query("""
CREATE TABLE IF NOT EXISTS louvores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT,
    artista TEXT,
    letra TEXT
);
""")

try:
    executar_query("ALTER TABLE louvores ADD COLUMN arquivo_audio BLOB;")
except Exception:
    pass

# Sincronização do Administrador Nativo
def verificar_e_criar_admin():
    admin_usuario = "admin@agape.com"
    admin_senha_pura = "agape2026"
    hash_admin = generate_password_hash(admin_senha_pura, method="scrypt")
    
    existe = consultar_db("SELECT id FROM usuarios WHERE usuario = :user", {"user": admin_usuario})
    
    if existe.empty:
        executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:user, :senha, 'Pastor')", 
                       {"user": admin_usuario, "senha": hash_admin})
    else:
        executar_query("UPDATE usuarios SET senha = :senha, nivel = 'Pastor' WHERE usuario = :user", 
                       {"user": admin_usuario, "senha": hash_admin})

verificar_e_criar_admin()

# --- 4. ESTILIZAÇÃO CUSTOMIZADA ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%) !important;
    }
    .stMetric, div[data-testid="stMetricValue"], div[data-testid="metric-container"], .card-flutuante, .cartao-membro {
        background-color: #ffffff !important;
        padding: 20px;
        border-radius: 16px !important;
        box-shadow: 0 6px 16px rgba(0,0,0,0.1) !important;
        border: 1px solid #e0a800 !important;
        color: #212529 !important;
    }
    .versiculo-box {
        background: linear-gradient(135deg, #212529 0%, #000000 100%);
        color: #FFD700;
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.2);
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. FUNÇÃO DE CARGA DA BÍBLIA CORRIGIDA ---
def carregar_biblia_completa():
    try:
        url = "githubusercontent.com"
        resposta = requests.get(url, timeout=20)
        
        if resposta.status_code == 200:
            dados_totais = resposta.json()
            linhas_db = []
            
            for livro_dados in dados_totais:
                nome_livro = livro_dados.get("name", "Desconhecido")
                for c_idx, capitulo in enumerate(livro_dados.get("chapters", []), start=1):
                    for v_idx, versiculo in enumerate(capitulo, start=1):
                        linhas_db.append({
                            "livro": nome_livro,
                            "capitulo": int(c_idx),
                            "versiculo": int(v_idx),
                            "texto": str(versiculo)
                        })
            
            if linhas_db:
                df_biblia = pd.DataFrame(linhas_db)
                df_biblia.to_sql("biblia", engine, if_exists="replace", index=False)
                return True
        return False
    except Exception as e:
        st.error(f"Erro técnico na carga da Bíblia: {e}")
        return False

# --- 6. GESTÃO DE ACESSO (AUTENTICAÇÃO) ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario_atual = None
    st.session_state.nivel_atual = "Membro"

st.sidebar.title("🔐 Portal Ágape")

if not st.session_state.autenticado:
    with st.sidebar.form(key="form_login"):
        campo_usuario = st.text_input("E-mail/Usuário", value="admin@agape.com")
        campo_senha = st.text_input("Senha", type="password", value="agape2026")
        botao_entrar = st.form_submit_button("Entrar")
        if botao_entrar:
            df_u = consultar_db("SELECT senha, nivel FROM usuarios WHERE usuario = :user", {"user": campo_usuario})
            if not df_u.empty and check_password_hash(str(df_u.iloc[0]['senha']), campo_senha):
                st.session_state.autenticado = True
                st.session_state.usuario_atual = campo_usuario
                st.session_state.nivel_atual = df_u.iloc[0]['nivel']
                st.rerun()
            else:
                st.sidebar.error("Usuário ou senha incorretos.")
    st.stop()
else:
    st.sidebar.write(f"Usuário: **{st.session_state.usuario_atual}**")
    st.sidebar.info(f"Acesso: {st.session_state.nivel_atual}")
    if st.sidebar.button("🚪 Sair do Sistema"):
        st.session_state.autenticado = False
        st.session_state.usuario_atual = None
        st.session_state.nivel_atual = "Membro"
        st.rerun()

# --- 7. MONTAGEM DO PAINEL DE CONTEÚDO ---
st.title("⛪ Portal Administrativo Ágape")

if st.session_state.nivel_atual == "Pastor":
    abas = st.tabs(["📢 Mural & Vídeo", "📖 Bíblia Sagrada", "👥 Gestão de Membros", "💰 Financeiro", "🎵 Louvores", "🔐 Credenciais"])
else:
    abas = st.tabs(["📢 Mural & Vídeo", "📖 Bíblia Sagrada", "🎵 Louvores"])

# ABA 1: CONTEÚDO INICIAL
with abas[0]:
    col_topo1, col_topo2 = st.columns(2)
    with col_topo1:
        st.markdown("""
        <div class='versiculo-box'>
            <h3 style='margin:0; color:#FFD700;'>📖 Palavra do Dia</h3>
            <p style='font-size: 16px; font-style: italic; margin-top:10px;'>\"O Senhor é o meu pastor, nada me faltará. Deita-me em verdes pastos, guia-me mansamente a águas tranquilas.\"</p>
            <p style='text-align: right; font-weight: bold; margin:0;'>Salmos 23:1-2</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_topo2:
        meses_pt = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        mes_atual = meses_pt[datetime.date.today().month - 1]
        
        st.markdown(f"""
        <div style='background: white; padding: 20px; border-radius: 20px; border: 1px solid #e0a800; min-height: 145px;'>
            <h3 style='margin:0; color:#212529;'>🎂 Aniversariantes de {mes_atual}</h3>
        """, unsafe_allow_html=True)
        
        df_aniv = consultar_db("SELECT nome, cargo FROM membros WHERE mes_aniversario = :mes", {"mes": mes_atual})
        if not df_aniv.empty:
            nomes_aniv = ", ".join([f"<b>{row['nome']}</b> ({row['cargo']})" for _, row in df_aniv.iterrows()])
            st.markdown(f"<p style='color:#333; margin-top:10px; font-size:16px;'>🎉 Parabéns a: {nomes_aniv}!</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color:gray; margin-top:10px;'>Nenhum membro faz aniversário este mês.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    col_aviso, col_video = st.columns(2)
    
    with col_aviso:
        st.header("📋 Mural de Avisos")
        if st.session_state.nivel_atual == "Pastor":
            with st.expander("➕ Novo Aviso (Exclusivo Pastor)"):
                t_aviso = st.text_input("Título do Aviso")
                c_aviso = st.text_area("Conteúdo")
                if st.button("Publicar Aviso"):
                    if t_aviso and c_aviso:
                        executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)",
                                       {"t": t_aviso, "c": c_aviso, "d": datetime.date.today().strftime('%d/%m/%Y')})
                        st.success("Publicado!")
                        st.rerun()
        
        lista_avisos = consultar_db("SELECT titulo, conteudo, data FROM avisos ORDER BY id DESC LIMIT 5")
        if not lista_avisos.empty:
            for _, av in lista_avisos.iterrows():
                st.markdown(f"""
                <div style='background-color: white; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #FFA500;'>
                    <h4 style='margin:0;'>{av['titulo']}</h4>
                    <p style='color: gray; font-size: 12px;'>Postado em: {av['data']}</p>
                    <p style='margin:0; color:#333;'>{av['conteudo']}</p>
                </div>
                """, unsafe_allow_html=True)

    with col_video:
        st.header("🎥 Conferência Ao Vivo")
        st.html(f'<iframe src="{URL_CHAT_RAILWAY}" width="100%" height="450" style="border:none; border-radius: 15px; background: white;" scrolling="yes" allow="camera; microphone"></iframe>')

# ABA 2: BÍBLIA SAGRADA
with abas[1]:
    st.header("📖 Leitura e Pesquisa Bíblica")
    tabela_existe = consultar_db("SELECT name FROM sqlite_master WHERE type='table' AND name='biblia'")
    
    if tabela_existe.empty:
        st.info("A base de dados local da Bíblia precisa ser sincronizada.")
        if st.button("🚀 Sincronizar Bíblia Sagrada Agora", use_container_width=True):
            with st.spinner("Sincronizando base de dados..."):
                if carregar_biblia_completa():
                    st.success("Sincronização concluída com sucesso!")
                    st.rerun()
    else:
        busca = st.text_input("🔍 Digite uma palavra ou trecho para buscar na Bíblia:")
        if busca:
            res_b = consultar_db("SELECT livro, capitulo, versiculo, texto FROM biblia WHERE texto LIKE :b LIMIT 50", {"b": f"%{busca}%"})
            if not res_b.empty:
                st.dataframe(res_b, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum resultado encontrado.")

# ABA 3: LOUVORES
idx_louvores = 4 if st.session_state.nivel_atual == "Pastor" else 2
with abas[idx_louvores]:
    st.header("🎵 Hinário & Letras de Louvores")
    if st.session_state.nivel_atual == "Pastor":
        with st.expander("➕ Adicionar Novo Louvor"):
            t_louvor = st.text_input("Título do Hino")
            a_louvor = st.text_input("Ministério / Artista")
            l_louvor = st.text_area("Letra Completa")
            upload_audio = st.file_uploader("Arquivo de Áudio (Opcional - MP3)", type=["mp3"])
            
            if st.button("Cadastrar Louvor"):
                audio_bytes = upload_audio.read() if upload_audio else None
                with engine.begin() as conn:
                    conn.execute(text("INSERT INTO louvores (titulo, artista, letra, arquivo_audio) VALUES (:t, :a, :l, :audio)"),
                                 {"t": t_louvor, "a": a_louvor, "l": l_louvor, "audio": audio_bytes})
                st.success("Louvor cadastrado!")
                st.rerun()
                
    lista_louvores = consultar_db("SELECT id, titulo, artista FROM louvores ORDER BY titulo ASC")
    if not lista_louvores.empty:
        selecionado = st.selectbox("Escolha um Louvor para exibir", lista_louvores['titulo'] + " - " + lista_louvores['artista'])
        if selecionado:
            t_sel = selecionado.split(" - ")[0] # Filtra puramente o título textual antes do separador
            dados_l = consultar_db("SELECT letra, arquivo_audio FROM louvores WHERE titulo = :t LIMIT 1", {"t": t_sel})
            
            if not dados_l.empty:
                st.subheader(selecionado)
                registro_audio = dados_l.iloc[0]['arquivo_audio']
                if registro_audio is not None:
                    st.audio(bytes(registro_audio), format="audio/mp3")
                st.text(dados_l.iloc[0]['letra'])

# ABAS GESTÃO EXCLUSIVA DO PASTOR
if st.session_state.nivel_atual == "Pastor":
    with abas[2]:
        st.header("👥 Cadastro de Membros")
        with st.form("form_membro", clear_on_submit=True):
            n_m = st.text_input("Nome Completo")
            t_m = st.text_input("Telefone / WhatsApp")
            c_m = st.selectbox("Cargo Eclesiástico", ["Membro", "Diácono", "Presbítero", "Evangelista", "Pastor", "Missionária"])
            m_a = st.selectbox("Mês de Aniversário", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
            if st.form_submit_button("Salvar Membro"):
                if n_m:
                    executar_query("INSERT INTO membros (nome, telefone, cargo, data_cadastro, mes_aniversario) VALUES (:n, :t, :c, :d, :m)",
                                   {"n": n_m, "t": t_m, "c": c_m, "d": datetime.date.today().strftime('%d/%m/%Y'), "m": m_a})
                    st.success("Membro adicionado!")
                    st.rerun()
        
        membros_df = consultar_db("SELECT id, nome AS Nome, telefone AS Telefone, cargo AS Cargo, mes_aniversario AS Aniversário FROM membros")
        st.dataframe(membros_df, use_container_width=True, hide_index=True)

    with abas[3]:
        st.header("💰 Fluxo de Caixa Financeiro")
        c1, c2 = st.columns(2)
        with c1:
            tipo_f = st.radio("Tipo de Lançamento", ["Entrada (Dízimo/Oferta)", "Saída (Despesa)"])
            desc_f = st.text_input("Descrição da Transação")
            val_f = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
        with c2:
            membros_lista = consultar_db("SELECT id, nome FROM membros")
            id_membro_v = None
            if tipo_f.startswith("Entrada") and not membros_lista.empty:
                escolha_m = st.selectbox("Vincular a um Membro (Opcional)", ["Nenhum"] + list(membros_lista['nome']))
                if escolha_m != "Nenhum":
                    id_membro_v = int(membros_lista[membros_lista['nome'] == escolha_m]['id'].values[0])
            
            if st.button("Confirmar Lançamento", use_container_width=True):
                mes_ano_v = datetime.date.today().strftime('%m/%Y')
                executar_query("INSERT INTO financeiro (tipo, descricao, valor, data, mes_ano, membro_id) VALUES (:t, :desc, :v, :data, :ma, :mid)",
                               {"t": "Entrada" if "Entrada" in tipo_f else "Saída", "desc": desc_f, "v": val_f, "data": datetime.date.today().strftime('%d/%m/%Y'), "ma": mes_ano_v, "mid": id_membro_v})
                st.success("Lançamento Realizado!")
                st.rerun()
        
        df_ent = consultar_db("SELECT SUM(valor) as total FROM financeiro WHERE tipo = 'Entrada'")
        df_sai = consultar_db("SELECT SUM(valor) as total FROM financeiro WHERE tipo = 'Saída'")
        ent = float(df_ent.iloc[0]['total']) if not df_ent.empty and df_ent.iloc[0]['total'] is not None else 0.0
        sai = float(df_sai.iloc[0]['total']) if not df_sai.empty and df_sai.iloc[0]['total'] is not None else 0.0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Entradas", f"R$ {ent:,.2f}")
        m2.metric("Total Saídas", f"R$ {sai:,.2f}")
        m3.metric("Saldo em Caixa", f"R$ {(ent - sai):,.2f}")

    with abas[5]:
        st.header("🔐 Controle de Usuários do Portal")
        with st.form("novo_usuario_painel"):
            u_nome = st.text_input("E-mail de Acesso").strip()
            u_senha = st.text_input("Senha", type="password")
            u_nivel = st.selectbox("Nível de Acesso", ["Membro", "Pastor"])
            if st.form_submit_button("Gerar Conta"):
                if u_nome and u_senha:
                    check_e = consultar_db("SELECT id FROM usuarios WHERE usuario = :u", {"u": u_nome})
                    if check_e.empty:
                        executar_query("INSERT INTO usuarios (usuario, senha, nivel) VALUES (:u, :s, :n)",
                                       {"u": u_nome, "s": generate_password_hash(u_senha, method="scrypt"), "n": u_nivel})
                        st.success("Conta criada!")
                    else:
                        st.error("Usuário já existe.")
