import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, io, re

# --- 1. CONFIGURAÇÕES E ESTILO DIVINO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

def aplicar_estilo_divino(tam_fonte):
    st.markdown(f"""
        <style>
        /* Fundo com degradê suave e iluminado */
        .stApp {{
            background: radial-gradient(circle, #ffffff 0%, #fdfbf0 100%);
        }}
        
        /* Títulos em Dourado e Azul Real */
        h1, h2, h3 {{
            color: #b8860b !important;
            text-align: center;
            font-family: 'Georgia', serif;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
        }}

        /* Cards do Mural - Aparência de Pergaminho/Luxo */
        .card-mural {{
            background: white;
            padding: 30px;
            border-radius: 20px;
            border: 2px solid #ffd700;
            box-shadow: 0 10px 25px rgba(184, 134, 11, 0.15);
            margin-bottom: 25px;
            color: #2c3e50;
        }}

        /* Palavra do Dia - Destaque Celestial */
        .palavra-do-dia {{
            background: linear-gradient(135.2deg, #fffcf0 1.2%, #fff3ad 98.8%);
            padding: 40px;
            border-radius: 25px;
            border: 3px double #b8860b;
            text-align: center;
            margin-bottom: 40px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        }}

        /* Caixa de Leitura da Bíblia */
        .caixa-leitura {{
            background: #ffffff;
            padding: 40px;
            border-radius: 15px;
            border-left: 15px solid #b8860b;
            box-shadow: inset 0 0 10px rgba(0,0,0,0.05);
            font-size: {tam_fonte}px !important;
            line-height: 1.8;
            color: #1a1a1a;
            font-family: 'Times New Roman', serif;
        }}

        /* Chat Bubbles - Branco e Dourado Suave */
        .chat-bubble {{
            padding: 15px;
            border-radius: 20px;
            margin-bottom: 10px;
            border: 1px solid #eee;
            color: #333 !important;
            font-size: 18px;
        }}
        
        /* Botões Estilizados */
        .stButton>button {{
            background-color: #b8860b !important;
            color: white !important;
            border-radius: 50px !important;
            border: none !important;
            transition: 0.3s;
        }}
        .stButton>button:hover {{
            background-color: #ffd700 !important;
            transform: scale(1.02);
        }}
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

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    aplicar_estilo_divino(22)
    _, col_c, _ = st.columns([1, 1.5, 1])
    with col_c:
        st.markdown("<h1 style='font-size: 50px;'>⛪ ÁGAPE</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#b8860b;'>Bem-vindo à Casa do Senhor</p>", unsafe_allow_html=True)
        t_l, t_c = st.tabs(["✨ Entrar", "📝 Cadastrar-se"])
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
                n, em, se = st.text_input("Nome Completo"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Minha Conta"):
                    c = "AG-" + "".join(random.choices(string.digits, k=4))
                    executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES (:n,:e,:c,:p,0)", {"n":n,"e":em,"c":c,"p":generate_password_hash(se)})
                    st.success(f"Glória a Deus! Sua conta foi criada. Código: {c}")

# --- 4. ÁREA LOGADA ---
else:
    u = st.session_state.user
    with st.sidebar:
        st.markdown(f"<h2 style='color:#b8860b;'>🙏 {u['nome']}</h2>", unsafe_allow_html=True)
        menu = st.radio("Caminho", ["📢 Mural da Fé", "📖 Bíblia Sagrada", "🎥 Comunhão (Bate-papo)", "💰 Tesouraria"])
        tam_fonte = st.select_slider("Tamanho da Letra", options=range(18, 46, 2), value=24)
        admin_mode = st.checkbox("⚙️ Modo Supervisor") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.clear(); st.rerun()

    aplicar_estilo_divino(tam_fonte)

    if admin_mode and menu != "🎥 Comunhão (Bate-papo)":
        st.title("⚙️ Administração da Igreja")
        tm, tf = st.tabs(["📢 Mural", "💰 Financeiro"])
        with tm:
            with st.form("f_mural", clear_on_submit=True):
                tit, cont = st.text_input("Título"), st.text_area("Conteúdo")
                foto = st.file_uploader("Imagem", type=['jpg','png','jpeg'])
                if st.form_submit_button("Publicar Aviso"):
                    img = base64.b64encode(foto.read()).decode() if foto else ""
                    executar_query("INSERT INTO avisos (titulo, conteudo, img_data, data) VALUES (:t,:c,:i,:d)", {"t":tit, "c":cont, "i":img, "d":datetime.now().strftime("%d/%m/%Y")})
                    st.rerun()
            for _, r in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
                if st.button(f"🗑️ Excluir: {r['titulo']}", key=f"del_{r['id']}"):
                    executar_query("DELETE FROM avisos WHERE id=:id", {"id":r['id']}); st.rerun()
        with tf:
            with st.form("f_fin"):
                d, v, t = st.text_input("Desc."), st.number_input("Valor"), st.selectbox("Tipo", ["Entrada", "Saída"])
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (:d,:v,:t,:dt)", {"d":d, "v":v, "t":t, "dt":datetime.now().strftime("%Y-%m-%d")})
                    st.rerun()

    elif menu == "📢 Mural da Fé":
        st.title("📢 Mural da Fé")
        if 'palavra_dia' not in st.session_state:
            p_res = consultar_db("SELECT livro, cap, ver, texto FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not p_res.empty: st.session_state.palavra_dia = p_res.iloc[0]
        
        if 'palavra_dia' in st.session_state:
            p = st.session_state.palavra_dia
            st.markdown(f"""<div class="palavra-do-dia"><span class="palavra-texto">"{p['texto']}"</span><br><br>
                        <span style="color:#b8860b; font-size:22px;">📖 {p['livro']} {p['cap']}:{p['ver']}</span></div>""", unsafe_allow_html=True)

        for _, av in consultar_db("SELECT * FROM avisos ORDER BY id DESC").iterrows():
            st.markdown(f'<div class="card-mural"><h3>{av["titulo"]}</h3><p style="font-size:22px;">{av["conteudo"]}</p><small>{av["data"]}</small></div>', unsafe_allow_html=True)
            if av['img_data']: st.image(base64.b64decode(av['img_data']), width=500)

    elif menu == "🎥 Comunhão (Bate-papo)":
        st.title("💬 Espaço de Comunhão")
        c1, c2 = st.columns([0.3, 0.7])
        with c1:
            st.subheader("👥 Irmãos")
            membros_db = consultar_db("SELECT nome FROM membros WHERE nome != :n ORDER BY nome ASC", {"n": u['nome']})
            contato = st.radio("Selecione para conversar:", ["Todos (Grupo)"] + list(membros_db['nome']))
            st.divider()
            sala_id = "Geral" if contato == "Todos (Grupo)" else "".join(sorted([u['nome'], contato])).replace(" ", "")
            st.link_button(f"🎥 Vídeo com {contato}", f"https://jit.si_{sala_id}#config.prejoinPageEnabled=false", use_container_width=True)

        with c2:
            st.subheader(f"🗨️ Conversa com {contato}")
            chat_container = st.container(height=450)
            
            if contato == "Todos (Grupo)":
                df_msg = consultar_db("SELECT * FROM mensagens WHERE para_user = 'Todos (Grupo)' ORDER BY id ASC")
            elif admin_mode:
                df_msg = consultar_db("SELECT * FROM mensagens WHERE (de_user = :c OR para_user = :c) AND para_user != 'Todos (Grupo)' ORDER BY id ASC", {"c": contato})
            else:
                df_msg = consultar_db("SELECT * FROM mensagens WHERE (de_user=:u AND para_user=:c) OR (de_user=:c AND para_user=:u) ORDER BY id ASC", {"u": u['nome'], "c": contato})
            
            with chat_container:
                for _, r in df_msg.iterrows():
                    is_me = r['de_user'] == u['nome']
                    align, cor = ("flex-end", "#fff9c4") if is_me else ("flex-start", "#ffffff")
                    st.markdown(f'<div style="display:flex; flex-direction:column; align-items:{align};"><div class="chat-bubble" style="background:{cor};"><b>{r["de_user"]}</b><br>{r["texto"]}</div></div>', unsafe_allow_html=True)
                    if r['anexo_data']:
                        try: st.download_button(label=f"📁 {r['anexo_nome']}", data=base64.b64decode(r['anexo_data']), file_name=r['anexo_nome'], key=f"dl_{r['id']}")
                        except: pass

            with st.form("f_chat", clear_on_submit=True):
                txt, arq = st.text_input("Sua mensagem"), st.file_uploader("Enviar um arquivo", type=['pdf','png','jpg','docx'])
                if st.form_submit_button("Enviar Mensagem"):
                    b64 = base64.b64encode(arq.read()).decode() if arq else ""
                    executar_query("INSERT INTO mensagens (de_user, para_user, texto, anexo_data, anexo_nome, data) VALUES (:d,:p,:t,:ad,:an,:dt)", 
                                  {"d":u['nome'], "p":contato, "t":txt, "ad":b64, "an":arq.name if arq else "", "dt":datetime.now().strftime("%H:%M")})
                    st.rerun()

    elif menu == "📖 Bíblia Sagrada":
        l_db = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not l_db.empty:
            cc1, cc2 = st.columns([0.3, 0.7])
            with cc1:
                l_s = cc1.selectbox("Livro", l_db['livro'])
                c_s = cc1.selectbox("Capítulo", consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":l_s})['cap'])
            v_res = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c", {"l":l_s, "c":c_s})
            txt_h = "".join([f"<p><span style='color:#b8860b; font-weight:bold;'>{v['ver']}</span> {v['texto']}</p>" for _, v in v_res.iterrows()])
            cc2.markdown(f'<div class="caixa-leitura">{txt_h}</div>', unsafe_allow_html=True)

    elif menu == "💰 Tesouraria":
        st.title("💰 Tesouraria da Igreja")
        df = consultar_db("SELECT * FROM financeiro")
        if not df.empty:
            e, s = df[df['tipo']=='Entrada']['valor'].sum(), df[df['tipo']=='Saída']['valor'].sum()
            st.metric("Saldo Abençoado", f"R$ {e-s:,.2f}", delta=e-s)
            st.dataframe(df, use_container_width=True)
