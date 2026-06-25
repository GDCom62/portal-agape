import streamlit as st
import json
import os
import urllib.request

# Configuração da página do Streamlit
st.set_page_config(page_title="Portal Ágape", page_icon="✝️", layout="wide")

# Inicialização das variáveis de estado (Session State)
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'mensagens_chat' not in st.session_state:
    st.session_state['mensagens_chat'] = []

# --- TELA DE LOGIN ---
if not st.session_state['autenticado']:
    st.markdown("<h2 style='text-align: center;'>🔒 Portal Ágape - Área Restrita</h2>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown("### Digite suas credenciais")
        campo_usuario = st.text_input("Usuário", key="login_user")
        campo_senha = st.text_input("Senha", type="password", key="login_pass")
        botao_entrar = st.button("Entrar no Sistema", use_container_width=True)
        
        if botao_entrar:
            if campo_usuario == "agape" and campo_senha == "12345":
                st.session_state['autenticado'] = True
                st.success("Acesso liberado!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# --- SISTEMA APÓS LOGIN (DASHBOARD) ---
else:
    # Menu lateral de navegação principal
    st.sidebar.title("⛪ Portal Ágape")
    st.sidebar.markdown(f"Bem-vindo, **{st.session_state.get('login_user', 'Membro')}**")
    
    # Seletor de abas do sistema
    aba_selecionada = st.sidebar.radio(
        "Navegar para:",
        ["📖 Bíblia Sagrada", "💬 Bate-Papo & Reuniões", "🙏 Sala de Oração Individual", "📻 Rádio Cristã"]
    )
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Fazer Logout", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

       # --- ABA 1: BÍBLIA SAGRADA ---
    if aba_selecionada == "📖 Bíblia Sagrada":
        st.title("📖 Bíblia Sagrada Completa")
        caminho_json = 'biblia.json'

        try:
            with open(caminho_json, 'r', encoding='utf-8-sig') as f:
                dados_biblia = json.load(f)

            if isinstance(dados_biblia, list):
                lista_livros = [livro['name'] for livro in dados_biblia]
                livro_sel = st.selectbox("Escolha o Livro:", lista_livros)
                
                dados_livro = next(item for item in dados_biblia if item["name"] == livro_sel)
                
                lista_capitulos = [f"Capítulo {i+1}" for i in range(len(dados_livro["chapters"]))]
                capitulo_sel = st.selectbox("Escolha o Capítulo:", lista_capitulos)
                idx_capitulo = lista_capitulos.index(capitulo_sel)
                
                versiculos = dados_livro["chapters"][idx_capitulo]
                
                st.markdown(f"### {livro_sel} - {capitulo_sel}")
                st.markdown("---")
                for idx, texto in enumerate(versiculos, start=1):
                    st.markdown(f"**{idx}** {texto}")
            else:
                st.error("O arquivo JSON não está no formato de lista esperado.")
        except FileNotFoundError:
            st.error("O arquivo 'biblia.json' não foi encontrado na pasta do projeto.")
        except Exception as e:
            st.error(f"Erro ao carregar os livros da Bíblia: {e}")


    # --- ABA 2: BATE-PAPO & VIDEOCONFERÊNCIA ---
    elif aba_selecionada == "💬 Bate-Papo & Reuniões":
        st.title("💬 Comunidade e Reuniões Ágape")
        
        col_video, col_chat = st.columns([2, 1])
        
        with col_video:
            st.subheader("📹 Sala de Transmissão / Videoconferência")
            st.caption("Ideal para cultos online, reuniões com o pastor e estudos bíblicos.")
            
            # Link público do Jitsi Meet embutido de forma segura
            sala_id = "PortalAgapeReuniaoGeral"
            jitsi_url = f"https://jit.si{sala_id}"
            
            # Incorpora a sala dentro do Streamlit via Iframe HTML
            st.components.v1.iframe(jitsi_url, height=550, scrolling=True)
            st.info("💡 Você também pode acessar diretamente ou convidar de fora usando o link público do [Jitsi Meet](https://jit.si).")

        with col_chat:
            st.subheader("💬 Mural de Conversas")
            
            # Caixa para digitar novas mensagens
            nova_msg = st.text_input("Digite sua mensagem para a igreja:", key="input_chat")
            if st.button("Enviar Mensagem", use_container_width=True):
                if nova_msg:
                    autor = st.session_state['login_user']
                    st.session_state['mensagens_chat'].append(f"**{autor}:** {nova_msg}")
                    st.rerun()
            
            # Exibição do histórico de mensagens enviadas nesta sessão
            st.markdown("---")
            for msg in reversed(st.session_state['mensagens_chat']):
                st.markdown(msg)

    # --- ABA 3: SALA DE ORAÇÃO INDIVIDUAL ---
    elif aba_selecionada == "🙏 Sala de Oração Individual":
        st.title("🙏 Sala de Oração Privada")
        st.markdown("Esta é uma sala reservada para atendimento pastoral individual ou orações particulares em vídeo.")
        
        # Gerador dinâmico de salas privadas com base no nome do usuário para não cruzar conexões
        usuario_atual = st.session_state.get('login_user', 'Membro')
        sala_privada_id = f"PortalAgapeOracao_{usuario_atual}"
        jitsi_privado_url = f"https://jit.si{sala_privada_id}"
        
        st.subheader("🎥 Sua Conexão Particular de Oração")
        st.caption("Passe o link da sua sala para o pastor entrar e orar com você de forma 100% isolada.")
        st.code(jitsi_privado_url, language="text")
        
        st.components.v1.iframe(jitsi_privado_url, height=500, scrolling=True)

           # --- ABA 4: RÁDIO CRISTÃ ---
    elif aba_selecionada == "📻 Rádio Cristã":
        st.title("📻 Rádio Web Ágape")
        st.markdown("Ouça louvores e programações edificantes direto do seu portal.")
        
        # Seleção de rádios usando players visuais e funcionais seguros
        radio_sel = st.selectbox(
            "Escolha uma estação de rádio:", 
            ["Rádio Melodia FM (Rio)", "Rádio Novo Tempo", "Rádio Gospel Adoração 24h"]
        )
        
        st.markdown(f"### Sintonizado: **{radio_sel}**")
        st.markdown("---")
        
        if radio_sel == "Rádio Melodia FM (Rio)":
            # Embutindo o player oficial que funciona direto sem travar o navegador
            st.components.v1.iframe("https://www.melodia.com.br/player/", height=180, scrolling=False)
            st.caption("📱 Toque no botão de 'Play' dentro da janela acima para ouvir a Melodia FM [Rádio Melodia](https://www.melodia.com.br/).")
            
        elif radio_sel == "Rádio Novo Tempo":
            # Player de transmissão oficial integrado da Novo Tempo
            st.components.v1.iframe("https://www.novotempo.com/radioaovivo/", height=400, scrolling=True)
            st.caption("📱 Navegue e ligue o áudio pelo painel oficial da [Rádio Novo Tempo](https://www.novotempo.com/radioaovivo/).")
            
        elif radio_sel == "Rádio Gospel Adoração 24h":
            # Player alternativo via rádio web aberta estável
            st.components.v1.iframe("https://vcfon.com", height=150, scrolling=False)
            st.caption("📱 Clique no Play caso o som não comece sozinho.")
