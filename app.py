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
# Comunicação direta via rede interna do container
URL_API_LOCAL = "http://127.0.0.1:8000"

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
        with st.spinner("📢 Configurando os 66 Livros da Bíblia Sagrada... Aguarde alguns segundos."):
            # NOTA: Substitua pela URL crua (raw) real do JSON da Bíblia desejada
            url = "githubusercontent.com"
            resposta = requests.get(url, timeout=15)
            
            if resposta.status_code == 200:
                dados_totais = resposta.json()
                linhas_db = []
                
                # Mapeamento completo dos 66 livros (Sigla original do JSON -> Nome em PT-BR)
                nomes_livros_pt = {
                    "gn": "Gênesis", "ex": "Êxodo", "lv": "Levítico", "num": "Números", "dt": "Deuteronômio",
                    "js": "Josué", "jz": "Juízes", "rt": "Rute", "1sm": "1 Samuel", "2sm": "2 Samuel",
                    "1re": "1 Reis", "2re": "2 Reis", "1cr": "1 Crônicas", "2cr": "2 Crônicas",
                    "ez": "Esdras", "ne": "Neemias", "et": "Ester", "jo": "Jó", "ps": "Salmos",
                    "pv": "Provérbios", "ec": "Eclesiastes", "ct": "Cantares", "is": "Isaías", 
                    "jr": "Jeremias", "lm": "Lamentações", "ezk": "Ezequiel", "dn": "Daniel", 
                    "os": "Oséias", "jl": "Joel", "am": "Amós", "ob": "Obadias", "jn": "Jonas", 
                    "mq": "Miqueias", "na": "Naum", "hc": "Habacuque", "sf": "Sofonias", 
                    "ag": "Ageu", "zc": "Zacarias", "ml": "Malaquias",
                    "mt": "Mateus", "mc": "Marcos", "lc": "Lucas", "joao": "João", "at": "Atos", 
                    "rm": "Romanos", "1co": "1 Coríntios", "2co": "2 Coríntios", "gl": "Gálatas", 
                    "ef": "Efésios", "fp": "Filipenses", "cl": "Colossenses", "1ts": "1 Tessalonicenses", 
                    "2ts": "2 Tessalonicenses", "1tm": "1 Timóteo", "2tm": "2 Timóteo", "tt": "Tito", 
                    "fm": "Filemom", "hb": "Hebreus", "tg": "Tiago", "1pe": "1 Pedro", "2pe": "2 Pedro", 
                    "1jo": "1 João", "2jo": "2 João", "3jo": "3 João", "jd": "Judas", "ap": "Apocalipse"
                }
                
                # Loop para processar a estrutura padrão de JSONs bíblicos (Livro -> Capítulo -> Versículo)
                for livro_dados in dados_totais:
                    sigla = livro_dados.get("abbrev", "").lower()
                    nome_livro = nomes_livros_pt.get(sigla, livro_dados.get("name", "Desconhecido"))
                    
                    for c_idx, capitulo in enumerate(livro_dados.get("chapters", []), start=1):
                        for v_idx, versiculo in enumerate(capitulo, start=1):
                            linhas_db.append({
                                "livro": nome_livro,
                                "capitulo": c_idx,
                                "versiculo": v_idx,
                                "texto": versiculo
                            })
                
                # Salva os dados estruturados diretamente no SQLite
                df_biblia = pd.DataFrame(linhas_db)
                df_biblia.to_sql("biblia", engine, if_exists="replace", index=False)
                st.success("✅ Bíblia Sagrada carregada com sucesso no banco de dados!")
            else:
                st.error(f"Erro ao baixar os dados. Código de status: {resposta.status_code}")
                
    except Exception as e:
        st.error(f"Falha ao carregar a Bíblia: {e}")
