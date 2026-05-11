import streamlit as st
import sqlite3
import datetime

def goster(db_yolu):
    st.subheader("Aidat ve Borç Tahakkuku")
    
    # Yeni faiz sütunlarını veritabanına ekliyoruz (Hata vermez, varsa geçer)
    conn = sqlite3.connect(db_yolu)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE aidatlar ADD COLUMN son_odeme_tarihi TEXT")
        c.execute("ALTER TABLE aidatlar ADD COLUMN faiz_uygula INTEGER DEFAULT 0")
        c.execute("ALTER TABLE aidatlar ADD COLUMN yillik_faiz REAL DEFAULT 0.0")
        conn.commit()
    except:
        pass
        
    c.execute("SELECT blok, daire_no, malik_ad FROM sakinler")
    s_list = c.fetchall()
    conn.close()
    
    sec = ["🌟 Toplu Borçlandırma"] + [f"{s[0]} Blok - No:{s[1]} ({s[2]})" for s in s_list]
    
    with st.form("borc_form", clear_on_submit=True):
        h = st.selectbox("Daire Seçiniz", sec)
        acik = st.text_input("Ödeme Türü / Açıklama (Örn: Haziran Aidatı, Demirbaş)")
        tut = st.number_input("Ana Para Tutarı (₺)", min_value=0.0)
        
        st.markdown("##### 📅 Tarih ve Otomatik Faiz Ayarları")
        col1, col2 = st.columns(2)
        with col1:
            islem_tarihi = st.date_input("Tahakkuk (İşlem) Tarihi", datetime.date.today())
            son_odeme = st.date_input("Son Ödeme Tarihi", datetime.date.today() + datetime.timedelta(days=7))
        with col2:
            st.write("Faiz Uygulaması")
            faiz_islesin = st.checkbox("Gecikme Durumunda Faiz İşletilsin", value=True)
            if faiz_islesin:
                # Yıllık faiz oranını manuel giriyoruz
                yillik_faiz = st.number_input("Yıllık Faiz Oranı (%)", min_value=0.0, value=60.0, step=1.0, help="Sistem bu oranı 365'e bölerek günlük faiz ekleyecektir.")
            else:
                yillik_faiz = 0.0
        
        if st.form_submit_button("💸 Borçlandır ve Sisteme İşle", type="primary"):
            if acik and tut > 0:
                conn = sqlite3.connect(db_yolu)
                c = conn.cursor()
                
                faiz_durumu = 1 if faiz_islesin else 0
                
                if h == "🌟 Toplu Borçlandırma":
                    for s in s_list: 
                        c.execute("""INSERT INTO aidatlar 
                                     (blok, daire_no, tarih, tutar, aciklama, son_odeme_tarihi, faiz_uygula, yillik_faiz) 
                                     VALUES (?,?,?,?,?,?,?,?)""", 
                                  (s[0], s[1], str(islem_tarihi), tut, acik, str(son_odeme), faiz_durumu, yillik_faiz))
                else:
                    idx = sec.index(h) - 1
                    s = s_list[idx]
                    c.execute("""INSERT INTO aidatlar 
                                 (blok, daire_no, tarih, tutar, aciklama, son_odeme_tarihi, faiz_uygula, yillik_faiz) 
                                 VALUES (?,?,?,?,?,?,?,?)""", 
                              (s[0], s[1], str(islem_tarihi), tut, acik, str(son_odeme), faiz_durumu, yillik_faiz))
                    
                conn.commit()
                conn.close()
                st.success("Borçlar başarıyla sisteme işlendi!")
            else:
                st.error("Lütfen ödeme türünü ve tutarı eksiksiz giriniz.")
