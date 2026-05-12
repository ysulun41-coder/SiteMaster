import streamlit as st
import pandas as pd
import sqlite3

# --- KENDİ YAZDIĞIMIZ MODÜLLERİ İÇERİ ÇEKİYORUZ ---
import sakin_kayit
import liste
import kisikart
import borclandirma
import tahsilat
import gider
import dashboard
import rapor
import sakin_guncelle
import gecikmeler
import hukuki

# --- VERİTABANI VE SİSTEM AYARLARI ---
def init_master_db():
    conn = sqlite3.connect('master.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS siteler (id INTEGER PRIMARY KEY AUTOINCREMENT, site_adi TEXT UNIQUE, tenant_db_adi TEXT)''')
    conn.commit()
    conn.close()

def init_tenant_db(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS yoneticiler (id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici_adi TEXT UNIQUE, sifre TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sakinler (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        blok TEXT, daire_no TEXT, malik_ad TEXT, malik_tc TEXT, malik_tel TEXT, 
        kiraci_ad TEXT, kiraci_tc TEXT, kiraci_tel TEXT, plaka TEXT, sifre TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bloklar (id INTEGER PRIMARY KEY AUTOINCREMENT, blok_adi TEXT, daire_sayisi INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS aidatlar (id INTEGER PRIMARY KEY AUTOINCREMENT, blok TEXT, daire_no TEXT, tarih TEXT, tutar REAL, aciklama TEXT, durum TEXT DEFAULT 'Ödenmedi')''')
    c.execute('''CREATE TABLE IF NOT EXISTS giderler (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, kategori TEXT, tutar REAL, aciklama TEXT)''')
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
        conn = sqlite3.connect('master.db')
        df_siteler = pd.read_sql_query("SELECT site_adi, tenant_db_adi FROM siteler", conn)
        conn.close()
        
        giris_tab1, giris_tab2 = st.tabs(["🔑 Yönetici Girişi", "🏠 Sakin Girişi"])
        
        # 1. Yönetici Giriş Sekmesi
        with giris_tab1:
            with st.container(border=True):
                if not df_siteler.empty:
                    sec_site = st.selectbox("Site Seçiniz", df_siteler['site_adi'].tolist(), key="adm_s")
                    k_adi = st.text_input("Kullanıcı Adı")
                    sifre = st.text_input("Şifre", type="password")
                    if st.button("Yönetici Girişi", type="primary", use_container_width=True):
                        db = df_siteler.loc[df_siteler['site_adi'] == sec_site, 'tenant_db_adi'].values[0]
                        init_tenant_db(db)
                        conn_t = sqlite3.connect(db); ct = conn_t.cursor()
                        ct.execute("SELECT kullanici_adi FROM yoneticiler WHERE kullanici_adi=? AND sifre=?", (k_adi, sifre))
                        if ct.fetchone():
                            st.session_state.aktif_site = sec_site
                            st.session_state.aktif_db = db
                            st.session_state.rol = "Yönetici"
                            sayfa_degistir('Ana_Sayfa'); st.rerun()
                        else: st.error("Hatalı bilgiler!")

        # 2. Sakin Giriş Sekmesi
        with giris_tab2:
            with st.container(border=True):
                if not df_siteler.empty:
                    sec_site_s = st.selectbox("Site Seçiniz", df_siteler['site_adi'].tolist(), key="sak_s")
                    db_s = df_siteler.loc[df_siteler['site_adi'] == sec_site_s, 'tenant_db_adi'].values[0]
                    init_tenant_db(db_s)
                    conn_s = sqlite3.connect(db_s)
                    df_bl = pd.read_sql_query("SELECT DISTINCT blok FROM sakinler", conn_s)
                    if not df_bl.empty:
                        s_bl = st.selectbox("Blok", df_bl['blok'].tolist())
                        df_dr = pd.read_sql_query(f"SELECT daire_no FROM sakinler WHERE blok='{s_bl}'", conn_s)
                        s_dr = st.selectbox("Daire No", df_dr['daire_no'].tolist())
                        s_sif = st.text_input("Şifreniz", type="password", key="sak_pass")
                        if st.button("Sakin Girişi", type="primary", use_container_width=True):
                            ct = conn_s.cursor()
                            ct.execute("SELECT malik_ad FROM sakinler WHERE blok=? AND daire_no=? AND sifre=?", (s_bl, s_dr, s_sif))
                            res = ct.fetchone()
                            if res:
                                st.session_state.aktif_site = sec_site_s
                                st.session_state.aktif_db = db_s
                                st.session_state.rol = "Sakin"
                                st.session_state.sakin_bilgi = {"blok": s_bl, "daire": s_dr, "isim": res[0]}
                                sayfa_degistir('Ana_Sayfa'); st.rerun()
                            else: st.error("Hatalı şifre!")
                    else: st.warning("Kayıtlı sakin bulunamadı.")
                    conn_s.close()
        st.divider()
        st.button("🏢 Yeni Site Kaydı Oluştur", on_click=sayfa_degistir, args=('Kayıt',), use_container_width=True)

# --- YENİ SİTE KAYIT SAYFASI ---
elif st.session_state.sayfa == 'Kayıt':
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📝 Yeni Site Kurulumu")
        with st.container(border=True):
            site_adi = st.text_input("Site Adı")
            blok_adedi = st.number_input("Blok Adedi", min_value=1, step=1)
            blok_verileri = []
            for i in range(int(blok_adedi)):
                c1, c2 = st.columns(2)
                with c1: b_ad = st.text_input(f"{i+1}. Blok İsmi", key=f"bn_{i}")
                with c2: d_say = st.number_input(f"{i+1}. Daire Sayısı", min_value=1, key=f"bc_{i}")
                blok_verileri.append((b_ad, d_say))
            st.divider()
            y_k = st.text_input("Yönetici Kullanıcı Adı")
            y_s = st.text_input("Şifre", type="password")
            y_s_t = st.text_input("Şifre Tekrarı", type="password")
            if st.button("Sisteme Kaydet", type="primary", use_container_width=True):
                if y_s == y_s_t and site_adi and y_k:
                    tenant_db = f"{site_adi.replace(' ', '_').lower()}_db.sqlite"
                    conn = sqlite3.connect('master.db'); c = conn.cursor()
                    c.execute("INSERT INTO siteler (site_adi, tenant_db_adi) VALUES (?, ?)", (site_adi, tenant_db))
                    conn.commit(); conn.close()
                    init_tenant_db(tenant_db)
                    conn_t = sqlite3.connect(tenant_db); ct = conn_t.cursor()
                    ct.executemany("INSERT INTO bloklar (blok_adi, daire_sayisi) VALUES (?, ?)", blok_verileri)
                    ct.execute("INSERT INTO yoneticiler (kullanici_adi, sifre) VALUES (?, ?)", (y_k, y_s))
                    conn_t.commit(); conn_t.close()
                    st.success("Kurulum tamamlandı!"); sayfa_degistir('Giriş'); st.rerun()
                else: st.error("Bilgileri kontrol edin!")
        st.button("⬅️ Geri Dön", on_click=sayfa_degistir, args=('Giriş',))

# --- ANA SAYFA (YÖNETİCİ & SAKİN AYRIMI) ---
elif st.session_state.sayfa == 'Ana_Sayfa':
    db_yolu = st.session_state.aktif_db
    
    # --- EVRENSEL ÜST BAŞLIK VE ÇIKIŞ BUTONU ---
    col_t, col_l = st.columns([4, 1])
    with col_t:
        st.title(f"🏢 {st.session_state.aktif_site}")
    with col_l:
        st.write("") 
        if st.button("🚪 Güvenli Çıkış", type="primary", use_container_width=True, key="universal_logout"):
            st.session_state.clear()
            st.rerun()
    st.divider()

    # --- HİZASI TAM DÜZELTİLMİŞ YÖNETİCİ BLOĞU ---
    if st.session_state.rol == "Yönetici":
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
            "➕ Sakin", "📋 Liste", "👤 Kişi Kartı", "💰 Tahakkuk", 
            "✅ Tahsilat", "💳 Gider", "📊 Dashboard", "📥 Raporlar", "🔧 Güncelle", "🚨 Gecikmeler", "⚖️ Hukuki"
        ])
        
        with tab1: sakin_kayit.goster(db_yolu)
        with tab2: liste.goster(db_yolu)
        with tab3: kisikart.goster(db_yolu)
        with tab4: borclandirma.goster(db_yolu)
        with tab5: tahsilat.goster(db_yolu, st.session_state.aktif_site)
        with tab6: gider.goster(db_yolu)
        with tab7: dashboard.goster(db_yolu)
        with tab8: rapor.goster(db_yolu, st.session_state.aktif_site)
        with tab9: sakin_guncelle.goster(db_yolu)
        with tab10: gecikmeler.goster(db_yolu, st.session_state.aktif_site)
        with tab11: hukuki.goster(db_yolu) # <--- YENİ MODÜL BURADA!

    # --- SAKİN BLOĞU ---
    elif st.session_state.rol == "Sakin":
        # Sakin paneli modülünü çağırıyoruz (Oluşturduğumuz sakin_panel.py dosyasından)
        import sakin_panel
        sakin_panel.goster(db_yolu, st.session_state.aktif_site, st.session_state.sakin_bilgi)
