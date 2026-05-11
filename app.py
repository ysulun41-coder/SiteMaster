import streamlit as st
import pandas as pd
import sqlite3
import os
import datetime

# --- 1. MASTER DB (FİHRİST) ---
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

# --- 2. TENANT DB (SİTEYE ÖZEL KASA) ---
def init_tenant_db(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS yoneticiler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kullanici_adi TEXT UNIQUE,
            sifre TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS sakinler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blok TEXT,
            daire_no TEXT,
            malik_ad TEXT,
            malik_tc TEXT,
            malik_tel TEXT,
            kiraci_ad TEXT,
            kiraci_tc TEXT,
            kiraci_tel TEXT,
            plaka TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bloklar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blok_adi TEXT,
            daire_sayisi INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS aidatlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blok TEXT,
            daire_no TEXT,
            tarih TEXT,
            tutar REAL,
            aciklama TEXT,
            durum TEXT DEFAULT 'Ödenmedi'
        )
    ''')
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
                # Senin istediğin gibi: Eski pratik açılır listeye (Selectbox) geri döndük!
                secilen_site = st.selectbox("Site / Apartman Seçiniz", df_siteler['site_adi'].tolist())
                kullanici_adi = st.text_input("Kullanıcı Adı")
                sifre = st.text_input("Şifre", type="password")
                
                if st.button("Giriş Yap", type="primary", use_container_width=True):
                    secilen_db = df_siteler.loc[df_siteler['site_adi'] == secilen_site, 'tenant_db_adi'].values[0]
                    
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
                        st.error("Kullanıcı adı veya şifre hatalı!")
        
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
                    with c1:
                        b_ad = st.text_input(f"{i+1}. Blok İsmi", key=f"bname_{i}")
                    with c2:
                        d_say = st.number_input(f"{i+1}. Daire Sayısı", min_value=1, step=1, key=f"bcnt_{i}")
                    blok_verileri.append((b_ad, d_say))
            else:
                d_say = st.number_input("Daire Sayısı", min_value=1, step=1)
                blok_verileri.append(("Ana Blok", d_say))
                
            st.divider()
            st.markdown("##### Yönetici Hesabı Oluştur")
            yeni_kullanici = st.text_input("Kullanıcı Adı")
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
                        
                        st.success("Kurulum başarıyla tamamlandı! Giriş ekranına yönlendiriliyorsunuz...")
                        sayfa_degistir('Giriş')
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Bu site adı zaten sisteme kayıtlı!")

        st.button("⬅️ İptal ve Geri Dön", on_click=sayfa_degistir, args=('Giriş',))

# --- ANA SAYFA ---
elif st.session_state.sayfa == 'Ana_Sayfa':
    db_yolu = st.session_state.aktif_db
    
    st.sidebar.title(f"🏢 {st.session_state.aktif_site}")
    if st.sidebar.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.clear()
        sayfa_degistir('Giriş')
        st.rerun()

    st.title("📊 Sakin, Aidat ve Finans Yönetimi")
    
    # 4. SEKMEYİ (TAHSİLAT) EKLİYORUZ
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Yeni Sakin", "📋 Daire Listesi", "💰 Tahakkuk (Borç)", "✅ Tahsilat (Ödeme)"])
    
    with tab1:
        conn = sqlite3.connect(db_yolu)
        c = conn.cursor()
        c.execute("SELECT blok_adi FROM bloklar")
        mevcut_bloklar = [row[0] for row in c.fetchall()]
        conn.close()

        with st.form("sakin_form", clear_on_submit=True):
            st.subheader("Konum ve Daire")
            col1, col2, col3 = st.columns(3)
            with col1:
                secilen_blok = st.selectbox("Blok Seçin", mevcut_bloklar)
            with col2:
                daire_no = st.text_input("Daire No")
            with col3:
                plaka = st.text_input("Araç Plakası")

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

            if st.form_submit_button("💾 Kaydı Tamamla", type="primary"):
                if secilen_blok and daire_no and m_ad:
                    conn = sqlite3.connect(db_yolu)
                    c = conn.cursor()
                    c.execute('''INSERT INTO sakinler 
                                (blok, daire_no, malik_ad, malik_tc, malik_tel, kiraci_ad, kiraci_tc, kiraci_tel, plaka) 
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                              (secilen_blok, daire_no, m_ad, m_tc, m_tel, k_ad, k_tc, k_tel, plaka))
                    conn.commit()
                    conn.close()
                    st.success("Kayıt başarıyla veritabanına işlendi!")
                else:
                    st.error("Lütfen gerekli alanları doldurun!")

    with tab2:
        st.subheader("Daire Listesi")
        conn = sqlite3.connect(db_yolu)
        df = pd.read_sql_query("SELECT * FROM sakinler", conn)
        conn.close()
        if not df.empty:
            st.dataframe(df.drop(columns=['id']), use_container_width=True, hide_index=True)
        else:
            st.info("Kayıtlı daire bulunamadı.")

    with tab3:
        st.subheader("Aidat ve Gider Tahakkuku")
        conn = sqlite3.connect(db_yolu)
        c = conn.cursor()
        c.execute("SELECT blok, daire_no, malik_ad FROM sakinler")
        sakin_listesi = c.fetchall()
        conn.close()
        
        secenekler = ["🌟 Tüm Dairelere Ortak Tahakkuk (Toplu)"]
        for s in sakin_listesi:
            secenekler.append(f"{s[0]} Blok - No: {s[1]} ({s[2]})")
            
        with st.form("tahakkuk_form", clear_on_submit=True):
            hedef = st.selectbox("Borçlandırılacak Daire", secenekler)
            col_a, col_b = st.columns(2)
            with col_a:
                tutar = st.number_input("Tahakkuk Tutarı (₺)", min_value=0.0, step=50.0, value=500.0)
            with col_b:
                tarih = st.date_input("Borçlandırma Tarihi", datetime.date.today())
                
            aciklama = st.text_input("Açıklama", placeholder="Örn: 2026 Mayıs Ayı Olağan Aidatı")
            
            if st.form_submit_button("💸 Seçili Hedefi Borçlandır", type="primary"):
                if tutar > 0 and aciklama:
                    conn = sqlite3.connect(db_yolu)
                    c = conn.cursor()
                    if hedef == "🌟 Tüm Dairelere Ortak Tahakkuk (Toplu)":
                        for sakin in sakin_listesi:
                            c.execute("INSERT INTO aidatlar (blok, daire_no, tarih, tutar, aciklama) VALUES (?, ?, ?, ?, ?)", 
                                      (sakin[0], sakin[1], str(tarih), tutar, aciklama))
                        st.success(f"Başarılı! Toplam {len(sakin_listesi)} daireye borç yazıldı.")
                    else:
                        secim_index = secenekler.index(hedef) - 1
                        secili_sakin = sakin_listesi[secim_index]
                        c.execute("INSERT INTO aidatlar (blok, daire_no, tarih, tutar, aciklama) VALUES (?, ?, ?, ?, ?)", 
                                  (secili_sakin[0], secili_sakin[1], str(tarih), tutar, aciklama))
                        st.success(f"Başarılı! {secili_sakin[0]} Blok No: {secili_sakin[1]} hesabına borç yazıldı.")
                    conn.commit()
                    conn.close()
                else:
                    st.error("Lütfen tutar ve açıklama giriniz.")
                    
        st.divider()
        st.markdown("##### Son Kesilen Borçlandırmalar")
        conn = sqlite3.connect(db_yolu)
        df_aidat = pd.read_sql_query("SELECT blok as Blok, daire_no as 'Daire No', tarih as Tarih, tutar as 'Tutar (₺)', aciklama as Açıklama, durum as Durum FROM aidatlar ORDER BY id DESC LIMIT 10", conn)
        conn.close()
        
        if not df_aidat.empty:
            # Ödenmeyenleri kırmızı, ödenenleri yeşil vurgulamak için ufak bir stil hilesi
            st.dataframe(df_aidat.style.map(lambda x: 'color: red' if x == 'Ödenmedi' else ('color: green' if x == 'Ödendi' else ''), subset=['Durum']), use_container_width=True, hide_index=True)
        else:
            st.caption("Henüz bir borçlandırma işlemi yapılmamış.")

    # --- YENİ EKLENEN 4. SEKME: TAHSİLAT ---
    with tab4:
        st.subheader("Ödeme Alma (Tahsilat İşlemleri)")
        
        conn = sqlite3.connect(db_yolu)
        c = conn.cursor()
        # Sadece durumu 'Ödenmedi' olan borçları çekiyoruz
        c.execute("SELECT id, blok, daire_no, aciklama, tutar, tarih FROM aidatlar WHERE durum='Ödenmedi'")
        odenmemis_borclar = c.fetchall()
        conn.close()

        if odenmemis_borclar:
            # Açılır listede şık görünmesi için sözlük (dictionary) yapısı kuruyoruz
            borc_secenekleri = {f"{b[1]} Blok No: {b[2]} | {b[3]} ({b[4]} ₺) - Tarih: {b[5]}": b[0] for b in odenmemis_borclar}
            
            with st.form("tahsilat_form"):
                st.info("Aşağıdaki listeden ödemesini yapan daireyi seçip tahsilatı gerçekleştirebilirsiniz.")
                secilen_borc_metin = st.selectbox("Ödemesi Alınacak Borcu Seçin", list(borc_secenekleri.keys()))
                
                if st.form_submit_button("✅ Seçili Borcu Tahsil Et (Ödendi İşaretle)", type="primary"):
                    borc_id = borc_secenekleri[secilen_borc_metin]
                    
                    conn = sqlite3.connect(db_yolu)
                    c = conn.cursor()
                    # Durumu Ödendi olarak güncelliyoruz
                    c.execute("UPDATE aidatlar SET durum='Ödendi' WHERE id=?", (borc_id,))
                    conn.commit()
                    conn.close()
                    
                    st.success("Tahsilat başarıyla işlendi ve makbuz kesildi! (Sayfa yenileniyor...)")
                    # Ekranı anında güncelleyip o borcu listeden düşürüyoruz
                    st.rerun()
        else:
            st.success("Harika haber! Sistemde ödenmemiş hiçbir borç veya aidat bulunmuyor. 🎉")
            
        st.divider()
        st.markdown("##### Son Alınan Ödemeler (Geçmiş Tahsilatlar)")
        conn = sqlite3.connect(db_yolu)
        df_odenen = pd.read_sql_query("SELECT blok as Blok, daire_no as 'Daire No', tarih as Tarih, tutar as 'Tutar (₺)', aciklama as Açıklama FROM aidatlar WHERE durum='Ödendi' ORDER BY id DESC LIMIT 10", conn)
        conn.close()
        
        if not df_odenen.empty:
            st.dataframe(df_odenen, use_container_width=True, hide_index=True)
        else:
            st.caption("Henüz tahsil edilmiş bir ödeme bulunmuyor.")
