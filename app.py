import json

try:
    with open('biblia.json', 'r', encoding='utf-8') as f:
        json.load(f)
    print("O arquivo JSON está perfeito! Sem erros estruturais.")
except json.JSONDecodeError as e:
    print("=== LOCALIZADOR DE ERRO NO JSON ===")
    print(f"Mensagem de erro: {e.msg}")
    print(f"Linha do erro: {e.lineno}")
    print(f"Coluna (caractere): {e.colno}")
    print(f"Posição total no arquivo: {e.pos}")
    print("\n--- Trecho aproximado do erro ---")
    
    # Abre o arquivo de novo para ler o trecho problemático
    with open('biblia.json', 'r', encoding='utf-8') as f:
        linhas = f.readlines()
        linha_erro = e.lineno - 1  # Índice do Python começa em 0
        
        # Mostra algumas linhas antes e a linha exata do erro
        inicio = max(0, linha_erro - 2)
        fim = min(len(linhas), linha_erro + 3)
        
        for i in range(inicio, fim):
            marcador = "-> " if i == linha_erro else "   "
            print(f"{marcador}Linha {i+1}: {linhas[i].rstrip()}")
