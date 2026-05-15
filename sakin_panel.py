import streamlit as st
import sqlite3
import pandas as pd
from utils import render_header, get_conn

def goster(db_yolu, aktif_site, sakin_bilgi):
    s = sakin_bilgi
    render_header(f"👋 Hoş Geldiniz, {s['isim']}")
    with st.container(border=True):
        st.subheader("Hesap Özeti")
        st.write(f"**Daire:** {s['blok']} Blok, No: {s['daire']}")
        conn = get_conn(db_yolu)
        df_hesap = pd.read_sql_query("SELECT tarih as Tarih, aciklama as Açıklama, tutar as 'Tutar (₺)', durum as Durum FROM aidatlar WHERE blok=? AND daire_no=? ORDER BY id DESC", conn, params=(s['blok'], s['daire']))
        conn.close()
        if not df_hesap.empty:
            st.dataframe(df_hesap.style.map(lambda x: 'color: red' if x == 'Ödenmedi' else 'color: green', subset=['Durum']), use_container_width=True, hide_index=True)
        else: 
            st.success("Borç kaydınız bulunmamaktadır.")

