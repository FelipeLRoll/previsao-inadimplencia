def gerar_previsoes():

    #imports
    import warnings
    import pandas as pd
    import pypyodbc as sql
    import os
    import joblib
    from dotenv import load_dotenv
    from sklearn.preprocessing import LabelEncoder, MinMaxScaler

    warnings.filterwarnings("ignore") 

    #carregando o modelo
    xg = joblib.load("modelo/modelo.pk")
    print("Pacotes Carregados...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")
    #carregando as variaveis de ambiente
    load_dotenv()

    USUARIO = os.environ.get("USUARIO")
    SENHA = os.environ.get("SENHA")
    HOST = os.environ.get("HOST")
    DATABASE = os.environ.get("DATABASE")
    print("Variáveis Carregadas...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #importar os dados do SQL
    connection_string = "Driver={SQL Server};Server=" + HOST + ";Database=" + DATABASE + ";UID=" + USUARIO + ";PWD=" + SENHA + ";"
    conexao = sql.connect(connection_string)
    cursor = conexao.cursor()
    cursor.execute("TRUNCATE TABLE RESULTADOS_INTERMEDIARIO")
    conexao.commit()
    conexao.close()
    print("Gerando Previsões...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    conexao = sql.connect(connection_string)
    df_original = pd.read_sql_query("SELECT * FROM EXTRACAO_DADOS_SISTEMA", conexao)
    conexao.close()
    print("Conectando com a tabela EXTRACAO_DADOS_SISTEMA...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #otimizando a coluna Data_Contratacao para datetime64[ns]                  
    df_original["data_assinatura_contrato"] = pd.to_datetime(df_original["data_assinatura_contrato"])
    #otimizando colunas categoricas
    colunas_categoricas = ["tipo_financiamento", "cidade_cliente", "estado_cliente", "inadimplente_cobranca"]

    for coluna in colunas_categoricas:
        df_original[coluna] = df_original[coluna].astype("category")

    #otimizando colunas numericas
    colunas_float = df_original.select_dtypes(include="float64").columns
    colunas_int = df_original.select_dtypes(include="int64").columns

    df_original[colunas_float] = df_original[colunas_float].apply(pd.to_numeric, downcast="float")
    df_original[colunas_int] = df_original[colunas_int].apply(pd.to_numeric, downcast="integer")
    print("Colunas otimizadas...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #removendo linhas duplicadas 
    df_original.drop_duplicates()      
    print("Linhas duplicadas removidas...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #excluindo linhas com valores nulos
    df_original.dropna(inplace=True)  
    print("Valores nulos removidos...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #eliminando colunas inúteis para a nossa análise
    df_original = df_original.drop(["data_assinatura_contrato", "tipo_financiamento"], axis=1)
    print("Colunas inúteis removidas...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #transformando nossas colunas para caixa alta
    df_original.columns = df_original.columns.str.upper()
    print("Nomes das colunas em caixa alta...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #renomeando algumas colunas
    df_original.rename(columns={"VALOR_FINANCIAMENTO": "VL_FINANCIAMENTO", "VALOR_PARCELA": "VL_PARCELA",  }, inplace=True)
    print("Colunas renomeadas...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #criando faixa de valores
    faixas = [-100, 8_675, 25_000, 47_000, 9_999_999]
    categorias = ["Até R$ 8.675", "de R$ 8.676 até R$ 25.000", "de R$ 25.001 até R$ 47.000", "Mais de R$ 47.000"]
    df_original["FAIXA_VL_TOTAL_PC_PAGAS"] = pd.cut(df_original["VL_TOTAL_PC_PAGAS"], bins=faixas, labels=categorias)
    df_original["FAIXA_VL_TOTAL_PC_PAGAS"] = df_original["FAIXA_VL_TOTAL_PC_PAGAS"].cat.set_categories(categorias, ordered = True)

    faixas = [-100, 210_000, 290_000, 400_000, 9_999_999]
    categorias = ["Até R$ 210.000", "de R$ 210.000 até R$ 290.000", "de R$ 290.001 até R$ 400.000", "Mais de R$ 400.000"]
    df_original["FAIXA_VALOR_FINANCIAMENTO"] = pd.cut(df_original["VL_FINANCIAMENTO"], bins=faixas, labels=categorias)
    df_original["FAIXA_VALOR_FINANCIAMENTO"] = df_original["FAIXA_VALOR_FINANCIAMENTO"].cat.set_categories(categorias, ordered = True)

    faixas = [-100, 2_500, 3_500, 5_000, 999999]
    categorias = ["Até R$ 2.500", "de R$ 2.501 até R$ 3.500", "de R$ 3.501 até R$ 5.000", "Mais de R$ 5.000"]
    df_original["FAIXA_VALOR_PARCELA"] = pd.cut(df_original["VL_PARCELA"], bins=faixas, labels=categorias)

    faixas = [-100, 18, 25, 35, 45, 55, 65, 999]
    categorias = ["0-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
    df_original["FAIXA_IDADE_DATA_ASSINATURA_CONTRATO"] = pd.cut(df_original["IDADE_DATA_ASSINATURA_CONTRATO"], bins=faixas, labels=categorias)
    print("Faixas de valores criadas...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #excluindo as colunas antigas
    colunas = ["CIDADE_CLIENTE", "ESTADO_CLIENTE", "RENDA_MENSAL_CLIENTE", "FAIXA_IDADE_DATA_ASSINATURA_CONTRATO", "TAXA_AO_ANO", "PZ_FINANCIAMENTO", "QT_PC_ATRASO", 
            "QT_DIAS_PRIM_PC_ATRASO", "QT_TOTAL_PC_PAGAS", "QT_PC_PAGA_EM_DIA", "QT_DIAS_MIN_ATRASO", "QT_DIAS_MEDIA_ATRASO", "QT_DIAS_MAX_ATRASO", 
            "FAIXA_VL_TOTAL_PC_PAGAS", "FAIXA_VALOR_FINANCIAMENTO", "FAIXA_VALOR_PARCELA", "INADIMPLENTE_COBRANCA"]

    df_tratado = pd.DataFrame(df_original, columns = colunas)
    print("Colunas inúteis removidas...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #separando colunas numericas, coluna alvo e colunas categoricas
    colunas_numericas = df_tratado.select_dtypes(include=["number"]).columns
    coluna_alvo = df_tratado[["INADIMPLENTE_COBRANCA"]]

    df_categorico = df_tratado.drop(columns=colunas_numericas).drop(columns=coluna_alvo)
    print("Colunas separadas...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #vamos usar o Label Encoder para transformar nossas colunas categoricas em numerica para usar no modelo, pois temos muita cardinalidade na coluna de cidade e estado
    lb = LabelEncoder()

    for var in df_categorico:
        df_tratado[var] = lb.fit_transform(df_tratado[var])
    print("Label Encoder usado...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #otimizando novamente as colunas
    colunas_float = df_tratado.select_dtypes(include="float64").columns
    colunas_int = df_tratado.select_dtypes(include="int64").columns
    df_tratado[colunas_float] = df_tratado[colunas_float].apply(pd.to_numeric, downcast="float")
    df_tratado[colunas_int] = df_tratado[colunas_int].apply(pd.to_numeric, downcast="integer")
    print("Colunas otimizadas...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #separando as variaveis preditoras da variavel alvo
    var_preditoras = df_tratado.drop("INADIMPLENTE_COBRANCA", axis = 1)
    print("Colunas Preditoras separadas...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #normalizacao
    normalizador = MinMaxScaler()
    dados_normalizados = normalizador.fit_transform(var_preditoras)
    print("Colunas Normalizadas...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #previsao
    previsoes = xg.predict(dados_normalizados)
    probabilidades = xg.predict_proba(dados_normalizados)
    df_original["PREVISOES"] = previsoes
    df_original["PROBABILIDADES"] = probabilidades[:, 1]
    print("Previsão Feita...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #criando um novo dataframe
    columns = ["NUMERO_CONTRATO", "PREVISOES", "PROBABILIDADES"]
    df_conversao = pd.DataFrame(df_original, columns=columns)
    print("Dataframe criado...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #adicionando as colunas na tabela
    conexao = sql.connect(connection_string)
    cursor = conexao.cursor()

    for index, row in df_conversao.iterrows():
        contrato = row["NUMERO_CONTRATO"]
        previsoes = row["PREVISOES"]
        probabilidades = row["PROBABILIDADES"]

        print(f"NUMERO_CONTRATO (type: {type(contrato)}): {contrato}")
        print(f"PREVISOES (type: {type(previsoes)}): {previsoes}")
        print(f"PROBABILIDADES (type: {type(probabilidades)}): {probabilidades}")

        try:

            sql = "INSERT INTO RESULTADOS_INTERMEDIARIO (NUMERO_CONTRATO, PREVISOES, PROBABILIDADES) VALUES (?, ?, ?)"
            val = (contrato, previsoes, probabilidades)
            cursor.execute(sql, val)
            conexao.commit()
        except Exception as e:
            print(f"Error inserting row {index}: {e}")

    try:
        cursor.execute("EXEC SP_INPUT_RESULTADOS_MODELO_PREDITIVO")
        conexao.commit()
    except Exception as e:
        print(f"Error executing stored procedure: {e}")


    print("Colunas adicionadas...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")

    #convertendo pra excel

    sql = "SELECT * FROM PREVISOES_INADIMPLENCIA"
    df_sql = pd.read_sql(sql, conexao)

    df_sql.to_excel("excel/resultado.xlsx", index=False) 

    cursor.close() 
    conexao.close()

    print("Excel gerado...")
    print("-----------------------------------------------------------------------------------------------------------------------------------------------")
       

def main():
    gerar_previsoes()    


if __name__ == "__main__":
    main()        