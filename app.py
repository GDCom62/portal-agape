import streamlit as st
import json
import os

# Configuração da página do Streamlit
st.set_page_config(page_title="Portal Ágape", page_icon="📖", layout="wide")

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

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

# --- TELA DA BÍBLIA (APÓS LOGIN CORRETO) ---
else:
    if st.sidebar.button("🚪 Sair / Fazer Logout", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

    st.title("📖 Portal Ágape - Bíblia Sagrada Dinâmica")
    st.markdown("---")

    caminho_json = 'biblia.json'

    if not os.path.exists(caminho_json):
        st.error(f"Arquivo '{caminho_json}' não encontrado na pasta raiz.")
    else:
        try:
            with open(caminho_json, 'r', encoding='utf-8') as f:
                dados_biblia = json.load(f)

            # CASO 1: O arquivo JSON corrigido é um Dicionário de Livros estruturado
            if isinstance(dados_biblia, dict):
                st.sidebar.markdown("### 🔍 Navegação")
                
                # Se o JSON tiver divisões de Testamentos no topo
                primeira_chave = list(dados_biblia.keys())[0]
                if isinstance(dados_biblia[primeira_chave], dict):
                    lista_livros = list(dados_biblia.keys())
                    livro_sel = st.sidebar.selectbox("Escolha o Livro/Categoria:", lista_livros)
                    
                    conteudo_livro = dados_biblia[livro_sel]
                    if isinstance(conteudo_livro, dict):
                        capitulo_sel = st.sidebar.selectbox("Escolha o Capítulo:", list(conteudo_livro.keys()))
                        versiculos = conteudo_livro[capitulo_sel]
                        
                        st.subheader(f"📖 {livro_sel} - {capitulo_sel}")
                        st.markdown("---")
                        
                        if isinstance(versiculos, list):
                            for idx, texto in enumerate(versiculos, start=1):
                                st.markdown(f"**{idx}** {texto}")
                        elif isinstance(versiculos, dict):
                            for v_num, v_texto in versiculos.items():
                                st.markdown(f"**{v_num}** {v_texto}")
                else:
                    st.write("Dados mapeados em formato alternativo:")
                    st.json(dados_biblia)

            # CASO 2: O arquivo JSON corrigido é uma Lista Linear de registros/versículos
            elif isinstance(dados_biblia, list):
                st.sidebar.markdown("### 🔍 Registro Manual")
                st.success(f"Dicionário em lista carregado! Total de registros: {len(dados_biblia)}")
                
                # Cria um seletor numérico para navegar de forma limpa pelos elementos da lista
                index_sel = st.number_input("Visualizar Registro Nº:", min_value=0, max_value=len(dados_biblia)-1, value=0)
                st.markdown("---")
                st.write("### Conteúdo do Registro Selecionado:")
                st.json(dados_biblia[index_sel])

        except Exception as e:
            st.error(f"Não foi possível processar o arquivo corrigido: {e}")

