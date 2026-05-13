import streamlit as st
import pandas as pd
import sqlite3
import io

def goster(db_yolu):
    st.subheader("📥 Akıllı Veri Transfer Merkezi (Excel'den İçe Aktar)")
    st.info("💡 Eski sisteminizden aldığınız Excel'i yükleyin. Sütun isimleri ne olursa olsun, sistemimizdeki alanlarla eşleştirerek saniyeler içinde aktarımı tamamlayabilirsiniz.")

    # 1. DOSYA YÜKLEME ALANI
    st.markdown("##### 📤 1. Adım: Excel Dosyanızı Yükleyin")
    yuklenen_dosya = st.file_uploader("Herhangi bir Excel dosyasını seçin (.xlsx)", type=['xlsx'])

    if yuklenen_dosya:
        try:
            df_yuklenen = pd.read_excel(yuklenen_dosya)
            
            # Excel'deki boş hücreleri (NaN) boş string ile değiştir (Hata vermemesi için)
            df_yuklenen.fillna("", inplace=True)
            
            st.success("✅ Dosya başarıyla okundu! Lütfen aşağıdaki eşleştirmeleri yapın.")
            st.write("**Yüklenen Dosyadan Örnek 3 Satır:**")
            st.dataframe(df_yuklenen.head(3), use_container_width=True)
            
            st.divider()
            
            # 2. SÜTUN EŞLEŞTİRME ALANI (MAPPING)
            st.markdown("##### 🔄 2. Adım: Sütun Eşleştirme")
            st.caption("Bizim sistemimizin ihtiyaç duyduğu bilgilerle, sizin Excel'inizdeki başlıkları eşleştirin. Excel'inizde o bilgi yoksa '-- SÜTUN YOK / BOŞ BIRAK --' seçeneğini seçebilirsiniz.")
            
            # Excel'den gelen sütun isimleri + Bir tane "Yok" seçeneği
            sutun_secenekleri = ["-- SÜTUN YOK / BOŞ BIRAK --"] + df_yuklenen.columns.tolist()
            
            # Kullanıcıya yan yana şık bir formda eşleştirme yaptıralım
            with st.form("eslestirme_formu"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**🏡 Temel Bilgiler**")
                    sec_blok = st.selectbox("Blok / Apartman Adı Sütunu", sutun_secenekleri)
                    sec_daire = st.selectbox("Daire / Kapı No Sütunu", sutun_secenekleri)
                    sec_sifre = st.selectbox("Sakin Giriş Şifresi Sütunu", sutun_secenekleri, help="Eğer Excel'de şifre yoksa boş bırakın. Sistem otomatik '1234' şifresi atayacaktır.")
                    
                    st.markdown("**🚗 Ekstra Bilgiler**")
                    sec_plaka = st.selectbox("Araç Plakası Sütunu", sutun_secenekleri)

                with col2:
                    st.markdown("**👤 Kat Maliki Bilgileri**")
                    sec_m_ad = st.selectbox("Malik (Ev Sahibi) Adı Sütunu", sutun_secenekleri)
                    sec_m_tc = st.selectbox("Malik TC No Sütunu", sutun_secenekleri)
                    sec_m_tel = st.selectbox("Malik Telefon Sütunu", sutun_secenekleri)
                    
                    st.markdown("**🧑‍💼 Kiracı Bilgileri**")
                    sec_k_ad = st.selectbox("Kiracı Adı Sütunu", sutun_secenekleri)
                    sec_k_tel = st.selectbox("Kiracı Telefon Sütunu", sutun_secenekleri)

                submit_btn = st.form_submit_button("🔥 Eşleştirmeyi Onayla ve Aktar", type="primary")

            # 3. VERİTABANINA YAZMA İŞLEMİ
            if submit_btn:
                # Blok ve Daire No en kritik bilgiler, onlar olmadan kayıt yapamayız
                if sec_blok == "-- SÜTUN YOK / BOŞ BIRAK --" or sec_daire == "-- SÜTUN YOK / BOŞ BIRAK --":
                    st.error("❌ Hata: 'Blok' ve 'Daire No' sütunlarını eşleştirmek ZORUNLUDUR! Bu bilgiler olmadan kayıt yapılamaz.")
                else:
                    conn = sqlite3.connect(db_yolu)
                    c = conn.cursor()
                    
                    eklenen = 0
                    hata = 0
                    
                    with st.spinner("Sakinler sisteme aktarılıyor..."):
                        for index, satir in df_yuklenen.iterrows():
                            try:
                                # Kullanıcının seçtiği sütun isimlerine göre Excel'den veriyi çek
                                # Eğer adam "Sütun Yok" seçtiyse o bilgiyi boş (veya varsayılan) atıyoruz
                                
                                val_blok = str(satir[sec_blok]) if sec_blok != "-- SÜTUN YOK / BOŞ BIRAK --" else ""
                                val_daire = str(satir[sec_daire]) if sec_daire != "-- SÜTUN YOK / BOŞ BIRAK --" else ""
                                
                                # Eğer blok veya daire no hücresi boşsa o satırı atla
                                if not val_blok.strip() or not val_daire.strip():
                                    continue

                                val_m_ad = str(satir[sec_m_ad]) if sec_m_ad != "-- SÜTUN YOK / BOŞ BIRAK --" else ""
                                val_m_tc = str(satir[sec_m_tc]) if sec_m_tc != "-- SÜTUN YOK / BOŞ BIRAK --" else ""
                                val_m_tel = str(satir[sec_m_tel]) if sec_m_tel != "-- SÜTUN YOK / BOŞ BIRAK --" else ""
                                
                                val_k_ad = str(satir[sec_k_ad]) if sec_k_ad != "-- SÜTUN YOK / BOŞ BIRAK --" else ""
                                val_k_tel = str(satir[sec_k_tel]) if sec_k_tel != "-- SÜTUN YOK / BOŞ BIRAK --" else ""
                                
                                val_plaka = str(satir[sec_plaka]) if sec_plaka != "-- SÜTUN YOK / BOŞ BIRAK --" else ""
                                
                                # Şifre özel durum: Eğer Excel'de yoksa herkese standart "1234" ata
                                val_sifre = str(satir[sec_sifre]) if sec_sifre != "-- SÜTUN YOK / BOŞ BIRAK --" else "1234"
                                if not val_sifre.strip(): val_sifre = "1234" # Hücre boşsa da 1234 yap

                                # Temizlenen verileri veritabanına bas
                                c.execute("""INSERT INTO sakinler 
                                             (blok, daire_no, malik_ad, malik_tc, malik_tel, kiraci_ad, kiraci_tel, plaka, sifre) 
                                             VALUES (?,?,?,?,?,?,?,?,?)""", 
                                          (val_blok, val_daire, val_m_ad, val_m_tc, val_m_tel, val_k_ad, val_k_tel, val_plaka, val_sifre))
                                eklenen += 1
                            except Exception as e:
                                hata += 1
                    
                    conn.commit()
                    conn.close()
                    
                    st.success(f"🎉 Aktarım Başarılı! Sisteme {eklenen} adet daire eklendi. (Hatalı/Atlanan Satır: {hata})")
                    if eklenen > 0:
                        st.balloons()
                        
        except Exception as e:
            st.error(f"Dosya okunurken sistemsel bir hata oluştu: {e}")
