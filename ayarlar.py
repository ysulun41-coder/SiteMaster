import streamlit as st
import sqlite3
import base64
from utils import render_header, get_conn, telefon_normalize, telefon_form_degeri

def goster(tenant_db_yolu, master_db_yolu, aktif_site):
    render_header("⚙️ Sistem Ayarları ve Bilgi Güncelleme")
    
    tab1, tab2 = st.tabs(["🔑 Güvenlik (Şifre)", "🏢 Site & Yönetici Profili"])
    
    # --- TAB 1: ŞİFRE DEĞİŞTİRME ---
    with tab1:
        with st.form("sifre_degistir_form", clear_on_submit=True):
            st.info("Güvenliğiniz için şifrenizi buradan periyodik olarak değiştirebilirsiniz.")
            eski_sifre = st.text_input("Mevcut Şifreniz", type="password")
            yeni_sifre = st.text_input("Yeni Şifreniz", type="password")
            yeni_sifre_t = st.text_input("Yeni Şifre (Tekrar)", type="password")
            
            if st.form_submit_button("Şifreyi Güncelle", type="primary"):
                conn = get_conn(tenant_db_yolu)
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
        conn_m = get_conn(master_db_yolu)
        c_m = conn_m.cursor()
        c_m.execute("SELECT adres, vergi_no, telefon, eposta, logo FROM siteler WHERE site_adi=?", (aktif_site,))
        m_data = c_m.fetchone()
        conn_m.close()

        conn_t = get_conn(tenant_db_yolu)
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
                yeni_tel = st.text_input(
                    "Site Telefon",
                    value=telefon_form_degeri(m_data[2] if m_data else ""),
                    placeholder="532 123 45 67",
                )
                yeni_kurumsal_mail = st.text_input("Site Kurumsal E-Posta", value=m_data[3] if m_data[3] else "")
                yeni_logo = st.file_uploader("Yeni Logo Yükle (Değiştirmek istemiyorsanız boş bırakın)", type=['png', 'jpg', 'jpeg'])

            st.divider()
            st.markdown("##### 📧 Yönetici İletişim (Şifre Kurtarma İçin)")
            # İşte senin istediğin can alıcı nokta burası kankam:
            yeni_yonetici_mail = st.text_input("Yönetici E-Posta Adresi", value=y_mail_data[0] if y_mail_data and y_mail_data[0] else "")
            st.caption("⚠️ Şifrenizi unutursanız kurtarma maili bu adrese gönderilecektir.")

            if st.form_submit_button("💾 Tüm Bilgileri Kaydet", type="primary"):
                ok_tel, tel_k, err_tel = telefon_normalize(yeni_tel, zorunlu=bool((yeni_tel or "").strip()))
                if not ok_tel:
                    st.error(f"Site telefonu: {err_tel}")
                else:
                    conn_m = get_conn(master_db_yolu)
                    c_m = conn_m.cursor()

                    logo_b64 = m_data[4]
                    if yeni_logo:
                        logo_b64 = base64.b64encode(yeni_logo.read()).decode()

                    c_m.execute(
                        """UPDATE siteler SET adres=?, vergi_no=?, telefon=?, eposta=?, logo=?
                           WHERE site_adi=?""",
                        (yeni_adres, yeni_vergi, tel_k, yeni_kurumsal_mail, logo_b64, aktif_site),
                    )
                    conn_m.commit()
                    conn_m.close()

                    conn_t = get_conn(tenant_db_yolu)
                    c_t = conn_t.cursor()
                    c_t.execute("UPDATE yoneticiler SET eposta=?", (yeni_yonetici_mail,))
                    conn_t.commit()
                    conn_t.close()

                    st.success("✅ Tüm kayıtlar başarıyla güncellendi!")
                    st.rerun()

        # Mevcut Logoyu Göster
        if m_data[4]:
            st.write("**Mevcut Logo:**")
            st.image(f"data:image/png;base64,{m_data[4]}", width=150)

