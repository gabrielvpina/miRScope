import argparse
import sys
import mirscope_analises as mca 

def main():
    # Cria o parser de argumentos da linha de comando
    parser = argparse.ArgumentParser(
        description="MIRSCOPE - Pipeline de Análise de miRNAs"
    )
    
    # Define o modo de análise (macro ou estrito)
    parser.add_argument(
        'modo', 
        type=str, 
        choices=['macro', 'estrito'], 
        help="Escolha o modo de análise: 'macro' (Modo 1) ou 'estrito' (Modo 2)"
    )
    
    # Define o cutoff como um argumento posicional opcional (nargs='?')
    parser.add_argument(
        'cutoff', 
        type=float, 
        nargs='?', 
        default=85.0, 
        help="Valor percentual do cutoff para o modo estrito (padrão: 85). Ignorado no modo macro."
    )
    
    # Caminho da pasta de dados (opcional, padrão: pasta atual '')
    parser.add_argument(
        '--dados', 
        type=str, 
        default='fasta_especies', 
        help="Caminho para a pasta com os arquivos FASTA (padrão: diretório atual 'fasta_especies')"
    )

    # Lê os argumentos fornecidos pelo usuário
    args = parser.parse_args()

    # Roteia para a função correta baseada no modo escolhido
    if args.modo == 'macro':
        # Executa a Análise do Tipo 1 (Conservação Ampla)
        mca.executar_modo_1(args.dados)
        
    elif args.modo == 'estrito':
        # Executa a Análise do Tipo 2 (Ortologia Estrita) com o cutoff definido
        mca.executar_modo_2(args.dados, args.cutoff)

if __name__ == "__main__":
    main()