import pandas as pd
import streamlit as st
from utils.auth import check_password
from utils.db import load_data, update_user_data

# ==========================================
# 0. 頁面基本設定
# ==========================================
st.set_page_config(
    page_title="公司內部用戶資料管理系統", page_icon="👥", layout="centered"
)

# 1. 執行登入驗證
if not check_password():
    st.stop()

# ==========================================
# 2. 狀態管理 (Session State)
# ==========================================
if "selected_user_id" not in st.session_state:
    st.session_state["selected_user_id"] = None
if "page_mode" not in st.session_state:
    st.session_state["page_mode"] = "list"  # 可選值: "list", "view", "edit"

df = load_data()

if df.empty:
    st.warning("目前資料庫中沒有用戶資料。")
    if st.button("🔄 重新載入"):
        st.rerun()
else:
    if "id" not in df.columns or "name" not in df.columns:
        st.error("資料表格式錯誤：必須包含 'id' 與 'name' 欄位。")
        st.stop()

    # 取得當前選中的用戶資料
    target_id = st.session_state["selected_user_id"]
    user_data = {}
    if target_id is not None:
        user_row = df[df["id"] == target_id]
        if not user_row.empty:
            user_data = user_row.iloc[0].to_dict()

    # ==========================================
    # 狀態 1：用戶詳細內容「簡介頁」(View Mode)
    # ==========================================
    if st.session_state["page_mode"] == "view" and target_id is not None:
        if not user_data:
            st.warning("找不到該用戶資料。")
            if st.button("⬅️ 返回列表"):
                st.session_state["page_mode"] = "list"
                st.rerun()
        else:
            current_name = user_data.get("name", "未命名")
            
            if st.button("⬅️ 返回用戶列表", type="secondary"):
                st.session_state["page_mode"] = "list"
                st.rerun()
                
            st.markdown(f"### 📋 用戶檔案：{current_name}")
            st.markdown("---")
            
            # 以漂亮的唯讀卡片/條列方式呈現詳細資料
            for col, val in user_data.items():
                if col == "id":
                    continue # ID 可以隱藏或低調顯示
                val_display = "無資料" if pd.isna(val) or str(val).strip() == "" else str(val)
                st.markdown(f"**🔹 {col}**")
                st.info(val_display)
                
            st.markdown("---")
            
            # 點擊後切換到編輯模式
            if st.button("✏️ 進入編輯模式", type="primary", use_container_width=True):
                st.session_state["page_mode"] = "edit"
                st.rerun()

    # ==========================================
    # 狀態 2：用戶資料「編輯頁面」(Edit Mode)
    # ==========================================
    elif st.session_state["page_mode"] == "edit" and target_id is not None:
        current_name = user_data.get("name", "未命名")
        
        if st.button("⬅️ 取消並返回詳細資料", type="secondary"):
            st.session_state["page_mode"] = "view"
            st.rerun()
            
        st.markdown(f"### ✏️ 編輯用戶資料：{current_name}")
        st.markdown("---")
        
        with st.form("edit_user_form"):
            updated_values = {}
            
            for col in df.columns:
                if col == "id":
                    st.text_input("ID (主鍵)", value=str(user_data[col]), disabled=True)
                    updated_values[col] = user_data[col]
                    continue
                    
                val = user_data[col]
                val_str = "" if pd.isna(val) else str(val)
                updated_values[col] = st.text_input(f"{col}", value=val_str)
                
            submitted = st.form_submit_button("💾 儲存變更", type="primary")
            
            if submitted:
                payload = {}
                for k, v in updated_values.items():
                    payload[k] = None if v == "" else v
                    
                success, msg = update_user_data(payload)
                if success:
                    st.success(msg)
                    st.session_state["page_mode"] = "view"  # 儲存後返回詳細頁
                    st.rerun()
                else:
                    st.error(msg)

    # ==========================================
    # 狀態 3：手機版友善的「用戶列表頁」(List Mode)
    # ==========================================
    else:
        st.title("👥 用戶資料管理")
        
        # 頂部操作列：搜尋與重新整理
        col_search, col_refresh = st.columns([4, 1])
        with col_search:
            search_keyword = st.text_input("🔍 搜尋關鍵字", placeholder="輸入姓名、電話或信箱...")
        with col_refresh:
            st.write("")
            if st.button("🔄"):
                st.cache_data.clear()
                st.rerun()

        # 新增：排序功能區塊 (使用兩欄設計，適合手機版)
        col_sort_col, col_sort_order = st.columns(2)
        with col_sort_col:
            # 取得資料表的所有欄位作為排序選項，並預設選擇 'id' 或 'name'
            sort_options = list(df.columns)
            default_index = sort_options.index("id") if "id" in sort_options else 0
            sort_by = st.selectbox("↕️ 排序欄位", options=sort_options, index=default_index)
            
        with col_sort_order:
            # 選擇升序或降序
            sort_order = st.selectbox("順序", options=["升序 (小到大)", "降序 (大到小)"])

        # 複製一份資料準備處理
        filtered_df = df.copy()

        # 1. 先執行關鍵字篩選
        if search_keyword:
            mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_keyword, case=False, na=False)).any(axis=1)
            filtered_df = filtered_df[mask]

        # 2. 執行排序邏輯
        is_ascending = True if sort_order == "升序 (小到大)" else False
        # pandas 的 sort_values 處理包含空值的欄位時，預設會將空值放在最後
        filtered_df = filtered_df.sort_values(by=sort_by, ascending=is_ascending, na_position='last')

        st.markdown(f"<p style='color: gray; font-size: 14px;'>共找到 {len(filtered_df)} 位用戶（點擊名字查看詳細內容）</p>", unsafe_allow_html=True)

        # 渲染卡片式清單
        for index, row in filtered_df.iterrows():
            uid = row["id"]
            name = row.get("name", "未命名")
            # 動態抓取使用者作為排序依據的欄位，顯示在名字下方（如果不是預設的 id 或 name 的話）
            if sort_by not in ["id", "name"] and not pd.isna(row.get(sort_by)):
                sub_info = f"{sort_by}: {row.get(sort_by)}"
            else:
                # 預設顯示電話或信箱
                sub_info = row.get("phone", row.get("email", ""))
          
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**👤 {name}**")
                    if sub_info:
                        st.markdown(f"<span style='color: gray; font-size: 12px;'>{sub_info}</span>", unsafe_allow_html=True)
                with col2:
                    if st.button("查看", key=f"btn_{uid}"):
                        st.session_state["selected_user_id"] = uid
                        st.session_state["page_mode"] = "view"
                        st.rerun()
                st.markdown("---")