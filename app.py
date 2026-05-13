import streamlit as st
import pandas as pd
import sqlite3
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
import datetime

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
import ayarlar
import banka
import aktar  # ice_aktar yerine senin değiştirdiğin aktar ismini kullanıyoruz

# --- MAİL GÖNDERME MOTORU (SMTP) ---
def sifre_sifirlama_maili_gonder(alici_eposta, yeni_sifre, site_adi):
    # KANKAM BURAYI KENDİ BİLGİLERİNLE DOLDUR:
    gonderici_eposta = "senin_mail_adresin@gmail.com" 
    gonderici_sifre = "BURAYA_16_HANELİ_GOOGLE_UYGULAMA_SİFRESİNİ_YAZ"

    try:
        msg = MIMEMultipart()
        msg['From'] = gonderici_eposta
        msg['To'] = alici_eposta
        msg['Subject'] = f"{site_adi} - SiteMaster Şifre Sıfırlama"

        govde = f"""
        Merhaba,
        
        {site_adi} yönetici panelinize giriş yapabilmeniz için şifreniz sıfırlanmıştır.
        
        Yeni Geçici Şifreniz: {yeni_sifre}
        
        Lütfen sisteme giriş yaptıktan sonra sağ üstteki 'Ayarlar' sekmesinden şifrenizi güvenli bir şifre ile değiştiriniz.
        
        Güvenli günler dileriz.
        🏢 SiteMaster Otomasyon Sistemi
        """
        msg.attach(MIMEText(govde, 'plain', 'utf-8'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gonderici_eposta, gonderici_sifre)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Mail gönderim hatası: Sistemsel bir hata oluştu. (Hata Detayı: {e})")
        return False

# --- VERİTABANI VE SİSTEM AYARLARI ---
def init_master_db():
    conn = sqlite3.connect('master.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS siteler (id INTEGER PRIMARY KEY AUTOINCREMENT, site_adi TEXT UNIQUE, tenant_db_adi TEXT)''')
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
    
    # Otomatik Tahakkuk Tabloları
    c.execute('''CREATE TABLE IF NOT EXISTS otomatik_talimatlar (id INTEGER PRIMARY KEY AUTOINCREMENT, tutar REAL, aciklama TEXT, durum INTEGER DEFAULT 1)''')
    c.execute('''CREATE TABLE IF NOT EXISTS otomatik_kayitlar (id INTEGER PRIMARY KEY AUTOINCREMENT, ay_yil TEXT UNIQUE)''')
    
    conn.commit()
    conn.close()

# --- SESSİZ ÇALIŞAN OTOMATİK BORÇLANDIRMA MOTORU ---
def otomatik_borclandir_motoru(db_yolu):
    bugun = datetime.date.today()
    ay_yil = bugun.strftime("%m-%Y")

    conn = sqlite3.connect(db_yolu)
    c = conn.cursor()

    c.execute("SELECT id FROM otomatik_kayitlar WHERE ay_yil=?", (ay_yil,))
    if not c.fetchone():
        c.execute("SELECT tutar, aciklama FROM otomatik_talimatlar WHERE durum=1 LIMIT 1")
        talimat = c.fetchone()
        
        if talimat:
            tutar, sablon_aciklama = talimat
            aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
            guncel_aciklama = f"{aylar[bugun.month-1]} {bugun.year} {sablon_aciklama}"
            
            c.execute("SELECT blok, daire_no FROM sakinler")
            sakinler = c.fetchall()
            
            for s in sakinler:
                son_tarih = (bugun + datetime.timedelta(days=10)).strftime("%Y-%m-%d")
                c.execute("""INSERT INTO aidatlar 
                             (blok, daire_no, tarih, tutar, aciklama, son_odeme_tarihi, faiz_uygula, yillik_faiz) 
                             VALUES (?,?,?,?,?,?,?,?)""", 
                          (s[0], s[1], str(bugun), tutar, guncel_aciklama, son_tarih, 1, 60.0))
            
            c.execute("INSERT INTO otomatik_kayitlar (ay_yil) VALUES (?)", (ay_yil,))
            conn.commit()
    conn.close()

# --- ANA SİSTEM BAŞLATMA ---
init_master_db()

st.set_page_config(page_title="SiteMaster", page_icon="🏢", layout="wide")

# 👇 İŞTE HATAYA SEBEP OLAN, YANLIŞLIKLA SİLDİĞİMİZ O SİGORTA KODU BURADA 👇
if 'sayfa' not in st.session_state: 
    st.session_state.sayfa = 'Giriş'

def sayfa_degistir(yeni_sayfa): 
    st.session_state.sayfa = yeni_sayfa

# --- GİRİŞ SAYFASI (YENİ VİTRİN TASARIMI) ---
if st.session_state.sayfa == 'Giriş':
    
    st.markdown("""
        <style>
        .vitrin-baslik { font-size: 28px; font-weight: bold; color: #10b981; margin-bottom: 10px; }
        .vitrin-alt-baslik { font-size: 18px; color: #64748b; margin-bottom: 30px; }
        .ozellik-kutu { padding: 15px; border-radius: 10px; background-color: rgba(16, 185, 129, 0.1); border-left: 5px solid #10b981; margin-bottom: 15px; }
        </style>
    """, unsafe_allow_html=True)

    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        try:
            st.image("logo.png", use_container_width=True)
        except:
            st.title("🏢 SİTEMASTER")
    
    st.divider()

    col_sol, col_bosluk, col_sag = st.columns([1.2, 0.1, 1])

    with col_sol:
        st.markdown('<div class="vitrin-baslik">Yeni Nesil Tesis ve Finans Yönetimi</div>', unsafe_allow_html=True)
        st.markdown('<div class="vitrin-alt-baslik">Yapay zeka destekli otonom sistem ile sitenizi tek tıkla yönetin, tahsilatlarınızı garanti altına alın.</div>', unsafe_allow_html=True)
        
        st.markdown("""
        <div class="ozellik-kutu">
            <b>💰 Akıllı Tahsilat & Borçlandırma</b><br>
            Sıfır hata ile toplu aidat tahakkuku, otomatik gecikme faizi ve şeffaf bakiye takibi.
        </div>
        <div class="ozellik-kutu">
            <b>🏦 Banka API & Ekstre Entegrasyonu</b><br>
            Banka hareketlerini saniyeler içinde okuyan ve sakinlerin hesaplarına otomatik işleyen yapay zeka motoru.
        </div>
        <div class="ozellik-kutu">
            <b>📦 Demirbaş ve Personel Otomasyonu</b><br>
            Zimmet takibi, bakım geçmişi ve personel puantajının tek bir ekrandan kurumsal yönetimi.
        </div>
        """, unsafe_allow_html=True)
        
        st.button("🏢 Yeni Kurumsal Site Kaydı Oluştur", on_click=sayfa_degistir, args=('Kayıt',), type="secondary", use_container_width=True)

    with col_sag:
        st.markdown("#### 🔒 Sisteme Giriş Yapın")
        
        conn = sqlite3.connect('master.db')
        df_siteler = pd.read_sql_query("SELECT site_adi, tenant_db_adi FROM siteler", conn)
        conn.close()
        
        giris_tab1, giris_tab2 = st.tabs(["🔑 Yönetici", "🏠 Sakin"])
        
        with giris_tab1:
            with st.container(border=True):
                if not df_siteler.empty:
                    sec_site = st.selectbox("Site Seçiniz", df_siteler['site_adi'].tolist(), key="adm_s")
                    k_adi = st.text_input("Kullanıcı Adı")
                    sifre = st.text_input("Şifre", type="password")
                    if st.button("Sisteme Gir", type="primary", use_container_width=True):
                        db = df_siteler.loc[df_siteler['site_adi'] == sec_site, 'tenant_db_adi'].values[0]
                        conn_t = sqlite3.connect(db); ct = conn_t.cursor()
                        ct.execute("SELECT kullanici_adi FROM yoneticiler WHERE kullanici_adi=? AND sifre=?", (k_adi, sifre))
                        if ct.fetchone():
                            st.session_state.aktif_site = sec_site; st.session_state.aktif_db = db; st.session_state.rol = "Yönetici"
                            sayfa_degistir('Ana_Sayfa'); st.rerun()
                        else: st.error("Hatalı bilgiler!")
            
            with st.expander("🆘 Şifremi Unuttum"):
                st.caption("Kayıtlı E-Posta adresinizi girin. Yeni şifreniz mail olarak gönderilecektir.")
                f_site = st.selectbox("Sitenizi Seçin", df_siteler['site_adi'].tolist() if not df_siteler.empty else [], key="f_site")
                f_eposta = st.text_input("Yönetici Kayıt E-Postası")
                
                if st.button("Şifremi Sıfırla ve Mail Gönder"):
                    if f_site and f_eposta:
                        f_db = df_siteler.loc[df_siteler['site_adi'] == f_site, 'tenant_db_adi'].values[0]
                        conn_t = sqlite3.connect(f_db); ct = conn_t.cursor()
                        ct.execute("SELECT id FROM yoneticiler WHERE eposta=?", (f_eposta,))
                        if ct.fetchone():
                            yeni_sifre = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                            with st.spinner("Mail sunucusuna bağlanılıyor..."):
                                mail_gitti_mi = sifre_sifirlama_maili_gonder(f_eposta, yeni_sifre, f_site)
                            if mail_gitti_mi:
                                ct.execute("UPDATE yoneticiler SET sifre=? WHERE eposta=?", (yeni_sifre, f_eposta))
                                conn_t.commit()
                                st.success("✅ Yeni şifreniz E-Posta adresinize gönderildi! (Spam klasörünü kontrol edin).")
                        else: st.error("Kayıt bulunamadı!")
                        conn_t.close()

        with giris_tab2:
            with st.container(border=True):
                if not df_siteler.empty:
                    sec_site_s = st.selectbox("Sitenizi Seçiniz", df_siteler['site_adi'].tolist(), key="sak_s")
                    db_s = df_siteler.loc[df_siteler['site_adi'] == sec_site_s, 'tenant_db_adi'].values[0]
                    conn_s = sqlite3.connect(db_s)
                    try:
                        df_bl = pd.read_sql_query("SELECT DISTINCT blok FROM sakinler", conn_s)
                        if not df_bl.empty:
                            s_bl = st.selectbox("Blok", df_bl['blok'].tolist())
                            df_dr = pd.read_sql_query(f"SELECT daire_no FROM sakinler WHERE blok='{s_bl}'", conn_s)
                            s_dr = st.selectbox("Daire No", df_dr['daire_no'].tolist())
                            s_sif = st.text_input("Şifreniz", type="password", key="sak_pass")
                            if st.button("Sakin Paneline Gir", type="primary", use_container_width=True):
                                ct = conn_s.cursor()
                                ct.execute("SELECT malik_ad FROM sakinler WHERE blok=? AND daire_no=? AND sifre=?", (s_bl, s_dr, s_sif))
                                res = ct.fetchone()
                                if res:
                                    st.session_state.aktif_site = sec_site_s; st.session_state.aktif_db = db_s; st.session_state.rol = "Sakin"
                                    st.session_state.sakin_bilgi = {"blok": s_bl, "daire": s_dr, "isim": res[0]}
                                    sayfa_degistir('Ana_Sayfa'); st.rerun()
                                else: st.error("Hatalı şifre!")
                        else: st.warning("Kayıtlı sakin bulunamadı.")
                    except: pass
                    conn_s.close()

# --- YENİ SİTE KAYIT ---
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
            logo_file = st.file_uploader("Site Logosu Yükle (Makbuzlar İçin)", type=['png', 'jpg', 'jpeg'])

        st.divider()
        st.markdown("#### 2. Mimari Yapı")
        blok_adedi = st.number_input("Blok Adedi", min_value=1, step=1)
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
                logo_b64 = ""
                if logo_file: logo_b64 = base64.b64encode(logo_file.read()).decode()

                tenant_db = f"{site_adi.replace(' ', '_').lower()}_db.sqlite"
                conn = sqlite3.connect('master.db'); c = conn.cursor()
                
                c.execute("""INSERT INTO siteler 
                             (site_adi, tenant_db_adi, adres, vergi_no, telefon, eposta, logo) 
                             VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                          (site_adi, tenant_db, adres, vergi_no, telefon, s_eposta, logo_b64))
                conn.commit(); conn.close()
                
                init_tenant_db(tenant_db)
                conn_t = sqlite3.connect(tenant_db); ct = conn_t.cursor()
                
                for i in range(int(blok_adedi)):
                    b_isim = f"{chr(65+i)} Blok"
                    ct.execute("INSERT INTO bloklar (blok_adi, daire_sayisi) VALUES (?, ?)", (b_isim, standart_daire))
                
                ct.execute("INSERT INTO yoneticiler (kullanici_adi, sifre, eposta) VALUES (?, ?, ?)", (y_k, y_s, y_eposta))
                
                conn_t.commit(); conn_t.close()
                st.success("Kurumsal Sistem başarıyla kuruldu! Giriş yapabilirsiniz."); sayfa_degistir('Giriş'); st.rerun()
            else: 
                st.error("Lütfen şifrelerin uyuştuğundan ve zorunlu alanların dolduğundan emin olun.")
                
    st.button("⬅️ Geri Dön", on_click=sayfa_degistir, args=('Giriş',))

# --- ANA SAYFA ---
elif st.session_state.sayfa == 'Ana_Sayfa':
    db_yolu = st.session_state.aktif_db
    
    # Sisteme girildiği an otomatik borçlandırma kontrolü yapılır
    otomatik_borclandir_motoru(db_yolu)
    
    st.title(f"🏢 {st.session_state.aktif_site}")
    st.divider()

    if st.session_state.rol == "Yönetici":
        with st.sidebar:
            if st.session_state.get('logo_b64'):
                st.image(f"data:image/png;base64,{st.session_state.logo_b64}", use_container_width=True)
            
            st.markdown("### 🧭 Menü")
            secim = st.radio(
                "İşlem Seçiniz:",
                [
                    "📊 Analiz (Dashboard)",
                    "➕ Sakin Kayıt", 
                    "📋 Liste", 
                    "👤 Kişi Kartı", 
                    "💰 Tahakkuk", 
                    "✅ Tahsilat", 
                    "💳 Gider", 
                    "📥 Rapor", 
                    "🔧 Güncelle", 
                    "🚨 Gecikmeler", 
                    "⚖️ Hukuki", 
                    "👥 Personel", 
                    "📦 Demirbaş", 
                    "🏦 Banka Ekstresi",
                    "📥 Veri Aktar",
                    "⚙️ Ayarlar"
                ]
            )
            
            st.divider()
            if st.button("🚪 Güvenli Çıkış", type="primary", use_container_width=True, key="universal_logout"):
                st.session_state.clear()
                st.rerun()

        if secim == "📊 Analiz (Dashboard)": dashboard.goster(db_yolu)
        elif secim == "➕ Sakin Kayıt": sakin_kayit.goster(db_yolu)
        elif secim == "📋 Liste": liste.goster(db_yolu)
        elif secim == "👤 Kişi Kartı": kisikart.goster(db_yolu)
        elif secim == "💰 Tahakkuk": borclandirma.goster(db_yolu)
        elif secim == "✅ Tahsilat": tahsilat.goster(db_yolu, st.session_state.aktif_site)
        elif secim == "💳 Gider": gider.goster(db_yolu)
        elif secim == "📥 Rapor": rapor.goster(db_yolu, st.session_state.aktif_site)
        elif secim == "🔧 Güncelle": sakin_guncelle.goster(db_yolu)
        elif secim == "🚨 Gecikmeler": gecikmeler.goster(db_yolu, st.session_state.aktif_site)
        elif secim == "⚖️ Hukuki": hukuki.goster(db_yolu)
        elif secim == "👥 Personel": personel.goster(db_yolu)
        elif secim == "📦 Demirbaş": demirbas.goster(db_yolu)
        elif secim == "🏦 Banka Ekstresi": banka.goster(db_yolu)
        elif secim == "📥 Veri Aktar": aktar.goster(db_yolu) # Senin değiştirdiğin aktar modülü
        elif secim == "⚙️ Ayarlar": ayarlar.goster(db_yolu, 'master.db', st.session_state.aktif_site)

    elif st.session_state.rol == "Sakin":
        import sakin_panel
        with st.sidebar:
            st.markdown("### 🏠 Sakin Menüsü")
            if st.button("🚪 Güvenli Çıkış", type="primary", use_container_width=True):
                st.session_state.clear()
                st.rerun()
                
        sakin_panel.goster(db_yolu, st.session_state.aktif_site, st.session_state.sakin_bilgi)
