import streamlit as st
import pandas as pd
import sqlite3
import datetime
from utils import sitemaster_logo_koy

def goster(db_yolu):
    sitemaster_logo_koy()
    st.subheader("📦 Demirbaş ve Zimmet Yönetimi")
    
    conn = sqlite3.connect(db_yolu)
    c = conn.cursor()
    
    # 1. VERİTABANI ALTYAPISI (Yeni alanlarla birlikte)
    c.execute('''CREATE TABLE IF NOT EXISTS demirbaslar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        adi TEXT, alim_tarihi TEXT, satici TEXT, garanti_suresi TEXT, durum TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS zimmetler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        demirbas_id INTEGER,
        zimmetlenen_kisi TEXT,
        verilis_tarihi TEXT,
        teslim_durumu TEXT,
        aciklama TEXT,
        geri_alma_tarihi TEXT,
        iade_durumu TEXT,
        iade_notu TEXT)''')
    
    # Eskiden kalan veritabanı varsa yeni sütunları ekleyelim
    try:
        c.execute("ALTER TABLE zimmetler ADD COLUMN iade_durumu TEXT")
        c.execute("ALTER TABLE zimmetler ADD COLUMN iade_notu TEXT")
        conn.commit()
    except: pass

    d_tab1, d_tab2, d_tab3 = st.tabs(["🛠️ Envanter", "🤝 Zimmetle / İade Al", "📜 Hareket Geçmişi"])

    # --- TAB 1: ENVANTER KAYIT ---
    with d_tab1:
        with st.form("demirbas_kayit_form", clear_on_submit=True):
            st.markdown("##### ➕ Yeni Demirbaş Ekle")
            col1, col2 = st.columns(2)
            with col1:
                d_adi = st.text_input("Demirbaş Adı")
                d_satici = st.text_input("Nereden Alındı?")
                d_alim = st.date_input("Alınma Tarihi", datetime.date.today())
            with col2:
                d_garanti = st.text_input("Garanti Süresi")
                d_durum = st.selectbox("Mevcut Durumu", ["Sağlam", "Arızalı", "Bakımda", "Atıl", "Kayıp"])
            
            if st.form_submit_button("💾 Kaydet", type="primary"):
                if d_adi:
                    c.execute("INSERT INTO demirbaslar (adi, alim_tarihi, satici, garanti_suresi, durum) VALUES (?,?,?,?,?)",
                              (d_adi, str(d_alim), d_satici, d_garanti, d_durum))
                    conn.commit(); st.success(f"{d_adi} kaydedildi."); st.rerun()

        st.divider()
        df_d = pd.read_sql_query("SELECT id as ID, adi as 'Ad', alim_tarihi as 'Alım', durum as 'Durum' FROM demirbaslar", conn)
        st.dataframe(df_d, use_container_width=True, hide_index=True)

    # --- TAB 2: ZİMMETLE VE İADE AL ---
    with d_tab2:
        c.execute("SELECT id, adi, durum FROM demirbaslar WHERE durum IN ('Sağlam', 'Bakımda')")
        d_list = c.fetchall()
        
        col_z_sol, col_z_sag = st.columns(2)
        
        with col_z_sol:
            st.markdown("##### 📤 Zimmet Ver")
            if d_list:
                d_secenekler = {f"ID:{d[0]} - {d[1]}": d[0] for d in d_list}
                with st.form("zimmet_ver_form", clear_on_submit=True):
                    sec_demirbas = st.selectbox("Verilecek Demirbaş", list(d_secenekler.keys()))
                    zimmet_kisi = st.text_input("Kime Verildi?")
                    v_durum = st.selectbox("Verilirken Durumu", ["Sağlam", "Hafif Kusurlu"])
                    v_not = st.text_input("Veriş Notu")
                    v_tarih = st.date_input("Veriliş Tarihi", datetime.date.today())
                    if st.form_submit_button("🤝 Zimmetle", type="primary", use_container_width=True):
                        c.execute("INSERT INTO zimmetler (demirbas_id, zimmetlenen_kisi, verilis_tarihi, teslim_durumu, aciklama) VALUES (?,?,?,?,?)",
                                  (d_secenekler[sec_demirbas], zimmet_kisi, str(v_tarih), v_durum, v_not))
                        conn.commit(); st.success("Zimmetlendi!"); st.rerun()
            else: st.info("Zimmetlenecek uygun mal yok.")

        with col_z_sag:
            st.markdown("##### 📥 İade Al")
            query_iade = """SELECT z.id, d.adi, z.zimmetlenen_kisi, z.verilis_tarihi, z.teslim_durumu 
                            FROM zimmetler z INNER JOIN demirbaslar d ON z.demirbas_id = d.id 
                            WHERE z.geri_alma_tarihi IS NULL"""
            df_iade = pd.read_sql_query(query_iade, conn)
            
            if not df_iade.empty:
                iade_sec = {f"{r['adi']} ({r['zimmetlenen_kisi']})": r['id'] for _, r in df_iade.iterrows()}
                with st.form("iade_al_form", clear_on_submit=True):
                    sec_z_id = st.selectbox("İade Alınacak Kayıt", list(iade_sec.keys()))
                    i_durum = st.selectbox("İade Anındaki Durumu", ["Sağlam", "Arızalı", "Bakım Gerekiyor", "Eksik Parçalı"])
                    i_not = st.text_input("İade Notu (Örn: Çantası eksik)")
                    i_tarih = st.date_input("İade Tarihi", datetime.date.today())
                    if st.form_submit_button("✅ Teslim Al", use_container_width=True):
                        c.execute("UPDATE zimmetler SET geri_alma_tarihi=?, iade_durumu=?, iade_notu=? WHERE id=?",
                                  (str(i_tarih), i_durum, i_not, iade_sec[sec_z_id]))
                        # Demirbaşın genel durumunu da güncelleyelim
                        c.execute("UPDATE demirbaslar SET durum=? WHERE id=(SELECT demirbas_id FROM zimmetler WHERE id=?)", (i_durum, iade_sec[sec_z_id]))
                        conn.commit(); st.success("İade alındı ve sistem güncellendi!"); st.rerun()
            else: st.info("Dışarıda zimmetli ürün yok.")

    # --- TAB 3: HAREKET GEÇMİŞİ (DENETİM EKRANI) ---
    with d_tab3:
        st.markdown("##### 📜 Demirbaş Kullanım Geçmişi")
        c.execute("SELECT id, adi FROM demirbaslar")
        tum_d = c.fetchall()
        if tum_d:
            d_hist_sec = {f"{d[1]} (ID:{d[0]})": d[0] for d in tum_d}
            sec_h = st.selectbox("Hareketlerini Görmek İstediğiniz Ürünü Seçin", list(d_hist_sec.keys()))
            
            query_hist = f"""
            SELECT zimmetlenen_kisi as 'Kullanan', verilis_tarihi as 'Alış Tarihi', 
            teslim_durumu as 'Alış Durumu', geri_alma_tarihi as 'İade Tarihi', 
            iade_durumu as 'İade Durumu', iade_notu as 'Notlar'
            FROM zimmetler WHERE demirbas_id = {d_hist_sec[sec_h]} ORDER BY id DESC
            """
            df_hist = pd.read_sql_query(query_hist, conn)
            if not df_hist.empty:
                st.dataframe(df_hist, use_container_width=True, hide_index=True)
            else: st.info("Bu ürüne ait henüz bir geçmiş hareket yok.")
        else: st.info("Kayıtlı demirbaş yok.")

    conn.close()
