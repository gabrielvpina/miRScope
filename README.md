# 🧬 MIRSCOPE

MIRSCOPE é uma ferramenta automatizada desenvolvida em Python para análise comparativa e conservação evolutiva de microRNAs.

A ferramenta utiliza uma abordagem centrada na região seed (nucleotídeos 2-8) e oferece duas vias analíticas para os pesquisadores: um Modo Macro (para conservação ampla da família) e um Modo Estrito (com motor de alinhamento para ortólogos reais, resgatando exclusividades biológicas).

## 🛠️ Pré-requisitos e Compatibilidade

O MIRSCOPE foi desenhado para correr em sistemas Linux e macOS (ou Windows via WSL).
Para utilizar a ferramenta, o seu sistema precisa ter:

Python 3.8+

MAFFT (Software de alinhamento múltiplo)

### Como instalar o MAFFT

O motor de coesão do MIRSCOPE exige que o MAFFT esteja instalado e acessível no seu terminal (PATH).

#### - Ubuntu/Debian (Linux):

sudo apt update
sudo apt install mafft


#### - macOS (via Homebrew):

brew install mafft


#### - Via Conda (Qualquer SO):

conda install -c bioconda mafft


## 📥 Instalação do MIRSCOPE

Faça o clone deste repositório e instale as dependências do Python:

## 1. Clonar o repositório
git clone [https://github.com/SEU_USUARIO/mirscope.git](https://github.com/TatyanaChagas/mirscope.git)
cd mirscope

## 2. Instalar as bibliotecas Python necessárias
pip install -r requirements.txt

## 3. Utilização da ferramenta

🚀 Como Usar

O MIRSCOPE exige que os seus arquivos de entrada estejam em uma pasta chamada fasta_especies/.
Atualmente, esta pasta no repositório já contém os arquivos de todos os miRNAs disponíveis no miRBase (maio/2026).

  ⚠️ Preparando os seus dados para análise:

  - Adicionar: Você pode adicionar os seus próprios arquivos de interesse nesta pasta. Cada arquivo FASTA deve representar uma única espécie e conter todas as sequências de miRNAs pertencentes a ela.
  
  - Regra de Ouro (Nomenclatura): O nome dos arquivos .fasta deve obrigatoriamente seguir o formato de taxonomia para que o MIRSCOPE reconheça a espécie. Ex: mirna_Homo_sapiens.fasta ou mirna_Mus_musculus.fa.
  
  - Filtrar (Altamente Recomendado): Se você não tem interesse em realizar a sua análise contra todo o banco do miRBase, exclua os arquivos das espécies que não vai usar. Manter na pasta apenas as espécies do seu estudo deixará o processamento muito mais rápido e gerará um UpSet Plot muito mais focado e limpo.

A ferramenta possui dois executáveis independentes:

### MODO 1: Conservação Ampla (Macro)

Agrupa miRNAs partindo exclusivamente da conservação da região seed, saltando o alinhamento completo. Ideal para respostas rápidas sobre a disseminação de grandes famílias.

python run_modo_macro.py


### MODO 2: Ortologia Estrita por Coesão

Utiliza o MAFFT para alinhar as famílias de seed e aplica um rigoroso cutoff de 85% de identidade base a base para isolar verdadeiros ortólogos maduros, garantindo simultaneamente o resgate de miRNAs espécie-específicos.

💡 Personalizando o Limite de Identidade (Cutoff):
O valor padrão de similaridade da ferramenta é de 85%. Se a sua pesquisa exigir um rigor maior (ex: 95%) ou for mais flexível, você pode alterar esse valor facilmente. Basta abrir o arquivo run_modo_estrito.py em qualquer editor de texto e alterar o valor numérico da variável cutoff_desejado = 85.0 localizada no início do código.

python run_modo_estrito.py


## 📊 Outputs (Resultados)

Após a execução, o MIRSCOPE gera relatórios padronizados e prontos para publicação na mesma pasta:

output_modoX_upset.png: Gráfico responsivo nativo mostrando as interseções evolutivas (UpSet Plot).

output_modo2_alinhamentos.fasta: Ficheiro de texto contendo todos os alinhamentos gerados pelo MAFFT.

output_modo2_clusters_detalhados.xlsx: Tabela detalhada indicando exatamente a que cluster evolutivo pertence cada miRNA de cada espécie.

output_modo2_grupos_intersecoes.xlsx: Tabela de leitura fácil detalhando os grupos biológicos (ex: Homo sapiens + Mus musculus) e a lista de miRNAs ortólogos partilhados.

## ✍️ Autoria e Citação

Desenvolvido por Tatyana Chagas Moura / BiovirLab
