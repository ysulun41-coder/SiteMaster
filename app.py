import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io

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

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='SiteMaster_Rapor')
    return output.getvalue()

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

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["➕ Sakin", "📋 Liste", "💰 Tahakkuk", "✅ Tahsilat", "📊 Dashboard", "📥 Raporlar"])

    with tab1:
        conn = sqlite3.connect(db_yolu); c = conn.cursor(); c.execute("SELECT blok_adi FROM bloklar")
        bloklar = [r[0] for r in c.fetchall()]; conn.close()
        with st.form("sakin_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1: s_blok = st.selectbox("Blok Seç", bloklar)
            with col2: d_no = st.text_input("Daire No")
            with col3: plk = st.text_input("Plaka")
            c_m, c_k = st.columns(2)
            with c_m: m_a = st.text_input("Malik Ad"); m_tc = st.text_input("Malik TC"); m_t = st.text_input("Malik Tel")
            with c_k: k_a = st.text_input("Kiracı Ad"); k_tc = st.text_input("Kiracı TC"); k_t = st.text_input("Kiracı Tel")
            if st.form_submit_button("💾 Kaydet", type="primary"):
                if s_blok and d_no and m_a:
                    conn = sqlite3.connect(db_yolu); c = conn.cursor()
                    c.execute("SELECT id FROM sakinler WHERE blok=? AND daire_no=?", (s_blok, d_no))
                    if c.fetchone():
                        st.error(f"⚠️ Hata: {s_blok} Blok, {d_no} No'lu daire zaten sistemde dolu!")
                    else:
                        c.execute('''INSERT INTO sakinler (blok, daire_no, malik_ad, malik_tc, malik_tel, kiraci_ad, kiraci_tc, kiraci_tel, plaka) VALUES (?,?,?,?,?,?,?,?,?)''', (s_blok, d_no, m_a, m_tc, m_t, k_a, k_tc, k_t, plk))
                        conn.commit(); st.success("Kayıt başarıyla işlendi!")
                    conn.close()
                else:
                    st.error("Blok, Daire No ve Malik Adı zorunludur!")

    with tab2:
        st.subheader("Daire Listesi"); conn = sqlite3.connect(db_yolu)
        df_s = pd.read_sql_query("SELECT * FROM sakinler", conn); conn.close()
        if not df_s.empty: st.dataframe(df_s.drop(columns=['id']), use_container_width=True, hide_index=True)

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
        st.subheader("💰 Tahsilat ve Makbuz Kesimi")
        if 'makbuz_data' in st.session_state:
            st.success("✅ Tahsilat başarıyla kaydedildi!")
            makbuz_metni = f"""
====================================
 🏢 SİTEMASTER TAHSİLAT MAKBUZU
====================================
Site Adı    : {st.session_state.aktif_site}
İşlem Tarihi: {datetime.date.today().strftime("%d.%m.%Y")}
------------------------------------
TAHSİLAT BİLGİSİ:
{st.session_state.makbuz_data}

Durum       : ÖDENDİ (Tahsil Edildi)
====================================
Bizi tercih ettiğiniz için teşekkürler.
            """
            st.code(makbuz_metni, language="text")
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.download_button("📥 Makbuzu İndir (Txt)", data=makbuz_metni, file_name="Makbuz.txt", mime="text/plain", use_container_width=True)
            with col_m2:
                if st.button("🔄 Yeni İşlem Yap (Makbuzu Kapat)", use_container_width=True):
                    del st.session_state.makbuz_data
                    st.rerun()
            st.divider()

        conn = sqlite3.connect(db_yolu)
        c = conn.cursor()
        c.execute("SELECT id, blok, daire_no, aciklama, tutar FROM aidatlar WHERE durum='Ödenmedi'")
        odenmemis_listesi = c.fetchall()
        
        if odenmemis_listesi:
            df_b = pd.DataFrame(odenmemis_listesi, columns=['id', 'Blok', 'Daire No', 'Açıklama', 'Tutar (₺)'])
            st.dataframe(df_b.drop(columns=['id']), use_container_width=True, hide_index=True)
            borc_secenekleri = {f"{r[1]} Blok No: {r[2]} | {r[3]} ({r[4]:.2f} ₺)": r[0] for r in odenmemis_listesi}
            
            with st.form("tahsilat_yap_form"):
                secilen_borc_metin = st.selectbox("Ödeme Alınacak Kayıt", list(borc_secenekleri.keys()))
                if st.form_submit_button("✅ Ödemeyi Al ve Makbuz Kes", type="primary"):
                    borc_id = borc_secenekleri[secilen_borc_metin]
                    c.execute("UPDATE aidatlar SET durum='Ödendi' WHERE id=?", (borc_id,))
                    conn.commit()
                    conn.close()
                    st.session_state.makbuz_data = secilen_borc_metin
                    st.rerun()
        else: 
            st.success("Ödenmemiş borç yok!")
            conn.close()

    with tab5:
        st.subheader("🏢 Finansal Analiz Dashboard")
        conn = sqlite3.connect(db_yolu); c = conn.cursor()
        c.execute("SELECT SUM(tutar) FROM aidatlar WHERE durum='Ödendi'"); gelir = c.fetchone()[0] or 0.0
        c.execute("SELECT SUM(tutar) FROM giderler"); gider = c.fetchone()[0] or 0.0
        c.execute("SELECT SUM(tutar) FROM aidatlar WHERE durum='Ödenmedi'"); bekleyen = c.fetchone()[0] or 0.0
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💰 Toplam Tahsilat", f"{gelir:,.0f} ₺"); m2.metric("💸 Toplam Gider", f"{gider:,.0f} ₺")
        m3.metric("⚖️ Net Kasa", f"{(gelir-gider):,.0f} ₺"); m4.metric("⏳ Bekleyen Alacak", f"{bekleyen:,.0f} ₺", delta_color="inverse")
        st.divider(); c_g1, c_g2 = st.columns(2)
        with c_g1: st.markdown("##### Gelir-Gider Dengesi"); st.bar_chart(pd.DataFrame({'Kategori': ['Gelir', 'Gider'], 'Tutar': [gelir, gider]}).set_index('Kategori'))
        with c_g2: st.markdown("##### Harcama Kategorileri"); df_ga = pd.read_sql_query("SELECT kategori, SUM(tutar) as Toplam FROM giderler GROUP BY kategori", conn); st.bar_chart(df_ga.set_index('kategori')) if not df_ga.empty else st.info("Gider yok.")
        st.divider(); 
        with st.expander("➕ Yeni Gider Ekle"):
            with st.form("g_f", clear_on_submit=True):
                ca, cb = st.columns(2)
                with ca: kg = st.selectbox("Kategori", ["Elektrik", "Su", "Maaş", "Bakım", "Diğer"]); tg = st.number_input("Tutar")
                with cb: dtg = st.date_input("Tarih"); acg = st.text_input("Açıklama")
                if st.form_submit_button("💳 Harca"):
                    c = conn.cursor(); c.execute("INSERT INTO giderler (tarih, kategori, tutar, aciklama) VALUES (?,?,?,?)", (str(dtg), kg, tg, acg))
                    conn.commit(); st.rerun()
        conn.close()

    with tab6:
        st.subheader("📥 Profesyonel Raporlama Merkezi")
        c1, c2, c3 = st.columns(3)
        conn = sqlite3.connect(db_yolu)
        
        with c1:
            st.info("🏠 **Sakin Listesi**")
            df_sakin_exp = pd.read_sql_query("SELECT blok as Blok, daire_no as Daire, malik_ad as Malik, malik_tel as Telefon, kiraci_ad as Kiracı, plaka as Plaka FROM sakinler", conn)
            if not df_sakin_exp.empty:
                st.download_button(label="📥 İndir (Excel)", data=to_excel(df_sakin_exp), file_name=f"Sakin_Listesi_{st.session_state.aktif_site}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            else: st.caption("Kayıt bulunamadı.")

        with c2:
            st.error("⏳ **Borçlu Listesi**")
            df_borc_exp = pd.read_sql_query("SELECT blok as Blok, daire_no as Daire, aciklama as Açıklama, tutar as Tutar, tarih as Tarih FROM aidatlar WHERE durum='Ödenmedi'", conn)
            if not df_borc_exp.empty:
                st.download_button(label="📥 İndir (Excel)", data=to_excel(df_borc_exp), file_name=f"Borclu_Listesi_{st.session_state.aktif_site}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            else: st.success("Ödenmemiş borç yok!")

        with c3:
            st.success("🧾 **Kasa Ekstresi**")
            df_gelir_exp = pd.read_sql_query("SELECT tarih, aciklama, tutar, 'GELİR' as Tip FROM aidatlar WHERE durum='Ödendi'", conn)
            df_gider_exp = pd.read_sql_query("SELECT tarih, aciklama, tutar, 'GİDER' as Tip FROM giderler", conn)
            df_kasa_ekstresi = pd.concat([df_gelir_exp, df_gider_exp]).sort_values(by='tarih', ascending=False)
            
            if not df_kasa_ekstresi.empty:
                st.download_button(label="📥 İndir (Excel)", data=to_excel(df_kasa_ekstresi), file_name=f"Kasa_Ekstresi_{st.session_state.aktif_site}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            else: st.caption("Hareket bulunamadı.")
            
        conn.close()
