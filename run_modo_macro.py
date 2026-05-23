import mirscope_core as mc
import pandas as pd

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 MIRSCOPE: MODO 1 (Conservação Ampla por Seed)")
    print("="*50 + "\n")
    
    caminho_dados = "fasta_especies" # Confirme se o caminho da sua pasta está correto
    
    print("⏳ Carregando dados...")
    todos_mirnas, lista_especies = mc.carregar_dados(caminho_dados)

    if todos_mirnas:
        print(f"✅ Foram carregadas {len(todos_mirnas)} sequências de {len(lista_especies)} espécies.\n")
        
        # 1. Agrupamento Primário
        dic_seed_especie = mc.agrupar_seed_especie(todos_mirnas)
        print(f"🧬 Famílias de Seed identificadas: {len(dic_seed_especie)}")
        
        # ==========================================
        # 💾 OUTPUT 1: EXCEL DOS MIRNAS (MACRO)
        # ==========================================
        mc.salvar_excel_modo_macro(todos_mirnas, "output_modo1_macro_detalhado.xlsx")

        # 2. Geração da Matriz
        print("⚙️ Gerando matriz booleana...")
        df_ortologia_seed = mc.gerar_dataframe_booleano_seed(dic_seed_especie)

        # 3. Geração do Gráfico
        if not df_ortologia_seed.empty:
            print("📈 Desenhando UpSet Plot...")
            mc.gerar_upset_plot(
                df_booleano=df_ortologia_seed, 
                caminho_saida="resultados_modo1_macro.png",
                titulo="Conservação Evolutiva por Família de Seed (Modo Macro)"
            )
        else:
            print("⚠️ Dados insuficientes para gerar o gráfico.")