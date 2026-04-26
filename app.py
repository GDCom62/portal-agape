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
    .live-container { position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 15px; box-shadow: 0 10px 15px rgba(0,0,0,0.2); }
    .live-container iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0; }
    .aviso-img { width: 100%; max-height: 400px; object-fit: contain; border-radius: 10px; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS (Versão Final V14) ---
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

# --- 4. ACESSO ---
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
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()}); st.rerun()
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
                    st.success("Postado!")

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
                st.write("Adicionar Explicação Teológica")
                l, c, v = st.text_input("Livro"), st.number_input("Capítulo", 1), st.number_input("Versículo", 1)
                exp = st.text_area("Explicação do Versículo")
                if st.form_submit_button("Salvar Explicação"):
                    executar_query("UPDATE biblia SET explicacao=:e WHERE livro=:l AND capitulo=:c AND versiculo=:v", {"e":exp,"l":l,"c":c,"v":v})
                    st.success("Explicação salva!")

        with t3:
            st.subheader("Configurar Live")
            lu = st.text_input("Link YouTube", placeholder="https://youtube.com...")
            la = st.selectbox("Live Ativa?", ["Não", "Sim"])
            if st.button("Gravar Configurações"):
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_url', :v)", {"v":lu})
                executar_query("INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES ('live_ativa', :v)", {"v":la})
            st.divider()
            st.subheader("👥 Lista de Membros para Chamada")
            mems = consultar_db("SELECT nome, codigo, email FROM membros WHERE is_admin=0")
            st.dataframe(mems, use_container_width=True)

        with t4:
            with st.form("f_louv"):
                nl, ul = st.text_input("Nome do Louvor"), st.text_input("Link MP3 (URL)")
                if st.form_submit_button("Adicionar à Playlist"):
                    executar_query("INSERT INTO playlist (nome, url) VALUES (:n, :u)", {"n":nl,"u":ul})
        
        with t5:
            st.subheader("🙏 Pedidos de Oração")
            st.write(consultar_db("SELECT * FROM oracoes WHERE status='Pendente'"))
            st.divider()
            st.subheader("🛡️ Consultas Espirituais")
            cons = consultar_db("SELECT * FROM consultas WHERE resposta IS NULL")
            for _, cn in cons.iterrows():
                st.write(f"**De: {cn['nome_membro']}** - {cn['problema']}")
                resp = st.text_area("Sua Orientação Pastoral", key=f"res_{cn['id']}")
                if st.button("Enviar Resposta", key=f"btn_{cn['id']}"):
                    executar_query("UPDATE consultas SET resposta=:r WHERE id=:id", {"r":resp, "id":cn['id']}); st.rerun()

    # --- PÁGINAS DO PORTAL (MEMBRO) ---
    elif menu == "📢 Mural":
        df_a = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, r in df_a.iterrows():
            img = f'<img src="{r["img_url"]}" class="aviso-img">' if r['img_url'] else ""
            st.markdown(f'<div class="mural-card">{img}<h3>{r["titulo"]}</h3><p>{r["conteudo"]}</p></div>', unsafe_allow_html=True)

    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia com Explicação")
        livros = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not livros.empty:
            l = st.selectbox("Livro", livros['livro'].tolist())
            cap = st.selectbox("Capítulo", consultar_db("SELECT DISTINCT capitulo FROM biblia WHERE livro=:l", {"l":l})['capitulo'].tolist())
            versos = consultar_db("SELECT * FROM biblia WHERE livro=:l AND capitulo=:c", {"l":l, "c":cap})
            for _, v in versos.iterrows():
                st.markdown(f"<div class='bible-card'><b>{v['versiculo']}</b> {v['texto']}</div>", unsafe_allow_html=True)
                if v['explicacao']:
                    st.markdown(f"<div class='explicacao'>💡 <b>Explicação:</b> {v['explicacao']}</div>", unsafe_allow_html=True)
        else: st.warning("Bíblia vazia.")

    elif menu == "📺 Ao Vivo":
        l_url = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_url'")
        l_stat = consultar_db("SELECT valor FROM configuracoes WHERE chave='live_ativa'")
        if not l_stat.empty and l_stat.iloc[0]['valor'] == 'Sim':
            embed = l_url.iloc[0]['valor'].replace("watch?v=", "embed/")
            st.markdown(f'<div class="live-container"><iframe src="{embed}" allowfullscreen></iframe></div>', unsafe_allow_html=True)
        else: st.info("Sem transmissões.")

    elif menu == "🎶 Louvores":
        st.title("🎶 Playlist de Louvores")
        for _, m in consultar_db("SELECT * FROM playlist").iterrows():
            with st.container(border=True):
                st.write(f"🎵 **{m['nome']}**")
                st.audio(m['url'])

    elif menu == "🙏 Sala de Oração":
        st.title("🙏 Sala de Oração")
        with st.form("ora_f", clear_on_submit=True):
            ped = st.text_area("Qual seu pedido de oração?")
            if st.form_submit_button("Enviar ao Conselho de Oração"):
                executar_query("INSERT INTO oracoes (nome_membro, pedido, data) VALUES (:n, :p, :d)", {"n":u['nome'], "p":ped, "d":datetime.now().strftime("%d/%m/%Y")})
                st.success("Pedido enviado!")

    elif menu == "🛡️ Ajuda Espiritual":
        st.title("🛡️ Consulta Pastoral Online")
        st.write("Espaço privado para orientação sobre problemas espirituais.")
        with st.form("cons_f", clear_on_submit=True):
            prob = st.text_area("Descreva seu problema ou dúvida espiritual:")
            if st.form_submit_button("Solicitar Orientação"):
                executar_query("INSERT INTO consultas (nome_membro, problema, data) VALUES (:n, :p, :d)", {"n":u['nome'], "p":prob, "d":datetime.now().strftime("%d/%m/%Y")})
                st.success("Sua consulta foi enviada. O pastor responderá em breve.")
        
        st.subheader("Minhas Respostas")
        minhas = consultar_db("SELECT * FROM consultas WHERE nome_membro=:n AND resposta IS NOT NULL", {"n":u['nome']})
        for _, mc in minhas.iterrows():
            with st.container(border=True):
                st.write(f"**Pergunta:** {mc['problema']}")
                st.markdown(f"✅ **Resposta Pastoral:** {mc['resposta']}")
