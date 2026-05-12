import streamlit as st
import sqlite3

def goster(tenant_db_yolu, master_db_yolu, aktif_site):
    st.subheader("⚙️ Sistem Ayarları ve Güvenlik")
    
    tab1, tab2 = st.tabs(["🔑 Şifre Değiştir", "🏢 Site Bilgileri"])
    
    # --- ŞİFRE DEĞİŞTİRME ---
    with tab1:
        with st.form("sifre_degistir_form", clear_on_submit=True):
            st.info("Güvenliğiniz için şifrenizi periyodik olarak değiştirin.")
            eski_sifre = st.text_input("Mevcut Şifreniz", type="password")
            yeni_sifre = st.text_input("Yeni Şifreniz", type="password")
            yeni_sifre_tekrar = st.text_input("Yeni Şifreniz (Tekrar)", type="password")
            
            if st.form_submit_button("Güncelle", type="primary"):
                conn = sqlite3.connect(tenant_db_yolu)
                c = conn.cursor()
                c.execute("SELECT id FROM yoneticiler WHERE sifre=?", (eski_sifre,))
                if c.fetchone():
                    if yeni_sifre == yeni_sifre_tekrar and yeni_sifre != "":
                        c.execute("UPDATE yoneticiler SET sifre=? WHERE sifre=?", (yeni_sifre, eski_sifre))
                        conn.commit()
                        st.success("Şifreniz başarıyla değiştirildi!")
                    else:
                        st.error("Yeni şifreler uyuşmuyor veya boş bırakılamaz.")
                else:
                    st.error("Mevcut şifrenizi yanlış girdiniz.")
                conn.close()

    # --- SİTE PROFİL BİLGİLERİ ---
    with tab2:
        conn_m = sqlite3.connect(master_db_yolu)
        c_m = conn_m.cursor()
        c_m.execute("SELECT adres, vergi_no, telefon, eposta, logo FROM siteler WHERE site_adi=?", (aktif_site,))
        site_bilgi = c_m.fetchone()
        conn_m.close()
        
        if site_bilgi:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Site Adı:** {aktif_site}")
                st.write(f"**Adres:** {site_bilgi[0]}")
                st.write(f"**Vergi No:** {site_bilgi[1]}")
                st.write(f"**Telefon:** {site_bilgi[2]}")
                st.write(f"**Kayıtlı E-Posta:** {site_bilgi[3]}")
                st.caption("Not: Bilgileri güncelleme modülü yakında eklenecektir.")
            with col2:
                if site_bilgi[4]: # Logo varsa göster
                    st.image(f"data:image/png;base64,{site_bilgi[4]}", use_container_width=True)
                else:
                    st.info("Logo Yüklenmemiş")
