import time
import pandas as pd
import mirscope_core as mc

def executar_modo_1(caminho_dados):
    print("\n" + "="*50)
    print("🚀 MIRSCOPE: MODO 1 (Conservação Ampla por Seed)")
    print("="*50 + "\n")

    inicio = time.perf_counter()
    
    print("⏳ Carregando dados...")
    todos_mirnas, lista_especies = mc.carregar_dados(caminho_dados)

    if todos_mirnas:
        print(f"✅ Foram carregadas {len(todos_mirnas)} sequências de {len(lista_especies)} espécies.\n")
        
        # 1. Agrupamento Primário
        dic_seed_especie = mc.agrupar_seed_especie(todos_mirnas)
        print(f"🧬 Famílias de Seed identificadas: {len(dic_seed_especie)}")
        
        # 2. OUTPUT 1: EXCEL DOS MIRNAS (MACRO)
        mc.salvar_excel_modo_macro(todos_mirnas, "output_modo1_macro_detalhado.xlsx")

        # 3. Geração da Matriz
        print("⚙️ Gerando matriz booleana...")
        df_ortologia_seed = mc.gerar_dataframe_booleano_seed(dic_seed_especie)

        # 4. Geração do Gráfico
        if not df_ortologia_seed.empty:
            print("📈 Desenhando UpSet Plot...")
            mc.gerar_upset_plot(
                df_booleano=df_ortologia_seed, 
                caminho_saida="resultados_modo1_macro.png",
                titulo="Conservação Evolutiva por Família de Seed (Modo Macro)"
            )
            print(f"⏱️ Análise executada em {(time.perf_counter() - inicio):.2f}s.\n")
        else:
            print("⚠️ Dados insuficientes para gerar o gráfico.")

def executar_modo_2(caminho_dados, cutoff_desejado):
    print("\n" + "="*50)
    print("🚀 MIRSCOPE: MODO 2 (Ortologia Estrita por Coesão)")
    print("="*50 + "\n")
    
    print("⏳ Carregando dados...")
    lista_mirnas, lista_especies = mc.carregar_dados(caminho_dados)

    if not lista_mirnas:
        return

    print(f"✅ Foram carregadas {len(lista_mirnas)} sequências.")
    
    # 1. Agrupamento e Preparação
    dicionario_bruto = mc.agrupar_por_seed(lista_mirnas)
    dicionario_formatado = mc.preparar_records_para_alinhamento(dicionario_bruto)
    print(f"🧬 Famílias de Seed para processar: {len(dicionario_formatado)}\n")

    # 2. Alinhamento MAFFT
    print("⚙️ Iniciando Rota de Alinhamento (MAFFT)...")
    inicio_mafft = time.perf_counter()
    resultados_alinhados = {}

    for seed, registros in dicionario_formatado.items():
        alinhamento = mc.alinhar_com_ancora_glocal(registros, seed)
        if alinhamento:
            resultados_alinhados[seed] = alinhamento

    print(f"⏱️ Alinhamentos concluídos em {(time.perf_counter() - inicio_mafft):.2f}s.\n")

    # 3. OUTPUT 1: ALINHAMENTO BRUTO (FASTA)
    mc.salvar_alinhamentos_fasta(resultados_alinhados, "output_modo2_alinhamentos.fasta")

    # 4. Processamento de Coesão All-Against-All e Via Expressa
    print("\n📊 Executando algoritmo de coesão e unificação de dados...")
    inicio_coesao = time.perf_counter()
    dicionario_clusters_finais = {}

    for seed, alinhamento in resultados_alinhados.items():
        clusters_da_seed = mc.separar_por_coesao_total(alinhamento, cutoff_desejado)
        dicionario_clusters_finais[seed] = clusters_da_seed

    qtd_resgatados = 0
    for seed, registros in dicionario_formatado.items():
        if len(registros) == 1:
            dicionario_clusters_finais[seed] = [registros]
            qtd_resgatados += 1
            
    if qtd_resgatados > 0:
        print(f"🚀 Resgatadas {qtd_resgatados} famílias exclusivas que pularam o alinhamento.")

    # 5. OUTPUT 2: EXCEL APÓS CLUSTERIZAÇÃO
    inicio_output = time.perf_counter()
    print(f"⏱️ Agrupamento concluído em {(inicio_output - inicio_coesao):.2f}s.\n")
    mc.salvar_excel_clusters_detalhados(dicionario_clusters_finais, "output_modo2_clusters_detalhados.xlsx")

    # 6. Geração da Matriz e do Gráfico
    print("\n⚙️ Gerando matriz booleana final...")
    df_ortologia = mc.gerar_df_booleano_dos_clusters(dicionario_clusters_finais)

    if not df_ortologia.empty:
        mc.salvar_excel_formatado(df_ortologia, "output_modo2_matriz_upsetplot.xlsx", manter_index=True)
        print("✅ Output Excel (Matriz Booleana) guardado.")
        
        lista_colunas_especies = df_ortologia.columns.tolist()
        dados_intersecoes = []
        
        for perfil_booleano, df_grupo in df_ortologia.groupby(lista_colunas_especies):
            especies_presentes = [lista_colunas_especies[i] for i, presente in enumerate(perfil_booleano) if presente]
            if especies_presentes:
                nome_grupo = " + ".join(especies_presentes)
                lista_de_clusters = df_grupo.index.tolist()
                dados_intersecoes.append({
                    "Interseção (Espécies)": nome_grupo,
                    "Total de Clusters": len(lista_de_clusters),
                    "Clusters Pertencentes (miRNAs)": ", ".join(lista_de_clusters)
                })
                
        df_intersecoes = pd.DataFrame(dados_intersecoes).sort_values(by="Total de Clusters", ascending=False)
        mc.salvar_excel_formatado(df_intersecoes, "output_modo2_grupos_intersecoes.xlsx")
        print("✅ Output Excel (Grupos Legíveis do Gráfico) guardado.")
        
        print("\n📈 Desenhando UpSet Plot...")
        mc.gerar_upset_plot(
            df_booleano=df_ortologia, 
            caminho_saida="output_modo2_estrito_upset.png",
            titulo=f"Ortologia de miRNAs - Coesão Total (Cutoff: {cutoff_desejado}%)"
        )
        print(f"⏱️ Resultados gerados em {(time.perf_counter()  - inicio_output):.2f}s.\n")
        print(f"⏱️ Tudo foi concluído em {(time.perf_counter() - inicio_mafft):.2f}s.\n")
    else:
        print("⚠️ Dados insuficientes para gerar o gráfico e matriz.")