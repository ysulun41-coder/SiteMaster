import streamlit as st
import sqlite3

def goster(db_yolu):
    st.subheader("Yeni Sakin Kaydı")
    conn = sqlite3.connect(db_yolu)
    c = conn.cursor()
    c.execute("SELECT blok_adi FROM bloklar")
    bloklar = [r[0] for r in c.fetchall()]
    conn.close()

    with st.form("sakin_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1: s_blok = st.selectbox("Blok Seç", bloklar)
        with col2: d_no = st.text_input("Daire No")
        with col3: s_sifre_ek = st.text_input("daire için Şifre belirle", help="Başına Blok ve Daire otomatik eklenecek.")
        
        c_m, c_k = st.columns(2)
        with c_m: 
            m_a = st.text_input("Kat Malik Ad")
            m_tc = st.text_input("Kat Malik TC", max_chars=11)
            m_t = st.text_input("Kat Malik Tel",max_chars=11)
            plk = st.text_input("Araç Plaka")
        with c_k: 
            k_a = st.text_input("Kiracı Ad")
            k_tc = st.text_input("Kiracı TC", max_chars=11)
            k_t = st.text_input("Kiracı Tel",max_chars=11)
           
            
        
        if st.form_submit_button("💾 Kaydet", type="primary"):
            if s_blok and d_no and m_a and s_sifre_ek:
                tam_sifre = f"{s_blok}{d_no}-{s_sifre_ek}"
                conn = sqlite3.connect(db_yolu); c = conn.cursor()
                c.execute("SELECT id FROM sakinler WHERE blok=? AND daire_no=?", (s_blok, d_no))
                if c.fetchone(): 
                    st.error(f"⚠️ Hata: {s_blok} Blok, {d_no} dolu!")
                else:
                    c.execute("INSERT INTO sakinler (blok, daire_no, malik_ad, malik_tc, malik_tel, kiraci_ad, kiraci_tc, kiraci_tel, plaka, sifre) VALUES (?,?,?,?,?,?,?,?,?,?)", (s_blok, d_no, m_a, m_tc, m_t, k_a, k_tc, k_t, plk, tam_sifre))
                    conn.commit(); st.success(f"Kayıt tamam! Şifre: {tam_sifre}")
                conn.close()
            else: st.error("Zorunlu alanları doldurun!")
