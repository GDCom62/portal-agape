import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json, base64, os

# --- 1. CONFIGURAÇÃO E ESTILO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# CSS para centralização, cartões flutuantes e design moderno
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
    h1, h2, h3 { color: #1e3a8a !important; font-family: 'Segoe UI', sans-serif; text-align: center; }
    
    /* Cartões do Mural e da Bíblia */
    .versiculo-card {
        background-color: white;
        padding: 18px 25px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border: 1px solid #f1f5f9;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .versiculo-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    .numero-v {
        color: #1e3a8a;
        font-weight: bold;
        font-size: 1.1em;
        margin-right: 12px;
    }
    .mural-card {
        background: linear-gradient(135deg, #ffffff 0%, #f9fafb 100%);
        padding: 20px;
        border-radius: 18px;
        border-left: 6px solid #1e3a8a;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_final_v21.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER, ativo INTEGER DEFAULT 1)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, explicacao TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS palavra_dia (id INTEGER PRIMARY KEY, versiculo TEXT, mensagem TEXT, data TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1, 1)", {"pw": pw})

init_db()

# --- 3. LOGIN CENTRALIZADO ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    _, col_central, _ = st.columns([1, 1.8, 1])
    with col_central:
        if os.path.exists(URL_LOGO):
            # Hack para centralizar a imagem do Streamlit
            st.markdown("<div style='text-align: center'>", unsafe_allow_html=True)
            st.image(URL_LOGO, width=200)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.title("⛪ Portal Ágape")
            
        tab_l, tab_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with tab_l:
            with st.form("login"):
                e = st.text_input("E-mail")
                s = st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar Portal", use_container_width=True):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty:
                        u_data = res.iloc[0].to_dict()
                        if check_password_hash(u_data['senha'], s):
                            st.session_state.update({"logado": True, "user": u_data})
                            st.rerun()
                    st.error("Credenciais incorretas.")
        with tab_c:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Cadastrar", use_container_width=True):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin, ativo) VALUES (:n, :e, :c, :p, 0, 1)", {"n": n, "e": em, "c": c, "p": generate_password_hash(se)})
                    st.success(f"Cadastro realizado! Seu código: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    if os.path.exists(URL_LOGO):
        st.sidebar.image(URL_LOGO, width=130)
    st.sidebar.markdown(f"### 🙏 Olá, **{u['nome']}**")
    
    menu = st.sidebar.radio("Navegação", ["📢 Mural", "📖 Bíblia", "📺 Ao Vivo", "💰 Financeiro"])
    admin_mode = st.sidebar.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
    if st.sidebar.button("🚪 Sair", use_container_width=True): 
        st.session_state.logado = False
        st.rerun()

    if admin_mode:
        st.title("⚙️ Administração")
        t1, t2, t3, t4, t5 = st.tabs(["📢 Avisos", "📖 Bíblia", "📺 Live", "💰 Financeiro", "📜 Palavra"])

        with t1:
            with st.form("f_aviso", clear_on_submit=True):
                tit, cont = st.text_input("Título"), st.text_area("Mensagem")
                if st.form_submit_button("Publicar Aviso"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t,:c,:d)", {"t":tit,"c":cont,"d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Postado!")

        with t2:
            st.subheader("Importar Bíblia (JSON)")
            arq = st.file_uploader("Subir arquivo acf.json", type=['json'])
            if arq and st.button("🚀 Iniciar Importação"):
                dados = json.load(arq)
                for livro in dados:
                    nm = livro.get('name')
                    for ic, cap in enumerate(livro.get('chapters', [])):
                        for iv, txt in enumerate(cap):
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)", {"l":nm, "c":ic+1, "v":iv+1, "t":txt})
                st.success("Bíblia Importada!")

        with t3:
            vid_id = st.text_input("ID do Vídeo YouTube (Ex: jNQXAC9IVRw)")
            if st.button("Salvar Transmissão"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_id', :v)", {"v": vid_id})
                st.success("Live atualizada!")

        with t4:
            with st.form("f_fin", clear_on_submit=True):
                d, v, t = st.text_input("Descrição"), st.number_input("Valor"), st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":d,"v":v,"t":t,"dt":datetime.now().strftime("%d/%m/%Y")})
                    st.rerun()

        with t5:
            with st.form("f_pal", clear_on_submit=True):
                ver, msg = st.text_input("Versículo"), st.text_area("Mensagem")
                if st.form_submit_button("Atualizar Palavra do Dia"):
                    executar_query("DELETE FROM palavra_dia")
                    executar_query("INSERT INTO palavra_dia (versiculo, mensagem, data) VALUES (:v,:m,:d)", {"v":ver,"m":msg,"d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Atualizada!")

    else:
        if menu == "📢 Mural":
            st.title("📢 Mural da Igreja")
            palavra = consultar_db("SELECT * FROM palavra_dia LIMIT 1")
            if not palavra.empty:
                st.markdown(f"""
                    <div style="background-color: #eef2ff; padding: 25px; border-radius: 20px; border-left: 8px solid #1e3a8a; margin-bottom: 30px;">
                        <h3 style="text-align: left; color: #1e3a8a; margin-top: 0;">📖 Palavra do Dia</h3>
                        <p style="font-size: 1.2em; font-style: italic; color: #334155;">"{palavra.iloc[0]['versiculo']}"</p>
                        <p style="color: #475569;">{palavra.iloc[0]['mensagem']}</p>
                    </div>
                """, unsafe_allow_html=True)
            
            avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, a in avisos.iterrows():
                st.markdown(f'<div class="mural-card"><b>📌 {a["titulo"]}</b><br><small>{a["data"]}</small><br><br>{a["conteudo"]}</div>', unsafe_allow_html=True)

        elif menu == "📺 Ao Vivo":
            st.title("📺 Transmissão Online")
            res = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_id'")
            if not res.empty:
                v_id = res.iloc[0]['valor']
                st.markdown(f'<div style="border-radius:20px; overflow:hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.15);"><iframe width="100%" height="550" src="https://youtube.com{v_id}" frameborder="0" allowfullscreen></iframe></div>', unsafe_allow_html=True)
            else: st.warning("Nenhuma live configurada no momento.")

        elif menu == "💰 Financeiro":
            st.title("💰 Transparência")
            df = consultar_db("SELECT descricao as Descrição, valor as Valor, tipo as Tipo, data as Data FROM financeiro")
            st.dataframe(df, use_container_width=True)

        elif menu == "📖 Bíblia":
            st.title("📖 Bíblia Sagrada")
            livros = consultar_db("SELECT DISTINCT livro FROM biblia")
            if not livros.empty:
                col_l, col_c = st.columns(2)
                with col_l:
                    l_sel = st.selectbox("Livro", livros['livro'])
                with col_c:
                    caps = consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l_sel})
                    c_sel = st.selectbox("Capítulo", caps['capitulo'])
                
                st.divider()
                vers = consultar_db("SELECT versiculo, texto FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l_sel, "c":c_sel})
                
                for _, v in vers.iterrows():
                    st.markdown(f"""
                        <div class="versiculo-card">
                            <span class="numero-v">{v['versiculo']}</span>
                            <span style="color: #334155; line-height: 1.6;">{v['texto']}</span>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("A Bíblia precisa ser importada pelo Administrador.")
