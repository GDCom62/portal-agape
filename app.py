import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, io, re

# --- 1. CONFIGURAÇÕES E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, img_data TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, codigo_doador TEXT, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, anexo_nome TEXT, anexo_data TEXT, data TEXT)')
    
    # Garantir que a coluna img_data existe no Mural (evita erro de banco antigo)
    try: consultar_db("SELECT img_data FROM avisos LIMIT 1")
    except: executar_query("ALTER TABLE avisos ADD COLUMN img_data TEXT")

    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

def exibir_logo(largura=150):
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as f:
            data = base64.b64encode(f.read()).decode()
            st.markdown(f'<p align="center"><img src="data:image/png;base64,{data}" width="{largura}"></p>', unsafe_allow_html=True)
    else:
        st.markdown(f'<h1 style="text-align:center; color:#1e3a8a;">⛪ ÁGAPE</h1>', unsafe_allow_html=True)

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    _, col_c, _ = st.columns([1, 1.5, 1])
    with col_c:
        exibir_logo(180)
        t_l, t_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_l:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar Portal", use_container_width=True):
                    res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e": e})
                    if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                        st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                        st.rerun()
                    st.error("Credenciais incorretas.")
        with t_c:
            with st.form("cad"):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Conta"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n,:e,:c,:p,0)", {"n":n,"e":em,"c":c,"p":generate_password_hash(se)})
                    st.success(f"Conta criada! Código: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    with st.sidebar:
        exibir_logo(100)
        st.markdown(f"<p style='text-align:center;'>🙏 <b>{u['nome']}</b></p>", unsafe_allow_html=True)
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo", "💰 Financeiro"])
        tam_fonte = st.select_slider("Tamanho Letra", options=range(18, 42, 2), value=24) if menu in ["📢 Mural", "📖 Bíblia"] else 18
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.logado = False; st.rerun()

    st.markdown(f"""<style>
        .stApp {{ background-color: #f8fafc; }}
        .caixa-leitura {{ background: white; padding: 25px; border-radius: 10px; border: 1px solid #ddd; height: 600px; overflow-y: auto; font-size: {tam_fonte}px !important; line-height: 1.7; color: #1e3a8a !important; font-family: serif; }}
        .card-mural {{ background: white; padding: 25px; border-radius: 15px; border-left: 8px solid #1e3a8a; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }}
    </style>""", unsafe_allow_html=True)

    if admin_mode:
        st.title("⚙️ Administração")
        t_m, t_f = st.tabs(["📢 Mural", "💰 Financeiro"])
        with t_m:
            with st.form("admin_mural", clear_on_submit=True):
                tit, cont = st.text_input("Título"), st.text_area("Conteúdo")
                arq_img = st.file_uploader("Adicionar Foto", type=['jpg', 'png', 'jpeg'])
                if st.form_submit_button("Publicar"):
                    b64 = base64.b64encode(arq_img.read()).decode() if arq_img else ""
                    executar_query("INSERT INTO avisos (titulo, conteudo, img_data, data) VALUES (:t,:c,:i,:d)", 
                                  {"t":tit, "c":cont, "i":b64, "d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Postado!")
        with t_f:
            with st.form("admin_fin"):
                c1, c2 = st.columns(2); cod = c1.text_input("Cód. Membro"); val = c2.number_input("Valor", min_value=0.0)
                tipo = st.selectbox("Tipo", ["Entrada", "Saída"]); desc = st.text_input("Descrição")
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (codigo_doador, descricao, valor, tipo, data) VALUES (:c,:d,:v,:t,:dt)", 
                                  {"c":cod, "d":desc, "v":val, "t":tipo, "dt":datetime.now().strftime("%Y-%m-%d")})
                    st.success("Registrado!")

    elif menu == "📢 Mural":
        st.title("📢 Mural Ágape")
        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, av in avisos.iterrows():
            st.markdown(f'<div class="card-mural"><h4>{av["titulo"]}</h4><p>{av["conteudo"]}</p><small>{av["data"]}</small></div>', unsafe_allow_html=True)
            if av['img_data']: st.image(base64.b64decode(av['img_data']), use_column_width=True)

    elif menu == "🎥 Bate-papo":
        st.title("💬 Bate-papo")
        col_l, col_c = st.columns([0.3, 0.7])
        with col_l:
            membros = consultar_db("SELECT nome FROM membros WHERE nome != :n", {"n":u['nome']})
            dest = st.radio("Para:", ["Todos (Grupo)"] + list(membros['nome']))
        with col_c:
            chat_area = st.container(height=400)
            msgs = consultar_db("SELECT * FROM mensagens ORDER BY id ASC")
            with chat_area:
                for _, r in msgs.iterrows():
                    eu = r['de_user'] == u['nome']
                    align, cor = ("flex-end", "#dcf8c6") if eu else ("flex-start", "#ffffff")
                    st.markdown(f'<div style="display:flex; flex-direction:column; align-items:{align};"><div style="background:{cor}; padding:10px; border-radius:10px; margin-bottom:5px; max-width:80%; border:1px solid #ddd;"><b>{r["de_user"]}</b><br>{r["texto"]}</div></div>', unsafe_allow_html=True)
            
            with st.form("chat_f", clear_on_submit=True):
                msg_t = st.text_input("Mensagem")
                c1, c2 = st.columns([0.7, 0.3])
                arq = c1.file_uploader("Anexo", type=['pdf','jpg','png'])
                # LIMPEZA DO LINK DE VÍDEO
                sala = re.sub(r'\W+', '', f"Agape{u['nome']}{dest}")
                c2.link_button("🎥 Vídeo", f"https://jit.si{sala}", use_container_width=True)
                if st.form_submit_button("Enviar"):
                    b64, n_arq = "", ""
                    if arq: n_arq, b64 = arq.name, base64.b64encode(arq.read()).decode()
                    executar_query("INSERT INTO mensagens (de_user, para_user, texto, anexo_nome, anexo_data, data) VALUES (:d,:p,:t,:an,:ad,:dt)", 
                                  {"d":u['nome'], "p":dest, "t":msg_t, "an":n_arq, "ad":b64, "dt":datetime.now().strftime("%H:%M")})
                    st.rerun()

    elif menu == "📖 Bíblia":
        # ... (Mantido o código da bíblia em duas colunas)
        livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros.empty:
            c1, c2 = st.columns([0.3, 0.7])
            with c1:
                l_s = st.selectbox("Livro", livros['livro'])
                caps = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l ORDER BY cap ASC", {"l":l_s})
                c_s = st.selectbox("Capítulo", caps['cap'])
                vers = consultar_db("SELECT ver FROM biblia WHERE livro=:l AND cap=:c ORDER BY ver ASC", {"l":l_s, "c":c_s})
                v_s = st.selectbox("Versículo", ["Todos"] + list(vers['ver']))
            with c2:
                q = "SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c"
                p = {"l":l_s, "c":c_s}
                if v_s != "Todos": q += " AND ver=:v"; p["v"] = v_s
                res = consultar_db(q + " ORDER BY ver ASC", p)
                txt = "".join([f"<p><b>{v['ver']}</b> {v['texto']}</p>" for _, v in res.iterrows()])
                st.markdown(f'<div class="caixa-leitura">{txt}</div>', unsafe_allow_html=True)

    elif menu == "💰 Financeiro":
        df = consultar_db("SELECT * FROM financeiro")
        if not df.empty:
            e, s = df[df['tipo']=='Entrada']['valor'].sum(), df[df['tipo']=='Saída']['valor'].sum()
            c1, c2, c3 = st.columns(3); c1.metric("Receitas", f"R$ {e:,.2f}"); c2.metric("Despesas", f"R$ {s:,.2f}"); c3.metric("Saldo", f"R$ {e-s:,.2f}")
            st.dataframe(df, use_container_width=True)
