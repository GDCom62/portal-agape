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

    st.title("📖 Portal Ágape - Bíblia Sagrada")
    st.markdown("---")

    caminho_json = 'biblia.json'

    # --- SISTEMA DE AUTOREPARAÇÃO DO ARQUIVO JSON ---
    criar_novo = False
    if not os.path.exists(caminho_json) or os.path.getsize(caminho_json) == 0:
        criar_novo = True
    else:
        try:
            with open(caminho_json, 'r', encoding='utf-8') as f:
                json.load(f)
        except json.JSONDecodeError:
            criar_novo = True

    if criar_novo:
        dados_padrao = {
            "Gênesis": {
                "Capítulo 1": [
                    "No princípio, criou Deus os céus e a terra.",
                    "E a terra era sem forma e vazia; e havia trevas sobre a face do abismo; e o Espírito de Deus se movia sobre a face das águas.",
                    "E disse Deus: Haja luz. E houve luz."
                ],
                "Capítulo 2": [
                    "Assim os céus, a terra e todo o seu exército foram acabados.",
                    "E havendo Deus acabado no dia sétimo a sua obra, que tinha feito, descansou."
                ]
            },
            "Êxodo": {
                "Capítulo 1": [
                    "Estes pois são os nomes dos filhos de Israel, que entraram no Egito com Jacó."
                ]
            }
        }
        with open(caminho_json, 'w', encoding='utf-8') as f:
            json.dump(dados_padrao, f, indent=4, ensure_ascii=False)
        st.sidebar.info("Aviso: 'biblia.json' padrão criado!")

    # --- LEITURA E RENDERIZAÇÃO DOS DADOS ---
    try:
        with open(caminho_json, 'r', encoding='utf-8') as f:
            dados_biblia = json.load(f)

        if isinstance(dados_biblia, dict):
            st.sidebar.markdown("### 🔍 Navegação")
            
            # 1. Seleciona o Livro
            lista_livros = list(dados_biblia.keys())
            livro_sel = st.sidebar.selectbox("Escolha o Livro:", lista_livros)
            
            # 2. Seleciona o Capítulo baseado no Livro escolhido
            conteudo_livro = dados_biblia[livro_sel]
            
            # Correção para caso o formato do JSON externo seja uma lista de capítulos em vez de dicionário
            if isinstance(conteudo_livro, list):
                lista_capitulos = [f"Capítulo {i+1}" for i in range(len(conteudo_livro))]
                capitulo_sel = st.sidebar.selectbox("Escolha o Capítulo:", lista_capitulos)
                # Extrai o índice numérico do capítulo
                idx_capitulo = lista_capitulos.index(capitulo_sel)
                versiculos = conteudo_livro[idx_capitulo]
            else:
                lista_capitulos = list(conteudo_livro.keys())
                capitulo_sel = st.sidebar.selectbox("Escolha o Capítulo:", lista_capitulos)
                versiculos = conteudo_livro[capitulo_sel]
            
            # Exibe na tela principal
            st.subheader(f"📖 {livro_sel} - {capitulo_sel}")
            st.markdown("---")
            
            # Renderização flexível de versículos
            if isinstance(versiculos, list):
                for idx, texto in enumerate(versiculos, start=1):
                    st.markdown(f"**{idx}** {texto}")
            elif isinstance(versiculos, dict):
                for v_num, v_texto in versiculos.items():
                    st.markdown(f"**{v_num}** {v_texto}")
            else:
                st.markdown(str(versiculos))
        else:
            st.error("A estrutura dentro do 'biblia.json' não está no formato esperado.")

    except Exception as e:
        st.error(f"Erro crítico ao processar a Bíblia: {e}")
