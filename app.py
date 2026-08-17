
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pandas as pd
from datetime import datetime
from io import BytesIO
from streamlit_cropper import st_cropper

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
st.subheader("Controle Inteligente e Filtragem Avançada de Falsos Círculos")

# --- INICIALIZAÇÃO DE VARIÁVEIS NA MEMÓRIA ---
if 'todos_diametros' not in st.session_state:
    st.session_state.todos_diametros = []
if 'fotos_processadas' not in st.session_state:
    st.session_state.fotos_processadas = 0
if 'historico_fechamentos' not in st.session_state:
    st.session_state.historico_fechamentos = []

# --- ÁREA DE INPUT: COLETA DE AMOSTRAS E CROP DA RÉGUA ---
st.markdown("---")
st.markdown("### 1. Selecione a foto e delimite a régua diretamente na imagem")
arquivo_foto = st.file_uploader("Arraste ou selecione a foto da pilha com a régua (JPG/PNG):", type=["jpg", "jpeg", "png"])

escala_pixels_cm = 5.2

if arquivo_foto:
    imagem_pil = Image.open(arquivo_foto)
    
    st.info("👇 **Como calibrar:** Arraste a caixa de seleção abaixo cobrindo exatamente a régua de referência (do 0cm na base até o 50cm no topo).")
    
    box_recorte = st_cropper(
        imagem_pil, 
        realtime_update=True, 
        box_color='#FF0000', 
        aspect_ratio=None,
        key="recorte_regua"
    )
    
    altura_pixels_regua = box_recorte.height
    
    if altura_pixels_regua > 10:
        escala_pixels_cm = altura_pixels_regua / 50.0
        st.success(f"📏 Altura da régua selecionada: **{altura_pixels_regua} pixels**\n\n🎯 **Escala Exata Aplicada: {escala_pixels_cm:.2f} pixels/cm**")
    else:
        st.warning("⚠️ Selecione uma área maior cobrindo a régua na foto.")

    if st.button("Processar Foto e Adicionar à Amostra"):
        if altura_pixels_regua <= 10:
            st.error("Por favor, delimite a régua corretamente na foto antes de processar.")
        else:
            imagem_np = np.array(imagem_pil)
            if len(imagem_np.shape) == 3 and imagem_np.shape[2] == 4:
                imagem_np = cv2.cvtColor(imagem_np, cv2.COLOR_RGBA2BGR)
                cinza = cv2.cvtColor(imagem_np, cv2.COLOR_RGB2GRAY)
            elif len(imagem_np.shape) == 3:
                cinza = cv2.cvtColor(imagem_np, cv2.COLOR_RGB2GRAY)
            else:
                cinza = imagem_np
                
            suavizada = cv2.GaussianBlur(cinza, (13, 13), 3)
            
            # Parâmetros endurecidos para evitar contagens em excesso (falsos positivos)
            circulos = cv2.HoughCircles(
                suavizada, cv2.HOUGH_GRADIENT, dp=1.4, minDist=65, 
                param1=80, param2=45, minRadius=22, maxRadius=110
            )
            
            if circulos is not None:
                circulos = np.round(circulos[0, :]).astype("int")
                diametros_esta_foto = []
                
                for (x, y, raio) in circulos:
                    d_cm = (raio * 2) / escala_pixels_cm
                    
                    # Filtro estrito: Apenas toras comerciais reais entre 14 cm e 42 cm
                    if 14.0 <= d_cm <= 42.0:
                        # Verificação adicional de textura interna (peneira de falsos positivos)
                        # Garante que o centro do círculo possui variação de pixels (não é sombra pura)
                        try:
                            mask_tora = np.zeros(cinza.shape, dtype=np.uint8)
                            cv2.circle(mask_tora, (x, y), int(raio * 0.6), 255, -1)
                            media_interno = cv2.mean(cinza, mask=mask_tora)[0]
                            
                            # Se o miolo não for completamente preto (sombra) ou branco estourado, aceita a tora
                            if 20 < media_interno < 235:
                                diametros_esta_foto.append(d_cm)
                                st.session_state.todos_diametros.append(d_cm)
                        except Exception:
                            # Fallback caso a máscara ultrapasse os limites da imagem
                            diametros_esta_foto.append(d_cm)
                            st.session_state.todos_diametros.append(d_cm)
                
                if len(diametros_esta_foto) > 0:
                    st.session_state.fotos_processadas += 1
                    media_foto = np.mean(diametros_esta_foto)
                    
                    st.success(f"Foto processada com sucesso! {len(diametros_esta_foto)} toras validadas.")
                    st.markdown(f"**Média de diâmetro desta foto:** `{media_foto:.1f} cm`")
                    df_foto_atual = pd.DataFrame({
                        "Tora #": range(1, len(diametros_esta_foto) + 1),
                        "Diâmetro (cm)": [round(d, 2) for d in diametros_esta_foto]
                    })
                    st.dataframe(df_foto_atual, hide_index=True)
                else:
                    st.warning("Nenhuma tora válida foi encontrada após a filtragem rigorosa.")
            else:
                st.error("Não foi possível detectar topos de toras claros. Verifique a iluminação.")

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
