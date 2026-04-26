import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json, base64

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
    h1, h2, h3 { color: #1e3a8a !important; font-family: 'Segoe UI', sans-serif; }
    .mural-card { background-color: white; padding: 25px; border-radius: 15px; border-top: 5px solid #1e3a8a; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .bible-card { background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #3b82f6; margin-bottom: 10px; }
    .explicacao { background: #eef2ff; padding: 15px; border-radius: 10px; border: 1px dashed #3b82f6; font-style: italic; margin-top: 10px; }
    .live-container { position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 15px; box-shadow: 0 10px 15px rgba(0,0,0,0.2); margin-bottom: 20px; }
    .live-container iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v14.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT, img_url TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS playlist (id INTEGER PRIMARY KEY, nome TEXT, url TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS oracoes (id INTEGER PRIMARY KEY, nome_membro TEXT, pedido TEXT, data TEXT, status TEXT DEFAULT "Pendente")')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN / SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.title("⛪ Portal Ágape")
        tab_l, tab_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with tab_l:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar"):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty:
                        u_data = res.iloc[0].to_dict()
                        if check_password_hash(u_data['senha'], s):
                            st.session_state.update({"logado": True, "user": u_data}); st.rerun()
                    st.error("Dados incorretos.")
        with tab_c:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)", {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Sucesso! Seu código é: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    st.sidebar.markdown(f"### 🙏 Olá, **{u['nome']}**")
    menu = st.sidebar.radio("Navegação", ["📢 Mural", "📖 Bíblia", "📺 Ao Vivo", "🎶 Playlist Ágape", "🙏 Sala de Oração"])
    
    if u['is_admin'] == 1:
        st.sidebar.divider()
        admin_mode = st.sidebar.checkbox("⚙️ Modo Administrador")
    else: admin_mode = False

    if st.sidebar.button("🚪 Sair"): 
        st.session_state.logado = False
        st.rerun()

    # --- PAINEL ADMIN ---
    if admin_mode:
        st.title("⚙️ Administração")
        t1, t2, t3, t4 = st.tabs(["📢 Mural", "📖 Bíblia", "📺 Live", "🎶 Playlist"])
        
        with t1:
            with st.form("f_aviso", clear_on_submit=True):
                tit, cont = st.text_input("Título"), st.text_area("Conteúdo")
                arq = st.file_uploader("Imagem", type=['jpg','png'])
                if st.form_submit_button("Postar"):
                    img = f"data:image/png;base64,{base64.b64encode(arq.getvalue()).decode()}" if arq else ""
                    executar_query("INSERT INTO avisos (titulo, conteudo, data, img_url) VALUES (:t,:c,:d,:i)", {"t":tit,"c":cont,"d":datetime.now().strftime("%d/%m/%Y"),"i":img})
                    st.success("Postado!")

        with t4:
            st.subheader("Gerenciar Louvores")
            with st.form("f_music", clear_on_submit=True):
                m_n, m_u = st.text_input("Nome do Louvor"), st.text_input("Link YouTube")
                if st.form_submit_button("Adicionar"):
                    executar_query("INSERT INTO playlist (nome, url) VALUES (:n, :u)", {"n": m_n, "u": m_u})
                    st.rerun()
            
            musicas = consultar_db("SELECT * FROM playlist")
            for _, m in musicas.iterrows():
                col_a, col_b = st.columns([4, 1])
                col_a.write(m['nome'])
                if col_b.button("Remover", key=f"rm_{m['id']}"):
                    executar_query("DELETE FROM playlist WHERE id=:id", {"id": m['id']})
                    st.rerun()

    # --- PÁGINAS DE MEMBRO ---
    else:
        if menu == "📢 Mural":
            st.title("📢 Mural Ágape")
            avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, a in avisos.iterrows():
                st.markdown(f'<div class="mural-card"><h3>{a["titulo"]}</h3><p>{a["conteudo"]}</p><small>{a["data"]}</small></div>', unsafe_allow_html=True)
                if a['img_url']: st.image(a['img_url'])

        elif menu == "🎶 Playlist Ágape":
            st.title("🎶 Playlist de Adoração")
            busca = st.text_input("🔍 Buscar louvor pelo nome...")
            query = "SELECT * FROM playlist WHERE nome LIKE :b ORDER BY id DESC"
            playlist = consultar_db(query, {"b": f"%{busca}%"})
            
            if not playlist.empty:
                escolha = st.selectbox("Selecione o louvor para tocar:", playlist['nome'])
                url = playlist[playlist['nome'] == escolha]['url'].values[0]
                st.video(url)
                
                st.divider()
                st.subheader("Lista Completa")
                for _, m in playlist.iterrows():
                    st.write(f"🎵 {m['nome']}")
            else:
                st.warning("Nenhum louvor encontrado.")

        elif menu == "📖 Bíblia":
            st.title("📖 Bíblia e Explicações")
            livros = consultar_db("SELECT DISTINCT livro FROM biblia")
            if not livros.empty:
                l = st.selectbox("Livro", livros['livro'])
                cap = st.number_input("Capítulo", 1)
                vers = consultar_db("SELECT * FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l, "c":cap})
                for _, v in vers.iterrows():
                    st.markdown(f"<div class='bible-card'>{v['versiculo']}. {v['texto']}</div>", unsafe_allow_html=True)
                    if v['explicacao']: st.markdown(f"<div class='explicacao'>{v['explicacao']}</div>", unsafe_allow_html=True)
            else:
                st.info("Bíblia ainda não importada.")

        elif menu == "📺 Ao Vivo":
            st.title("📺 Culto Online")
            st.info("Acompanhe nossa transmissão ao vivo abaixo.")
            st.markdown('<div class="live-container"><iframe src="https://youtube.com"></iframe></div>', unsafe_allow_html=True)
