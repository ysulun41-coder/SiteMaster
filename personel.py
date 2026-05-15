import streamlit as st
import pandas as pd
import sqlite3
import datetime
from utils import render_header, get_conn

def goster(db_yolu):
    render_header("👥 Personel Yönetimi ve Puantaj Takibi")
    
    conn = get_conn(db_yolu)
    c = conn.cursor()
    
    # 1. TABLO ALTYAPILARI
    c.execute('''CREATE TABLE IF NOT EXISTS personeller (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad_soyad TEXT, tc TEXT, tel TEXT, gorev TEXT, 
        giris_tarihi TEXT, ucret_tipi TEXT, ucret REAL)''')
        
    c.execute('''CREATE TABLE IF NOT EXISTS puantaj (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personel_id INTEGER, tarih TEXT, durum TEXT, notlar TEXT)''')
        
    c.execute('''CREATE TABLE IF NOT EXISTS personel_odemeler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personel_id INTEGER, tarih TEXT, tutar REAL, tip TEXT, aciklama TEXT)''')
    conn.commit()

    p_tab1, p_tab2, p_tab3 = st.tabs(["👤 Personel Kayıt", "📝 Günlük Puantaj", "💰 Maaş & Avans Takibi"])

    # --- TAB 1: PERSONEL KAYIT ---
    with p_tab1:
        with st.form("personel_kayit_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                ad = st.text_input("Adı Soyadı")
                tc = st.text_input("TC Kimlik No", max_chars=11)
                tel = st.text_input("Telefon Numarası")
            with col2:
                gor = st.selectbox("Görevi", ["Apartman Görevlisi", "Güvenlik", "Temizlik", "Bahçıvan", "Teknik Personel"])
                u_tip = st.selectbox("Ücret Tipi", ["Aylık Sabit Maaş", "Günlük Yevmiye"])
                u_miktar = st.number_input("Anlaşılan Tutar (₺)", min_value=0.0)
            
            if st.form_submit_button("💾 Personeli Sisteme Kaydet", type="primary"):
                if ad and tc:
                    c.execute("INSERT INTO personeller (ad_soyad, tc, tel, gorev, giris_tarihi, ucret_tipi, ucret) VALUES (?,?,?,?,?,?,?)",
                              (ad, tc, tel, gor, str(datetime.date.today()), u_tip, u_miktar))
                    conn.commit()
                    st.success(f"{ad} personeli kaydedildi.")
                    st.rerun()

        st.divider()
        st.markdown("##### 📋 Kayıtlı Personel Listesi")
        df_p = pd.read_sql_query("SELECT id, ad_soyad as 'Ad Soyad', gorev as Görev, ucret_tipi as 'Ücret Tipi', ucret as 'Tutar' FROM personeller", conn)
        st.dataframe(df_p, use_container_width=True, hide_index=True)

    # --- TAB 2: PUANTAJ GİRİŞİ ---
    with p_tab2:
        c.execute("SELECT id, ad_soyad FROM personeller")
        p_list = c.fetchall()
        if p_list:
            p_secenek = {p[1]: p[0] for p in p_list}
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                sec_p = st.selectbox("Personel Seç", list(p_secenek.keys()), key="puantaj_p")
            with col_p2:
                p_tarih = st.date_input("Tarih", datetime.date.today())
            with col_p3:
                p_durum = st.selectbox("Çalışma Durumu", ["Geldi (Tam Gün)", "Gelmedi / İzinli", "Raporlu", "Mesai Yaptı (+50%)"])
            
            p_not = st.text_input("Ekstra Açıklama (Opsiyonel)")
            if st.button("📌 Puantajı İşle", use_container_width=True):
                c.execute("INSERT INTO puantaj (personel_id, tarih, durum, notlar) VALUES (?,?,?,?)",
                          (p_secenek[sec_p], str(p_tarih), p_durum, p_not))
                conn.commit()
                st.success("Puantaj kaydedildi.")
        else:
            st.info("Önce personel kaydı yapmalısınız.")

    # --- TAB 3: MAAŞ & AVANS (GAYRI RESMİ YÖNETİM İÇİN) ---
    with p_tab3:
        if p_list:
            col_o1, col_o2 = st.columns(2)
            with col_o1:
                sec_o = st.selectbox("Personel", list(p_secenek.keys()), key="odeme_p")
                o_tip = st.selectbox("İşlem Türü", ["Maaş Ödemesi", "Avans Ödemesi", "Prim / İkramiye"])
            with col_o2:
                o_tutar = st.number_input("Ödenen Tutar (₺)", min_value=0.0)
                o_tarih = st.date_input("Ödeme Tarihi", datetime.date.today())
            
            if st.button("💸 Ödemeyi Kaydet ve Kasadan Düş", type="primary", use_container_width=True):
                p_id = p_secenek[sec_o]
                # 1. Personel Defterine Yaz
                c.execute("INSERT INTO personel_odemeler (personel_id, tarih, tutar, tip, aciklama) VALUES (?,?,?,?,?)",
                          (p_id, str(o_tarih), o_tutar, o_tip, f"{sec_o} personeline yapılan {o_tip}"))
                
                # 2. ANA KASAYA (Giderler) OTOMATİK İŞLE
                c.execute("INSERT INTO giderler (tarih, kategori, tutar, aciklama, firma_kisi) VALUES (?,?,?,?,?)",
                          (str(o_tarih), "Maaş / Personel", o_tutar, o_tip, sec_o))
                
                conn.commit()
                st.success(f"{o_tutar} ₺ ödeme yapıldı ve site giderlerine işlendi.")

            st.divider()
            st.markdown(f"##### 📑 {sec_o} - Hesap Özeti")
            p_id_sec = p_secenek[sec_o]
            
            # 🔥 İŞTE HATAYI ÇÖZDÜĞÜMÜZ SATIR BURASI (notlar as Notlar yaptık)
            df_puan = pd.read_sql_query(f"SELECT tarih as Tarih, durum as Durum, notlar as Notlar FROM puantaj WHERE personel_id={p_id_sec} ORDER BY tarih DESC LIMIT 30", conn)
            
            # Ödeme Özeti
            df_odemeler = pd.read_sql_query(f"SELECT tarih as Tarih, tip as Tür, tutar as Tutar FROM personel_odemeler WHERE personel_id={p_id_sec} ORDER BY tarih DESC", conn)
            
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Son Çalışma Kayıtları**")
                st.dataframe(df_puan, use_container_width=True, hide_index=True)
            with c2:
                st.write("**Ödeme Geçmişi**")
                st.dataframe(df_odemeler, use_container_width=True, hide_index=True)
        else:
            st.info("Kayıtlı personel yok.")

    conn.close()

