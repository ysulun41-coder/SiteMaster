import streamlit as st
import sqlite3
from utils import render_header

def goster(db_yolu):
    render_header("🔧 Sakin Bilgilerini Güncelle")
    conn = sqlite3.connect(db_yolu)
    c = conn.cursor()
    
    # Güncellenecek kişiyi seçmek için listeyi çekiyoruz
    c.execute("SELECT id, blok, daire_no, malik_ad FROM sakinler")
    sakinler = c.fetchall()
    
    if sakinler:
        sakin_secenekleri = {f"{s[1]} Blok - No: {s[2]} ({s[3]})": s[0] for s in sakinler}
        secilen_sakin_metin = st.selectbox("Güncellenecek Sakini Seçin", list(sakin_secenekleri.keys()))
        sakin_id = sakin_secenekleri[secilen_sakin_metin]
        
        # Mevcut tüm bilgileri veritabanından çekiyoruz
        c.execute("SELECT * FROM sakinler WHERE id=?", (sakin_id,))
        mevcut = c.fetchone()
        
        # Form düzeni (Kayıt ekranıyla birebir aynı alanlar)
        with st.form("guncelleme_formu"):
            st.info(f"📍 Şu an düzenlenen daire: {mevcut[1]} Blok - No: {mevcut[2]}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### 🏠 Malik Bilgileri")
                yeni_malik = st.text_input("Kat Maliki Adı Soyadı", value=mevcut[3])
                yeni_m_tc = st.text_input("Malik TC No", value=mevcut[4], max_chars=11)
                yeni_m_tel = st.text_input("Malik Telefon", value=mevcut[5])
                yeni_plaka = st.text_input("Araç Plakası", value=mevcut[9])

            with col2:
                st.markdown("##### 🔑 Kiracı & Giriş Bilgileri")
                yeni_kiraci = st.text_input("Kiracı Adı Soyadı", value=mevcut[6])
                yeni_k_tc = st.text_input("Kiracı TC No", value=mevcut[7], max_chars=11)
                yeni_k_tel = st.text_input("Kiracı Telefon", value=mevcut[8])
                yeni_sifre = st.text_input("Sakin Giriş Şifresi", value=mevcut[10])

            st.divider()
            
            if st.form_submit_button("✅ Tüm Bilgileri Güncelle", type="primary"):
                # Veritabanında tüm alanları güncelliyoruz
                c.execute("""
                    UPDATE sakinler 
                    SET malik_ad=?, malik_tc=?, malik_tel=?, 
                        kiraci_ad=?, kiraci_tc=?, kiraci_tel=?, 
                        plaka=?, sifre=? 
                    WHERE id=?
                """, (
                    yeni_malik, yeni_m_tc, yeni_m_tel, 
                    yeni_kiraci, yeni_k_tc, yeni_k_tel, 
                    yeni_plaka, yeni_sifre, sakin_id
                ))
                
                conn.commit()
                st.success("Sakin kartı başarıyla güncellendi! Veriler tıkır tıkır işlendi.")
                st.rerun()
    else:
        st.info("Sistemde güncellenecek herhangi bir sakin kaydı bulunamadı.")
        
    conn.close()
