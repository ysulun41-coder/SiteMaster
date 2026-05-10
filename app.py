import streamlit as st
import pandas as pd

# Sayfa ayarları (Cam gibi ferah bir görünüm için)
st.set_page_config(page_title="SiteMaster", page_icon="🏢", layout="wide")

# Verileri geçici olarak hafızada tutmak için (Test aşaması)
if 'kayitlar' not in st.session_state:
    # Boş bir veri tablosu (DataFrame) oluşturuyoruz
    st.session_state.kayitlar = pd.DataFrame(columns=[
        "Blok", "Daire No", "Kat Maliki", "Malik TC", "Malik Tel", 
        "Kiracı", "Kiracı TC", "Kiracı Tel", "Plaka"
    ])

# Sayfalar arası geçiş için röle mantığı
if 'sayfa' not in st.session_state:
    st.session_state.sayfa = 'Giriş'

def sayfa_degistir(yeni_sayfa):
    st.session_state.sayfa = yeni_sayfa

# --- GİRİŞ SAYFASI ---
if st.session_state.sayfa == 'Giriş':
    # Görünümü ortalamak için boş kolonlar kullanıyoruz
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🏢 SiteMaster")
        st.markdown("**Sistem Giriş Paneli**")
        
        with st.container(border=True):
            kullanici_adi = st.text_input("Kullanıcı Adı")
            sifre = st.text_input("Şifre", type="password")
            
            if st.button("Giriş Yap", type="primary", use_container_width=True):
                if kullanici_adi and sifre:
                    # Giriş başarılıysa Ana Sayfaya yönlendir
                    sayfa_degistir('Ana_Sayfa')
                    st.rerun()
                else:
                    st.warning("Lütfen kullanıcı adı ve şifre girin.")
        
        st.write("")
        st.button("Yeni Kayıt Oluştur", on_click=sayfa_degistir, args=('Kayıt',), use_container_width=True)

# --- YENİ SİTE KAYIT SAYFASI ---
elif st.session_state.sayfa == 'Kayıt':
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📝 Yeni Site Kurulumu")
        
        with st.container(border=True):
            site_adi = st.text_input("Site Adı", placeholder="Örn: İzmit Evleri")
            blok_adedi = st.number_input("Blok Adedi", min_value=1, step=1)
            
            if blok_adedi > 1:
                st.write("📌 Blok Detayları")
                for i in range(blok_adedi):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.text_input(f"{i+1}. Blok Adı", key=f"b_{i}")
                    with c2:
                        st.number_input(f"{i+1}. Blok Daire Sayısı", min_value=1, step=1, key=f"d_{i}")
            else:
                st.number_input("Daire Sayısı", min_value=1, step=1)
                
            st.divider()
            yeni_kullanici = st.text_input("Yönetici Kullanıcı Adı")
            yeni_sifre = st.text_input("Şifre", type="password")
            sifre_tekrar = st.text_input("Şifre Tekrarı", type="password")
            
            if st.button("Sisteme Kaydet", type="primary", use_container_width=True):
                sayfa_degistir('Giriş')
                st.rerun()
                
        st.button("⬅️ İptal ve Geri Dön", on_click=sayfa_degistir, args=('Giriş',))

# --- ANA SAYFA (YÖNETİM PANELİ) ---
elif st.session_state.sayfa == 'Ana_Sayfa':
    # Sol Menü (Sidebar)
    st.sidebar.title("🏢 SiteMaster")
    st.sidebar.markdown("Yönetim Paneli Aktif")
    st.sidebar.divider()
    if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
        sayfa_degistir('Giriş')
        st.rerun()

    st.title("📊 Sakin ve Daire Yönetimi")
    
    # Ekranı iki sekmeye ayırıyoruz
    tab1, tab2 = st.tabs(["➕ Yeni Kayıt Ekle", "📋 Daire Listesi"])
    
    # 1. SEKME: YENİ KAYIT FORMU
    with tab1:
        # Form kullanıyoruz ki "Kaydet" butonuna basmadan sayfa yenilenmesin
        with st.form("yeni_kayit_formu", clear_on_submit=True):
            st.subheader("Konum Bilgileri")
            col1, col2, col3 = st.columns(3)
            with col1:
                blok_isim = st.text_input("Blok (Örn: A)")
            with col2:
                daire_numarasi = st.text_input("Daire No")
            with col3:
                arac_plaka = st.text_input("Araç Plakası")

            st.divider()
            
            col_sol, col_sag = st.columns(2)
            
            with col_sol:
                st.subheader("Kat Maliki Bilgileri")
                malik_ad = st.text_input("Adı Soyadı")
                malik_tc = st.text_input("TC Kimlik No", max_chars=11)
                malik_tel = st.text_input("Telefon Numarası")
                
            with col_sag:
                st.subheader("Kiracı Bilgileri")
                st.caption("(Dairede kiracı yoksa boş bırakabilirsiniz)")
                kiraci_ad = st.text_input("Kiracı Adı Soyadı")
                kiraci_tc = st.text_input("Kiracı TC Kimlik No", max_chars=11)
                kiraci_tel = st.text_input("Kiracı Telefon Numarası")

            st.write("")
            kaydet_butonu = st.form_submit_button("💾 Daireyi Sisteme Kaydet", type="primary")

            if kaydet_butonu:
                if blok_isim and daire_numarasi and malik_ad:
                    # Yeni veriyi sözlük (dictionary) olarak hazırlıyoruz
                    yeni_veri = {
                        "Blok": blok_isim, "Daire No": daire_numarasi, 
                        "Kat Maliki": malik_ad, "Malik TC": malik_tc, "Malik Tel": malik_tel,
                        "Kiracı": kiraci_ad, "Kiracı TC": kiraci_tc, "Kiracı Tel": kiraci_tel,
                        "Plaka": arac_plaka
                    }
                    # Listeye ekliyoruz (İleride burası SQLite'a yazacak)
                    yeni_df = pd.DataFrame([yeni_veri])
                    st.session_state.kayitlar = pd.concat([st.session_state.kayitlar, yeni_df], ignore_index=True)
                    st.success(f"✅ {blok_isim} Blok, {daire_numarasi} No'lu daire başarıyla kaydedildi!")
                else:
                    st.error("Lütfen Blok, Daire No ve Kat Maliki Adı kısımlarını boş bırakmayın!")

    # 2. SEKME: LİSTELEME EKRANI
    with tab2:
        st.subheader("Mevcut Daire Kayıtları")
        # Eğer kayıt varsa tabloyu göster, yoksa uyarı ver
        if not st.session_state.kayitlar.empty:
            st.dataframe(st.session_state.kayitlar, use_container_width=True, hide_index=True)
        else:
            st.info("Sisteme henüz bir daire kaydı girilmemiş.")
