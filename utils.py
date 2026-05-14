"""SiteMaster – Ortak Araçlar"""
from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

_LOGO = Path(__file__).parent / "logo.png"
_B64_CACHE: str | None = None


def _logo_b64() -> str | None:
    """DB session_state → logo.png dosyası önceliğiyle base64 döner."""
    global _B64_CACHE
    b64 = st.session_state.get("logo_b64")
    if b64:
        return b64
    if _B64_CACHE is None and _LOGO.exists():
        _B64_CACHE = base64.b64encode(_LOGO.read_bytes()).decode()
    return _B64_CACHE


def render_sidebar_header() -> None:
    """Logoyu sidebar'ın en tepesinde, optimize edilmiş boyutla gösterir."""
    b64 = _logo_b64()
    if not b64:
        return
    with st.sidebar:
        st.image(f"data:image/png;base64,{b64}", use_container_width=True)
        st.divider()


def render_header(page_title: str) -> None:
    """
    Her sayfanın en üstünde logo + başlık satırı oluşturur.
      sol kolon [1] → logo
      sağ kolon [4] → sayfa başlığı
    İçerik bu satırın altında tam genişlikte (use_container_width) akar.
    """
    b64 = _logo_b64()
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        if b64:
            st.image(f"data:image/png;base64,{b64}", use_container_width=True)
    with col_title:
        st.subheader(page_title)
    st.divider()
