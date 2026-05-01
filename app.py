import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, os, base64, io

# --- 1. CONFIGURAÇÕES E ESTILO ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .card-flutuante {
        background: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 15px;
        border-left: 5px solid #1e3a8a;
    }
    .chat-bubble {
        padding: 10px; border-radius: 15px; margin-bottom: 10px; max-width: 80%;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
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
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, codigo_doador TEXT, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS mensagens (id INTEGER PRIMARY KEY, de_user TEXT, para_user TEXT, texto TEXT, anexo_nome TEXT, anexo_data TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, cap INTEGER, ver INTEGER, texto TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

    # Bíblia Automática
    if consultar_db("SELECT id FROM biblia LIMIT 1").empty:
        versos = [
            {"l":"Gênesis", "c":1, "v":1, "t":"No princípio criou Deus o céu e a terra."},
            {"l":"Salmos", "c":23, "v":1, "t":"O Senhor é o meu pastor, nada me faltará."},
            {"l":"João", "c":3, "v":16, "t":"Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito."}
        ]
        for item in versos:
            executar_query("INSERT INTO biblia (livro, cap, ver, texto) VALUES (:l, :c, :v, :t)", item)

init_db()

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    _, col_c, _ = st.columns([1, 1.5, 1])
    with col_c:
        st.title("⛪ Portal Ágape")
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
        st.markdown(f"### 🙏 {u['nome']}")
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo", "💰 Financeiro"])
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.logado = False; st.rerun()

    if admin_mode:
        st.title("⚙️ Administração")
        tab1, tab2 = st.tabs(["📢 Mural", "💰 Finanças"])
        with tab1:
            with st.form("novo_aviso"):
                tit, cont = st.text_input("Título Aviso"), st.text_area("Conteúdo")
                if st.form_submit_button("Publicar Mural"):
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t,:c,:d)", {"t":tit,"c":cont,"d":datetime.now().strftime("%d/%m/%Y")})
                    st.success("Postado!")
        with tab2:
            with st.form("fin_admin"):
                c1, c2 = st.columns(2)
                cod_m = c1.text_input("Cód. Membro")
                val_m = c2.number_input("Valor", min_value=0.0)
                tipo_m = st.selectbox("Tipo", ["Entrada", "Saída"])
                desc_m = st.text_input("Descrição")
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (codigo_doador, descricao, valor, tipo, data) VALUES (:c,:d,:v,:t,:dt)", 
                                  {"c":cod_m, "d":desc_m, "v":val_m, "t":tipo_m, "dt":datetime.now().strftime("%Y-%m-%d")})
                    st.success("Sucesso!")

    else:
        if menu == "📢 Mural":
            st.title("📢 Mural")
            avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
            for _, av in avisos.iterrows():
                st.markdown(f'<div class="card-flutuante"><h4>{av["titulo"]}</h4><p>{av["conteudo"]}</p><small>{av["data"]}</small></div>', unsafe_allow_html=True)

        elif menu == "🎥 Bate-papo":
            st.title("💬 Bate-papo & Arquivos")
            membros = consultar_db("SELECT nome FROM membros WHERE nome != :n", {"n":u['nome']})
            contato = st.selectbox("Conversar com:", ["Todos"] + list(membros['nome']))
            
            area = st.container(height=400)
            msgs = consultar_db("SELECT * FROM mensagens ORDER BY id ASC")
            with area:
                for _, row in msgs.iterrows():
                    is_me = row['de_user'] == u['nome']
                    align, color = ("flex-end", "#dcf8c6") if is_me else ("flex-start", "#ffffff")
                    st.markdown(f'<div style="display: flex; flex-direction: column; align-items: {align};"><div class="chat-bubble" style="background-color: {color};"><b>{row["de_user"]}</b><br>{row["texto"]}</div></div>', unsafe_allow_html=True)
                    if row['anexo_data']:
                        st.download_button(label=f"📁 {row['anexo_nome']}", data=base64.b64decode(row['anexo_data']), file_name=row['anexo_nome'], key=f"btn_{row['id']}")

            with st.form("envio_chat", clear_on_submit=True):
                txt_msg = st.text_input("Mensagem")
                arq = st.file_uploader("Anexar (PDF, Imagem)", type=['pdf', 'jpg', 'png'])
                if st.form_submit_button("Enviar"):
                    b64, nome = "", ""
                    if arq:
                        nome = arq.name
                        b64 = base64.b64encode(arq.read()).decode()
                    executar_query("INSERT INTO mensagens (de_user, para_user, texto, anexo_nome, anexo_data, data) VALUES (:d,:p,:t,:an,:ad,:dt)", 
                                  {"d":u['nome'], "p":contato, "t":txt_msg, "an":nome, "ad":b64, "dt":datetime.now().strftime("%H:%M")})
                    st.rerun()

        elif menu == "📖 Bíblia":
            st.title("📖 Bíblia Sagrada")
            livros = consultar_db("SELECT DISTINCT livro FROM biblia")
            if not livros.empty:
                l_sel = st.selectbox("Livro", livros['livro'])
                caps = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro=:l", {"l":l_sel})
                c_sel = st.selectbox("Capítulo", caps['cap'])
                versos = consultar_db("SELECT ver, texto FROM biblia WHERE livro=:l AND cap=:c", {"l":l_sel, "c":c_sel})
                for _, v in versos.iterrows():
                    st.write(f"**{v['ver']}** {v['texto']}")

        elif menu == "💰 Financeiro":
            st.title("💰 Financeiro")
            df = consultar_db("SELECT * FROM financeiro")
            if not df.empty:
                ent, sai = df[df['tipo']=='Entrada']['valor'].sum(), df[df['tipo']=='Saída']['valor'].sum()
                c1, c2, c3 = st.columns(3)
                c1.metric("Receitas", f"R$ {ent:,.2f}")
                c2.metric("Despesas", f"R$ {sai:,.2f}")
                c3.metric("Saldo Atual", f"R$ {ent-sai:,.2f}")
                
                # Exportar Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Financeiro')
                st.download_button(label="📥 Baixar Relatório Excel", data=output.getvalue(), file_name="financeiro_agape.xlsx")
                
                st.dataframe(df, use_container_width=True)
            else: st.info("Sem registros.")
