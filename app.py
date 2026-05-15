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
from werkzeug.security import generate_password_hash, check_password_hash

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
import tr_adres
from utils import get_conn, telefon_normalize

# Tanıtım videosu: YouTube/Vimeo linki veya None. Ayrıca aşağıdaki yerel dosya yolu doluysa oynatılır.
TANITIM_VIDEO_URL = None  # örn. "https://www.youtube.com/watch?v=..."
TANITIM_VIDEO_DOSYA = "assets/tanitim.mp4"  # proje köküne göre; yoksa yer tutucu gösterilir

# Landing page adresi — index.html'nin servis edildiği URL (VS Code Live Server: 5500, python -m http.server: 8000)
LANDING_URL = "http://localhost:8000/index.html"
LANDING_KAYIT = "http://localhost:8000/kayit.html"

# --- MAİL GÖNDERME MOTORU (SMTP) ---
def sifre_sifirlama_maili_gonder(alici_eposta, yeni_sifre, site_adi):
    try:
        gonderici_eposta = st.secrets["smtp"]["gonderici_eposta"]
        gonderici_sifre  = st.secrets["smtp"]["gonderici_sifre"]
    except KeyError:
        st.error("SMTP ayarları eksik. Lütfen .streamlit/secrets.toml dosyasını doldurun.")
        return False

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
    conn = get_conn('master.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS siteler (id INTEGER PRIMARY KEY AUTOINCREMENT, site_adi TEXT UNIQUE, tenant_db_adi TEXT)''')
    for col_def in [
        "ALTER TABLE siteler ADD COLUMN adres TEXT",
        "ALTER TABLE siteler ADD COLUMN vergi_no TEXT",
        "ALTER TABLE siteler ADD COLUMN telefon TEXT",
        "ALTER TABLE siteler ADD COLUMN eposta TEXT",
        "ALTER TABLE siteler ADD COLUMN logo TEXT",
        "ALTER TABLE siteler ADD COLUMN il TEXT",
        "ALTER TABLE siteler ADD COLUMN ilce TEXT",
        "ALTER TABLE siteler ADD COLUMN mahalle TEXT",
    ]:
        try:
            c.execute(col_def)
        except Exception:
            pass
    conn.commit()
    conn.close()


def init_tenant_db(db_name):
    conn = get_conn(db_name)
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

    conn = get_conn(db_yolu)
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
    st.session_state.sayfa = 'Vitrin'
if 'odeme_tamamlandi' not in st.session_state:
    st.session_state.odeme_tamamlandi = False

# Dış link: /?p=odeme veya /?p=kayit (ödeme sonrası kurulum)
_qp = st.query_params.get('p', '')
if _qp == 'odeme':
    st.session_state.sayfa = 'Odeme'
    st.query_params.clear()
    st.rerun()
if _qp == 'kayit':
    if st.session_state.get('odeme_tamamlandi'):
        st.session_state.sayfa = 'Kayıt'
    else:
        st.session_state.sayfa = 'Odeme'
    st.query_params.clear()
    st.rerun()


def sayfa_degistir(yeni_sayfa):
    st.session_state.sayfa = yeni_sayfa


def guvenli_cikis():
    st.session_state.clear()
    st.session_state.sayfa = 'Vitrin'
    st.rerun()


def form_alan_css():
    """Giriş, ödeme ve kayıt formlarında alanların okunaklı görünmesi."""
    return """
    [data-testid="stWidgetLabel"] p,
    [data-testid="stWidgetLabel"] label {
        color: #334155 !important;
        font-weight: 600 !important;
    }
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input {
        background-color: #ffffff !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        caret-color: #0f172a !important;
        border: 1px solid #94a3b8 !important;
        border-radius: 8px !important;
        min-height: 2.75rem !important;
        opacity: 1 !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] {
        background-color: #ffffff !important;
        border: 1px solid #94a3b8 !important;
        border-radius: 8px !important;
        min-height: 2.75rem !important;
    }
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] span {
        color: #0f172a !important;
        background-color: transparent !important;
    }
    [data-testid="stFileUploader"] section {
        background: #f8fafc !important;
        border: 1px dashed #94a3b8 !important;
        border-radius: 8px !important;
    }
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span {
        color: #475569 !important;
    }
    """


def public_sayfa_css():
    st.markdown(f"""
    <style>
    .stApp, [data-testid="stAppViewContainer"] {{
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }}
    [data-testid="stHeader"] {{ background: transparent !important; }}
    .main h1, .main h2, .main h3, .main h4, .main p {{
        color: #0f172a !important;
    }}
    [data-testid="stVerticalBlockBorderWrapper"] {{
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,.08) !important;
        padding: 0.75rem 1.25rem 1.25rem !important;
    }}
    [data-testid="stForm"] {{
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 1.25rem 1.5rem !important;
    }}
    {form_alan_css()}
    </style>
    """, unsafe_allow_html=True)


def odeme_sayfa_css():
    st.markdown("""
    <style>
    .stApp { background-color: #f8fafc !important; }
    .odeme-baslik { text-align: center; margin: 0 0 2rem; }
    .odeme-baslik h2 {
        font-size: 1.75rem; font-weight: 800; color: #0f172a !important;
        letter-spacing: -0.03em; margin: 0 0 0.4rem;
    }
    .odeme-baslik p { color: #64748b !important; font-size: 1rem; margin: 0; }
    .sm-price-card {
        background: #ffffff;
        border: 1.5px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.75rem 1.5rem 1.5rem;
        min-height: 420px;
        display: flex;
        flex-direction: column;
        box-shadow: 0 1px 3px rgba(15,23,42,.06);
    }
    .sm-price-card.popular {
        border-color: #2563eb;
        box-shadow: 0 4px 24px rgba(37,99,235,.18);
    }
    .sm-popular-badge {
        display: inline-block;
        background: #2563eb;
        color: #fff;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        padding: 0.28rem 0.85rem;
        border-radius: 99px;
        margin: -2.35rem auto 1rem;
        width: fit-content;
    }
    .sm-price-name {
        font-size: 0.8rem; font-weight: 700; color: #64748b !important;
        letter-spacing: 0.06em; text-transform: uppercase; margin: 0 0 0.6rem;
    }
    .sm-price-amount {
        font-size: 2.35rem; font-weight: 900; color: #0f172a !important;
        letter-spacing: -0.04em; line-height: 1; margin: 0;
    }
    .sm-price-amount sup { font-size: 1rem; font-weight: 700; }
    .sm-price-period {
        font-size: 0.8rem; color: #94a3b8 !important; margin: 0.35rem 0 1.25rem;
    }
    .sm-price-features {
        list-style: none; padding: 0; margin: 0 0 1rem; flex: 1;
    }
    .sm-price-features li {
        font-size: 0.875rem; color: #334155 !important;
        padding: 0.35rem 0; display: flex; align-items: flex-start; gap: 0.5rem;
    }
    .sm-price-features li::before {
        content: "✓"; color: #22c55e; font-weight: 800; flex-shrink: 0;
    }
    .sm-secili-plan {
        text-align: center; padding: 0.65rem 1rem; margin: 1rem 0;
        background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;
        color: #1e40af !important; font-size: 0.9rem; font-weight: 600;
    }
    .odeme-kart-baslik {
        font-size: 1.25rem; font-weight: 700; color: #0f172a !important;
        margin: 2rem 0 0.35rem; text-align: center;
    }
    .odeme-kart-alt {
        text-align: center; color: #64748b !important; font-size: 0.9rem;
        margin: 0 0 1.25rem;
    }
    [data-testid="stForm"] {
        background: #ffffff !important;
        border: 1.5px solid #e2e8f0 !important;
        border-radius: 14px !important;
        padding: 1.75rem 2rem 1.5rem !important;
        box-shadow: 0 4px 16px rgba(15,23,42,.06) !important;
    }
    [data-testid="stForm"] label,
    [data-testid="stForm"] [data-testid="stWidgetLabel"] p {
        color: #334155 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }
    [data-testid="stForm"] input {
        background: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }
    [data-testid="stForm"] input:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,.15) !important;
    }
    [data-testid="stForm"] [data-testid="stCaptionContainer"] p {
        color: #64748b !important;
    }
    """ + form_alan_css() + """
    </style>
    """, unsafe_allow_html=True)


# --- VİTRİN ---
if st.session_state.sayfa == 'Vitrin':
    public_sayfa_css()
    st.link_button("🏠 Tanıtım sayfasına dön", url=LANDING_URL, key="vitrin_landing_btn")

    conn = get_conn('master.db')
    df_siteler = pd.read_sql_query("SELECT site_adi, tenant_db_adi FROM siteler", conn)
    conn.close()

    with st.container(border=True):
        st.markdown("**Giriş**")
        st.caption("Mevcut sitenize yönetici veya sakin olarak bağlanın.")

        tab_y, tab_s = st.tabs(["Yönetici Girişi", "Sakin Girişi"])

        with tab_y:
            if df_siteler.empty:
                st.info(
                    "Henüz kayıtlı site yok. Aşağıdaki butondan plan seçerek yeni site oluşturabilirsiniz."
                )
            else:
                sec_site = st.selectbox("Site seçin", df_siteler['site_adi'].tolist(), key="sm_adm_site")
                k_adi = st.text_input("Kullanıcı adı", key="sm_adm_user")
                sifre = st.text_input("Şifre", type="password", key="sm_adm_pass")
                if st.button("Panele gir", type="primary", use_container_width=True, key="sm_adm_go"):
                    db = df_siteler.loc[df_siteler['site_adi'] == sec_site, 'tenant_db_adi'].values[0]
                    conn_t = get_conn(db)
                    try:
                        ct = conn_t.cursor()
                        ct.execute(
                            "SELECT kullanici_adi, sifre FROM yoneticiler WHERE kullanici_adi=?",
                            (k_adi,),
                        )
                        row = ct.fetchone()
                        if row and check_password_hash(row[1], sifre):
                            st.session_state.aktif_site = sec_site
                            st.session_state.aktif_db = db
                            st.session_state.rol = "Yönetici"
                            try:
                                _ml = get_conn('master.db')
                                _lr = _ml.execute("SELECT logo FROM siteler WHERE site_adi=?", (sec_site,)).fetchone()
                                _ml.close()
                                if _lr and _lr[0]:
                                    st.session_state.logo_b64 = _lr[0]
                            except Exception:
                                pass
                            sayfa_degistir('Ana_Sayfa')
                            st.rerun()
                        else:
                            st.error("Kullanıcı adı veya şifre hatalı.")
                    finally:
                        conn_t.close()

                with st.expander("Şifremi unuttum"):
                    st.caption("SMTP ayarlıysa e-postaya geçici şifre gönderilir.")
                    f_site = st.selectbox("Site", df_siteler['site_adi'].tolist(), key="sm_f_site")
                    f_eposta = st.text_input("Yönetici e-postası", key="sm_f_mail")

                    if st.button("Sıfırla ve mail gönder", key="sm_f_btn"):
                        if f_site and f_eposta:
                            f_db = df_siteler.loc[df_siteler['site_adi'] == f_site, 'tenant_db_adi'].values[0]
                            conn_t = get_conn(f_db)
                            ct = conn_t.cursor()
                            ct.execute("SELECT id FROM yoneticiler WHERE eposta=?", (f_eposta,))
                            if ct.fetchone():
                                yeni_sifre = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                                with st.spinner("Mail gönderiliyor..."):
                                    mail_gitti_mi = sifre_sifirlama_maili_gonder(f_eposta, yeni_sifre, f_site)
                                if mail_gitti_mi:
                                    ct.execute(
                                        "UPDATE yoneticiler SET sifre=? WHERE eposta=?",
                                        (generate_password_hash(yeni_sifre), f_eposta),
                                    )
                                    conn_t.commit()
                                    st.success("Yeni şifre e-postanıza gönderildi.")
                            else:
                                st.error("Bu e-posta ile kayıt bulunamadı.")
                            conn_t.close()
                        else:
                            st.warning("Site ve e-posta girin.")

        with tab_s:
            if df_siteler.empty:
                st.info(
                    "Henüz kayıtlı site yok. Aşağıdaki butondan plan seçerek önce site oluşturulmalıdır."
                )
            else:
                sec_site_s = st.selectbox("Site seçin", df_siteler['site_adi'].tolist(), key="sm_sak_site")
                db_s = df_siteler.loc[df_siteler['site_adi'] == sec_site_s, 'tenant_db_adi'].values[0]
                conn_s = get_conn(db_s)
                try:
                    df_bl = pd.read_sql_query("SELECT DISTINCT blok FROM sakinler", conn_s)
                    if df_bl.empty:
                        st.warning("Bu sitede kayıtlı sakin yok.")
                    else:
                        s_bl = st.selectbox("Blok", df_bl['blok'].tolist(), key="sm_sak_blok")
                        df_dr = pd.read_sql_query(
                            "SELECT daire_no FROM sakinler WHERE blok = ? ORDER BY daire_no",
                            conn_s,
                            params=[s_bl],
                        )
                        s_dr = st.selectbox("Daire", df_dr['daire_no'].tolist(), key="sm_sak_daire")
                        s_sif = st.text_input("Sakin şifresi", type="password", key="sm_sak_pass")
                        if st.button("Sakin paneline gir", type="primary", use_container_width=True, key="sm_sak_go"):
                            ct = conn_s.cursor()
                            ct.execute(
                                "SELECT malik_ad, sifre FROM sakinler WHERE blok=? AND daire_no=?",
                                (s_bl, s_dr),
                            )
                            res = ct.fetchone()
                            if res and check_password_hash(res[1], s_sif):
                                st.session_state.aktif_site = sec_site_s
                                st.session_state.aktif_db = db_s
                                st.session_state.rol = "Sakin"
                                st.session_state.sakin_bilgi = {
                                    "blok": s_bl,
                                    "daire": s_dr,
                                    "isim": res[0],
                                }
                                sayfa_degistir('Ana_Sayfa')
                                st.rerun()
                            else:
                                st.error("Şifre hatalı.")
                except Exception:
                    st.error("Sakin listesi yüklenirken hata oluştu.")
                finally:
                    conn_s.close()

    st.button(
        "Kayıt olmak için önce bir plan seçin →",
        on_click=sayfa_degistir,
        args=('Odeme',),
        type="secondary",
        use_container_width=True,
        key="sm_vitrin_btn_odeme",
    )

# --- ÖDEME SAYFASI ---
elif st.session_state.sayfa == 'Odeme':
    odeme_sayfa_css()
    public_sayfa_css()

    if "odeme_secilen_plan" not in st.session_state:
        st.session_state.odeme_secilen_plan = "Profesyonel — ₺999/ay"

    if st.button("← Plan seçimine dön", key="odeme_ust_geri"):
        st.session_state.sayfa = "Vitrin"
        st.rerun()

    st.markdown("""
    <div class="odeme-baslik">
        <h2>Şeffaf ve sabit fiyatlandırma</h2>
        <p>Gizli ücret yok. Siteye göre ölçeklenir.</p>
    </div>
    """, unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3, gap="large")

    with p1:
        st.markdown("""
        <div class="sm-price-card">
            <p class="sm-price-name">Başlangıç</p>
            <p class="sm-price-amount"><sup>₺</sup>499</p>
            <p class="sm-price-period">/ ay · tek site</p>
            <ul class="sm-price-features">
                <li>1 Site · 1 Blok</li>
                <li>Otonom borçlandırma</li>
                <li>Tahsilat takibi</li>
                <li>Sakin paneli</li>
                <li>E-posta desteği</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Satın Al", use_container_width=True, key="plan_sec_bas"):
            st.session_state.odeme_secilen_plan = "Başlangıç — ₺499/ay"
            st.rerun()

    with p2:
        st.markdown("""
        <div class="sm-price-card popular">
            <span class="sm-popular-badge">En Popüler</span>
            <p class="sm-price-name">Profesyonel</p>
            <p class="sm-price-amount"><sup>₺</sup>999</p>
            <p class="sm-price-period">/ ay · sınırsız blok</p>
            <ul class="sm-price-features">
                <li>Sınırsız blok ve daire</li>
                <li>Banka entegrasyonu</li>
                <li>Hukuki takip modülü</li>
                <li>Personel &amp; demirbaş</li>
                <li>PDF / Excel raporlar</li>
                <li>Öncelikli destek</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Satın Al →", type="primary", use_container_width=True, key="plan_sec_pro"):
            st.session_state.odeme_secilen_plan = "Profesyonel — ₺999/ay"
            st.rerun()

    with p3:
        st.markdown("""
        <div class="sm-price-card">
            <p class="sm-price-name">Kurumsal</p>
            <p class="sm-price-amount" style="font-size:1.55rem;">Teklif Al</p>
            <p class="sm-price-period">çoklu site · özel sözleşme</p>
            <ul class="sm-price-features">
                <li>Birden fazla site yönetimi</li>
                <li>Özel entegrasyonlar</li>
                <li>SLA güvencesi</li>
                <li>Yerinde kurulum desteği</li>
                <li>Dedicated hesap yöneticisi</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("İletişime Geç", use_container_width=True, key="plan_sec_kur"):
            st.session_state.odeme_secilen_plan = "Kurumsal — Teklif Al"
            st.rerun()

    secilen_plan = st.session_state.odeme_secilen_plan
    st.markdown(
        f'<p class="sm-secili-plan">Seçilen plan: {secilen_plan}</p>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<p class="odeme-kart-baslik">Kart bilgileri</p>'
        '<p class="odeme-kart-alt">Ödemenizi güvenle tamamlayın</p>',
        unsafe_allow_html=True,
    )

    _, col_kart, _ = st.columns([1, 1.4, 1])
    with col_kart:
        with st.form("odeme_kart_form"):
            st.text_input("Kart üzerindeki ad soyad", placeholder="AD SOYAD", key="odeme_kart_ad")
            st.text_input(
                "Kart numarası",
                placeholder="0000  0000  0000  0000",
                max_chars=19,
                key="odeme_kart_no",
            )
            c_son, c_cvv = st.columns(2)
            with c_son:
                st.text_input("Son kullanma", placeholder="AA / YY", max_chars=5, key="odeme_kart_son")
            with c_cvv:
                st.text_input("CVV", placeholder="•••", type="password", max_chars=4, key="odeme_kart_cvv")
            st.caption("Kart bilgileriniz 256-bit SSL ile korunur. (Demo: gerçek ödeme alınmaz.)")
            gonder = st.form_submit_button(
                "Ödemeyi tamamla ve kuruluma geç →",
                type="primary",
                use_container_width=True,
            )
            if gonder:
                kart_ad = (st.session_state.get("odeme_kart_ad") or "").strip()
                kart_no = (st.session_state.get("odeme_kart_no") or "").strip()
                kart_son = (st.session_state.get("odeme_kart_son") or "").strip()
                kart_cvv = (st.session_state.get("odeme_kart_cvv") or "").strip()
                if not kart_ad or not kart_no or not kart_son or not kart_cvv:
                    st.error("Lütfen tüm kart alanlarını eksiksiz doldurun.")
                else:
                    st.session_state.odeme_tamamlandi = True
                    st.session_state.secilen_plan = secilen_plan
                    st.session_state.sayfa = "Kayıt"
                    st.rerun()


# --- YENİ SİTE KAYIT ---
elif st.session_state.sayfa == 'Kayıt':
    public_sayfa_css()
    if not st.session_state.get('odeme_tamamlandi'):
        st.warning(
            "Site kurulumu için önce plan seçip kart bilgilerini girmeniz gerekir. "
            "Ödeme adımını tamamladıysanız aynı tarayıcı sekmesinde devam edin; "
            "yeni sekme açarsanız oturum sıfırlanır."
        )
        if st.button("Ödeme adımına git →", type="primary", key="kayit_odeme_yonlendir"):
            st.session_state.sayfa = "Odeme"
            st.rerun()
        st.stop()

    if st.button("← Ödeme / plan adımına dön", key="kayit_ust_geri"):
        st.session_state.sayfa = "Odeme"
        st.rerun()

    st.title("Kurumsal Site Kurulumu")
    plan_etiket = st.session_state.get("secilen_plan", "")
    if plan_etiket:
        st.info(f"Seçilen plan: **{plan_etiket}**")
    st.caption("Aşağıdaki bölümleri sırayla doldurun; kurulum bitince giriş ekranından panele girebilirsiniz.")

    st.subheader("1. Mimari yapı")
    with st.container(border=True):
        blok_adedi = st.number_input(
            "Blok adedi",
            min_value=1,
            step=1,
            key="kur_blok_adet",
            help="Kaç ayrı blok var? Her blok için ad ve daire sayısı girilir.",
        )
        n_blok = int(blok_adedi)
        for i in range(n_blok):
            if n_blok > 1:
                st.markdown(f"**Blok {i + 1}**")
            _r1, _r2 = st.columns(2)
            with _r1:
                st.text_input(
                    "Blok adı" if n_blok == 1 else f"Blok {i + 1} adı",
                    value=f"{chr(65 + i)} Blok",
                    key=f"kur_blok_adi_{i}",
                )
            with _r2:
                st.number_input(
                    "Daire adedi" if n_blok == 1 else f"Daire adedi (Blok {i + 1})",
                    min_value=1,
                    value=8,
                    step=1,
                    key=f"kur_blok_daire_{i}",
                )

    st.subheader("2. Adres bilgileri")
    with st.container(border=True):
        st.caption("İl → ilçe → mahalle seçin.")
        _a1, _a2, _a3 = st.columns(3)
        with _a1:
            st.selectbox("İl ✱", tr_adres.il_listesi(), key="kur_il")
        with _a2:
            _ilce_opts = tr_adres.ilce_listesi(st.session_state.get("kur_il", tr_adres.il_listesi()[0]))
            st.selectbox("İlçe ✱", _ilce_opts, key="kur_ilce")
        with _a3:
            _mah_opts = tr_adres.mahalle_listesi(st.session_state.get("kur_ilce", _ilce_opts[0]))
            st.selectbox("Mahalle ✱", _mah_opts, key="kur_mahalle")
        if st.session_state.get("kur_mahalle") == tr_adres.DIGER_MAHALLE:
            st.text_input(
                "Mahalle adını yazın ✱",
                key="kur_mahalle_diger",
                placeholder="Örn: Yeni Mahalle",
            )

    st.subheader("3. Site, kurum ve yönetici")
    with st.form("yeni_kayit_formu"):
        st.markdown("**Site ve kurum**")
        _f1, _f2 = st.columns(2)
        with _f1:
            site_adi = st.text_input("Site / apartman adı ✱", placeholder="Örn: Güneş Sitesi")
            telefon = st.text_input(
                "Yönetim telefonu ✱",
                placeholder="532 123 45 67 (0 otomatik eklenir)",
                help="5xx mobil veya sabit hat. +90 veya baştaki 0 yazmasanız da olur.",
            )
        with _f2:
            vergi_no = st.text_input("Vergi numarası / dairesi", placeholder="Opsiyonel")
            s_eposta = st.text_input("Kurumsal e-posta", placeholder="info@siteniz.com")

        logo_file = st.file_uploader(
            "Site logosu (PNG/JPG) — makbuz ve raporlarda kullanılır",
            type=["png", "jpg", "jpeg"],
        )

        st.divider()
        st.markdown("**Yönetici hesabı**")
        _y1, _y2 = st.columns(2)
        with _y1:
            y_k = st.text_input("Yönetici kullanıcı adı ✱", placeholder="yonetici")
            y_eposta = st.text_input("Yönetici e-posta ✱", placeholder="yonetici@mail.com")
        with _y2:
            y_s = st.text_input("Giriş şifresi ✱", type="password")
            y_s_t = st.text_input("Şifre tekrarı ✱", type="password")

        if st.form_submit_button("Sistemi kur ve kaydet", type="primary", use_container_width=True):
            _n = int(st.session_state.get("kur_blok_adet", 1))
            blok_adi_list   = [st.session_state.get(f"kur_blok_adi_{i}", "")   for i in range(_n)]
            blok_daire_list = [int(st.session_state.get(f"kur_blok_daire_{i}", 1)) for i in range(_n)]

            # Adres değerlerini session_state'den oku
            _il_val  = st.session_state.get("kur_il", "")
            _ilce_val= st.session_state.get("kur_ilce", "")
            _mah_val = st.session_state.get("kur_mahalle_diger", "").strip() \
                       if st.session_state.get("kur_mahalle") == tr_adres.DIGER_MAHALLE \
                       else st.session_state.get("kur_mahalle", "")

            # Telefon validasyonu
            _tel_gecerli, _tel_fmt, _tel_msg = telefon_normalize(telefon, zorunlu=True)

            # Validasyonlar
            if not site_adi or not y_k or not y_eposta:
                st.error("Site adı, yönetici kullanıcı adı ve e-posta zorunludur.")
            elif y_s != y_s_t or not y_s:
                st.error("Şifreler eşleşmeli ve boş bırakılmamalı.")
            elif not _tel_gecerli:
                st.error(f"Telefon numarası hatalı: {_tel_msg}")
            elif not _il_val or not _ilce_val or not _mah_val:
                st.error("İl, ilçe ve mahalle seçimi zorunludur.")
            elif len(blok_adi_list) != _n or len(blok_daire_list) != _n:
                st.error("Mimari bilgiler eksik.")
            else:
                blok_ciftleri = list(zip(blok_adi_list, blok_daire_list))
                isimler = [b[0].strip() for b in blok_ciftleri]
                if any(not name for name in isimler):
                    st.error("Tüm blok adlarını doldurun.")
                elif len(set(isimler)) != len(isimler):
                    st.error("Blok adları birbirinden farklı olmalı.")
                else:
                    logo_b64 = ""
                    if logo_file:
                        logo_b64 = base64.b64encode(logo_file.read()).decode()

                    # Adres metni (il + ilçe + mahalle birleşimi)
                    adres_tam = f"{_mah_val}, {_ilce_val}, {_il_val}"

                    tenant_db = f"{site_adi.replace(' ', '_').lower()}_db.sqlite"
                    try:
                        conn = get_conn("master.db")
                        c = conn.cursor()
                        c.execute(
                            """INSERT INTO siteler
                               (site_adi, tenant_db_adi, adres, vergi_no, telefon, eposta, logo,
                                il, ilce, mahalle)
                               VALUES (?,?,?,?,?,?,?,?,?,?)""",
                            (site_adi, tenant_db, adres_tam, vergi_no, _tel_fmt,
                             s_eposta, logo_b64, _il_val, _ilce_val, _mah_val),
                        )
                        conn.commit()
                        conn.close()

                        init_tenant_db(tenant_db)
                        conn_t = get_conn(tenant_db)
                        ct = conn_t.cursor()
                        for bn, ds in blok_ciftleri:
                            ct.execute(
                                "INSERT INTO bloklar (blok_adi, daire_sayisi) VALUES (?,?)",
                                (bn.strip(), int(ds)),
                            )
                        ct.execute(
                            "INSERT INTO yoneticiler (kullanici_adi, sifre, eposta) VALUES (?,?,?)",
                            (y_k, generate_password_hash(y_s), y_eposta),
                        )
                        conn_t.commit()
                        conn_t.close()
                        st.success(f"Kurulum tamam! {site_adi} sisteme eklendi. Giriş yapabilirsiniz.")
                        sayfa_degistir("Vitrin")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(f"'{site_adi}' adıyla zaten bir site kayıtlı.")
                    except Exception as _e:
                        st.error(f"Kayıt sırasında hata: {_e}")

    st.link_button("🏠 Tanıtım sitesine dön", url=LANDING_KAYIT, key="kayit_alt_landing")

# --- ANA SAYFA ---
elif st.session_state.sayfa == 'Ana_Sayfa':
    db_yolu = st.session_state.aktif_db
    
    # Sisteme girildiği an otomatik borçlandırma kontrolü yapılır
    otomatik_borclandir_motoru(db_yolu)
    
    _site_b64 = st.session_state.get("logo_b64")

    if st.session_state.rol == "Yönetici":
        with st.sidebar:
            # ── Sidebar: dinamik site logosu + site adı ───────────────────
            if _site_b64:
                st.image(f"data:image/png;base64,{_site_b64}", width=200)
            st.markdown(
                f"<p style='font-size:1.1rem;font-weight:700;margin:4px 0 0;'>"
                f"{st.session_state.aktif_site}</p>",
                unsafe_allow_html=True,
            )
            st.divider()
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
        elif secim == "💳 Gider": gider.goster(db_yolu, st.session_state.aktif_site)
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

