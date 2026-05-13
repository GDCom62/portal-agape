import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import redis, random, requests

# --- CONFIGURAÇÕES BÁSICAS ---
st.set_page_config(page_title="Portal Ágape", layout="wide", page_icon="⛪")

# URLs Oficiais (Substitua pelas suas URLs reais do Railway)
URL_CHAT_RAILWAY = "railway.app" 
REDIS_URL = "rediss://default:gQAAAAAAAcePAAIgcDFiYzVlZTAzZGZiNTg0OWFlYjUxZDdhY2E3Mzg0ODQ2Mg@calm-kangaroo-116623.upstash.io:6379"

# --- CONEXÃO BANCO E REDIS ---
engine = create_engine("sqlite:///agape_v60.db", connect_args={"check_same_thread": False})

try:
    r_db = redis.from_url(REDIS_URL, decode_responses=True)
except:
    r_db = None

def executar_query(sql, params=None):
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})

def consultar_db(sql, params=None):
    with engine.connect() as conn:
        try:
            return pd.read_sql_query(text(sql), conn, params=params or {})
        except:
            return pd.DataFrame()

# --- CARGA AUTOMÁTICA DA BÍBLIA COMPLETA ---
def carregar_biblia_completa():
    try:
        with st.spinner("📖 Configurando os 66 Livros da Bíblia... Aguarde alguns segundos."):
            # URL completa, direta e pública com o protocolo HTTPS obrigatório
            url = "githubusercontent.com"
            resposta = requests.get(url, timeout=15)
            
            if resposta.status_code == 200:
                dados_totais = resposta.json()
                linhas_db = []
                
                nomes_livros_pt = {
                    "gn": "Gênesis", "ex": "Êxodo", "lv": "Levítico", "num": "Números", "dt": "Deuteronômio",
                    "js": "Josué", "jz": "Juízes", "rt": "Rute", "1sm": "1 Samuel", "2sm": "2 Samuel",
                    "1re": "1 Reis", "2re": "2 Reis", "1cr": "1 Crônicas", "2cr": "2 Crônicas",
                    "ez": "Esdras", "ne": "Neemias", "et": "Ester", "jo": "Jó", "ps": "Salmos",
                    "pv": "Provérbios", "ec": "Eclesiastes", "ct": "Cânticos", "is": "Isaías",
                    "jr": "Jeremias", "lm": "Lamentações", "ezq": "Ezequiel", "dn": "Daniel",
                    "os": "Oséias", "jl": "Joel", "am": "Amós", "ob": "Obadias", "jn": "Jonas",
                    "mq": "Miqueias", "na": "Naum", "hc": "Habacuque", "sf": "Sofonias",
                    "ag": "Ageu", "zc": "Zacarias", "ml": "Malaquias",
                    "mt": "Mateus", "mc": "Marcos", "lc": "Lucas", "jo": "João", "at": "Atos",
                    "rm": "Romanos", "1co": "1 Coríntios", "2co": "2 Coríntios", "gl": "Gálatas",
                    "ef": "Efésios", "fp": "Filipenses", "cl": "Colossenses",
                    "1ts": "1 Tessalonicenses", "2ts": "2 Tessalonicenses",
                    "1tm": "1 Timóteo", "2tm": "2 Timóteo", "tt": "Tito", "fm": "Filemom",
                    "hb": "Hebreus", "tg": "Tiago", "1pe": "1 Pedro", "2pe": "2 Pedro",
                    "1jo": "1 João", "2jo": "2 João", "3jo": "3 João", "jd": "Judas", "ap": "Apocalipse"
                }
                
                for livro_sigla, capitulos in dados_totais.items():
                    nome_formatado = nomes_livros_pt.get(livro_sigla, livro_sigla.upper())
                    for cap_num, versiculos in capitulos.items():
                        for ver_num, texto_txt in versiculos.items():
                            linhas_db.append({
                                "livro": nome_formatado,
                                "cap": int(cap_num),
                                "ver": int(ver_num),
                                "texto": texto_txt.strip()
                            })
                
                df_salvar = pd.DataFrame(linhas_db)
                with engine.begin() as conn:
                    df_salvar.to_sql('biblia', conn, if_exists='replace', index=False)
                st.success("✅ Todos os 66 livros foram configurados!")
                st.rerun()
    except Exception as e:
        st.error(f"Erro ao estruturar banco da Bíblia: {e}")

# --- COMPONENTES VISUAIS (LOUVOR DO DIA) ---
def render_louvor():
    if 'versiculo_dia' not in st.session_state:
        try:
            df = consultar_db("SELECT livro, cap, ver, texto FROM biblia ORDER BY RANDOM() LIMIT 1")
            if len(df) > 0:
                st.session_state.versiculo_dia = {
                    "texto": df.iloc[0]['texto'],
                    "ref": f"{df.iloc[0]['livro']} {df.iloc[0]['cap']}:{df.iloc[0]['ver']}"
                }
            else: raise Exception()
        except:
            st.session_state.versiculo_dia = {"texto": "O Senhor é o meu pastor, nada me faltará.", "ref": "Salmos 23:1"}
    
    v = st.session_state.versiculo_dia
    st.markdown(f'<div class="floating-louvor"><small style="color:#1877f2;font-weight:bold">PALAVRA DE VIDA</small><br><i style="color:#333">"{v["texto"]}"</i><br><div style="text-align:right;color:#555;font-size:14px"><b>{v["ref"]}</b></div></div>', unsafe_allow_html=True)

# --- CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state: st.session_state.logado = False
if 'tela' not in st.session_state: st.session_state.tela = "login"

aplicar_estilo()

if not st.session_state.logado:
    st.markdown("<br><h1 style='text-align:center; color:#1877f2;'>⛪ Portal Ágape</h1>", unsafe_allow_html=True)
    if st.session_state.tela == "login":
        with st.form("login_f"):
            e, s = st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("ENTRAR", use_container_width=True):
                res = consultar_db("SELECT * FROM membros WHERE email=:e", {"e":e})
                if len(res) > 0 and check_password_hash(res.iloc[0]['senha'], s):
                    st.session_state.update({"logado": True, "user": res.iloc[0].to_dict()})
                    st.rerun()
                else: st.error("Login inválido")
        if st.button("Cadastrar novo membro"): st.session_state.tela = "cadastro"; st.rerun()
    else:
        with st.form("cad_f"):
            n, em, se = st.text_input("Nome"), st.text_input("E-mail"), st.text_input("Senha", type="password")
            if st.form_submit_button("CADASTRAR"):
                executar_query("INSERT INTO membros (nome, email, senha, is_admin) VALUES (:n,:em,:s,0)", {"n":n,"em":em,"s":generate_password_hash(se)})
                st.success("Sucesso!"); st.session_state.tela = "login"; st.rerun()
        if st.button("Voltar"): st.session_state.tela = "login"; st.rerun()

else:
    # --- ÁREA LOGADA ---
    u = st.session_state.user
    render_louvor()
    if r_db: r_db.set(f"online:{u['nome']}", "on", ex=60)

    with st.sidebar:
        st.markdown(f"### Olá, {u['nome']}! 🕊️")
        if st.button("🔄 Novo Louvor"):
            if 'versiculo_dia' in st.session_state: del st.session_state['versiculo_dia']
            st.rerun()
        if st.button("🚪 Sair"):
            st.session_state.clear(); st.rerun()

    # ABAS INTERNAS
    aba_mural, aba_chat, aba_biblia = st.tabs(["🏠 Mural", "💬 Chat Ágape", "📖 Bíblia"])

    with aba_mural:
        with st.expander("📢 Postar Mensagem"):
            msg = st.text_area("O que deseja compartilhar?")
            if st.button("Publicar"):
                executar_query("INSERT INTO avisos (conteudo, data, autor) VALUES (:c,:d,:a)", {"c":msg, "d":datetime.now().strftime("%d/%m %H:%M"), "a":u['nome']})
                st.rerun()
        
        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, av in avisos.iterrows():
            st.markdown(f'<div class="card-post"><b>@{av["autor"]}</b> • <small>{av["data"]}</small><p>{av["conteudo"]}</p></div>', unsafe_allow_html=True)
            if u['is_admin'] and st.button("🗑️ Excluir", key=f"del_{av['id']}"):
                executar_query("DELETE FROM avisos WHERE id=:id", {"id":av['id']})
                st.rerun()

    with aba_chat:
        # CORREÇÃO DEFINITIVA: Usando a sintaxe st.iframe recomendada nativamente pela nova versão do Streamlit
        st.iframe(f"{URL_CHAT_RAILWAY}?user={u['nome']}&room=agape", height=700)

    with aba_biblia:
        st.title("📖 Bíblia Sagrada Completa (Almeida)")
        
        df_livros = consultar_db("SELECT DISTINCT livro FROM biblia")
        
        if len(df_livros) > 0:
            lista_livros = df_livros['livro'].tolist()
            livro_selecionado = st.selectbox("Escolha o Livro:", lista_livros)
            
            if livro_selecionado:
                df_caps = consultar_db("SELECT DISTINCT cap FROM biblia WHERE livro = :l ORDER BY cap", {"l": livro_selecionado})
                lista_caps = df_caps['cap'].tolist()
                cap_selecionado = st.selectbox("Escolha o Capítulo:", lista_caps)
                
                if cap_selecionado:
                    st.divider()
                    st.subheader(f"📖 {livro_selecionado} - Capítulo {cap_selecionado}")
                    
                    df_versiculos = consultar_db(
                        "SELECT ver, texto FROM biblia WHERE livro = :l AND cap = :c ORDER BY ver",
                        {"l": livro_selecionado, "c": cap_selecionado}
                    )
                    
                    for _, row in df_versiculos.iterrows():
                        st.markdown(f"**{row['ver']}** {row['texto']}")
        else:
            st.warning("O banco de dados bíblico está sendo estruturado. Atualize a página.")
