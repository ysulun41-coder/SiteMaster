import streamlit as st
import pandas as pd
import sqlite3
from utils import render_header, get_conn, telefon_goster

def goster(db_yolu):
    render_header("👤 Detaylı Kişi Kartı ve Hesap Ekstresi")
    
    conn = get_conn(db_yolu)
    c = conn.cursor()
    
    # Kişi seçimi için listeyi çekiyoruz
    c.execute("SELECT id, blok, daire_no, malik_ad FROM sakinler")
    sakinler = c.fetchall()
    
    if not sakinler:
        st.info("Sistemde henüz kayıtlı sakin bulunmuyor.")
        conn.close()
        return

    sakin_secenekleri = {f"{s[1]} Blok - No: {s[2]} ({s[3]})": s[0] for s in sakinler}
    secilen_sakin_metin = st.selectbox("İncelemek İstediğiniz Sakini Seçin", list(sakin_secenekleri.keys()))
    sakin_id = sakin_secenekleri[secilen_sakin_metin]
    
    # 1. Kişisel Bilgiler
    c.execute("SELECT * FROM sakinler WHERE id=?", (sakin_id,))
    s = c.fetchone()
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("##### 🏠 Daire & Malik Bilgileri")
            st.write(f"**Konum:** {s[1]} Blok - No: {s[2]}")
            st.write(f"**Kat Maliki:** {s[3]}")
            st.write(f"**TC No:** {s[4]}")
            st.write(f"**Telefon:** {telefon_goster(s[5])}")
            st.write(f"**Araç Plaka:** {s[9]}")
            st.write(f"**Giriş Şifresi:** `{s[10]}`")

    with col2:
        with st.container(border=True):
            st.markdown("##### 🔑 Kiracı Bilgileri")
            if s[6]: # Kiracı adı varsa
                st.write(f"**Kiracı Adı:** {s[6]}")
                st.write(f"**Kiracı TC:** {s[7]}")
                st.write(f"**Kiracı Tel:** {telefon_goster(s[8])}")
            else:
                st.write("Dairede kiracı kaydı bulunmamaktadır.")

    st.divider()

    # 2. Finansal Özet (Metrics)
    c.execute("SELECT SUM(tutar) FROM aidatlar WHERE blok=? AND daire_no=? AND durum='Ödendi'", (s[1], s[2]))
    toplam_odenen = c.fetchone()[0] or 0.0
    
    c.execute("SELECT SUM(tutar) FROM aidatlar WHERE blok=? AND daire_no=? AND durum='Ödenmedi'", (s[1], s[2]))
    toplam_borc = c.fetchone()[0] or 0.0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("✅ Toplam Ödenen", f"{toplam_odenen:,.2f} ₺")
    m2.metric("❌ Bekleyen Borç", f"{toplam_borc:,.2f} ₺", delta=f"-{toplam_borc:,.2f}", delta_color="inverse")
    m3.metric("📊 İşlem Sayısı", len(pd.read_sql_query(f"SELECT id FROM aidatlar WHERE blok='{s[1]}' AND daire_no='{s[2]}'", conn)))

    # 3. Hareket Dökümü (Hesap Ekstresi)
    st.markdown("##### 🧾 İşlem Geçmişi")
    query = f"SELECT tarih as Tarih, aciklama as Açıklama, tutar as 'Tutar (₺)', durum as Durum FROM aidatlar WHERE blok='{s[1]}' AND daire_no='{s[2]}' ORDER BY id DESC"
    df_ekstre = pd.read_sql_query(query, conn)
    
    if not df_ekstre.empty:
        st.dataframe(
            df_ekstre.style.map(lambda x: 'color: red; font-weight: bold' if x == 'Ödenmedi' else 'color: green; font-weight: bold', subset=['Durum']),
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("Bu daireye ait henüz bir mali hareket bulunmuyor.")

    conn.close()

