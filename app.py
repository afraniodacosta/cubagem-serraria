
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pandas as pd
from datetime import datetime
from io import BytesIO

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
st.markdown("### 1. Coleta de Amostras (Ao longo do lote/dia)")
arquivo_foto = st.file_uploader("Arraste ou selecione a foto da pilha (topo das toras - JPG/PNG):", type=["jpg", "jpeg", "png"])

if arquivo_foto:
    imagem_pil = Image.open(arquivo_foto)
    st.image(imagem_pil, caption="Foto Carregada", width=400)
    
    if st.button("Processar Foto e Adicionar à Amostra"):
        imagem_np = np.array(imagem_pil)
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
            st.markdown(f"**Média de diâmetro desta foto:** `{media_foto:.1f} cm`")
            df_foto_atual = pd.DataFrame({
                "Tora #": range(1, len(diametros_esta_foto) + 1),
                "Diâmetro (cm)": [round(d, 2) for d in diametros_esta_foto]
            })
            st.dataframe(df_foto_atual, hide_index=True)
        else:
            st.error("Não foi possível detectar topos de toras claros. Ajuste a calibração na barra lateral ou use uma foto mais nítida.")

# --- FECHAMENTO DO LOTE ---
st.markdown("---")
st.markdown("### 2. Fechamento do Lote / Turno")
col_a, col_b = st.columns(2)
total_toras_dia = col_a.number_input("Total de toras serradas neste lote:", min_value=0, value=4000)
comprimento_m = col_b.number_input("Comprimento padrão das toras (m):", min_value=0.5, value=3.0)

if st.button("CALCULAR E GERAR CÓDIGO DO LOTE", type="primary"):
    if len(st.session_state.todos_diametros) > 0:
        media_geral = np.mean(st.session_state.todos_diametros)
        area_media = (3.14159 * (media_geral / 100) ** 2) / 4
        
        # Volume Medido Sólido (Convertido)
        volume_convertido = area_media * comprimento_m * total_toras_dia
        # Volume Estéreo Correspondente (multiplicado por 1.5)
        volume_estereo = volume_convertido * 1.5
        
        st.success("Cálculo realizado com sucesso!")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("M³ Estéreo", f"{volume_estereo:.2f} m³")
        col_m2.metric("M³ Medido (Sólido)", f"{volume_convertido:.2f} m³")
        col_m3.metric("Média Diâmetro", f"{media_geral:.1f} cm")
        col_m4.metric("Toras Amostradas", f"{len(st.session_state.todos_diametros)} un")
        
        data_hora_lote = datetime.now().strftime("%Y%m%d-%H%M")
        checksum_id = f"LOTE-{data_hora_lote}"
        
        texto_copia = f"ID: {checksum_id} | VOL: {volume_estereo:.2f} | DIAM: {media_geral:.1f} | TORAS: {total_toras_dia}"
        
        st.markdown("---")
        st.markdown("### 📋 Copie o código abaixo (Ctrl+C) para colar no sistema HTML:")
        st.code(texto_copia, language="text")
        
        # GERAÇÃO DE RELATÓRIO EM PDF SIMPLES UTILIZANDO REPORTLAB OU MATPLOTLIB/PANDAS SE NECESSÁRIO
        # Vamos estruturar o download CSV e um resumo executivo para download
        novo_registro = {
            "Data/Hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Comprimento (m)": comprimento_m,
            "Nº Toras": total_toras_dia,
            "Média Diâmetro (cm)": round(media_geral, 1),
            "M³ Medido (Sólido)": round(volume_convertido, 2),
            "M³ Estéreo": round(volume_estereo, 2)
        }
        st.session_state.historico_fechamentos.insert(0, novo_registro)
        if len(st.session_state.historico_fechamentos) > 5:
            st.session_state.historico_fechamentos.pop()
            
        df_final = pd.DataFrame({'Diametros_Medidos_Cm': st.session_state.todos_diametros})
        st.download_button("Baixar Relatório Detalhado (CSV)", df_final.to_csv(index=False), f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.csv")
        
        # GERAÇÃO DE PDF DO RESUMO DO LOTE
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, 750, "Kavaco Indústria - Relatório de Cubagem de Toras")
        p.setFont("Helvetica", 11)
        p.drawString(50, 720, f"ID do Lote: {checksum_id}")
        p.drawString(50, 700, f"Data e Hora: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        p.drawString(50, 680, f"Total de Toras Serradas: {total_toras_dia}")
        p.drawString(50, 660, f"Comprimento Padrão: {comprimento_m} m")
        p.drawString(50, 640, f"Média Geral de Diâmetro: {media_geral:.1f} cm")
        p.drawString(50, 620, f"Volume M³ Medido (Sólido): {volume_convertido:.2f} m³")
        p.drawString(50, 600, f"Volume M³ Estéreo: {volume_estereo:.2f} m³")
        p.showPage()
        p.save()
        buffer.seek(0)
        
        st.download_button(
            label="📄 Baixar Resumo do Lote (PDF)",
            data=buffer,
            file_name=f"resumo_lote_{data_hora_lote}.pdf",
            mime="application/pdf"
        )
    else:
        st.warning("Nenhuma foto foi processada para gerar o cálculo.")

if st.button("🔄 Reiniciar Amostras"):
    st.session_state.todos_diametros = []
    st.session_state.fotos_processadas = 0
    st.rerun()

# --- HISTÓRICO ---
st.markdown("---")
st.markdown("### 📊 Histórico dos Últimos Fechamentos")
if len(st.session_state.historico_fechamentos) > 0:
    df_historico = pd.DataFrame(st.session_state.historico_fechamentos)
    st.dataframe(df_historico, hide_index=True)
else:
    st.info("Nenhum fechamento registrado ainda nesta sessão.")
