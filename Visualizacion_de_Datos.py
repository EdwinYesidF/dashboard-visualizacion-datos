# ----------------------------------------------------------------------------
# 1. IMPORTS
# ----------------------------------------------------------------------------
import dash
from dash import dcc, html, dash_table, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import geopandas as gpd
import branca.colormap as cm
import folium
import base64
from pathlib import Path


# ----------------------------------------------------------------------------
# 2. INICIALIZAR LA APLICACIÓN DASH
# ----------------------------------------------------------------------------
app = dash.Dash(__name__)

ruta_certificado = Path(__file__).with_name("Certificado IBM DV0101EN _ Cognitive Class.png")
certificado_base64 = base64.b64encode(ruta_certificado.read_bytes()).decode("utf-8")


# ----------------------------------------------------------------------------
# 3. CARGA Y LIMPIEZA DEL DATASET
# ----------------------------------------------------------------------------

# 3.1 Cargar el dataset original
dataset = pd.read_excel("Anexo 1 - dataset fase 2.xlsx")

# 3.2 Latitudes fuera de rango (-90 a 90 grados)
# Se detectaron valores multiplicados por un factor muy grande (~1e12).
Latitud = dataset[(dataset['Latitud'] < -90) | (dataset['Latitud'] > 90)]
dataset = dataset[(dataset['Latitud'] >= -90) & (dataset['Latitud'] <= 90)]

# 3.3 Precios fuera de rango
valores_fuera = dataset[dataset['Precio promedio (USD)'] > 50]
dataset['Precio promedio (USD)'] = dataset['Precio promedio (USD)'].astype(float)
dataset.loc[dataset['Precio promedio (USD)'] > 100, 'Precio promedio (USD)'] = (
    dataset['Precio promedio (USD)'] / 100
)

# 3.4 Precios negativos -> se corrigen con valor absoluto
precios_negativos = dataset[dataset['Precio promedio (USD)'] < 0]
dataset['Precio promedio (USD)'] = dataset['Precio promedio (USD)'].abs()

# 3.5 Unificar categorías inconsistentes
dataset['Categoría'] = dataset['Categoría'].replace({
    'Fusión?': 'Colombiana',
    'Chino': 'China',
    ' ': 'Colombiana',
    'Desconocida': 'Colombiana',
    'Colombian': 'Colombiana'
})

# 3.6 Resumen: número de restaurantes por categoría
categorias_resumen = (
    dataset.groupby("Categoría")["Nombre"]
    .count()
    .reset_index()
    .rename(columns={"Nombre": "Número de restaurantes"})
)


# ----------------------------------------------------------------------------
# 4. PREPARACIÓN GEOESPACIAL
# ----------------------------------------------------------------------------

# 4.1 Cargar el shapefile de departamentos de Colombia
departamentos = gpd.read_file("COLOMBIA.shp")
if departamentos.crs is None:
    departamentos = departamentos.set_crs("EPSG:4326", allow_override=True)
print(departamentos.columns)  # referencia rápida de los nombres de columnas

# 4.2 Convertir el dataset de restaurantes a GeoDataFrame
gdf = gpd.GeoDataFrame(
    dataset,
    geometry=gpd.points_from_xy(dataset["Longitud"], dataset["Latitud"]),
    crs="EPSG:4326"  # WGS84, el sistema de coordenadas estándar de GPS
)

# 4.3 Cruce espacial
gdf = gpd.sjoin(gdf, departamentos, how="left", predicate="within")

# Nombre de la columna del shapefile que identifica al departamento.
left_on = "DPTO_CNMBR"
dataset["Departamento"] = gdf[left_on]

# 4.4 Precio promedio por departamento 
precio_por_departamento = (
    dataset.groupby("Departamento")["Precio promedio (USD)"]
    .mean()
    .reset_index()
    .rename(columns={"Precio promedio (USD)": "precio_promedio"})
)

# 4.5 Unir la geometría de los departamentos con su precio promedio
gdf_merged = departamentos.merge(
    precio_por_departamento,
    left_on=left_on,
    right_on="Departamento",
    how="left"
)


# ----------------------------------------------------------------------------
# 5. ANÁLISIS EXPLORATORIO DE DATOS (EDA)
# ----------------------------------------------------------------------------
variables = dataset[['Calificación', 'Precio promedio (USD)', 'Número de reseñas']]
resumen = variables.describe().reset_index()


# ----------------------------------------------------------------------------
# 6. GRÁFICOS DE PLOTLY
# ----------------------------------------------------------------------------

# 6.1 Precio promedio por categoría 
precios_por_categoria = dataset.groupby("Categoría")["Precio promedio (USD)"].mean().reset_index()

fig_precios_categorias = px.bar(
    precios_por_categoria,
    x="Precio promedio (USD)",
    y="Categoría",
    orientation="h",
    title="Precio promedio por categoría",
    color="Precio promedio (USD)",
    color_continuous_scale="viridis"
)

# 6.2 Boxplots de Calificación, Precio y Número de reseñas
fig_calificaciones = px.box(
    dataset,
    y="Calificación",
    title="Boxplot Calificaciones",
    color_discrete_sequence=["skyblue"]
)

fig_precios = px.box(
    dataset,
    y="Precio promedio (USD)",
    title="Boxplot Precios",
    color_discrete_sequence=["lightgreen"]
)

fig_reseñas = px.box(
    dataset,
    y="Número de reseñas",
    title="Boxplot Reseñas",
    color_discrete_sequence=["salmon"]
)

# 6.3 Categorías de comida más populares
categorias_populares = dataset["Categoría"].value_counts().reset_index()
categorias_populares.columns = ["Categoría", "Número de restaurantes"]

fig_categorias = px.bar(
    categorias_populares,
    x="Número de restaurantes",
    y="Categoría",
    title="Categorías de comida más populares",
    orientation="h",
    color="Número de restaurantes",
    color_continuous_scale="Viridis",
    text="Número de restaurantes"
)
fig_categorias.update_traces(
    textposition="outside",
    hovertemplate="<b>%{y}</b><br>Número de restaurantes: %{x}<extra></extra>"
)
fig_categorias.update_yaxes(categoryorder="total ascending")
fig_categorias.update_layout(
    template="plotly_white",
    title_font=dict(size=20, color="#2C3E50"),
    yaxis_title="Categorías",
    xaxis_title="Número de restaurantes",
    plot_bgcolor="#F8F9F9",
    paper_bgcolor="#F8F9F9",
    font=dict(family="Arial", size=12, color="#1C2936"),
    hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial"),
    margin=dict(l=80, r=40, t=80, b=80)
)

# 6.4 Departamentos con mayor concentración de restaurantes
departamentos_populares = dataset["Departamento"].value_counts().reset_index()
departamentos_populares.columns = ["Departamento", "Número de restaurantes"]

fig_departamentos = px.bar(
    departamentos_populares,
    x="Número de restaurantes",
    y="Departamento",
    title="Departamentos con mayor concentración de restaurantes",
    orientation="h",
    color="Número de restaurantes",
    color_continuous_scale="Viridis",
    text="Número de restaurantes"
)
fig_departamentos.update_traces(
    textposition="outside",
    hovertemplate="<b>%{x}</b><br>Número de restaurantes: %{y}<extra></extra>"
)
fig_departamentos.update_yaxes(categoryorder="total ascending")
fig_departamentos.update_layout(
    template="plotly_white",
    title_font=dict(size=20, color="#2C3E50"),
    yaxis_title="Departamentos",
    xaxis_title="Número de restaurantes",
    plot_bgcolor="#F8F9F9",
    paper_bgcolor="#F8F9F9",
    font=dict(family="Arial", size=12, color="#1C2936"),
    hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial"),
    margin=dict(l=80, r=40, t=80, b=80)
)

# 6.5 Análisis geoespacial: precio y calificación promedio por departamento
#¿hay departamentos con restaurantes más caros
# o mejor calificados que otros?
analisis_geo = dataset.groupby("Departamento").agg(
    precio_promedio=("Precio promedio (USD)", "mean"),
    calificacion_promedio=("Calificación", "mean"),
    num_restaurantes=("Nombre", "count")
).reset_index()

correlacion_precio_calidad = analisis_geo["precio_promedio"].corr(
    analisis_geo["calificacion_promedio"]
)

# El dataset entregado no contiene la columna Ciudad. Si se incorpora en una
# versión posterior se usa automáticamente; por ahora se filtra por Departamento.
columna_ubicacion = "Ciudad" if "Ciudad" in dataset.columns else "Departamento"
etiqueta_ubicacion = "Ciudad" if columna_ubicacion == "Ciudad" else "Departamento"

# Filtra los datos usados por todos los componentes de la Actividad 3.
def filtrar_dashboard(categorias, ubicaciones):
   
    df = dataset.copy()
    if categorias:
        df = df[df["Categoría"].isin(categorias)]
    if ubicaciones:
        df = df[df[columna_ubicacion].isin(ubicaciones)]
    return df

#Crea una dispersión y añade la recta de regresión lineal y Pearson r.
def crear_regresion(df, x, titulo):
    
    figura = px.scatter(
        df, x=x, y="Calificación", color="Categoría",
        hover_data=["Nombre", columna_ubicacion, "Precio promedio (USD)", "Número de reseñas"],
        labels={x: x, "Calificación": "Calificación"},
    )
    datos = df[[x, "Calificación"]].dropna()
    if len(datos) >= 2 and datos[x].nunique() > 1:
        pendiente, intercepto = np.polyfit(datos[x], datos["Calificación"], 1)
        valores_x = np.linspace(datos[x].min(), datos[x].max(), 100)
        figura.add_trace(go.Scatter(
            x=valores_x, y=pendiente * valores_x + intercepto,
            mode="lines", name="Regresión lineal",
            line={"color": "#C0392B", "width": 3},
        ))
        titulo = f"{titulo} (r = {datos[x].corr(datos['Calificación']):.3f})"
    figura.update_layout(title=titulo, template="plotly_white", legend_title_text="Categoría")
    return figura


def crear_figuras_actividad3(df):
    """Construye las visualizaciones de dispersión, burbujas y regresión."""
    hover = ["Nombre", columna_ubicacion, "Número de reseñas"]
    dispersion = px.scatter(
        df, x="Precio promedio (USD)", y="Calificación", color="Categoría",
        hover_data=hover, title="Dispersión: precio promedio y calificación",
        labels={"Precio promedio (USD)": "Precio promedio (USD)", "Calificación": "Calificación"},
    )
    burbujas = px.scatter(
        df, x="Precio promedio (USD)", y="Calificación", size="Número de reseñas",
        color="Categoría", size_max=42, hover_data=hover,
        title="Burbujas: precio, calificación y número de reseñas",
        labels={"Precio promedio (USD)": "Precio promedio (USD)", "Calificación": "Calificación"},
    )
    for figura in [dispersion, burbujas]:
        figura.update_layout(template="plotly_white", legend_title_text="Categoría")
    return (
        dispersion,
        burbujas,
        crear_regresion(df, "Precio promedio (USD)", "Regresión: precio frente a calificación"),
        crear_regresion(df, "Número de reseñas", "Regresión: reseñas frente a calificación"),
    )





def crear_mapa_filtrado(df):
    """Genera el mapa Folium con los restaurantes que cumplen los filtros."""
    df = df.dropna(subset=["Latitud", "Longitud"])
    df = df[df["Latitud"].between(-90, 90) & df["Longitud"].between(-180, 180)]
    if df.empty:
        return "<p>No hay restaurantes con coordenadas para los filtros seleccionados.</p>"
    mapa = folium.Map(location=[df["Latitud"].mean(), df["Longitud"].mean()], zoom_start=6)
    for _, fila in df.iterrows():
        folium.CircleMarker(
            location=[fila["Latitud"], fila["Longitud"]], radius=5, fill=True,
            tooltip=str(fila["Nombre"]),
            popup=(f"<b>{fila['Nombre']}</b><br>Categoría: {fila['Categoría']}<br>"
                   f"Calificación: {fila['Calificación']}<br>"
                   f"Precio: USD {fila['Precio promedio (USD)']}<br>"
                   f"Reseñas: {fila['Número de reseñas']}"),
        ).add_to(mapa)
    return mapa._repr_html_()

fig_precio_calidad = px.scatter(
    analisis_geo,
    x="precio_promedio",
    y="calificacion_promedio",
    size="num_restaurantes",
    color="Departamento",
    text="Departamento",
    title="Precio promedio vs. Calificación promedio por departamento",
    labels={
        "precio_promedio": "Precio promedio (USD)",
        "calificacion_promedio": "Calificación promedio",
        "num_restaurantes": "N.º de restaurantes"
    }
)
fig_precio_calidad.update_traces(textposition="top center")
fig_precio_calidad.update_layout(
    template="plotly_white",
    showlegend=False,
    plot_bgcolor="#F8F9F9",
    paper_bgcolor="#F8F9F9",
    font=dict(family="Arial", size=12, color="#1C2936"),
    margin=dict(l=80, r=40, t=80, b=80)
)


# ----------------------------------------------------------------------------
# 7. CALLBACKS — MAPAS DE FOLIUM
# ----------------------------------------------------------------------------

@app.callback(
    Output("mapa", "srcDoc"),
    Input("dropdown-departamento", "value")
)
def actualizar_mapa(departamento_seleccionado):
    """Mapa de marcadores: un pin por restaurante del departamento elegido."""
    if departamento_seleccionado is None:
        return ""  # evita errores si aún no hay valor seleccionado

    df_filtrado = dataset[dataset["Departamento"] == departamento_seleccionado]

    if df_filtrado.empty or "Latitud" not in df_filtrado.columns or "Longitud" not in df_filtrado.columns:
        return "<p>No hay datos geográficos para este departamento.</p>"

    mapa = folium.Map(location=[4.5709, -74.2973], zoom_start=6)

    for _, row in df_filtrado.iterrows():
        try:
            lat = float(row["Latitud"])
            lon = float(row["Longitud"])
        except Exception:
            continue
        folium.Marker(
            location=[lat, lon],
            popup=f"{row.get('Nombre', '')} - {row.get('Categoría', '')} ({row.get('Calificación', '')})",
            tooltip=row.get("Nombre", "")
        ).add_to(mapa)

    return mapa._repr_html_()

#Mapa de coropletas: colorea cada departamento según su precio promedioy resalta con borde azul el departamento elegido en el dropdown.
def crear_mapa_coropletas(departamento_seleccionado=None):

    mapa = folium.Map(location=[4.5709, -74.2973], zoom_start=6, tiles="OpenStreetMap")

    if gdf_merged.empty or "precio_promedio" not in gdf_merged.columns:
        return mapa._repr_html_()

    min_val = gdf_merged["precio_promedio"].min()
    max_val = gdf_merged["precio_promedio"].max()
    colormap = cm.linear.YlOrRd_09.scale(min_val, max_val)
    colormap.caption = "Precio promedio por departamento"

    # Se construye el GeoJSON directamente desde gdf_merged, así
    # 'precio_promedio' siempre está disponible en cada feature.
    geojson_con_datos = gdf_merged.__geo_interface__

    def estilo(feature):
        valor = feature["properties"].get("precio_promedio")
        seleccionado = feature["properties"].get(left_on) == departamento_seleccionado
        return {
            "fillColor": colormap(valor) if valor is not None else "lightgray",
            "color": "black" if not seleccionado else "blue",
            "weight": 0.3 if not seleccionado else 2,
            "fillOpacity": 0.8,
        }

    folium.GeoJson(
        geojson_con_datos,
        name="Precios",
        style_function=estilo,
        highlight_function=lambda f: {"weight": 2, "color": "blue"},
        tooltip=folium.GeoJsonTooltip(
            fields=[left_on, "precio_promedio"],
            aliases=["Departamento:", "Precio promedio:"],
            localize=True
        )
    ).add_to(mapa)

    colormap.add_to(mapa)
    folium.LayerControl().add_to(mapa)
    return mapa._repr_html_()


@app.callback(
    Output("mapa_coropletas", "srcDoc"),
    Input("dropdown-departamento", "value")
)
def actualizar_mapa_coropletas(departamento_seleccionado):
    return crear_mapa_coropletas(departamento_seleccionado)


@app.callback(
    Output("grafico-dispersion", "figure"),
    Output("grafico-burbujas", "figure"),
    Output("grafico-regresion-precio", "figure"),
    Output("grafico-regresion-reseñas", "figure"),
    Input("filtro-categoria", "value"),
    Input("filtro-ubicacion", "value"),
)
def actualizar_graficos_actividad3(categorias, ubicaciones):
    return crear_figuras_actividad3(filtrar_dashboard(categorias, ubicaciones))


@app.callback(
    Output("mapa-actividad3", "srcDoc"),
    Input("filtro-categoria", "value"),
    Input("filtro-ubicacion", "value"),
)
def actualizar_mapa_actividad3(categorias, ubicaciones):
    return crear_mapa_filtrado(filtrar_dashboard(categorias, ubicaciones))


# ----------------------------------------------------------------------------
# 8. LAYOUT DEL DASHBOARD
# ----------------------------------------------------------------------------
app.layout = html.Div([

    html.H1(
        "VISUALIZACIÓN PARA LA ANALÍTICA DE DATOS - (203238429A_2204)",
        style={"textAlign": "center", "color": "#FFFFFF", "backgroundColor": "#222", "padding": "10px"}
    ),

    html.Div([
        html.H3("Fase 2 - Componente Práctico"),
        html.P("Presentado por: Edwin Yesid Fonseca Ahumada"),
        html.P("Grupo: 203238429_7"),
        html.P("Código: 80012391"),
        html.P("Presentado a: SIXYEL JEYSON CASTAÑEDA CORONADO"),
        html.P("Universidad Nacional Abierta y a Distancia – UNAD"),
        html.P("Fecha: Septiembre 2026"),
    ], style={"margin": "20px"}),

    html.H2("Tabla de contenidos"),
    html.Ul([
        html.Li(html.A("1. Introducción", href="#introduccion")),
        html.Li(html.A("2. Objetivos", href="#objetivos")),
        html.Li(html.A("3. Actividad 1 Preparación del dataset y Análisis Exploratorio de Datos", href="#actividad1")),
        html.Li(html.A("4. Actividad 2 Visualización Geoespacial con Folium", href="#actividad2")),
        html.Li(html.A("5. Actividad 3 Creación de Gráficos Interactivos y Dashboard con Plotly y Dash", href="#actividad3")),
        html.Li(html.A("6. Actividad 4 Completar la Certificación IBM Cognitive", href="#actividad4")),
    ], style={"backgroundColor": "#D9F7FF", "padding": "10px"}),

    html.H1("Introducción", id="introduccion"),
    html.P("""
    La visualización de datos constituye una herramienta esencial dentro del proceso de analítica,
    ya que permite transformar grandes volúmenes de información en representaciones gráficas comprensibles
    y útiles para la toma de decisiones. En esta fase se aplicarán técnicas de visualización mediante el uso
    de librerías de Python como Matplotlib, Seaborn, Folium y Plotly, con el fin de explorar, analizar y
    comunicar los hallazgos obtenidos a partir del dataset de restaurantes de Colombia.
    """),
    html.P("""
    El desarrollo de esta actividad permitirá fortalecer las competencias en el manejo de herramientas
    de programación orientadas al análisis visual, fomentando la interpretación crítica de los resultados
    y la generación de conclusiones basadas en evidencia. Además, se integrarán conceptos de visualización
    geoespacial e interacción dinámica, elementos clave en la analítica moderna.
    """),

    html.H1("Objetivos", id="objetivos"),

    html.H2("Objetivo General"),
    html.P("""
    Aplicar técnicas de visualización de datos mediante herramientas de programación en Python,
    con el fin de analizar, interpretar y comunicar información relevante a partir de un dataset,
    fortaleciendo las competencias en analítica y toma de decisiones.
    """),

    html.H2("Objetivos Específicos"),
    html.Ul([
        html.Li("Preparar y depurar el dataset para garantizar la calidad de la información utilizada en el análisis."),
        html.Li("Realizar un análisis exploratorio de datos (EDA) que permita identificar patrones, tendencias y relaciones significativas."),
        html.Li("Implementar visualizaciones geoespaciales utilizando la librería Folium para representar datos en mapas interactivos."),
        html.Li("Diseñar gráficos dinámicos e interactivos con Plotly y Dash, orientados a la construcción de dashboards informativos."),
        html.Li("Desarrollar habilidades prácticas en el uso de librerías de visualización que faciliten la interpretación crítica de los resultados.")
    ]),

    html.H1("Actividad 1 Preparación del dataset y Análisis Exploratorio de Datos", id="actividad1"),

    html.H2("Carga del Data set Inicial"),
    dash_table.DataTable(
        data=dataset.to_dict('records'),
        columns=[{"name": i, "id": i} for i in dataset.columns],
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'}
    ),

    html.H2("Latitudes fuera de rango"),
    html.P("""
        Al realizar la verificación del dataset se encontraron valores en la columna latitud con un rango
        inválido; el rango debe estar entre -90 y 90 grados. Se observa que los valores parecen estar
        multiplicados por un factor muy grande (~1e12). La solución es dividirlos por 1e12 para llevarlos
        al rango correcto.
    """),
    dash_table.DataTable(
        data=Latitud.to_dict('records'),
        columns=[{"name": i, "id": i} for i in Latitud.columns],
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'}
    ),

    html.H2("Valores fuera de rango en Precio promedio (USD)"),
    html.P("""
        Se observaron 3 valores de precio promedio por encima del rango esperado. Los precios deberían
        estar entre 10 y 50 unidades (según los demás registros del dataset). Por tanto, la mejor
        estrategia es reescalar los valores grandes dividiéndolos por 100.La columna llega como int64 d
        esde el Excel; se convierte a float ANTES de dividir
    """),
    dash_table.DataTable(
        data=valores_fuera.to_dict('records'),
        columns=[{"name": i, "id": i} for i in valores_fuera.columns],
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'}
    ),

    html.H2("Valores negativos en Precio promedio (USD)"),
    html.P("""
        Se evidenciaron valores negativos en la columna Precio promedio (USD); lo más lógico es aplicar
        valor absoluto (abs()), asumiendo que el error fue un signo mal digitado.
    """),
    dash_table.DataTable(
        data=precios_negativos.to_dict('records'),
        columns=[{"name": i, "id": i} for i in precios_negativos.columns],
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'}
    ),

    html.H2("Categorías únicas y número de restaurantes"),
    html.P("""
        Se identificaron inconsistencias en los nombres de las categorías ("Fusión?", "Desconocida",
        "Chino", "Colombian") y valores nulos. Esto se resolvió con una limpieza de texto para unificar
        y corregir los valores antes de graficar. Como los restaurantes están en Colombia, las categorías
        "Desconocida" y "Fusión?" se reasignaron a la categoría "Colombiana".
    """),
    dash_table.DataTable(
        data=categorias_resumen.to_dict('records'),
        columns=[{"name": i, "id": i} for i in categorias_resumen.columns],
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'},
    ),

    html.H2("Dataset depurado y con nueva columna Departamento"),
    dash_table.DataTable(
        data=dataset.to_dict('records'),
        columns=[{"name": i, "id": i} for i in dataset.columns],
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'}
    ),

    html.H2("Resumen estadístico descriptivo"),
    dash_table.DataTable(
        data=resumen.to_dict('records'),
        columns=[{"name": i, "id": i} for i in resumen.columns],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'}
    ),

    html.H2("Tabla de categorías y precios promedio"),
    dash_table.DataTable(
        data=dataset[['Categoría', 'Precio promedio (USD)']].to_dict('records'),
        columns=[{"name": i, "id": i} for i in ['Categoría', 'Precio promedio (USD)']],
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'}
    ),

    dcc.Graph(id="grafico-precios-categorias", figure=fig_precios_categorias),

    html.H2("Distribución de calificaciones, precios y reseñas."),
    html.Div([
        dcc.Graph(figure=fig_calificaciones, style={"display": "inline-block", "width": "33%"}),
        dcc.Graph(figure=fig_precios, style={"display": "inline-block", "width": "33%"}),
        dcc.Graph(figure=fig_reseñas, style={"display": "inline-block", "width": "33%"}),
    ]),

    html.H2("Categorias de comidas mas populares en Colombia"),
    html.Div([
        dcc.Graph(figure=fig_categorias),
    ]),

    html.H2("Departamentos que concentran mas restaurantes"),
    html.Div([
        dcc.Graph(figure=fig_departamentos),
    ]),

    html.H1("Actividad 2 Visualización Geoespacial con Folium", id="actividad2"),

    html.Div([
        html.H2("Mapa de Restaurantes por Departamento", style={"textAlign": "center"}),

        dcc.Dropdown(
            id="dropdown-departamento",
            options=[{"label": d, "value": d} for d in sorted(dataset["Departamento"].dropna().unique())],
            value=(
                sorted(dataset["Departamento"].dropna().unique())[0]
                if len(dataset["Departamento"].dropna().unique()) > 0 else None
            ),
            style={"width": "500px"}
        ),

        html.Iframe(id="mapa", width="100%", height="600"),

        html.H2("Mapa de Precios Promedio por Departamento (coropletas)", style={"textAlign": "center"}),
        html.Iframe(id="mapa_coropletas", width="100%", height="600"),

        html.H2("¿Existen departamentos con restaurantes más caros o mejor calificados?"),
        html.P("""
            Se calculó el precio promedio y la calificación promedio de los restaurantes agrupados por
            departamento, para identificar si existen patrones geográficos claros en precio y calidad.
        """),

        dash_table.DataTable(
            data=analisis_geo.sort_values("precio_promedio", ascending=False).to_dict('records'),
            columns=[{"name": i, "id": i} for i in analisis_geo.columns],
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'center'}
        ),

        dcc.Graph(id="grafico-precio-calidad", figure=fig_precio_calidad),

        html.P(
            f"Correlación entre precio promedio y calificación promedio por departamento: "
            f"{correlacion_precio_calidad:.3f}. "
            + (
                "Una correlación cercana a 0 indica que no hay una relación clara entre pagar más "
                "y recibir mejor calificación en los distintos departamentos."
                if abs(correlacion_precio_calidad) < 0.3 else
                "Esto sugiere una relación entre el precio promedio y la calificación de los restaurantes "
                "según el departamento."
            ),
            style={"fontStyle": "italic", "margin": "10px 20px"}
        ),

    ], style={"margin": "20px"}),

    # ------------------------------------------------------------------------
    # ACTIVIDAD 3 — Dashboard interactivo con Plotly, Dash y Folium
    # ------------------------------------------------------------------------
    html.H1("Actividad 3: Gráficos Interactivos y Dashboard", id="actividad3"),
    html.P(
        "Utilice los filtros para actualizar simultáneamente los gráficos y el mapa.",
        style={"margin": "0 20px 15px"},
    ),
    html.Div([
        html.Div([
            html.Label("Categorías"),
            dcc.Dropdown(
                id="filtro-categoria", multi=True, value=[],
                options=[{"label": c, "value": c} for c in sorted(dataset["Categoría"].dropna().unique())],
                placeholder="Todas las categorías",
            ),
        ], style={"width": "48%", "display": "inline-block", "verticalAlign": "top"}),
        html.Div([
            html.Label(etiqueta_ubicacion),
            dcc.Dropdown(
                id="filtro-ubicacion", multi=True, value=[],
                options=[{"label": u, "value": u} for u in sorted(dataset[columna_ubicacion].dropna().unique())],
                placeholder=f"Todos los {etiqueta_ubicacion.lower()}s",
            ),
        ], style={"width": "48%", "marginLeft": "3%", "display": "inline-block", "verticalAlign": "top"}),
    ], style={"margin": "0 20px 10px"}),
    html.P(
        "El archivo fuente no contiene la variable Ciudad; por ahora el segundo filtro usa Departamento. "
        "Al agregar una columna Ciudad, el dashboard la reconocerá automáticamente.",
        style={"fontStyle": "italic", "margin": "0 20px 15px"},
    ) if columna_ubicacion == "Departamento" else html.Div(),
    dcc.Tabs(value="relaciones", children=[
        dcc.Tab(label="Dispersión y burbujas", value="relaciones", children=[
            html.Div([
                dcc.Graph(id="grafico-dispersion"),
                dcc.Graph(id="grafico-burbujas"),
            ], style={"margin": "20px"}),
        ]),
        dcc.Tab(label="Regresiones y correlaciones", value="regresiones", children=[
            html.Div([
                html.P("La línea roja es el ajuste lineal; r corresponde a la correlación de Pearson."),
                dcc.Graph(id="grafico-regresion-precio"),
                dcc.Graph(id="grafico-regresion-reseñas"),
            ], style={"margin": "20px"}),
        ]),
        dcc.Tab(label="Mapa filtrado", value="mapa", children=[
            html.Div([
                html.P("Cada marcador representa un restaurante incluido por los filtros activos."),
                html.Iframe(id="mapa-actividad3", width="100%", height="600"),
            ], style={"margin": "20px"}),
        ]),
    ]),

      # ------------------------------------------------------------------------
        # ACTIVIDAD 4 — DActividad 4 Completar la Certificación IBM Cognitive
        # ------------------------------------------------------------------------

    html.H1("Actividad 4 Completar la Certificación IBM Cognitive", id="actividad4"),
    html.H2("Certificación Data Visualization with Python"),
    html.Div([
        html.Img(
            src=f"data:image/png;base64,{certificado_base64}",
            alt="Certificado IBM Data Visualization with Python de Edwin Yesid Fonseca",
            style={"display": "block", "maxWidth": "100%", "height": "auto", "margin": "20px auto"},
        ),
    ], style={"margin": "20px"}),

], style={"fontFamily": "Arial", "margin": "40px"})


# ----------------------------------------------------------------------------
# 9. ARRANCAR EL SERVIDOR
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
