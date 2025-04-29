import streamlit as st
from sqlalchemy import create_engine
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- Configurar página ---
st.set_page_config(
    page_title="Dashboard Pedidos Cancelados",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Función para crear el gráfico de dona ---
def donut_plotly(percentage, color_palette):
    if color_palette == 'green':
        chart_colors = ['#27AE60', '#12783D']  # Verde
    elif color_palette == 'red':
        chart_colors = ['#E74C3C', '#781F16']  # Rojo
    else:
        chart_colors = ['#29b5e8', '#155F7A']  #  azul

    fig = go.Figure(data=[go.Pie(
        labels=['CANCELADO', 'FACTURADO'],
        values=[100 - percentage, percentage],  # corregido: porcentaje facturado
        hole=0.6,
        marker_colors=chart_colors,
        textinfo='none'
    )])

    fig.add_annotation(
        text=f"{percentage}%",
        font_size=24,
        showarrow=False
    )

    fig.update_layout(
        showlegend=False,
        width=250,
        height=250,
        margin=dict(t=0, b=0, l=0, r=0)
    )

    return fig
# Crear motor SQLAlchemy a partir de la URL del archivo secrets.toml
engine = create_engine(st.secrets["connections"]["sql"]["ebs12"])

# Consulta con cacheo
@st.cache_data(ttl=120)  # Cachea por 10 minutos
def obtener_datos():
    query = r"""
    
Select 
	ooha.HEADER_ID,
	RCTA.PURCHASE_ORDER		AS OCC,
	OOHA.ORDER_NUMBER		AS [No PEDIDO ORACLE],
	HAOU.NAME				AS ALMACEN,
	HPSF.PARTY_SITE_NUMBER	AS CLIENTE_FACTURACION,
    HPS.PARTY_SITE_NUMBER	AS CLIENTE_ENTREGA,
    HP.PARTY_NAME			AS CLIENTE,
	HP.Party_ID				AS Party_ID,
	client.Formato			AS FORMATO,
	client.Canal			AS CANAL,
	OOHA.PRICING_DATE		AS [FECHA OC],
	OOHA.ATTRIBUTE6			AS [FECHA ENTREGA],
	OOHA.ATTRIBUTE1			AS [FECHA CANCELACION],
	OOLA.LINE_NUMBER		AS LINEA,
	MSIB.SEGMENT1			AS SKU,
	MSIB.DESCRIPTION		AS DESCRIPCION,
	pro.[Unidad de Negocio]	AS FAMILIA,
	PRO.[Factor Conversion]	AS [Factor Conversion],
	Muc.CONVERSION_RATE		AS [Tarimas a cajas],
	OOLA.ORDER_QUANTITY_UOM	AS UDM,
	ISNULL(Muc.CONVERSION_RATE,	1) * (COALESCE(RCTL.QUANTITY_CREDITED, 0) + COALESCE(RCTL.QUANTITY_INVOICED, 0)) AS [CANTIDAD FACTURADA],
	ISNULL(Muc.CONVERSION_RATE,	1) * (OOLA.ORDERED_QUANTITY)	AS [CANTIDAD ORDENADA],
	ISNULL(Muc.CONVERSION_RATE,	1) * (OOLA.CANCELLED_QUANTITY)	AS	[CANTIDAD CANCELADA],
	--ISNULL(FND.LOOKUP_CODE, FND.LOOKUP_CODE) AS [CODIGO MOTIVO],
	--ISNULL(FND.DESCRIPTION, FND.DESCRIPTION) AS [MOTIVO CANCELACION],
	FND.LOOKUP_CODE AS CODIGO_MOTIVO,
	FND.DESCRIPTION AS MOTIVO_CANCELACION,
 
	TL.NAME					AS [TIPO PEDIDO],
	OOHA.CREATION_DATE		AS [FECHA CREACION],
	RCTA.TRX_NUMBER			AS FACTURA,
	RCTA.TRX_DATE			AS [FECHA FACTURA]
 
 
 
from
RA_CUSTOMER_TRX_ALL RCTA
LEFT JOIN RA_CUST_TRX_TYPES_ALL			RCTTA	ON RCTTA.CUST_TRX_TYPE_ID = RCTA.CUST_TRX_TYPE_ID  
LEFT JOIN RA_CUSTOMER_TRX_LINES_ALL		RCTL	ON RCTL.CUSTOMER_TRX_ID = RCTA.CUSTOMER_TRX_ID 
LEFT JOIN OE_ORDER_LINES_ALL			OOLA	ON OOLA.LINE_ID = RCTL.INTERFACE_LINE_ATTRIBUTE6
LEFT JOIN OE_ORDER_HEADERS_ALL			OOHA	ON OOHA.HEADER_ID = OOLA.HEADER_ID
LEFT JOIN OE_TRANSACTION_TYPES_TL		TL		ON TL.TRANSACTION_TYPE_ID = OOHA.ORDER_TYPE_ID and TL.LANGUAGE = 'ESA'
LEFT JOIN MTL_SYSTEM_ITEMS_B			MSIB	ON MSIB.INVENTORY_ITEM_ID	= RCTL.INVENTORY_ITEM_ID AND MSIB.ORGANIZATION_ID = 101
LEFT JOIN HR_ALL_ORGANIZATION_UNITS		HAOU	ON HAOU.ORGANIZATION_ID = OOLA.SHIP_FROM_ORG_ID
LEFT JOIN HZ_CUST_SITE_USES_ALL			HCSUA	ON HCSUA.SITE_USE_ID = OOHA.SHIP_TO_ORG_ID 
LEFT JOIN HZ_CUST_ACCT_SITES_ALL		HCAS	ON HCAS.CUST_ACCT_SITE_ID = HCSUA.CUST_ACCT_SITE_ID 
LEFT JOIN HZ_PARTY_SITES				HPS		ON HPS.PARTY_SITE_ID = HCAS.PARTY_SITE_ID
left JOIN HZ_PARTIES					HP		ON HP.PARTY_ID = HPS.PARTY_ID 
left JOIN HZ_CUST_SITE_USES_ALL			HCSUAF	ON HCSUAF.SITE_USE_ID = OOHA.INVOICE_TO_ORG_ID 
left JOIN HZ_CUST_ACCT_SITES_ALL		HCASF   ON HCASF.CUST_ACCT_SITE_ID = HCSUAF.CUST_ACCT_SITE_ID 
Left JOIN HZ_PARTY_SITES				HPSF    ON HPSF.PARTY_SITE_ID = HCASF.PARTY_SITE_ID 
left JOIN HZ_PARTIES					HPF		ON HPF.PARTY_ID = HPSF.PARTY_ID 
left JOIN HZ_CUST_ACCOUNTS				HCA		ON HCA.CUST_ACCOUNT_ID = HCAS.CUST_ACCOUNT_ID 
Left Join [PICO_VENTAS].[dbo].[clientes] client On client.[No_] = HPS.PARTY_SITE_NUMBER
left Join [PICO_VENTAS].[dbo].[productos] pro 	ON pro.[No_] = MSIB.SEGMENT1
Left Join MTL_UOM_CONVERSIONS			MUC		On Muc.[UOM_CODE] = RCTL.UOM_CODE and Muc.[INVENTORY_ITEM_ID] = RCTL.[INVENTORY_ITEM_ID]
LEFT JOIN FND_LOOKUP_VALUES				FND		ON FND.LOOKUP_CODE= RCTA.REASON_CODE AND FND.LANGUAGE = 'ESA' AND FND.VIEW_APPLICATION_ID = RCTA.PROGRAM_APPLICATION_ID AND FND.DESCRIPTION IS NOT NULL
 
 
 
where (RCTL.QUANTITY_CREDITED IS NOT NULL OR RCTL.QUANTITY_INVOICED IS NOT NULL)
and CONVERT(DATETIME, CONVERT(DATE, OOHA.CREATION_DATE)) > '01-01-2022'

and RCTA.ORG_ID = 81
AND OOHA.ORG_ID = 81
 
 
UNION
 
 

 
SELECT DISTINCT 
	OOHA.HEADER_ID,
	OOLA.CUST_PO_NUMBER			AS		OCC,
	OOHA.ORDER_NUMBER			AS		[No PEDIDO ORACLE],
	HAOU.NAME					AS		ALMACEN,
	HPSF.PARTY_SITE_NUMBER		AS		CLIENTE_FACTURACION,
    HPS.PARTY_SITE_NUMBER		AS		CLIENTE_ENTREGA,
    HP.PARTY_NAME				AS		CLIENTE,
	HP.Party_ID					AS		Party_ID,
	client.Formato				AS		FORMATO,
	client.Canal				AS		CANAL,
	OOHA.PRICING_DATE			AS		[FECHA OC],
	OOHA.ATTRIBUTE6				AS		[FECHA ENTREGA],
	OOHA.ATTRIBUTE1				AS		[FECHA CANCELACION],
	OOLA.LINE_NUMBER			AS		LINEA,
	MSIB.SEGMENT1				AS		SKU,
	MSIB.DESCRIPTION			AS		DESCRIPCION,
	pro.[Unidad de Negocio]		AS		FAMILIA,
	PRO.[Factor Conversion]		AS		[Factor Conversion],
	Muc.CONVERSION_RATE			AS [Tarimas a cajas],
	OOLA.ORDER_QUANTITY_UOM	AS UDM,
	NULL						AS		[CANTIDAD FACTURADA],
	NULL						AS		[CANTIDAD ORDENADA],
	ISNULL(Muc.CONVERSION_RATE,	1) * (OOLA.CANCELLED_QUANTITY)	AS	[CANTIDAD CANCELADA],
	FND.LOOKUP_CODE				AS		[CODIGO MOTIVO],
	FND.DESCRIPTION				AS		[MOTIVO CANCELACION],
 
 
 
	TL.NAME						AS		[TIPO PEDIDO],
	OOLA.CREATION_DATE			AS		[FECHA_CREACION],
	NULL						AS		FACTURA,
	NULL						AS		[FECHA FACTURA]
 
 

 
 
FROM OE_ORDER_LINES_ALL OOLA
LEFT JOIN OE_ORDER_HEADERS_ALL			OOHA	ON OOHA.HEADER_ID = OOLA.HEADER_ID
LEFT JOIN MTL_SYSTEM_ITEMS_B			MSIB	ON MSIB.INVENTORY_ITEM_ID	= OOLA.INVENTORY_ITEM_ID AND MSIB.ORGANIZATION_ID = 101
left JOIN OE_TRANSACTION_TYPES_TL		TL		ON TL.TRANSACTION_TYPE_ID = OOHA.ORDER_TYPE_ID and TL.LANGUAGE = 'ESA'
LEFT JOIN HR_ALL_ORGANIZATION_UNITS		HAOU	ON HAOU.ORGANIZATION_ID = OOLA.SHIP_FROM_ORG_ID
LEFT JOIN HZ_CUST_SITE_USES_ALL			HCSUA	ON HCSUA.SITE_USE_ID = OOHA.SHIP_TO_ORG_ID 
LEFT JOIN HZ_CUST_ACCT_SITES_ALL		HCAS	ON HCAS.CUST_ACCT_SITE_ID = HCSUA.CUST_ACCT_SITE_ID 
LEFT JOIN HZ_PARTY_SITES				HPS		ON HPS.PARTY_SITE_ID = HCAS.PARTY_SITE_ID
left JOIN HZ_PARTIES					HP		ON HP.PARTY_ID = HPS.PARTY_ID 
left JOIN HZ_CUST_SITE_USES_ALL			HCSUAF	ON HCSUAF.SITE_USE_ID = OOHA.INVOICE_TO_ORG_ID 
left JOIN HZ_CUST_ACCT_SITES_ALL		HCASF   ON HCASF.CUST_ACCT_SITE_ID = HCSUAF.CUST_ACCT_SITE_ID 
Left JOIN HZ_PARTY_SITES				HPSF    ON HPSF.PARTY_SITE_ID = HCASF.PARTY_SITE_ID 
left JOIN HZ_PARTIES					HPF		ON HPF.PARTY_ID = HPSF.PARTY_ID 
left JOIN HZ_CUST_ACCOUNTS				HCA		ON HCA.CUST_ACCOUNT_ID = HCAS.CUST_ACCOUNT_ID 
Left Join [PICO_VENTAS].[dbo].[clientes] client On client.[No_] = HPS.PARTY_SITE_NUMBER
left Join [PICO_VENTAS].[dbo].[productos] pro 	ON pro.[No_] = MSIB.SEGMENT1
Left Join MTL_UOM_CONVERSIONS			MUC		On Muc.[UOM_CODE] = OOLA.ORDER_QUANTITY_UOM and Muc.[INVENTORY_ITEM_ID] = OOLA.[INVENTORY_ITEM_ID]
LEFT JOIN OE_REASONS					REA		On REA.HEADER_ID = OOHA.HEADER_ID AND REA.ENTITY_ID = OOLA.LINE_ID
inner JOIN FND_LOOKUP_VALUES			FND		ON FND.LOOKUP_CODE = REA.REASON_CODE AND FND.LANGUAGE = 'ESA'  AND FND.LOOKUP_TYPE = 'CANCEL_CODE'
 
 
WHERE OOLA.FLOW_STATUS_CODE = 'CANCELLED'
and OOLA.ORG_ID = 81
and CONVERT(DATETIME, CONVERT(DATE, OOHA.CREATION_DATE)) > '01-01-2022'
    
    
    
    """
    with engine.connect() as connection:
        return pd.read_sql(query, connection)

df = obtener_datos()


  # Asegurar que fecha sea datetime
df['FECHA CREACION'] = pd.to_datetime(df['FECHA CREACION'])

# --- Sidebar ---
st.sidebar.image('https://cdn-icons-png.flaticon.com/512/483/483361.png', width=50)
st.sidebar.title('Título Sidebar')
st.sidebar.header("⚙️ Configurar filtros")

# --- Filtros ---
años = sorted(df['FECHA CREACION'].dt.year.unique())
meses = sorted(df['FECHA CREACION'].dt.month.unique())
almacenes = sorted(df['ALMACEN'].unique())
clientes = sorted(df['CLIENTE'].fillna('Sin cliente').unique())
familia = sorted(df['FAMILIA'].unique())

fil_año = st.sidebar.selectbox('Año', options=años, index=0)
fil_mes = st.sidebar.selectbox('Mes', options=meses, index=0)

opciones_almacenes = ["Todos"] + almacenes
opciones_clientes = ["Todos"] + clientes
opciones_familia = ["Todos"] + familia

fil_al = st.sidebar.multiselect('Almacen', options=opciones_almacenes, default="Todos")
fil_cli = st.sidebar.multiselect('Clientes', options=opciones_clientes, default="Todos")
fil_fa = st.sidebar.multiselect('Familia', options=opciones_familia, default="Todos")

# --- Filtro de datos ---
df_filtrado = df.copy()

if fil_año:
    df_filtrado = df_filtrado[df_filtrado['FECHA CREACION'].dt.year == fil_año]

if fil_mes:
    df_filtrado = df_filtrado[df_filtrado['FECHA CREACION'].dt.month == fil_mes]

if "Todos" not in fil_al:
    df_filtrado = df_filtrado[df_filtrado['ALMACEN'].isin(fil_al)]

if "Todos" not in fil_cli:
    df_filtrado = df_filtrado[df_filtrado['CLIENTE'].isin(fil_cli)]

if "Todos" not in fil_fa:
    df_filtrado = df_filtrado[df_filtrado['FAMILIA'].isin(fil_fa)]

# --- Cálculo de métricas ---
cantidad_facturada = df_filtrado['CANTIDAD FACTURADA'].fillna(0).astype(int).sum()
cantidad_ordenes = df_filtrado['CANTIDAD ORDENADA'].fillna(0).astype(int).sum()
cantidad_cancelada = df_filtrado['CANTIDAD CANCELADA'].fillna(0).astype(int).sum()

cantidad_total = cantidad_ordenes + cantidad_cancelada

if cantidad_total > 0:
    porcentaje_facturado = round((cantidad_facturada / cantidad_total) * 100, 2)
else:
    porcentaje_facturado = 0

# --- Mostrar gráfico de dona en Sidebar ---
st.sidebar.subheader("% Cantidad")
grafico_dona = donut_plotly(porcentaje_facturado,'blue')
st.sidebar.plotly_chart(grafico_dona, use_container_width=True)

# --- Métricas principales ---
col1, col2, col3 = st.columns(3)

col1.metric("CANTIDAD DE FACTURAS", f"{cantidad_facturada:,}")
col2.metric("CANTIDAD DE ORDENES", f"{cantidad_ordenes:,}")
col3.metric("CANTIDAD DE CANCELACIONES", f"{cantidad_cancelada:,}")

# --- Vista previa de datos ---
with st.expander('Vista previa de los datos filtrados'):
    st.dataframe(df_filtrado)
    
    
# --- Top 10 clientes por CANTIDAD ORDENADA ---
top_clientes = (
    df_filtrado.groupby('CLIENTE')['CANTIDAD ORDENADA']
    .sum()
    .reset_index()
    .sort_values(by='CANTIDAD ORDENADA', ascending=False)
    .head(10)
)
# --- Crear gráfico de barras ---
fig_top_clientes = px.bar(
    top_clientes,
    x='CLIENTE',
    y='CANTIDAD ORDENADA',
    color='CLIENTE',  # Cada barra diferente color automáticamente
    #title="Top 10 Clientes por Cantidad Ordenada",
    text='CANTIDAD ORDENADA',  # Mostrar valor encima de la barra
    labels={'CANTIDAD ORDENADA': 'Cantidad Ordenada', 'CLIENTE': 'Cliente'}
)

# Ajustes de diseño para que se vea más limpio
fig_top_clientes.update_layout(
    xaxis_tickangle=-45,
    showlegend=False,
    plot_bgcolor='white',
    margin=dict(t=30, l=10, r=10, b=10),
    height=500
)

fig_top_clientes.update_traces(
    texttemplate='%{text:.2s}',  # Texto encima de la barra
    textposition='outside'
)

# --- Mostrar el gráfico ---
st.markdown("<h3 style='text-align: center;'>📊 Top 10 Clientes por Cantidad Ordenada</h3>", unsafe_allow_html=True)
st.plotly_chart(fig_top_clientes, use_container_width=True)