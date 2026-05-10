import streamlit as st
import pandas as pd
import sqlite3
import os

# --- 1. MASTER DB (KAPICI) ---
def init_master_db():
    conn = sqlite3.connect('master.db')
    c = conn.cursor()
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

# --- 2. TENANT DB (SİTEYE ÖZEL VERİTABANI) ---
def init_tenant_db(db_name):
    # Bu fonksiyon sadece yönetici giriş yaptığında kendi sitesi için çalışır
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sakinler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blok TEXT,
            daire_no TEXT,
            malik_ad TEXT,
            malik_tc TEXT,
            malik_tel TEXT,
            kiraci_ad TEXT,
            kiraci_tc TEXT,
            kiraci_tel TEXT,
            plaka TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_master_db()

st.set_page_config(page_title="SiteMaster", page_icon="🏢", layout="wide")

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
                conn = sqlite3.connect('master.db')
                c = conn.cursor()
                c.execute("SELECT site_adi, tenant_db_adi FROM siteler WHERE yonetici_kullanici=? AND yonetici_sifre=?", (kullanici_adi, sifre))
                sonuc = c.fetchone()
                conn.close()
                
                if sonuc:
                    st.session_state.aktif_site = sonuc[0]
                    st.session_state.aktif_db = sonuc[1]
                    # Giriş başarılıysa o sitenin veritabanını ve tablolarını hazırla
                    init_tenant_db(st.session_state.aktif_db)
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
    db_yolu = st.session_state.aktif_db
    
    st.sidebar.title(f"🏢 {st.session_state.aktif_site}")
    st.sidebar.markdown(f"Aktif DB: `{db_yolu}`")
    st.sidebar.divider()
    if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.clear()
        sayfa_degistir('Giriş')
        st.rerun()

    st.title("📊 Sakin ve Daire Yönetimi")
    
    tab1, tab2 = st.tabs(["➕ Yeni Kayıt Ekle", "📋 Daire Listesi"])
    
    # 1. SEKME: VERİTABANINA YAZMA İŞLEMİ (INSERT)
    with tab1:
        with st.form("yeni_kayit_formu", clear_on_submit=True):
            st.subheader("Konum Bilgileri")
            col1, col2, col3 = st.columns(3)
            with col1: blok_isim = st.text_input("Blok (Örn: A)")
            with col2: daire_numarasi = st.text_input("Daire No")
            with col3: arac_plaka = st.text_input("Araç Plakası")

            st.divider()
            col_sol, col_sag = st.columns(2)
            with col_sol:
                st.subheader("Kat Maliki Bilgileri")
                malik_ad = st.text_input("Adı Soyadı")
                malik_tc = st.text_input("TC Kimlik No", max_chars=11)
                malik_tel = st.text_input("Telefon Numarası")
            with col_sag:
                st.subheader("Kiracı Bilgileri")
                kiraci_ad = st.text_input("Kiracı Adı Soyadı")
                kiraci_tc = st.text_input("Kiracı TC Kimlik No", max_chars=11)
                kiraci_tel = st.text_input("Kiracı Telefon Numarası")

            st.write("")
            kaydet_butonu = st.form_submit_button("💾 Daireyi Sisteme Kaydet", type="primary")

            if kaydet_butonu:
                if blok_isim and daire_numarasi and malik_ad:
                    # Formdan gelen verileri aktif sitenin özel veritabanına yazıyoruz
                    conn = sqlite3.connect(db_yolu)
                    c = conn.cursor()
                    c.execute('''INSERT INTO sakinler 
                                (blok, daire_no, malik_ad, malik_tc, malik_tel, kiraci_ad, kiraci_tc, kiraci_tel, plaka) 
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                              (blok_isim, daire_numarasi, malik_ad, malik_tc, malik_tel, kiraci_ad, kiraci_tc, kiraci_tel, arac_plaka))
                    conn.commit()
                    conn.close()
                    st.success(f"✅ {blok_isim} Blok, {daire_numarasi} No'lu daire kalıcı olarak kaydedildi!")
                else:
                    st.error("Blok, Daire No ve Kat Maliki Adı zorunludur!")

    # 2. SEKME: VERİTABANINDAN OKUMA İŞLEMİ (SELECT)
    with tab2:
        st.subheader("Mevcut Daire Kayıtları")
        # Aktif sitenin veritabanındaki sakinler tablosunu Pandas ile çekiyoruz
        conn = sqlite3.connect(db_yolu)
        df_sakinler = pd.read_sql_query("SELECT * FROM sakinler", conn)
        conn.close()
        
        if not df_sakinler.empty:
            # id kolonunu arayüzde gizliyoruz (daha temiz bir görünüm için)
            st.dataframe(df_sakinler.drop(columns=['id']), use_container_width=True, hide_index=True)
        else:
            st.info("Sisteme henüz bir daire kaydı girilmemiş.")
