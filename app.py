import streamlit as st
import pandas as pd
import sqlite3
import os
import datetime

# --- 1. MASTER DB (REHBER) ---
def init_master_db():
    conn = sqlite3.connect('master.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS siteler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_adi TEXT UNIQUE,
            tenant_db_adi TEXT
        )
    ''')
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
                st.info("Sisteme henüz kayıtlı bir site yok. Lütfen yeni kurulum yapın.")
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
                    sonuc = ct.fetchone()
                    conn_t.close()
                    
                    if sonuc:
                        st.session_state.aktif_site = secilen_site
                        st.session_state.aktif_db = secilen_db
                        sayfa_degistir('Ana_Sayfa')
                        st.rerun()
                    else:
                        st.error("Hatalı bilgiler!")
        
        st.write("")
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
                st.markdown("##### Blok Detaylarını Girin")
                for i in range(blok_adedi):
                    c1, c2 = st.columns(2)
                    with c1: b_ad = st.text_input(f"{i+1}. Blok İsmi", key=f"bname_{i}")
                    with c2: d_say = st.number_input(f"{i+1}. Daire Sayısı", min_value=1, step=1, key=f"bcnt_{i}")
                    blok_verileri.append((b_ad, d_say))
            else:
                d_say = st.number_input("Daire Sayısı", min_value=1, step=1)
                blok_verileri.append(("Ana Blok", d_say))
                
            st.divider()
            yeni_kullanici = st.text_input("Yönetici Kullanıcı Adı")
            yeni_sifre = st.text_input("Şifre", type="password")
            sifre_tekrar = st.text_input("Şifre Tekrarı", type="password")
            
            if st.button("Sisteme Kaydet", type="primary", use_container_width=True):
                if yeni_sifre != sifre_tekrar:
                    st.error("Şifreler uyuşmuyor!")
                elif not site_adi or not yeni_kullanici or not yeni_sifre:
                    st.warning("Lütfen tüm alanları doldurun.")
                else:
                    tenant_db = f"{site_adi.replace(' ', '_').lower()}_db.sqlite"
                    try:
                        conn = sqlite3.connect('master.db')
                        c = conn.cursor()
                        c.execute("INSERT INTO siteler (site_adi, tenant_db_adi) VALUES (?, ?)", (site_adi, tenant_db))
                        conn.commit()
                        conn.close()
                        
                        init_tenant_db(tenant_db)
                        conn_t = sqlite3.connect(tenant_db)
                        ct = conn_t.cursor()
                        ct.executemany("INSERT INTO bloklar (blok_adi, daire_sayisi) VALUES (?, ?)", blok_verileri)
                        ct.execute("INSERT INTO yoneticiler (kullanici_adi, sifre) VALUES (?, ?)", (yeni_kullanici, yeni_sifre))
                        conn_t.commit()
                        conn_t.close()
                        
                        st.success("Kurulum tamamlandı!")
                        sayfa_degistir('Giriş')
                        st.rerun()
                    except:
                        st.error("Bu site zaten mevcut!")

        st.button("⬅️ Geri Dön", on_click=sayfa_degistir, args=('Giriş',))

# --- ANA SAYFA ---
elif st.session_state.sayfa == 'Ana_Sayfa':
    db_yolu = st.session_state.aktif_db
    st.sidebar.title(f"🏢 {st.session_state.aktif_site}")
    if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.clear()
        sayfa_degistir('Giriş')
        st.rerun()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["➕ Yeni Sakin", "📋 Daire Listesi", "💰 Tahakkuk", "✅ Tahsilat", "📉 Kasa & Gider"])
    
    with tab1:
        conn = sqlite3.connect(db_yolu)
        c = conn.cursor()
        c.execute("SELECT blok_adi FROM bloklar")
        mevcut_bloklar = [row[0] for row in c.fetchall()]
        conn.close()
        with st.form("sakin_form", clear_on_submit=True):
            st.subheader("Konum ve Daire")
            col1, col2, col3 = st.columns(3)
            with col1: secilen_blok = st.selectbox("Blok Seçin", mevcut_bloklar)
            with col2: daire_no = st.text_input("Daire No")
            with col3: plaka = st.text_input("Araç Plakası")
            st.divider()
            c_malik, c_kiraci = st.columns(2)
            with c_malik:
                st.markdown("**Kat Maliki**")
                m_ad = st.text_input("Ad Soyad", key="m1")
                m_tc = st.text_input("TC No", max_chars=11, key="m2")
                m_tel = st.text_input("Telefon", key="m3")
            with c_kiraci:
                st.markdown("**Kiracı (Varsa)**")
                k_ad = st.text_input("Ad Soyad", key="k1")
                k_tc = st.text_input("TC No", max_chars=11, key="k2")
                k_tel = st.text_input("Telefon", key="k3")
            if st.form_submit_button("💾 Kaydet", type="primary"):
                if secilen_blok and daire_no and m_ad:
                    conn = sqlite3.connect(db_yolu)
                    c = conn.cursor()
                    c.execute('''INSERT INTO sakinler (blok, daire_no, malik_ad, malik_tc, malik_tel, kiraci_ad, kiraci_tc, kiraci_tel, plaka) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (secilen_blok, daire_no, m_ad, m_tc, m_tel, k_ad, k_tc, k_tel, plaka))
                    conn.commit()
                    conn.close()
                    st.success("Kayıt başarılı!")
                else: st.error("Eksik bilgi!")

    with tab2:
        st.subheader("Daire Listesi")
        conn = sqlite3.connect(db_yolu)
        df = pd.read_sql_query("SELECT * FROM sakinler", conn)
        conn.close()
        if not df.empty: st.dataframe(df.drop(columns=['id']), use_container_width=True, hide_index=True)
        else: st.info("Kayıt yok.")

    with tab3:
        st.subheader("Borçlandırma İşlemi")
        conn = sqlite3.connect(db_yolu)
        c = conn.cursor()
        c.execute("SELECT blok, daire_no, malik_ad FROM sakinler")
        sakinler = c.fetchall()
        conn.close()
        secenekler = ["🌟 Tüm Dairelere Ortak Tahakkuk (Toplu)"]
        for s in sakinler: secenekler.append(f"{s[0]} Blok - No: {s[1]} ({s[2]})")
        with st.form("tahakkuk_form", clear_on_submit=True):
            hedef = st.selectbox("Daire Seçin", secenekler)
            tutar = st.number_input("Tutar (₺)", min_value=0.0, step=50.0, value=500.0)
            tarih = st.date_input("Tarih", datetime.date.today())
            aciklama = st.text_input("Açıklama", placeholder="Örn: Aidat")
            if st.form_submit_button("💸 Borçlandır", type="primary"):
                if tutar > 0 and aciklama:
                    conn = sqlite3.connect(db_yolu)
                    c = conn.cursor()
                    if hedef == "🌟 Tüm Dairelere Ortak Tahakkuk (Toplu)":
                        for s in sakinler: c.execute("INSERT INTO aidatlar (blok, daire_no, tarih, tutar, aciklama, durum) VALUES (?, ?, ?, ?, ?, ?)", (s[0], s[1], str(tarih), tutar, aciklama, 'Ödenmedi'))
                    else:
                        idx = secenekler.index(hedef) - 1
                        s = sakinler[idx]
                        c.execute("INSERT INTO aidatlar (blok, daire_no, tarih, tutar, aciklama, durum) VALUES (?, ?, ?, ?, ?, ?)", (s[0], s[1], str(tarih), tutar, aciklama, 'Ödenmedi'))
                    conn.commit()
                    conn.close()
                    st.success("İşlem başarılı!")
                else: st.error("Eksik bilgi!")

    # --- TAHSİLAT EKRANI (DÜZELTİLDİ) ---
    with tab4:
        st.subheader("💰 Borçlu Listesi ve Ödeme Alma")
        conn = sqlite3.connect(db_yolu)
        # 1. Önce bekleyen borçları bir tablo olarak gösterelim
        df_borclular = pd.read_sql_query("SELECT blok as Blok, daire_no as 'Daire No', aciklama as Açıklama, tutar as 'Tutar (₺)', tarih as Tarih FROM aidatlar WHERE durum='Ödenmedi'", conn)
        
        if not df_borclular.empty:
            st.warning("⚠️ Ödenmesi beklenen borçların listesi aşağıdadır:")
            st.dataframe(df_borclular, use_container_width=True, hide_index=True)
            
            st.divider()
            # 2. Şimdi bu borçlardan birini seçip tahsil etme formu
            c = conn.cursor()
            c.execute("SELECT id, blok, daire_no, aciklama, tutar FROM aidatlar WHERE durum='Ödenmedi'")
            odenmemis_listesi = c.fetchall()
            conn.close()

            borc_secenekleri = {f"{b[1]} Blok No: {b[2]} - {b[3]} ({b[4]} ₺)": b[0] for b in odenmemis_listesi}

            with st.form("tahsilat_yap_form"):
                st.markdown("##### Tahsilat Yapılacak Daireyi Seçin")
                secilen_borc_metin = st.selectbox("Borç Kaydı", list(borc_secenekleri.keys()))
                tahsil_et = st.form_submit_button("✅ Ödemeyi Al (Ödendi İşaretle)", type="primary")

                if tahsil_et:
                    borc_id = borc_secenekleri[secilen_borc_metin]
                    conn = sqlite3.connect(db_yolu)
                    c = conn.cursor()
                    c.execute("UPDATE aidatlar SET durum='Ödendi' WHERE id=?", (borc_id,))
                    conn.commit()
                    conn.close()
                    st.success("Tahsilat başarıyla kaydedildi! Liste güncelleniyor...")
                    st.rerun()
        else:
            st.success("Harika! Ödenmemiş herhangi bir borç kaydı bulunamadı. 🎉")
            conn.close()

    with tab5:
        st.subheader("📉 Kasa & Gider Yönetimi")
        conn = sqlite3.connect(db_yolu)
        c = conn.cursor()
        c.execute("SELECT SUM(tutar) FROM aidatlar WHERE durum='Ödendi'")
        gelir = c.fetchone()[0] or 0.0
        c.execute("SELECT SUM(tutar) FROM giderler")
        gider = c.fetchone()[0] or 0.0
        conn.close()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Gelir", f"{gelir:,.2f} ₺")
        c2.metric("Gider", f"{gider:,.2f} ₺")
        c3.metric("Kasa", f"{(gelir-gider):,.2f} ₺")
        
        with st.form("gider_form", clear_on_submit=True):
            st.markdown("##### Yeni Gider Çıkışı")
            kat = st.selectbox("Kategori", ["Elektrik", "Su", "Maaş", "Bakım", "Diğer"])
            tut = st.number_input("Tutar", min_value=0.0)
            detay = st.text_input("Açıklama")
            if st.form_submit_button("💳 Ödeme Yap"):
                if tut > 0:
                    conn = sqlite3.connect(db_yolu)
                    c = conn.cursor()
                    c.execute("INSERT INTO giderler (tarih, kategori, tutar, aciklama) VALUES (?, ?, ?, ?)", (str(datetime.date.today()), kat, tut, detay))
                    conn.commit()
                    conn.close()
                    st.rerun()
