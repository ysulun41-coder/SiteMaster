import streamlit as st
import sqlite3
from utils import render_header


def goster(db_yolu):
    render_header("Yeni Kişi Kaydı")

    conn = sqlite3.connect(db_yolu)
    c = conn.cursor()
    c.execute("SELECT blok_adi, daire_sayisi FROM bloklar ORDER BY id")
    blok_rows = c.fetchall()
    conn.close()

    if not blok_rows:
        st.warning("Kayıtlı blok yok. Önce site kurulumunda mimari yapıyı (blok adı ve daire adedi) tanımlayın.")
        return

    blok_map = {r[0]: int(r[1]) for r in blok_rows}
    blok_names = [r[0] for r in blok_rows]

    with st.expander("Mimari plan (site kurulumunda girilen liste)", expanded=True):
        for bn, dcnt in blok_rows:
            st.markdown(f"- **{bn}** — {dcnt} daire")

    with st.form("sakin_form", clear_on_submit=True):
        st.markdown("##### Kayıt bilgileri")
        col1, col2, col3 = st.columns(3)
        with col1:
            s_blok = st.selectbox("Blok", blok_names)
        d_max = blok_map[s_blok]
        with col2:
            st.caption(f"Bu blokta {d_max} daire tanımlı (1–{d_max}).")
            plan_daire = st.selectbox(
                "Plandaki daire no",
                [str(x) for x in range(1, d_max + 1)],
                key="sk_plan_daire",
            )
        with col3:
            d_ozel = st.text_input(
                "Özel daire no",
                placeholder="Boş bırakılırsa soldaki seçilir",
                help="Planda olmayan bir numara (ör. B12) gerekiyorsa buraya yazın.",
            )
        d_no = d_ozel.strip() if d_ozel.strip() else plan_daire

        c_m, c_k = st.columns(2)
        with c_m:
            m_a = st.text_input("Kat malik adı *")
            m_tc = st.text_input("Kat malik TC", max_chars=11)
            m_t = st.text_input("Kat malik tel", max_chars=11)
            plk = st.text_input("Araç plaka")
        with c_k:
            k_a = st.text_input("Kiracı ad")
            k_tc = st.text_input("Kiracı TC", max_chars=11)
            k_t = st.text_input("Kiracı tel")

        s_sifre_ek = st.text_input(
            "Daire şifresi (ek parça)",
            help="Tam şifre: blok + daire + bu parça birleştirilir.",
        )

        if st.form_submit_button("Kaydet", type="primary"):
            if not s_blok or not d_no or not m_a or not s_sifre_ek:
                st.error("Blok, daire, kat malik adı ve şifre ek parçası zorunludur.")
            else:
                tam_sifre = f"{s_blok}{d_no}-{s_sifre_ek}"
                conn = sqlite3.connect(db_yolu)
                c = conn.cursor()
                c.execute("SELECT id FROM sakinler WHERE blok=? AND daire_no=?", (s_blok, d_no))
                if c.fetchone():
                    st.error(f"{s_blok} / {d_no} için kayıt zaten var.")
                else:
                    c.execute(
                        """INSERT INTO sakinler
                        (blok, daire_no, malik_ad, malik_tc, malik_tel, kiraci_ad, kiraci_tc, kiraci_tel, plaka, sifre)
                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (s_blok, d_no, m_a, m_tc, m_t, k_a, k_tc, k_t, plk, tam_sifre),
                    )
                    conn.commit()
                    st.success(f"Kayıt tamam. Giriş şifresi: `{tam_sifre}`")
                conn.close()
