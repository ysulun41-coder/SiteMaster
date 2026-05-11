import streamlit as st
import sqlite3
import datetime

def goster(db_yolu):
    st.subheader("Aidat ve Borç Tahakkuku")
    
    # KANKAM BURASI SİHİRLİ: Eski veritabanına yeni sütunları hata vermeden ekler
    conn = sqlite3.connect(db_yolu)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE aidatlar ADD COLUMN son_odeme_tarihi TEXT")
        c.execute("ALTER TABLE aidatlar ADD COLUMN faiz_orani REAL")
        conn.commit()
    except:
        pass # Zaten varsa hata vermeden geçer
        
    c.execute("SELECT blok, daire_no, malik_ad FROM sakinler")
    s_list = c.fetchall()
    conn.close()
    
    sec = ["🌟 Toplu Borçlandırma"] + [f"{s[0]} Blok - No:{s[1]} ({s[2]})" for s in s_list]
    
    with st.form("borc_form", clear_on_submit=True):
        h = st.selectbox("Daire Seçiniz", sec)
        tut = st.number_input("Tutar (₺)", min_value=0.0)
        acik = st.text_input("Açıklama (Örn: Haziran Aidatı)")
        
        st.markdown("##### 📅 Tarih ve Faiz Ayarları")
        col1, col2, col3 = st.columns(3)
        with col1:
            islem_tarihi = st.date_input("Tahakkuk (Kesim) Tarihi", datetime.date.today())
        with col2:
            # Varsayılan olarak 7 gün mühlet verelim
            son_odeme = st.date_input("Son Ödeme Tarihi", datetime.date.today() + datetime.timedelta(days=7))
        with col3:
            # Günlük faiz oranı. Örn: %0.1 (Binde bir)
            faiz = st.number_input("Günlük Faiz Oranı (%)", min_value=0.0, value=0.1, step=0.01, format="%.2f", help="Gecikme yaşanırsa günlük eklenecek % oran.")
        
        if st.form_submit_button("💸 Borçlandır ve Sisteme İşle", type="primary"):
            conn = sqlite3.connect(db_yolu)
            c = conn.cursor()
            
            if h == "🌟 Toplu Borçlandırma":
                for s in s_list: 
                    c.execute("INSERT INTO aidatlar (blok, daire_no, tarih, tutar, aciklama, son_odeme_tarihi, faiz_orani) VALUES (?,?,?,?,?,?,?)", 
                              (s[0], s[1], str(islem_tarihi), tut, acik, str(son_odeme), faiz))
            else:
                idx = sec.index(h) - 1
                s = s_list[idx]
                c.execute("INSERT INTO aidatlar (blok, daire_no, tarih, tutar, aciklama, son_odeme_tarihi, faiz_orani) VALUES (?,?,?,?,?,?,?)", 
                          (s[0], s[1], str(islem_tarihi), tut, acik, str(son_odeme), faiz))
                
            conn.commit()
            conn.close()
            st.success("Borçlar; Son Ödeme Tarihi ve Faiz Oranlarıyla birlikte sisteme başarıyla yansıtıldı!")
