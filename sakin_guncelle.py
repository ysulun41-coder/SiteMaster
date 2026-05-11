# sakin_guncelle.py
import streamlit as st
import sqlite3

def goster(db_yolu):
    st.subheader("🔧 Sakin Bilgilerini Güncelle")
    conn = sqlite3.connect(db_yolu)
    c = conn.cursor()
    c.execute("SELECT id, blok, daire_no, malik_ad FROM sakinler")
    sakinler = c.fetchall()
    
    if sakinler:
        sakin_secenekleri = {f"{s[1]} Blok - No: {s[2]} ({s[3]})": s[0] for s in sakinler}
        secilen_sakin_metin = st.selectbox("Güncellenecek Sakini Seçin", list(sakin_secenekleri.keys()))
        sakin_id = sakin_secenekleri[secilen_sakin_metin]
        
        # Mevcut bilgileri çek
        c.execute("SELECT * FROM sakinler WHERE id=?", (sakin_id,))
        mevcut = c.fetchone()
        
        with st.form("guncelleme_formu"):
            col1, col2 = st.columns(2)
            with col1:
                yeni_malik = st.text_input("Kat Maliki Adı", value=mevcut[3])
                yeni_m_tel = st.text_input("Malik Tel", max_chars=11, value=mevcut[5])
                yeni_malikTC = st.text_input("Araç Plakası", value=mevcut[7])
                yeni_plaka = st.text_input("Araç Plakası", value=mevcut[9])
            with col2:
                yeni_kiraci = st.text_input("Kiracı Adı", value=mevcut[6])
                yeni_k_tel = st.text_input("Kiracı Tel", max_chars=11, value=mevcut[8])
                yeni_sifre = st.text_input("Giriş Şifresi (Aynı kalabilir)", value=mevcut[10])
            
            if st.form_submit_button("✅ Bilgileri Güncelle", type="primary"):
                c.execute("""UPDATE sakinler SET malik_ad=?, malik_tel=?, plaka=?, kiraci_ad=?, kiraci_tel=?, sifre=? 
                             WHERE id=?""", (yeni_malik, yeni_m_tel, yeni_plaka, yeni_kiraci, yeni_k_tel, yeni_sifre, sakin_id))
                conn.commit()
                st.success("Bilgiler başarıyla güncellendi!")
                st.rerun()
    else:
        st.info("Güncellenecek kayıt bulunamadı.")
    conn.close()
