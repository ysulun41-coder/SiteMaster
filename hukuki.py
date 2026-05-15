import streamlit as st
import pandas as pd
import sqlite3
import datetime
from utils import render_header, get_conn, tarih_input

def goster(db_yolu):
    render_header("⚖️ Hukuki Süreç ve İcra Takibi")
    
    # 1. VERİTABANI ALTYAPISI: Hukuki dosyalar tablosunu otomatik oluştur (Yoksa)
    conn = get_conn(db_yolu)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS hukuki_dosyalar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sakin_id INTEGER,
        dosya_no TEXT,
        icra_dairesi TEXT,
        avukat_adi TEXT,
        acilis_tarihi TEXT,
        dava_turu TEXT,
        durum TEXT DEFAULT 'Devam Ediyor',
        notlar TEXT
    )''')
    conn.commit()

    # Sakinleri çekelim (Formlarda kullanmak için)
    c.execute("SELECT id, blok, daire_no, malik_ad FROM sakinler")
    sakinler_liste = c.fetchall()
    sakin_secenekleri = {f"{s[1]} Blok - No:{s[2]} ({s[3]})": s[0] for s in sakinler_liste}

    # --- ÜST PANEL: YENİ DOSYA AÇMA ---
    with st.expander("➕ Yeni İcra / Dava Dosyası Oluştur", expanded=False):
        with st.form("hukuki_yeni_form", clear_on_submit=True):
            if not sakinler_liste:
                st.warning("Sistemde kayıtlı sakin yok.")
            else:
                sec_sakin = st.selectbox("İcraya/Davaya Verilen Daire", list(sakin_secenekleri.keys()))
                
                col1, col2 = st.columns(2)
                with col1:
                    dosya_no = st.text_input("Dosya Numarası (Örn: 2026/1453 Esas)")
                    icra_dairesi = st.text_input("İcra Dairesi / Mahkeme (Örn: İzmit 1. İcra)")
                    dava_turu = st.selectbox("Dosya Türü", ["İlamsız İcra Takibi", "İlamlı İcra", "Tahliye Davası", "Diğer"])
                with col2:
                    avukat_adi = st.text_input("Dosyayı Takip Eden Avukat")
                    acilis_tarihi = tarih_input("Dosya Açılış Tarihi", datetime.date.today(), key="hukuki_acilis")
                    notlar = st.text_input("Kısa Açıklama / Notlar")

                if st.form_submit_button("⚖️ Dosyayı Kaydet ve Takibe Başla", type="primary"):
                    if dosya_no and icra_dairesi:
                        sakin_id = sakin_secenekleri[sec_sakin]
                        c.execute("""INSERT INTO hukuki_dosyalar 
                                     (sakin_id, dosya_no, icra_dairesi, avukat_adi, acilis_tarihi, dava_turu, notlar) 
                                     VALUES (?,?,?,?,?,?,?)""", 
                                  (sakin_id, dosya_no, icra_dairesi, avukat_adi, str(acilis_tarihi), dava_turu, notlar))
                        conn.commit()
                        st.success(f"{dosya_no} numaralı hukuki süreç başlatıldı!")
                        st.rerun()
                    else:
                        st.error("Dosya Numarası ve İcra Dairesi boş bırakılamaz.")

    st.divider()

    # --- ORTA PANEL: AKTİF DOSYALAR LİSTESİ ---
    st.markdown("##### 📂 İcra ve Dava Dosyaları Arşivi")
    query = """
    SELECT 
        h.id, s.blok, s.daire_no, s.malik_ad, 
        h.dosya_no, h.icra_dairesi, h.avukat_adi, h.acilis_tarihi, h.dava_turu, h.durum, h.notlar
    FROM hukuki_dosyalar h
    INNER JOIN sakinler s ON h.sakin_id = s.id
    ORDER BY h.id DESC
    """
    df_hukuk = pd.read_sql_query(query, conn)
    
    if not df_hukuk.empty:
        # Görsel düzenleme
        gosterim_df = df_hukuk.copy()
        gosterim_df['Daire/Kişi'] = gosterim_df['blok'] + " No:" + gosterim_df['daire_no'] + " (" + gosterim_df['malik_ad'] + ")"
        gosterim_df = gosterim_df[['Daire/Kişi', 'dosya_no', 'icra_dairesi', 'dava_turu', 'avukat_adi', 'acilis_tarihi', 'durum', 'notlar']]
        gosterim_df.columns = ['İlgili Kişi', 'Dosya No', 'Merci', 'Tür', 'Avukat', 'Açılış', 'Durum', 'Notlar']
        
        # Duruma göre renk verelim
        st.dataframe(gosterim_df.style.map(lambda x: 'color: green; font-weight: bold' if x == 'Kapatıldı / Tahsil Edildi' else ('color: red; font-weight: bold' if x == 'Devam Ediyor' else 'color: orange'), subset=['Durum']), use_container_width=True, hide_index=True)
        
        # --- ALT PANEL: DURUM GÜNCELLEME ---
        with st.container(border=True):
            st.markdown("##### 🔄 Dosya Durumu Güncelle")
            dosyalar_dict = {f"{r['dosya_no']} - {r['malik_ad']} ({r['durum']})": r['id'] for _, r in df_hukuk.iterrows()}
            
            col_g1, col_g2, col_g3 = st.columns([2, 1, 1])
            with col_g1:
                secilen_dosya_metin = st.selectbox("İşlem Yapılacak Dosyayı Seçin", list(dosyalar_dict.keys()))
            with col_g2:
                yeni_durum = st.selectbox("Yeni Durum", ["Devam Ediyor", "İtiraz Edildi", "Haciz Aşamasında", "Kapatıldı / Tahsil Edildi", "İptal Edildi"])
            with col_g3:
                st.write("") # Hizalama boşluğu
                if st.button("Güncelle", use_container_width=True):
                    dosya_id = dosyalar_dict[secilen_dosya_metin]
                    c.execute("UPDATE hukuki_dosyalar SET durum=? WHERE id=?", (yeni_durum, dosya_id))
                    conn.commit()
                    st.success("Dosya durumu güncellendi!")
                    st.rerun()
    else:
        st.success("🎉 Harika! Sistemde takip edilen hiçbir icra veya dava dosyası bulunmuyor.")

    conn.close()

