import streamlit as st
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
import uuid
from datetime import datetime

# --- CONFIGURAÇÃO INICIAL (HACK PARA USAR SQLALCHEMY COM STREAMLIT) ---
# Criamos um app Flask "fantasma" apenas para o SQLAlchemy não reclamar
if 'db_initialized' not in st.session_state:
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portal_r.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)
    st.session_state.db = db
    st.session_state.app = app
    st.session_state.db_initialized = True

db = st.session_state.db
app = st.session_state.app

# --- MODELOS ---
class Membro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    codigo_membro = db.Column(db.String(20), unique=True, default=lambda: str(uuid.uuid4().hex[:6]).upper())

# Cria o banco se não existir
with app.app_context():
    db.create_all()

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Portal Agape", layout="wide")

# Menu Lateral (Substitui as rotas /login, /cadastro)
menu = st.sidebar.selectbox("Navegação", ["Home", "Bíblia", "Harpa Cristã", "Prestação de Contas", "Chat"])

if menu == "Home":
    st.title("⛪ Portal Agape")
    st.write("Bem-vindo ao portal! Use o menu lateral para navegar.")
    
    # Exemplo de Cadastro Simples
    with st.expander("Novo Cadastro"):
        nome = st.text_input("Nome")
        email = st.text_input("Email")
        if st.button("Cadastrar"):
            with app.app_context():
                novo = Membro(nome=nome, email=email)
                db.session.add(novo)
                db.session.commit()
                st.success(f"Membro {nome} cadastrado com sucesso!")

elif menu == "Bíblia":
    st.header("📖 Bíblia Sagrada")
    pesquisa = st.text_input("Pesquisar Livro ou Versículo")
    # Aqui você integraria com sua tabela Biblia

elif menu == "Chat":
    st.header("💬 Chat da Comunidade")
    # Nota: O Streamlit não usa SocketIO da mesma forma que o Flask.
    # Para um chat real, usaríamos o st.chat_message
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Diga algo..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
