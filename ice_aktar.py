import streamlit as st
import pandas as pd
import sqlite3
import io

def goster(db_yolu):
    st.subheader("📥 Veri Transfer Merkezi (Excel'den Sakin Aktar)")
    st.info("💡 Başka bir sistemden geçiş yapıyorsanız, aşağıdaki şablonu kullanarak yüzlerce daireyi saniyeler içinde içeri aktarabilirsiniz.")

    # 1. ŞABLON İNDİRME ALANI
    st.markdown("##### 📝 1. Adım: Şablonu İndirin ve Doldurun")
    # Örnek bir Excel şablonu oluşturuyoruz
    sablon_verisi = {
        'Blok': ['A', 'A', 'B'],
        'Daire_No': ['1', '2', '1'],
        'Malik_Ad': ['Ahmet Yılmaz', 'Mehmet Demir', 'Ayşe Kaya'],
        'Malik_TC': ['11111111111', '', ''],
        'Malik_Tel': ['05001112233', '', ''],
        'Kiraci_Ad': ['', '', 'Hüseyin Can'],
        'Kiraci_Tel': ['', '', '05004445566'],
        'Plaka': ['41 ABC 041', '', ''],
        'Sifre': ['1234', '1234', '1234']
    }
    df_sablon = pd.DataFrame(sablon_verisi)
    
    # Excel dosyasını bellekte oluşturma
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_sablon.to_excel(writer, index=False, sheet_name='Sakin_Listesi')
    
    st.download_button(
        label="📥 Boş Excel Şablonunu İndir",
        data=buffer.getvalue(),
        file_name="SiteMaster_Sakin_Yukleme_Sablonu.xlsx",
        mime="application/vnd.ms-excel",
        use_container_width=True
    )

    st.divider()

    # 2. DOSYA YÜKLEME ALANI
    st.markdown("##### 📤 2. Adım: Doldurduğunuz Dosyayı Yükleyin")
    yuklenen_dosya = st.file_uploader("Excel dosyasını seçin", type=['xlsx'])

    if yuklenen_dosya:
        try:
            df_yuklenen = pd.read_excel(yuklenen_dosya)
            
            # Verileri kontrol et ve önizleme göster
            st.write("**Yüklenen Verilerin Önizlemesi:**")
            st.dataframe(df_yuklenen.head(), use_container_width=True)
            
            if st.button("🔥 Verileri Sisteme Aktar", type="primary", use_container_width=True):
                conn = sqlite3.connect(db_yolu)
                c = conn.cursor()
                
                eklenen = 0
                hata = 0
                
                for _, satir in df_yuklenen.iterrows():
                    try:
                        # Veritabanına toplu insert
                        c.execute("""INSERT INTO sakinler 
                                     (blok, daire_no, malik_ad, malik_tc, malik_tel, kiraci_ad, kiraci_tel, plaka, sifre) 
                                     VALUES (?,?,?,?,?,?,?,?,?)""", 
                                  (str(satir['Blok']), str(satir['Daire_No']), str(satir['Malik_Ad']), 
                                   str(satir['Malik_TC']), str(satir['Malik_Tel']), str(satir['Kiraci_Ad']), 
                                   str(satir['Kiraci_Tel']), str(satir['Plaka']), str(satir['Sifre'])))
                        eklenen += 1
                    except Exception as e:
                        hata += 1
                
                conn.commit()
                conn.close()
                st.success(f"✅ İşlem Tamamlandı! {eklenen} daire sisteme eklendi. {hata} hata oluştu.")
                if eklenen > 0:
                    st.balloons()
                    
        except Exception as e:
            st.error(f"Dosya işlenirken hata oluştu: {e}")
