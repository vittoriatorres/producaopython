# Importando bibliotecas
import arcpy
import arcpy.mp
import os
import math

projeto = arcpy.mp.ArcGISProject("CURRENT")
m = projeto.listMaps("Map")[0]
diretorio = r"T:\RECAD\Vittoria Torres\Dados\Base Info\Input\ArcGISLevantamento.gdb"
quadras = r"T:\RECAD\Vittoria Torres\Dados\Base Info\Input\Teste_Qds.shp"
lotes = r"T:\RECAD\Vittoria Torres\Dados\Base Info\Input\Teste_Lts.shp"
edific = r"T:\RECAD\Vittoria Torres\Dados\Base Info\Input\Teste_Edific.shp"
logra = r"T:\RECAD\Vittoria Torres\Dados\Base de Dados\CamadasVetoriais\Logradouros.shp"

# Definindo o ambiente de trabalho
arcpy.env.workspace = diretorio

# Definindo nomes de saída para as camadas
lotes_arestas = f"{diretorio}\\Lotes_Arestas"
buffer_15m = f"{diretorio}\\Logra_Buffer_15m"
lotes_testadas = f"{diretorio}\\Lotes_Testadas"
lotes_testadas_m=f"{diretorio}\\Lotes_Testadas_M"
quadra_linha=f"{diretorio}\\Qds_Linha"

# Listar e imprimir os nomes dos campos da camada e seus tipos

campos = arcpy.ListFields(lotes_testadas_m)

# Imprimir os nomes dos campos e seus tipos
print(f"Campos na camada {lotes_testadas_m}:")
for campo in campos:
    print(f"Nome: {campo.name}, Tipo: {campo.type}")

try:
    # 1. Extrair as arestas dos polígonos da camada 'lotes' e conservar apenas os campos OBJECTID, tx_insct e tx_faststr
    arcpy.FeatureToLine_management(
        in_features=lotes,
        out_feature_class=lotes_arestas,
        attributes="ATTRIBUTES"
    )
    print("1. Arestas dos polígonos extraídas com sucesso.")
except arcpy.ExecuteError as e:
    print(f"Erro ao extrair as arestas dos polígonos: {e}")

try:
    # Manter apenas os campos OBJECTID, tx_insct, tx_faststr e Shape_Length na camada 'lotes_arestas'
    fields_to_keep = ["OBJECTID", "tx_insct", "tx_faststr","Shape_Length"]
    all_fields = [f.name for f in arcpy.ListFields(lotes_arestas) 
                  if f.name not in fields_to_keep and f.type not in ["OID", "Geometry"]]

    # Remover campos não obrigatórios
    removable_fields = []
    for field in all_fields:
        field_info = arcpy.ListFields(lotes_arestas, field)[0]
        if not field_info.required:  # Verifica se o campo não é obrigatório
            removable_fields.append(field)
    
    if removable_fields:
        arcpy.DeleteField_management(lotes_arestas, removable_fields)
        print("Campos desnecessários removidos com sucesso.")
    else:
        print("Nenhum campo desnecessário encontrado para remover.")
except arcpy.ExecuteError as e:
    print(f"Erro ao remover campos desnecessários: {e}")

try:
    # 3. Criar um campo na camada lotes_arestas chamado int_testada para guardar a medida das arestas selecionadas como um número inteiro
    arcpy.AddField_management(
        in_table=lotes_arestas,
        field_name="int_testada",
        field_type="LONG"  # Tipo inteiro
    )
    print("3. Campo 'int_testada' adicionado com sucesso.")
except arcpy.ExecuteError as e:
    print(f"Erro ao adicionar o campo 'int_testada': {e}")

try:
    # 2. Criar um buffer de 15 metros da camada de logradouros e dissolver as feições em uma só
    arcpy.Buffer_analysis(
        in_features=logra,
        out_feature_class=buffer_15m,
        buffer_distance_or_field="15 Meters",
        line_side="FULL",
        line_end_type="ROUND",
        dissolve_option="ALL"  # Dissolve todas as feições em uma única feição
    )
    print("2. Buffer de 15 metros criado e dissolvido com sucesso.")
except arcpy.ExecuteError as e:
    print(f"Erro ao criar o buffer de 15 metros: {e}")

try:
    # Preencher o campo 'int_testada' com a medida da aresta
    arcpy.CalculateField_management(
        in_table=lotes_arestas,
        field="int_testada",
        expression="!Shape_Length!",  # Preenche o campo com a medida da aresta
        expression_type="PYTHON3",
    )
    print("5. Campo 'int_testada' preenchido com a medida das arestas.")
except arcpy.ExecuteError as e:
    print(f"Erro ao preencher o campo 'int_testada': {e}")

# Criar uma camada temporária com a seleção
try:
    arcpy.MakeFeatureLayer_management(
        in_features=lotes_arestas,
        out_layer="Lotes_Arestas_Layer"
    )
    print("Camada temporária criada com sucesso.")
except arcpy.ExecuteError as e:
    print(f"Erro ao criar a camada temporária: {e}")

# Selecionar as arestas que são testadas
try:
    arcpy.SelectLayerByLocation_management(
        in_layer="Lotes_Arestas_Layer",
        overlap_type="HAVE_THEIR_CENTER_IN",
        select_features=buffer_15m,
        selection_type="NEW_SELECTION"
    )
    print("Testadas selecionadas com sucesso.")
except arcpy.ExecuteError as e:
    print(f"Erro ao selecionar as arestas testadas: {e}")

# Exportar as feições selecionadas da camada temporária
try:
    arcpy.FeatureClassToFeatureClass_conversion(
        in_features="Lotes_Arestas_Layer",
        out_path=diretorio,
        out_name="Lotes_Testadas",
        where_clause="1=1"  # Seleciona apenas as feições selecionadas na camada temporária
    )
    print("Feições selecionadas exportadas para 'Lotes_Testadas' com sucesso.")
except arcpy.ExecuteError as e:
    print(f"Erro ao exportar feições selecionadas: {e}")

# Mesclar feições da camada 'Lotes_Testadas' com a mesma informação no campo 'tx_faststr'
try:
    dissolve_field = "tx_faststr"  # Campo para dissolver
    # Especificar os campos e as funções de agregação
    fields_to_aggregate = [
        ["tx_insct", "FIRST"],  # Mantém o primeiro valor do campo 'x_insct'
        ["OBJECTID", "FIRST"],  # Mantém o primeiro valor do campo 'OBJECTID'
        ["int_testada", "FIRST"]  # Soma os valores do campo 'int_testada'
    ]

    # Executar o dissolve com base no campo 'tx_faststr'
    arcpy.management.Dissolve(
        in_features=lotes_testadas,
        out_feature_class=lotes_testadas_m,
        dissolve_field=dissolve_field,  # Dissolve baseado no campo 'tx_faststr'
        statistics_fields=fields_to_aggregate,  # Especifica como os campos serão agregados
        multi_part="SINGLE_PART"  # Mantém as feições multiparticionadas separadas
    )
    print("Feições dissolvidas com sucesso com base no campo 'tx_faststr'.")
except arcpy.ExecuteError as e:
    print(f"Erro ao dissolver as feições: {e}")

# Realizar verificação manual após a operação, pois, dependendo da configuração do desenho a quadra, algumas testadas podem não ser selecionadas.
# Ajustes os parâmetros conforme suas necessidades. :)

# Transformar polígono Quadra em linha
arcpy.FeatureToLine_management(quadras, quadra_linha)

# ESSA PARTE NECESSITA REVISÃO

try:
    # Reordenar vértices da quadra a partir do ponto 0
    with arcpy.da.UpdateCursor(quadra_linha, ["SHAPE@"]) as cursor:
        for row in cursor:
            # Obter vértices
            polyline = row[0]
            points = [p for p in polyline.getPart(0)]
            
            # Escolher novo ponto inicial (ex.: índice 57)
            # Observação: Antes deve obter o índice do vértice desejado manualmente
            # Ribbon> Edit> Edit Vertices> Select Feature> Select Vertice>
        # Right Click on the selected vertice > Search for the number of the desired index (it will be selected)
            new_start_index = 57  # Substitua pelo índice que você determinou
            
            # Reordenar os pontos começando do novo ponto inicial
            new_points = points[new_start_index:] + points[:new_start_index]
            
            # Criar uma nova linha com a nova ordem de vértices
            new_line = arcpy.Polyline(arcpy.Array([arcpy.Point(p.X, p.Y) for p in new_points]))
            
            # Atualizar o cursor com a nova geometria
            row[0] = new_line
            cursor.updateRow(row)

    print("Os vértices foram reordenados com sucesso")

except arcpy.ExecuteError as e:
    print(f"Erro ao reordenar vértices: {e}")

except Exception as e:
    print(f"Erro geral: {e}")
    
# PROBLEMA: APÓS A OPERAÇÃO, PARTE DA LINHHA PODE SUMIR. ESTOU REALIZANDO 'Continue Feature'

# Será necessário adiconar novos campos em 'Lotes_Testadas_M': tx_abr_n(string) e seq_quadra(long)
# tx_abr_n(string) = recebe o n° novo dos lotes
# seq_quadra(long) = indexa os lotes de acordo com a sequencia da quadra
