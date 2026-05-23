import time
import pandas as pd
import mirscope_core as mc

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 MIRSCOPE: MODO 2 (Ortologia Estrita por Coesão)")
    print("="*50 + "\n")
    
    caminho_dados = "fasta_especies" 
    cutoff_desejado = 85.0

    print("⏳ A carregar dados...")
    lista_mirnas, lista_especies = mc.carregar_dados(caminho_dados)

    if not lista_mirnas:
        exit()

    print(f"✅ Foram carregadas {len(lista_mirnas)} sequências.")
    
    # 1. Agrupamento e Preparação
    dicionario_bruto = mc.agrupar_por_seed(lista_mirnas)
    dicionario_formatado = mc.preparar_records_para_alinhamento(dicionario_bruto)
    print(f"🧬 Famílias de Seed para processar: {len(dicionario_formatado)}\n")

    # 2. Alinhamento MAFFT
    print("⚙️ A iniciar Rota de Alinhamento (MAFFT)...")
    inicio_mafft = time.perf_counter()
    resultados_alinhados = {}

    for seed, registros in dicionario_formatado.items():
        alinhamento = mc.alinhar_com_ancora_glocal(registros, seed)
        if alinhamento:
            resultados_alinhados[seed] = alinhamento

    print(f"⏱️ Alinhamentos concluídos em {(time.perf_counter() - inicio_mafft):.2f}s.\n")

    # ==========================================
    # 💾 OUTPUT 1: ALINHAMENTO BRUTO (FASTA)
    # ==========================================
    mc.salvar_alinhamentos_fasta(resultados_alinhados, "output_modo2_alinhamentos.fasta")

    # 3. Processamento de Coesão e Via Expressa
    print("\n📊 A executar algoritmo de coesão e unificação de dados...")
    
    dicionario_clusters_finais = {}

    # Rota Principal (Após Coesão)
    for seed, alinhamento in resultados_alinhados.items():
        clusters_da_seed = mc.separar_por_coesao_total(alinhamento, cutoff_desejado)
        dicionario_clusters_finais[seed] = clusters_da_seed

    # Via Expressa (Resgate de Únicas)
    qtd_resgatados = 0
    for seed, registros in dicionario_formatado.items():
        if len(registros) == 1:
            # Colocamos o registo único dentro de uma lista que simula um "Cluster"
            dicionario_clusters_finais[seed] = [registros]
            qtd_resgatados += 1
            
    if qtd_resgatados > 0:
        print(f"🚀 Resgatadas {qtd_resgatados} famílias exclusivas que pularam o alinhamento.")

    # ==========================================
    # 💾 OUTPUT 2: EXCEL APÓS CLUSTERIZAÇÃO (Detalhado)
    # ==========================================
    mc.salvar_excel_clusters_detalhados(dicionario_clusters_finais, "output_modo2_clusters_detalhados.xlsx")

    # 4. Geração da Matriz e do Gráfico
    print("\n⚙️ A gerar matriz booleana final...")
    df_ortologia = mc.gerar_df_booleano_dos_clusters(dicionario_clusters_finais)

    # ==========================================
    # 💾 OUTPUT 3: EXCEL DOS GRUPOS DO UPSETPLOT (Interseções)
    # ==========================================
    if not df_ortologia.empty:
        # Mantém o backup da matriz booleana original
        df_ortologia.to_excel("output_modo2_matriz_upsetplot.xlsx")
        print("✅ Output Excel (Matriz Booleana) guardado em: 'output_modo2_matriz_upsetplot.xlsx'")
        
        # --- LÓGICA NOVA: Gerar tabela legível das interseções ---
        lista_colunas_especies = df_ortologia.columns.tolist()
        dados_intersecoes = []
        
        # Agrupa os dados pelas combinações exatas de True/False
        for perfil_booleano, df_grupo in df_ortologia.groupby(lista_colunas_especies):
            
            # Descobre quais as espécies que são 'True' nesta combinação
            especies_presentes = [lista_colunas_especies[i] for i, presente in enumerate(perfil_booleano) if presente]
            
            if especies_presentes:
                nome_grupo = " + ".join(especies_presentes)
                lista_de_clusters = df_grupo.index.tolist()
                
                dados_intersecoes.append({
                    "Interseção (Espécies)": nome_grupo,
                    "Total de Clusters": len(lista_de_clusters),
                    "Clusters Pertencentes (miRNAs)": ", ".join(lista_de_clusters)
                })
                
        # Converte para DataFrame e ordena do maior grupo para o menor (igual às barras do gráfico)
        df_intersecoes = pd.DataFrame(dados_intersecoes).sort_values(by="Total de Clusters", ascending=False)
        df_intersecoes.to_excel("output_modo2_grupos_intersecoes.xlsx", index=False)
        
        print("✅ Output Excel (Grupos Legíveis do Gráfico) guardado em: 'output_modo2_grupos_intersecoes.xlsx'")
        
        # ---------------------------------------------------------
        
        print("\n📈 A desenhar UpSet Plot...")
        mc.gerar_upset_plot(
            df_booleano=df_ortologia, 
            caminho_saida="output_modo2_estrito_upset.png",
            titulo=f"Ortologia de miRNAs - Coesão Total (Cutoff: {cutoff_desejado}%)"
        )
    else:
        print("⚠️ Dados insuficientes para gerar o gráfico e matriz.")