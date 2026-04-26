import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json, base64, os

# --- 1. CONFIGURAÇÃO E ESTILO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
    h1, h2, h3 { color: #1e3a8a !important; font-family: 'Segoe UI', sans-serif; text-align: center; }
    
    /* Cartões Flutuantes da Bíblia */
    .versiculo-card {
        background-color: white;
        padding: 18px 25px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 12px;
        border: 1px solid #f1f5f9;
        transition: transform 0.2s ease;
    }
    .versiculo-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    .numero-v { color: #1e3a8a; font-weight: bold; margin-right: 12px; }

    /* Estilo da Rádio */
    .radio-box {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 30px;
        border-radius: 30px;
        text-align: center;
        color: white;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v23_final.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

# --- 3. LÓGICA PALAVRA DO DIA AUTOMÁTICA ---
def obter_palavra_dia():
    try:
        res = consultar_db("SELECT livro, capitulo, versiculo, texto FROM biblia ORDER BY RANDOM() LIMIT 1")
        if not res.empty:
            v = res.iloc[0]
            return f"📖 {v['livro']} {v['capitulo']}:{v['versiculo']}", v['texto']
    except: pass
    return "📖 Salmos 23:1", "O Senhor é o meu pastor, nada me faltará."

# --- 4. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    _, col_central, _ = st.columns([1, 1.8, 1])
    with col_central:
        if os.path.exists(URL_LOGO):
            st.markdown("<div style='text-align: center'>", unsafe_allow_html=True)
            st.image(URL_LOGO, width=180)
            st.markdown("</div>", unsafe_allow_html=True)
        else: st.title("⛪ Portal Ágape")
        
        t_login, t_cad = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_login:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar", use_container_width=True):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty:
                        u_data = res.iloc[0].to_dict()
                        if check_password_hash(u_data['senha'], s):
                            st.session_state.update({"logado": True, "user": u_data}); st.rerun()
                    st.error("Credenciais inválidas.")
        with t_cad:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar", use_container_width=True):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n, :e, :c, :p, 0)", {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Cadastrado! Código: {c}")

# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    if os.path.exists(URL_LOGO): st.sidebar.image(URL_LOGO, width=120)
    st.sidebar.markdown(f"### 🙏 Olá, **{u['nome']}**")
    
    menu = st.sidebar.radio("Navegação", ["📢 Mural", "📖 Bíblia", "📻 Rádio Ágape", "🎥 Reunião de Vídeo", "📺 Ao Vivo", "💰 Financeiro"])
    admin_mode = st.sidebar.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
    if st.sidebar.button("🚪 Sair", use_container_width=True): st.session_state.logado = False; st.rerun()

    if admin_mode:
        st.title("⚙️ Painel Administrador")
        tab1, tab2, tab3, tab4 = st.tabs(["📢 Avisos", "📖 Bíblia", "📺 Live/Rádio", "💰 Financeiro"])
        with tab1:
            with st.form("f_aviso", clear_on_submit=True):
                tit, cont = st.text_input("Título"), st.text_area("Conteúdo")
                if st.form_submit_button("Postar Aviso"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t,:c,:d)", {"t":tit,"c":cont,"d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Postado!")
        with tab2:
            arq = st.file_uploader("Subir acf.json", type=['json'])
            if arq and st.button("🚀 Importar Bíblia"):
                dados = json.load(arq)
                for livro in dados:
                    nm = livro.get('name')
                    for ic, cap in enumerate(livro.get('chapters', [])):
                        for iv, txt in enumerate(cap):
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)", {"l":nm, "c":ic+1, "v":iv+1, "t":txt})
                st.success("Bíblia Importada!")
        with tab3:
            v_id = st.text_input("ID do Vídeo YouTube (Live)")
            r_url = st.text_input("Link do Streaming da Rádio (URL .mp3 ou stream)")
            if st.button("Salvar Configurações"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_id', :v)", {"v": v_id})
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('radio_url', :r)", {"r": r_url})
                st.success("Dados salvos!")
        with tab4:
            with st.form("f_fin", clear_on_submit=True):
                d, v, t = st.text_input("Descrição"), st.number_input("Valor"), st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":d,"v":v,"t":t,"dt":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Registrado!")

    else:
        if menu == "📢 Mural":
            st.title("📢 Mural Ágape")
            ref, texto = obter_palavra_dia()
            st.markdown(f'<div style="background:#eef2ff; padding:25px; border-radius:20px; border-left:8px solid #1e3a8a;"><h4>{ref}</h4><p><i>"{texto}"</i></p></div>', unsafe_allow_html=True)
            for _, a in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
                st.markdown(f'<div class="versiculo-card"><b>📌 {a["titulo"]}</b><br><small>{a["data"]}</small><br>{a["conteudo"]}</div>', unsafe_allow_html=True)

        elif menu == "📻 Rádio Ágape":
            st.title("📻 Rádio Online")
            r_res = consultar_db("SELECT valor FROM configuracoes WHERE chave='radio_url'")
            url_radio = r_res.iloc[0]['valor'] if not r_res.empty else ""
            st.markdown(f'<div class="radio-box"><h3>No Ar: Rádio Ágape</h3><audio controls autoplay style="width:100%"><source src="{url_radio}" type="audio/mpeg"></audio></div>', unsafe_allow_html=True)

        elif menu == "🎥 Reunião de Vídeo":
            st.title("🎥 Sala de Vídeo e Bate-papo")
            st.markdown(f'<iframe src="https://jit.si_{string.ascii_uppercase[0]}" allow="camera; microphone; fullscreen; display-capture; autoplay" style="height:600px; width:100%; border-radius:20px; border:0;"></iframe>', unsafe_allow_html=True)

        elif menu == "📖 Bíblia":
            st.title("📖 Bíblia Sagrada")
            livros = consultar_db("SELECT DISTINCT livro FROM biblia")
            if not livros.empty:
                l_sel = st.selectbox("Livro", livros['livro'])
                c_sel = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l_sel})['capitulo'])
                for _, v in consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l_sel, "c":c_sel}).iterrows():
                    st.markdown(f'<div class="versiculo-card"><span class="numero-v">{v["versiculo"]}</span>{v["texto"]}</div>', unsafe_allow_html=True)
            else: st.info("Bíblia vazia. Admin deve importar o JSON.")

        elif menu == "📺 Ao Vivo":
            st.title("📺 Transmissão")
            res = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_id'")
            if not res.empty: st.markdown(f'<iframe width="100%" height="500" src="https://youtube.com{res.iloc[0]["valor"]}" frameborder="0" allowfullscreen style="border-radius:20px;"></iframe>', unsafe_allow_html=True)

        elif menu == "💰 Financeiro":
            st.title("💰 Transparência")
            st.dataframe(consultar_db("SELECT descricao, valor, tipo, data FROM financeiro"), width='stretch')
