import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from urllib.parse import urlencode
import requests
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build


# --- Configurar página ---
st.set_page_config(
    page_title="Dashboard Pedidos Cancelados",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Leer secretos ---
AUTH0_CLIENT_ID = st.secrets["auth0"]["client_id"]
AUTH0_CLIENT_SECRET = st.secrets["auth0"]["client_secret"]
AUTH0_DOMAIN = st.secrets["auth0"]["domain"]
REDIRECT_URI = "https://dash-down-drag-csv-file.streamlit.app/"

# --- URLs de Auth0 ---
AUTH0_AUTHORIZE_URL = f"https://{AUTH0_DOMAIN}/authorize"
AUTH0_TOKEN_URL = f"https://{AUTH0_DOMAIN}/oauth/token"
AUTH0_USERINFO_URL = f"https://{AUTH0_DOMAIN}/userinfo"
AUTH0_LOGOUT_URL = f"https://{AUTH0_DOMAIN}/v2/logout"

# --- Función para construir URL de login ---
def build_login_url():
    return AUTH0_AUTHORIZE_URL + "?" + urlencode({
        "response_type": "code",
        "client_id": AUTH0_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid profile email",
    })

# --- Función para obtener el token de acceso ---
def get_token(code):
    data = {
        "grant_type": "authorization_code",
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
    response = requests.post(AUTH0_TOKEN_URL, data=data)
    return response.json()

# --- Función para obtener el perfil del usuario ---
def get_user_info(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(AUTH0_USERINFO_URL, headers=headers)
    return response.json()

# --- Autenticación manual ---
code = st.query_params.get("code")

if "user" not in st.session_state and code:
    token_data = get_token(code)
    access_token = token_data.get("access_token")
    if access_token:
        user_info = get_user_info(access_token)
        st.session_state.user = user_info
        st.query_params.clear()  # Limpia parámetros en URL tras login


# --- Si no estás autenticado, muestra login ---
if "user" not in st.session_state:
    
    st.title("Bienvenido al Dashboard de Pedidos Cancelados")
    st.markdown("Para acceder, inicia sesión con el siguiente botón:")
    login_url = build_login_url()
    st.markdown(f"[🔐 Iniciar sesión con Auth0]({login_url})", unsafe_allow_html=True)
    st.stop()

# --- Botón cerrar sesión ---
logout_url = AUTH0_LOGOUT_URL + "?" + urlencode({
    "returnTo": REDIRECT_URI,
    "client_id": AUTH0_CLIENT_ID
})



with st.sidebar:
    
    if "user" in st.session_state:
        st.markdown(f"""
    <div style='display: flex; flex-direction: column; align-items: center;'>
        <img src="{st.session_state.user['picture']}" 
             style="border-radius: 50%; width: 100px; height: 100px; object-fit: cover;"/>
        <p style='margin-top: 10px; font-weight: bold;'>{st.session_state.user['name']}</p>
    </div>
""", unsafe_allow_html=True)
    
    if st.button("Cerrar sesión", use_container_width=True):
        st.markdown(f'<meta http-equiv="refresh" content="0;URL=\'{logout_url}\'" />', unsafe_allow_html=True)
    

# --- Mostrar mensaje de bienvenida temporal ---
if "welcome_shown" not in st.session_state:
    welcome_placeholder = st.empty()
    welcome_placeholder.success(f"Bienvenido, {st.session_state.user['name']} 👋")
    time.sleep(5)
    welcome_placeholder.empty()
    st.session_state.welcome_shown = True  # Evita que vuelva a mostrarse

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

#Configuración
SERVICE_ACCOUNT_FILE = st.secrets['json_file'] # Actualiza esta ruta
SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_ID = st.secrets["drive"]["folder_id"]  # Asegúrate de que sea el correcto

# Autenticación
credentials = service_account.Credentials.from_service_account_info(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

# Obtener archivo único en la carpeta
def get_single_file_id(service, folder_id):
    query = f"'{folder_id}' in parents and trashed = false"
    result = service.files().list(q=query, fields="files(id, name)").execute()
    files = result.get('files', [])
    
    if not files:
        return None, "❌ No hay archivos en la carpeta."
    elif len(files) > 1:
        return None, "⚠️ Hay más de un archivo en la carpeta."
    else:
        return files[0]['id'], files[0]['name']

# Streamlit UI
st.title("📁 Descarga de Archivo desde Google Drive")

file_id, message = get_single_file_id(drive_service, FOLDER_ID)

if file_id:
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    st.success(f"Archivo disponible: {message}")
    st.markdown(
        f"""
        <a href="{download_url}" target="_blank">
            <button style="
                background-color:#4CAF50;
                color:white;
                padding:10px 16px;
                border:none;
                border-radius:5px;
                cursor:pointer;
                font-size:16px;">
                Descargar archivo
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )
else:
    st.warning(message)


# --- Cargar archivo CSV ---
st.header("📁 Subir archivo CSV")

uploaded_file = st.file_uploader("Arrastra aquí tu archivo CSV", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("✅ Archivo cargado correctamente.")
    except Exception as e:
        st.error(f"❌ Error al leer el archivo CSV: {e}")
        st.stop()
else:
    st.warning("⚠️ Por favor, sube un archivo CSV para continuar.")
    st.stop()

  # Asegurar que fecha sea datetime
df['FECHA CREACION'] = pd.to_datetime(df['FECHA CREACION'])

# --- Sidebar ---
#st.sidebar.title('Título Sidebar')
#st.sidebar.image('https://iscam.com/wp-content/uploads/2023/11/Logo-Pinsa.png', width=100)
st.sidebar.markdown("<img src='https://iscam.com/wp-content/uploads/2023/11/Logo-Pinsa.png' width='100' style='display: block; margin: 0 auto;'>" , unsafe_allow_html=True)
st.sidebar.header("⚙️ Configurar filtros")

# --- Filtros ---
años = sorted(df['FECHA CREACION'].dt.year.unique())
meses = sorted(df['FECHA CREACION'].dt.month.unique())
almacenes = sorted(df['ALMACEN'].unique())
clientes = sorted(df['CLIENTE'].fillna('Sin cliente').unique())
familia = sorted(df['FAMILIA'].unique())

fil_año = st.sidebar.selectbox('Año', options=años, index=len(años) - 1)
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
# --- Métricas secundarias orientacion  ---
col1, col2 = st.columns(2)

col1.metric("AÑO", f"{fil_año:}")
col2.metric("MES", f"{fil_mes:}")

# --------SE MUESTRA EL GRAFICO DE BARRAS CON LOS TOP 10 CLIENTES--------------#
st.plotly_chart(fig_top_clientes, use_container_width=True)