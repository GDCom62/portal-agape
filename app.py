import streamlit as st

# Configuração da página do Streamlit
st.set_page_config(page_title="Bíblia Sagrada - Portal Ágape", page_icon="📖", layout="wide")

st.title("📖 Portal Ágape - Bíblia Sagrada")
st.markdown("---")

# Base de dados estruturada diretamente no código para evitar erros de leitura de arquivos externos
# Você pode expandir este dicionário adicionando mais capítulos e livros seguindo o mesmo padrão!
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

# --- INTERFACE VISUAL NO NAVEGADOR ---

# 1. Seleção do Testamento
testamento_selecionado = st.sidebar.selectbox("Selecione o Testamento", list(BIBLIA_DADOS.keys()))

# 2. Seleção do Livro (Filtra baseado no Testamento escolhido)
livros_disponiveis = list(BIBLIA_DADOS[testamento_selecionado].keys())
livro_selecionado = st.sidebar.selectbox("Selecione o Livro", livros_disponiveis)

# 3. Seleção do Capítulo (Filtra baseado no Livro escolhido)
capitulos_disponiveis = list(BIBLIA_DADOS[testamento_selecionado][livro_selecionado].keys())
capitulo_selecionado = st.sidebar.selectbox("Selecione o Capítulo", capitulos_disponiveis)

# Exibição dos Versículos na Tela Principal
st.subheader(f"📖 {livro_selecionado} - {capitulo_selecionado}")
st.markdown(f"*Tradução estruturada para o Portal Ágape*")
st.markdown("---")

versiculos = BIBLIA_DADOS[testamento_selecionado][livro_selecionado][capitulo_selecionado]

for indice, texto in enumerate(versiculos, start=1):
    # Renderiza cada versículo elegantemente em formato de bloco de leitura
    st.markdown(f"**{indice}** {texto}")
