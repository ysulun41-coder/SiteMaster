import streamlit as st
import pandas as pd
import sqlite3

def goster(db_yolu):
    st.subheader("Daire Detay Listesi")
    conn = sqlite3.connect(db_yolu)
    df_full = pd.read_sql_query("SELECT blok as Blok, daire_no as Daire, malik_ad as Malik, malik_tc as 'Malik TC', malik_tel as Telefon, kiraci_ad as Kiracı, kiraci_tc as 'Kiracı TC', kiraci_tel as 'Kiracı Tel', plaka as Plaka, sifre as Şifre FROM sakinler", conn)
    conn.close()
    if not df_full.empty: 
        st.dataframe(df_full, use_container_width=True, hide_index=True)
    else: 
        st.info("Kayıt yok.")
        # liste.py dosyasının sonuna eklenebilir:
st.info("💡 Bir kişinin ödemelerini ve detaylarını görmek için '👤 Kişi Kartı' sekmesini kullanabilirsiniz.")
