import streamlit as st
import sqlite3
import pandas as pd
import io
from utils import sitemaster_logo_koy

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Rapor')
    return output.getvalue()

def goster(db_yolu, aktif_site):
    sitemaster_logo_koy()
    st.subheader("Excel Raporları")
    c1, c2, c3 = st.columns(3)
    conn = sqlite3.connect(db_yolu)
    
    with c1:
        st.info("🏠 **Sakin Listesi**")
        df_s = pd.read_sql_query("SELECT blok as Blok, daire_no as Daire, malik_ad as Malik, malik_tel as Telefon, kiraci_ad as Kiracı, plaka as Plaka FROM sakinler", conn)
        if not df_s.empty: st.download_button("📥 İndir (Excel)", data=to_excel(df_s), file_name=f"Sakinler_{aktif_site}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    with c2:
        st.error("⏳ **Borçlu Listesi**")
        df_b = pd.read_sql_query("SELECT blok as Blok, daire_no as Daire, aciklama as Açıklama, tutar as Tutar, tarih as Tarih FROM aidatlar WHERE durum='Ödenmedi'", conn)
        if not df_b.empty: st.download_button("📥 İndir (Excel)", data=to_excel(df_b), file_name=f"Borclular_{aktif_site}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    with c3:
        st.success("🧾 **Kasa Ekstresi**")
        df_gelir = pd.read_sql_query("SELECT tarih, aciklama, tutar, 'GELİR' as Tip FROM aidatlar WHERE durum='Ödendi'", conn)
        df_gider = pd.read_sql_query("SELECT tarih, aciklama, tutar, 'GİDER' as Tip FROM giderler", conn)
        df_kasa = pd.concat([df_gelir, df_gider]).sort_values(by='tarih', ascending=False)
        if not df_kasa.empty: st.download_button("📥 İndir (Excel)", data=to_excel(df_kasa), file_name=f"Kasa_{aktif_site}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        
    conn.close()
