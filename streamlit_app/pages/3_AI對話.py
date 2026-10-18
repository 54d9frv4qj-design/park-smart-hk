# -*- coding: utf-8 -*-
"""
泊得好 Park Smart HK — AI 對話
Streamlit chat 界面，query_parser 解析，recommender 排序，港式用語
"""
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from src.config import COLORS
from src.db.connection import get_engine, init_db
from src.genai.rag_engine import get_assistant

st.set_page_config(page_title="AI 對話 — 泊得好", page_icon="💬", layout="wide")
st.markdown(f"<h1 style='color:{COLORS['primary']}'>💬 AI 泊車助手</h1>", unsafe_allow_html=True)
st.caption("用港式中文問我，邊度好泊車、收費幾多、未來會唔會滿，我都答到你！")

@st.cache_resource
def get_db_engine():
    e = get_engine()
    init_db(e)
    return e

engine = get_db_engine()
assistant = get_assistant()

# 快捷問題
st.subheader("⚡ 快捷問題")
quick_questions = [
    "而家旺角邊度有位泊？",
    "中環邊個停車場最平？",
    "30分鐘後銅鑼灣會唔會滿？",
    "附近有冇路邊咪錶？",
    "今晚夜泊邊度抵？",
]
cols = st.columns(5)
for i, q in enumerate(quick_questions):
    if cols[i].button(q, use_container_width=True):
        st.session_state.quick_q = q

# 對話歷史
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "你好！我係泊得好助手 🅿️ 想搵邊度泊車？話我知就得！"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 用戶輸入
user_input = st.chat_input("問我關於泊車嘅問題...")
if hasattr(st.session_state, "quick_q"):
    user_input = st.session_state.quick_q
    del st.session_state.quick_q

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # AI 回應
    with st.chat_message("assistant"):
        with st.spinner("諗緊..."):
            result = assistant.chat(user_input, st.session_state.messages)
            response = result["response"]
            st.markdown(response)

            # 顯示解析資訊
            with st.expander("🔍 解析細節"):
                st.write(f"意圖：`{result['intent']}`")
                st.write(f"信心：`{result['confidence']:.0%}`")
                st.write(f"實體：`{result['entities']}`")
                if result.get("recommendations"):
                    st.write("推薦：")
                    for r in result["recommendations"][:3]:
                        st.write(f"  - {r.get('name', '')}（{r.get('vacancy', '?')}位）")

    st.session_state.messages.append({"role": "assistant", "content": response})

# 側邊欄
with st.sidebar:
    st.header("💡 使用技巧")
    st.markdown("""
    - 講地區名就得：「旺角」「中環」「銅鑼灣」
    - 可以問收費：「邊個最平？」「時租幾多？」
    - 可以問預測：「30分鐘後會唔會滿？」
    - 可以問咪錶：「附近有冇路邊咪錶？」
    - 可以問夜泊：「今晚邊度夜泊抵？」
    """)
    st.divider()
    if st.button("🗑️ 清除對話"):
        st.session_state.messages = [
            {"role": "assistant", "content": "你好！我係泊得好助手 🅿️ 想搵邊度泊車？"}
        ]
        st.rerun()
