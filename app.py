import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, re, unicodedata

# --- 1. CONFIGURAÇÕES E ESTILO DE ALTO CONTRASTE ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

def aplicar_estilo_facebook():
    st.markdown("""
        <style>
        /* Fonte Arial e Cores de Fundo */
        html, body, [class*="st-"], .stMarkdown {
            font-family: Arial, Helvetica, sans-serif !important;
        }
        .stApp { background-color: #f0f2f5; }

        /* Texto Geral: Preto Absoluto e Maior */
        p, span, label {
            color: #000000 !important;
            font-size: 20px !important;
            font-weight: 500 !important;
        }

        /* Bíblia: Texto Extra Grande para Leitura */
        .texto-biblico {
            font-size: 28px !important;
            color: #000000 !important;
            line-height: 1.6 !important;
            margin-bottom: 15px;
            text-align: justify;
        }

        /* Menu Lateral: Fundo Preto e Letras Brancas */
        [data-testid="stSidebar"] {
            background-color: #1c1e21 !important;
        }
        [data-testid="stSidebar"] * {
            color: #ffffff !important;
            font-size: 19px !important;
        }
        
        /* Cards do Feed e Bíblia */
        .card-post {
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            margin-bottom: 20px;
            border: 1px solid #ced0d4;
            color: black !important;
        }

        /* Títulos Azul Facebook */
        h1, h2, h3 { 
            color: #1877f2 !important; 
            font-family: Arial !important;
            font-weight: bold !important;
        }

        /* Botões */
        .stButton>button {
            border-radius: 8px !important;
            font-weight: bold !important;
        }
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
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, data TEXT)')
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

def importar_biblia_acf():
    if not os.path.exists("acf.json"):
        st.error("Arquivo acf.json não encontrado!")
        return
    try:
        with open("acf.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            executar_query("DELETE FROM biblia")
            for livro in data:
                nome_livro = livro['name']
                for i, cap in enumerate(livro['chapters']):
                    for j, texto in enumerate(cap):
                        executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l, :c, :v, :t)",
                                       {"l": nome_livro, "c": i+1, "v": j+1, "t": texto})
        st.success("Bíblia Importada com Sucesso!")
    except Exception as e: st.error(f"Erro na carga: {e}")

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    aplicar_estilo_facebook()
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        st.markdown("<h1 style='text-align:center; font-size:45px;'>facebook</h1>", unsafe_allow_html=True)
        with st.form("entrar"):
            e = st.text_input("E-mail")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if not res.empty and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                st.error("Dados incorretos.")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    aplicar_estilo_facebook()

    with st.sidebar:
        st.markdown(f"### 👤 {u['nome']}")
        menu = st.radio("Navegação", ["🏠 Feed", "📖 Bíblia", "👥 Comunhão", "💰 Financeiro"])
        adm = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if adm and st.button("📥 Importar acf.json"): importar_biblia_acf()
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    if menu == "🏠 Feed":
        st.title("Feed de Notícias")
        col_feed, col_side = st.columns([2, 1])
        with col_feed:
            if adm:
                with st.container():
                    st.markdown('<div class="card-post">', unsafe_allow_html=True)
                    with st.form("novo_post", clear_on_submit=True):
                        txt = st.text_area("No que você está pensando?")
                        if st.form_submit_button("Publicar"):
                            executar_query("INSERT INTO avisos (conteudo, data) VALUES (:c, :d)", 
                                           {"c":txt, "d":datetime.now().strftime("%d/%m/%Y %H:%M")})
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            
            posts = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, p in posts.iterrows():
                st.markdown(f"<div class='card-post'><b>Ministério Ágape</b> • <small>{p['data']}</small><br><br>{p['conteudo']}</div>", unsafe_allow_html=True)

    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        res_l = consultar_db("SELECT DISTINCT livro FROM biblia ORDER BY id")
        if not res_l.empty:
            c1, c2 = st.columns(2)
            l_sel = c1.selectbox("Livro", res_l['livro'].tolist())
            res_c = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l ORDER BY cap", {"l":l_sel})
            c_sel = c2.selectbox("Capítulo", res_c['cap'].tolist())
            
            st.markdown('<div class="card-post">', unsafe_allow_html=True)
            versos = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c ORDER BY ver", {"l":l_sel, "c":c_sel})
            for _, v in versos.iterrows():
                st.markdown(f'<p class="texto-biblico"><b>{v["ver"]}</b> {v["texto"]}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else: st.warning("Importe o arquivo acf.json no Modo Admin.")

    elif menu == "👥 Comunhão":
        st.title("👥 Espaço de Comunhão")
        membros = consultar_db("SELECT nome FROM membros")['nome'].tolist()
        dest = st.selectbox("Conversar com:", [m for m in membros if m != u['nome']])
        st.link_button(f"🎥 Iniciar Vídeo Chamada com {dest}", f"https://jit.si_{u['id']}_{dest}")
        
        st.markdown('<div class="card-post">', unsafe_allow_html=True)
        msgs = consultar_db("SELECT * FROM mensagens WHERE (de_user=:u AND para_user=:d) OR (de_user=:d AND para_user=:u) ORDER BY id", {"u":u['nome'], "d":dest})
        for _, m in msgs.iterrows():
            cor = "#e7f3ff" if m['de_user'] == u['nome'] else "#f0f2f5"
            st.markdown(f"<div style='background:{cor}; padding:10px; border-radius:10px; margin-bottom:5px;'><b>{m['de_user']}</b>: {m['texto']}</div>", unsafe_allow_html=True)
        
        with st.form("chat_msg", clear_on_submit=True):
            mtxt = st.text_input("Escreva sua mensagem...")
            if st.form_submit_button("Enviar"):
                executar_query("INSERT INTO mensagens (de_user, para_user, texto, data) VALUES (:u, :d, :t, :dt)",
                               {"u":u['nome'], "d":dest, "t":mtxt, "dt":datetime.now().isoformat()})
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    elif menu == "💰 Financeiro":
        st.title("💰 Gestão Financeira")
        if adm:
            with st.expander("Novo Lançamento"):
                with st.form("fin_form"):
                    desc = st.text_input("Descrição")
                    val = st.number_input("Valor", 0.0)
                    tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
                    if st.form_submit_button("Registrar"):
                        executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d, :v, :t, :dt)",
                                       {"d":desc, "v":val, "t":tipo, "dt":datetime.now().strftime("%d/%m/%Y")})
                        st.rerun()
        
        df_f = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
        if not df_f.empty:
            st.table(df_f[['data', 'descricao', 'tipo', 'valor']])
            ent = df_f[df_f['tipo']=='Entrada']['valor'].sum()
            sai = df_f[df_f['tipo']=='Saída']['valor'].sum()
            st.metric("Saldo Geral", f"R$ {ent - sai:,.2f}", f"Entradas: {ent} | Saídas: {sai}")
