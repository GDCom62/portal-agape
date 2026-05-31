import json
import os

def inspecionar_primeiro_item():
    caminho_arquivo = 'biblia.json'
    
    # Verifica se o arquivo realmente existe no diretório
    if not os.path.exists(caminho_arquivo):
        print(f"Erro: O arquivo '{caminho_arquivo}' não foi encontrado.")
        return

    try:
        # Abre o arquivo tratando a codificação para evitar erros com acentos
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados_biblia = json.load(f)
        
        print("--- Inspecionando o primeiro item (Opção 2) ---\n")
        
        # Verifica se a lista não está vazia antes de acessar o índice 0
        if len(dados_biblia) > 0:
            primeiro_item = dados_biblia[0]
            
            # Agora que pegamos o elemento de dentro da lista, ele deve ser um dicionário
            if isinstance(primeiro_item, dict):
                chaves = primeiro_item.keys()
                print("Sucesso! O primeiro item é um dicionário.")
                print(f"As chaves encontradas foram: {list(chaves)}")
                print("\nExemplo do conteúdo do primeiro item:")
                print(json.dumps(primeiro_item, indent=4, ensure_ascii=False)[:500] + "... (resumido)")
            else:
                print(f"O primeiro item da lista não possui chaves porque ele é do tipo: {type(primeiro_item)}")
        else:
            print("A lista dentro do arquivo 'biblia.json' está vazia.")

    except json.JSONDecodeError:
        print("Erro: O arquivo 'biblia.json' não está em um formato JSON válido.")
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")

if __name__ == '__main__':
    inspecionar_primeiro_item()
