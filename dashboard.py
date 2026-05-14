import streamlit as st
import sqlite3
import pandas as pd
from utils import render_header

def goster(db_yolu):
    render_header("KASA DURUMU")
    conn = sqlite3.connect(db_yolu); c = conn.cursor()
    c.execute("SELECT SUM(tutar) FROM aidatlar WHERE durum='Ödendi'"); gelir = c.fetchone()[0] or 0.0
    c.execute("SELECT SUM(tutar) FROM giderler"); gider = c.fetchone()[0] or 0.0
    c.execute("SELECT SUM(tutar) FROM aidatlar WHERE durum='Ödenmedi'"); bekleyen = c.fetchone()[0] or 0.0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam Tahsilat", f"{gelir}₺")
    m2.metric("Toplam Gider", f"{gider}₺")
    m3.metric("Kasa", f"{gelir-gider}₺")
    m4.metric("Bekleyen", f"{bekleyen}₺", delta_color="inverse")
    
    st.divider(); c_g1, c_g2 = st.columns(2)
    with c_g1: st.bar_chart(pd.DataFrame({'Kategori': ['Gelir', 'Gider'], 'Tutar': [gelir, gider]}).set_index('Kategori'))
    with c_g2:
        df_ga = pd.read_sql_query("SELECT kategori, SUM(tutar) as Toplam FROM giderler GROUP BY kategori", conn)
        if not df_ga.empty: st.bar_chart(df_ga.set_index('kategori'))
    conn.close()
