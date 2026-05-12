import streamlit as st
import pandas as pd
import sqlite3
import datetime

def goster(db_yolu):
    st.subheader("📦 Demirbaş ve Zimmet Yönetimi")
    
    conn = sqlite3.connect(db_yolu)
    c = conn.cursor()
    
    # 1. VERİTABANI ALTYAPILARI (Otomatik Oluşturulur)
    c.execute('''CREATE TABLE IF NOT EXISTS demirbaslar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adi TEXT,
        alim_tarihi TEXT,
        satici TEXT,
        garanti_suresi TEXT,
        durum TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS zimmetler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        demirbas_id INTEGER,
        zimmetlenen_kisi TEXT,
        verilis_tarihi TEXT,
        teslim_durumu TEXT,
        aciklama TEXT,
        geri_alma_tarihi TEXT
    )''')
    conn.commit()

    d_tab1, d_tab2 = st.tabs(["🛠️ Demirbaş Kayıt & Liste", "🤝 Zimmet / Emanet Takibi"])

    # --- TAB 1: DEMİRBAŞ KAYIT VE LİSTE ---
    with d_tab1:
        with st.form("demirbas_kayit_form", clear_on_submit=True):
            st.markdown("##### ➕ Yeni Demirbaş Ekle")
            col1, col2 = st.columns(2)
            with col1:
                d_adi = st.text_input("Demirbaş Adı (Örn: Bosch Matkap, Çim Biçme Makinesi)")
                d_satici = st.text_input("Nereden Alındı? (Firma/Şahıs)")
                d_alim = st.date_input("Alınma Tarihi", datetime.date.today())
            with col2:
                d_garanti = st.text_input("Garanti Süresi (Örn: 2 Yıl, Yok)")
                d_durum = st.selectbox("Mevcut Durumu", ["Sağlam", "Arızalı", "Bakımda", "Atıl", "Kayıp"])
            
            if st.form_submit_button("💾 Demirbaşı Kaydet", type="primary"):
                if d_adi:
                    c.execute("INSERT INTO demirbaslar (adi, alim_tarihi, satici, garanti_suresi, durum) VALUES (?,?,?,?,?)",
                              (d_adi, str(d_alim), d_satici, d_garanti, d_durum))
                    conn.commit()
                    st.success(f"{d_adi} sisteme başarıyla eklendi.")
                    st.rerun()
                else:
                    st.error("Lütfen Demirbaş Adı giriniz.")

        st.divider()
        st.markdown("##### 📋 Envanter Listesi")
        df_d = pd.read_sql_query("SELECT id as ID, adi as 'Demirbaş Adı', alim_tarihi as 'Alım Tarihi', satici as 'Satıcı', garanti_suresi as 'Garanti', durum as 'Durum' FROM demirbaslar ORDER BY id DESC", conn)
        if not df_d.empty:
            # Duruma göre renklendirme
            st.dataframe(df_d.style.map(lambda x: 'color: red' if x in ['Arızalı', 'Kayıp'] else ('color: orange' if x in ['Bakımda', 'Atıl'] else 'color: green'), subset=['Durum']), use_container_width=True, hide_index=True)
        else:
            st.info("Sistemde henüz demirbaş kaydı bulunmuyor.")

    # --- TAB 2: ZİMMET VE EMANET TAKİBİ ---
    with d_tab2:
        c.execute("SELECT id, adi, durum FROM demirbaslar WHERE durum != 'Kayıp' AND durum != 'Atıl'")
        d_list = c.fetchall()
        
        if d_list:
            # Sadece boştaki demirbaşları vermek için aktif zimmetleri kontrol edebiliriz ama esnek bırakalım
            d_secenekler = {f"ID:{d[0]} - {d[1]} ({d[2]})": d[0] for d in d_list}
            
            with st.form("zimmet_ver_form", clear_on_submit=True):
                st.markdown("##### 📤 Demirbaşı Emanet Ver")
                col_z1, col_z2 = st.columns(2)
                with col_z1:
                    sec_demirbas = st.selectbox("Verilecek Demirbaş", list(d_secenekler.keys()))
                    zimmet_kisi = st.text_input("Kime Verildi? (Ad Soyad / Görev)")
                    verilis_tarih = st.date_input("Veriliş Tarihi", datetime.date.today())
                with col_z2:
                    teslim_durum = st.selectbox("Teslim Edilirken Durumu", ["Sağlam", "Arızalı / Çizik"])
                    teslim_aciklama = st.text_input("Durum Açıklaması (Örn: Ucu kırıktı öyle verdim)")
                
                if st.form_submit_button("🤝 Zimmetle", type="primary"):
                    if zimmet_kisi:
                        d_id = d_secenekler[sec_demirbas]
                        c.execute("INSERT INTO zimmetler (demirbas_id, zimmetlenen_kisi, verilis_tarihi, teslim_durumu, aciklama) VALUES (?,?,?,?,?)",
                                  (d_id, zimmet_kisi, str(verilis_tarih), teslim_durum, teslim_aciklama))
                        conn.commit()
                        st.success(f"Demirbaş {zimmet_kisi} adlı kişiye zimmetlendi.")
                        st.rerun()
                    else:
                        st.error("Lütfen kime verildiğini yazınız.")

            st.divider()
            
            # TESLİM ALINMAMIŞ (DIŞARIDAKİ) ZİMMETLER LİSTESİ
            st.markdown("##### 📥 Dışarıdaki (İade Bekleyen) Demirbaşlar")
            query = """
            SELECT z.id, d.adi, z.zimmetlenen_kisi, z.verilis_tarihi, z.teslim_durumu, z.aciklama 
            FROM zimmetler z 
            INNER JOIN demirbaslar d ON z.demirbas_id = d.id 
            WHERE z.geri_alma_tarihi IS NULL
            """
            df_z = pd.read_sql_query(query, conn)
            
            if not df_z.empty:
                gosterim_z = df_z.copy()
                gosterim_z.columns = ['Zimmet ID', 'Demirbaş Adı', 'Zimmetlenen Kişi', 'Veriliş Tarihi', 'Teslimdeki Durum', 'Açıklama']
                st.dataframe(gosterim_z.drop(columns=['Zimmet ID']), use_container_width=True, hide_index=True)
                
                # İade Alma İşlemi
                iade_secenekler = {f"{r['Demirbaş Adı']} (Sende: {r['Zimmetlenen Kişi']})": r['Zimmet ID'] for _, r in df_z.iterrows()}
                with st.container(border=True):
                    col_i1, col_i2 = st.columns([3, 1])
                    with col_i1:
                        sec_iade = st.selectbox("Geri Alınacak Demirbaşı Seçin", list(iade_secenekler.keys()))
                    with col_i2:
                        st.write("") # Hizalama boşluğu
                        if st.button("✅ Teslim Al", type="primary", use_container_width=True):
                            z_id = iade_secenekler[sec_iade]
                            bugun = str(datetime.date.today())
                            c.execute("UPDATE zimmetler SET geri_alma_tarihi=? WHERE id=?", (bugun, z_id))
                            conn.commit()
                            st.success("Demirbaş başarıyla geri alındı!")
                            st.rerun()
            else:
                st.success("Dışarıda bekleyen zimmetli demirbaş yok.")
                
        else:
            st.warning("Zimmetlenecek demirbaş bulunmuyor. Önce 'Demirbaş Kayıt' sekmesinden ekleme yapın.")

    conn.close()
