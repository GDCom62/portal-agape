import streamlit as st
import json
import os

# Configuração da página do Streamlit
st.set_page_config(page_title="Bíblia Sagrada - Ágape", page_icon="📖", layout="wide")

st.title("📖 Aplicativo Bíblia Sagrada")
st.markdown("---")

caminho_arquivo = 'biblia.json'

# 1. Verifica se o arquivo existe
if not os.path.exists(caminho_arquivo):
    st.error(f"Erro: O arquivo '{caminho_arquivo}' não foi encontrado na pasta C:\\AGAPE.")
else:
    try:
        # 2. Carrega o arquivo JSON tratando os acentos corretamente
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados_biblia = json.load(f)

        # 3. CORREÇÃO DO ERRO: Valida se é uma lista e renderiza os dados
        if isinstance(dados_biblia, list):
            if len(dados_biblia) > 0:
                st.success(f"Bíblia carregada com sucesso! Total de registros encontrados: {len(dados_biblia)}")
                
                # Exemplo: Pega as chaves internas do primeiro dicionário da lista de forma segura
                primeiro_registro = dados_biblia[0]
                if isinstance(primeiro_registro, dict):
                    chaves_disponiveis = list(primeiro_registro.keys())
                    st.write(f"**Campos disponíveis no seu arquivo:** {chaves_disponiveis}")
                    
                    # Interface interativa básica para navegar pelos dados da lista
                    st.subheader("Navegador de Conteúdo")
                    indice = st.number_input("Escolha o índice do livro/versículo:", min_value=0, max_value=len(dados_biblia)-1, value=0)
                    
                    # Exibe o item selecionado de forma organizada na página web
                    st.json(dados_biblia[indice])
                else:
                    st.warning("Os itens dentro da lista do arquivo JSON não são estruturas de dados legíveis (dicionários).")
            else:
                st.warning("O arquivo 'biblia.json' contém uma lista, mas ela está totalmente vazia.")
        else:
            st.error("A estrutura do arquivo não é uma lista. Verifique a formatação do seu JSON.")

    except json.JSONDecodeError:
        st.error("Erro Crítico: O arquivo 'biblia.json' contém erros de digitação e não é um JSON válido.")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")
