import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, io, re, unicodedata

# --- 1. CONFIGURAÇÕES E ESTILO DIVINO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

def aplicar_estilo_divino(tam_fonte):
    st.markdown(f"""
        <style>
        .stApp {{ background: #fdfbf0; }}
        h1, h2, h3 {{ color: #b8860b !important; text-align: center; font-weight: bold; font-family: 'Georgia', serif; }}
        p, span, label, li, .stMarkdown, .stSelectbox label {{ 
            color: #000000 !important; 
            font-weight: 600 !important; 
        }}
        .card-mural {{ background: white; padding: 20px; border-radius: 15px; border: 2px solid #ffd700; margin-bottom: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); color: #000 !important; }}
        .palavra-do-dia {{ background: #fff3ad; padding: 30px; border-radius: 20px; border: 3px double #b8860b; text-align: center; margin-bottom: 30px; }}
        .palavra-texto {{ font-size: 32px !important; color: #1e3a8a !important; font-family: serif; font-style: italic; font-weight: bold; line-height: 1.3; }}
        .caixa-leitura {{ background: white; padding: 30px; border-radius: 10px; border: 2px solid #b8860b; font-size: {tam_fonte}px !important; line-height: 1.7; color: black !important; font-family: serif; }}
        .chat-bubble {{ padding: 12px; border-radius: 15px; margin-bottom: 8px; color: black !important; border: 1px solid #ccc; font-size: 18px; font-weight: 500; }}
        </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, img_data TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, anexo_nome TEXT, anexo_data TEXT, data TEXT)')
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

def exibir_logo(largura=150):
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as f:
            data = base64.b64encode(f.read()).decode()
            st.markdown(f'<p align="center"><img src="data:image/png;base64,{data}" width="{largura}"></p>', unsafe_allow_html=True)
    else: st.markdown(f'<h1 style="text-align:center; color:#b8860b;">⛪ ÁGAPE</h1>', unsafe_allow_html=True)

def limpar_nome_video(texto):
    texto = unicodedata.normalize('NFD', str(texto)).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'\W+', '', texto)

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    aplicar_estilo_divino(22)
    _, col_c, _ = st.columns([1, 1.5, 1])
    with col_c:
        exibir_logo(180)
        t_l, t_c = st.tabs(["🔐 Entrar", "📝 Cadastro"])
        with t_l:
            with st.form("login"):
                e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Acessar", use_container_width=True):
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
        exibir_logo(80)
        st.markdown(f"### 🙏 {u['nome']}")
        menu = st.radio("Caminho", ["📢 Mural da Fé", "📖 Bíblia Sagrada", "🎥 Comunhão", "💰 Tesouraria"])
        tam_fonte = st.select_slider("Tamanho Fonte", options=range(18, 48, 2), value=24)
        admin_mode = st.checkbox("⚙️ Modo Admin (Supervisor)") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    aplicar_estilo_divino(tam_fonte)

    # --- MENU: MURAL ---
    if menu == "📢 Mural da Fé":
        st.title("📢 Mural da Fé")
        if admin_mode:
            with st.expander("➕ Publicar Novo Aviso"):
                with st.form("f_mural", clear_on_submit=True):
                    tit, cont = st.text_input("Título"), st.text_area("Conteúdo")
                    foto = st.file_uploader("Foto", type=['jpg','png','jpeg'])
                    if st.form_submit_button("Publicar"):
                        img = base64.b64encode(foto.read()).decode() if foto else ""
                        executar_query("INSERT INTO avisos (titulo, conteudo, img_data, data) VALUES (:t,:c,:i,:d)", {"t":tit, "c":cont, "i":img, "d":datetime.now().strftime("%d/%m/%Y")})
                        st.rerun()

        # Palavra do Dia Automática
        p_res = consultar_db("SELECT livro, cap, ver, texto FROM biblia ORDER BY RANDOM() LIMIT 1")
        if not p_res.empty:
            p = p_res.iloc[0]
            st.markdown(f'<div class="palavra-do-dia"><span class="palavra-texto">"{p["texto"]}"</span><br><br><span style="color:#b8860b; font-size:22px;">📖 {p["livro"]} {p["cap"]}:{p["ver"]}</span></div>', unsafe_allow_html=True)
        
        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, av in avisos.iterrows():
            st.markdown(f'<div class="card-mural"><h3>{av["titulo"]}</h3><p style="font-size:20px;">{av["conteudo"]}</p><small>{av["data"]}</small></div>', unsafe_allow_html=True)
            if av['img_data']: st.image(base64.b64decode(av['img_data']), width=300)
            if admin_mode:
                if st.button(f"🗑️ Excluir {av['titulo']}", key=f"del_av_{av['id']}"):
                    executar_query("DELETE FROM avisos WHERE id=:id", {"id":av['id']}); st.rerun()

    # --- MENU: BÍBLIA ---
    elif menu == "📖 Bíblia Sagrada":
        st.title("📖 Bíblia Sagrada")
        if consultar_db("SELECT COUNT(*) as t FROM biblia").iloc[0]['t'] < 10 and os.path.exists("acf.json"):
            with st.spinner("Carregando Escrituras..."):
                with open("acf.json", "r", encoding="utf-8-sig") as f:
                    dados = json.load(f)
                    for livro in dados:
                        for n_cap, cap in enumerate(livro['chapters']):
                            for n_ver, texto in enumerate(cap):
                                executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l,:c,:v,:t)", {"l":livro['name'],"c":n_cap+1,"v":n_ver+1,"t":str(texto)})
            st.rerun()
        
        l_db = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not l_db.empty:
            cc1, cc2 = st.columns([0.3, 0.7])
            l_s = cc1.selectbox("Livro", l_db['livro'])
            c_s = cc1.selectbox("Capítulo", consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":l_s})['cap'])
            txts = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c", {"l":l_s, "c":c_s})
            txt_h = "".join([f"<p><span style='color:#b8860b; font-weight:bold;'>{v['ver']}</span> {v['texto']}</p>" for _, v in txts.iterrows()])
            cc2.markdown(f'<div class="caixa-leitura">{txt_h}</div>', unsafe_allow_html=True)

    # --- MENU: COMUNHÃO ---
    elif menu == "🎥 Comunhão":
        st.title("💬 Espaço de Comunhão")
        c1, c2 = st.columns([0.4, 0.6])
        with c1:
            st.subheader("👥 Irmãos")
            m_db = consultar_db("SELECT nome FROM membros ORDER BY nome ASC")
            outros = [n for n in m_db['nome'] if n != u['nome']]
            dest = st.radio("Escolha com quem conversar:", ["Todos (Grupo)"] + outros, key="chat_dest")
            
            st.divider()
            # SALA DE VÍDEO CORRIGIDA COM BARRA /
            sala_id = f"Agape{limpar_nome_video(u['nome'])}{limpar_nome_video(dest)}"
            url_v = f"https://jit.si{sala_id}#config.prejoinPageEnabled=false"
            
            st.write("📹 **Vídeo Chamada**")
            st.components.v1.html(f"""
                <iframe src="{url_v}" allow="camera; microphone; fullscreen; display-capture; autoplay" 
                style="height: 380px; width: 100%; border: 3px solid #b8860b; border-radius: 15px; background: black;"></iframe>
            """, height=400)
            st.link_button("🚀 Abrir Vídeo em Tela Cheia", url_v, use_container_width=True)

        with c2:
            st.subheader(f"🗨️ {dest}")
            chat = st.container(height=450)
            if dest == "Todos (Grupo)":
                df_msg = consultar_db("SELECT * FROM mensagens WHERE para_user = 'Todos (Grupo)' ORDER BY id ASC")
            elif admin_mode:
                df_msg = consultar_db("SELECT * FROM mensagens WHERE (de_user = :c OR para_user = :c) AND para_user != 'Todos (Grupo)' ORDER BY id ASC", {"c": dest})
            else:
                df_msg = consultar_db("SELECT * FROM mensagens WHERE (de_user=:u AND para_user=:c) OR (de_user=:c AND para_user=:u) ORDER BY id ASC", {"u": u['nome'], "c": dest})
            
            with chat:
                for _, r in df_msg.iterrows():
                    me = r['de_user'] == u['nome']
                    align, cor = ("flex-end", "#fff9c4") if me else ("flex-start", "#ffffff")
                    st.markdown(f'<div style="display:flex; flex-direction:column; align-items:{align};"><div class="chat-bubble" style="background:{cor};"><b>{r["de_user"]}</b><br>{r["texto"]}</div></div>', unsafe_allow_html=True)
            
            with st.form("chat_f", clear_on_submit=True):
                txt, arq = st.text_input("Mensagem"), st.file_uploader("Anexo")
                if st.form_submit_button("Enviar"):
                    b64 = base64.b64encode(arq.read()).decode() if arq else ""
                    executar_query("INSERT INTO mensagens (de_user, para_user, texto, anexo_data, anexo_nome, data) VALUES (:d,:p,:t,:ad,:an,:dt)", 
                                  {"d":u['nome'], "p":dest, "t":txt, "ad":b64, "an":arq.name if arq else "", "dt":datetime.now().strftime("%H:%M")})
                    st.rerun()

    # --- MENU: TESOURARIA ---
    elif menu == "💰 Tesouraria":
        st.title("💰 Tesouraria")
        if admin_mode:
            with st.form("f_fin"):
                d_f, v_f, t_f = st.text_input("Desc."), st.number_input("Valor"), st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":d_f, "v":v_f, "t":t_f, "dt":datetime.now().strftime("%Y-%m-%d")})
                    st.rerun()
        
        df = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
        if not df.empty:
            e, s = df[df['tipo']=='Entrada']['valor'].sum(), df[df['tipo']=='Saída']['valor'].sum()
            st.metric("Saldo Abençoado", f"R$ {e-s:,.2f}")
            st.dataframe(df, use_container_width=True)
            if admin_mode:
                for _, r in df.iterrows():
                    if st.button(f"🗑️ Apagar {r['descricao']} (R${r['valor']})", key=f"dfin_{r['id']}"):
                        executar_query("DELETE FROM financeiro WHERE id=:id", {"id":r['id']}); st.rerun()
