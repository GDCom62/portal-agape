import streamlit as st
import pandas as pd
import json, os, base64
from sqlalchemy import create_engine, text
from datetime import datetime
from streamlit_webrtc import webrtc_streamer # Para a câmera

# --- CONFIGURAÇÕES ---
engine = create_engine("sqlite:///agape_v60.db", pool_pre_ping=True)

def executar_query(sql, params={}):
    with engine.begin() as conn: conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn: return pd.read_sql_query(text(sql), conn, params=params)

# --- ÁREA LOGADA ---
if st.session_state.get('logado'):
    u = st.session_state.user
    menu = st.sidebar.radio("Menu", ["📢 Mural", "📖 Bíblia", "🎥 Bate-papo", "💰 Financeiro"])
    admin_mode = st.sidebar.checkbox("⚙️ Modo Admin") if u['is_admin'] == 1 else False

    if admin_mode:
        st.title("⚙️ Administração")
        t1, t2 = st.tabs(["📄 Importar ACF.json", "💰 Finanças"])
        
        with t1:
            st.subheader("Carregar Dados ACF")
            arq_json = st.file_uploader("Selecione o arquivo acf.json", type="json")
            if arq_json:
                dados = json.load(arq_json)
                # Exemplo: salvando no banco (ajuste conforme a estrutura do seu JSON)
                st.write("Dados detectados:", dados)
                if st.button("Confirmar Importação"):
                    # Aqui você criaria a lógica para salvar cada item do JSON no banco
                    st.success("Dados importados com sucesso!")

    elif menu == "🎥 Bate-papo":
        st.title("🎥 Bate-papo & Câmera")
        
        aba_chat, aba_camera = st.tabs(["💬 Mensagens", "📷 Chamada de Vídeo"])
        
        with aba_chat:
            # Lista de Contatos
            membros = consultar_db("SELECT nome FROM membros WHERE nome != :n", {"n": u['nome']})
            contato_sel = st.selectbox("Conversar com:", ["Todos"] + list(membros['nome']))
            
            chat_area = st.container(height=300)
            df_msg = consultar_db("SELECT * FROM mensagens ORDER BY id ASC") # Adicione filtro de para_user se desejar
            
            with chat_area:
                for _, row in df_msg.iterrows():
                    st.markdown(f"**{row['de_user']}:** {row['texto']}")

            with st.form("msg"):
                txt = st.text_input("Sua mensagem")
                if st.form_submit_button("Enviar"):
                    executar_query("INSERT INTO mensagens (de_user, para_user, texto, data) VALUES (:d, :p, :t, :dt)",
                                  {"d": u['nome'], "p": contato_sel, "t": txt, "dt": datetime.now().strftime("%H:%M")})
                    st.rerun()

        with aba_camera:
            st.subheader("Conectar Câmera")
            st.write("Clique no botão abaixo para iniciar sua câmera no portal.")
            # Este componente abre a câmera do usuário localmente
            webrtc_streamer(key="chat-video")

    elif menu == "📢 Mural":
        st.title("📢 Mural")
        # Mostra avisos salvos no banco
        avisos = consultar_db("SELECT * FROM avisos ORDER BY id DESC")
        for _, av in avisos.iterrows():
            st.info(f"**{av['titulo']}**\n\n{av['conteudo']}")

    elif menu == "💰 Financeiro":
        st.title("💰 Financeiro")
        df = consultar_db("SELECT * FROM financeiro")
        st.metric("Saldo Geral", f"R$ {df['valor'].sum() if not df.empty else 0:,.2f}")
        st.dataframe(df)

else:
    st.warning("Por favor, faça login.")
