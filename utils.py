"""
SiteMaster – Ortak Araçlar
sitemaster_logo_koy() → aktif sitenin logosunu CSS position:absolute ile
sayfanın sağ üst köşesine yüzdürür; sayfa layout'una dokunmaz.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

_LOGO_DOSYA = Path(__file__).parent / "logo.png"


def sitemaster_logo_koy() -> None:
    """
    Aktif sitenin logosunu sayfanın SAĞ ÜST köşesine yüzdürür.

    Kaynak önceliği:
      1. st.session_state.logo_b64  — giriş sonrası DB'den yüklenen logo
      2. logo.png                   — proje klasöründeki yedek dosya
    Her ikisi de yoksa sessizce çıkar; emoji veya ikon uydurmaz.

    Yerleşim: position:absolute, top:-60px, right:0 — layout bozulmaz.
    """
    # ── Logo base64 kaynağını belirle ────────────────────────────────────────
    b64: str | None = st.session_state.get("logo_b64")

    if not b64 and _LOGO_DOSYA.exists():
        b64 = base64.b64encode(_LOGO_DOSYA.read_bytes()).decode()

    if not b64:
        return  # logo kaynağı yok — hiçbir şey gösterme

    # ── CSS floating logo (kullanıcı tarafından belirlenen yapı) ─────────────
    st.markdown(
        f"""
        <div style="position: absolute; top: -60px; right: 0px;
                    z-index: 1000; text-align: center;">
            <img src="data:image/png;base64,{b64}" width="80">
            <p style="font-size: 10px; margin-top: -5px; color: gray;">SiteMaster</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
