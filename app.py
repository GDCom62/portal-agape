import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
import redis
import json
import requests
import datetime
import random

st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

URL_CHAT_RAILWAY = "https://railway.app" 
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

@st.cache_resource
def inicializar_conexoes():
    engine = create_engine("sqlite:///agape_v60.db", connect_args={"check_same_thread": False, "timeout": 30})
    try:
        r_db = redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        r_db = None
    return engine, r_db

engine, r_db = inicializar_conexoes()

def executar_query(sql, params=None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except Exception:
            return pd.DataFrame()

def buscar_versiculo_api():
    sugestoes = [
        {"slug": "jo", "cap": 3}, {"slug": "sl", "cap": 23},
        {"slug": "fp", "cap": 4}, {"slug": "is", "cap": 41},
        {"slug": "rm", "cap": 8}, {"slug": "mt", "cap": 6}
    ]
    escolha = random.choice(sugestoes)
    try:
        url = f"https://abibliadigital.com.br{escolha['slug']}/{escolha['cap']}"
        resposta = requests.get(url, timeout=3)
        if resposta.status_code == 200:
            dados = resposta.json()
            if "verses" in dados and len(dados["verses"]) > 0:
                v_sorteado = random.choice(dados["verses"])
                return v_sorteado.get("text", ""), f"{dados['book']['name']} {dados['chapter']}:{v_sorteado.get('number', 1)}"
    except Exception:
        pass
    return ("Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.", "João 3:16")

executar_query("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, senha TEXT, nivel TEXT DEFAULT 'Membro');")
executar_query("CREATE TABLE IF NOT EXISTS membros (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, telefone TEXT, cargo TEXT, data_cadastro TEXT, mes_aniversario TEXT, observacoes TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, descricao TEXT, valor REAL, data TEXT, mes_ano TEXT, membro_id INTEGER);")
executar_query("CREATE TABLE IF NOT EXISTS avisos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, conteudo TEXT, data TEXT);")
executar_query("CREATE TABLE IF NOT EXISTS louvores (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, artista TEXT, letra TEXT, arquivo_audio BLOB);")

st.title("⛪ Portal Ágape")
menu = ["Início & Versículos", "Membros", "Financeiro", "Avisos", "Louvores"]
escolha = st.selectbox("Selecione a seção do Portal:", menu, key="navigation_box_direct")
st.divider()

if escolha == "Início & Versículos":
    st.header("Mural de Versículos")
    texto_v, ref_v = buscar_versiculo_api()
    st.info(f'"{texto_v}" — {ref_v}')
    df_m_total = consultar_db("SELECT id FROM membros")
    st.metric("Total de Membros Cadastrados", f"{len(df_m_total)} Irmãos")

elif escolha == "Membros":
    st.header("👥 Gestão de Membros")
    aba_ver, aba_cadastrar = st.tabs(["Ver Membros", "Cadastrar Novo Membro"])
    with aba_cadastrar:
        with st.form("cad_membro_form", clear_on_submit=True):
            nome = st.text_input("Nome do Membro")
            telefone = st.text_input("Telefone / WhatsApp")
            cargo = st.selectbox("Cargo", ["Membro", "Diácono", "Presbítero", "Evangelista", "Pastor", "Missionária"])
            mes_aniv = st.selectbox("Mês Aniversário", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
            obs = st.text_area("Observações")
            if st.form_submit_button("Salvar Membro"):
                if nome:
                    data_atual = datetime.date.today().strftime('%d/%m/%Y')
                    executar_query("INSERT INTO membros (nome, telefone, cargo, data_cadastro, mes_aniversario, observacoes) VALUES (:nome, :tel, :cargo, :dt, :mes, :obs)", {"nome": nome, "tel": telefone, "cargo": cargo, "dt": data_atual, "mes": mes_aniv, "obs": obs})
                    st.success(f"{nome} cadastrado!")
                else:
                    st.error("Nome obrigatório.")
    with aba_ver:
        busca = st.text_input("Buscar por nome:", key="search_membro_input")
        df_membros = consultar_db("SELECT * FROM membros WHERE nome LIKE :b", {"b": f"%{busca}%"}) if busca else consultar_db("SELECT * FROM membros")
        if not df_membros.empty:
            for idx, row in df_membros.iterrows():
                st.write(f"**👤 {row['nome']}** - {row['cargo']} | Contato: {row['telefone']}")
                if st.button(f"Excluir {row['nome']}", key=f"del_m_{row['id']}"):
                    executar_query("DELETE FROM membros WHERE id = :id", {"id": row['id']})
                    st.rerun()
                st.divider()
        else:
            st.info("Nenhum membro encontrado.")

elif escolha == "Financeiro":
    st.header("💰 Controle Financeiro")
    aba_lancar, aba_caixa = st.tabs(["Lançar Movimentação", "Livro Caixa"])
    with aba_lancar:
        with st.form("cad_financeiro_form", clear_on_submit=True):
            tipo = st.radio("Tipo", ["Entrada (Dízimo/Oferta)", "Saída (Despesa)"])
            desc = st.text_input("Descrição / Finalidade")
            val = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
            if st.form_submit_button("Registrar Lançamento"):
                if desc and val > 0:
                    hj = datetime.date.today()
                    executar_query("INSERT INTO financeiro (tipo, descricao, valor, data, mes_ano, membro_id) VALUES (:tipo, :desc, :val, :dt, :ma, NULL)", {"tipo": tipo, "desc": desc, "val": val, "dt": hj.strftime('%d/%m/%Y'), "ma": hj.strftime('%m/%Y')})
                    st.success("Registrado!")
                else:
                    st.error("Preencha os dados corretamente.")
    with aba_caixa:
        df_fin = consultar_db("SELECT * FROM financeiro ORDER BY id DESC")
        if not df_fin.empty:
            ent = df_fin[df_fin['tipo'].str.contains("Entrada")]['valor'].sum()
            sai = df_fin[df_fin['tipo'].str.contains("Saída")]['valor'].sum()
            st.metric("Saldo Atual", f"R$ {ent - sai:,.2f}")
            st.dataframe(df_fin, use_container_width=True)
        else:
            st.info("Nenhum lançamento.")

elif escolha == "Avisos":
    st.header("📢 Mural de Avisos")
    with st.expander("➕ Publicar Novo Aviso"):
        with st.form("cad_aviso_form", clear_on_submit=True):
            t_aviso = st.text_input("Título")
            c_aviso = st.text_area("Conteúdo")
            if st.form_submit_button("Postar"):
                if t_aviso and c_aviso:
                    executar_query("INSERT INTO avisos (titulo, conteudo, data) VALUES (:t, :c, :d)", {"t": t_aviso, "c": c_aviso, "d": datetime.date.today().strftime('%d/%m/%Y')})
                    st.success("Postado!")
                    st.rerun()
    df_avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
    if not df_avisos.empty:
        for idx, row in df_avisos.iterrows():
            st.subheader(row['titulo'])
            st.caption(f"📅 {row['data']}")
            st.write(row['conteudo'])
            if st.button("Remover Aviso", key=f"del_av_{row['id']}"):
                executar_query("DELETE FROM avisos WHERE id = :id", {"id": row['id']})
                st.rerun()
            st.divider()
    else:
        st.info("Mural vazio.")

elif escolha == "Louvores":
    st.header("🎵 Repertório de Louvores")
    aba_list_l, aba_cad_l = st.tabs(["Repertório", "Adicionar Louvor"])
    with aba_cad_l:
        with st.form("form_louvor", clear_on_submit=True):
            t_musica = st.text_input("Título")
            a_musica = st.text_input("Artista")
            letra_m = st.text_area("Letra")
            if st.form_submit_button("Adicionar"):
                if t_musica and a_musica:
                    executar_query("INSERT INTO louvores (titulo, artista, letra, arquivo_audio) VALUES (:t, :a, :l, NULL)", {"t": t_musica, "a": a_musica, "l": letra_m})
                    st.success("Salvo!")
                else:
                    st.error("Campos obrigatórios.")
    with aba_list_l:
        df_louvores = consultar_db("SELECT id, titulo, artista, letra FROM louvores")
        if not df_louvores.empty:
            for idx, row in df_louvores.iterrows():
                with st.expander(f"🎶 {row['titulo']} — {row['artista']}"):
                    st.text(row['letra'])
                    if st.button("Excluir Música", key=f"del_l_{row['id']}"):
                        executar_query("DELETE FROM louvores WHERE id = :id", {"id": row['id']})
                        st.rerun()
        else:
            st.info("Repertório vazio.")
