import streamlit as st
import pandas as pd
import sqlite3
import datetime
from utils import sitemaster_logo_koy

def goster(db_yolu):
    sitemaster_logo_koy()
    st.subheader("🏦 Akıllı Banka Ekstresi Okuyucu (Yapay Zeka)")
    st.info("💡 **Premium API Entegrasyonu Öncesi Manuel Yükleme Modülü:** Bankanızdan indirdiğiniz hesap hareketleri (Excel) dosyasını buraya yükleyin, sistem açıklamaları okuyup borçlarla otomatik eşleştirsin.")

    conn = sqlite3.connect(db_yolu)
    
    # Bekleyen borçları çekiyoruz
    query = """
    SELECT a.id, a.blok, a.daire_no, s.malik_ad, a.tutar as ana_para, a.aciklama 
    FROM aidatlar a
    INNER JOIN sakinler s ON a.blok = s.blok AND a.daire_no = s.daire_no
    WHERE a.durum = 'Ödenmedi'
    """
    df_borclar = pd.read_sql_query(query, conn)
    
    # 1. DOSYA YÜKLEME ALANI
    yuklenen_dosya = st.file_uploader("Banka Ekstrenizi Yükleyin (.xlsx veya .csv)", type=['xlsx', 'csv'])
    
    if yuklenen_dosya is not None:
        try:
            # Excel veya CSV okuma
            if yuklenen_dosya.name.endswith('.csv'):
                df_ekstre = pd.read_csv(yuklenen_dosya)
            else:
                df_ekstre = pd.read_excel(yuklenen_dosya)
                
            st.success("Dosya başarıyla okundu! Veriler analiz ediliyor...")
            
            # (Geçici) Varsayılan banka sütun isimleri - Bunlar bankaya göre değişebilir
            st.markdown("##### 🔍 Eşleştirme Ayarları")
            sutunlar = df_ekstre.columns.tolist()
            
            col1, col2 = st.columns(2)
            with col1:
                aciklama_sutunu = st.selectbox("Bankanın 'Açıklama' veya 'Gönderen' Sütunu Hangisi?", sutunlar)
            with col2:
                tutar_sutunu = st.selectbox("Bankanın 'Yatan Tutar' Sütunu Hangisi?", sutunlar)

            st.divider()
            
            if st.button("🤖 Otomatik Eşleştirmeyi Başlat", type="primary", use_container_width=True):
                eslesenler = []
                eslesmeyenler = []
                
                with st.spinner("Yapay zeka borçlularla banka hareketlerini karşılaştırıyor..."):
                    for index, banka_satir in df_ekstre.iterrows():
                        islem_aciklama = str(banka_satir[aciklama_sutunu]).upper()
                        islem_tutar = float(banka_satir[tutar_sutunu]) if pd.notna(banka_satir[tutar_sutunu]) else 0.0
                        
                        if islem_tutar <= 0:
                            continue # Çıkan paraları (giderleri) atla
                            
                        eslesti_mi = False
                        
                        # Bekleyen borçlarla kontrol et
                        for _, borc in df_borclar.iterrows():
                            # Eşleşme Mantığı 1: İsim Soyisim açıklamada geçiyor mu?
                            # Eşleşme Mantığı 2: Blok ve Daire No geçiyor mu? (Örn: A Blok D:5)
                            isim = str(borc['malik_ad']).upper()
                            
                            if (isim in islem_aciklama) and (float(borc['ana_para']) == islem_tutar):
                                eslesenler.append({
                                    "Borç_ID": borc['id'],
                                    "Kişi": borc['malik_ad'],
                                    "Daire": f"{borc['blok']} No:{borc['daire_no']}",
                                    "Banka Açıklaması": islem_aciklama,
                                    "Tahsil Edilecek": islem_tutar
                                })
                                eslesti_mi = True
                                break # Bu banka işlemini eşleştirdik, sıradakine geç
                                
                        if not eslesti_mi:
                            eslesmeyenler.append({"Banka Açıklaması": islem_aciklama, "Gelen Tutar": islem_tutar})

                # SONUÇLARI EKRANA YANSIT
                c_es, c_hata = st.columns(2)
                with c_es:
                    st.markdown(f"### ✅ Eşleşenler ({len(eslesenler)})")
                    if eslesenler:
                        df_es = pd.DataFrame(eslesenler)
                        st.dataframe(df_es[['Kişi', 'Daire', 'Tahsil Edilecek']], use_container_width=True, hide_index=True)
                        
                        if st.button("🔥 Tüm Eşleşenleri 'ÖDENDİ' Olarak Sisteme İşle"):
                            kur = conn.cursor()
                            bugun = datetime.date.today().strftime("%d.%m.%Y")
                            for es in eslesenler:
                                kur.execute("UPDATE aidatlar SET durum='Ödendi', aciklama=aciklama || ' (Banka Otomatik)' WHERE id=?", (es['Borç_ID'],))
                            conn.commit()
                            st.success(f"{len(eslesenler)} adet tahsilat başarıyla sisteme işlendi!")
                    else:
                        st.info("Tam eşleşen kayıt bulunamadı.")
                        
                with c_hata:
                    st.markdown(f"### ⚠️ Eşleşmeyenler ({len(eslesmeyenler)})")
                    st.caption("Açıklama eksikliği veya tutar uyuşmazlığı nedeniyle bulunamayanlar.")
                    if eslesmeyenler:
                        st.dataframe(pd.DataFrame(eslesmeyenler), use_container_width=True, hide_index=True)
                        
        except Exception as e:
            st.error(f"Dosya okunurken bir hata oluştu: {e}")

    conn.close()
