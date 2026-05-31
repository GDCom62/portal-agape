import os
import sys

def diagnostico_imediato():
    caminho_arquivo = 'biblia.json'
    
    # 1. Forçar print imediato para testar o terminal
    print("=== INICIANDO O SCRIPT APP.PY ===", flush=True)
    
    # 2. Verificar se o arquivo existe e o tamanho dele
    if not os.path.exists(caminho_arquivo):
        print(f"ERRO CRÍTICO: O arquivo '{caminho_arquivo}' NÃO está na mesma pasta que o app.py!", flush=True)
        return
        
    tamanho_bytes = os.path.getsize(caminho_arquivo)
    tamanho_mb = tamanho_bytes / (1024 * 1024)
    print(f"Arquivo encontrado! Tamanho: {tamanho_mb:.2f} MB", flush=True)
    
    if tamanho_bytes == 0:
        print("AVISO: O seu arquivo 'biblia.json' está totalmente VAZIO (0 bytes).", flush=True)
        return

    # 3. Ler apenas as primeiras 10 linhas para descobrir o formato real sem travar a memória
    print("\n--- LENDO AS PRIMEIRAS LINHAS DO ARQUIVO ---", flush=True)
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            for i in range(15):
                linha = f.readline()
                if not linha:
                    break
                # Remove espaços em branco nas pontas e exibe
                print(f"Linha {i+1}: {linha.strip()}", flush=True)
    except Exception as e:
        print(f"Erro ao tentar ler o arquivo texto: {e}", flush=True)
        
    print("\n=== FIM DO DIAGNÓSTICO ===", flush=True)

if __name__ == '__main__':
    diagnostico_imediato()
