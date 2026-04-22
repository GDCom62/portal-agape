import streamlit as st
import pandas as pd
from datetime import datetime
import io
import smtplib
from email.message import EmailMessage
from sqlalchemy import create_engine, text
from fpdf import FPDF

# --- 1. DESIGN E CONFIGURAÇÃO ---
st.set_page_config(page_title="Lavanderia Pro", layout="wide")

st.markdown("""
    <style>
    .stButton>button, .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input { border-radius: 12px !important; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #e0e0e0; }
    h1, h2, h3 { color: #1E3A8A; font-family: 'Segoe UI', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///gestao_lavanderia.db", pool_size=20, max_overflow=30)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS operadores (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, senha TEXT, funcao TEXT)')
    executar_query('''CREATE TABLE IF NOT EXISTS lotes (
                      id INTEGER PRIMARY KEY AUTOINCREMENT, hospital TEXT, peso_entrada REAL, maquina TEXT, 
                      processo TEXT, status TEXT, inicio_lavagem TEXT, fim_lavagem TEXT, inicio_secagem TEXT, 
                      fim_secagem TEXT, inicio_acabamento TEXT, fim_acabamento TEXT, saida_motorista TEXT, 
                      motorista_nome TEXT, peso_saida REAL, gaiola_num TEXT, operador_lavagem TEXT, 
                      operador_secagem TEXT, operador_acabamento TEXT)''')
    executar_query('CREATE TABLE IF NOT EXISTS contagem_itens (lote_id INTEGER, item TEXT, quantidade INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS alertas_panico (id INTEGER PRIMARY KEY AUTOINCREMENT, operador TEXT, etapa TEXT, data TEXT, resolvido INTEGER)')
    if consultar_db("SELECT * FROM operadores WHERE nome='admin'").empty:
        executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES ('admin', '1234', 'Administrador')")

init_db()

# --- 3. ESTADO DA SESSÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'operador' not in st.session_state: st.session_state['operador'] = ""
if 'funcao' not in st.session_state: st.session_state['funcao'] = ""
if 'tambor' not in st.session_state: st.session_state['tambor'] = []

# --- 4. LOGIN ---
if not st.session_state['logado']:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        try: st.image("logo.png", use_container_width=True)
        except: st.title("🏥 Lavanderia Login")
        
        with st.form("login"):
            u = st.text_input("Usuário")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                res = consultar_db("SELECT nome, funcao FROM operadores WHERE nome=:u AND senha=:s", {"u": u, "s": s})
                if not res.empty:
                    # CORREÇÃO AQUI: Acesso seguro aos dados da primeira linha
                    st.session_state['logado'] = True
                    st.session_state['operador'] = str(res.iloc[0]['nome'])
                    st.session_state['funcao'] = str(res.iloc[0]['funcao'])
                    st.rerun()
                else: st.error("Acesso Negado")

# --- 5. APP LOGADO ---
else:
    try: st.sidebar.image("logo.png", use_container_width=True)
    except: pass
    
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    menu = st.sidebar.radio("Navegação", ["Painel Geral", "1. Lavagem", "2. Rampa", "3. Secagem", "4. Acabamento", "5. Expedição", "📊 Relatórios", "⚙️ Gestão"])
    
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    # --- TELAS ---
    if menu == "Painel Geral":
        st.title("📈 Monitoramento Ativo")
        df_l = consultar_db("SELECT id, hospital, status, maquina, inicio_lavagem FROM lotes WHERE status != 'Finalizado'")
        if not df_l.empty:
            st.dataframe(df_l, use_container_width=True)
        else: st.info("Sem lotes em processamento.")

    elif menu == "1. Lavagem":
        st.header("📥 Entrada Lavadora")
        maq = st.selectbox("Máquina", ["M1 (120kg)", "M2 (120kg)", "M3 (100kg)", "M4 (60kg)", "M5 (50kg)"])
        with st.form("add_tambor", clear_on_submit=True):
            h_n = st.selectbox("Hospital", ["Hospital A", "Hospital B", "Hospital C"])
            h_p = st.number_input("Peso (kg)", min_value=1.0)
            h_t = st.radio("Tipo", ["Leve", "Pesada", "Relave"], horizontal=True)
            if st.form_submit_button("➕ Adicionar"): 
                st.session_state.tambor.append({"h": h_n, "p": h_p, "t": h_t})
        
        if st.session_state.tambor:
            st.table(pd.DataFrame(st.session_state.tambor))
            if st.button("🚀 INICIAR LAVAGEM"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                for i in st.session_state.tambor:
                    executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, processo, status, inicio_lavagem, operador_lavagem) VALUES (:h, :p, :m, :pr, 'Lavando', :dt, :op)",
                                   {"h": i['h'], "p": i['p'], "m": maq, "pr": i['t'], "dt": dt, "op": st.session_state['operador']})
                st.session_state.tambor = []; st.success("Lavagem Iniciada!"); st.rerun()

    elif menu == "4. Acabamento":
        st.header("🧺 Dobra e Passagem")
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Secando', 'Pronto')")
        if not df.empty:
            sel = st.selectbox("Lote:", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - ")[0])
            # Lista de itens
            lista = ["Lencol", "Fronha", "Oleado", "Colcha", "Edredon", "Calca", "Camisa", "Campo", "Tracado", "Camisola Adulto", "Camisola Infantil", "Cobertor", "Capote", "Toalha de Banho", "Toalha de Rosto", "Piso", "Cortina", "Outros"]
            ed = st.data_editor(pd.DataFrame([{"Item": i, "Qtd": 0} for i in lista]), hide_index=True)
            if st.button("✅ Salvar"):
                executar_query("UPDATE lotes SET status='Pronto', fim_secagem=:dt, inicio_acabamento=:dt, operador_acabamento=:op WHERE id=:id", {"dt": datetime.now().strftime("%Y-%m-%d %H:%M"), "op": st.session_state['operador'], "id": id_l})
                for _, r in ed.iterrows():
                    if r['Qtd'] > 0: executar_query("INSERT INTO contagem_itens VALUES (:id, :it, :q)", {"id": id_l, "it": r['Item'], "q": r['Qtd']})
                st.rerun()

    elif menu == "📊 Relatórios":
        st.title("📊 Produtividade")
        df = consultar_db("SELECT * FROM lotes")
        st.dataframe(df)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df.to_excel(wr, index=False)
        st.download_button("📥 Exportar Excel", buf.getvalue(), "relatorio.xlsx")

    elif menu == "⚙️ Gestão":
        st.header("⚙️ Cadastro de Colaborador")
        with st.form("cad"):
            n, s, f = st.text_input("Nome"), st.text_input("Senha"), st.selectbox("Função", ["Operador", "Motorista", "Administrador"])
            if st.form_submit_button("Salvar"): 
                executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES (:n, :s, :f)", {"n": n, "s": s, "f": f})
                st.success("Cadastrado!"); st.rerun()
