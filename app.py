
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
st.subheader("Controle Inteligente e Amostragem com Calibração Automática por Régua")

# --- INICIALIZAÇÃO DE VARIÁVEIS NA MEMÓRIA ---
if 'todos_diametros' not in st.session_state:
    st.session_state.todos_diametros = []
if 'fotos_processadas' not in st.session_state:
    st.session_state.fotos_processadas = 0
if 'historico_fechamentos' not in st.session_state:
    st.session_state.historico_fechamentos = []

# --- FUNÇÃO DE CALIBRAÇÃO EXATA BASEADA NA FITA DA RÉGUA (0 A 50 CM) ---
def detectar_regua_exata(imagem_bgr):
    """
    Filtra o papel branco vertical da régua de forma isolada, encontrando 
    com exatidão a altura em pixels entre o topo (50cm) e a base (0cm).
    """
    try:
        hsv = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2HSV)
        
        # Isola a faixa de branco da fita da régua
        lower_white = np.array([0, 0, 150])
        upper_white = np.array([180, 55, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        # Remove ruídos e fecha falhas
        kernel = np.ones((7, 7), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contornos, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        img_h, img_w = imagem_bgr.shape[:2]
        melhor_h = None
        max_area = 0

        for c in contornos:
            x, y, w, h = cv2.boundingRect(c)
            area = cv2.contourArea(c)
            
            # Filtros geométricos para garantir que estamos pegando a régua vertical na pilha
            # A altura deve ser consideravelmente maior que a largura e o objeto localizado na metade central
            if h > w * 2.0 and h > (img_h * 0.12) and area > max_area:
                # Confirma se o objeto tem proporção retangular vertical típica de uma régua
                if (x + w/2) > (img_w * 0.2) and (x + w/2) < (img_w * 0.8):
                    max_area = area
                    melhor_h = h

        if melhor_h:
            # A altura exata em pixels do retângulo branco corresponde exatamente a 50 cm reais
            pixels_por_cm_calculado = melhor_h / 50.0
            if 1.5 <= pixels_por_cm_calculado <= 35.0:
                return pixels_por_cm_calculado
    except Exception:
        pass
    return None

# --- BARRA LATERAL: Configurações ---
st.sidebar.header("⚙️ Configurações de Calibração")
calibracao_auto = st.sidebar.checkbox("Usar Detecção Automática da Régua", value=True, help="Identifica a régua na foto e calcula a escala sozinha.")
pixels_por_cm_manual = st.sidebar.slider("Calibração Manual (Pixels/cm):", 1.0, 20.0, 5.2, 0.1)

# --- ÁREA DE INPUT: COLETA DE AMOSTRAS ---
st.markdown("---")
st.markdown("### 1. Coleta de Amostras (Ao longo do lote/dia)")
arquivo_foto = st.file_uploader("Arraste ou selecione a foto da pilha com a régua posicionada (JPG/PNG):", type=["jpg", "jpeg", "png"])

if arquivo_foto:
    imagem_pil = Image.open(arquivo_foto)
    st.image(imagem_pil, caption="Foto Carregada com Régua de Referência", width=400)
    
    if st.button("Processar Foto e Adicionar à Amostra"):
        imagem_np = np.array(imagem_pil)
        if len(imagem_np.shape) == 3 and imagem_np.shape[2] == 4:
            imagem_np = cv2.cvtColor(imagem_np, cv2.COLOR_RGBA2BGR)
            cinza = cv2.cvtColor(imagem_np, cv2.COLOR_RGB2GRAY)
            bgr = imagem_np
        elif len(imagem_np.shape) == 3:
            cinza = cv2.cvtColor(imagem_np, cv2.COLOR_RGB2GRAY)
            bgr = cv2.cvtColor(imagem_np, cv2.COLOR_RGB2BGR)
        else:
            cinza = imagem_np
            bgr = cv2.cvtColor(cinza, cv2.COLOR_GRAY2BGR)
            
        # Determina o pixels_por_cm (Automático via Régua ou Manual)
        escala_pixels_cm = pixels_por_cm_manual
        if calibracao_auto:
            escala_detectada = detectar_regua_exata(bgr)
            if escala_detectada:
                escala_pixels_cm = escala_detectada
                st.success(f"📏 Régua calibrada com sucesso! Escala aplicada: `{escala_pixels_cm:.2f} pixels/cm`")
            else:
                st.warning("⚠️ Não foi possível isolar a régua automaticamente com precisão. Aplicando o valor manual da barra lateral como segurança.")

        suavizada = cv2.GaussianBlur(cinza, (9, 9), 2)
        
        circulos = cv2.HoughCircles(
            suavizada, cv2.HOUGH_GRADIENT, dp=1.2, minDist=40, 
            param1=50, param2=30, minRadius=15, maxRadius=80
        )
        
        if circulos is not None:
            circulos = np.round(circulos[0, :]).astype("int")
            diametros_esta_foto = []
            
            for (x, y, raio) in circulos:
                d_cm = (raio * 2) / escala_pixels_cm
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
            st.error("Não foi possível detectar topos de toras claros. Verifique a iluminação ou ajuste a calibração.")

# --- FECHAMENTO DO LOTE ---
st.markdown("---")
st.markdown("### 2. Fechamento do Lote / Turno")
col_a, col_b = st.columns(2)
total_toras_dia = col_a.number_input("Total de toras serradas neste lote:", min_value=0, value=4000)
comprimento_m = col_b.number_input("Comprimento padrão das toras (m):", min_value=0.5, value=2.20, step=0.1)

if st.button("CALCULAR E GERAR CÓDIGO DO LOTE", type="primary"):
    if len(st.session_state.todos_diametros) > 0:
        media_geral = np.mean(st.session_state.todos_diametros)
        area_media = (3.14159 * (media_geral / 100) ** 2) / 4
        
        volume_convertido = area_media * comprimento_m * total_toras_dia
        volume_estereo = volume_convertido * 1.5
        
        st.success("Cálculo realizado com sucesso!")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("M³ Estéreo", f"{volume_estereo:.2f} m³")
        col_m2.metric("M³ Medido (Sólido)", f"{volume_convertido:.2f} m³")
        col_m3.metric("Média Diâmetro", f"{media_geral:.1f} cm")
        col_m4.metric("Toras Amostradas", f"{len(st.session_state.todos_diametros)} un")
        
        data_hora_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        checksum_id = f"LOTE-{datetime.now().strftime('%Y%m%d-%H%M')}"
        
        texto_copia = f"ID: {checksum_id} | VOL: {volume_estereo:.2f} | DIAM: {media_geral:.1f} | TORAS: {total_toras_dia} | COMP: {comprimento_m:.2f}"
        
        st.markdown("---")
        st.markdown("### 📋 Copie o código abaixo (Ctrl+C) para colar no sistema HTML:")
        st.code(texto_copia, language="text")
        
        amostra_aleatoria = pd.Series(st.session_state.todos_diametros).sample(n=min(7, len(st.session_state.todos_diametros))).tolist()
        
        dados_relatorio = [
            ["RELATÓRIO DE CUBAGEM DE TORAS - KAVACO INDÚSTRIA", ""],
            ["Data / Hora do Fechamento:", data_hora_str],
            ["ID do Lote (Checksum):", checksum_id],
            ["Comprimento Padrão (m):", comprimento_m],
            ["Quantidade Total de Toras:", total_toras_dia],
            ["Média Geral de Diâmetro (cm):", round(media_geral, 1)],
            ["Volume M³ Medido (Sólido):", round(volume_convertido, 2)],
            ["Volume M³ Estéreo:", round(volume_estereo, 2)],
            ["", ""],
            ["AMOSTRA DE DIÂMETROS ALEATÓRIOS (CM)", ""]
        ]
        
        for idx, d in enumerate(amostra_aleatoria, 1):
            dados_relatorio.append([f"Amostra #{idx}", round(d, 2)])
            
        df_export = pd.DataFrame(dados_relatorio, columns=["Indicador / Parâmetro", "Resultado"])
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Resumo do Lote')
        excel_data = output.getvalue()
        
        novo_registro = {
            "Data/Hora": data_hora_str,
            "Comprimento (m)": comprimento_m,
            "Nº Toras": total_toras_dia,
            "Média Diâmetro (cm)": round(media_geral, 1),
            "M³ Medido (Sólido)": round(volume_convertido, 2),
            "M³ Estéreo": round(volume_estereo, 2)
        }
        st.session_state.historico_fechamentos.insert(0, novo_registro)
        if len(st.session_state.historico_fechamentos) > 5:
            st.session_state.historico_fechamentos.pop()
            
        st.download_button(
            label="📥 Baixar Relatório em Excel (.xlsx)", 
            data=excel_data, 
            file_name=f"relatorio_cubagem_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
