import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
import tahsilat # <--- İŞTE YENİ DOSYAMIZI BURADAN ÇAĞIRIYORUZ!

# --- (VERİTABANI VE GİRİŞ FONKSİYONLARI BURADA AYNI KALIYOR) ---
def init_master_db():
    conn = sqlite3.connect('master.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS siteler (id INTEGER PRIMARY KEY AUTOINCREMENT, site_adi TEXT UNIQUE, tenant_db_adi TEXT)''')
    conn.commit(); conn.close()

def init_tenant_db(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS yoneticiler (id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici_adi TEXT UNIQUE, sifre TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sakinler (id INTEGER PRIMARY KEY AUTOINCREMENT, blok TEXT, daire_no TEXT, malik_ad TEXT, malik_tc TEXT, malik_tel TEXT, kiraci_ad TEXT, kiraci_tc TEXT, kiraci_tel TEXT, plaka TEXT, sifre TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS bloklar (id INTEGER PRIMARY KEY AUTOINCREMENT, blok_adi TEXT, daire_sayisi INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS aidatlar (id INTEGER PRIMARY KEY AUTOINCREMENT, blok TEXT, daire_no TEXT, tarih TEXT, tutar REAL, aciklama TEXT, durum TEXT DEFAULT 'Ödenmedi')''')
    c.execute('''CREATE TABLE IF NOT EXISTS giderler (id INTEGER PRIMARY KEY AUTOINCREMENT, tarih TEXT, kategori TEXT, tutar REAL, aciklama TEXT)''')
    conn.commit(); conn.close()

init_master_db()
st.set_page_config(page_title="SiteMaster", page_icon="🏢", layout="wide")

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False, sheet_name='SiteMaster_Rapor')
    return output.getvalue()

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
                    secilen_site = st.selectbox("Site Seçiniz", df_siteler['site_adi'].tolist(), key="admin_site")
                    k_adi = st.text_input("Yönetici Kullanıcı Adı")
                    sifre = st.text_input("Şifre", type="password")
                    if st.button("Yönetici Girişi", type="primary", use_container_width=True):
                        db = df_siteler.loc[df_siteler['site_adi'] == secilen_site, 'tenant_db_adi'].values[0]
                        init_tenant_db(db)
                        conn_t = sqlite3.connect(db); ct = conn_t.cursor()
                        ct.execute("SELECT kullanici_adi FROM yoneticiler WHERE kullanici_adi=? AND sifre=?", (k_adi, sifre))
                        if ct.fetchone():
                            st.session_state.aktif_site = secilen_site; st.session_state.aktif_db = db; st.session_state.rol = "Yönetici"
                            sayfa_degistir('Ana_Sayfa'); st.rerun()
                        else: st.error("Hatalı bilgiler!")
        with giris_tab2:
            with st.container(border=True):
                if not df_siteler.empty:
                    secilen_site_s = st.selectbox("Site Seçiniz", df_siteler['site_adi'].tolist(), key="sakin_site")
                    s_sifre_giris = st.text_input("Giriş Şifreniz", type="password")
                    if st.button("Sakin Girişi", type="primary", use_container_width=True):
                        db = df_siteler.loc[df_siteler['site_adi'] == secilen_site_s, 'tenant_db_adi'].values[0]
                        init_tenant_db(db)
                        conn_t = sqlite3.connect(db); ct = conn_t.cursor()
                        ct.execute("SELECT blok, daire_no, malik_ad FROM sakinler WHERE sifre=?", (s_sifre_giris,))
                        res = ct.fetchone()
                        if res:
                            st.session_state.aktif_site = secilen_site_s; st.session_state.aktif_db = db; st.session_state.rol = "Sakin"
                            st.session_state.sakin_bilgi = {"blok": res[0], "daire": res[1], "isim": res[2]}
                            sayfa_degistir('Ana_Sayfa'); st.rerun()
                        else: st.error("Hatalı şifre!")
        st.divider()
        st.button("🏢 Yeni Site Kaydı Oluştur", on_click=sayfa_degistir, args=('Kayıt',), use_container_width=True)

# --- YENİ SİTE KAYIT ---
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
            y_s_tekrar = st.text_input("Şifre Tekrarı", type="password")
            if st.button("Sisteme Kaydet", type="primary", use_container_width=True):
                if y_s != y_s_tekrar: st.error("Şifreler uyuşmuyor!")
                elif site_adi and y_k and y_s:
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
                else: st.error("Eksik bilgi!")
        st.button("⬅️ Geri Dön", on_click=sayfa_degistir, args=('Giriş',))

# --- ANA SAYFA (MODÜLER YAPI) ---
elif st.session_state.sayfa == 'Ana_Sayfa':
    db_yolu = st.session_state.aktif_db
    st.sidebar.title(f"🏢 {st.session_state.aktif_site}")
    if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.clear(); sayfa_degistir('Giriş'); st.rerun()

    if st.session_state.rol == "Yönetici":
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["➕ Sakin", "📋 Liste", "💰 Tahakkuk", "✅ Tahsilat", "💳 Gider", "📊 Dashboard", "📥 Raporlar"])
        
        with tab1:
            conn = sqlite3.connect(db_yolu); c = conn.cursor(); c.execute("SELECT blok_adi FROM bloklar")
            bloklar = [r[0] for r in c.fetchall()]; conn.close()
            with st.form("sakin_form", clear_on_submit=True):
                st.subheader("Yeni Sakin Kaydı")
                col1, col2, col3 = st.columns(3)
                with col1: s_blok = st.selectbox("Blok Seç", bloklar)
                with col2: d_no = st.text_input("Daire No")
                with col3: s_sifre_ek = st.text_input("Şifre Eki (Örn: Ahmet)", help="Başına Blok ve Daire otomatik eklenecek.")
                c_m, c_k = st.columns(2)
                with c_m: m_a = st.text_input("Malik Ad"); m_tc = st.text_input("Malik TC", max_chars=11); m_t = st.text_input("Malik Tel")
                with c_k: k_a = st.text_input("Kiracı Ad"); k_tc = st.text_input("Kiracı TC", max_chars=11); k_t = st.text_input("Kiracı Tel"); plk = st.text_input("Plaka")
                if st.form_submit_button("💾 Kaydet", type="primary"):
                    if s_blok and d_no and m_a and s_sifre_ek:
                        tam_sifre = f"{s_blok}{d_no}-{s_sifre_ek}"
                        conn = sqlite3.connect(db_yolu); c = conn.cursor()
                        c.execute("SELECT id FROM sakinler WHERE blok=? AND daire_no=?", (s_blok, d_no))
                        if c.fetchone(): st.error(f"⚠️ Hata: {s_blok} Blok, {d_no} dolu!")
                        else:
                            c.execute('''INSERT INTO sakinler (blok, daire_no, malik_ad, malik_tc, malik_tel, kiraci_ad, kiraci_tc, kiraci_tel, plaka, sifre) VALUES (?,?,?,?,?,?,?,?,?,?)''', (s_blok, d_no, m_a, m_tc, m_t, k_a, k_tc, k_t, plk, tam_sifre))
                            conn.commit(); st.success(f"Kayıt tamam! Şifre: {tam_sifre}")
                        conn.close()
                    else: st.error("Zorunlu alanları doldurun!")

        with tab2:
            st.subheader("Daire Detay Listesi")
            conn = sqlite3.connect(db_yolu)
            df_full = pd.read_sql_query("SELECT blok as Blok, daire_no as Daire, malik_ad as Malik, malik_tc as 'Malik TC', malik_tel as Telefon, kiraci_ad as Kiracı, kiraci_tc as 'Kiracı TC', kiraci_tel as 'Kiracı Tel', plaka as Plaka, sifre as Şifre FROM sakinler", conn)
            conn.close()
            if not df_full.empty: st.dataframe(df_full, use_container_width=True, hide_index=True)
            else: st.info("Kayıt yok.")

        with tab3:
            st.subheader("Aidat Tahakkuku")
            conn = sqlite3.connect(db_yolu); c = conn.cursor(); c.execute("SELECT blok, daire_no, malik_ad FROM sakinler"); s_list = c.fetchall(); conn.close()
            sec = ["🌟 Toplu Borçlandırma"] + [f"{s[0]} Blok - No:{s[1]} ({s[2]})" for s in s_list]
            with st.form("borc_form", clear_on_submit=True):
                h = st.selectbox("Daire", sec); tut = st.number_input("Tutar", min_value=0.0); acik = st.text_input("Açıklama")
                if st.form_submit_button("💸 Borçlandır"):
                    conn = sqlite3.connect(db_yolu); c = conn.cursor()
                    if h == "🌟 Toplu Borçlandırma":
                        for s in s_list: c.execute("INSERT INTO aidatlar (blok, daire_no, tarih, tutar, aciklama) VALUES (?,?,?,?,?)", (s[0], s[1], str(datetime.date.today()), tut, acik))
                    else:
                        idx = sec.index(h) - 1; s = s_list[idx]
                        c.execute("INSERT INTO aidatlar (blok, daire_no, tarih, tutar, aciklama) VALUES (?,?,?,?,?)", (s[0], s[1], str(datetime.date.today()), tut, acik))
                    conn.commit(); conn.close(); st.success("Borçlar yansıtıldı!")

        # ---------------------------------------------------------
        # İŞTE MUCİZE BURASI! YÜZLERCE SATIR YERİNE SADECE 1 SATIR
        # ---------------------------------------------------------
        with tab4:
            tahsilat.tahsilat_ekrani(db_yolu, st.session_state.aktif_site)

        with tab5:
            st.subheader("Gider Girişi")
            with st.form("gider_form"):
                kat = st.selectbox("Kategori", ["Elektrik", "Su", "Maaş", "Bakım", "Temizlik", "Diğer"])
                t = st.number_input("Tutar", min_value=0.0); a = st.text_input("Açıklama")
                if st.form_submit_button("💳 Harca"):
                    conn = sqlite3.connect(db_yolu); c = conn.cursor()
                    c.execute("INSERT INTO giderler (tarih, kategori, tutar, aciklama) VALUES (?,?,?,?)", (str(datetime.date.today()), kat, t, a))
                    conn.commit(); conn.close(); st.rerun()

        with tab6:
            st.subheader("Finansal Dashboard")
            conn = sqlite3.connect(db_yolu); c = conn.cursor()
            c.execute("SELECT SUM(tutar) FROM aidatlar WHERE durum='Ödendi'"); gelir = c.fetchone()[0] or 0.0
            c.execute("SELECT SUM(tutar) FROM giderler"); gider = c.fetchone()[0] or 0.0
            m1, m2, m3 = st.columns(3)
            m1.metric("Toplam Tahsilat", f"{gelir}₺"); m2.metric("Toplam Gider", f"{gider}₺"); m3.metric("Kasa", f"{gelir-gider}₺")
            st.divider(); c_g1, c_g2 = st.columns(2)
            with c_g1: st.bar_chart(pd.DataFrame({'Kategori': ['Gelir', 'Gider'], 'Tutar': [gelir, gider]}).set_index('Kategori'))
            with c_g2:
                df_ga = pd.read_sql_query("SELECT kategori, SUM(tutar) as Toplam FROM giderler GROUP BY kategori", conn)
                if not df_ga.empty: st.bar_chart(df_ga.set_index('kategori'))
            conn.close()

        with tab7:
            st.subheader("Excel Raporları")
            conn = sqlite3.connect(db_yolu)
            st.download_button("📥 Sakin Listesini İndir", data=to_excel(pd.read_sql_query("SELECT * FROM sakinler", conn)), file_name="Sakinler.xlsx")
            st.download_button("📥 Borçlu Listesini İndir", data=to_excel(pd.read_sql_query("SELECT * FROM aidatlar WHERE durum='Ödenmedi'", conn)), file_name="Borclular.xlsx")
            conn.close()

    # --- SAKİN PANELİ ---
    elif st.session_state.rol == "Sakin":
        s = st.session_state.sakin_bilgi
        st.title(f"👋 Hoş Geldiniz, {s['isim']}")
        with st.container(border=True):
            st.subheader("Hesap Özeti")
            st.write(f"**Daire:** {s['blok']} Blok, No: {s['daire']}")
            conn = sqlite3.connect(db_yolu)
            df_hesap = pd.read_sql_query("SELECT tarih, aciklama, tutar, durum FROM aidatlar WHERE blok=? AND daire_no=? ORDER BY id DESC", conn, params=(s['blok'], s['daire']))
            conn.close()
            if not df_hesap.empty:
                st.dataframe(df_hesap.style.map(lambda x: 'color: red' if x == 'Ödenmedi' else 'color: green', subset=['durum']), use_container_width=True, hide_index=True)
            else: st.success("Borç kaydınız bulunmamaktadır.")
