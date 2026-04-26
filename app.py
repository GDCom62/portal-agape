import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json, base64, io

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
    .aviso-img { width: 100%; max-height: 400px; object-fit: contain; border-radius: 10px; margin-bottom: 15px; }
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
    executar_query('CREATE TABLE IF NOT EXISTS consultas (id INTEGER PRIMARY KEY, nome_membro TEXT, problema TEXT, resposta TEXT, data TEXT)')
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
        try: st.image("logo.png", use_container_width=True)
        except: st.title("⛪ Portal Ágape")
        tab_l, tab_c, tab_r = st.tabs(["🔐 Entrar", "📝 Cadastro", "🔑 Senha"])
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
                    st.success(f"Sucesso! Código: {c}")
        with tab_r:
            with st.form("rec"):
                re_e, re_c, re_s = st.text_input("E-mail"), st.text_input("Código AG-XXXX"), st.text_input("Nova Senha", type="password")
                if st.form_submit_button("Redefinir"):
                    check = consultar_db("SELECT id FROM membros WHERE email=:e AND codigo=:c", {"e":re_e, "c":re_c})
                    if not check.empty:
                        executar_query("UPDATE membros SET senha=:s WHERE email=:e", {"s": generate_password_hash(re_s), "e": re_e})
                        st.success("Senha atualizada!")

# --- 5. ÁREA LOGADA ---
else:
    u = st.session_state.user
    st.sidebar.markdown(f"### 🙏 Olá, **{u['nome']}**")
    menu = st.sidebar.radio("Navegação", ["📢 Mural", "📖 Bíblia", "📺 Ao Vivo", "🎶 Louvores", "🙏 Sala de Oração", "🛡️ Ajuda Espiritual"])
    
    if u['is_admin'] == 1:
        st.sidebar.divider()
        if st.sidebar.button("⚙️ Painel Admin"): st.session_state.admin_mode = True
        if st.sidebar.button("🏠 Voltar ao Portal"): st.session_state.admin_mode = False
    
    if st.sidebar.button("🚪 Sair"): st.session_state.logado = False; st.rerun()

    # --- PÁGINAS ADMINISTRATIVAS ---
    if u['is_admin'] == 1 and st.session_state.get('admin_mode'):
        st.title("⚙️ Painel do Administrador")
        t1, t2, t3, t4, t5 = st.tabs(["📢 Mural", "📖 Bíblia/Explicação", "📺 Live/Membros", "🎶 Playlist", "🙏 Atendimento"])
        
        with t1:
            with st.form("f_aviso"):
                tit, cont = st.text_input("Título"), st.text_area("Conteúdo")
                arq = st.file_uploader("Foto do Aviso", type=['jpg','png'])
                if st.form_submit_button("Publicar Aviso"):
                    img = f"data:image/png;base64,{base64.b64encode(arq.getvalue()).decode()}" if arq else ""
                    executar_query("INSERT INTO avisos (titulo, conteudo, data, img_url) VALUES (:t,:c,:d,:i)", {"t":tit,"c":cont,"d":datetime.now().strftime("%d/%m/%Y"),"i":img})
                    st.success("Postado!"); st.rerun()

        with t2:
            st.subheader("Bíblia e Explicações")
            f_bib = st.file_uploader("Subir acf.json", type=['json'])
            if f_bib and st.button("Importar Bíblia"):
                dados = json.load(f_bib)
                for liv in dados:
                    nm = liv.get('name')
                    for ic, cl in enumerate(liv.get('chapters', [])):
                        for iv, tv in enumerate(cl):
                            executar_query("INSERT OR IGNORE INTO biblia (livro, capitulo, versiculo, texto) VALUES (:l,:c,:v,:t)", {"l": str(nm), "c": ic+1, "v": iv+1, "t": str(tv)})
                st.success("Bíblia Carregada!")
            st.divider()
            with st.form("f_exp"):
                l, c, v = st.text_input("Livro"), st.number_input("Capítulo", 1), st.number_input("Versículo", 1)
                exp = st.text_area("Explicação")
                if st.form_submit_button("Salvar Explicação"):
                    executar_query("UPDATE biblia SET explicacao=:e WHERE livro=:l AND capitulo=:c AND versiculo=:v", {"e":exp,"l":l,"c":c,"v":v})
                    st.success("Salva!")

        with t3:
            lu = st.text_input("Link YouTube", placeholder="Ex: https://youtube.com...")
            la = st.selectbox("Live Ativa?", ["Não", "Sim"])
            if st.button("Gravar Configurações"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_url', :v)", {"v":lu})
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_ativa', :v)", {"v":la})
            st.divider()
            st.subheader("👥 Membros")
            st.dataframe(consultar_db("SELECT nome, codigo, email FROM membros WHERE is_admin=0"), use_container_width=True)

        with t4:
            with st.form("f_playlist"):
                nl, ul = st.text_input("Nome do Louvor"), st.text_input("Link MP3 (Dropbox/Drive)")
                if st.form_submit_button("Adicionar"):
                    executar_query("INSERT INTO playlist (nome, url) VALUES (:n, :u)", {"n":nl,"u":ul})
                    st.success("Adicionado!")
            st.divider()
            st.subheader("Gerenciar Playlist")
            pl = consultar_db("SELECT * FROM playlist")
            for _, m in pl.iterrows():
                col_a, col_b = st.columns([4,1])
                col_a.write(m['nome'])
                if col_b.button("Remover", key=f"rm_{m['id']}"):
                    executar_query("DELETE FROM playlist WHERE id=:id", {"id":m['id']}); st.rerun()

        with t5:
            st.subheader("🙏 Oração & Atendimento")
            st.write(consultar_db("SELECT * FROM oracoes WHERE status='Pendente'"))
            st.divider()
            cons = consultar_db("SELECT * FROM consultas WHERE resposta IS NULL")
            for _, cn in cons.iterrows():
                st.write(f"**De: {cn['nome_membro']}** - {cn['problema']}")
                resp = st.text_area("Resposta", key=f"res_{cn['id']}")
                if st.button("Responder", key=f"btn_{cn['id']}"):
                    executar_query("UPDATE consultas SET resposta=:r WHERE id=:id", {"r":resp, "id":cn['id']}); st.rerun()

    # --- PÁGINAS DO PORTAL ---
    elif menu == "📢 Mural":
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in df_a.iterrows():
            img = f'<img src="{r["img_url"]}" class="aviso-img">' if r['img_url'] else ""
            st.markdown(f'<div class="mural-card">{img}<h3>{r["titulo"]}</h3><p>{r["conteudo"]}</p></div>', unsafe_allow_html=True)

    elif menu == "🎶 Louvores":
        st.title("🎶 Playlist Ágape")
        pl = consultar_db("SELECT * FROM playlist")
        if pl.empty: st.info("Playlist vazia.")
        for _, m in pl.iterrows():
            with st.container():
                st.markdown(f"**🎵 {m['nome']}**")
                # Player Seguro contra MediaFileStorageError
                try:
                    if "http" in m['url']:
                        st.audio(m['url'])
                    else:
                        st.warning("Link inválido.")
                except:
                    st.markdown(f'<audio controls style="width:100%"><source src="{m["url"]}" type="audio/mpeg"></audio>', unsafe_allow_html=True)

    elif menu == "📖 Bíblia":
        livs = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not livs.empty:
            l = st.selectbox("Livro", livs['livro'].tolist())
            cap = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l})['capitulo'].tolist())
            versos = consultar_db("SELECT * FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l, "c":cap})
            for _, v in versos.iterrows():
                st.markdown(f"<div class='bible-card'><b>{v['versiculo']}</b> {v['texto']}</div>", unsafe_allow_html=True)
                if v['explicacao']: st.markdown(f"<div class='explicacao'>💡 {v['explicacao']}</div>", unsafe_allow_html=True)
        else: st.info("Bíblia não carregada.")

    elif menu == "📺 Ao Vivo":
        st.title("📺 Transmissão ao Vivo")
        l_url = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_url'")
        l_stat = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_ativa'")
        if not l_stat.empty and l_stat.iloc[0]['valor'] == 'Sim':
            emb = l_url.iloc[0]['valor'].replace("watch?v=", "embed/")
            st.markdown(f'<div class="live-container"><iframe src="{emb}" allowfullscreen></iframe></div>', unsafe_allow_html=True)
        else: st.info("Sem transmissões agora.")

    elif menu == "🙏 Sala de Oração":
        with st.form("f_ora", clear_on_submit=True):
            p = st.text_area("Pedido de Oração")
            if st.form_submit_button("Enviar"):
                executar_query("INSERT INTO oracoes (nome_membro, pedido, data) VALUES (:n,:p,:d)", {"n":u['nome'],"p":p,"d":datetime.now().strftime("%d/%m/%Y")})
                st.success("Enviado!")

    elif menu == "🛡️ Ajuda Espiritual":
        with st.form("f_cons", clear_on_submit=True):
            p = st.text_area("Sua dúvida ou problema espiritual")
            if st.form_submit_button("Pedir Orientação"):
                executar_query("INSERT INTO consultas (nome_membro, problema, data) VALUES (:n,:p,:d)", {"n":u['nome'],"p":p,"d":datetime.now().strftime("%d/%m/%Y")})
                st.success("Enviado ao pastor!")
