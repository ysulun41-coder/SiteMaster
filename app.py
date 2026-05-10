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

# --- 2. TENANT DB (SİTEYE ÖZEL VERİTABANI GÜNCELLEME) ---
def init_tenant_db(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    # Sakinler Tablosu
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
    # Bloklar Tablosu (YENİ)
    c.execute('''
        CREATE TABLE IF NOT EXISTS bloklar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blok_adi TEXT,
            daire_sayisi INTEGER
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
                    init_tenant_db(st.session_state.aktif_db)
                    sayfa_degistir('Ana_Sayfa')
                    st.rerun()
                else:
                    st.error("Kullanıcı adı veya şifre hatalı!")
        
        st.write("")
        st.button("Yeni Kayıt Oluştur", on_click=sayfa_degistir, args=('Kayıt',), use_container_width=True)

# --- YENİ SİTE KAYIT SAYFASI (BLOK YÖNETİMİ EKLENDİ) ---
elif st.session_state.sayfa == 'Kayıt':
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📝 Yeni Site Kurulumu")
        with st.container(border=True):
            site_adi = st.text_input("Site Adı")
            blok_adedi = st.number_input("Blok Adedi", min_value=1, step=1, value=1)
            
            blok_verileri = []
            if blok_adedi > 1:
                st.markdown("##### Blok Detaylarını Girin")
                for i in range(blok_adedi):
                    c1, c2 = st.columns(2)
                    with c1:
                        b_ad = st.text_input(f"{i+1}. Blok İsmi", key=f"bname_{i}", placeholder="Örn: A Blok")
                    with c2:
                        d_say = st.number_input(f"{i+1}. Daire Sayısı", min_value=1, step=1, key=f"bcnt_{i}")
                    blok_verileri.append((b_ad, d_say))
            else:
                d_say = st.number_input("Daire Sayısı", min_value=1, step=1)
                blok_verileri.append(("Ana Blok", d_say)) # Tek bloksa otomatik isim veriyoruz
                
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
                        tenant_db = f"{site_adi.replace(' ', '_').lower()}_db.sqlite"
                        
                        # 1. Master DB Kaydı
                        conn = sqlite3.connect('master.db')
                        c = conn.cursor()
                        c.execute("INSERT INTO siteler (site_adi, yonetici_kullanici, yonetici_sifre, tenant_db_adi) VALUES (?, ?, ?, ?)", 
                                  (site_adi, yeni_kullanici, yeni_sifre, tenant_db))
                        conn.commit()
                        conn.close()
                        
                        # 2. Tenant DB ve Blokların Kaydı
                        init_tenant_db(tenant_db)
                        conn_t = sqlite3.connect(tenant_db)
                        ct = conn_t.cursor()
                        ct.executemany("INSERT INTO bloklar (blok_adi, daire_sayisi) VALUES (?, ?)", blok_verileri)
                        conn_t.commit()
                        conn_t.close()
                        
                        st.success("Kurulum başarıyla tamamlandı!")
                        sayfa_degistir('Giriş')
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Bu kullanıcı adı zaten mevcut!")

        st.button("⬅️ Geri Dön", on_click=sayfa_degistir, args=('Giriş',))

# --- ANA SAYFA (SİSTEMATİK KAYIT PANELİ) ---
elif st.session_state.sayfa == 'Ana_Sayfa':
    db_yolu = st.session_state.aktif_db
    
    st.sidebar.title(f"🏢 {st.session_state.aktif_site}")
    if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.clear()
        sayfa_degistir('Giriş')
        st.rerun()

    st.title("📊 Sakin ve Daire Yönetimi")
    
    tab1, tab2 = st.tabs(["➕ Yeni Sakin Kaydı", "📋 Daire Listesi"])
    
    with tab1:
        # Veritabanından blok isimlerini çekiyoruz
        conn = sqlite3.connect(db_yolu)
        c = conn.cursor()
        c.execute("SELECT blok_adi FROM bloklar")
        mevcut_bloklar = [row[0] for row in c.fetchall()]
        conn.close()

        with st.form("sakin_form", clear_on_submit=True):
            st.subheader("Konum ve Daire")
            col1, col2, col3 = st.columns(3)
            with col1:
                # Blok seçimi artık dinamik açılır liste!
                secilen_blok = st.selectbox("Blok Seçin", mevcut_bloklar)
            with col2:
                daire_no = st.text_input("Daire No")
            with col3:
                plaka = st.text_input("Araç Plakası")

            st.divider()
            c_malik, c_kiraci = st.columns(2)
            with c_malik:
                st.markdown("**Kat Maliki**")
                m_ad = st.text_input("Ad Soyad", key="m1")
                m_tc = st.text_input("TC No", max_chars=11, key="m2")
                m_tel = st.text_input("Telefon", key="m3")
            with c_kiraci:
                st.markdown("**Kiracı (Varsa)**")
                k_ad = st.text_input("Ad Soyad", key="k1")
                k_tc = st.text_input("TC No", max_chars=11, key="k2")
                k_tel = st.text_input("Telefon", key="k3")

            if st.form_submit_button("💾 Kaydı Tamamla", type="primary"):
                if secilen_blok and daire_no and m_ad:
                    conn = sqlite3.connect(db_yolu)
                    c = conn.cursor()
                    c.execute('''INSERT INTO sakinler 
                                (blok, daire_no, malik_ad, malik_tc, malik_tel, kiraci_ad, kiraci_tc, kiraci_tel, plaka) 
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                              (secilen_blok, daire_no, m_ad, m_tc, m_tel, k_ad, k_tc, k_tel, plaka))
                    conn.commit()
                    conn.close()
                    st.success("Kayıt başarıyla veritabanına işlendi!")
                else:
                    st.error("Lütfen gerekli alanları doldurun!")

    with tab2:
        st.subheader("Daire Listesi")
        conn = sqlite3.connect(db_yolu)
        df = pd.read_sql_query("SELECT * FROM sakinler", conn)
        conn.close()
        if not df.empty:
            st.dataframe(df.drop(columns=['id']), use_container_width=True, hide_index=True)
        else:
            st.info("Kayıtlı daire bulunamadı.")
