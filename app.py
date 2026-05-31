import streamlit as st

# Configuração da página do Streamlit
st.set_page_config(page_title="Portal Ágape - Login", page_icon="📖", layout="wide")

# --- SISTEMA DE CONTROLE DE ACESSO (LOGIN) ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

def realizar_login(usuario, senha):
    # Altere aqui o usuário e a senha padrão do seu portal
    if usuario == "agape" and senha == "12345":
        st.session_state['autenticado'] = True
        st.success("Acesso liberado com sucesso!")
        st.rerun()
    else:
        st.error("Usuário ou senha incorretos. Tente novamente.")

# Se NÃO estiver logado, exibe apenas o formulário de login na tela
if not st.session_state['autenticado']:
    st.markdown("<h2 style='text-align: center;'>🔒 Portal Ágape - Área Restrita</h2>", unsafe_allow_html=True)
    
    # Centraliza o formulário de login na tela
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("formulario_login"):
            st.markdown("### Digite suas credenciais")
            campo_usuario = st.text_input("Usuário")
            campo_senha = st.text_input("Senha", type="password")
            botao_entrar = st.form_submit_button("Entrar no Sistema")
            
            if botao_entrar:
                realizar_login(campo_usuario, campo_senha)

# Se JÁ estiver logado, libera o acesso completo ao Portal da Bíblia
else:
    # Botão de Sair no menu lateral
    if st.sidebar.button("🚪 Sair / Fazer Logout"):
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
