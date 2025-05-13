import streamlit as st
from ftplib import FTP
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import io
from io import StringIO

# Configuración FTP
ftp_filepath = "meteos_data.dat"
local_filepath = "/tmp/meteos_data.dat"
spectra_filepath ="/tmp/Spectrum_D2.csv"
spectra_ftp = "Spectrum_D2.csv"

# Conectar al servidor FTP
ftp = FTP(st.secrets["ftp_host"])
ftp.login(st.secrets["ftp_user"], st.secrets["ftp_pass"])

# Descargar archivo DAT
with open(local_filepath, "wb") as file:
    ftp.retrbinary(f"RETR {ftp_filepath}", file.write)
with open(spectra_filepath, "wb") as file:
    ftp.retrbinary(f"RETR {spectra_ftp}", file.write)
ftp.quit()

# Leer archivo sin asumir encabezado y omitir posibles metadatos
with open(local_filepath, 'r', encoding='utf-8') as f:
    all_lines = f.readlines()

lineas_filtradas = [linea for linea in all_lines if len(linea.strip().split(',')) <= 13]

data = pd.read_csv(StringIO(''.join(lineas_filtradas)), header=4)

# Asignar nombres de columnas
data.columns = ["timestamp", "record", "batt_v", "Temperature", "%RH", "Wind Speed", "Wind Direction", "Peri", "Pira_tracker", "GH", "Pressure", "baro_temp", "PPFD"]  

# Eliminar filas no numéricas en timestamp
data = data[data["timestamp"].str.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", na=False)]

# Convertir timestamp a datetime
data["timestamp"] = pd.to_datetime(data["timestamp"], errors='coerce')

# Convertir columnas numéricas
cols_numeric = ["Temperature", "%RH", "Wind Speed", "Wind Direction", "Peri", "Pira_tracker", "GH", "Pressure", "baro_temp", "PPFD"]
data[cols_numeric] = data[cols_numeric].apply(pd.to_numeric, errors="coerce")

# Reemplazar valores nulos en las columnas clave por 0
data[["timestamp", "record", "batt_v", "Temperature", "%RH", "Wind Speed", "Wind Direction", 
      "Peri", "Pira_tracker", "GH", "Pressure", "baro_temp", "PPFD"]] = \
    data[["timestamp", "record", "batt_v", "Temperature", "%RH", "Wind Speed", "Wind Direction", 
          "Peri", "Pira_tracker", "GH", "Pressure", "baro_temp", "PPFD"]].fillna(0)

# Establecer índice de tiempo
data.set_index("timestamp", inplace=True)

st.set_page_config(layout="wide")

# Título
st.title("SDAES Meteo Station")

# Selección de fecha y hora de inicio y fin
min_date = data.index.min().date()
max_date = data.index.max().date()

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", min_value=min_date, max_value=max_date, value=min_date, key="start_date")
    start_time = st.time_input("Start Time", value=datetime.min.time(), key="start_time")
with col2:
    end_date = st.date_input("End Date", min_value=min_date, max_value=max_date, value=max_date, key="end_date")
    end_time = st.time_input("End Time", value=datetime.max.time(), key="end_time")

# Convertir a datetime
selected_start_datetime = datetime.combine(start_date, start_time)
selected_end_datetime = datetime.combine(end_date, end_time)

# Filtrar datos en el rango seleccionado
data_filtered = data[(data.index >= selected_start_datetime) & (data.index <= selected_end_datetime)]

# Create figure with secondary y-axis
fig1 = make_subplots(specs=[[{"secondary_y": True}]])

# Add traces
fig1.add_trace(
    go.Scatter(x=data_filtered.index, y=data_filtered["Temperature"], name="Temp (°C)"),
    secondary_y=False,
)

fig1.add_trace(
    go.Scatter(x=data_filtered.index, y=data_filtered["%RH"], name="RH (%)"),
    secondary_y=True,
)

# Set x-axis title
fig1.update_xaxes(title_text="Date & Time")

# Set y-axes titles
fig1.update_yaxes(title_text="Temperature (°C)", range=[-10,50], showgrid=False, secondary_y=False)
fig1.update_yaxes(title_text="Relative Humidity (%)", range=[0,100], showgrid=False, secondary_y=True)

press = make_subplots()

press.add_trace(
    go.Scatter(x=data_filtered.index, y=data_filtered["Pressure"], name="Pressure", line=dict(color="#9467bd"))
    )
press.update_xaxes(title_text="Date & Time")
press.update_yaxes(title_text="Pressure (hPa)", showgrid=False)

trh, pressure = st.columns([3,1], border=True)

with trh:
    st.subheader("Temperature and Relative Humidity")
    if not data_filtered.empty:
        st.plotly_chart(fig1)
        min_temp = data_filtered["Temperature"].min().round(2)
        max_temp = data_filtered["Temperature"].max().round(2)
        mean_temp = data_filtered["Temperature"].mean().round(2)

        left, middle, right = st.columns(3, border=True)

        with left:
            st.markdown("**Minimum Temperature**")
            st.text(f"{min_temp} °C")

        with middle:
            st.markdown("**Average Temperature**")
            st.text(f"{mean_temp} °C")

        with right:
            st.markdown("**Maximum Temperature**")
            st.text(f"{max_temp} °C")
    else:
        st.warning("No data available for date & time selected.")

with pressure:
    st.subheader("Barometric Pressure")
    if not data_filtered.empty:
        st.plotly_chart(press)
        
        press = st.container(border=True)
        
        mean_baro = data_filtered["Pressure"].mean().round(2)
        
        with press:
            st.markdown("**Average Pressure**")
            st.text(f"{mean_baro} hPa")
    else:
        st.warning("No data available for date & time selected.")
    
# Create figure with secondary y-axis
fig2 = make_subplots()
fig2.add_trace(
    go.Scatter(x=data_filtered.index, y=data_filtered["Wind Speed"], name="Wind Speed (m/s)", line=dict(color="#ff7f0e"))
    )

# Set x-axis title
fig2.update_xaxes(title_text="Date & Time")
fig2.update_yaxes(title_text="Wind Speed (m s-1)", showgrid=False)

# Contar la frecuencia de cada dirección única
direction_counts = data_filtered['Wind Direction'].round().value_counts().reset_index()
direction_counts.columns = ['Wind Direction', 'frequency']

# Ordenar los datos por dirección en escala ascendente
direction_counts = direction_counts.sort_values(by='Wind Direction').reset_index(drop=True)

# Crear el gráfico polar con Plotly Express
fig3 = px.line_polar(
    direction_counts,
    r='frequency',
    theta='Wind Direction',
    line_close=True
    )
fig3.update_traces(line=dict(color='#ff7f0e'))

speed, direct = st.columns(2, border=True)

with speed:
    st.subheader("Wind Speed")
    if not data_filtered.empty:
        st.plotly_chart(fig2)
    else:
        st.warning("No data available for date & time selected.")
with direct:
    st.subheader("Wind Direction")
    if not data_filtered.empty:
        st.plotly_chart(fig3)
    else:
        st.warning("No data available for date & time selected.")

fig4 = make_subplots(specs=[[{"secondary_y": True}]]) 
fig4.add_trace(go.Scatter(x=data_filtered.index, y=data_filtered["Peri"], name="Peri", line=dict(color="#d62728")))
fig4.add_trace(go.Scatter(x=data_filtered.index, y=data_filtered["Pira_tracker"], name="Pira", line=dict(color="#e377c2")))
fig4.update_xaxes(title_text="Date & Time")
fig4.update_yaxes(title_text="Peri & Pira (W m-2)", showgrid=False)

fig5 = make_subplots(specs=[[{"secondary_y": True}]]) 
fig5.add_trace(go.Scatter(x=data_filtered.index, y=data_filtered["GH"], name="GH", line=dict(color="#2ca02c")), secondary_y=False)
fig5.add_trace(go.Scatter(x=data_filtered.index, y=data_filtered["PPFD"], name="PPFD", line=dict(color="#bcbd22")), secondary_y=True)
fig5.update_xaxes(title_text="Date & Time")
fig5.update_yaxes(title_text="GH (W m-2)", range=[0,1500], showgrid=False, secondary_y=False)
fig5.update_yaxes(title_text="PPFD (μmol m-2 s-1)", range=[0,4000], showgrid=False, secondary_y=True)

sun1, sun2 = st.columns(2, border=True)

with sun1:
    st.subheader("Suntracked Solar Radiation")
    if not data_filtered.empty:
        st.plotly_chart(fig4)
        st.text("Since 30/04, data shown in Pira plot is GHI data and it is not suntracked.")
    else:
        st.warning("No data available for date & time selected.")
with sun2:
    st.subheader("Solar Radiation")
    if not data_filtered.empty:
        st.plotly_chart(fig5)
    else:
        st.warning("No data available for date & time selected.")

#--------------------------------------------------------------------------------------------------------------
# Leer archivo sin asumir encabezado y omitir posibles metadatos
with open(spectra_filepath, 'r', encoding='utf-8') as f:
    spectra_lines = f.readlines()

lineas_spectra = [linea for linea in spectra_lines if len(linea.strip().split(',')) <= 13]

spectra = pd.read_csv(StringIO(''.join(lineas_spectra)), header=4)

# Asignar nombres de columnas
spectra.columns = ["TIMESTAMP", "RECORD", "Timezone", "AmbientPressure", "AmbientTemperature", "InternalTemperature", "InternalHumidity", 
                "ChannelVoltage1", "ChannelVoltage2", "ChannelVoltage3", "ChannelVoltage4", "ChannelVoltage5", "ChannelVoltage6"]  

# Eliminar filas no numéricas en timestamp
spectra = spectra[spectra["TIMESTAMP"].str.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", na=False)]

# Convertir timestamp a datetime
spectra["TIMESTAMP"] = pd.to_datetime(spectra["TIMESTAMP"], errors='coerce')

# Convertir columnas numéricas
spectra_numeric = ["AmbientPressure", "AmbientTemperature", "InternalTemperature", "InternalHumidity", 
                "ChannelVoltage1", "ChannelVoltage2", "ChannelVoltage3", "ChannelVoltage4", "ChannelVoltage5", "ChannelVoltage6"]
spectra[spectra_numeric] = spectra[spectra_numeric].apply(pd.to_numeric, errors="coerce")

# Reemplazar valores nulos en las columnas clave por 0
spectra[["TIMESTAMP", "RECORD", "Timezone", "AmbientPressure", "AmbientTemperature", "InternalTemperature", "InternalHumidity", 
      "ChannelVoltage1", "ChannelVoltage2", "ChannelVoltage3", "ChannelVoltage4", "ChannelVoltage5", "ChannelVoltage6"]] = \
    spectra[["TIMESTAMP", "RECORD", "Timezone", "AmbientPressure", "AmbientTemperature", "InternalTemperature", "InternalHumidity", 
          "ChannelVoltage1", "ChannelVoltage2", "ChannelVoltage3", "ChannelVoltage4", "ChannelVoltage5", "ChannelVoltage6"]].fillna(0)

# Establecer índice de tiempo
spectra.set_index("TIMESTAMP", inplace=True)

st.subheader("Spectrometer Data")

# Selección de fecha y hora de inicio y fin
spec_min_date = spectra.index.min().date()
spec_max_date = spectra.index.max().date()

col1, col2 = st.columns(2)
with col1:
    spec_start_date = st.date_input("Start Date", min_value=spec_min_date, max_value=spec_max_date, value=spec_min_date, key="spec_start_date")
    spec_start_time = st.time_input("Start Time", value=datetime.min.time(), key="spec_start_time")
with col2:
    spec_end_date = st.date_input("End Date", min_value=spec_min_date, max_value=spec_max_date, value=spec_max_date, key="spec_end_date")
    spec_end_time = st.time_input("End Time", value=datetime.max.time(), key="spec_end_time")

# Convertir a datetime
spectra_selected_start_datetime = datetime.combine(spec_start_date, spec_start_time)
spectra_selected_end_datetime = datetime.combine(spec_end_date, spec_end_time)

# Filtrar datos en el rango seleccionado
spectra_filtered = spectra[(spectra.index >= spectra_selected_start_datetime) & (spectra.index <= spectra_selected_end_datetime)]

fig7 =  make_subplots()
fig7.add_trace(
    go.Scatter(x=spectra_filtered.index, y=spectra_filtered["AmbientPressure"], name="Amb. Press.", line=dict(color="#9467bd"))
    )
fig7.update_xaxes(title_text="Date & Time")
fig7.update_yaxes(title_text="Pressure (kPa)", showgrid=False)

fig8 = make_subplots(specs=[[{"secondary_y": True}]]) 
fig8.add_trace(go.Scatter(x=spectra_filtered.index, y=spectra_filtered["AmbientTemperature"], name="Amb. Temp.", line=dict(color="#2ca02c")))
fig8.add_trace(go.Scatter(x=spectra_filtered.index, y=spectra_filtered["InternalTemperature"], name="Int. Temp.", line=dict(color="#bcbd22")))
fig8.update_xaxes(title_text="Date & Time")
fig8.update_yaxes(title_text="Temperature (°C)", range=[0,50], showgrid=False)

fig9 =  make_subplots()
fig9.add_trace(
    go.Scatter(x=spectra_filtered.index, y=spectra_filtered["InternalHumidity"], name="Int. Hum.", line=dict(color="#ff7f0e"))
    )
fig9.update_xaxes(title_text="Date & Time")
fig9.update_yaxes(title_text="IH (%)", range=[0,100], showgrid=False)

spec1, spec2, spec3 = st.columns(3, border=True)

with spec1:
    st.subheader("Ambient and Internal Temperature")
    if not spectra_filtered.empty:
        st.plotly_chart(fig8)
    else:
        st.warning("No data available for date & time selected.")
with spec2:
    st.subheader("Ambient Pressure")
    if not spectra_filtered.empty:
        st.plotly_chart(fig7)
    else:
        st.warning("No data available for date & time selected.")
with spec3:
    st.subheader("Internal Humidity")
    if not spectra_filtered.empty:
        st.plotly_chart(fig9)
    else:
        st.warning("No data available for date & time selected.")
        
fig10 = make_subplots(specs=[[{"secondary_y": True}]]) 
fig10.add_trace(go.Scatter(x=spectra_filtered.index, y=spectra_filtered["ChannelVoltage1"], name="V1"))
fig10.add_trace(go.Scatter(x=spectra_filtered.index, y=spectra_filtered["ChannelVoltage2"], name="V2"))
fig10.add_trace(go.Scatter(x=spectra_filtered.index, y=spectra_filtered["ChannelVoltage3"], name="V3"))
fig10.add_trace(go.Scatter(x=spectra_filtered.index, y=spectra_filtered["ChannelVoltage4"], name="V4"))
fig10.add_trace(go.Scatter(x=spectra_filtered.index, y=spectra_filtered["ChannelVoltage5"], name="V5"))
fig10.add_trace(go.Scatter(x=spectra_filtered.index, y=spectra_filtered["ChannelVoltage6"], name="V6"))
fig10.update_xaxes(title_text="Date & Time")
fig10.update_yaxes(title_text="Voltage (mV)", showgrid=False)

spec4 = st.container(border=True)

with spec4:
    st.subheader("Channel Voltages")
    if not spectra_filtered.empty:
        st.plotly_chart(fig10)
    else:
        st.warning("No data available fr date & time selected.")

#--------------------------------------------------------------------------------------------------------------

# Definir la latitud y longitud del punto
lat = [41.6062055056575]
lon = [0.6245933114307467]

# Crear el mapa con Scattergeo
fig6 = go.Figure(go.Scattergeo(
    lon=lon,
    lat=lat,
    mode='markers',
    marker=dict(size=10, color='red'),
    name='Ubicación'
))

# Configurar el diseño del mapa
fig6.update_geos(
    projection_type="natural earth",
    landcolor="white",
    oceancolor="MidnightBlue",
    showocean=True,
    lakecolor="LightBlue"
)

def generate_csv():
    # Guardar en un buffer de memoria
    output = io.StringIO()
    data_filtered.to_csv(output, index=True)
    return output.getvalue()

csv_data = generate_csv()

position, download = st.columns(2, border=True)

with position:
    st.subheader("Where is our station?")
    st.plotly_chart(fig6)
with download:
    st.subheader("Want to get the data?")
    st.text("Are you interested in downloading our meteo data?")
    st.text("Click the 'Download' button to get our data on a .csv file")
    #st.download_button(
        #label="Download",
        #data=csv_data,
        #file_name="SDAES_meteo_data.csv",
        #mime="text/csv"
    #)
