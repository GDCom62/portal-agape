import json
import os

def carregar_e_processar_biblia():
    caminho_arquivo = 'biblia.json'
    
    # Verifica se o arquivo realmente existe no diretório
    if not os.path.exists(caminho_arquivo):
        print(f"Erro: O arquivo '{caminho_arquivo}' não foi encontrado.")
        return

    try:
        # Abre o arquivo tratando a codificação para evitar erros com acentos
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados_biblia = json.load(f)
        
        print("--- Processando dados da Bíblia (Opção 1) ---\n")
        
        # Como dados_biblia é uma lista, fazemos o loop diretamente nela
        for indice, item in enumerate(dados_biblia):
            # Verificamos se o item de dentro da lista é um dicionário antes de ler suas chaves
            if isinstance(item, dict):
                print(f"Item [{indice}] extraído com sucesso!")
                print(f"Campos disponíveis neste item: {list(item.keys())}")
                
                # Exemplo de como acessar os dados (ajuste os nomes 'nome' ou 'titulo' conforme seu JSON)
                # nome_livro = item.get('nome') or item.get('titulo') or "Desconhecido"
                # print(f"Conteúdo: {nome_livro}")
                print("-" * 40)
            else:
                print(f"O item no índice {indice} não é um dicionário, é um: {type(item)}")

    except json.JSONDecodeError:
        print("Erro: O arquivo 'biblia.json' não está em um formato JSON válido.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == '__main__':
    carregar_e_processar_biblia()
