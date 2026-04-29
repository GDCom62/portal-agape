import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random, string, json, os, base64, re

# --- 1. CONFIGURAÇÕES E ESTILO ---
URL_LOGO = "logo.png" 
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    h1, h2, h3 { color: #1e3a8a !important; text-align: center; }
    .card-flutuante {
        background-color: white; padding: 20px; border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 15px;
        border-left: 8px solid #1e3a8a;
    }
    .pix-box { background-color: #f0f9ff; padding: 20px; border-radius: 15px; border: 2px dashed #0369a1; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS (v60) ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY, nome TEXT, email TEXT UNIQUE, codigo TEXT, senha TEXT, is_admin INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS biblia (id INTEGER PRIMARY KEY, livro TEXT, capitulo INTEGER, versiculo INTEGER, texto TEXT, UNIQUE(livro, capitulo, versiculo))')
    executar_query('CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY, titulo TEXT, conteudo TEXT, data TEXT, img_data TEXT)')
    # Coluna data alterada para formato ISO no registro
    executar_query('CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY, codigo_doador TEXT, descricao TEXT, valor REAL, tipo TEXT, data TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY, titulo TEXT, link TEXT)')
    executar_query('CREATE TABLE IF NOT EXISTS configuracoes (id INTEGER PRIMARY KEY, chave TEXT UNIQUE, valor TEXT)')
    
    if consultar_db("SELECT id FROM membros WHERE email='admin@agape.com'").empty:
        pw = generate_password_hash('Agape2026')
        executar_query("INSERT INTO membros (nome, email, codigo, senha, is_admin) VALUES ('Admin', 'admin@agape.com', 'ADM-000', :pw, 1)", {"pw": pw})

init_db()

def logo_central(largura):
    if os.path.exists(URL_LOGO):
        with open(URL_LOGO, "rb") as f:
            data = base64.b64encode(f.read()).decode()
            st.markdown(f'<p align="center"><img src="data:image/png;base64,{data}" width="{largura}"></p>', unsafe_allow_html=True)

# --- 3. LOGIN ---
if 'logado' not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    _, col_c, _ = st.columns([1, 1.5, 1])
    with col_c:
        logo_central(180)
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
        logo_central(100)
        st.markdown(f"<p style='text-align: center;'>🙏 <b>{u['nome']}</b><br><small>Cód: {u['codigo']}</small></p>", unsafe_allow_html=True)
        menu = st.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎶 Louvores", "🎥 Bate-papo", "💰 Financeiro", "🎁 Doações"])
        admin_mode = st.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False
        if st.button("Sair"): st.session_state.logado = False; st.rerun()

    if admin_mode:
        st.title("⚙️ Administração")
        t_m, t_b, t_l, t_f, t_p = st.tabs(["📢 Mural", "📖 Bíblia", "🎶 Louvores", "💰 Finanças", "🎁 Pix"])
        
        with t_f:
            st.subheader("Registrar Movimentação")
            with st.form("f_fin", clear_on_submit=True):
                cod = st.text_input("Código do Membro", placeholder="Ex: AG-1234")
                desc = st.text_input("Descrição")
                valor = st.number_input("Valor R$", min_value=0.0)
                tipo = st.selectbox("Tipo", ["Entrada", "Saída"])
                data_lanca = st.date_input("Data do Lançamento", datetime.now())
                if st.form_submit_button("Lançar"):
                    executar_query("INSERT INTO financeiro (codigo_doador, descricao, valor, tipo, data) VALUES (:c,:d,:v,:t,:dt)", 
                                  {"c":cod if cod else "IGREJA", "d":desc, "v":valor, "t":tipo, "dt":data_lanca.strftime("%Y-%m-%d")})
                    st.success("Lançado!")

        # ... (Mantendo as outras abas de Admin: Mural, Bíblia, Louvores, Pix)

    else:
        if menu == "💰 Financeiro":
            st.title("💰 Balanço Financeiro")
            
            # Busca todos os dados e trata a data
            df = consultar_db("SELECT codigo_doador as 'Cód.', descricao as Descrição, valor as Valor, tipo as Tipo, data as Data FROM financeiro")
            
            if not df.empty:
                df['Data'] = pd.to_datetime(df['Data'])
                
                # --- FILTROS ---
                col_f1, col_f2 = st.columns(2)
                anos = sorted(df['Data'].dt.year.unique(), reverse=True)
                ano_sel = col_f1.selectbox("Filtrar por Ano", ["Todos"] + list(anos))
                
                meses_nomes = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 
                               7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
                
                mes_sel = col_f2.selectbox("Filtrar por Mês", ["Todos"] + list(meses_nomes.values()))

                # Aplicação do Filtro
                df_filtrado = df.copy()
                if ano_sel != "Todos":
                    df_filtrado = df_filtrado[df_filtrado['Data'].dt.year == int(ano_sel)]
                
                if mes_sel != "Todos":
                    mes_num = [k for k, v in meses_nomes.items() if v == mes_sel][0]
                    df_filtrado = df_filtrado[df_filtrado['Data'].dt.month == mes_num]

                # --- EXIBIÇÃO ---
                r = df_filtrado[df_filtrado['Tipo'] == 'Entrada']['Valor'].sum()
                p = df_filtrado[df_filtrado['Tipo'] == 'Saída']['Valor'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Receitas", f"R$ {r:,.2f}")
                c2.metric("Despesas", f"R$ {p:,.2f}")
                c3.metric("Saldo do Período", f"R$ {r-p:,.2f}")
                
                st.divider()
                # Formata data para exibição brasileira na tabela
                df_exibir = df_filtrado.copy()
                df_exibir['Data'] = df_exibir['Data'].dt.strftime('%d/%m/%Y')
                st.dataframe(df_exibir, use_container_width=True)
            else:
                st.info("Sem registros financeiros.")

        # ... (Mural, Bíblia, Louvores, Doações mantidos)
