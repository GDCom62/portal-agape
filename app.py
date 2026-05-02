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
    else: st.markdown(f'<h1 style="text-align:center; color:#1e3a8a;">⛪ ÁGAPE</h1>', unsafe_allow_html=True)

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
                    st.success(f"Criado! Cód: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    with st.sidebar:
        exibir_logo(80)
        st.markdown(f"### 🙏 {u['nome']}")
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo", "💰 Financeiro"])
        tam_fonte = st.select_slider("Tamanho da Letra", options=range(18, 42, 2), value=24)
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    # CSS GLOBAL
    st.markdown(f"""<style>
        .stApp {{ background-color: #f8fafc; }}
        .caixa-leitura {{ background: white; padding: 25px; border-radius: 10px; border: 2px solid #1e3a8a; font-size: {tam_fonte}px !important; color: black; line-height: 1.6; }}
        .card-mural {{ background: white; padding: 25px; border-radius: 15px; border-left: 10px solid #1e3a8a; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 20px; color: black; }}
        .palavra-do-dia {{ background-color: #e0f2fe; padding: 30px; border-radius: 20px; border: 2px solid #0369a1; text-align: center; margin-bottom: 30px; }}
        .palavra-texto {{ font-size: 30px !important; color: #0369a1 !important; font-family: serif; font-style: italic; font-weight: bold; }}
    </style>""", unsafe_allow_html=True)

    if admin_mode:
        st.title("⚙️ Administração")
        tm, tf = st.tabs(["📢 Mural", "💰 Financeiro"])
        with tm:
            st.subheader("Gerenciar Avisos")
            with st.form("f_mural", clear_on_submit=True):
                tit = st.text_input("Título")
                cont = st.text_area("Conteúdo")
                foto = st.file_uploader("Foto", type=['jpg','png','jpeg'])
                if st.form_submit_button("Publicar"):
                    img = base64.b64encode(foto.read()).decode() if foto else ""
                    executar_query("INSERT INTO avisos (titulo, conteudo, img_data, data) VALUES (:t,:c,:i,:d)", {"t":tit, "c":cont, "i":img, "d":datetime.now().strftime("%d/%m/%Y")})
                    st.rerun()
            
            st.divider()
            avisos_list = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, r in avisos_list.iterrows():
                col_i, col_b = st.columns([0.8, 0.2])
                col_i.write(f"**{r['titulo']}**")
                if col_b.button("🗑️ Excluir", key=f"del_av_{r['id']}"):
                    executar_query("DELETE FROM avisos WHERE id=:id", {"id":r['id']}); st.rerun()

        with tf:
            st.subheader("Gerenciar Lançamentos")
            with st.form("f_fin"):
                d_f, v_f = st.text_input("Descrição"), st.number_input("Valor", min_value=0.0)
                t_f = st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":d_f, "v":v_f, "t":t_f, "dt":datetime.now().strftime("%Y-%m-%d")})
                    st.rerun()
            
            st.divider()
            fin_list = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
            for _, r in fin_list.iterrows():
                col_i, col_b = st.columns([0.8, 0.2])
                col_i.write(f"**{r['descricao']}** - R$ {r['valor']:.2f}")
                if col_b.button("🗑️", key=f"del_fin_{r['id']}"):
                    executar_query("DELETE FROM financeiro WHERE id=:id", {"id":r['id']}); st.rerun()

    elif menu == "📢 Mural":
        st.title("📢 Mural Ágape")
        # Palavra do Dia Automática (Sorteia uma por sessão)
        if 'palavra_dia' not in st.session_state:
            p_res = consultar_db("SELECT livro, cap, ver, texto FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not p_res.empty:
                st.session_state.palavra_dia = p_res.iloc[0]
        
        if 'palavra_dia' in st.session_state:
            p = st.session_state.palavra_dia
            st.markdown(f'<div class="palavra-do-dia"><span class="palavra-texto">"{p["texto"]}"</span><br><br><span style="color:#0369a1;">📖 {p["livro"]} {p["cap"]}:{p["ver"]}</span></div>', unsafe_allow_html=True)

        for _, av in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
            st.markdown(f'<div class="card-mural"><h3>{av["titulo"]}</h3><p style="font-size:22px;">{av["conteudo"]}</p><small>{av["data"]}</small></div>', unsafe_allow_html=True)
            if av['img_data']: st.image(base64.b64decode(av['img_data']), width=500)

    elif menu == "🎥 Bate-papo":
        st.title("💬 Bate-papo & Reunião")
        st.link_button("🎥 ENTRAR NA VÍDEO CHAMADA", "https://jit.si", use_container_width=True)
        st.divider()
        chat_box = st.container(height=400)
        msgs = consultar_db("SELECT * FROM mensagens ORDER BY id ASC")
        with chat_box:
            for _, r in msgs.iterrows():
                me = r['de_user'] == u['nome']
                align, cor = ("flex-end", "#dcf8c6") if me else ("flex-start", "#ffffff")
                st.markdown(f'<div style="display:flex; flex-direction:column; align-items:{align};"><div style="background:{cor}; padding:12px; border-radius:15px; margin-bottom:5px; max-width:80%; color:black; border:1px solid #ddd;"><b>{r["de_user"]}</b><br>{r["texto"]}</div></div>', unsafe_allow_html=True)
        
        with st.form("chat_f", clear_on_submit=True):
            txt, arq = st.text_input("Sua mensagem"), st.file_uploader("Anexo")
            if st.form_submit_button("Enviar"):
                b64 = base64.b64encode(arq.read()).decode() if arq else ""
                executar_query("INSERT INTO mensagens (de_user, texto, anexo_data, anexo_nome) VALUES (:d,:t,:ad,:an)", {"d":u['nome'], "t":txt, "ad":b64, "an":arq.name if arq else ""})
                st.rerun()

    elif menu == "💰 Financeiro":
        st.title("💰 Financeiro")
        df = consultar_db("SELECT * FROM financeiro")
        if not df.empty:
            e, s = df[df['tipo']=='Entrada']['valor'].sum(), df[df['tipo']=='Saída']['valor'].sum()
            st.metric("Saldo do Portal", f"R$ {e-s:,.2f}", delta=e-s)
            st.dataframe(df, use_container_width=True)

    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        # Importação do acf.json se necessário
        if consultar_db("SELECT COUNT(*) as total FROM biblia").iloc[0]['total'] < 10 and os.path.exists("acf.json"):
            with st.spinner("Importando Bíblia..."):
                with open("acf.json", "r", encoding="utf-8-sig") as f:
                    dados = json.load(f)
                    for livro in dados:
                        n_l = livro.get('name', 'Livro')
                        for n_c, cap in enumerate(livro['chapters']):
                            for n_v, txt in enumerate(cap):
                                executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l,:c,:v,:t)", {"l":n_l,"c":n_c+1,"v":n_v+1,"t":str(txt)})
                st.rerun()

        l_db = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not l_db.empty:
            c1, c2 = st.columns([0.3, 0.7])
            l_s = c1.selectbox("Livro", l_db['livro'])
            c_s = c1.selectbox("Capítulo", consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":l_s})['cap'])
            v_res = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c", {"l":l_s, "c":c_s})
            txt_h = "".join([f"<p><b>{v['ver']}</b> {v['texto']}</p>" for _, v in v_res.iterrows()])
            c2.markdown(f'<div class="caixa-leitura">{txt_h}</div>', unsafe_allow_html=True)
