import subprocess
import tempfile
import os
import glob
import xlsxwriter
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
import numpy as np

# =============================================================================
# 1. LEITURA E PREPARAÇÃO DE DADOS
# =============================================================================

class miRNA:
    def __init__(self, id_mirna, especie, sequencia, arquivo_origem):
        self.id = id_mirna
        self.especie = especie
        self.sequencia = sequencia.strip().upper()
        self.arquivo_origem = arquivo_origem

def extrair_especie(nome_arquivo):
    base = os.path.splitext(nome_arquivo)[0] 
    partes = base.split('_')
    if len(partes) >= 3 and partes[0].lower() == 'mirna':
        return " ".join(partes[1:])
    return f"{base}"

def carregar_dados(pasta_fastas):
    extensoes = ["*.fasta", "*.fa"]
    arquivos = []
    for ext in extensoes:
        arquivos.extend(glob.glob(os.path.join(pasta_fastas, ext)))
    
    arquivos = sorted(list(set(arquivos)))
    if not arquivos:
        print(f"[ERRO] Nenhum arquivo encontrado na pasta '{pasta_fastas}'.")
        return [], []

    banco_mirnas = []
    especies_encontradas = set()

    for caminho_arquivo in arquivos:
        nome_arquivo = os.path.basename(caminho_arquivo)
        especie_atual = extrair_especie(nome_arquivo)
        especies_encontradas.add(especie_atual)
        
        with open(caminho_arquivo, 'r') as f:
            id_atual = None
            for linha in f:
                linha = linha.strip()
                if not linha: continue 
                if linha.startswith(">"):
                    id_atual = linha[1:].split()[0]
                else:
                    if id_atual and len(linha) >= 8:
                        banco_mirnas.append(miRNA(id_atual, especie_atual, linha, nome_arquivo))
                    id_atual = None 

    return banco_mirnas, sorted(list(especies_encontradas))

def agrupar_seed_especie(lista_mirnas):
    dic_seeds = {}
    for mirna in lista_mirnas:
        seed = mirna.sequencia[1:8]
        if seed not in dic_seeds: dic_seeds[seed] = []
        if mirna.especie not in dic_seeds[seed]: dic_seeds[seed].append(mirna.especie)
    return dic_seeds

def agrupar_por_seed(lista_mirnas):
    dic_seeds = {}
    for mirna in lista_mirnas:
        seed = mirna.sequencia[1:8]
        if seed not in dic_seeds: dic_seeds[seed] = []
        dic_seeds[seed].append({
            'id_original': mirna.id,
            'especie': mirna.especie,
            'sequencia': mirna.sequencia
        })
    return dic_seeds

def preparar_records_para_alinhamento(dic_seeds):
    dic_formatado = {}
    for seed, membros in dic_seeds.items():
        lista_records = []
        for dado in membros:
            especie_sem_espaco = dado['especie'].replace(" ", "_")
            id_composto = f"{dado['id_original']}|{especie_sem_espaco}"
            registro = SeqRecord(Seq(dado['sequencia']), id=id_composto, description="")
            lista_records.append(registro)
        dic_formatado[seed] = lista_records
    return dic_formatado

# =============================================================================
# 2. ALINHAMENTO (MAFFT) E COESÃO
# =============================================================================

def alinhar_com_ancora_glocal(records_da_seed, sequencia_seed):
    if len(records_da_seed) < 2: return records_da_seed

    ancora_a = SeqRecord(Seq(sequencia_seed), id="ANCORA_A", description="")
    ancora_b = SeqRecord(Seq(sequencia_seed), id="ANCORA_B", description="")
    temp_seed_path = None

    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta', delete=False) as temp_seed:
            SeqIO.write([ancora_a, ancora_b], temp_seed, 'fasta')
            temp_seed_path = temp_seed.name

        todos_os_records = [ancora_a, ancora_b] + records_da_seed
        fastas_str = "\n".join([f">{rec.id}\n{str(rec.seq)}" for rec in todos_os_records])

        comando = ['mafft', '--nuc', '--seed', temp_seed_path, '--genafpair', '--maxiterate', '1000', '-']
        processo = subprocess.Popen(comando, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = processo.communicate(input=fastas_str.encode())

        if processo.returncode != 0: raise RuntimeError(f"Erro MAFFT: {stderr.decode('utf8')}")

        alinhamento_bruto = list(SeqIO.parse(StringIO(stdout.decode('utf8')), 'fasta'))
        return [seq for seq in alinhamento_bruto if "ancora" not in seq.id.lower()]

    except Exception as erro:
        print(f"Falha ao processar: {erro}")
        return None
    finally:
        if temp_seed_path and os.path.exists(temp_seed_path): os.remove(temp_seed_path)

def calcular_identidade_alinhada(seq1_str, seq2_str):
    matches = 0
    tamanho_efetivo = 0
    for base1, base2 in zip(seq1_str, seq2_str):
        if base1 == '-' and base2 == '-': continue
        if base1 == base2: matches += 1
        tamanho_efetivo += 1
    return (matches / tamanho_efetivo) * 100.0 if tamanho_efetivo > 0 else 0.0

def separar_por_coesao_total(alinhamento_limpo, cutoff_percentual):
    if not alinhamento_limpo: return []
    grupos = [] 
    
    for registro_atual in alinhamento_limpo:
        alocado = False
        seq_str_atual = str(registro_atual.seq).lower()
        for grupo_index, grupo in enumerate(grupos):
            passou_em_todos = True
            for membro in grupo:
                seq_str_membro = str(membro.seq).lower()
                identidade = calcular_identidade_alinhada(seq_str_membro, seq_str_atual)
                if identidade < cutoff_percentual:
                    passou_em_todos = False
                    break 
            if passou_em_todos:
                grupos[grupo_index].append(registro_atual)
                alocado = True
                break 
        if not alocado: grupos.append([registro_atual])
    return grupos

# =============================================================================
# 3. EXPORTAÇÃO DE DADOS (EXCEL E FASTA)
# =============================================================================

def salvar_excel_modo_macro(lista_mirnas, caminho_saida):
    """Salva a informação bruta separada por Seed no Modo 1, com filtros e cores."""
    dados = []
    for m in lista_mirnas:
        dados.append({
            'Seed': m.sequencia[1:8],
            'Especie': m.especie,
            'ID_Original': m.id,
            'Sequencia': m.sequencia
        })
    df = pd.DataFrame(dados)
    
    # Conta espécies únicas por Seed e reorganiza as colunas
    if not df.empty:
        df['Qtd_Especies'] = df.groupby('Seed')['Especie'].transform('nunique')
        df = df[['Seed', 'Qtd_Especies', 'Especie', 'ID_Original', 'Sequencia']]
        df = df.sort_values(by=['Seed', 'Especie'])
    
    exportar_planilha_agrupada(df, caminho_saida, coluna_grupo='Seed')
    print(f"✅ Output Excel (Macro) guardado em: '{caminho_saida}'")

def salvar_alinhamentos_fasta(resultados_alinhados, caminho_saida):
    """Guarda todos os alinhamentos do MAFFT num ficheiro único de texto."""
    with open(caminho_saida, 'w') as f:
        for seed, records in resultados_alinhados.items():
            f.write(f"\n# ================= SEED: {seed} =================\n")
            for rec in records:
                f.write(f">{rec.id}\n{str(rec.seq)}\n")
    print(f"✅ Output Alinhamento (FASTA) guardado em: '{caminho_saida}'")

def salvar_excel_clusters_detalhados(dicionario_clusters, caminho_saida):
    """Salva a tabela completa com filtros e zebra colors por cluster."""
    dados = []
    for seed, clusters in dicionario_clusters.items():
        for idx, cluster in enumerate(clusters):
            cluster_id = f"{seed}_Clust_{idx + 1}"
            for rec in cluster:
                partes = rec.id.split('|')
                id_orig = partes[0]
                especie = partes[1].replace("_", " ") if len(partes) > 1 else "Desconhecida"
                dados.append({
                    'Seed': seed,
                    'Cluster_ID': cluster_id,
                    'Especie': especie,
                    'ID_Original': id_orig,
                    'Sequencia_Alinhada': str(rec.seq)
                })
    df = pd.DataFrame(dados)
    
    # Conta espécies únicas por Cluster e reorganiza as colunas
    if not df.empty:
        df['Qtd_Especies'] = df.groupby('Cluster_ID')['Especie'].transform('nunique')
        df = df[['Seed', 'Cluster_ID', 'Qtd_Especies', 'Especie', 'ID_Original', 'Sequencia_Alinhada']]
    
    exportar_planilha_agrupada(df, caminho_saida, coluna_grupo='Cluster_ID')
    print(f"✅ Output Excel (Clusters Detalhados) guardado em: '{caminho_saida}'")

# =============================================================================
# 4. MATRIZES BOOLEANAS E GRÁFICOS
# =============================================================================

def gerar_dataframe_booleano_seed(dicionario_bruto):
    dados_tabela = []
    todas_especies_encontradas = set()

    for seed, registros in dicionario_bruto.items():
        especies_na_seed = set()
        for registro in registros:
            especie = str(registro)
            especies_na_seed.add(especie)
            todas_especies_encontradas.add(especie)
        
        if especies_na_seed:
            linha = {"miRNA_ID": seed}
            for esp in especies_na_seed: linha[esp] = True
            dados_tabela.append(linha)

    df = pd.DataFrame(dados_tabela)
    if df.empty: return df

    df.set_index("miRNA_ID", inplace=True)
    for coluna in todas_especies_encontradas:
        if coluna not in df.columns: df[coluna] = False 
        df[coluna] = df[coluna].fillna(False).astype(bool)

    return df

def gerar_df_booleano_dos_clusters(dicionario_clusters):
    """Gera a matriz booleana lendo diretamente os clusters prontos."""
    dados_tabela = []
    todas_especies_encontradas = set()

    for seed, clusters in dicionario_clusters.items():
        for idx, cluster in enumerate(clusters):
            cluster_id = f"{seed}_Clust_{idx + 1}"
            especies_no_cluster = set()
            for rec in cluster:
                partes = rec.id.split('|')
                if len(partes) > 1:
                    especie = partes[1].replace("_", " ")
                    especies_no_cluster.add(especie)
                    todas_especies_encontradas.add(especie)
            
            if especies_no_cluster:
                linha = {"miRNA_ID": cluster_id}
                for esp in especies_no_cluster: linha[esp] = True
                dados_tabela.append(linha)

    df = pd.DataFrame(dados_tabela)
    if df.empty: return df

    df.set_index("miRNA_ID", inplace=True)
    for coluna in todas_especies_encontradas:
        if coluna not in df.columns: df[coluna] = False 
        df[coluna] = df[coluna].fillna(False).astype(bool)

    return df

def gerar_upset_plot(df_booleano, caminho_saida="resultados_mirscope_upset.png", titulo="Conservação Evolutiva de miRNAs"):
    """Gera um UpSet Plot responsivo 100% nativo."""
    if df_booleano.empty:
        print("[AVISO] O DataFrame está vazio. Nenhum gráfico gerado.")
        return
        
    lista_de_especies = df_booleano.columns.tolist()
    if len(lista_de_especies) < 2:
         print(f"[AVISO] Apenas a espécie '{lista_de_especies[0]}' formou clusters.")
         return

    df_agrupado = df_booleano.groupby(lista_de_especies).size()
    df_agrupado = df_agrupado[df_agrupado > 0].sort_values(ascending=False)

    num_intersecoes = len(df_agrupado)
    num_especies = len(lista_de_especies)

    largura_dinamica = max(10.0, num_intersecoes * 0.7) 
    altura_dinamica = max(6.0, (num_especies * 0.5) + 4.0)  

    fig = plt.figure(figsize=(largura_dinamica, altura_dinamica))
    gs = fig.add_gridspec(2, 1, height_ratios=[3, max(1, num_especies * 0.4)], hspace=0.05)

    ax_barras = fig.add_subplot(gs[0])
    ax_matriz = fig.add_subplot(gs[1], sharex=ax_barras)

    x_pos = np.arange(num_intersecoes)
    contagens = df_agrupado.values

    # BARRAS
    ax_barras.bar(x_pos, contagens, color='#404040', width=0.6, zorder=3)
    ax_barras.grid(axis='y', linestyle='--', alpha=0.3, zorder=0) 
    for i, count in enumerate(contagens):
        ax_barras.text(i, count + (max(contagens) * 0.02), str(count), ha='center', va='bottom', fontweight='bold', fontsize=10)

    ax_barras.set_title(titulo, fontsize=16, pad=20, fontweight='bold')
    ax_barras.set_ylabel("Tamanho da Interseção", fontsize=12)
    for spine in ['top', 'right', 'bottom']: ax_barras.spines[spine].set_visible(False)
    ax_barras.tick_params(axis='x', which='both', bottom=False, top=False, labelbottom=False)

    # MATRIZ
    lista_de_especies_rev = list(reversed(lista_de_especies))
    y_pos = np.arange(num_especies)
    ax_matriz.grid(axis='y', linestyle='-', color='whitesmoke', zorder=0)

    for x_indice, intersecao in enumerate(df_agrupado.index):
        bolinhas_y = [] 
        for y_indice, especie in enumerate(lista_de_especies_rev):
            idx_orig = lista_de_especies.index(especie)
            if intersecao[idx_orig]:
                ax_matriz.plot(x_indice, y_indice, marker='o', color='black', markersize=14, zorder=5)
                bolinhas_y.append(y_indice)
            else:
                ax_matriz.plot(x_indice, y_indice, marker='o', color='#E0E0E0', markersize=14, zorder=4)

        if len(bolinhas_y) > 1:
            ax_matriz.plot([x_indice, x_indice], [min(bolinhas_y), max(bolinhas_y)], color='black', lw=3.5, zorder=3)

    ax_matriz.set_yticks(y_pos)
    ax_matriz.set_yticklabels(lista_de_especies_rev, fontsize=12)
    ax_matriz.set_xticks([])
    for spine in ['top', 'right', 'bottom', 'left']: ax_matriz.spines[spine].set_visible(False)

    plt.margins(x=0.02) 
    plt.savefig(caminho_saida, bbox_inches='tight', dpi=300, facecolor='white')
    plt.close()
    
    print(f"✅ Gráfico guardado com sucesso em: '{caminho_saida}'")

def salvar_excel_formatado(df, caminho_saida, manter_index=False):
    """Salva um DataFrame ajustando larguras de coluna e estilos visuais."""
    
    # Se o DataFrame estiver vazio, usa o método padrão para evitar erros
    if df.empty:
        df.to_excel(caminho_saida, index=manter_index)
        return

    # Usa o xlsxwriter como motor para permitir formatação
    with pd.ExcelWriter(caminho_saida, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=manter_index, sheet_name='Resultados')
        
        workbook  = writer.book
        worksheet = writer.sheets['Resultados']
        
        # Formato do cabeçalho (negrito com fundo cinza)
        formato_cabecalho = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3', 
            'border': 1
        })
        
        # Trava a primeira linha para facilitar a rolagem
        worksheet.freeze_panes(1, 0)
        
        # Ajusta as colunas iterando pelos nomes (e considerando se há index)
        offset_coluna = 1 if manter_index else 0
        
        for i, col in enumerate(df.columns):
            # Descobre o maior tamanho: nome da coluna ou conteúdo
            tamanho_maximo = max(
                df[col].astype(str).map(len).max(),
                len(str(col))
            ) + 2
            
            # Limita a largura (ex: 60) para não estourar a tela em sequências longas
            largura = min(tamanho_maximo, 60)
            
            # Aplica a largura na coluna
            idx_coluna = i + offset_coluna
            worksheet.set_column(idx_coluna, idx_coluna, largura)
            
            # Aplica o estilo na célula do cabeçalho
            worksheet.write(0, idx_coluna, col, formato_cabecalho)

def exportar_planilha_agrupada(df, caminho_saida, coluna_grupo):
    """Salva o Excel com AutoFiltro e cores alternadas baseadas no grupo."""
    if df.empty:
        df.to_excel(caminho_saida, index=False)
        return

    with pd.ExcelWriter(caminho_saida, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('Resultados')
        
        # Paleta de cores e estilos
        formato_cabecalho = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
        formato_impar = workbook.add_format({'bg_color': '#FCE4D6', 'border': 1, 'border_color': '#E0E0E0'}) # Laranja pastel
        formato_par = workbook.add_format({'bg_color': '#FFFFFF', 'border': 1, 'border_color': '#E0E0E0'})   # Branco
        
        # 1. Escreve os cabeçalhos
        for col_num, col_name in enumerate(df.columns):
            worksheet.write(0, col_num, col_name, formato_cabecalho)
        
        idx_grupo = df.columns.get_loc(coluna_grupo)
        grupo_atual = None
        usar_cor_impar = False
        
        # 2. Escreve os dados linha por linha alternando cores
        for row_num, row_data in enumerate(df.values, start=1):
            valor_grupo = row_data[idx_grupo]
            
            # Se o grupo mudou em relação à linha anterior, inverte a cor
            if valor_grupo != grupo_atual:
                usar_cor_impar = not usar_cor_impar
                grupo_atual = valor_grupo
                
            formato_linha = formato_impar if usar_cor_impar else formato_par
            
            for col_num, cell_value in enumerate(row_data):
                worksheet.write(row_num, col_num, cell_value, formato_linha)
        
        # 3. Adiciona o AutoFiltro em todas as colunas
        max_row = len(df)
        max_col = len(df.columns) - 1
        worksheet.autofilter(0, 0, max_row, max_col)
        worksheet.freeze_panes(1, 0) # Trava o cabeçalho
        
        # 4. Ajusta larguras
        for i, col in enumerate(df.columns):
            tamanho_maximo = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
            worksheet.set_column(i, i, min(tamanho_maximo, 60))
