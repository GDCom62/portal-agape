import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, json, io

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
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, codigo_doador TEXT, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, anexo_nome TEXT, anexo_data TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (chave TEXT PRIMARY KEY, valor TEXT)')
    
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
        st.markdown(f'<h1 style="text-align:center;">⛪</h1>', unsafe_allow_html=True)

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    _, col_c, _ = st.columns([1, 1.5, 1])
    with col_c:
        exibir_logo(180)
        st.title("Portal Ágape")
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
            with st.form("cad", clear_on_submit=True):
                n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Conta", use_container_width=True):
                    if n and em and se:
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
        
        if menu == "📖 Bíblia":
            tam_fonte = st.select_slider("Tamanho da Letra", options=range(18, 36, 2), value=24)
        else: tam_fonte = 20

        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.logado = False; st.rerun()

    # CSS Global Atualizado
    st.markdown(f"""
        <style>
        .stApp {{ background-color: #f8fafc; }}
        /* Estilo do Mural */
        .card-mural {{ background: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; border-left: 8px solid #1e3a8a; }}
        .card-mural h4 {{ color: #1e3a8a !important; font-size: 26px !important; margin-bottom: 10px; }}
        .card-mural p {{ font-size: 22px !important; color: #334155; line-height: 1.6; }}
        /* Estilo da Bíblia */
        .caixa-leitura {{ background: white; padding: 30px; border-radius: 10px; border: 1px solid #ddd; height: 600px; overflow-y: auto; font-size: {tam_fonte}px !important; line-height: 1.8; font-family: serif; color: #1e3a8a !important; }}
        .num-verso {{ color: #64748b; font-weight: bold; font-size: 0.7em; margin-right: 8px; }}
        /* Estilo do Chat */
        .chat-bubble {{ padding: 12px; border-radius: 15px; margin-bottom: 10px; max-width: 80%; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); font-size: 18px; }}
        </style>
    """, unsafe_allow_html=True)

    if admin_mode:
        st.title("⚙️ Administração")
        with st.form("novo_aviso"):
            tit, cont = st.text_input("Título Aviso"), st.text_area("Conteúdo")
            if st.form_submit_button("Publicar Aviso"):
                executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t,:c,:d)", {"t":tit, "c":cont, "d":datetime.now().strftime("%d/%m/%Y")})
                st.rerun()

    elif menu == "📢 Mural":
        st.title("📢 Mural Ágape")
        
        if 'palavra_gerada' not in st.session_state:
            res_p = consultar_db("SELECT livro, cap, ver, texto FROM biblia ORDER BY RANDOM() LIMIT 1")
            if not res_p.empty:
                p = res_p.iloc[0]
                st.session_state.palavra_gerada = f'"{p["texto"]}" ({p["livro"]} {p["cap"]}:{p["ver"]})'
        
        if 'palavra_gerada' in st.session_state:
            st.info(f"📖 **PALAVRA DO DIA**\n\n{st.session_state.palavra_gerada}")
        
        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, av in avisos.iterrows():
            st.markdown(f'<div class="card-mural"><h4>{av["titulo"]}</h4><p>{av["conteudo"]}</p><small>{av["data"]}</small></div>', unsafe_allow_html=True)

    elif menu == "📖 Bíblia":
        st.title("📖 Bíblia Sagrada")
        
        # Importação (Verifica se está vazia)
        total_v_res = consultar_db("SELECT COUNT(*) as total FROM biblia")
        total_v = total_v_res.iloc[0]['total'] if not total_v_res.empty else 0

        if total_v < 10 and os.path.exists("acf.json"):
            with st.spinner("Importando Bíblia..."):
                try:
                    with open("acf.json", "r", encoding="utf-8-sig") as f:
                        dados = json.load(f)
                        for livro in dados:
                            nome_l = livro.get('name', livro.get('abrev'))
                            for n_cap, cap in enumerate(livro['chapters']):
                                for n_ver, texto in enumerate(cap):
                                    executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l,:c,:v,:t)", {"l":nome_l, "c":n_cap+1, "v":n_ver+1, "t":str(texto)})
                    st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

        livros_db = consultar_db("SELECT DISTINCT livro FROM biblia")
        if not livros_db.empty:
            col_nav, col_txt = st.columns([0.3, 0.7])
            with col_nav:
                l_sel = st.selectbox("Escolha o Livro", livros_db['livro'])
                caps_db = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l ORDER BY cap ASC", {"l":l_sel})
                c_sel = st.selectbox("Capítulo", caps_db['cap'])
            with col_txt:
                versos = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c ORDER BY ver ASC", {"l":l_sel, "c":c_sel})
                texto_html = "".join([f"<p><span class='num-verso'>{v['ver']}</span> {v['texto']}</p>" for _, v in versos.iterrows()])
                st.markdown(f'<div class="caixa-leitura">{texto_html}</div>', unsafe_allow_html=True)

    elif menu == "🎥 Bate-papo":
        st.title("💬 Bate-papo Interno")
        membros = consultar_db("SELECT nome FROM membros WHERE nome != :n", {"n":u['nome']})
        contato = st.selectbox("Enviar para:", ["Todos"] + list(membros['nome']))
        area = st.container(height=400)
        msgs = consultar_db("SELECT * FROM mensagens ORDER BY id ASC")
        with area:
            for _, row in msgs.iterrows():
                is_me = row['de_user'] == u['nome']
                align, color = ("flex-end", "#dcf8c6") if is_me else ("flex-start", "#ffffff")
                st.markdown(f'<div style="display: flex; flex-direction: column; align-items: {align};"><div class="chat-bubble" style="background-color: {color};"><b>{row["de_user"]}</b><br>{row["texto"]}</div></div>', unsafe_allow_html=True)
                if row['anexo_data']:
                    st.download_button(label=f"📁 {row['anexo_nome']}", data=base64.b64decode(row['anexo_data']), file_name=row['anexo_nome'], key=f"chat_{row['id']}")
        with st.form("envio", clear_on_submit=True):
            t_msg = st.text_input("Mensagem")
            arq = st.file_uploader("Anexo", type=['pdf','jpg','png'])
            if st.form_submit_button("Enviar"):
                b64, nome = "", ""
                if arq: nome, b64 = arq.name, base64.b64encode(arq.read()).decode()
                executar_query("INSERT INTO mensagens (de_user, para_user, texto, anexo_nome, anexo_data, data) VALUES (:d,:p,:t,:an,:ad,:dt)", {"d":u['nome'], "p":contato, "t":t_msg, "an":nome, "ad":b64, "dt":datetime.now().strftime("%H:%M")})
                st.rerun()

    elif menu == "💰 Financeiro":
        st.title("💰 Financeiro")
        df = consultar_db("SELECT * FROM financeiro")
        if not df.empty:
            ent, sai = df[df['tipo']=='Entrada']['valor'].sum(), df[df['tipo']=='Saída']['valor'].sum()
            c1, c2, c3 = st.columns(3); c1.metric("Receitas", f"R$ {ent:,.2f}"); c2.metric("Despesas", f"R$ {sai:,.2f}"); c3.metric("Saldo", f"R$ {ent-sai:,.2f}")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer: df.to_excel(writer, index=False, sheet_name='Financeiro')
            st.download_button(label="📥 Baixar Excel", data=output.getvalue(), file_name="financeiro.xlsx")
            st.dataframe(df, use_container_width=True)
