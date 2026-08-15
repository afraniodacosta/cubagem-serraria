
# No seu app.py, certifique-se de que o cálculo do volume gerado para o Ctrl+V siga a proporção exata:
if st.button("CALCULAR E GERAR CÓDIGO DO LOTE", type="primary"):
    if len(st.session_state.todos_diametros) > 0:
        media_geral = np.mean(st.session_state.todos_diametros)
        area_media = (3.14159 * (media_geral / 100) ** 2) / 4
        # Volume convertido real (sólido)
        volume_convertido = area_media * comprimento_m * total_toras_dia
        # Volume estéreo correspondente (multiplicado por 1.5 para equiparar à entrada)
        volume_estereo = volume_convertido * 1.5
        
        data_hora_lote = datetime.now().strftime("%Y%m%d-%H%M")
        checksum_id = f"LOTE-{data_hora_lote}"
        
        # O VOL enviado passa a ser o estéreo medido para bater com a tabela
        texto_copia = f"ID: {checksum_id} | VOL: {volume_estereo:.2f} | DIAM: {media_geral:.1f} | TORAS: {total_toras_dia}"
        
        st.markdown("---")
        st.markdown("### 📋 Copie o código abaixo (Ctrl+C) para colar no sistema HTML:")
        st.code(texto_copia, language="text")
