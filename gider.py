import streamlit as st
import sqlite3
import datetime
import pandas as pd

def goster(db_yolu):
    st.subheader("Gider ve Harcama Girişi")
    
    with st.form("gider_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            kat = st.selectbox("Harcama Kategorisi", ["Elektrik", "Su", "Maaş", "Bakım", "Temizlik", "Demirbaş", "Diğer"])
            t = st.number_input("Tutar (₺)", min_value=0.0)
        with col2:
            a = st.text_input("Açıklama")
            # --- TARİH SEÇİCİ (DTP) ---
            harcama_tarihi = st.date_input("Harcama Tarihi", datetime.date.today())
            
        if st.form_submit_button("💳 Kasadan Harca"):
            conn = sqlite3.connect(db_yolu)
            c = conn.cursor()
            c.execute("INSERT INTO giderler (tarih, kategori, tutar, aciklama) VALUES (?,?,?,?)", (str(harcama_tarihi), kat, t, a))
            conn.commit()
            conn.close()
            st.success("Gider başarıyla kasadan düşüldü!")
            st.rerun()
    
    st.divider()
    st.markdown("##### 📜 Son Harcamalar")
    conn = sqlite3.connect(db_yolu)
    df_g = pd.read_sql_query("SELECT tarih as Tarih, kategori as Kategori, tutar as 'Tutar (₺)', aciklama as Açıklama FROM giderler ORDER BY id DESC LIMIT 15", conn)
    conn.close()
    if not df_g.empty: 
        st.dataframe(df_g, use_container_width=True, hide_index=True)
