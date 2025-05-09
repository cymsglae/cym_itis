import streamlit as st
import pandas as pd
import requests
import time
import io
import csv

st.set_page_config(page_title="Verificación de Especies con ITIS", layout="wide")

st.sidebar.title("Cargar archivo CSV")
archivo = st.sidebar.file_uploader("Sube tu archivo con especies", type=["csv"])

if archivo:
    try:
        # Leer el archivo como texto
        content = archivo.read().decode("utf-8", errors="ignore")

        # Detectar el delimitador
        dialect = csv.Sniffer().sniff(content.splitlines()[0])
        delimiter = dialect.delimiter

        # Leer el DataFrame, ignorando filas mal formateadas
        df = pd.read_csv(io.StringIO(content), delimiter=delimiter, on_bad_lines='skip')
    except Exception as e:
        st.error(f"Error al leer el archivo CSV: {e}")
        st.stop()

    if "componente_biologico" in df.columns and "especie" in df.columns:
        componentes = df["componente_biologico"].dropna().unique()
        componente_seleccionado = st.sidebar.selectbox("Selecciona el componente biológico", componentes)

        df_filtrado = df[df["componente_biologico"] == componente_seleccionado].copy()

        st.write(f"### Resultados de comparación para componente: {componente_seleccionado}")

        resultados = []

        for nombre in df_filtrado["especie"].dropna().unique():
            nombre_limpio = nombre.replace(" sp.", "").replace(" cf.", "").replace(" aff.", "").strip()
            url = f"https://www.itis.gov/ITISWebService/jsonservice/searchByScientificName?srchKey={nombre_limpio}"
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data and isinstance(data, dict):
                            matches = data.get("scientificNames", [])
                            if matches:
                                resultados.append({"especie": nombre, "estado": "Coincide en ITIS", "nombre_encontrado": matches[0].get("combinedName", "")})
                            else:
                                resultados.append({"especie": nombre, "estado": "No encontrada en ITIS", "nombre_encontrado": None})
                        else:
                            resultados.append({"especie": nombre, "estado": "Respuesta no válida de ITIS", "nombre_encontrado": None})
                    except Exception as e:
                        resultados.append({"especie": nombre, "estado": f"Error de decodificación JSON: {str(e)}", "nombre_encontrado": None})
                else:
                    resultados.append({"especie": nombre, "estado": f"HTTP {response.status_code}", "nombre_encontrado": None})
            except Exception as e:
                resultados.append({"especie": nombre, "estado": f"Error de conexión: {str(e)}", "nombre_encontrado": None})

            time.sleep(0.5)  # Limitar a 2 llamadas por segundo

        df_resultado = pd.DataFrame(resultados)

        # Tarjeta de resumen
        total = len(df_resultado)
        encontradas = df_resultado[df_resultado["estado"] == "Coincide en ITIS"].shape[0]
        porcentaje = (encontradas / total * 100) if total > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total analizadas", total)
        col2.metric("Encontradas en ITIS", encontradas)
        col3.metric("% Coincidencia", f"{porcentaje:.1f}%")

        st.dataframe(df_resultado)

    else:
        st.error("El CSV debe tener las columnas 'componente_biologico' y 'especie'.")
else:
    st.sidebar.info("Sube un archivo CSV para comenzar.")
