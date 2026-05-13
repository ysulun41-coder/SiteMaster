import streamlit as st
import sqlite3
import datetime

def goster(db_yolu):
    st.subheader("💰 Otomatik Aidat ve Tahakkuk Merkezi")
    
    # Veritabanını sağlama alalım (Eski sistemden geçenler için)
    conn = sqlite3.connect(db_yolu)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE aidatlar ADD COLUMN son_odeme_tarihi TEXT")
        c.execute("ALTER TABLE aidatlar ADD COLUMN faiz_uygula INTEGER DEFAULT 0")
        c.execute("ALTER TABLE aidatlar ADD COLUMN yillik_faiz REAL DEFAULT 0.0")
        conn.commit()
    except: pass
        
    c.execute("SELECT blok, daire_no, malik_ad FROM sakinler")
    s_list = c.fetchall()
    conn.close()

    if not s_list:
        st.warning("Sistemde kayıtlı sakin bulunmuyor. Önce 'Sakin Ekle' bölümünden kayıt yapmalısınız.")
        return

    # İşleri iki sekmeye ayırdık: Aylık Rutin işler ve Tekil istisnai durumlar
    tab1, tab2 = st.tabs(["🔄 Aylık Otomatik Toplu Aidat", "🎯 Tekil / Ekstra Borçlandırma"])

    # --- TAB 1: TOPLU BORÇLANDIRMA VE YÖNETİCİ MUAFİYETİ ---
    with tab1:
        st.info("Her ay tek tuşla tüm siteyi borçlandırın. Yönetici gibi aidat ödemeyecek daireleri listeden çıkarabilirsiniz.")
        
        with st.form("toplu_borc_form", clear_on_submit=False):
            col1, col2 = st.columns(2)
            
            # Ay adını otomatik bulup açıklamayı kendisi yazsın (Örn: Mayıs 2026 Aidatı)
            aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
            su_an = datetime.datetime.now()
            varsayilan_aciklama = f"{aylar[su_an.month-1]} {su_an.year} Aidatı"

            with col1:
                tut = st.number_input("Her Daire İçin Aidat Tutarı (₺)", min_value=0.0, step=50.0)
                acik = st.text_input("Açıklama", value=varsayilan_aciklama)
            
            with col2:
                # Muafiyet listesi (Yönetici vs. buradan seçilip harici tutulacak)
                tum_daireler = [f"{s[0]} Blok - No:{s[1]} ({s[2]})" for s in s_list]
                muaf_daireler = st.multiselect("Muaf Tutulacak Daireler (Örn: Yönetici Dairesi)", tum_daireler, help="Buradan seçeceğiniz dairelere bu aidat borcu YAZILMAYACAKTIR.")

            st.markdown("##### 📅 Tarih ve Otomatik Faiz Ayarları")
            c1, c2, c3 = st.columns(3)
            with c1:
                islem_tarihi = st.date_input("Tahakkuk (İşlem) Tarihi", datetime.date.today(), key="t_islem")
            with c2:
                son_odeme = st.date_input("Son Ödeme Tarihi", datetime.date.today() + datetime.timedelta(days=7), key="t_son")
            with c3:
                faiz_islesin = st.checkbox("Gecikmede Faiz İşlesin", value=True, key="t_faiz_check")
                if faiz_islesin:
                    yillik_faiz = st.number_input("Yıllık Faiz Oranı (%)", min_value=0.0, value=60.0, step=1.0)
                else:
                    yillik_faiz = 0.0

            if st.form_submit_button("🚀 Tüm Siteyi Borçlandır (Muaflar Hariç)", type="primary"):
                if tut > 0 and acik:
                    conn = sqlite3.connect(db_yolu)
                    c = conn.cursor()
                    faiz_durumu = 1 if faiz_islesin else 0
                    islem_sayisi = 0

                    for s in s_list:
                        daire_etiketi = f"{s[0]} Blok - No:{s[1]} ({s[2]})"
                        # 🔥 SİHİR BURADA: Eğer daire muaf listesinde YOKSA borç yazıyoruz
                        if daire_etiketi not in muaf_daireler:
                            c.execute("""INSERT INTO aidatlar 
                                         (blok, daire_no, tarih, tutar, aciklama, son_odeme_tarihi, faiz_uygula, yillik_faiz) 
                                         VALUES (?,?,?,?,?,?,?,?)""", 
                                      (s[0], s[1], str(islem_tarihi), tut, acik, str(son_odeme), faiz_durumu, yillik_faiz))
                            islem_sayisi += 1
                    
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 İşlem Başarılı! {len(muaf_daireler)} daire muaf tutuldu, toplam {islem_sayisi} daireye otomatik borç yansıtıldı.")
                else:
                    st.error("Lütfen tutar ve açıklama kısmını boş bırakmayın.")

    # --- TAB 2: TEKİL BORÇLANDIRMA (EKSTRA DURUMLAR İÇİN) ---
    with tab2:
        st.info("Sadece belirli bir daireye özel borç (Örn: Demirbaş katılımı, asansör hasar bedeli) eklemek için bu alanı kullanın.")
        with st.form("tekil_borc_form", clear_on_submit=True):
            sec = [f"{s[0]} Blok - No:{s[1]} ({s[2]})" for s in s_list]
            h = st.selectbox("Daire Seçiniz", sec)
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                tut_tekil = st.number_input("Tutar (₺)", min_value=0.0, key="tek_tut")
                acik_tekil = st.text_input("Açıklama (Örn: Cam kırılma bedeli)", key="tek_acik")
            with col_t2:
                islem_tarihi_tekil = st.date_input("İşlem Tarihi", datetime.date.today(), key="tek_islem")
                son_odeme_tekil = st.date_input("Son Ödeme", datetime.date.today() + datetime.timedelta(days=7), key="tek_son")
            
            faiz_islesin_tekil = st.checkbox("Gecikme Durumunda Faiz İşletilsin", value=True, key="tek_faiz")
            if faiz_islesin_tekil:
                yillik_faiz_tekil = st.number_input("Yıllık Faiz Oranı (%)", min_value=0.0, value=60.0, step=1.0, key="tek_oran")
            else:
                yillik_faiz_tekil = 0.0

            if st.form_submit_button("💸 Seçili Daireyi Borçlandır", type="primary"):
                if tut_tekil > 0 and acik_tekil:
                    idx = sec.index(h)
                    s = s_list[idx]
                    conn = sqlite3.connect(db_yolu)
                    c = conn.cursor()
                    faiz_durumu_tekil = 1 if faiz_islesin_tekil else 0
                    
                    c.execute("""INSERT INTO aidatlar 
                                 (blok, daire_no, tarih, tutar, aciklama, son_odeme_tarihi, faiz_uygula, yillik_faiz) 
                                 VALUES (?,?,?,?,?,?,?,?)""", 
                              (s[0], s[1], str(islem_tarihi_tekil), tut_tekil, acik_tekil, str(son_odeme_tekil), faiz_durumu_tekil, yillik_faiz_tekil))
                    conn.commit()
                    conn.close()
                    st.success(f"{h} için borçlandırma başarıyla yapıldı!")
                else:
                    st.error("Lütfen tutar ve açıklama giriniz.")
