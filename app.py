import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA E IDENTIDADE VISUAL ---
st.set_page_config(
    page_title="Kavaco Indústria - Controle de Toras",
    page_icon="🪵",
    layout="wide"
)

# Exibição do Logotipo da Empresa
col_logo1, col_logo2, col_logo3 = st.columns([2, 1, 2])
with col_logo2:
    try:
        # Carrega o logotipo enviado
        logo = Image.open("Kvaco Dark ICO.ico")
        st.image(logo, width=120)
    except Exception:
        pass

st.title("🪵 Kavaco Indústria - Sistema de Cubagem")
st.subheader("Controle Inteligente e Amostragem de Eucalipto")

# --- INICIALIZAÇÃO DE VARIÁVEIS NA MEMÓRIA ---
if 'todos_diametros' not in st.session_state:
    st.session_state.todos_diametros = []
if 'fotos_processadas' not in st.session_state:
    st.session_state.fotos_processadas = 0
if 'historico_fechamentos' not in st.session_state:
    st.session_state.historico_fechamentos = []

# --- BARRA LATERAL: Configurações ---
st.sidebar.header("⚙️ Configurações")
pixels_por_cm = st.sidebar.slider("Calibração (Pixels/cm):", 1.0, 20.0, 5.2, 0.1, help="Ajuste fino baseado na trena de referência.")

# --- ÁREA DE INPUT: COLETA DE AMOSTRAS ---
st.markdown("---")
st.markdown("### 1. Coleta de Amostras (Ao longo do dia)")
arquivo_foto = st.file_uploader("Arraste ou selecione a foto da pilha (topo das toras - JPG/PNG):", type=["jpg", "jpeg", "png"])

if arquivo_foto:
    imagem_pil = Image.open(arquivo_foto)
    st.image(imagem_pil, caption="Foto Carregada", width=400)
    
    if st.button("Processar Foto e Adicionar à Amostra"):
        imagem_np = np.array(imagem_pil)
        # Verifica se a imagem é RGB ou RGBA e converte corretamente para cinza
        if len(imagem_np.shape) == 3 and imagem_np.shape[2] == 4:
            imagem_np = cv2.cvtColor(imagem_np, cv2.COLOR_RGBA2BGR)
            cinza = cv2.cvtColor(imagem_np, cv2.COLOR_BGR2GRAY)
        elif len(imagem_np.shape) == 3:
            cinza = cv2.cvtColor(imagem_np, cv2.COLOR_RGB2GRAY)
        else:
            cinza = imagem_np
            
        suavizada = cv2.GaussianBlur(cinza, (9, 9), 2)
        
        circulos = cv2.HoughCircles(
            suavizada, cv2.HOUGH_GRADIENT, dp=1.2, minDist=40, 
            param1=50, param2=30, minRadius=15, maxRadius=80
        )
        
        if circulos is not None:
            circulos = np.round(circulos[0, :]).astype("int")
            diametros_esta_foto = []
            
            for (x, y, raio) in circulos:
                d_cm = (raio * 2) / pixels_por_cm
                diametros_esta_foto.append(d_cm)
                st.session_state.todos_diametros.append(d_cm)
                
            st.session_state.fotos_processadas += 1
            media_foto = np.mean(diametros_esta_foto)
            
            st.success(f"Foto processada com sucesso! {len(diametros_esta_foto)} toras detectadas.")
            
            # Apresentando os diâmetros e a média desta foto específica
            st.markdown(f"**Média de diâmetro desta foto:** `{media_foto:.1f} cm`")
            df_foto_atual = pd.DataFrame({
                "Tora #": range(1, len(diametros_esta_foto) + 1),
                "Diâmetro (cm)": [round(d, 2) for d in diametros_esta_foto]
            })
            st.dataframe(df_foto_atual, hide_index=True)
            
        else:
            st.error("Não foi possível detectar topos de toras claros. Ajuste a calibração na barra lateral ou use uma foto mais nítida.")

# --- FECHAMENTO DO DIA ---
st.markdown("---")
st.markdown("### 2. Fechamento do Dia")
col_a, col_b = st.columns(2)
total_toras_dia = col_a.number_input("Total de toras serradas no dia:", min_value=0, value=4000)
comprimento_m = col_b.number_input("Comprimento padrão das toras (m):", min_value=0.5, value=3.0)

if st.button("CALCULAR E SALVAR FECHAMENTO DO DIA", type="primary"):
    if len(st.session_state.todos_diametros) > 0:
        media_geral = np.mean(st.session_state.todos_diametros)
        area_media = (3.14159 * (media_geral / 100) ** 2) / 4
        volume_total = area_media * comprimento_m * total_toras_dia
        
        st.success("Fechamento calculado com sucesso!")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Volume Final do Dia", f"{volume_total:.2f} m³")
        col_m2.metric("Média Geral de Diâmetro", f"{media_geral:.1f} cm")
        col_m3.metric("Total de Toras Amostradas", f"{len(st.session_state.todos_diametros)} un")
        
        # Salva no histórico (mantém os últimos 5)
        novo_registro = {
            "Data": datetime.now().strftime("%d/%m/%Y"),
            "Comprimento (m)": comprimento_m,
            "Nº Toras Serradas": total_toras_dia,
            "Média Diâmetro (cm)": round(media_geral, 1),
            "Cubagem (m³)": round(volume_total, 2)
        }
        st.session_state.historico_fechamentos.insert(0, novo_registro)
        if len(st.session_state.historico_fechamentos) > 5:
            st.session_state.historico_fechamentos.pop()
            
        # Botão para baixar relatório do dia
        df_final = pd.DataFrame({'Diametros_Medidos_Cm': st.session_state.todos_diametros})
        st.download_button("Baixar Relatório Detalhado (CSV)", df_final.to_csv(index=False), f"relatorio_{datetime.now().strftime('%Y-%m-%d')}.csv")
    else:
        st.warning("Nenhuma foto foi processada hoje para gerar o cálculo.")

# Botão para limpar dados do dia corrente
if st.button("🔄 Reiniciar Amostras do Dia"):
    st.session_state.todos_diametros = []
    st.session_state.fotos_processadas = 0
    st.rerun()

# --- HISTÓRICO DOS 5 ÚLTIMOS FECHAMENTOS ---
st.markdown("---")
st.markdown("### 📊 Histórico dos Últimos Fechamentos Diários")
if len(st.session_state.historico_fechamentos) > 0:
    df_historico = pd.DataFrame(st.session_state.historico_fechamentos)
    st.dataframe(df_historico, hide_index=True)
else:
    st.info("Nenhum fechamento diário registrado ainda nesta sessão.")
