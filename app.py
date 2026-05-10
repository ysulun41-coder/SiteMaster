import streamlit as st

# Sayfa ayarları (Cam gibi ferah bir görünüm için)
st.set_page_config(page_title="SiteMaster", page_icon="🏢", layout="centered")

# Sayfalar arası geçiş için röle mantığı (Session State)
if 'sayfa' not in st.session_state:
    st.session_state.sayfa = 'Giriş'

def sayfa_degistir(yeni_sayfa):
    st.session_state.sayfa = yeni_sayfa

# --- GİRİŞ SAYFASI ---
if st.session_state.sayfa == 'Giriş':
    st.title("🏢 SiteMaster'a Hoş Geldiniz")
    st.markdown("Lütfen yönetici bilgilerinizle giriş yapın veya yeni site kaydedin.")
    
    with st.container(border=True):
        kullanici_adi = st.text_input("Kullanıcı Adı")
        sifre = st.text_input("Şifre", type="password")
        
        if st.button("Giriş Yap", type="primary", use_container_width=True):
            if kullanici_adi and sifre:
                st.success("Giriş başarılı! (Ana sayfa bağlantısı eklenecek)")
            else:
                st.warning("Lütfen kullanıcı adı ve şifre girin.")
    
    st.write("")
    st.markdown("Siteniz henüz kayıtlı değil mi?")
    st.button("Yeni Kayıt Oluştur", on_click=sayfa_degistir, args=('Kayıt',))

# --- YENİ KAYIT SAYFASI ---
elif st.session_state.sayfa == 'Kayıt':
    st.title("📝 Yeni Site Kurulumu")
    st.markdown("Sitenizi sisteme entegre etmek için aşağıdaki bilgileri doldurun.")
    
    with st.container(border=True):
        site_adi = st.text_input("Site Adı", placeholder="Örn: İzmit Evleri")
        
        # Blok mantığı
        blok_adedi = st.number_input("Blok Adedi", min_value=1, step=1)
        
        if blok_adedi > 1:
            st.write("📌 Blok Detayları")
            for i in range(blok_adedi):
                col1, col2 = st.columns(2)
                with col1:
                    st.text_input(f"{i+1}. Blok Adı", placeholder="Örn: A", key=f"blok_adi_{i}")
                with col2:
                    st.number_input(f"{i+1}. Blok Daire Sayısı", min_value=1, step=1, key=f"daire_sayisi_{i}")
        else:
            st.number_input("Daire Sayısı", min_value=1, step=1)
            
        st.divider()
        st.write("👤 Yönetici Bilgileri")
        yeni_kullanici = st.text_input("Kullanıcı Adı", key="yeni_kullanici")
        yeni_sifre = st.text_input("Şifre", type="password", key="yeni_sifre")
        sifre_tekrar = st.text_input("Şifre Tekrarı", type="password", key="sifre_tekrar")
        
        if st.button("Sisteme Kaydet", type="primary", use_container_width=True):
            if yeni_sifre != sifre_tekrar:
                st.error("Şifreler eşleşmiyor, lütfen kontrol edin!")
            elif not site_adi or not yeni_kullanici or not yeni_sifre:
                st.warning("Lütfen zorunlu alanları doldurun.")
            else:
                st.success(f"{site_adi} başarıyla oluşturuldu! Her site için özel veritabanı altyapısı hazırlanıyor...")
                # Kayıt bitince tekrar giriş sayfasına atıyoruz
                sayfa_degistir('Giriş')
                st.rerun()
                
    st.write("")
    st.button("⬅️ Giriş Ekranına Dön", on_click=sayfa_degistir, args=('Giriş',))
