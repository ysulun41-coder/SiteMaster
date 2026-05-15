import streamlit as st
import pandas as pd
from utils import render_header, get_conn

try:
    import altair as alt

    _ALTAIR = True
except ImportError:
    _ALTAIR = False

_GELIR_RENK = "#22c55e"
_GIDER_RENK = "#ef4444"
_MARKA_RENK = "#2563eb"


def _dashboard_css() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stMetric"] {
            background: linear-gradient(160deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 0.85rem 1rem 1rem;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
        }
        div[data-testid="stMetric"] label {
            color: #64748b !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
        }
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: #0f172a !important;
            font-weight: 800 !important;
        }
        .dash-grafik-baslik {
            font-size: 1rem;
            font-weight: 700;
            color: #0f172a;
            margin: 0 0 0.15rem;
        }
        .dash-grafik-alt {
            font-size: 0.82rem;
            color: #64748b;
            margin: 0 0 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _tl(v: float) -> str:
    return f"{v:,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")


def _grafik_kutu(baslik: str, alt: str, chart_fn) -> None:
    with st.container(border=True):
        st.markdown(f'<p class="dash-grafik-baslik">{baslik}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="dash-grafik-alt">{alt}</p>', unsafe_allow_html=True)
        chart_fn()


def _fetch_aylik_trend(conn) -> pd.DataFrame:
    """Aidat tahsilatı ve giderleri aya göre toplar."""
    parcalar = []
    for sql, tur in [
        ("SELECT tarih, tutar FROM aidatlar WHERE durum='Ödendi'", "Gelir"),
        ("SELECT tarih, tutar FROM giderler", "Gider"),
    ]:
        ham = pd.read_sql_query(sql, conn)
        if ham.empty:
            continue
        ham["tarih"] = pd.to_datetime(ham["tarih"], errors="coerce")
        ham = ham.dropna(subset=["tarih"])
        if ham.empty:
            continue
        ham["ay"] = ham["tarih"].dt.to_period("M").dt.to_timestamp()
        ozet = ham.groupby("ay", as_index=False)["tutar"].sum()
        ozet["Tur"] = tur
        parcalar.append(ozet)
    if not parcalar:
        return pd.DataFrame(columns=["ay", "tutar", "Tur"])
    return pd.concat(parcalar, ignore_index=True).sort_values("ay")


def _chart_gelir_gider(gelir: float, gider: float) -> None:
    df = pd.DataFrame({"Kategori": ["Gelir", "Gider"], "Tutar": [gelir, gider]})
    if _ALTAIR:
        chart = (
            alt.Chart(df)
            .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, size=56)
            .encode(
                x=alt.X("Kategori:N", title=None),
                y=alt.Y("Tutar:Q", title="Tutar (₺)", axis=alt.Axis(format=",.0f")),
                color=alt.Color(
                    "Kategori:N",
                    scale=alt.Scale(domain=["Gelir", "Gider"], range=[_GELIR_RENK, _GIDER_RENK]),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("Kategori:N", title=""),
                    alt.Tooltip("Tutar:Q", title="Tutar", format=",.2f"),
                ],
            )
            .properties(height=300)
            .configure_view(strokeWidth=0, fill="#ffffff")
            .configure_axis(gridColor="#f1f5f9", domainColor="#e2e8f0", labelColor="#475569")
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.bar_chart(df.set_index("Kategori"), height=300)


def _chart_gider_kategori(df_ga: pd.DataFrame) -> None:
    if df_ga.empty:
        st.info("Henüz gider kaydı yok.")
        return
    df_ga = df_ga.sort_values("Toplam", ascending=True)
    if _ALTAIR:
        chart = (
            alt.Chart(df_ga)
            .mark_bar(cornerRadiusEnd=6, color=_MARKA_RENK)
            .encode(
                y=alt.Y("kategori:N", title=None, sort="-x"),
                x=alt.X("Toplam:Q", title="Tutar (₺)", axis=alt.Axis(format=",.0f")),
                tooltip=[
                    alt.Tooltip("kategori:N", title="Kategori"),
                    alt.Tooltip("Toplam:Q", title="Toplam", format=",.2f"),
                ],
            )
            .properties(height=max(260, 40 * len(df_ga)))
            .configure_view(strokeWidth=0)
            .configure_axis(gridColor="#f1f5f9", domainColor="#e2e8f0", labelColor="#475569")
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.bar_chart(df_ga.set_index("kategori"), height=260)


def _chart_aylik_trend(df_trend: pd.DataFrame) -> None:
    if df_trend.empty:
        st.info("Aylık trend için tarihli tahsilat veya gider kaydı gerekir.")
        return
    if _ALTAIR:
        chart = (
            alt.Chart(df_trend)
            .mark_line(point=alt.OverlayMarkDef(filled=True, size=70), strokeWidth=2.5)
            .encode(
                x=alt.X(
                    "ay:T",
                    title="Ay",
                    axis=alt.Axis(format="%b %Y", labelAngle=-35, tickCount=8),
                ),
                y=alt.Y("tutar:Q", title="Tutar (₺)", axis=alt.Axis(format=",.0f")),
                color=alt.Color(
                    "Tur:N",
                    title="",
                    scale=alt.Scale(domain=["Gelir", "Gider"], range=[_GELIR_RENK, _GIDER_RENK]),
                ),
                tooltip=[
                    alt.Tooltip("ay:T", title="Ay", format="%B %Y"),
                    alt.Tooltip("Tur:N", title="Tür"),
                    alt.Tooltip("tutar:Q", title="Tutar", format=",.2f"),
                ],
            )
            .properties(height=340)
            .configure_view(strokeWidth=0, fill="#ffffff")
            .configure_axis(gridColor="#f1f5f9", domainColor="#e2e8f0", labelColor="#475569")
            .configure_legend(orient="top", titleAnchor="start", labelColor="#475569")
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        piv = df_trend.pivot(index="ay", columns="Tur", values="tutar").fillna(0)
        st.line_chart(piv, height=340)


def _chart_gider_pasta(df_ga: pd.DataFrame) -> None:
    if df_ga.empty:
        st.info("Pasta grafik için gider kaydı yok.")
        return
    df = df_ga.copy()
    toplam = df["Toplam"].sum()
    if toplam <= 0:
        st.info("Gider tutarı sıfır.")
        return
    df["Oran"] = df["Toplam"] / toplam

    if _ALTAIR:
        chart = (
            alt.Chart(df)
            .mark_arc(innerRadius=58, outerRadius=118, padAngle=0.02)
            .encode(
                theta=alt.Theta("Toplam:Q", stack=True),
                color=alt.Color(
                    "kategori:N",
                    legend=alt.Legend(title="Kategori", orient="right", labelLimit=120),
                    scale=alt.Scale(scheme="tableau10"),
                ),
                tooltip=[
                    alt.Tooltip("kategori:N", title="Kategori"),
                    alt.Tooltip("Toplam:Q", title="Tutar", format=",.2f"),
                    alt.Tooltip("Oran:Q", title="Pay", format=".1%"),
                ],
            )
            .properties(height=340)
            .configure_view(strokeWidth=0)
            .configure_legend(labelColor="#475569", titleColor="#334155")
        )
        st.altair_chart(chart, use_container_width=True)
        st.caption(f"Toplam gider: **{_tl(toplam)}**")
    else:
        st.bar_chart(df.set_index("kategori")["Toplam"], height=340)


def goster(db_yolu: str) -> None:
    render_header("KASA DURUMU")
    _dashboard_css()

    conn = get_conn(db_yolu)
    c = conn.cursor()
    c.execute("SELECT SUM(tutar) FROM aidatlar WHERE durum='Ödendi'")
    gelir = c.fetchone()[0] or 0.0
    c.execute("SELECT SUM(tutar) FROM giderler")
    gider = c.fetchone()[0] or 0.0
    c.execute("SELECT SUM(tutar) FROM aidatlar WHERE durum='Ödenmedi'")
    bekleyen = c.fetchone()[0] or 0.0
    kasa = gelir - gider

    df_ga = pd.read_sql_query(
        "SELECT kategori, SUM(tutar) AS Toplam FROM giderler GROUP BY kategori ORDER BY Toplam DESC",
        conn,
    )
    df_trend = _fetch_aylik_trend(conn)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam Tahsilat", _tl(gelir))
    m2.metric("Toplam Gider", _tl(gider))
    m3.metric("Net Kasa", _tl(kasa))
    m4.metric("Bekleyen Alacak", _tl(bekleyen), delta_color="inverse")

    st.divider()

    c_g1, c_g2 = st.columns(2, gap="large")
    with c_g1:
        _grafik_kutu(
            "Gelir / Gider dengesi",
            "Tahsil edilen aidatlar ile yapılan harcamaların karşılaştırması",
            lambda: _chart_gelir_gider(gelir, gider),
        )
    with c_g2:
        _grafik_kutu(
            "Gider dağılımı (çubuk)",
            "Kategorilere göre toplam harcama",
            lambda: _chart_gider_kategori(df_ga),
        )

    st.divider()

    c_t1, c_t2 = st.columns(2, gap="large")
    with c_t1:
        _grafik_kutu(
            "Aylık kasa trendi",
            "Ay bazında tahsilat (yeşil) ve gider (kırmızı) hareketi",
            lambda: _chart_aylik_trend(df_trend),
        )
    with c_t2:
        _grafik_kutu(
            "Gider payları (pasta)",
            "Harcama kategorilerinin toplam gider içindeki oranı",
            lambda: _chart_gider_pasta(df_ga),
        )

    conn.close()
