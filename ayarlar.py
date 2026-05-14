import streamlit as st
import sqlite3
import base64
from utils import sitemaster_logo_koy

def goster(tenant_db_yolu, master_db_yolu, aktif_site):
    sitemaster_logo_koy()
    st.subheader("⚙️ Sistem Ayarları ve Bilgi Güncelleme")
    
    tab1, tab2 = st.tabs(["🔑 Güvenlik (Şifre)", "🏢 Site & Yönetici Profili"])
    
    # --- TAB 1: ŞİFRE DEĞİŞTİRME ---
    with tab1:
        with st.form("sifre_degistir_form", clear_on_submit=True):
            st.info("Güvenliğiniz için şifrenizi buradan periyodik olarak değiştirebilirsiniz.")
            eski_sifre = st.text_input("Mevcut Şifreniz", type="password")
            yeni_sifre = st.text_input("Yeni Şifreniz", type="password")
            yeni_sifre_t = st.text_input("Yeni Şifre (Tekrar)", type="password")
            
            if st.form_submit_button("Şifreyi Güncelle", type="primary"):
                conn = sqlite3.connect(tenant_db_yolu)
                c = conn.cursor()
                c.execute("SELECT id FROM yoneticiler WHERE sifre=?", (eski_sifre,))
                if c.fetchone():
                    if yeni_sifre == yeni_sifre_t and yeni_sifre != "":
                        c.execute("UPDATE yoneticiler SET sifre=? WHERE sifre=?", (yeni_sifre, eski_sifre))
                        conn.commit()
                        st.success("✅ Şifre başarıyla değiştirildi!")
                    else: st.error("Yeni şifreler eşleşmiyor veya boş!")
                else: st.error("Mevcut şifre yanlış!")
                conn.close()

    # --- TAB 2: SİTE VE YÖNETİCİ BİLGİLERİ GÜNCELLEME ---
    with tab2:
        # Mevcut verileri çekelim
        conn_m = sqlite3.connect(master_db_yolu)
        c_m = conn_m.cursor()
        c_m.execute("SELECT adres, vergi_no, telefon, eposta, logo FROM siteler WHERE site_adi=?", (aktif_site,))
        m_data = c_m.fetchone()
        conn_m.close()

        conn_t = sqlite3.connect(tenant_db_yolu)
        c_t = conn_t.cursor()
        c_t.execute("SELECT eposta FROM yoneticiler LIMIT 1")
        y_mail_data = c_t.fetchone()
        conn_t.close()

        with st.form("site_guncelle_form"):
            st.markdown("##### 🏘️ Site Kurumsal Bilgileri")
            col1, col2 = st.columns(2)
            with col1:
                yeni_adres = st.text_area("Site Adresi", value=m_data[0] if m_data[0] else "")
                yeni_vergi = st.text_input("Vergi Dairesi / No", value=m_data[1] if m_data[1] else "")
            with col2:
                yeni_tel = st.text_input("Site Telefon", value=m_data[2] if m_data[2] else "")
                yeni_kurumsal_mail = st.text_input("Site Kurumsal E-Posta", value=m_data[3] if m_data[3] else "")
                yeni_logo = st.file_uploader("Yeni Logo Yükle (Değiştirmek istemiyorsanız boş bırakın)", type=['png', 'jpg', 'jpeg'])

            st.divider()
            st.markdown("##### 📧 Yönetici İletişim (Şifre Kurtarma İçin)")
            # İşte senin istediğin can alıcı nokta burası kankam:
            yeni_yonetici_mail = st.text_input("Yönetici E-Posta Adresi", value=y_mail_data[0] if y_mail_data and y_mail_data[0] else "")
            st.caption("⚠️ Şifrenizi unutursanız kurtarma maili bu adrese gönderilecektir.")

            if st.form_submit_button("💾 Tüm Bilgileri Kaydet", type="primary"):
                # 1. Master DB Güncelleme (Site Genel Bilgileri)
                conn_m = sqlite3.connect(master_db_yolu)
                c_m = conn_m.cursor()
                
                logo_b64 = m_data[4] # Mevcut logoyu koru
                if yeni_logo:
                    logo_b64 = base64.b64encode(yeni_logo.read()).decode()

                c_m.execute("""UPDATE siteler SET adres=?, vergi_no=?, telefon=?, eposta=?, logo=? 
                             WHERE site_adi=?""", 
                          (yeni_adres, yeni_vergi, yeni_tel, yeni_kurumsal_mail, logo_b64, aktif_site))
                conn_m.commit()
                conn_m.close()

                # 2. Tenant DB Güncelleme (Yönetici E-Postası)
                conn_t = sqlite3.connect(tenant_db_yolu)
                c_t = conn_t.cursor()
                c_t.execute("UPDATE yoneticiler SET eposta=?", (yeni_yonetici_mail,))
                conn_t.commit()
                conn_t.close()

                st.success("✅ Tüm kayıtlar başarıyla güncellendi! Artık sistem tam kapasite hazır.")
                st.rerun()

        # Mevcut Logoyu Göster
        if m_data[4]:
            st.write("**Mevcut Logo:**")
            st.image(f"data:image/png;base64,{m_data[4]}", width=150)
