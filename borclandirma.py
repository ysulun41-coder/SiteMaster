import datetime
import sqlite3
from typing import Optional

import streamlit as st


def _daire_etiketi(blok: str, daire_no: str, malik_ad: Optional[str]) -> str:
    isim = (malik_ad or "").strip() or "İsimsiz"
    return f"{blok} - {daire_no} ({isim})"


def goster(db_yolu: str) -> None:
    st.subheader("💰 Borçlandırma ve Otomatik Aidat Sistemi")
    bugun = datetime.date.today()

    tab1, tab2, tab3 = st.tabs(
        ["⚙️ Otomatik Aidat Talimatı", "🔄 Toplu Tahakkuk", "🎯 Tekil Borç"]
    )

    # --- TAB 1: OTOMATİK TALİMAT ---
    with tab1:
        st.markdown("#### 🤖 Her Ay Otomatik Dağıtım")
        st.caption(
            "Aylık sabit tutar ve açıklama taslağı tanımlayın; motor her ay için "
            "kayıt oluşturur (aylık tekilleştirme `otomatik_kayitlar` ile)."
        )

        conn = sqlite3.connect(db_yolu)
        c = conn.cursor()
        c.execute("SELECT tutar, aciklama, durum FROM otomatik_talimatlar WHERE id=1")
        mevcut_talimat = c.fetchone()

        with st.form("otomatik_ayar_form"):
            tutar = st.number_input(
                "Aylık Sabit Aidat Tutarı (₺)",
                value=float(mevcut_talimat[0]) if mevcut_talimat else 0.0,
                step=100.0,
            )
            aciklama = st.text_input(
                "Açıklama Taslağı (Örn: Aidat Ödemesi)",
                value=mevcut_talimat[1] if mevcut_talimat else "Aidat Ödemesi",
            )
            durum = st.toggle(
                "Otomatik Dağıtım Aktif",
                value=bool(mevcut_talimat[2]) if mevcut_talimat else False,
            )

            if st.form_submit_button("Talimatı Kaydet / Güncelle"):
                if mevcut_talimat:
                    c.execute(
                        "UPDATE otomatik_talimatlar SET tutar=?, aciklama=?, durum=? WHERE id=1",
                        (tutar, aciklama, 1 if durum else 0),
                    )
                else:
                    c.execute(
                        "INSERT INTO otomatik_talimatlar (tutar, aciklama, durum) VALUES (?,?,?)",
                        (tutar, aciklama, 1 if durum else 0),
                    )
                conn.commit()
                st.success("Otomatik aidat talimatı başarıyla güncellendi.")
        conn.close()

    # --- TAB 2: AKILLI TOPLU TAHAKKUK ---
    with tab2:
        varsayilan_son = bugun + datetime.timedelta(days=10)

        conn = sqlite3.connect(db_yolu)
        c = conn.cursor()
        c.execute(
            "SELECT blok, daire_no, malik_ad FROM sakinler ORDER BY blok, daire_no"
        )
        sakin_satirlari = c.fetchall()
        conn.close()

        etiketten_konum: dict[str, tuple[str, str]] = {}
        daire_secenekleri: list[str] = []
        for blok, daire_no, malik_ad in sakin_satirlari:
            etiket = _daire_etiketi(blok, daire_no, malik_ad)
            etiketten_konum[etiket] = (blok, daire_no)
            daire_secenekleri.append(etiket)

        with st.container(border=True):
            st.markdown("### Toplu Aidat Dağıtımı")
            st.caption(
                "Tüm kayıtlı dairelere aynı tutarda tahakkuk oluşturur; hariç "
                "işaretlediğiniz dairelere kayıt düşmez."
            )

            col_a, col_b = st.columns(2)
            with col_a:
                borc_tanimi = st.text_input(
                    "Borç Tanımı",
                    placeholder="Örn: Haziran 2026 Aidatı",
                    key="toplu_borc_tanimi",
                )
                aidat_tutari = st.number_input(
                    "Aidat Tutarı (₺)",
                    min_value=0.0,
                    value=0.0,
                    step=50.0,
                    format="%.2f",
                    key="toplu_aidat_tutari",
                )
            with col_b:
                tahakkuk_tarihi = st.date_input(
                    "Tahakkuk Tarihi",
                    value=bugun,
                    key="toplu_tahakkuk_tarihi",
                )
                son_odeme_tarihi = st.date_input(
                    "Son Ödeme Tarihi",
                    value=varsayilan_son,
                    key="toplu_son_odeme",
                )

            hariç_etiketler = st.multiselect(
                "Borçlandırma Harici Tutulacak Daireler",
                options=daire_secenekleri,
                default=[],
                help="Seçilen dairelere bu işlemde borç kaydı oluşturulmaz; liste boşsa tüm daireler borçlandırılır.",
                key="toplu_haric_daireler",
            )

            haric_konumlar = {etiketten_konum[e] for e in hariç_etiketler if e in etiketten_konum}

            st.divider()
            toplu_borclandir = st.button(
                "Toplu Borçlandır",
                type="primary",
                use_container_width=True,
                key="btn_toplu_borclandir",
            )

        if toplu_borclandir:
            borc_tanimi_k = (borc_tanimi or "").strip()
            if not borc_tanimi_k:
                st.error("Lütfen borç tanımını doldurun.")
            elif aidat_tutari <= 0:
                st.warning("Aidat tutarı sıfırdan büyük olmalıdır.")
            elif not sakin_satirlari:
                st.error("Sistemde kayıtlı sakin bulunmuyor; önce sakin listesini oluşturun.")
            else:
                tahakkuk_str = tahakkuk_tarihi.isoformat()
                son_odeme_str = son_odeme_tarihi.isoformat()

                conn = sqlite3.connect(db_yolu)
                c = conn.cursor()
                islenen = 0
                try:
                    for blok, daire_no, _malik in sakin_satirlari:
                        if (blok, daire_no) in haric_konumlar:
                            continue
                        c.execute(
                            """
                            INSERT INTO aidatlar
                            (blok, daire_no, tarih, tutar, aciklama, son_odeme_tarihi, faiz_uygula, yillik_faiz)
                            VALUES (?,?,?,?,?,?,?,?)
                            """,
                            (
                                blok,
                                daire_no,
                                tahakkuk_str,
                                float(aidat_tutari),
                                borc_tanimi_k,
                                son_odeme_str,
                                1,
                                60.0,
                            ),
                        )
                        islenen += 1
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Kayıt sırasında hata oluştu: {e}")
                finally:
                    conn.close()

                if islenen > 0:
                    toplam_tl = islenen * float(aidat_tutari)
                    st.success(
                        f"Toplam {islenen} daireye {toplam_tl:,.2f} TL borç başarıyla tahakkuk ettirildi."
                    )
                    st.balloons()

    # --- TAB 3: TEKİL BORÇ ---
    with tab3:
        st.markdown("#### Tek daireye borç / tahakkuk")
        conn = sqlite3.connect(db_yolu)
        c = conn.cursor()
        c.execute(
            "SELECT id, blok, daire_no, malik_ad FROM sakinler ORDER BY blok, daire_no"
        )
        tekil_liste = c.fetchall()
        conn.close()

        if not tekil_liste:
            st.info("Sakin kaydı yok; tekil borçlandırma için önce daire ekleyin.")
        else:
            secenek_map = {
                _daire_etiketi(r[1], r[2], r[3]): (r[1], r[2]) for r in tekil_liste
            }
            secilen = st.selectbox("Daire", list(secenek_map.keys()), key="tekil_daire")
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                t_aciklama = st.text_input("Borç açıklaması", key="tekil_aciklama")
                t_tutar = st.number_input(
                    "Tutar (₺)", min_value=0.0, value=0.0, step=50.0, key="tekil_tutar"
                )
            with t_col2:
                t_tahakkuk = st.date_input(
                    "Tahakkuk tarihi", value=bugun, key="tekil_tahakkuk"
                )
                t_son = st.date_input(
                    "Son ödeme tarihi",
                    value=bugun + datetime.timedelta(days=10),
                    key="tekil_son",
                )

            if st.button("Tekil borcu kaydet", key="btn_tekil_borc"):
                if not (t_aciklama or "").strip():
                    st.error("Açıklama zorunludur.")
                elif t_tutar <= 0:
                    st.warning("Tutar sıfırdan büyük olmalıdır.")
                else:
                    b, d = secenek_map[secilen]
                    conn = sqlite3.connect(db_yolu)
                    c = conn.cursor()
                    try:
                        c.execute(
                            """
                            INSERT INTO aidatlar
                            (blok, daire_no, tarih, tutar, aciklama, son_odeme_tarihi, faiz_uygula, yillik_faiz)
                            VALUES (?,?,?,?,?,?,?,?)
                            """,
                            (
                                b,
                                d,
                                t_tahakkuk.isoformat(),
                                float(t_tutar),
                                (t_aciklama or "").strip(),
                                t_son.isoformat(),
                                1,
                                60.0,
                            ),
                        )
                        conn.commit()
                        st.success("Borç kaydı oluşturuldu.")
                    except Exception as e:
                        conn.rollback()
                        st.error(str(e))
                    finally:
                        conn.close()
