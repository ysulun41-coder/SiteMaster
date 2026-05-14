"""
SiteMaster – Ortak Araçlar
sitemaster_logo_koy() → aktif sitenin logosunu her sayfanın sağ üst
köşesine st.columns([5, 1]) ile yerleştirir.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_LOGO_DOSYA = Path(__file__).parent / "logo.png"


def sitemaster_logo_koy() -> None:
    """
    Aktif sitenin logosunu sayfanın SAĞ ÜST köşesine koyar.

    Kaynak önceliği:
      1. st.session_state.logo_b64  — giriş yapıldığında DB'den yüklenen logo
      2. logo.png                   — proje klasöründeki yedek dosya
      Her ikisi de yoksa hiçbir şey göstermez; emoji veya ikon uydurmaz.

    Yerleşim: st.columns([5, 1]) — sağ dar kolona logo, sol geniş kolon boş.
    Sayfa başlığı ve içerik bu satırın altında tam genişlikte akar.
    """
    # ── Logo kaynağını belirle ────────────────────────────────────────────────
    b64 = st.session_state.get("logo_b64")
    if b64:
        gorsel: str = f"data:image/png;base64,{b64}"
    elif _LOGO_DOSYA.exists():
        gorsel = str(_LOGO_DOSYA)
    else:
        return  # logo kaynağı yok — hiçbir şey gösterme, emoji yok

    # ── Sağ üst köşe yerleşimi ────────────────────────────────────────────────
    _, col_logo = st.columns([5, 1])
    with col_logo:
        st.image(gorsel, width=90)
