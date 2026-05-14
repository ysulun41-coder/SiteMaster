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

# Tanıtım videosu: YouTube/Vimeo linki veya None. Ayrıca aşağıdaki yerel dosya yolu doluysa oynatılır.
TANITIM_VIDEO_URL = None  # örn. "https://www.youtube.com/watch?v=..."
TANITIM_VIDEO_DOSYA = "assets/tanitim.mp4"  # proje köküne göre; yoksa yer tutucu gösterilir

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
    st.session_state.sayfa = 'Vitrin'


def sayfa_degistir(yeni_sayfa):
    st.session_state.sayfa = yeni_sayfa


def guvenli_cikis():
    st.session_state.clear()
    st.session_state.sayfa = 'Vitrin'
    st.rerun()


def sm_vitrin_saas_css():
    st.markdown(
        """
        <style>
            font-size: clamp(1.35rem, 2.8vw, 1.85rem);
            font-weight: 800;
            letter-spacing: -0.035em;
            color: #0f172a;
            line-height: 1.2;
            margin: 0 0 0.65rem;
        }
        .saas-sub {
            font-size: clamp(0.92rem, 1.5vw, 1.05rem);
            color: #475569;
            line-height: 1.65;
            margin: 0 0 1.25rem;
            max-width: 38rem;
        }
        .saas-feat-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 0.75rem;
            margin-top: 0.5rem;
        }
        @media (min-width: 700px) {
            .saas-feat-grid { grid-template-columns: repeat(3, 1fr); gap: 0.85rem; }
        }
        .saas-feat {
            background: linear-gradient(145deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 1rem 1rem 1.05rem;
            box-shadow: 0 2px 12px rgba(15, 23, 42, 0.05);
            transition: box-shadow 0.2s ease, border-color 0.2s ease;
        }
        .saas-feat:hover {
            border-color: #cbd5e1;
            box-shadow: 0 6px 20px rgba(15, 23, 42, 0.08);
        }
        .saas-feat h4 {
            margin: 0 0 0.4rem;
            font-size: 0.95rem;
            font-weight: 700;
            color: #0f172a;
            letter-spacing: -0.02em;
        }
        .saas-feat p {
            margin: 0;
            font-size: 0.82rem;
            color: #64748b;
            line-height: 1.5;
        }
        .saas-feat .ic {
            font-size: 1.35rem;
            margin-bottom: 0.35rem;
            display: block;
        }
        .saas-activation {
            margin-top: 1.5rem;
            padding: 1.15rem 1.2rem;
            border-radius: 16px;
            border: 1px dashed #94a3b8;
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        }
        .saas-activation h3 {
            margin: 0 0 0.35rem;
            font-size: 0.95rem;
            font-weight: 700;
            color: #334155;
            letter-spacing: -0.02em;
        }
        .saas-activation p {
            margin: 0 0 0.85rem;
            font-size: 0.82rem;
            color: #64748b;
            line-height: 1.5;
        }
        div[data-testid="stTabs"] button { font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# --- VİTRİN: SaaS vitrin + giriş (mantık / sorgular korunur) ---
if st.session_state.sayfa == 'Vitrin':
    sm_vitrin_saas_css()

    conn = sqlite3.connect('master.db')
    df_siteler = pd.read_sql_query("SELECT site_adi, tenant_db_adi FROM siteler", conn)
    conn.close()

    logo_primary = Path("logo.png")
    logo_path = str(logo_primary) if logo_primary.exists() else None
    if not logo_path:
        logo_path = next(
            (p for p in ("logo.png.png", "assets/logo.png") if Path(p).exists()),
            None,
        )

    _lc0, _lc1, _lc2 = st.columns([1, 2.2, 1])
    with _lc1:
        if logo_path:
            st.image(logo_path, use_container_width=True)
        else:
            st.markdown(
                '<p class="saas-h1" style="text-align:center;margin-bottom:0.25rem">SiteMaster</p>',
                unsafe_allow_html=True,
            )

    col_sol, _gap, col_sag = st.columns([1.2, 0.1, 1], gap="small")

    with col_sol:
        st.markdown(
            """
            <h1 class="saas-h1">Otonom Site Yönetimi ve Finans Çözümleri</h1>
            <p class="saas-sub">
            Yapay zeka destekli altyapımızla aidat tahsilat oranınızı %98'e çıkarın. Banka entegrasyonu,
            hukuki takip ve otonom muhasebe ile yöneticiliğin tüm yükünden kurtulun.
            </p>
            <div class="saas-feat-grid">
              <div class="saas-feat">
                <span class="ic">⏱</span>
                <h4>Zaman Tasarrufu</h4>
                <p>Tek panelde tahakkuk, tahsilat ve raporlama; tekrarlayan işleri otomatikleştirin.</p>
              </div>
              <div class="saas-feat">
                <span class="ic">✓</span>
                <h4>Sıfır Hata Payı</h4>
                <p>Standart akışlar ve veri tutarlılığı ile manuel hataları azaltın, denetimi kolaylaştırın.</p>
              </div>
              <div class="saas-feat">
                <span class="ic">◇</span>
                <h4>Tam Şeffaflık</h4>
                <p>Sakin ve yönetim için net bakiye, hareket ve geçmiş görünürlüğü.</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.divider()
        st.markdown(
            """
            <div class="saas-activation">
            <h3>Kurumsal kurulum / satın alma sonrası aktivasyon</h3>
            <p>Yeni apartman veya site için veritabanı ve yönetici hesabını bir kez oluşturun.
            Günlük giriş için sağdaki sekmeleri kullanın.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "Yeni kurumsal site kaydı oluştur",
            on_click=sayfa_degistir,
            args=('Kayıt',),
            type="secondary",
            use_container_width=True,
            key="sm_saas_btn_kurulum",
        )

    with col_sag:
        with st.container(border=True):
            st.markdown("**Giriş**")
            st.caption("Mevcut sitenize yönetici veya sakin olarak bağlanın.")

            tab_y, tab_s = st.tabs(["Yönetici Girişi", "Sakin Girişi"])

            with tab_y:
                if df_siteler.empty:
                    st.info(
                        "Henüz kayıtlı site yok. Sol alttaki **Kurumsal kurulum** bölümünden yeni site oluşturun."
                    )
                else:
                    sec_site = st.selectbox("Site seçin", df_siteler['site_adi'].tolist(), key="sm_adm_site")
                    k_adi = st.text_input("Kullanıcı adı", key="sm_adm_user")
                    sifre = st.text_input("Şifre", type="password", key="sm_adm_pass")
                    if st.button("Panele gir", type="primary", use_container_width=True, key="sm_adm_go"):
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
                        st.caption("SMTP ayarlıysa e-postaya geçici şifre gönderilir.")
                        f_site = st.selectbox("Site", df_siteler['site_adi'].tolist(), key="sm_f_site")
                        f_eposta = st.text_input("Yönetici e-postası", key="sm_f_mail")

                        if st.button("Sıfırla ve mail gönder", key="sm_f_btn"):
                            if f_site and f_eposta:
                                f_db = df_siteler.loc[df_siteler['site_adi'] == f_site, 'tenant_db_adi'].values[0]
                                conn_t = sqlite3.connect(f_db)
                                ct = conn_t.cursor()
                                ct.execute("SELECT id FROM yoneticiler WHERE eposta=?", (f_eposta,))
                                if ct.fetchone():
                                    yeni_sifre = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                                    with st.spinner("Mail gönderiliyor..."):
                                        mail_gitti_mi = sifre_sifirlama_maili_gonder(f_eposta, yeni_sifre, f_site)
                                    if mail_gitti_mi:
                                        ct.execute(
                                            "UPDATE yoneticiler SET sifre=? WHERE eposta=?",
                                            (yeni_sifre, f_eposta),
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
                        "Henüz kayıtlı site yok. Sol alttaki **Kurumsal kurulum** bölümünden önce site oluşturulmalıdır."
                    )
                else:
                    sec_site_s = st.selectbox("Site seçin", df_siteler['site_adi'].tolist(), key="sm_sak_site")
                    db_s = df_siteler.loc[df_siteler['site_adi'] == sec_site_s, 'tenant_db_adi'].values[0]
                    conn_s = sqlite3.connect(db_s)
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
                                    "SELECT malik_ad FROM sakinler WHERE blok=? AND daire_no=? AND sifre=?",
                                    (s_bl, s_dr, s_sif),
                                )
                                res = ct.fetchone()
                                if res:
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

# --- YENİ SİTE KAYIT ---
elif st.session_state.sayfa == 'Kayıt':
    st.title("Kurumsal site kurulumu")

    # Mimari formun DIŞINDA: blok adedi değişince anında aşağıda satırlar güncellenir.
    st.markdown("#### Mimari yapı")
    blok_adedi = st.number_input(
        "Blok adedi",
        min_value=1,
        step=1,
        key="kur_blok_adet",
        help="Kaç ayrı blok olduğunu seçin; hemen altında her blok için ad ve daire sayısı çıkar.",
    )
    n_blok = int(blok_adedi)
    if n_blok == 1:
        st.caption("Tek blok: aşağıya **blok adı** ve bu bloktaki **daire adedi**ni girin.")
    else:
        st.caption(
            f"**{n_blok} blok** için aşağıda her satırda blok adı ve o bloktaki daire adedi girilir."
        )

    for i in range(n_blok):
        if n_blok > 1:
            st.markdown(f"**Blok {i + 1}**")
        r1, r2 = st.columns(2)
        with r1:
            ad_label = "Blok adı" if n_blok == 1 else f"Blok {i + 1} adı"
            st.text_input(
                ad_label,
                value=f"{chr(65 + i)} Blok",
                key=f"kur_blok_adi_{i}",
            )
        with r2:
            daire_label = "Daire adedi" if n_blok == 1 else f"Blok {i + 1} — daire adedi"
            st.number_input(
                daire_label,
                min_value=1,
                value=8,
                step=1,
                key=f"kur_blok_daire_{i}",
            )

    st.divider()

    with st.form("yeni_kayit_formu"):
        st.markdown("#### Site ve kurum bilgileri")
        c1, c2 = st.columns(2)
        with c1:
            site_adi = st.text_input("Site / apartman adı")
            adres = st.text_area("Açık adres", height=100)
            telefon = st.text_input("Yönetim iletişim numarası")
        with c2:
            vergi_no = st.text_input("Vergi numarası / dairesi")
            s_eposta = st.text_input("Kurumsal e-posta")
            logo_file = st.file_uploader("Site logosu (makbuzlar için)", type=["png", "jpg", "jpeg"])

        st.markdown("#### Yönetici ve güvenlik")
        c_y1, c_y2 = st.columns(2)
        with c_y1:
            y_k = st.text_input("Yönetici kullanıcı adı")
            y_eposta = st.text_input("Yönetici e-posta (şifre sıfırlama)")
        with c_y2:
            y_s = st.text_input("Giriş şifresi", type="password")
            y_s_t = st.text_input("Şifre tekrarı", type="password")

        if st.form_submit_button("Sistemi kur ve kaydet", type="primary"):
            n = int(st.session_state.get("kur_blok_adet", 1))
            blok_adi_list = [st.session_state.get(f"kur_blok_adi_{i}", "") for i in range(n)]
            blok_daire_list = [
                int(st.session_state.get(f"kur_blok_daire_{i}", 1)) for i in range(n)
            ]

            if y_s != y_s_t or not site_adi or not y_k or not y_eposta:
                st.error("Şifreler aynı olmalı ve zorunlu alanlar dolu olmalı.")
            elif len(blok_adi_list) != n or len(blok_daire_list) != n:
                st.error("Mimari bilgiler eksik. Blok adedini kontrol edin.")
            else:
                blok_ciftleri = list(zip(blok_adi_list, blok_daire_list))
                isimler = [b[0].strip() for b in blok_ciftleri]
                if any(not name for name in isimler):
                    st.error("Tüm blok adlarını doldurun (mimari bölümü).")
                elif len(set(isimler)) != len(isimler):
                    st.error("Blok adları birbirinden farklı olmalı.")
                else:
                    logo_b64 = ""
                    if logo_file:
                        logo_b64 = base64.b64encode(logo_file.read()).decode()

                    tenant_db = f"{site_adi.replace(' ', '_').lower()}_db.sqlite"
                    conn = sqlite3.connect("master.db")
                    c = conn.cursor()
                    c.execute(
                        """INSERT INTO siteler
                             (site_adi, tenant_db_adi, adres, vergi_no, telefon, eposta, logo)
                             VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (site_adi, tenant_db, adres, vergi_no, telefon, s_eposta, logo_b64),
                    )
                    conn.commit()
                    conn.close()

                    init_tenant_db(tenant_db)
                    conn_t = sqlite3.connect(tenant_db)
                    ct = conn_t.cursor()

                    for bn, ds in blok_ciftleri:
                        ct.execute(
                            "INSERT INTO bloklar (blok_adi, daire_sayisi) VALUES (?, ?)",
                            (bn.strip(), int(ds)),
                        )

                    ct.execute(
                        "INSERT INTO yoneticiler (kullanici_adi, sifre, eposta) VALUES (?, ?, ?)",
                        (y_k, y_s, y_eposta),
                    )

                    conn_t.commit()
                    conn_t.close()
                    st.success("Kurulum tamam. Giriş yapabilirsiniz.")
                    sayfa_degistir("Vitrin")
                    st.rerun()

    st.button("Geri dön", on_click=sayfa_degistir, args=("Vitrin",))

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
