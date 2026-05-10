import streamlit as st
import pandas as pd
import sqlite3
import os

# --- 1. VERİTABANI ALTYAPISI (MASTER DB) ---
def init_master_db():
    # master.db yoksa oluşturur, varsa bağlanır
    conn = sqlite3.connect('master.db')
    c = conn.cursor()
    # Siteler tablosunu oluştur
    c.execute('''
        CREATE TABLE IF NOT EXISTS siteler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_adi TEXT,
            yonetici_kullanici TEXT UNIQUE,
            yonetici_sifre TEXT,
            tenant_db_adi TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Uygulama başlarken DB'yi hazırla
init_master_db()

# Sayfa ayarları
st.set_page_config(page_title="SiteMaster", page_icon="🏢", layout="wide")

# Sayfalar arası geçiş için röle
if 'sayfa' not in st.session_state:
    st.session_state.sayfa = 'Giriş'

def sayfa_degistir(yeni_sayfa):
    st.session_state.sayfa = yeni_sayfa

# --- GİRİŞ SAYFASI ---
if st.session_state.sayfa == 'Giriş':
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🏢 SiteMaster")
        st.markdown("**Sistem Giriş Paneli**")
        
        with st.container(border=True):
            kullanici_adi = st.text_input("Kullanıcı Adı")
            sifre = st.text_input("Şifre", type="password")
            
            if st.button("Giriş Yap", type="primary", use_container_width=True):
                # Veritabanında kullanıcı kontrolü yapıyoruz
                conn = sqlite3.connect('master.db')
                c = conn.cursor()
                c.execute("SELECT site_adi, tenant_db_adi FROM siteler WHERE yonetici_kullanici=? AND yonetici_sifre=?", (kullanici_adi, sifre))
                sonuc = c.fetchone()
                conn.close()
                
                if sonuc:
                    # Giriş başarılı, site bilgilerini hafızaya al ve geç
                    st.session_state.aktif_site = sonuc[0]
                    st.session_state.aktif_db = sonuc[1]
                    sayfa_degistir('Ana_Sayfa')
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı!")
        
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
            # (Görsellik kalabalık yapmasın diye blok detaylarını şimdilik atlıyoruz, DB'ye odaklanıyoruz)
                
            st.divider()
            yeni_kullanici = st.text_input("Yönetici Kullanıcı Adı")
            yeni_sifre = st.text_input("Şifre", type="password")
            sifre_tekrar = st.text_input("Şifre Tekrarı", type="password")
            
            if st.button("Sisteme Kaydet", type="primary", use_container_width=True):
                if yeni_sifre != sifre_tekrar:
                    st.error("Şifreler uyuşmuyor!")
                elif not site_adi or not yeni_kullanici or not yeni_sifre:
                    st.warning("Lütfen tüm alanları doldurun.")
                else:
                    try:
                        # Her site için benzersiz bir db adı oluşturuyoruz (Örn: izmit_evleri_db.sqlite)
                        tenant_db = f"{site_adi.replace(' ', '_').lower()}_db.sqlite"
                        
                        conn = sqlite3.connect('master.db')
                        c = conn.cursor()
                        c.execute("INSERT INTO siteler (site_adi, yonetici_kullanici, yonetici_sifre, tenant_db_adi) VALUES (?, ?, ?, ?)", 
                                  (site_adi, yeni_kullanici, yeni_sifre, tenant_db))
                        conn.commit()
                        conn.close()
                        
                        st.success(f"Tebrikler! {site_adi} sisteme eklendi. Şimdi giriş yapabilirsiniz.")
                        sayfa_degistir('Giriş')
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Bu kullanıcı adı zaten alınmış, lütfen başka bir tane deneyin.")

        st.button("⬅️ İptal ve Geri Dön", on_click=sayfa_degistir, args=('Giriş',))

# --- ANA SAYFA (YÖNETİM PANELİ) ---
elif st.session_state.sayfa == 'Ana_Sayfa':
    st.sidebar.title(f"🏢 {st.session_state.aktif_site}")
    st.sidebar.markdown(f"Aktif DB: `{st.session_state.aktif_db}`")
    st.sidebar.divider()
    
    if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.clear() # Çıkışta hafızayı temizle
        sayfa_degistir('Giriş')
        st.rerun()

    st.title(f"Hoş Geldiniz, {st.session_state.aktif_site} Yönetimi")
    st.success("Master Veritabanı bağlantısı başarıyla kuruldu ve yetki doğrulandı!")
    st.info("Sıradaki aşamamızda, sağ menüde yazan ve sadece bu siteye ait olan veritabanı dosyasının içine sakinleri kaydetmeye başlayacağız.")
