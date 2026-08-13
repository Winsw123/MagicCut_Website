import streamlit as st

def check_password():
    """簡單的密碼驗證函式"""
    def password_entered():
        if st.session_state["password"] == st.secrets.get("APP_PASSWORD"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.subheader("🔒 內部系統登入")
        st.text_input(
            "請輸入內部存取密碼", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.subheader("🔒 內部系統登入")
        st.text_input(
            "請輸入內部存取密碼", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 密碼錯誤，請重新輸入")
        return False
    else:
        return True