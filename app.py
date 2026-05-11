import streamlit as st
import pandas as pd
import sqlite3
import datetime

# --- 1. MASTER DB (FİHRİST) ---
def init_master_db():
    conn = sqlite3.connect('master.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS siteler (id INTEGER PRIMARY KEY AUTOINCREMENT, site_adi TEXT UNIQUE, tenant_db_adi TEXT)''')
    conn.commit()
    conn.close()

# --- 2. TENANT DB (SİTE ÖZEL KASA) ---
def init_tenant_db(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS yoneticiler (id INTEGER PRIMARY KEY AUTOINCREMENT, kullanici_adi TEXT UNIQUE, sifre TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sakinler (id INTEGER PRIMARY KEY AUTOINCREMENT, blok TEXT, daire_no TEXT, malik_ad TEXT, malik_tc TEXT, malik_tel TEXT, kiraci_ad TEXT, kiraci_tc TEXT, kiraci_tel TEXT, plaka TEXT)''')
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
        st.markdown("**Sistem Giriş Paneli**")
        conn = sqlite3.connect('master.db')
        df_siteler = pd.read_sql_query("SELECT site_adi, tenant_db_adi FROM siteler", conn)
        conn.close()
        
        with st.container(border=True):
            if df_siteler.empty:
                st.info("Kayıtlı site yok. Lütfen yeni kurulum yapın.")
            else:
                secilen_site = st.selectbox("Site / Apartman Seçiniz", df_siteler['site_adi'].tolist())
                kullanici_adi = st.text_input("Kullanıcı Adı")
                sifre = st.text_input("Şifre", type="password")
                if st.button("Giriş Yap", type="primary", use_container_width=True):
                    secilen_db = df_siteler.loc[df_siteler['site_adi'] == secilen_site, 'tenant_db_adi'].values[0]
                    init_tenant_db(secilen_db)
                    conn_t = sqlite3.connect(secilen_db)
                    ct = conn_t.cursor()
                    ct.execute("SELECT kullanici_adi FROM yoneticiler WHERE kullanici_adi=? AND sifre=?", (kullanici_adi, sifre))
                    if ct.fetchone():
                        st.session_state.aktif_site = secilen_site
                        st.session_state.aktif_db = secilen_db
                        sayfa_degistir('Ana_Sayfa')
                        st.rerun()
                    else: st.error("Hatalı bilgiler!")
        st.button("Yeni Site Kaydı Oluştur", on_click=sayfa_degistir, args=('Kayıt',), use_container_width=True)

# --- YENİ SİTE KAYIT SAYFASI ---
elif st.session_state.sayfa == 'Kayıt':
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("📝 Yeni Site Kurulumu")
        with st.container(border=True):
            site_adi = st.text_input("Site / Apartman Adı")
            blok_adedi = st.number_input("Blok Adedi", min_value=1, step=1, value=1)
            blok_verileri = []
            if blok_adedi > 1:
                for i in range(blok_adedi):
                    c1, c2 = st.columns(2)
                    with c1: b_ad = st.text_input(f"{i+1}. Blok İsmi", key=f"bn_{i}")
                    with c2: d_say = st.number_input(f"{i+1}. Daire Sayısı", min_value=1, key=f"bc_{i}")
                    blok_verileri.append((b_ad, d_say))
            else:
                d_say = st.number_input("Daire Sayısı", min_value=1)
                blok_verileri.append(("Ana Blok", d_say))
            st.divider()
            yeni_k = st.text_input("Kullanıcı Adı")
            yeni_s = st.text_input("Şifre", type="password")
            s_tek = st.text_input("Şifre Tekrarı", type="password")
            if st.button("Sisteme Kaydet", type="primary", use_container_width=True):
                if yeni_s == s_tek and site_adi and yeni_k:
                    tenant_db = f"{site_adi.replace(' ', '_').lower()}_db.sqlite"
                    conn = sqlite3.connect('master.db'); c = conn.cursor()
                    c.execute("INSERT INTO siteler (site_adi, tenant_db_adi) VALUES (?, ?)", (site_adi, tenant_db))
                    conn.commit(); conn.close()
                    init_tenant_db(tenant_db)
                    conn_t = sqlite3.connect(tenant_db); ct = conn_t.cursor()
                    ct.executemany("INSERT INTO bloklar (blok_adi, daire_sayisi) VALUES (?, ?)", blok_verileri)
                    ct.execute("INSERT INTO yoneticiler (kullanici_adi, sifre) VALUES (?, ?)", (yeni_k, yeni_s))
                    conn_t.commit(); conn_t.close()
                    st.success("Kayıt başarılı!"); sayfa_degistir('Giriş'); st.rerun()
                else: st.error("Bilgileri kontrol edin!")
        st.button("⬅️ Geri Dön", on_click=sayfa_degistir, args=('Giriş',))

# --- ANA SAYFA ---
elif st.session_state.sayfa == 'Ana_Sayfa':
    db_yolu = st.session_state.aktif_db
    st.sidebar.title(f"🏢 {st.session_state.aktif_site}")
    if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.clear(); sayfa_degistir('Giriş'); st.rerun()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ Yeni Sakin", "📋 Daire Listesi", "💰 Tahakkuk", "✅ Tahsilat", "📊 Görsel Dashboard & Kasa"])

    with tab1:
        conn = sqlite3.connect(db_yolu); c = conn.cursor(); c.execute("SELECT blok_adi FROM bloklar")
        bloklar = [r[0] for r in c.fetchall()]; conn.close()
        with st.form("sakin_form", clear_on_submit=True):
            st.subheader("Konum ve Daire")
            col1, col2, col3 = st.columns(3)
            with col1: s_blok = st.selectbox("Blok Seç", bloklar)
            with col2: d_no = st.text_input("Daire No")
            with col3: plk = st.text_input("Plaka")
            st.divider(); c_m, c_k = st.columns(2)
            with c_m: m_a = st.text_input("Malik Ad"); m_tc = st.text_input("Malik TC"); m_t = st.text_input("Malik Tel")
            with c_k: k_a = st.text_input("Kiracı Ad"); k_tc = st.text_input("Kiracı TC"); k_t = st.text_input("Kiracı Tel")
            if st.form_submit_button("💾 Kaydet", type="primary"):
                conn = sqlite3.connect(db_yolu); c = conn.cursor()
                c.execute('''INSERT INTO sakinler (blok, daire_no, malik_ad, malik_tc, malik_tel, kiraci_ad, kiraci_tc, kiraci_tel, plaka) VALUES (?,?,?,?,?,?,?,?,?)''', (s_blok, d_no, m_a, m_tc, m_t, k_a, k_tc, k_t, plk))
                conn.commit(); conn.close(); st.success("Kayıt başarılı!")

    with tab2:
        st.subheader("Daire Listesi"); conn = sqlite3.connect(db_yolu)
        df_s = pd.read_sql_query("SELECT * FROM sakinler", conn); conn.close()
        if not df_s.empty: st.dataframe(df_s.drop(columns=['id']), use_container_width=True, hide_index=True)
        else: st.info("Kayıt yok.")

    with tab3:
        st.subheader("Borçlandırma"); conn = sqlite3.connect(db_yolu); c = conn.cursor()
        c.execute("SELECT blok, daire_no, malik_ad FROM sakinler"); s_list = c.fetchall(); conn.close()
        sec = ["🌟 Tüm Dairelere (Toplu)"] + [f"{s[0]} Blok No:{s[1]} ({s[2]})" for s in s_list]
        with st.form("borc_form", clear_on_submit=True):
            h = st.selectbox("Daire", sec); t = st.number_input("Tutar", min_value=0.0); dt = st.date_input("Tarih"); ac = st.text_input("Açıklama")
            if st.form_submit_button("💸 Borçlandır", type="primary"):
                conn = sqlite3.connect(db_yolu); c = conn.cursor()
                if h == "🌟 Tüm Dairelere (Toplu)":
                    for s in s_list: c.execute("INSERT INTO aidatlar (blok, daire_no, tarih, tutar, aciklama) VALUES (?,?,?,?,?)", (s[0], s[1], str(dt), t, ac))
                else:
                    idx = sec.index(h) - 1; s = s_list[idx]
                    c.execute("INSERT INTO aidatlar (blok, daire_no, tarih, tutar, aciklama) VALUES (?,?,?,?,?)", (s[0], s[1], str(dt), t, ac))
                conn.commit(); conn.close(); st.success("İşlem başarılı!")

    with tab4:
        st.subheader("Tahsilat"); conn = sqlite3.connect(db_yolu)
        df_b = pd.read_sql_query("SELECT id, blok, daire_no, aciklama, tutar FROM aidatlar WHERE durum='Ödenmedi'", conn)
        if not df_b.empty:
            st.dataframe(df_b.drop(columns=['id']), use_container_width=True, hide_index=True)
            opt = {f"{r[1]} Blok No:{r[2]} | {r[3]} ({r[4]} ₺)": r[0] for r in df_b.values}
            s_borc = st.selectbox("Ödeme Al", list(opt.keys()))
            if st.button("✅ Tahsil Et", type="primary"):
                c = conn.cursor(); c.execute("UPDATE aidatlar SET durum='Ödendi' WHERE id=?", (opt[s_borc],))
                conn.commit(); conn.close(); st.success("Tahsil edildi!"); st.rerun()
        else: st.success("Ödenmemiş borç yok."); conn.close()

    # --- 5. SEKME: GÖRSEL DASHBOARD & KASA ---
    with tab5:
        st.subheader("🏢 Site Finansal Analiz Dashboard")
        conn = sqlite3.connect(db_yolu)
        # Verileri çek
        c = conn.cursor()
        c.execute("SELECT SUM(tutar) FROM aidatlar WHERE durum='Ödendi'"); gelir = c.fetchone()[0] or 0.0
        c.execute("SELECT SUM(tutar) FROM giderler"); gider = c.fetchone()[0] or 0.0
        c.execute("SELECT SUM(tutar) FROM aidatlar WHERE durum='Ödenmedi'"); bekleyen = c.fetchone()[0] or 0.0
        
        # Üst Metrikler
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Toplam Tahsilat", f"{gelir:,.0f} ₺")
        m2.metric("💸 Toplam Gider", f"{gider:,.0f} ₺")
        m3.metric("⚖️ Net Kasa", f"{(gelir-gider):,.0f} ₺")
        m4.metric("⏳ Bekleyen Alacak", f"{bekleyen:,.0f} ₺", delta_color="inverse")

        st.divider()
        col_graf_1, col_graf_2 = st.columns(2)

        with col_graf_1:
            st.markdown("##### 📊 Gelir vs Gider Dengesi")
            # Basit Bar Chart verisi
            chart_data = pd.DataFrame({'Kategori': ['Gelir', 'Gider'], 'Tutar (₺)': [gelir, gider]})
            st.bar_chart(chart_data.set_index('Kategori'))

        with col_graf_2:
            st.markdown("##### 📉 Harcama Dağılımı (Kategori Bazlı)")
            df_gider_analiz = pd.read_sql_query("SELECT kategori, SUM(tutar) as Toplam FROM giderler GROUP BY kategori", conn)
            if not df_gider_analiz.empty:
                st.bar_chart(df_gider_analiz.set_index('kategori'))
            else:
                st.info("Harcama grafiği için henüz gider kaydı girilmemiş.")

        st.divider()
        # Gider Ekleme Alanı
        with st.expander("➕ Yeni Gider (Harcama) Ekle"):
            with st.form("gider_form_new", clear_on_submit=True):
                c_a, c_b = st.columns(2)
                with c_a: k_g = st.selectbox("Kategori", ["Elektrik", "Su", "Maaş", "Bakım", "Temizlik", "Diğer"]); t_g = st.number_input("Tutar", min_value=0.0)
                with c_b: dt_g = st.date_input("Tarih"); ac_g = st.text_input("Açıklama")
                if st.form_submit_button("💳 Kasadan Harca"):
                    c = conn.cursor(); c.execute("INSERT INTO giderler (tarih, kategori, tutar, aciklama) VALUES (?,?,?,?)", (str(dt_g), k_g, t_g, ac_g))
                    conn.commit(); st.success("Gider işlendi!"); st.rerun()

        # Son Hareketler
        st.markdown("##### 📜 Son Kasa Hareketleri (Harcamalar)")
        df_g_list = pd.read_sql_query("SELECT tarih as Tarih, kategori as Kategori, tutar as 'Tutar (₺)', aciklama as Açıklama FROM giderler ORDER BY id DESC LIMIT 5", conn)
        st.table(df_g_list)
        conn.close()
