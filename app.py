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
from pathlib import Path

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

# Ödeme / ürün sayfası (Shopier, Stripe, kendi siteniz — adresi güncelleyin)
SATINAL_ODEME_URL = "https://example.com/sitemaster-satin-al"

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

if 'sayfa' not in st.session_state:
    st.session_state.sayfa = 'Satın_Al'


def sayfa_degistir(yeni_sayfa):
    st.session_state.sayfa = yeni_sayfa


def guvenli_cikis():
    st.session_state.clear()
    st.session_state.sayfa = 'Vitrin'
    st.rerun()


def sm_dis_ekran_css():
    st.markdown(
        """
        <style>
        .sm-login-hero h1 {
            font-size: clamp(1.4rem, 3vw, 1.75rem);
            font-weight: 700;
            letter-spacing: -0.03em;
            color: #0f172a;
            margin: 0.25rem 0 0.35rem;
        }
        .sm-login-hero p {
            color: #64748b;
            font-size: 0.98rem;
            margin: 0 auto;
            max-width: 36rem;
            line-height: 1.55;
        }
        .sm-login-hero { text-align: center; }
        .sm-login-panel {
            background: linear-gradient(160deg, #f8fafc 0%, #f1f5f9 100%);
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 1.1rem 1.15rem;
            margin-bottom: 0.75rem;
        }
        .sm-login-panel h2 {
            font-size: 0.95rem;
            font-weight: 600;
            color: #0f172a;
            margin: 0 0 0.65rem;
            letter-spacing: -0.01em;
        }
        .sm-feat {
            display: flex;
            gap: 0.7rem;
            padding: 0.55rem 0;
            border-top: 1px solid #e2e8f0;
        }
        .sm-feat:first-of-type { border-top: none; padding-top: 0; }
        .sm-feat-ic { font-size: 1.2rem; line-height: 1.2; flex-shrink: 0; opacity: 0.92; }
        .sm-feat b { display: block; color: #0f172a; font-size: 0.9rem; margin-bottom: 0.15rem; }
        .sm-feat span { color: #64748b; font-size: 0.82rem; line-height: 1.45; }
        .sm-satin-ust {
            text-align: center;
            max-width: 32rem;
            margin: 0 auto 1.25rem;
        }
        .sm-satin-ust p { color: #64748b; font-size: 0.95rem; line-height: 1.55; margin: 0.5rem 0 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --- 1) SATIN ALMA (uygulamayı açan ilk ekran) ---
if st.session_state.sayfa == 'Satın_Al':
    sm_dis_ekran_css()
    st.markdown(
        '<div class="sm-login-hero"><h1>SiteMaster</h1>'
        "<p>Apartman ve site yönetimi için masaüstü programı. Önce lisans satın alın, ardından panelden site oluşturup giriş yapın.</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sm-satin-ust"><p><b>Neler dahil?</b> Aidat ve tahsilat, gider, sakin kayıtları, rapor ve banka ekstresi modülleri tek uygulamada.</p></div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        try:
            st.link_button(
                "Programı satın al (ödeme sayfası)",
                SATINAL_ODEME_URL,
                type="primary",
                use_container_width=True,
            )
        except Exception:
            st.markdown(f"[Programı satın al — ödeme bağlantısı]({SATINAL_ODEME_URL})")
        if st.button(
            "Satın aldım — panele geç",
            type="secondary",
            use_container_width=True,
            help="Ödeme tamamlandıktan sonra site oluşturma ve giriş ekranına gidersiniz.",
        ):
            sayfa_degistir('Vitrin')
            st.rerun()
        st.caption(
            "Geliştirme / deneme: Yukarıdaki ödeme linkini kendi mağaza adresinizle değiştirin (`SATINAL_ODEME_URL`)."
        )

# --- 2) VİTRİN: reklam + yönlendirme (site yok → kayıt, var → giriş) ---
elif st.session_state.sayfa == 'Vitrin':
    sm_dis_ekran_css()

    logo_path = next(
        (p for p in ("logo.png", "logo.png.png", "assets/logo.png") if Path(p).exists()),
        None,
    )

    _t1, _t2, _t3 = st.columns([1, 2, 1])
    with _t2:
        if logo_path:
            st.image(logo_path, use_container_width=True)
            st.markdown(
                '<p style="text-align:center;color:#64748b;font-size:0.98rem;margin:0.35rem 0 0;line-height:1.5">'
                "Apartman ve site yönetimi — aidat, tahsilat ve operasyon."
                "</p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="sm-login-hero"><h1>SiteMaster</h1><p>Apartman ve site yönetimi: aidat, tahsilat, gider ve sakin işlemleri tek panelde.</p></div>',
                unsafe_allow_html=True,
            )

    st.divider()

    st.markdown(
        '<p style="text-align:center;color:#475569;font-size:1rem;margin:0 0 0.25rem">'
        "<b>Site kaydınız yoksa</b> soldan oluşturun; <b>varsa</b> sağdan siteyi seçip giriş yapın.</p>",
        unsafe_allow_html=True,
    )

    conn = sqlite3.connect('master.db')
    df_siteler = pd.read_sql_query("SELECT site_adi, tenant_db_adi FROM siteler", conn)
    conn.close()

    col_yeni, col_giris = st.columns([1, 1], gap="large")

    with col_yeni:
        st.markdown("##### Siteniz yok mu?")
        st.caption("İlk kez kurulum: apartman / site bilgileri ve yönetici hesabı oluşturulur.")
        st.markdown(
            """
            <div class="sm-login-panel">
            <h2>Programda neler var?</h2>
            <div class="sm-feat"><div class="sm-feat-ic">📊</div><div><b>Finans</b><span>Dashboard, tahakkuk ve tahsilat.</span></div></div>
            <div class="sm-feat"><div class="sm-feat-ic">🏦</div><div><b>Banka & gider</b><span>Ekstre ve gider takibi.</span></div></div>
            <div class="sm-feat"><div class="sm-feat-ic">👥</div><div><b>Sakin işleri</b><span>Kayıt, liste, gecikme ve raporlar.</span></div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "Yeni site kaydı oluştur",
            on_click=sayfa_degistir,
            args=('Kayıt',),
            type="primary",
            use_container_width=True,
        )

    with col_giris:
        st.markdown("##### Kayıtlı siteye giriş")
        st.caption("Listeden sitenizi seçin; yönetici veya sakin olarak devam edin.")
        with st.container(border=True):
            if df_siteler.empty:
                st.info("Henüz kayıtlı site yok. Soldaki **Yeni site kaydı oluştur** ile başlayın.")
            else:
                giris_tab1, giris_tab2 = st.tabs(["Yönetici", "Sakin"])

                with giris_tab1:
                    sec_site = st.selectbox("Site", df_siteler['site_adi'].tolist(), key="adm_s")
                    k_adi = st.text_input("Kullanıcı adı")
                    sifre = st.text_input("Şifre", type="password")
                    if st.button("Giriş yap", type="primary", use_container_width=True):
                        db = df_siteler.loc[df_siteler['site_adi'] == sec_site, 'tenant_db_adi'].values[0]
                        conn_t = sqlite3.connect(db)
                        try:
                            ct = conn_t.cursor()
                            ct.execute(
                                "SELECT kullanici_adi FROM yoneticiler WHERE kullanici_adi=? AND sifre=?",
                                (k_adi, sifre),
                            )
                            if ct.fetchone():
                                st.session_state.aktif_site = sec_site
                                st.session_state.aktif_db = db
                                st.session_state.rol = "Yönetici"
                                sayfa_degistir('Ana_Sayfa')
                                st.rerun()
                            else:
                                st.error("Kullanıcı adı veya şifre hatalı.")
                        finally:
                            conn_t.close()

                    with st.expander("Şifremi unuttum"):
                        st.caption("Kayıtlı yönetici e-postanıza geçici şifre gönderilir (SMTP ayarları gerekir).")
                        f_site = st.selectbox("Site", df_siteler['site_adi'].tolist(), key="f_site")
                        f_eposta = st.text_input("Yönetici e-postası")

                        if st.button("Sıfırla ve mail gönder"):
                            if f_site and f_eposta:
                                f_db = df_siteler.loc[df_siteler['site_adi'] == f_site, 'tenant_db_adi'].values[0]
                                conn_t = sqlite3.connect(f_db)
                                ct = conn_t.cursor()
                                ct.execute("SELECT id FROM yoneticiler WHERE eposta=?", (f_eposta,))
                                if ct.fetchone():
                                    yeni_sifre = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                                    with st.spinner("Mail sunucusuna bağlanılıyor..."):
                                        mail_gitti_mi = sifre_sifirlama_maili_gonder(f_eposta, yeni_sifre, f_site)
                                    if mail_gitti_mi:
                                        ct.execute("UPDATE yoneticiler SET sifre=? WHERE eposta=?", (yeni_sifre, f_eposta))
                                        conn_t.commit()
                                        st.success("Yeni şifre e-postanıza gönderildi. Gerekirse spam klasörüne bakın.")
                                else:
                                    st.error("Bu e-posta ile kayıt bulunamadı.")
                                conn_t.close()
                            else:
                                st.warning("Site ve e-posta alanlarını doldurun.")

                with giris_tab2:
                    sec_site_s = st.selectbox("Site", df_siteler['site_adi'].tolist(), key="sak_s")
                    db_s = df_siteler.loc[df_siteler['site_adi'] == sec_site_s, 'tenant_db_adi'].values[0]
                    conn_s = sqlite3.connect(db_s)
                    try:
                        df_bl = pd.read_sql_query("SELECT DISTINCT blok FROM sakinler", conn_s)
                        if df_bl.empty:
                            st.warning("Bu sitede kayıtlı sakin yok.")
                        else:
                            s_bl = st.selectbox("Blok", df_bl['blok'].tolist())
                            df_dr = pd.read_sql_query(
                                "SELECT daire_no FROM sakinler WHERE blok = ? ORDER BY daire_no",
                                conn_s,
                                params=[s_bl],
                            )
                            s_dr = st.selectbox("Daire", df_dr['daire_no'].tolist())
                            s_sif = st.text_input("Sakin şifresi", type="password", key="sak_pass")
                            if st.button("Sakin paneline gir", type="primary", use_container_width=True):
                                ct = conn_s.cursor()
                                ct.execute(
                                    "SELECT malik_ad FROM sakinler WHERE blok=? AND daire_no=? AND sifre=?",
                                    (s_bl, s_dr, s_sif),
                                )
                                res = ct.fetchone()
                                if res:
                                    st.session_state.aktif_site = sec_site_s
                                    st.session_state.aktif_db = db_s
                                    st.session_state.rol = "Sakin"
                                    st.session_state.sakin_bilgi = {"blok": s_bl, "daire": s_dr, "isim": res[0]}
                                    sayfa_degistir('Ana_Sayfa')
                                    st.rerun()
                                else:
                                    st.error("Şifre hatalı.")
                    except Exception:
                        st.error("Sakin listesi yüklenirken bir hata oluştu.")
                    finally:
                        conn_s.close()

    st.divider()
    if st.button("Lisans ve satın alma ekranına dön", key="sm_vitrin_satin"):
        sayfa_degistir('Satın_Al')
        st.rerun()

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
                st.success("Kurumsal Sistem başarıyla kuruldu! Giriş yapabilirsiniz."); sayfa_degistir('Vitrin'); st.rerun()
            else: 
                st.error("Lütfen şifrelerin uyuştuğundan ve zorunlu alanların dolduğundan emin olun.")
                
    st.button("⬅️ Geri Dön", on_click=sayfa_degistir, args=('Vitrin',))

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
                guvenli_cikis()

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
                guvenli_cikis()
                
        sakin_panel.goster(db_yolu, st.session_state.aktif_site, st.session_state.sakin_bilgi)
