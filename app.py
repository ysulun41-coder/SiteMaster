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
from utils import get_conn

# Tanıtım videosu: YouTube/Vimeo linki veya None. Ayrıca aşağıdaki yerel dosya yolu doluysa oynatılır.
TANITIM_VIDEO_URL = None  # örn. "https://www.youtube.com/watch?v=..."
TANITIM_VIDEO_DOSYA = "assets/tanitim.mp4"  # proje köküne göre; yoksa yer tutucu gösterilir

# Landing page adresi — index.html'nin servis edildiği URL (VS Code Live Server: 5500, python -m http.server: 8000)
LANDING_URL = "http://localhost:8000/index.html"

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


# ─── Telefon doğrulama yardımcısı ───────────────────────────────────────────
def _tel_dogrula(ham: str) -> tuple[bool, str, str]:
    """
    Girilen telefon numarasını doğrula ve formatla.
    Döndürür: (gecerli, formatli, mesaj)
    Desteklenen: 05XXXXXXXXX veya 5XXXXXXXXX (Türk mobil/sabit)
    """
    if not ham:
        return False, "", "Telefon numarası boş."
    sadece_rakam = "".join(ch for ch in ham if ch.isdigit())
    # Başında 90 varsa kırp
    if sadece_rakam.startswith("90") and len(sadece_rakam) == 12:
        sadece_rakam = sadece_rakam[2:]
    # Başında 0 varsa kırp
    if sadece_rakam.startswith("0") and len(sadece_rakam) == 11:
        sadece_rakam = sadece_rakam[1:]
    if len(sadece_rakam) != 10:
        return False, ham, f"Geçersiz numara uzunluğu ({len(sadece_rakam)} rakam). 10 rakam olmalı."
    if not sadece_rakam[0] in ("5", "2", "3", "4"):
        return False, ham, "Numara 5XX (mobil) veya 2XX/3XX/4XX (sabit hat) ile başlamalı."
    formatli = f"+90 ({sadece_rakam[:3]}) {sadece_rakam[3:6]} {sadece_rakam[6:8]} {sadece_rakam[8:10]}"
    return True, formatli, ""

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

# Dış linkten gelen /?p=odeme sinyalini yakala
_qp = st.query_params.get('p', '')
if _qp == 'odeme' and st.session_state.sayfa == 'Vitrin':
    st.session_state.sayfa = 'Odeme'
    st.query_params.clear()
    st.rerun()


def sayfa_degistir(yeni_sayfa):
    st.session_state.sayfa = yeni_sayfa


def guvenli_cikis():
    st.session_state.clear()
    st.session_state.sayfa = 'Vitrin'
    st.rerun()



# --- VİTRİN ---
if st.session_state.sayfa == 'Vitrin':
    st.link_button("🏠 Ana Sayfaya Dön", url=LANDING_URL, key="vitrin_landing_btn")

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
                    "Henüz kayıtlı site yok. Aşağıdaki **Yeni kurumsal site kaydı oluştur** butonundan yeni site oluşturun."
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
                            # Site logosunu master.db'den yükle
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
                    "Henüz kayıtlı site yok. Aşağıdaki **Yeni kurumsal site kaydı oluştur** butonundan önce site oluşturulmalıdır."
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
    st.markdown("""
    <style>
    .odeme-plan-kart {
        border: 2px solid #e2e8f0; border-radius: 16px; padding: 1.5rem 1.4rem 1.6rem;
        background: #fff; text-align: center; transition: border-color .2s, box-shadow .2s;
        height: 100%;
    }
    .odeme-plan-kart.populer { border-color: #2563eb; box-shadow: 0 4px 24px rgba(37,99,235,.18); }
    .odeme-plan-kart h3 { font-size: 1rem; font-weight: 700; color: #64748b; letter-spacing:.06em; text-transform:uppercase; margin-bottom:.6rem; }
    .odeme-plan-kart .fiyat { font-size: 2.4rem; font-weight: 900; color: #0f172a; letter-spacing:-.05em; line-height:1; }
    .odeme-plan-kart .donem { font-size: .8rem; color: #94a3b8; margin-bottom: 1rem; }
    .odeme-plan-kart ul { list-style:none; padding:0; text-align:left; font-size:.875rem; color:#334155; display:flex; flex-direction:column; gap:.45rem; }
    .odeme-plan-kart ul li::before { content:"✓ "; color:#22c55e; font-weight:800; }
    .populer-rozet { background:#2563eb; color:#fff; font-size:.72rem; font-weight:700; letter-spacing:.06em; text-transform:uppercase; padding:.28rem .8rem; border-radius:99px; display:inline-block; margin-bottom:.75rem; }
    </style>
    """, unsafe_allow_html=True)

    st.link_button("🏠 Ana Sayfaya Dön", url=LANDING_URL, key="odeme_ust_geri")

    _lp, _cm, _rp = st.columns([1, 4, 1])
    with _cm:
        st.markdown("## 🏷️ Plan Seçimi")
        st.caption("Kuruluma geçmeden önce size uygun planı seçin ve ödemenizi tamamlayın.")
        st.divider()

        # Plan seçimi
        st.markdown("#### 1. Planınızı Seçin")
        p1, p2, p3 = st.columns(3, gap="medium")

        with p1:
            st.markdown("""
            <div class="odeme-plan-kart">
                <h3>Başlangıç</h3>
                <div class="fiyat">₺499</div>
                <div class="donem">/ ay · tek site</div>
                <ul>
                    <li>1 Site · 1 Blok</li>
                    <li>Otonom borçlandırma</li>
                    <li>Tahsilat takibi</li>
                    <li>Sakin paneli</li>
                    <li>E-posta desteği</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with p2:
            st.markdown("""
            <div class="odeme-plan-kart populer">
                <div class="populer-rozet">En Popüler</div>
                <h3>Profesyonel</h3>
                <div class="fiyat">₺999</div>
                <div class="donem">/ ay · sınırsız blok</div>
                <ul>
                    <li>Sınırsız blok ve daire</li>
                    <li>Banka entegrasyonu</li>
                    <li>Hukuki takip modülü</li>
                    <li>Personel & demirbaş</li>
                    <li>PDF / Excel raporlar</li>
                    <li>Öncelikli destek</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with p3:
            st.markdown("""
            <div class="odeme-plan-kart">
                <h3>Kurumsal</h3>
                <div class="fiyat" style="font-size:1.5rem;padding-top:.3rem;">Teklif Al</div>
                <div class="donem">çoklu site · özel sözleşme</div>
                <ul>
                    <li>Birden fazla site</li>
                    <li>Özel entegrasyonlar</li>
                    <li>SLA güvencesi</li>
                    <li>Dedicated hesap yöneticisi</li>
                    <li>Yerinde kurulum desteği</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        secilen_plan = st.radio(
            "Planınız:",
            ["Başlangıç — ₺499/ay", "Profesyonel — ₺999/ay", "Kurumsal — Teklif Al"],
            index=1,
            horizontal=True,
            key="odeme_plan",
            label_visibility="collapsed",
        )

        st.divider()
        st.markdown("#### 2. Kart Bilgileri")

        with st.container(border=True):
            kart_ad = st.text_input("Kart Üzerindeki Ad Soyad", placeholder="AD SOYAD", key="krt_ad")
            k1, k2 = st.columns([2, 1])
            with k1:
                kart_no = st.text_input("Kart Numarası", placeholder="0000  0000  0000  0000", key="krt_no", max_chars=19)
            with k2:
                kart_son = st.text_input("Son Kullanma", placeholder="AA/YY", key="krt_son", max_chars=5)
            k3, k4 = st.columns([1, 2])
            with k3:
                kart_cvv = st.text_input("CVV", placeholder="•••", type="password", key="krt_cvv", max_chars=4)
            with k4:
                st.markdown("")
                st.caption("🔒 Kart bilgileriniz 256-bit SSL şifrelemesiyle korunur.")

        st.divider()

        if st.button("Ödemeyi Tamamla ve Kuruluma Geç →", type="primary", use_container_width=True, key="odeme_tamamla"):
                if not kart_ad or not kart_no or not kart_son or not kart_cvv:
                    st.error("Lütfen tüm kart bilgilerini eksiksiz doldurun.")
                else:
                    st.session_state.odeme_tamamlandi = True
                    st.session_state.secilen_plan = secilen_plan
                    sayfa_degistir("Kayıt")
                    st.rerun()

# --- YENİ SİTE KAYIT ---
elif st.session_state.sayfa == 'Kayıt':
    if not st.session_state.get('odeme_tamamlandi'):
        st.warning("Bu sayfaya erişmek için önce bir plan seçip ödeme yapmanız gerekmektedir.")
        st.button("Planlara Git →", on_click=sayfa_degistir, args=("Odeme",), type="primary")
        st.stop()

    st.link_button("🏠 Ana Sayfaya Dön", url=LANDING_URL, key="kayit_ust_geri")

    st.title("Kurumsal Site Kurulumu")
    st.caption("Tüm alanları eksiksiz doldurun; kurulum tamamlandıktan sonra giriş yapabilirsiniz.")

    # ── Mimari yapı (form DIŞINDA — reaktif) ─────────────────────────────────
    with st.container(border=True):
        st.markdown("#### 1. Mimari Yapı")
        blok_adedi = st.number_input(
            "Blok adedi",
            min_value=1, step=1, key="kur_blok_adet",
            help="Kaç ayrı blok olduğunu seçin; her blok için ad ve daire sayısı otomatik çıkar.",
        )
        n_blok = int(blok_adedi)
        st.caption(
            "Tek blok: blok adı ve daire adedini girin."
            if n_blok == 1
            else f"**{n_blok} blok** için her satırda blok adı ve daire adedi girilir."
        )
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
                    "Daire adedi" if n_blok == 1 else f"Blok {i + 1} — daire adedi",
                    min_value=1, value=8, step=1,
                    key=f"kur_blok_daire_{i}",
                )

    # ── Hiyerarşik adres seçimi (form DIŞINDA — reaktif) ─────────────────────
    with st.container(border=True):
        st.markdown("#### 2. Adres Bilgileri")
        st.caption("İl → İlçe → Mahalle sırasıyla seçin; her seçim bir sonrakini günceller.")
        _a1, _a2, _a3 = st.columns(3)
        with _a1:
            _il_sec = st.selectbox("İl ✱", tr_adres.il_listesi(), key="kur_il")
        with _a2:
            _ilce_opts = tr_adres.ilce_listesi(_il_sec)
            _ilce_sec = st.selectbox("İlçe ✱", _ilce_opts, key="kur_ilce")
        with _a3:
            _mah_opts = tr_adres.mahalle_listesi(_ilce_sec)
            _mah_sec = st.selectbox("Mahalle ✱", _mah_opts, key="kur_mahalle")

        # "Diğer" seçilirse serbest metin kutusu aç
        _mah_gir = ""
        if _mah_sec == tr_adres.DIGER_MAHALLE:
            _mah_gir = st.text_input(
                "Mahalle adını yazın",
                key="kur_mahalle_diger",
                placeholder="Örn: Yeni Mahalle",
            )

    # ── Kurum bilgileri formu ─────────────────────────────────────────────────
    with st.form("yeni_kayit_formu"):
        with st.container(border=True):
            st.markdown("#### 3. Site ve Kurum Bilgileri")
            _f1, _f2 = st.columns(2)
            with _f1:
                site_adi  = st.text_input("Site / apartman adı ✱")
                telefon   = st.text_input(
                    "Yönetim telefonu ✱",
                    placeholder="05XX XXX XX XX",
                    help="Türk mobil (05XX) veya sabit hat (0XXX) formatında girin.",
                )
            with _f2:
                vergi_no  = st.text_input("Vergi numarası / dairesi")
                s_eposta  = st.text_input("Kurumsal e-posta")

            logo_file = st.file_uploader(
                "Site logosu — makbuz ve raporlarda görünür (PNG/JPG)",
                type=["png", "jpg", "jpeg"],
            )

        with st.container(border=True):
            st.markdown("#### 4. Yönetici ve Güvenlik")
            _y1, _y2 = st.columns(2)
            with _y1:
                y_k      = st.text_input("Yönetici kullanıcı adı ✱")
                y_eposta = st.text_input("Yönetici e-posta (şifre sıfırlama) ✱")
            with _y2:
                y_s   = st.text_input("Giriş şifresi ✱", type="password")
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
            _tel_gecerli, _tel_fmt, _tel_msg = _tel_dogrula(telefon)

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

    if st.link_button("🏠 Ana Sayfaya Dön", url=LANDING_URL, key="kayit_alt_geri"):
        st.toast("Yönlendiriliyorsunuz...")

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

