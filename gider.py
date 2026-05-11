import streamlit as st
import sqlite3
import datetime
import pandas as pd

def goster(db_yolu):
    st.subheader("Gider Girişi")
    with st.form("gider_form", clear_on_submit=True):
        kat = st.selectbox("Kategori", ["Elektrik", "Su", "Maaş", "Bakım", "Temizlik", "Diğer"])
        t = st.number_input("Tutar", min_value=0.0); a = st.text_input("Açıklama")
        if st.form_submit_button("💳 Harca"):
            conn = sqlite3.connect(db_yolu); c = conn.cursor()
            c.execute("INSERT INTO giderler (tarih, kategori, tutar, aciklama) VALUES (?,?,?,?)", (str(datetime.date.today()), kat, t, a))
            conn.commit(); conn.close(); st.success("Gider eklendi!")
            st.rerun()
    
    st.divider()
    st.markdown("##### 📜 Son Harcamalar")
    conn = sqlite3.connect(db_yolu)
    df_g = pd.read_sql_query("SELECT tarih as Tarih, kategori as Kategori, tutar as 'Tutar (₺)', aciklama as Açıklama FROM giderler ORDER BY id DESC LIMIT 15", conn)
    conn.close()
    if not df_g.empty: st.dataframe(df_g, use_container_width=True, hide_index=True)
