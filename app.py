import streamlit as st

# Configuração da página do Streamlit
st.set_page_config(page_title="Portal Ágape - Login", page_icon="📖", layout="wide")

# Inicializa o estado de autenticação de forma segura
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# --- TELA DE LOGIN ---
if not st.session_state['autenticado']:
    st.markdown("<h2 style='text-align: center;'>🔒 Portal Ágape - Área Restrita</h2>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Centraliza o formulário de login usando colunas
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        # Usamos uma caixa visual limpa em vez do elemento "st.form" clássico para evitar travamentos de envio
        st.markdown("### Digite suas credenciais")
        campo_usuario = st.text_input("Usuário", key="login_user")
        campo_senha = st.text_input("Senha", type="password", key="login_pass")
        botao_entrar = st.button("Entrar no Sistema", use_container_width=True)
        
        if botao_entrar:
            # Defina aqui o seu usuário e senha de acesso
            if campo_usuario == "agape" and campo_senha == "12345":
                st.session_state['autenticado'] = True
                st.success("Acesso liberado com sucesso!")
                st.rerun() # Agora executado com segurança fora de um bloco de formulário estático
            else:
                st.error("Usuário ou senha incorretos. Tente novamente.")

# --- TELA DO SISTEMA DA BÍBLIA (SÓ APARECE SE ESTIVER LOGADO) ---
else:
    # Botão de Sair posicionado no topo do menu lateral para fácil acesso
    if st.sidebar.button("🚪 Sair / Fazer Logout", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

    st.title("📖 Portal Ágape - Bíblia Sagrada")
    st.markdown("---")

    # Base de dados estruturada diretamente no código
    BIBLIA_DADOS = {
        "Antigo Testamento": {
            "Gênesis": {
                "Capítulo 1": [
                    "No princípio, criou Deus os céus e a terra.",
                    "E a terra era sem forma e vazia; e havia trevas sobre a face do abismo; e o Espírito de Deus se movia sobre a face das águas.",
                    "E disse Deus: Haja luz. E houve luz.",
                    "E viu Deus que era boa a luz; e fez Deus separação entre a luz e as trevas."
                ]
            }
        },
        "Novo Testamento": {
            "João": {
                "Capítulo 1": [
                    "No princípio era o Verbo, e o Verbo estava com Deus, e o Verbo era Deus.",
                    "Ele estava no princípio com Deus.",
                    "Todas as coisas foram feitas por ele, e sem ele nada do que foi feito se fez.",
                    "Nele estava a vida, e a vida era a luz dos homens."
                ]
            }
        }
    }

    # --- INTERFACE VISUAL DA BÍBLIA ---
    st.sidebar.markdown("### 🔍 Navegação")
    testamento_selecionado = st.sidebar.selectbox("Selecione o Testamento", list(BIBLIA_DADOS.keys()))

    livros_disponiveis = list(BIBLIA_DADOS[testamento_selecionado].keys())
    livro_selecionado = st.sidebar.selectbox("Selecione o Livro", livros_disponiveis)

    capitulos_disponiveis = list(BIBLIA_DADOS[testamento_selecionado][livro_selecionado].keys())
    capitulo_selecionado = st.sidebar.selectbox("Selecione o Capítulo", capitulos_disponiveis)

    # Exibição dos Versículos
    st.subheader(f"📖 {livro_selecionado} - {capitulo_selecionado}")
    st.markdown("---")

    versiculos = BIBLIA_DADOS[testamento_selecionado][livro_selecionado][capitulo_selecionado]

    for indice, texto in enumerate(versiculos, start=1):
        st.markdown(f"**{indice}** {texto}")
