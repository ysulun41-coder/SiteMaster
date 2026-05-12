import streamlit as st
import pandas as pd
import sqlite3
import base64

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
import personel
import demirbas
import ayarlar  # <--- YENİ AYARLAR MODÜLÜ

# --- VERİTABANI VE SİSTEM AYARLARI ---
def init_master_db():
    conn = sqlite3.connect('master.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS siteler (id INTEGER PRIMARY KEY AUTOINCREMENT, site_adi TEXT UNIQUE, tenant_db_adi TEXT)''')
    # GÜVENLİ GÜNCELLEME: Eski veritabanlarına yeni sütunları otomatik ekler
    try:
        c.execute("ALTER TABLE siteler ADD COLUMN adres TEXT")
        c.execute("ALTER TABLE siteler ADD COLUMN vergi_no TEXT")
        c.execute("ALTER TABLE siteler ADD COLUMN telefon TEXT")
        c.execute("ALTER TABLE siteler ADD COLUMN eposta TEXT")
        c.execute("ALTER TABLE siteler ADD COLUMN logo TEXT")
    except: pass
    conn.commit()
    conn.close()

def init_tenant_db(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS yoneticiler (id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici_adi TEXT UNIQUE, sifre TEXT)''')
    try:
        c.execute("ALTER TABLE yoneticiler ADD COLUMN eposta TEXT")
    except: pass
    c.execute('''CREATE TABLE IF NOT EXISTS sakinler (id INTEGER PRIMARY KEY AUTOINCREMENT, blok TEXT, daire_no TEXT, malik_ad TEXT, malik_tc TEXT, malik_tel TEXT, kiraci_ad TEXT, kiraci_tc TEXT, kiraci_tel TEXT, plaka TEXT, sifre TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bloklar (id INTEGER PRIMARY KEY AUTOINCREMENT, blok_adi TEXT, daire_sayisi INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS aidatlar (id INTEGER PRIMARY KEY AUTOINCREMENT, blok TEXT, daire_no TEXT, tarih TEXT, tutar REAL, aciklama TEXT, durum TEXT DEFAULT 'Ödenmedi', son_odeme_tarihi TEXT, faiz_uygula INTEGER DEFAULT 0, yillik_faiz REAL DEFAULT 0.0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS giderler (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, kategori TEXT, tutar REAL, aciklama TEXT, firma_kisi TEXT, tc_no TEXT)''')
    conn.commit()
    conn.close()

init_master_db()

st.set_page_config(page_title="SiteMaster", page_icon="🏢", layout="wide")

if 'sayfa' not in st.session_state: st.session_state.sayfa = 'Giriş'
def sayfa_degistir(yeni_sayfa): st.session_state.sayfa = yeni_sayfa

# --- GİRİŞ SAYFASI ---
if st.session_state.sayfa == 'Giriş':
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🏢 SiteMaster")
        conn = sqlite3.connect('master.db')
        df_siteler = pd.read_sql_query("SELECT site_adi, tenant_db_adi FROM siteler", conn)
        conn.close()
        
        giris_tab1, giris_tab2 = st.tabs(["🔑 Yönetici Girişi", "🏠 Sakin Girişi"])
        
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
                            st.session_state.aktif_site = sec_site; st.session_state.aktif_db = db; st.session_state.rol = "Yönetici"
                            sayfa_degistir('Ana_Sayfa'); st.rerun()
                        else: st.error("Hatalı bilgiler!")
            
            # 🔥 ŞİFREMİ UNUTTUM MODÜLÜ 🔥
            with st.expander("🆘 Şifremi Unuttum"):
                st.caption("Kayıtlı E-Posta adresinizi girerek yeni şifre belirleyebilirsiniz.")
                f_site = st.selectbox("Sitenizi Seçin", df_siteler['site_adi'].tolist() if not df_siteler.empty else [], key="f_site")
                f_eposta = st.text_input("Yönetici Kayıt E-Postası")
                f_yeni_sifre = st.text_input("Yeni Şifre", type="password")
                
                if st.button("Şifremi Sıfırla"):
                    if f_site and f_eposta and f_yeni_sifre:
                        f_db = df_siteler.loc[df_siteler['site_adi'] == f_site, 'tenant_db_adi'].values[0]
                        conn_t = sqlite3.connect(f_db); ct = conn_t.cursor()
                        # E-posta eşleşiyorsa şifreyi güncelle
                        ct.execute("SELECT id FROM yoneticiler WHERE eposta=?", (f_eposta,))
                        if ct.fetchone():
                            ct.execute("UPDATE yoneticiler SET sifre=? WHERE eposta=?", (f_yeni_sifre, f_eposta))
                            conn_t.commit(); st.success("Şifreniz başarıyla sıfırlandı! Yukarıdan giriş yapabilirsiniz.")
                        else: st.error("Bu E-Posta adresine ait yönetici kaydı bulunamadı.")
                        conn_t.close()

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
                                st.session_state.aktif_site = sec_site_s; st.session_state.aktif_db = db_s; st.session_state.rol = "Sakin"
                                st.session_state.sakin_bilgi = {"blok": s_bl, "daire": s_dr, "isim": res[0]}
                                sayfa_degistir('Ana_Sayfa'); st.rerun()
                            else: st.error("Hatalı şifre!")
                    else: st.warning("Kayıtlı sakin bulunamadı.")
                    conn_s.close()

        st.divider()
        st.button("🏢 Yeni Kurumsal Site Kaydı Oluştur", on_click=sayfa_degistir, args=('Kayıt',), use_container_width=True)

# --- YENİ SİTE KAYIT (GENİŞLETİLMİŞ KURUMSAL KAYIT) ---
elif st.session_state.sayfa == 'Kayıt':
    st.title("📝 Kurumsal Site Kurulumu")
    
    with st.form("yeni_kayit_formu"):
        st.markdown("#### 1. Site ve Kurum Bilgileri")
        c1, c2 = st.columns(2)
        with c1:
            site_adi = st.text_input("Site / Apartman Adı")
            adres = st.text_area("Açık Adres", height=100)
            telefon = st.text_input("Yönetim İletişim Numarası")
        with c2:
            vergi_no = st.text_input("Vergi Numarası / Dairesi")
            s_eposta = st.text_input("Kurumsal E-Posta Adresi")
            # LOGO YÜKLEME VE BASE64 ÇEVİRME
            logo_file = st.file_uploader("Site Logosu Yükle (Makbuzlar İçin)", type=['png', 'jpg', 'jpeg'])

        st.divider()
        st.markdown("#### 2. Mimari Yapı")
        blok_adedi = st.number_input("Blok Adedi", min_value=1, step=1)
        blok_verileri = []
        c_b1, c_b2 = st.columns(2)
        # Sadece ilk bloğu örnek olarak formda doldurtalım ki çok uzamasın (Gerçekte döngüyle de yapılabilir ama form içinde döngü kısıtlıdır, o yüzden manuel 1 adet blok girişini örnek tutalım veya basit liste kullanalım. Basitlik için Blok sayısı kadar daireyi aynı varsayalım)
        # Form kısıtlamasından dolayı blok eklemeyi basitleştiriyoruz
        standart_daire = st.number_input("Her Bloktaki Ortalama Daire Sayısı", min_value=1)
        
        st.divider()
        st.markdown("#### 3. Yönetici ve Güvenlik Bilgileri")
        c_y1, c_y2 = st.columns(2)
        with c_y1:
            y_k = st.text_input("Yönetici Kullanıcı Adı")
            y_eposta = st.text_input("Yönetici Şahsi E-Posta (Şifre Sıfırlama İçin ÖNEMLİ!)")
        with c_y2:
            y_s = st.text_input("Giriş Şifresi", type="password")
            y_s_t = st.text_input("Şifre Tekrarı", type="password")
            
        if st.form_submit_button("Sistemi Kur ve Kaydet", type="primary"):
            if y_s == y_s_t and site_adi and y_k and y_eposta:
                # Logoyu base64'e çevir (Veritabanında yer kaplamadan durur)
                logo_b64 = ""
                if logo_file: logo_b64 = base64.b64encode(logo_file.read()).decode()

                tenant_db = f"{site_adi.replace(' ', '_').lower()}_db.sqlite"
                conn = sqlite3.connect('master.db'); c = conn.cursor()
                
                # SİTEYİ KAYDET
                c.execute("""INSERT INTO siteler 
                             (site_adi, tenant_db_adi, adres, vergi_no, telefon, eposta, logo) 
                             VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                          (site_adi, tenant_db, adres, vergi_no, telefon, s_eposta, logo_b64))
                conn.commit(); conn.close()
                
                init_tenant_db(tenant_db)
                conn_t = sqlite3.connect(tenant_db); ct = conn_t.cursor()
                
                # BLOKLARI KAYDET
                for i in range(int(blok_adedi)):
                    b_isim = f"{chr(65+i)} Blok" # A Blok, B Blok otomatik üretilir
                    ct.execute("INSERT INTO bloklar (blok_adi, daire_sayisi) VALUES (?, ?)", (b_isim, standart_daire))
                
                # YÖNETİCİYİ KAYDET
                ct.execute("INSERT INTO yoneticiler (kullanici_adi, sifre, eposta) VALUES (?, ?, ?)", (y_k, y_s, y_eposta))
                
                conn_t.commit(); conn_t.close()
                st.success("Kurumsal Sistem başarıyla kuruldu! Giriş yapabilirsiniz."); sayfa_degistir('Giriş'); st.rerun()
            else: 
                st.error("Lütfen şifrelerin uyuştuğundan ve zorunlu alanların (Ad, Kullanıcı Adı, Yönetici E-Posta) dolduğundan emin olun.")
                
    st.button("⬅️ Geri Dön", on_click=sayfa_degistir, args=('Giriş',))

# --- ANA SAYFA ---
elif st.session_state.sayfa == 'Ana_Sayfa':
    db_yolu = st.session_state.aktif_db
    col_t, col_l = st.columns([4, 1])
    with col_t: st.title(f"🏢 {st.session_state.aktif_site}")
    with col_l:
        st.write("") 
        if st.button("🚪 Güvenli Çıkış", type="primary", use_container_width=True, key="universal_logout"):
            st.session_state.clear(); st.rerun()
    st.divider()

    if st.session_state.rol == "Yönetici":
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13, tab14 = st.tabs([
            "➕ Sakin", "📋 Liste", "👤 Kişi", "💰 Tahakkuk", 
            "✅ Tahsilat", "💳 Gider", "📊 Analiz", "📥 Rapor", "🔧 Güncelle", 
            "🚨 Gecikmeler", "⚖️ Hukuki", "👥 Personel", "📦 Demirbaş", "⚙️ Ayarlar"
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
        with tab11: hukuki.goster(db_yolu)
        with tab12: personel.goster(db_yolu)
        with tab13: demirbas.goster(db_yolu)
        with tab14: ayarlar.goster(db_yolu, 'master.db', st.session_state.aktif_site) # <--- YENİ EKLENDİ

    elif st.session_state.rol == "Sakin":
        import sakin_panel
        sakin_panel.goster(db_yolu, st.session_state.aktif_site, st.session_state.sakin_bilgi)
