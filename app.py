import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Sistema de Cubagem Afranio", layout="wide")

st.title("🪵 Sistema de Cubagem de Eucalipto")
st.subheader("Processamento de Amostras Diárias")

# Inicializa o estado (a memória do dia)
if 'todos_diametros' not in st.session_state:
    st.session_state.todos_diametros = []
if 'fotos_processadas' not in st.session_state:
    st.session_state.fotos_processadas = 0

# --- BARRA LATERAL: Configurações ---
st.sidebar.header("Configurações")
pixels_por_cm = st.sidebar.slider("Calibração (Pixels/cm):", 1.0, 20.0, 5.2, 0.1)

# --- ÁREA DE INPUT ---
st.markdown("### 1. Coleta de Amostras (Ao longo do dia)")
arquivo_foto = st.file_uploader("Arraste a foto da pilha (topo das toras):", type=["jpg", "png"])

if arquivo_foto:
    if st.button("Processar Foto e Adicionar à Média"):
        imagem_pil = Image.open(arquivo_foto)
        imagem_np = np.array(imagem_pil)
        cinza = cv2.cvtColor(imagem_np, cv2.COLOR_RGB2GRAY)
        suavizada = cv2.GaussianBlur(cinza, (9, 9), 2)
        
        circulos = cv2.HoughCircles(suavizada, cv2.HOUGH_GRADIENT, 1.2, 40, param1=50, param2=30, minRadius=15, maxRadius=80)
        
        if circulos is not None:
            circulos = np.round(circulos[0, :]).astype("int")
            for (x, y, raio) in circulos:
                st.session_state.todos_diametros.append((raio * 2) / pixels_por_cm)
            st.session_state.fotos_processadas += 1
            st.success(f"Foto {st.session_state.fotos_processadas} processada! Toras acumuladas: {len(st.session_state.todos_diametros)}")
        else:
            st.error("Não detectei toras. Ajuste a calibração ou a foto.")

# --- FECHAMENTO DO DIA ---
st.markdown("---")
st.markdown("### 2. Fechamento do Dia")
col_a, col_b = st.columns(2)
total_toras_dia = col_a.number_input("Total de toras serradas no dia:", min_value=0, value=4000)
comprimento_m = col_b.number_input("Comprimento padrão (m):", min_value=0.5, value=3.0)

if st.button("CALCULAR VOLUME TOTAL DO DIA"):
    if len(st.session_state.todos_diametros) > 0:
        media_geral = np.mean(st.session_state.todos_diametros)
        area_media = (3.14159 * (media_geral / 100) ** 2) / 4
        volume_total = area_media * comprimento_m * total_toras_dia
        
        st.metric("Volume Final (m³)", f"{volume_total:.2f} m³")
        st.write(f"Baseado em {len(st.session_state.todos_diametros)} toras medidas em {st.session_state.fotos_processadas} fotos.")
        
        # Gerar CSV para download
        df_final = pd.DataFrame({'Diametros_Medidos': st.session_state.todos_diametros})
        st.download_button("Baixar Relatório do Dia (CSV)", df_final.to_csv(), "relatorio_diario.csv")
    else:
        st.warning("Nenhuma foto processada hoje.")

if st.button("Limpar dados do dia"):
    st.session_state.todos_diametros = []
    st.session_state.fotos_processadas = 0
    st.rerun()
