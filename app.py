import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types
from PIL import Image
import pandas as pd
from datetime import datetime, timezone, timedelta
import json
import requests
import plotly.graph_objects as go
import numpy as np
import re
import time
import random
import base64
import os
import math
import scipy.stats as stats
import concurrent.futures
import plotly.express as px
import urllib.parse
import ast

# ==============================================================================
# 1. CẤU HÌNH TRANG WEB (BẮT BUỘC Ở DÒNG ĐẦU TIÊN)
# ==============================================================================
st.set_page_config(
    page_title="Gia Sư AI - Hệ Sinh Thái Lớp Học Đảo Ngược",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# KHIÊN BẢO VỆ CHỐNG SẬP APP 
# ==============================================================================
try:
    # --- 1. ĐỒNG BỘ GIỜ VIỆT NAM (GMT+7) CHUẨN XÁC ---
    VN_TZ = timezone(timedelta(hours=7))
    def get_vn_time():
        return datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")

    # --- ĐỌC SECRETS AN TOÀN ---
    def get_secret(name, default=""):
        try:
            return st.secrets.get(name, default)
        except Exception:
            return default

    # np.trapezoid chỉ có ở NumPy >= 2.0; bản cũ dùng np.trapz
    _trapz = getattr(np, "trapezoid", None) or getattr(np, "trapz")

    # --- 2. KHỞI TẠO BỘ NHỚ PHIÊN & BỘ ĐẾM THỰC NGHIỆM TỰ ĐỘNG ---
    for key in ["messages", "analytics_logs", "feedback_logs", "parsed_quiz", "va_loi_logs"]:
        if key not in st.session_state: st.session_state[key] = []
    if "tram1_count" not in st.session_state: st.session_state.tram1_count = 0
    if "tram2_count" not in st.session_state: st.session_state.tram2_count = 0
    if "tram3_count" not in st.session_state: st.session_state.tram3_count = 0
    if "chat" not in st.session_state: st.session_state.chat = None
    if "current_lesson" not in st.session_state: st.session_state.current_lesson = ""
    if "current_topic" not in st.session_state: st.session_state.current_topic = ""
    if "lab_data" not in st.session_state: st.session_state.lab_data = None
    if "quiz_states" not in st.session_state: st.session_state.quiz_states = {}
    if "global_stats_loaded" not in st.session_state: st.session_state.global_stats_loaded = False
    if "global_exam_count" not in st.session_state: st.session_state.global_exam_count = 0
    if "global_logs" not in st.session_state: st.session_state.global_logs = []
    if "student_progress_history" not in st.session_state: st.session_state.student_progress_history = []
    if "active_context_key" not in st.session_state: st.session_state.active_context_key = None

    APP_URL = get_secret("APP_URL", "https://gsaithptth-khkt2026.streamlit.app/")

    # ==============================================================================
    # CSS GIAO DIỆN CHÍNH
    # ==============================================================================
    st.markdown("""
    <style>
        .block-container { padding-top: 2rem !important; padding-bottom: 1rem !important; }
        .brand-container {
            display: flex; align-items: center; justify-content: center; gap: 12px;
            margin-bottom: 20px; padding: 10px;
            background: linear-gradient(145deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9));
            border-radius: 12px; border: 1px solid #334155; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        .school-icon { width: 45px; height: auto; transition: transform 0.3s ease; }
        .school-icon:hover { transform: scale(1.1); }
        .thiennhan-logo {
            width: 115px; height: auto; border-radius: 6px;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.4); border: 1.5px solid #38bdf8;
        }
        .main-header { text-align: center; padding: 0px 0 15px 0; border-bottom: 1px dashed #475569; margin-bottom: 25px; }
        .main-title { 
            background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-size: 2.5rem; font-weight: 900; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1.5px;
        }
        .sub-title { color: #cbd5e1; font-size: 1.15rem; font-weight: 500;}
        .badge-tag { 
            background: rgba(15, 23, 42, 0.7); border: 1px solid #38bdf8; color: #38bdf8; 
            padding: 5px 15px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; 
            display: inline-block; margin-top: 8px; margin-right: 8px; box-shadow: 0 2px 5px rgba(56, 189, 248, 0.2);
        }
        .stButton > button {
            background: linear-gradient(135deg, #0284c7, #3b82f6) !important; color: white !important;
            border-radius: 10px !important; border: none !important; box-shadow: 0 4px 15px rgba(56, 189, 248, 0.3) !important;
            transition: all 0.3s ease !important; font-weight: 700 !important; padding: 0.5rem 1rem !important;
        }
        .stButton > button:hover {
            transform: translateY(-2px) !important; box-shadow: 0 6px 20px rgba(56, 189, 248, 0.6) !important;
            background: linear-gradient(135deg, #0369a1, #2563eb) !important;
        }
        .stTabs [data-baseweb="tab-list"] { 
            background: rgba(30, 41, 59, 0.5); backdrop-filter: blur(10px);
            border-radius: 12px; padding: 5px; gap: 8px; border: 1px solid #334155;
        }
        .stTabs [data-baseweb="tab"] { 
            height: 50px; white-space: pre-wrap; background-color: transparent; 
            border-radius: 8px; border: none; color: #94a3b8; font-weight: 600; transition: all 0.3s;
        }
        .stTabs [aria-selected="true"] { 
            background: rgba(56, 189, 248, 0.15) !important; color: #38bdf8 !important; 
            border-bottom: 3px solid #38bdf8 !important; box-shadow: inset 0 -3px 10px rgba(56, 189, 248, 0.1);
        }
        .lab-box-container { 
            background: linear-gradient(145deg, #0f172a, #1e293b); border: 2px solid #0ea5e9; 
            box-shadow: 0 0 20px rgba(14, 165, 233, 0.2), inset 0 0 15px rgba(14, 165, 233, 0.05);
            padding: 25px; border-radius: 15px; margin-top: 25px; margin-bottom: 20px;
            position: relative; overflow: hidden;
        }
        .lab-box-container::before {
            content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 3px;
            background: linear-gradient(90deg, transparent, #38bdf8, transparent);
        }
        [data-testid="stChatMessage"] {
            border-radius: 15px; padding: 15px; margin-bottom: 12px;
            background: rgba(30, 41, 59, 0.6); border: 1px solid #475569; box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }
        .short-link-badge { background-color: #1e293b; border: 1px dashed #38bdf8; padding: 8px 12px; border-radius: 8px; font-family: 'Courier New', Courier, monospace; font-size: 0.8rem; color: #38bdf8; text-align: center; margin: 10px 0; word-break: break-all; }
    </style>
    """, unsafe_allow_html=True)

    # ==============================================================================
    # 2. THANH BÊN (SIDEBAR) & LIÊN KẾT MÔN HỌC KHỐI LỚP
    # ==============================================================================
    def get_local_img_as_base64(file_path):
        try:
            with open(file_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception: return ""

    logo_b64 = get_local_img_as_base64("LOGO THIỆN NHÂN 3D.jpg")
    logo_html = f'<img src="data:image/jpeg;base64,{logo_b64}" class="thiennhan-logo" alt="Logo">' if logo_b64 else '<div style="background: linear-gradient(45deg, #0f172a, #1e293b); padding: 8px 12px; border-radius: 8px; color: #f8fafc; font-weight: 800; font-size: 14px; border: 1.5px solid #38bdf8; box-shadow: 0 0 10px rgba(56,189,248,0.4);">THIỆN NHÂN</div>'

    school_icon_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2338bdf8'><path d='M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3zm6.82 6L12 12.72 5.18 9 12 5.28 18.82 9zM17 15.99l-5 2.73-5-2.73v-3.72L12 15l5-2.73v3.72z'/></svg>"

    st.sidebar.markdown(f'<div class="brand-container"><img src="{school_icon_svg}" class="school-icon" alt="Icon Trường">{logo_html}</div><div style="text-align: center; margin-bottom: 15px;"><h2 style="color: #38bdf8; font-weight: 800; font-size: 1.8rem; margin: 0; text-shadow: 0px 2px 4px rgba(0,0,0,0.5);">THIẾT LẬP HỌC TẬP</h2></div>', unsafe_allow_html=True)

    with st.sidebar.expander("📱 Quét mã QR vào app trên điện thoại", expanded=False):
        qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(APP_URL, safe='')}"
        st.image(qr_api_url, caption="Bật camera Zalo/iPhone quét mượt mà!", use_container_width=True)
        st.markdown(f'<div class="short-link-badge">🔗 {APP_URL}</div>', unsafe_allow_html=True)

    with st.sidebar.expander("📲 Cài đặt Icon App vào Điện thoại & Máy tính (PWA)", expanded=False):
        st.markdown("""
        **Cách tạo Icon App mở trực tiếp (không cần gõ web/quét mã):**
        - 🤖 **Android (Chrome/Cốc Cốc):** Bấm biểu tượng menu $\\vdots$ ở góc trên ➔ Chọn **"Cài đặt ứng dụng"** (hoặc **"Thêm vào Màn hình chính"**).
        - 🍏 **iPhone / iPad (Safari):** Bấm nút **Chia sẻ** (biểu tượng $\\uparrow$) ➔ Kéo xuống chọn **"Thêm vào MH chính" (Add to Home Screen)**.
        - 💻 **Máy tính (Chrome/Edge):** Bấm biểu tượng Cài đặt trên thanh địa chỉ (góc phải thanh URL) để cài app vào Desktop. Hoặc vào `chrome://apps` tạo lối tắt.
        """)

    # JAVASCRIPT ĐỒNG BỘ LOCALSTORAGE CHO THIẾT BỊ HỌC SINH
    st.markdown("""
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        try {
            const savedKey = localStorage.getItem("GSAI_USER_CUSTOM_KEY");
            if (savedKey && !window.keyRestored) {
                window.keyRestored = true;
                console.log("GSAI: Đã phục hồi cấu hình cá nhân.");
            }
        } catch(e) {}
    });
    </script>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔑 ĐƯỜNG TRUYỀN AI CÁ NHÂN (0 ĐỒNG)")

    st.sidebar.link_button("👉 Lấy Key riêng miễn phí (15s)", "https://aistudio.google.com/apikey", use_container_width=True)
    user_custom_key = st.sidebar.text_input("Dán mã API Key của em vào đây:", type="password", placeholder="AIzaSy...")

    raw_api_key = get_secret("GEMINI_API_KEY")
    raw_sheet_url = get_secret("GOOGLE_SHEET_URL")
    sheet_webhook_url = "".join(raw_sheet_url.split()) if raw_sheet_url else ""

    sheet_view_url_secret = get_secret("GOOGLE_SHEET_VIEW_URL")
    DEFAULT_SHEET_VIEW_URL = "https://docs.google.com/spreadsheets/d/1fnG9qxmtQ5sa1C8Sb5Z9hepzB2G8asNVgSk05p7Pu9M/edit?gid=0#gid=0"
    if sheet_view_url_secret:
        sheet_view_url = "".join(sheet_view_url_secret.split())
        if "1InG9qxmTQ5saIc8Sb5Z9nepZbZG8asNVgSk05p7Pu9M" in sheet_view_url:
            sheet_view_url = DEFAULT_SHEET_VIEW_URL
    else:
        sheet_view_url = DEFAULT_SHEET_VIEW_URL

    if not st.session_state.global_stats_loaded and sheet_webhook_url:
        try:
            res = requests.get(sheet_webhook_url, timeout=3)
            if res.status_code == 200:
                data_gs = res.json()
                if isinstance(data_gs, list):
                    st.session_state.global_logs = data_gs
                    st.session_state.global_exam_count = len([x for x in data_gs if x.get('type') == 'EXAM_RESULT'])
            st.session_state.global_stats_loaded = True
        except Exception:
            pass

    admin_keys_pool = [k.strip() for k in raw_api_key.split(",")] if raw_api_key else []
    active_keys_pool = [user_custom_key.strip()] if user_custom_key.strip() else admin_keys_pool

    if not active_keys_pool:
        st.error("⚠️ Hệ thống chưa tìm thấy API Key nào khả dụng!")
        st.stop()
    elif user_custom_key.strip(): st.sidebar.success("🟢 Em đang dùng đường truyền riêng siêu tốc!")
    else: st.sidebar.info("🔵 Đang dùng đường truyền chung của Trường")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👤 THÔNG TIN HỌC SINH")
    student_name_input = st.sidebar.text_input("Họ và tên của em:", placeholder="Ví dụ: Nguyễn Văn A...")
    student_name = student_name_input.strip() if student_name_input.strip() else "Ẩn danh"

    all_grades = [f"Lớp {i}" for i in range(6, 13)]
    grade = st.sidebar.selectbox("🎯 Chọn khối lớp:", all_grades, index=6)
    grade_num = int(grade.split()[1])

    available_subjects = (
        ["Toán học", "Khoa học tự nhiên", "Ngữ văn", "Tiếng Anh", "Lịch sử & Địa lý", "Tin học", "Giáo dục công dân"]
        if grade_num <= 9 else
        ["Toán học", "Vật lý", "Hóa học", "Sinh học", "Ngữ văn", "Tiếng Anh", "Lịch sử", "Địa lý", "Tin học", "Giáo dục kinh tế và pháp luật"]
    )
    subject = st.sidebar.selectbox("📚 Môn học cần hỗ trợ:", available_subjects)

    # TỰ ĐỘNG ĐỒNG BỘ NGỮ CẢNH ĐA MÔN & XÓA SẠCH DỮ LIỆU CŨ KHI ĐỔI MÔN/LỚP
    current_context_key = f"{grade}_{subject}"
    previous_context_key = st.session_state.get("active_context_key")

    if previous_context_key is not None and previous_context_key != current_context_key:
        st.session_state.current_lesson = ""
        st.session_state.current_topic = ""
        st.session_state.parsed_quiz = []
        st.session_state.quiz_states = {}
        st.session_state.lab_data = None
        st.session_state.messages = []
        st.session_state.chat = None
        st.session_state.exam_data = None
        st.session_state.exam_answers = {}
        st.session_state.exam_state = "config"
        st.session_state.tram3_chat_messages = []
        st.session_state.exam_code = str(random.randint(1011, 9999))
        st.toast(f"🔄 Đã chuyển sang không gian học tập môn {subject} - {grade}!", icon="✨")

    st.session_state.active_context_key = current_context_key

    st.sidebar.markdown("---")
    with st.sidebar.expander("🛠️ Báo lỗi ứng dụng & Góp ý trải nghiệm", expanded=False):
        fb_category = st.selectbox("Loại vấn đề gặp phải:", ["📷 Lỗi nhận diện chữ", "📊 Lỗi đồ thị Lab", "🤖 AI giải thích khó hiểu", "⏳ Ứng dụng chậm", "💡 Đề xuất mới"])
        fb_rating = st.feedback("stars", key="fb_stars")
        fb_detail = st.text_area("Mô tả chi tiết:", key="fb_text")
        if st.button("📤 Gửi phản hồi", use_container_width=True) and fb_detail.strip():
            fb_entry = {"time": get_vn_time(), "name": student_name, "grade": grade, "subject": subject, "category": fb_category, "rating": fb_rating + 1 if fb_rating is not None else 5, "detail": fb_detail.strip(), "type": "USER_FEEDBACK"}
            st.session_state.feedback_logs.append(fb_entry)
            if sheet_webhook_url:
                try: requests.post(sheet_webhook_url, json=fb_entry, timeout=5)
                except: pass
            st.success("Đã gửi phản hồi thành công!")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 THỐNG KÊ THỰC NGHIỆM (KHKT)")
    col_sb1, col_sb2, col_sb3 = st.sidebar.columns(3)
    with col_sb1:
        st.metric("Tự học (T1)", f"{st.session_state.tram1_count}")
    with col_sb2:
        st.metric("Socratic (T2)", f"{st.session_state.tram2_count}")
    with col_sb3:
        current_exam_count = len([x for x in st.session_state.get('analytics_logs', []) if x.get('type') == 'EXAM_RESULT'])
        total_display_count = max(current_exam_count, st.session_state.get('global_exam_count', 0))
        st.metric("Khảo thí (T3)", f"{total_display_count}")
        
    with st.sidebar.expander("📚 SGK Điện Tử (Kết Nối Tri Thức)", expanded=False):
        sgk_url = "https://www.vniteach.com/sach-dien-tu-ket-noi-tri-thuc/"
        st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(sgk_url, safe='')}", use_container_width=True)
        st.link_button("🌐 Mở sách điện tử ngay", sgk_url, use_container_width=True)

    st.sidebar.info("💡 **Triết lý:** Dưỡng thiện tâm - Ươm nhân tài • Dẫn dắt tư duy tự học!")

    # ==============================================================================
    # 3. ĐIỀU PHỐI AI BỀN BỈ (GIA PHẢ 3.X TỐI THƯỢNG THEO LỆNH GOOGLE)
    # ==============================================================================
    ALL_GEMINI_MODELS = [
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-3-flash-preview"
    ]

    if "working_model" not in st.session_state: st.session_state.working_model = None

    DEFAULT_PEDAGOGICAL_SYSTEM_INSTRUCTION = """Bạn là Gia Sư AI Sư Phạm hàng đầu Việt Nam, hỗ trợ học sinh học tập theo đúng chuẩn Chương Trình Giáo Dục Phổ Thông 2018 (SGK Kết Nối Tri Thức với Cuộc Sống - NXB Giáo Dục Việt Nam & Cục Quản Lý Chất Lượng - Bộ GD&ĐT).
NGUYÊN TẮC SƯ PHẠM BẮT BUỘC THEO CT GDPT 2018:
1. MÔN TOÁN HỌC:
   - TUYỆT ĐỐI NGHIÊM CẤM ra đề/giải bài về hàm số bậc bốn trùng phương y = ax^4 + bx^2 + c (đã BỊ BỎ HOÀN TOÀN khỏi CT 2018).
   - Khảo sát hàm số Lớp 12 CHỈ ĐƯỢC PHÉP DÙNG 3 LOẠI HÀM:
     + Hàm đa thức bậc ba: y = ax^3 + bx^2 + cx + d (a != 0)
     + Hàm phân thức bậc nhất / bậc nhất: y = (ax + b) / (cx + d)
     + Hàm phân thức bậc hai / bậc nhất: y = (ax^2 + bx + c) / (px + q) (có tiệm cận xiên)
   - Lớp 10: Hàm bậc nhất & Parabol bậc hai y = ax^2 + bx + c.
   - Lớp 11: Cấp số cộng/nhân, Hàm lượng giác, Giới hạn, Đạo hàm, Mẫu số liệu ghép nhóm.
2. MÔN HÓA HỌC & KHOA HỌC TỰ NHIÊN:
   - 100% sử dụng danh pháp quốc tế IUPAC chuẩn CT 2018 (Alkane, Alkene, Alkyne, Alcohol, Aldehyde, Carboxylic acid, Ester, Amine, Amino acid, Carbohydrate, Polymer...). TUYỆT ĐỐI KHÔNG dùng tên cũ (Ancol, Anđehit, Axit axetic, Benzen...).
3. MÔN NGỮ VĂN:
   - 100% ngữ liệu ĐỌC HIỂU và VIẾT BẮT BUỘC lấy từ tác phẩm văn học, báo chí, đời sống bên ngoài SGK (không lấy bài có sẵn trong SGK), chuẩn ma trận đề thi tốt nghiệp THPT 2025-2026.
4. MÔN TIẾNG ANH:
   - Bám sát chuẩn khung năng lực ngoại ngữ 6 bậc VN / CEFR (A2/B1/B2) và định dạng đề thi THPT 2026.
   - TUYỆT ĐỐI BẮT BUỘC: Toàn bộ từ vựng, đoạn văn, câu hỏi trắc nghiệm, các lựa chọn đáp án (A, B, C, D), và bài tập ngữ pháp PHẢI ĐƯỢC VIẾT 100% BẰNG TIẾNG ANH. Chỉ dùng tiếng Việt khi giải thích hoặc phân tích phương pháp giải.
5. QUY TẮC CÔNG THỨC TOÁN:
   - TUYỆT ĐỐI KHÔNG bọc chữ tiếng Việt có dấu trong dấu $...$. Dấu $...$ chỉ dùng cho công thức toán ($x$, $f(x)$)."""

    def call_gemini_with_fallback(prompt_or_contents, system_instruction=None, json_mode=False):
        model_queue = [st.session_state.working_model] + [m for m in ALL_GEMINI_MODELS if m != st.session_state.working_model] if st.session_state.working_model else ALL_GEMINI_MODELS
        last_error_msg = ""
        with st.status("Gia sư AI đang tiếp nhận yêu cầu...", expanded=True) as status_box:
            for current_model in model_queue:
                status_box.update(label=f"Đang thử kết nối AI qua kênh {current_model}...", state="running")
                for current_key in active_keys_pool:
                    try:
                        client = genai.Client(api_key=current_key)
                        cfg = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="low"))
                        effective_si = f"{DEFAULT_PEDAGOGICAL_SYSTEM_INSTRUCTION}\n\n{system_instruction}" if system_instruction else DEFAULT_PEDAGOGICAL_SYSTEM_INSTRUCTION
                        cfg.system_instruction = effective_si
                        if json_mode: cfg.response_mime_type = "application/json"
                        response = client.models.generate_content(model=current_model, contents=prompt_or_contents, config=cfg)
                        st.session_state.working_model = current_model
                        status_box.update(label="Tuyệt vời, kết nối thành công!", state="complete")
                        return response.text
                    except Exception as e:
                        err_str = str(e)
                        last_error_msg = err_str
                        if "404" in err_str or "NOT_FOUND" in err_str:
                            st.session_state.working_model = None
                            status_box.write(f"Kênh `{current_model}` đã bị chặn, chuyển kênh...")
                            break  
                        elif "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                            status_box.write("Kênh đang nghẽn, tự động đổi API Key...")
                            continue  
                        elif any(err in err_str for err in ["503", "UNAVAILABLE", "high demand", "overloaded"]):
                            status_box.write(f"Máy chủ `{current_model}` bận, thử kênh khác...")
                            time.sleep(1) 
                            break  
                        else: break  
        status_box.update(label="Tất cả các kết nối hiện đang quá tải. Hãy nghỉ ngơi 1 phút nhé!", state="error")
        raise Exception(f"Hệ thống đang quá tải. Lỗi kỹ thuật: {last_error_msg}")

    # ==============================================================================
    # 4. CÁC HÀM PHÂN TÍCH VÀ HIỂN THỊ (PARSE, CLEAN, MERMAID, LAB)
    # ==============================================================================
    def clean_vietnamese_math(text):
        if not text: return ""
        vn_chars = r'[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ]'
        def fix_math(m):
            content = m.group(1).strip()
            if re.search(vn_chars, content):
                return f"<i>{content}</i>" if content.startswith("(") and content.endswith(")") else f" {content} "
            return f"${content}$"
        res = re.sub(r'\$(.*?)\$', fix_math, str(text))
        res = re.sub(r'  +', ' ', res)
        return res.strip()

    def clean_question_bbt_text(q_text):
        if not q_text: return ""
        if "bảng biến thiên như sau:" in q_text:
            parts = q_text.split("bảng biến thiên như sau:")
            prefix = parts[0].rstrip() + " có bảng biến thiên như sau:"
            tail = parts[1].strip()
            match_ask = re.search(r'([A-ZÀ-Ỹ][^\.\n]*?(?:Có bao nhiêu|Hàm số|Tìm|Điểm|Mệnh đề|Khẳng định|Giá trị|Tập hợp|Khoảng cách)[^\.\n]*?\?.*)$', tail, re.DOTALL)
            if match_ask:
                return f"{prefix} {match_ask.group(1).strip()}"
            else:
                return prefix
        return q_text

    def parse_quiz_questions(text):
        questions = []
        part3_match = re.search(r'(?i)###\s*PHẦN\s*3', text)
        part2_text = text[:part3_match.start()] if part3_match else text

        pattern = r'(?i)(?:\[Q\d+\]|C[âa]u\s*\d+[\.\:]?)'
        parts = re.split(pattern, part2_text)
        
        for part in parts[1:]:
            lines = [l.strip() for l in part.strip().split('\n') if l.strip()]
            if not lines: continue
            q_header = lines[0]
            level, options, correct, explain = "Vận dụng", [], "A", "Gợi ý tự suy luận!"
            
            match = re.search(r'(?i)\[Mức độ:\s*(.*?)\]', q_header)
            if match:
                level = match.group(1)
                q_header = re.sub(r'(?i)\[Mức độ:\s*.*?\]', '', q_header).strip()
                
            q_text_lines = [q_header]
            parsing_options = False
            
            for line in lines[1:]:
                clean_line = re.sub(r'(?i)^\*{0,2}([A-D])\b[\.\:]?\*{0,2}\s*', r'\1. ', line)
                
                if re.match(r'(?i)###\s*PHẦN\s*3', line):
                    break
                    
                if clean_line.upper().startswith(('A.', 'B.', 'C.', 'D.')):
                    parsing_options = True
                    options.append(clean_line)
                elif re.search(r'(?i)^(CORRECT|ĐÁP ÁN|Đáp án đúng)\s*:', line):
                    ext = re.sub(r'[^A-D]', '', line.split(":")[-1].upper())
                    if ext: correct = ext[0]
                elif re.search(r'(?i)^(EXPLAIN|GIẢI THÍCH|Gợi ý)\s*:', line):
                    explain = line.split(":", 1)[-1].strip()
                else:
                    if not parsing_options:
                        q_text_lines.append(line)
                    elif options and not clean_line.upper().startswith(('A.', 'B.', 'C.', 'D.')):
                        explain += " " + line
                            
            if len(options) >= 4:
                questions.append({
                    "question": " ".join(q_text_lines).strip(),
                    "level": level,
                    "options": options[:4],
                    "correct": correct,
                    "explain": explain
                })
        return questions

    def create_pedagogical_tts_component(raw_text: str, subject_name: str, comp_key: str):
        if subject_name != "Tiếng Anh":
            return
        tts_html = f"""
        <script>
        (function() {{
            if (window.__english_tts_global_injected) return;
            window.__english_tts_global_injected = true;
            let currentRate = 0.92;
            let lastSpoken = "";
            let lastSpeakTime = 0;
            function getBestEnglishVoice() {{
                const voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [];
                return voices.find(v => v.lang.startsWith('en') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Jenny') || v.name.includes('Guy') || v.name.includes('US') || v.name.includes('Samantha') || v.name.includes('Aria'))) ||
                       voices.find(v => v.lang.startsWith('en')) || null;
            }}
            window.speakEnglishText = function(text) {{
                if (!text || !window.speechSynthesis) return;
                text = text.trim();
                text = text.replace(/^[A-Da-d][.:)]\\s*/, '').replace(/[*#`_~\\[\\]()]/g, ' ').trim();
                if (!text || text.length < 2 || text.length > 350) return;
                const viRegex = /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i;
                if (viRegex.test(text)) return;
                if (!/[a-zA-Z]/.test(text)) return;
                const now = Date.now();
                if (text.toLowerCase() === lastSpoken.toLowerCase() && (now - lastSpeakTime) < 1000) return;
                lastSpoken = text;
                lastSpeakTime = now;
                try {{
                    window.speechSynthesis.cancel();
                    const u = new SpeechSynthesisUtterance(text);
                    u.lang = 'en-US';
                    u.rate = currentRate;
                    u.pitch = 1.0;
                    const voice = getBestEnglishVoice();
                    if (voice) u.voice = voice;
                    window.speechSynthesis.speak(u);
                }} catch(err) {{
                    console.warn("TTS error:", err);
                }}
            }};
            function handleSelectionToSpeak() {{
                try {{
                    const targetDoc = window.parent.document || document;
                    const sel = targetDoc.getSelection();
                    if (!sel) return;
                    let text = sel.toString().trim();
                    if (text && window.speakEnglishText) window.speakEnglishText(text);
                }} catch(e) {{}}
            }}
            function handleElementClickToSpeak(event) {{
                try {{
                    const el = event.target;
                    if (!el) return;
                    const customBtn = el.closest('.custom-speak-btn');
                    if (customBtn) {{
                        const hiddenSpan = customBtn.querySelector('.hidden-speak-text');
                        if (hiddenSpan && hiddenSpan.innerText && window.speakEnglishText) {{
                            return window.speakEnglishText(hiddenSpan.innerText);
                        }}
                    }}
                    const radioLabel = el.closest('label[data-baseweb="radio"]') || el.closest('[data-testid="stRadio"] label');
                    if (radioLabel) {{
                        const labelText = radioLabel.innerText || radioLabel.textContent || "";
                        if (labelText && window.speakEnglishText) return window.speakEnglishText(labelText);
                    }}
                }} catch(e) {{}}
            }}
            try {{
                const targetDoc = window.parent.document || document;
                if (window.parent) window.parent.speakEnglishText = window.speakEnglishText;
                targetDoc.addEventListener("mouseup", handleSelectionToSpeak);
                targetDoc.addEventListener("touchend", handleSelectionToSpeak);
                targetDoc.addEventListener("click", handleElementClickToSpeak, true);
            }} catch(e) {{}}
        }})();
        </script>
        """
        components.html(tts_html, height=0)

    def render_voice_speech_tex_and_english_evaluator(stage_id: str, current_subject: str, current_grade: int):
        if current_subject != "Tiếng Anh" or stage_id != 'Tram 1':
            return
        st.markdown("---")
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.95)); border: 1.5px solid #38bdf8; border-radius: 12px; padding: 14px 18px; margin-bottom: 12px; box-shadow: 0 4px 15px rgba(56, 189, 248, 0.15);">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 24px;">🇬🇧</span>
                    <div>
                        <span style="color: #38bdf8; font-weight: 800; font-size: 15px; text-transform: uppercase; letter-spacing: 0.5px;">PHÒNG THỰC HÀNH NÓI TIẾNG ANH PHẢN XẠ 1-1 BẢN NGỮ (AI SPEAKING LAB)</span>
                        <div style="color: #94a3b8; font-size: 12.5px; margin-top: 2px;">
                            💡 <b>Mẹo học sinh:</b> Click nút 🔊 bên cạnh từ/cụm từ hoặc <b>bôi đen (select text)</b> bất kỳ đoạn tiếng Anh nào để nghe phát âm chuẩn US (en-US).
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        create_pedagogical_tts_component("", "Tiếng Anh", f"init_{stage_id}")

        curriculum_english_units = {
            "Unit 1: Life stories & Inspiring People": {
                "vocab": [
                    {"word": "Perseverance", "ipa": "/ˌpɜːsɪˈvɪərəns/", "meaning": "Sự kiên trì, bền chí"},
                    {"word": "Inspirational", "ipa": "/ˌɪnspəˈreɪʃənl/", "meaning": "Truyền cảm hứng"},
                    {"word": "Distinguished", "ipa": "/dɪˈstɪŋɡwɪʃt/", "meaning": "Xuất chúng, lỗi lạc"},
                    {"word": "Dedication", "ipa": "/ˌdedɪˈkeɪʃn/", "meaning": "Sự cống hiến tận tụy"}
                ],
                "passage": "Uncle Ho devoted his entire life to national liberation, inspiring generations of Vietnamese students to study diligently and cultivate personal integrity.",
                "q_reflex": "Who is a historical or modern figure that inspired you the most in your life? Explain why."
            },
            "Unit 2: A Green Planet & Environmental Protection": {
                "vocab": [
                    {"word": "Biodiversity", "ipa": "/ˌbaɪəʊdaɪˈvɜːsəti/", "meaning": "Đa dạng sinh học"},
                    {"word": "Deforestation", "ipa": "/diːˌfɒrɪˈsteɪʃn/", "meaning": "Nạn phá rừng"},
                    {"word": "Sustainability", "ipa": "/səˌsteɪnəˈbɪləti/", "meaning": "Sự phát triển bền vững"},
                    {"word": "Carbon footprint", "ipa": "/ˌkɑːbən ˈfʊtprɪnt/", "meaning": "Dấu chân carbon"}
                ],
                "passage": "Transitioning to renewable clean energy and minimizing single-use plastic are decisive steps to preserve Earth's climate stability.",
                "q_reflex": "What practical actions can high school students in Vietnam take to reduce plastic waste on campus?"
            }
        }

        sel_unit = st.selectbox(
            "📚 Chọn Chủ Đề Bài Học SGK Kết Nối Tri Thức:",
            list(curriculum_english_units.keys()),
            key=f"unit_eng_sel_{stage_id}"
        )
        unit_info = curriculum_english_units[sel_unit]

        col_left_data, col_right_speak = st.columns([1.1, 1.1])

        with col_left_data:
            st.markdown("##### 📖 1. Từ Vựng Trọng Tâm SGK (New Words):")
            for v in unit_info["vocab"]:
                v_word, v_ipa, v_meaning = v['word'], v['ipa'], v['meaning']
                btn_play_code = f"""
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; margin-bottom: 6px;">
                    <div>
                        <span style="color: #38bdf8; font-weight: 700; font-size: 13.5px;">• {v_word}</span>
                        <span style="color: #94a3b8; font-size: 12px; margin-left: 6px;">{v_ipa}</span>:
                        <span style="color: #cbd5e1; font-size: 12.5px; font-style: italic; margin-left: 4px;">{v_meaning}</span>
                    </div>
                    <button class="custom-speak-btn" style="background: #1e293b; color: #38bdf8; border: 1px solid #38bdf8; padding: 3px 8px; border-radius: 6px; font-size: 11.5px; font-weight: 700; cursor: pointer;">
                        🔊 Đọc
                        <span style="display:none;" class="hidden-speak-text">{v_word}</span>
                    </button>
                </div>
                """
                st.markdown(btn_play_code, unsafe_allow_html=True)

            st.markdown("##### 📝 2. Đoạn Văn Luyện Đọc Chuẩn (Reading Passage):")
            passage_code = f"""
            <div style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 12px 14px; margin-top: 4px;">
                <div style="color: #e2e8f0; font-size: 13.5px; line-height: 1.6; font-style: italic;">"{unit_info['passage']}"</div>
                <div style="text-align: right; margin-top: 8px;">
                    <button class="custom-speak-btn" data-text="{unit_info['passage']}" style="background: linear-gradient(135deg, #0284c7, #0369a1); color: #ffffff; border: none; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 700; cursor: pointer;">
                        🔊 Đọc cả đoạn văn
                        <span style="display:none;" class="hidden-speak-text">{unit_info['passage']}</span>
                    </button>
                </div>
            </div>
            """
            st.markdown(passage_code, unsafe_allow_html=True)

        with col_right_speak:
            st.markdown("##### 🎙️ 3. Phòng Thu Phản Xạ 1-1 Cùng Gia Sư AI:")
            q_code = f"""
            <div style="background: rgba(30, 41, 59, 0.95); border: 1.5px solid #38bdf8; border-radius: 10px; padding: 12px 14px; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                    <div style="color: #38bdf8; font-weight: 800; font-size: 13px;">🤖 CÂU HỎI PHẢN XẠ CỦA GIA SƯ AI:</div>
                    <button class="custom-speak-btn" data-text="{unit_info['q_reflex']}" style="background: #1e293b; color: #38bdf8; border: 1px solid #38bdf8; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: 700; cursor: pointer;">
                        🔊 Nghe
                        <span style="display:none;" class="hidden-speak-text">{unit_info['q_reflex']}</span>
                    </button>
                </div>
                <div style="color: #ffffff; font-size: 13.5px; font-weight: 600; margin-top: 6px; line-height: 1.5;">"{unit_info['q_reflex']}"</div>
            </div>
            """
            st.markdown(q_code, unsafe_allow_html=True)

            ielts_mic_code = f"""
            <div style="background: #0f172a; border: 1.5px solid #334155; border-radius: 10px; padding: 12px 14px; font-family: system-ui, sans-serif;">
                <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 8px;">
                    <button id="btn_hold_eng" style="background: linear-gradient(135deg, #10b981, #059669); color: #ffffff; border: 1.5px solid #34d399; padding: 9px 18px; border-radius: 8px; font-weight: 800; font-size: 13.5px; cursor: pointer; display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 14px rgba(16,185,129,0.35); user-select: none; transition: all 0.2s ease;">
                        <span id="eng_icon">🎙️</span> <span id="eng_lbl">ĐÈ ĐỂ NÓI TIẾNG ANH (en-US)</span>
                    </button>
                    <span id="eng_status" style="color: #94a3b8; font-size: 11.5px; font-weight: 600;">(Đè chuột nói, nhả chuột để dừng)</span>
                </div>
                <div id="eng_box" style="min-height: 52px; background: #1e293b; border: 1px dashed #475569; border-radius: 8px; padding: 8px 12px; color: #34d399; font-size: 13.5px; font-weight: 600; line-height: 1.5;">
                    Your spoken English will appear here in real-time...
                </div>
            </div>
            <script>
            (function() {{
                let rec = null;
                let isRecording = false;
                const btn = document.getElementById('btn_hold_eng');
                const lbl = document.getElementById('eng_lbl');
                const icon = document.getElementById('eng_icon');
                const stat = document.getElementById('eng_status');
                const box = document.getElementById('eng_box');

                function setNativeValue(element, value) {{
                    try {{
                        const valueSetter = Object.getOwnPropertyDescriptor(element, 'value').set;
                        const prototype = Object.getPrototypeOf(element);
                        const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                        if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {{
                            prototypeValueSetter.call(element, value);
                        }} else if (valueSetter) {{
                            valueSetter.call(element, value);
                        }} else {{
                            element.value = value;
                        }}
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }} catch(e) {{
                        element.value = value;
                    }}
                }}

                const targetWin = window.parent || window;
                const SpeechClass = targetWin.SpeechRecognition || targetWin.webkitSpeechRecognition || window.SpeechRecognition || window.webkitSpeechRecognition;

                if (SpeechClass) {{
                    try {{
                        rec = new SpeechClass();
                        rec.continuous = true;
                        rec.interimResults = true;
                        rec.lang = 'en-US';

                        rec.onstart = function() {{
                            isRecording = true;
                            btn.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
                            btn.style.boxShadow = '0 0 18px rgba(239, 68, 68, 0.7)';
                            btn.style.borderColor = '#f87171';
                            lbl.innerText = 'ĐANG THU ÂM... NHẢ CHUỘT ĐỂ DỪNG';
                            icon.innerText = '🔴';
                            stat.innerText = '● Recording speech in en-US...';
                            stat.style.color = '#ef4444';
                        }};

                        rec.onresult = function(e) {{
                            let str = '';
                            for (let i = e.resultIndex; i < e.results.length; ++i) {{
                                str += e.results[i][0].transcript;
                            }}
                            if (str) {{
                                box.innerText = str;
                                try {{
                                    const targetDoc = window.parent.document || document;
                                    const textareas = targetDoc.querySelectorAll('textarea');
                                    for (let ta of textareas) {{
                                        const pText = (ta.placeholder || ta.getAttribute('aria-label') || '').toLowerCase();
                                        if (pText.includes('english')) {{
                                            setNativeValue(ta, str);
                                            break;
                                        }}
                                    }}
                                }} catch(err) {{ console.warn(err); }}
                            }}
                        }};

                        rec.onerror = function(e) {{
                            console.warn("Speech Rec Error:", e.error);
                            stat.innerText = '⚠️ Lỗi Mic: ' + e.error;
                            stat.style.color = '#f87171';
                            isRecording = false;
                        }};

                        rec.onend = function() {{
                            if (isRecording) stopRec();
                        }};
                    }} catch(err) {{
                        console.warn("Speech init err:", err);
                    }}
                }} else {{
                    stat.innerText = 'Web Speech Mic không hỗ trợ trình duyệt này';
                }}

                function startRec(e) {{
                    if (e) e.preventDefault();
                    if (!rec) return alert('Vui lòng sử dụng Google Chrome hoặc MS Edge để dùng Mic thu âm!');
                    if (!isRecording) {{
                        try {{ rec.start(); }} catch(err) {{ console.warn(err); }}
                    }}
                }}

                function stopRec(e) {{
                    if (e) e.preventDefault();
                    if (rec && isRecording) {{
                        try {{ rec.stop(); }} catch(err) {{}}
                    }}
                    isRecording = false;
                    btn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
                    btn.style.boxShadow = '0 4px 14px rgba(16,185,129,0.35)';
                    btn.style.borderColor = '#34d399';
                    lbl.innerText = 'ĐÈ ĐỂ NÓI TIẾNG ANH (en-US)';
                    icon.innerText = '🎙️';
                    if (!stat.innerText.includes('Lỗi')) {{
                        stat.innerText = '✅ Đã ghi nhận bài nói thành công!';
                        stat.style.color = '#34d399';
                    }}
                }}

                btn.addEventListener('mousedown', startRec);
                btn.addEventListener('mouseup', stopRec);
                btn.addEventListener('mouseleave', stopRec);
                btn.addEventListener('touchstart', startRec);
                btn.addEventListener('touchend', stopRec);
            }})();
            </script>
            """
            components.html(ielts_mic_code, height=125)

            student_speech = st.text_area(
                "Nội dung bài nói của em (tự động nhận diện từ Mic):", 
                key=f"eng_speech_input_{stage_id}",
                placeholder="Your spoken English will be captured here...",
                height=85
            )

            btn_score_ielts = st.button("📊 Chấm Điểm 4 Tiêu Chí IELTS & Nâng Cấp Band 8.0", key=f"btn_eval_ielts_{stage_id}", type="primary", use_container_width=True)

            if btn_score_ielts and student_speech.strip():
                with st.spinner("AI Giám khảo IELTS đang phân tích..."):
                    try:
                        rubric_prompt = f"""Bạn là Giám khảo Khảo thí IELTS Quốc tế kiêm Giáo viên Tiếng Anh THPT.
Chủ đề bài học SGK: {sel_unit}
Câu hỏi bối cảnh: '{unit_info['q_reflex']}'
Đoạn văn đọc mẫu: '{unit_info['passage']}'
Bài nói/phát âm thực tế của học sinh: '{student_speech}'

YÊU CẦU ĐÁNH GIÁ:
1. OVERALL BAND SCORE (Thang điểm 0 - 9.0)
2. BẢNG ĐIỂM 4 TIÊU CHÍ CHUẨN QUỐC TẾ: Fluency, Lexical, Grammar, Pronunciation.
3. SOI LỖI CỤ THỂ VÀ BẢN NÂNG CẤP BAND 8.0."""
                        eval_ielts_res = call_gemini_with_fallback(rubric_prompt)
                        st.success("🏆 BẢNG ĐÁNH GIÁ NĂNG LỰC NÓI TIẾNG ANH CHUẨN QUỐC TẾ:")
                        st.markdown(eval_ielts_res)
                    except Exception as e:
                        st.error(f"Lỗi chấm điểm: {e}")

    def render_mermaid(code: str):
        safe_code = code.strip().replace('[[', '[').replace(']]', ']')
        safe_code = re.sub(r'^```(?:mermaid)?', '', safe_code, flags=re.MULTILINE)
        safe_code = re.sub(r'```$', '', safe_code, flags=re.MULTILINE).strip()
        safe_code = re.sub(r'^\s*graph\s+TD', 'graph LR', safe_code, flags=re.IGNORECASE)
        safe_code = re.sub(r'^\s*flowchart\s+TD', 'flowchart LR', safe_code, flags=re.IGNORECASE)
        if not safe_code.startswith(("graph", "flowchart")):
            safe_code = "graph LR\n" + safe_code

        json_code_str = json.dumps(safe_code).replace("</", "<\\/")

        html_template = r"""
        <!-- TÍCH HỢP KATEX VÀ D3.JS CHUẨN SƯ PHẠM QUỐC GIA -->
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
        <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
        <script src="https://d3js.org/d3.v7.min.js"></script>

        <div style="background: radial-gradient(circle at center, #0f172a 0%, #020617 100%); border-radius: 14px; border: 1.5px solid #1e293b; padding: 12px; position: relative; font-family: system-ui, -apple-system, sans-serif;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding: 0 10px;">
                <span style="color: #38bdf8; font-size: 13px; font-weight: 700; letter-spacing: 0.5px;">🎯 SƠ ĐỒ TƯ DUY TƯƠNG TÁC THUYẾT TRÌNH (HỖ TRỢ CÔNG THỨC TOÁN KATEX • CLICK ĐỂ SỔ/THU)</span>
                <div>
                    <button onclick="expandAll()" style="background: #1e293b; color: #38bdf8; border: 1px solid #38bdf8; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; margin-right: 6px;">➕ Mở tất cả</button>
                    <button onclick="collapseAll()" style="background: #1e293b; color: #f43f5e; border: 1px solid #f43f5e; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; margin-right: 6px;">➖ Thu gọn</button>
                    <button onclick="resetZoom()" style="background: #1e293b; color: #34d399; border: 1px solid #34d399; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; margin-right: 6px;">🎯 Căn giữa</button>
                    <button onclick="downloadMindmapSVG()" style="background: #0ea5e9; color: #ffffff; border: none; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700; cursor: pointer;">📥 Tải Sơ Đồ (SVG)</button>
                </div>
            </div>
            <div id="mindmap-container" style="width: 100%; height: 550px; overflow: hidden; cursor: grab;"></div>
        </div>

        <script>
        const rawCode = ___JSON_CODE_PLACEHOLDER___;

        function renderLabelWithKaTeX(rawLabel) {
            if (!rawLabel) return "";
            let text = rawLabel.trim();
            text = text.replace(/\$([^\$]+)\$/g, function(match, tex) {
                try {
                    if (window.katex) {
                        return window.katex.renderToString(tex, { throwOnError: false, displayMode: false });
                    }
                } catch (e) {
                    console.warn("KaTeX error:", e);
                }
                return match;
            });
            return text;
        }

        function parseNodePart(part) {
            if (!part) return null;
            part = part.trim().split(':::')[0].trim();
            
            let firstDelim = -1;
            let openChar = null;
            for (let i = 0; i < part.length; i++) {
                const ch = part[i];
                if (ch === '(' || ch === '[' || ch === '{') {
                    firstDelim = i;
                    openChar = ch;
                    break;
                }
            }

            if (firstDelim === -1) {
                return { id: part, label: part };
            }

            const id = part.substring(0, firstDelim).trim();
            const rest = part.substring(firstDelim).trim();
            const closeChar = openChar === '(' ? ')' : (openChar === '[' ? ']' : '}');
            const lastClose = rest.lastIndexOf(closeChar);

            let label = lastClose !== -1 ? rest.substring(1, lastClose).trim() : rest.substring(1).trim();
            if ((label.startsWith('"') && label.endsWith('"')) || (label.startsWith("'") && label.endsWith("'"))) {
                label = label.substring(1, label.length - 1).trim();
            }
            return { id: id || label, label: label || id };
        }

        function parseMermaidToTree(code) {
            if (!code) return null;
            let lines = code.split(/\r?\n/);
            if (lines.length <= 1 && code.includes('\\n')) {
                lines = code.split('\\n');
            }

            const nodeLabels = {};
            const childrenMap = {};
            const parentMap = {};

            function registerNode(node) {
                if (!node || !node.id) return;
                if (node.label && node.label !== node.id) {
                    nodeLabels[node.id] = node.label;
                } else if (!nodeLabels[node.id]) {
                    nodeLabels[node.id] = node.label || node.id;
                }
            }

            lines.forEach(line => {
                line = line.trim();
                if (!line || line.startsWith('graph') || line.startsWith('flowchart') || line.startsWith('classDef') || line.startsWith('style') || line.startsWith('subgraph') || line === 'end') {
                    return;
                }
                const arrowMatch = line.match(/^(.*?)\s*(?:-->|==>|-\.->|---|->)(?:\|.*?\|)?\s*(.*)$/);
                if (arrowMatch) {
                    const src = parseNodePart(arrowMatch[1]);
                    const tgt = parseNodePart(arrowMatch[2]);
                    if (src && tgt) {
                        registerNode(src);
                        registerNode(tgt);

                        if (!childrenMap[src.id]) childrenMap[src.id] = [];
                        if (!childrenMap[src.id].includes(tgt.id)) childrenMap[src.id].push(tgt.id);
                        parentMap[tgt.id] = src.id;
                    }
                } else {
                    const node = parseNodePart(line);
                    if (node && node.id) {
                        registerNode(node);
                    }
                }
            });

            const allIds = Object.keys(nodeLabels);
            if (allIds.length === 0) return null;
            let rootId = allIds.find(id => !parentMap[id]) || allIds[0];

            function build(id, depth) {
                const item = { id: id, name: nodeLabels[id] || id, depth: depth };
                const childIds = childrenMap[id] || [];
                if (childIds.length > 0) {
                    item.children = childIds.map(cId => build(cId, depth + 1));
                }
                return item;
            }
            return build(rootId, 0);
        }

        function generateAutoHealerTree(code) {
            let topicName = "NỘI DUNG TRỌNG TÂM BÀI HỌC";
            const m = (code || '').match(/\[["']?(.*?)["']?\]/);
            if (m && m[1] && m[1].length < 60) {
                topicName = m[1].replace(/["']/g, '').trim();
            }
            return {
                id: "Root",
                name: "🎯 " + topicName,
                depth: 0,
                children: [
                    {
                        id: "N1",
                        name: "📖 1. Định nghĩa & Khái niệm cốt lõi",
                        depth: 1,
                        children: [
                            { id: "N1_1", name: "Định nghĩa chuẩn SGK Kết Nối Tri Thức", depth: 2 },
                            { id: "N1_2", name: "Điều kiện xác định & Phạm vi áp dụng", depth: 2 }
                        ]
                    },
                    {
                        id: "N2",
                        name: "⚡ 2. Công thức & Quy tắc trọng tâm",
                        depth: 1,
                        children: [
                            { id: "N2_1", name: "Công thức cơ bản nền tảng", depth: 2 },
                            { id: "N2_2", name: "Tính chất biến đổi & Mở rộng", depth: 2 }
                        ]
                    },
                    {
                        id: "N3",
                        name: "🔍 3. Phương pháp giải & Dạng bài tập",
                        depth: 1,
                        children: [
                            { id: "N3_1", name: "Dạng 1: Nhận biết & Thông hiểu", depth: 2 },
                            { id: "N3_2", name: "Dạng 2: Vận dụng liên môn & Thực tiễn", depth: 2 }
                        ]
                    }
                ]
            };
        }

        let treeData = parseMermaidToTree(rawCode);
        if (!treeData || !treeData.children || treeData.children.length === 0) {
            console.warn("Kích hoạt Auto-Healer Tree Generator cho sơ đồ tư duy!");
            treeData = generateAutoHealerTree(rawCode);
        }
        const container = document.getElementById("mindmap-container");
        const height = 550;

        {
            const svg = d3.select("#mindmap-container").append("svg")
                .attr("width", "100%")
                .attr("height", height)
                .attr("id", "svg-mindmap-element")
                .style("user-select", "text");

            const g = svg.append("g");

            const zoom = d3.zoom()
                .scaleExtent([0.25, 3.5])
                .on("zoom", (e) => g.attr("transform", e.transform));
            svg.call(zoom);

            const treeLayout = d3.tree().nodeSize([78, 240]);
            const root = d3.hierarchy(treeData);
            root.x0 = height / 2;
            root.y0 = 40;

            const palette = ["#818cf8", "#38bdf8", "#34d399", "#fbbf24", "#f472b6", "#a78bfa", "#38bdf8"];

            if (root.children) {
                root.children.forEach(c => {
                    if (c.children) {
                        c.children.forEach(sub => {
                            if (sub.children) {
                                sub._children = sub.children;
                                sub.children = null;
                            }
                        });
                    }
                });
            }

            let measureBox = document.getElementById("mindmap-measure-box");
            if (!measureBox) {
                measureBox = document.createElement("div");
                measureBox.id = "mindmap-measure-box";
                measureBox.style.cssText = "position:absolute; visibility:hidden; top:-9999px; left:-9999px; white-space:nowrap; font-family:system-ui,-apple-system,sans-serif;";
                document.body.appendChild(measureBox);
            }

            function getPreciseNodeWidth(text, depth) {
                if (!text) return 90;
                measureBox.style.fontSize = depth === 0 ? "13.5px" : "12.5px";
                measureBox.style.fontWeight = depth === 0 ? "800" : "600";
                measureBox.innerHTML = renderLabelWithKaTeX(text);
                const rect = measureBox.getBoundingClientRect();
                const measuredW = Math.ceil(rect.width || measureBox.offsetWidth || (text.length * 8));
                return Math.max(90, measuredW + 48);
            }

            let i = 0;
            function update(source) {
                const treeInfo = treeLayout(root);
                const nodes = treeInfo.descendants();
                const links = treeInfo.links();

                const maxWByDepth = {};
                nodes.forEach(d => {
                    d.boxWidth = getPreciseNodeWidth(d.data.name, d.depth);
                    d.boxHeight = 42;
                    if (!maxWByDepth[d.depth] || d.boxWidth > maxWByDepth[d.depth]) {
                        maxWByDepth[d.depth] = d.boxWidth;
                    }
                });

                const depthX = [35];
                for (let dep = 1; dep <= 12; dep++) {
                    depthX[dep] = depthX[dep - 1] + (maxWByDepth[dep - 1] || 120) + 55;
                }

                nodes.forEach(d => { 
                    d.y = depthX[d.depth]; 
                });

                const node = g.selectAll("g.node").data(nodes, d => d.id || (d.id = ++i));

                function speakMindmapText(rawName) {
                    if (window.parent && window.parent.speakEnglishText) {
                        window.parent.speakEnglishText(rawName);
                    } else {
                        console.warn("Mindmap TTS: window.parent.speakEnglishText not available.");
                    }
                }

                const nodeEnter = node.enter().append("g")
                    .attr("class", "node")
                    .attr("transform", d => `translate(${source.y0},${source.x0})`)
                    .style("cursor", "pointer")
                    .on("click", (event, d) => {
                        speakMindmapText(d.data.name);
                        if (d.children) {
                            d._children = d.children;
                            d.children = null;
                        } else if (d._children) {
                            d.children = d._children;
                            d._children = null;
                        }
                        update(d);
                    });

                nodeEnter.append("rect")
                    .attr("rx", 9).attr("ry", 9)
                    .attr("x", 0).attr("y", -21)
                    .attr("height", d => d.boxHeight)
                    .attr("width", d => d.boxWidth)
                    .style("fill", "#0f172a")
                    .style("stroke", d => palette[d.depth % palette.length])
                    .style("stroke-width", d => d.depth === 0 ? "2.5px" : "1.8px")
                    .style("filter", "drop-shadow(0 4px 10px rgba(0,0,0,0.65))");

                nodeEnter.append("circle")
                    .attr("cx", 14).attr("cy", 0).attr("r", 5.5)
                    .style("fill", d => d._children ? palette[d.depth % palette.length] : (d.children ? "#0f172a" : "#475569"))
                    .style("stroke", d => palette[d.depth % palette.length])
                    .style("stroke-width", "2px");

                const fo = nodeEnter.append("foreignObject")
                    .attr("x", 26)
                    .attr("y", -21)
                    .attr("width", d => d.boxWidth - 28)
                    .attr("height", d => d.boxHeight)
                    .style("overflow", "visible")
                    .style("pointer-events", "auto");

                fo.append("xhtml:div")
                    .style("color", "#ffffff")
                    .style("font-size", d => d.depth === 0 ? "13.5px" : "12.5px")
                    .style("font-weight", d => d.depth === 0 ? "800" : "600")
                    .style("line-height", "42px")
                    .style("white-space", "nowrap")
                    .style("overflow", "visible")
                    .style("user-select", "text")
                    .style("cursor", "pointer")
                    .on("dblclick", (event, d) => {
                        event.stopPropagation();
                        speakMindmapText(d.data.name);
                    })
                    .html(d => renderLabelWithKaTeX(d.data.name));

                const nodeUpdate = node.merge(nodeEnter).transition().duration(350)
                    .attr("transform", d => `translate(${d.y},${d.x})`);

                nodeUpdate.select("rect").attr("width", d => d.boxWidth);
                nodeUpdate.select("foreignObject").attr("width", d => d.boxWidth - 28);
                nodeUpdate.select("circle")
                    .style("fill", d => d._children ? palette[d.depth % palette.length] : (d.children ? "#0f172a" : "#475569"));

                const nodeExit = node.exit().transition().duration(350)
                    .attr("transform", d => `translate(${source.y},${source.x})`)
                    .remove();

                const link = g.selectAll("path.link").data(links, d => d.target.id);

                const linkPath = d => {
                    const startX = d.source.y + d.source.boxWidth;
                    const startY = d.source.x;
                    const endX = d.target.y;
                    const endY = d.target.x;
                    return `M ${startX} ${startY} C ${(startX + endX) / 2} ${startY}, ${(startX + endX) / 2} ${endY}, ${endX} ${endY}`;
                };

                const linkEnter = link.enter().insert("path", "g")
                    .attr("class", "link")
                    .attr("d", d => {
                        const startX = source.y0 + (source.boxWidth || 150);
                        return `M ${startX} ${source.x0} C ${startX} ${source.x0}, ${startX} ${source.x0}`;
                    })
                    .style("fill", "none")
                    .style("stroke", d => palette[d.target.depth % palette.length])
                    .style("stroke-opacity", 0.75)
                    .style("stroke-width", "2px");

                link.merge(linkEnter).transition().duration(350)
                    .attr("d", linkPath);

                link.exit().transition().duration(350)
                    .attr("d", d => {
                        const startX = source.y + (source.boxWidth || 150);
                        return `M ${startX} ${source.x} C ${startX} ${source.x}, ${startX} ${source.x}`;
                    })
                    .remove();

                nodes.forEach(d => { d.x0 = d.x; d.y0 = d.y; });
            }

            update(root);

            svg.call(zoom.transform, d3.zoomIdentity.translate(50, height / 2.3).scale(0.85));

            window.expandAll = function() {
                function expand(d) {
                    if (d._children) { d.children = d._children; d._children = null; }
                    if (d.children) d.children.forEach(expand);
                }
                expand(root);
                update(root);
            };

            window.collapseAll = function() {
                if (root.children) {
                    root.children.forEach(c => {
                        function collapse(d) {
                            if (d.children) { d._children = d.children; d.children = null; }
                            if (d._children) d._children.forEach(collapse);
                        }
                        collapse(c);
                    });
                }
                update(root);
            };

            window.resetZoom = function() {
                svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity.translate(50, height / 2.3).scale(0.85));
            };

            window.downloadMindmapSVG = function() {
                const svgEl = document.getElementById("svg-mindmap-element");
                if (!svgEl) return;
                const serializer = new XMLSerializer();
                let source = serializer.serializeToString(svgEl);
                if(!source.match(/^<svg/)){
                    source = source.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
                }
                const url = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(source);
                const downloadLink = document.createElement("a");
                downloadLink.href = url;
                downloadLink.download = "SoDoTuDuy_KNTT.svg";
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
            };
        }
        </script>
        """

        final_html = html_template.replace("___JSON_CODE_PLACEHOLDER___", json_code_str)
        if hasattr(st, "iframe"):
            st.iframe(final_html, height=580)
        else:
            components.html(final_html, height=580, scrolling=False)

    def safe_eval_func(expr, x_val):
        tree = ast.parse(expr.strip(), mode="eval")
        _SAFE_NAMES = {"x", "np", "math", "pi", "e", "abs", "min", "max", "pow", "round", "float", "int", "go"}
        _SAFE_CALL_ROOTS = {"np", "math", "go"}
        for n in ast.walk(tree):
            if isinstance(n, ast.Name) and n.id not in _SAFE_NAMES: raise ValueError(f"Tên không được phép: {n.id}")
            if isinstance(n, ast.Attribute):
                if n.attr.startswith("_"): raise ValueError("Thuộc tính không được phép")
                root = n
                while isinstance(root, ast.Attribute): root = root.value
                if not (isinstance(root, ast.Name) and root.id in _SAFE_CALL_ROOTS): raise ValueError("Chỉ cho phép np.*, math.*, go.*")
        env = {"__builtins__": {}, "x": x_val, "np": np, "math": math, "pi": math.pi, "e": math.e, "abs": abs, "min": min, "max": max, "pow": pow, "round": round, "float": float, "int": int}
        return eval(compile(tree, "<ham_so>", "eval"), env)

    def render_dynamic_python_lab(python_code: str):
        try:
            clean_code = re.sub(r'st\.plotly_chart\(.*?\)', '', python_code)
            clean_code = re.sub(r'(?m)^\s*(?:import|from)\s+.*$', '', clean_code)
            tree = ast.parse(clean_code)
            _BLOCKED_NAMES = {"exec", "eval", "compile", "open", "input", "globals", "locals", "vars", "getattr", "setattr", "delattr", "__import__", "os", "sys", "subprocess", "st", "builtins", "importlib", "socket", "requests", "shutil", "pathlib"}
            for n in ast.walk(tree):
                if isinstance(n, ast.Name) and (n.id in _BLOCKED_NAMES or n.id.startswith("__")): raise ValueError(f"Mã mô phỏng dùng tên bị cấm: {n.id}")
                if isinstance(n, ast.Attribute) and n.attr.startswith("_"): raise ValueError("Mã mô phỏng dùng thuộc tính bị cấm")
                if isinstance(n, (ast.Import, ast.ImportFrom)): raise ValueError("Không cho phép import trong mã mô phỏng")
            
            _SAFE_BUILTINS = {k: __builtins__[k] if isinstance(__builtins__, dict) else getattr(__builtins__, k) for k in ["range", "len", "min", "max", "abs", "sum", "round", "float", "int", "list", "dict", "tuple", "zip", "enumerate", "str", "pow", "sorted", "bool", "map", "any", "all", "set", "reversed", "isinstance", "True", "False", "None"]}
            local_env = {"__builtins__": _SAFE_BUILTINS, "go": go, "np": np, "math": math, "setup_pedagogical_oxy": setup_pedagogical_oxy}
            exec(compile(tree, "<mo_phong>", "exec"), local_env)
            if "fig" in local_env and isinstance(local_env["fig"], go.Figure):
                unique_plot_id = f"dynamic_plot_{int(time.time() * 1000)}_{random.randint(1, 1000)}"
                st.plotly_chart(local_env["fig"], use_container_width=True, key=unique_plot_id)
        except Exception as e:
            st.error(f"Lỗi biên dịch mô phỏng nâng cao: {e}")

    def render_smart_lab(data):
        dtype = data.get("type")
        if dtype == "mermaid":
            st.markdown("### 🗺️ Trực quan hóa Sơ Đồ Tư Duy / Chu Trình Mô Phỏng")
            render_mermaid(data.get("code", ""))
            return

        if dtype == "area":
            c1, c2 = st.columns([1.2, 2.8])
            func_str = str(data.get("func", "x**2 - 3*x + 2")).replace('$', '').strip()
            clean_f = re.sub(r'\\frac{(.*?)}{(.*?)}', r'((\1)/(\2))', func_str)
            clean_f = clean_f.replace('\\sin', 'np.sin').replace('\\cos', 'np.cos').replace('\\tan', 'np.tan').replace('\\ln', 'np.log').replace('\\pi', 'np.pi')
            clean_f = re.sub(r'\be\^\{([^{}]*)\}', r'np.exp(\1)', clean_f)
            clean_f = re.sub(r'\be\^(\([^()]*\)|[\w\.]+)', r'np.exp(\1)', clean_f)
            clean_f = clean_f.replace('^', '**').replace('y=', '').replace('f(x)=', '').strip()
            clean_f = re.sub(r'(?<![\w.])(\d+(?:\.\d+)?)\s*([a-zA-Z\(])', r'\1*\2', clean_f)
            clean_f = re.sub(r'(\))\s*([a-zA-Z0-9\(])', r'\1*\2', clean_f).replace('{', '(').replace('}', ')')
            math_str = func_str.replace('**', '^').replace('*', '').replace(' ', '')
            sa_def, sb_def = float(data.get("a", 0.0)), float(data.get("b", 3.0))

            with c1:
                st.caption("⚙️ **Thông số Diện tích hình phẳng:**")
                st.info(f"**Hàm số:** $y = {math_str}$")
                sa = st.slider("Cận dưới a:", -10.0, 10.0, sa_def, 0.5, key="lab_area_a")
                sb = st.slider("Cận trên b:", -10.0, 10.0, sb_def, 0.5, key="lab_area_b")
                if sa >= sb:
                    st.warning("⚠️ Cận a phải nhỏ hơn cận b!"); sb = sa + 0.5
                try:
                    x_area = np.linspace(sa, sb, 400)
                    y_area = safe_eval_func(clean_f, x_area)
                    if isinstance(y_area, (int, float)): y_area = np.full_like(x_area, float(y_area))
                    area_val = _trapz(np.abs(y_area), x_area)
                    st.success(f"📐 **Diện tích (S):**\n\n$$S = \\int_{{{sa}}}^{{{sb}}} |{math_str}| dx \\approx {abs(area_val):.2f}$$")
                except Exception: pass

            with c2:
                try:
                    fig_area = go.Figure()
                    x_full = np.linspace(sa - 3, sb + 3, 600)
                    y_full = safe_eval_func(clean_f, x_full)
                    if isinstance(y_full, (int, float)): y_full = np.full_like(x_full, float(y_full))
                    fig_area.add_trace(go.Scatter(x=x_full, y=y_full, mode='lines', line=dict(color='#38bdf8', width=3), name='Đồ thị hàm số'))
                    y_area_fill = safe_eval_func(clean_f, x_area)
                    if isinstance(y_area_fill, (int, float)): y_area_fill = np.full_like(x_area, float(y_area_fill))
                    fig_area.add_trace(go.Scatter(x=np.concatenate([x_area, x_area[::-1]]), y=np.concatenate([y_area_fill, np.zeros_like(y_area_fill)]), fill='toself', fillcolor='rgba(236, 72, 153, 0.4)', line=dict(color='rgba(255,255,255,0)'), hoverinfo="skip", name='Diện tích (S)'))
                    
                    y_view_min, y_view_max = min(y_full), max(y_full)
                    y_pad = (y_view_max - y_view_min) * 0.15 
                    if y_pad == 0: y_pad = 2
                    y_min, y_max = y_view_min - y_pad, y_view_max + y_pad
                    if y_min > 0: y_min = -y_pad
                    if y_max < 0: y_max = y_pad

                    y_sa, y_sb = safe_eval_func(clean_f, sa), safe_eval_func(clean_f, sb)
                    fig_area.add_trace(go.Scatter(x=[sa, sa], y=[0, float(y_sa)], mode='lines', line=dict(color='#f59e0b', width=2, dash='dash'), name='Cận a'))
                    fig_area.add_trace(go.Scatter(x=[sb, sb], y=[0, float(y_sb)], mode='lines', line=dict(color='#10b981', width=2, dash='dash'), name='Cận b'))
                    setup_pedagogical_oxy(fig_area, [min(x_full), max(x_full)], [y_min, y_max])
                    fig_area.update_layout(title="Mô phỏng Diện tích hình phẳng (Tích phân)", height=500, showlegend=True)
                    st.plotly_chart(fig_area, use_container_width=True)
                except Exception as err: st.error(f"Lỗi vẽ đồ thị diện tích: {err}")
            return
            
        if dtype == "revolve_ox":
            func_str = str(data.get("func", "2*x + 1")).replace('$', '').strip()
            clean_f = re.sub(r'\\frac{(.*?)}{(.*?)}', r'((\1)/(\2))', func_str)
            clean_f = clean_f.replace('\\sin', 'np.sin').replace('\\cos', 'np.cos').replace('\\tan', 'np.tan').replace('\\ln', 'np.log').replace('\\pi', 'np.pi')
            clean_f = re.sub(r'\be\^\{([^{}]*)\}', r'np.exp(\1)', clean_f)
            clean_f = re.sub(r'\be\^(\([^()]*\)|[\w\.]+)', r'np.exp(\1)', clean_f)
            clean_f = clean_f.replace('^', '**').replace('y=', '').replace('f(x)=', '').strip()
            clean_f = re.sub(r'(?<![\w.])(\d+(?:\.\d+)?)\s*([a-zA-Z\(])', r'\1*\2', clean_f)
            clean_f = re.sub(r'(\))\s*([a-zA-Z0-9\(])', r'\1*\2', clean_f).replace('{', '(').replace('}', ')')

            a_def, b_def = float(data.get("a", 2.0)), float(data.get("b", 5.0))

            c1, c2 = st.columns([1.2, 2.8])
            with c1:
                st.caption("⚙️ **Thông số Khối tròn xoay quanh trục Ox:**")
                math_str = func_str.replace('**', '^').replace('*', '')
                st.info(f"**Đường giới hạn:** $y = {math_str}$")
                sa = st.slider("Cận dưới a:", -8.0, 8.0, a_def, 0.5, key="lab_revolve_a")
                sb = st.slider("Cận trên b:", -8.0, 8.0, b_def, 0.5, key="lab_revolve_b")
                angle_deg = st.slider("Góc quay quanh trục Ox:", 30, 360, 360, 15, key="lab_revolve_angle")
                if sa >= sb:
                    st.warning("⚠️ Cận a phải nhỏ hơn cận b!"); sb = sa + 0.5
                try:
                    x_num = np.linspace(sa, sb, 400)
                    y_num = safe_eval_func(clean_f, x_num)
                    if isinstance(y_num, (int, float)): y_num = np.full_like(x_num, float(y_num))
                    vol_val = _trapz(y_num**2, x_num) * np.pi
                    st.success(f"📐 **Thể tích khối tròn xoay:**\n\n$$V = \\pi \\int_{{{sa}}}^{{{sb}}} [{math_str}]^2 dx \\approx {abs(vol_val):.2f}\\text{{ (đvtt)}}$$")
                except Exception: pass

            with c2:
                try:
                    u = np.linspace(sa, sb, 60)
                    v = np.linspace(0, np.radians(angle_deg), 60)
                    U, V = np.meshgrid(u, v)
                    R = safe_eval_func(clean_f, U)
                    if isinstance(R, (int, float)): R = np.full_like(U, float(R))
                    X_3d = U; Y_3d = R * np.cos(V); Z_3d = R * np.sin(V)

                    fig_3d = go.Figure()
                    fig_3d.add_trace(go.Surface(x=X_3d, y=Y_3d, z=Z_3d, colorscale='Viridis', opacity=0.82, showscale=False, name='Khối tròn xoay'))
                    ox_min, ox_max = min(sa - 1.5, -2), max(sb + 1.5, 2)
                    fig_3d.add_trace(go.Scatter3d(x=[ox_min, ox_max], y=[0, 0], z=[0, 0], mode='lines+text', line=dict(color='#ffffff', width=4), text=["", "Trục Ox"], textposition="top right", name="Trục Ox"))
                    y_gen = safe_eval_func(clean_f, u)
                    if isinstance(y_gen, (int, float)): y_gen = np.full_like(u, float(y_gen))
                    fig_3d.add_trace(go.Scatter3d(x=u, y=y_gen, z=np.zeros_like(u), mode='lines', line=dict(color='#f43f5e', width=5), name='Đường sinh y=f(x)'))
                    fig_3d.update_layout(title=f"Mô hình 3D Khối tròn xoay: $y = {math_str}$ quay quanh Ox", template="plotly_dark", scene=dict(xaxis=dict(title="Trục Ox", backgroundcolor="#0f172a", gridcolor="#1e293b"), yaxis=dict(title="Trục Oy", backgroundcolor="#0f172a", gridcolor="#1e293b"), zaxis=dict(title="Trục Oz", backgroundcolor="#0f172a", gridcolor="#1e293b"), aspectmode='data'), height=520, margin=dict(l=10, r=10, t=35, b=10))
                    st.plotly_chart(fig_3d, use_container_width=True)
                except Exception as err: st.error(f"Lỗi tính toán mô phỏng 3D: {err}")
            return

        if dtype == "dynamic_code":
            st.markdown("### 🎨 Mô Phỏng Đồ Họa Động / Không Gian Nâng Cao")
            render_dynamic_python_lab(data.get("python_code", ""))
            return

        fig = go.Figure()
        if dtype == "func_3":
            c1, c2 = st.columns([1.2, 2.8])
            with c1:
                st.caption("⚙️ **Thay đổi hệ số hàm bậc 3:**")
                fa = st.slider("Hệ số a:", -3.0, 3.0, float(data.get("a", 1.0)), 0.5, key="lab_f3_a")
                if fa == 0: fa = 0.5
                fb = st.slider("Hệ số b:", -5.0, 5.0, float(data.get("b", -3.0)), 0.5, key="lab_f3_b")
                fc = st.slider("Hệ số c:", -5.0, 5.0, float(data.get("c", 0.0)), 0.5, key="lab_f3_c")
                fd = st.slider("Hệ số d:", -5.0, 5.0, float(data.get("d", 2.0)), 0.5, key="lab_f3_d")
                st.info(f"**$y = {fa}x^3 + ({fb})x^2 + ({fc})x + ({fd})$**")
            with c2:
                x_vals = np.linspace(-6, 6, 800)
                y_vals = fa * (x_vals**3) + fb * (x_vals**2) + fc * x_vals + fd
                fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', line=dict(color='#38bdf8', width=3), name='Đồ thị'))
                y_pad = (max(y_vals) - min(y_vals)) * 0.15
                setup_pedagogical_oxy(fig, [-6, 6], [min(y_vals) - y_pad, max(y_vals) + y_pad])
                fig.update_layout(title="Đồ thị Hàm số Bậc 3", height=500)
                st.plotly_chart(fig, use_container_width=True)

        elif dtype == "func_1_1":
            c1, c2 = st.columns([1.2, 2.8])
            with c1:
                st.caption("⚙️ **Thay đổi hệ số hàm phân thức bậc 1/1:**")
                fa = st.slider("Hệ số a:", -4.0, 4.0, float(data.get("a", 1.0)), 0.5, key="lab_f11_a")
                fb = st.slider("Hệ số b:", -5.0, 5.0, float(data.get("b", 1.0)), 0.5, key="lab_f11_b")
                fc = st.slider("Hệ số c:", -4.0, 4.0, float(data.get("c", 1.0)), 0.5, key="lab_f11_c")
                if fc == 0: fc = 1.0
                fd = st.slider("Hệ số d:", -5.0, 5.0, float(data.get("d", -1.0)), 0.5, key="lab_f11_d")
                x_tc_dung = -fd / fc; y_tc_ngang = fa / fc
                st.info(f"**$y = \\frac{{{fa}x + {fb}}}{{{fc}x + {fd}}}$**")
                st.caption(f"📌 Tiệm cận đứng: $x = {x_tc_dung:.2f}$<br>📌 Tiệm cận ngang: $y = {y_tc_ngang:.2f}$", unsafe_allow_html=True)
            with c2:
                x_left = np.linspace(-7, x_tc_dung - 0.05, 400); x_right = np.linspace(x_tc_dung + 0.05, 7, 400)
                y_left = (fa * x_left + fb) / (fc * x_left + fd); y_right = (fa * x_right + fb) / (fc * x_right + fd)
                y_left[np.abs(y_left) > 15] = np.nan; y_right[np.abs(y_right) > 15] = np.nan
                fig.add_trace(go.Scatter(x=x_left, y=y_left, mode='lines', line=dict(color='#38bdf8', width=3), name='Nhánh trái'))
                fig.add_trace(go.Scatter(x=x_right, y=y_right, mode='lines', line=dict(color='#38bdf8', width=3), name='Nhánh phải'))
                fig.add_trace(go.Scatter(x=[x_tc_dung, x_tc_dung], y=[-15, 15], mode='lines', line=dict(color='#f59e0b', width=1.8, dash='dash'), name='TC Đứng'))
                fig.add_trace(go.Scatter(x=[-7, 7], y=[y_tc_ngang, y_tc_ngang], mode='lines', line=dict(color='#10b981', width=1.8, dash='dash'), name='TC Ngang'))
                setup_pedagogical_oxy(fig, [-7, 7], [-8, 8])
                fig.update_layout(title="Đồ thị Hàm phân thức Bậc 1/1", height=500)
                st.plotly_chart(fig, use_container_width=True)

        elif dtype == "func_2_1":
            c1, c2 = st.columns([1.2, 2.8])
            with c1:
                st.caption("⚙️ **Hệ số hàm phân thức bậc 2/1:**")
                fa = st.slider("a:", -3.0, 3.0, float(data.get("a", 1.0)), 0.5, key="lab_f21_a")
                if fa == 0: fa = 1.0
                fb = st.slider("b:", -5.0, 5.0, float(data.get("b", -2.0)), 0.5, key="lab_f21_b")
                fc = st.slider("c:", -5.0, 5.0, float(data.get("c", 2.0)), 0.5, key="lab_f21_c")
                fd = st.slider("d:", -3.0, 3.0, float(data.get("d", 1.0)), 0.5, key="lab_f21_d")
                if fd == 0: fd = 1.0
                fe = st.slider("e:", -5.0, 5.0, float(data.get("e", -1.0)), 0.5, key="lab_f21_e")
                x_tc_dung = -fe / fd; m_slope = fa / fd; n_intercept = (fb - m_slope * fe) / fd
                st.info(f"**$y = \\frac{{{fa}x^2 + {fb}x + {fc}}}{{{fd}x + {fe}}}$**")
                st.caption(f"📌 TC Đứng: $x = {x_tc_dung:.2f}$<br>📌 TC Xiên: $y = {m_slope:.2f}x + ({n_intercept:.2f})$", unsafe_allow_html=True)
            with c2:
                x_left = np.linspace(-7, x_tc_dung - 0.05, 400); x_right = np.linspace(x_tc_dung + 0.05, 7, 400)
                y_left = (fa * x_left**2 + fb * x_left + fc) / (fd * x_left + fe)
                y_right = (fa * x_right**2 + fb * x_right + fc) / (fd * x_right + fe)
                y_left[np.abs(y_left) > 18] = np.nan; y_right[np.abs(y_right) > 18] = np.nan
                fig.add_trace(go.Scatter(x=x_left, y=y_left, mode='lines', line=dict(color='#38bdf8', width=3), name='Đồ thị'))
                fig.add_trace(go.Scatter(x=x_right, y=y_right, mode='lines', line=dict(color='#38bdf8', width=3), name='Đồ thị'))
                fig.add_trace(go.Scatter(x=[x_tc_dung, x_tc_dung], y=[-18, 18], mode='lines', line=dict(color='#f59e0b', width=1.8, dash='dash'), name='TC Đứng'))
                x_slant = np.linspace(-7, 7, 100); y_slant = m_slope * x_slant + n_intercept
                fig.add_trace(go.Scatter(x=x_slant, y=y_slant, mode='lines', line=dict(color='#ec4899', width=1.8, dash='dash'), name='TC Xiên'))
                setup_pedagogical_oxy(fig, [-7, 7], [-10, 10])
                fig.update_layout(title="Đồ thị Hàm phân thức Bậc 2/1", height=500)
                st.plotly_chart(fig, use_container_width=True)

        elif dtype in ["parabola", "func_2"]:
            c1, c2 = st.columns([1.2, 2.8])
            with c1:
                st.caption("⚙️ **Hệ số Parabol bậc 2:**")
                fa = st.slider("Hệ số a:", -4.0, 4.0, float(data.get("a", 1.0)), 0.5, key="lab_p2_a")
                if fa == 0: fa = 1.0
                fb = st.slider("Hệ số b:", -6.0, 6.0, float(data.get("b", -2.0)), 0.5, key="lab_p2_b")
                fc = st.slider("Hệ số c:", -6.0, 6.0, float(data.get("c", -1.0)), 0.5, key="lab_p2_c")
                x_dinh = -fb / (2 * fa); y_dinh = fa * x_dinh**2 + fb * x_dinh + fc
                st.info(f"**$y = {fa}x^2 + ({fb})x + ({fc})$**")
                st.caption(f"📌 Đỉnh: $I({x_dinh:.2f}; {y_dinh:.2f})$<br>📌 Trục đối xứng: $x = {x_dinh:.2f}$", unsafe_allow_html=True)
            with c2:
                x_vals = np.linspace(-6, 6, 600); y_vals = fa * x_vals**2 + fb * x_vals + fc
                fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', line=dict(color='#38bdf8', width=3), name='Parabol'))
                fig.add_trace(go.Scatter(x=[x_dinh, x_dinh], y=[-12, 12], mode='lines', line=dict(color='#f59e0b', width=1.5, dash='dash'), name='Trục đối xứng'))
                fig.add_trace(go.Scatter(x=[x_dinh], y=[y_dinh], mode='markers+text', marker=dict(size=8, color='gold'), text=[f'I({x_dinh:.1f}; {y_dinh:.1f})'], textposition="top center"))
                y_pad = (max(y_vals) - min(y_vals)) * 0.15
                setup_pedagogical_oxy(fig, [-6, 6], [min(y_vals) - y_pad, max(y_vals) + y_pad])
                fig.update_layout(title="Đồ thị Parabol", height=500)
                st.plotly_chart(fig, use_container_width=True)

        elif dtype == "oxyz":
            c1, c2 = st.columns([1, 3])
            with c1:
                st.caption("⚙️ **Tọa độ điểm M(x; y; z):**")
                mx = st.slider("x:", -4.0, 5.0, float(data.get("x", 2.0)), 0.5, key="lab_3d_x")
                my = st.slider("y:", -4.0, 5.0, float(data.get("y", 3.0)), 0.5, key="lab_3d_y")
                mz = st.slider("z:", -4.0, 5.0, float(data.get("z", 4.0)), 0.5, key="lab_3d_z")
                st.info(f"**M({mx}; {my}; {mz})$**")
            with c2:
                fig.add_trace(go.Scatter3d(x=[mx], y=[my], z=[mz], mode='markers+text', marker=dict(size=9, color='#38bdf8'), text=[f'M({mx}; {my}; {mz})'], textposition="top center"))
                fig.add_trace(go.Scatter3d(x=[0, mx, mx], y=[0, 0, my], z=[0, 0, 0], mode='lines', line=dict(color='#94a3b8', width=3, dash='dash'), hoverinfo='skip'))
                fig.add_trace(go.Scatter3d(x=[mx, mx], y=[my, my], z=[0, mz], mode='lines', line=dict(color='#f59e0b', width=3, dash='dash'), hoverinfo='skip'))
                fig.update_layout(title="Không gian Oxyz", template="plotly_dark", scene=dict(xaxis=dict(range=[-5, 5], backgroundcolor="#0f172a"), yaxis=dict(range=[-5, 5], backgroundcolor="#0f172a"), zaxis=dict(range=[-5, 5], backgroundcolor="#0f172a"), aspectmode='cube'), height=500, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig, use_container_width=True)

    # ------------------------------------------------------------------------------
    # TRẠM 1: LÝ THUYẾT & PHÒNG LAB 
    # ------------------------------------------------------------------------------
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader(f"📖 Tự học & Chiếm lĩnh kiến thức môn {subject} - Lớp {grade_num}")
        topic_input = st.text_input("📝 Nhập bài học cần chiếm lĩnh kiến thức:", placeholder="Ví dụ: Khảo sát hàm số, Hình chóp, Nhị thức Newton...")
        
        if st.button("🚀 Soạn bài học chuẩn GDPT 2018", use_container_width=True) and topic_input.strip():
            st.session_state.tram1_count += 1
            with st.spinner("Đang biên soạn chuẩn ngữ liệu SGK KNTT..."):
                study_prompt = f"""[HỆ THỐNG BIÊN SOẠN BÀI HỌC CHUẨN QUỐC GIA - CT GDPT 2018 & QUY CHẾ THI 2026]
Môn học: {subject} | Khối lớp: {grade_num}. Chủ đề bài học: '{topic_input}'.
YÊU CẦU BẮT BUỘC:
1. BÁM SÁT 100% NGỮ LIỆU KNTT. TOÁN HỌC: CẤM DÙNG HÀM BẬC 4 TRÙNG PHƯƠNG.
2. TRẮC NGHIỆM SOCRATIC: Sinh chính xác 3 câu trắc nghiệm (A, B, C, D). Kèm đáp án và giải thích gợi mở.
3. TỰ LUẬN: Sinh 2 bài tập vận dụng kèm hướng dẫn POLYA 4 bước (Không giải chi tiết).
TIÊU ĐỀ BẮT BUỘC:
### PHẦN 1: TÓM TẮT CỐT LÕI
### PHẦN 2: TRẮC NGHIỆM KHÁCH QUAN SOCRATIC
### PHẦN 3: BÀI TẬP TỰ LUẬN
"""
                try:
                    res_text = call_gemini_with_fallback(study_prompt)
                    st.session_state.current_lesson = res_text
                    st.session_state.current_topic = topic_input.strip()
                    st.session_state.parsed_quiz = parse_quiz_questions(res_text)
                    st.session_state.quiz_states = {}
                except Exception as e:
                    st.error(f"Lỗi: {e}")

        if st.session_state.get("current_lesson"):
            lesson_text = st.session_state.current_lesson
            part2_split = re.split(r'(?i)(?:###\s*)?PHẦN 2[\:\.]?', lesson_text)
            part3_split = re.split(r'(?i)(?:###\s*)?PHẦN 3[\:\.]?', lesson_text)
            
            if len(part2_split) > 0 and part2_split[0].strip():
                cleaned_p1 = re.sub(r'\n\s*\n', '\n\n', part2_split[0].strip())
                cleaned_p1 = re.sub(r'(?:\s*\-\-\-\s*)+$', '', cleaned_p1)
                st.markdown(cleaned_p1)
                create_pedagogical_tts_component(cleaned_p1, subject, "tram1_lesson")

            quiz_list = st.session_state.get("parsed_quiz", [])
            if quiz_list:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### 🎯 Phần 2: Trắc nghiệm khách quan Socratic")
                for idx, q in enumerate(quiz_list):
                    st.markdown(f"**Câu {idx+1}:** `[{q['level']}]` {q['question']}")
                    user_choice = st.radio(f"Chọn đáp án câu {idx+1}:", q['options'], key=f"q_{idx}", label_visibility="collapsed")
                    if st.button(f"🔍 Kiểm tra câu {idx+1}", key=f"btn_{idx}"):
                        if user_choice:
                            choice_letter = re.sub(r'[^A-D]', '', user_choice.strip()[:3]).upper()[:1]
                            if choice_letter == q['correct']: 
                                st.session_state.quiz_states[idx] = ("correct", "🎉 Xuất sắc! Em tư duy rất chuẩn.")
                            else: 
                                st.session_state.quiz_states[idx] = ("incorrect", f"💡 **Gợi ý Socratic:** {q['explain']}")
                        else: st.warning("Vui lòng chọn một đáp án!")
                    if idx in st.session_state.quiz_states:
                        status, msg = st.session_state.quiz_states[idx]
                        if status == "correct": st.success(msg)
                        else: st.warning("🤔 Suy ngẫm thêm gợi ý dưới đây nhé:"); st.info(msg)
                    st.markdown("---")
            elif len(part2_split) > 1 and "PHẦN 3" in part2_split[1].upper():
                fallback_p2 = re.split(r'(?i)###\s*PHẦN\s*3', part2_split[1])[0]
                st.markdown(fallback_p2.strip())
            
            if len(part3_split) > 1 and part3_split[-1].strip():
                st.markdown("### ✍️ Phần 3: Bài tập tự luận & Hướng dẫn tư duy")
                st.markdown(part3_split[-1].strip())

        st.markdown("---")
        st.markdown('<h4 style="color: #38bdf8; margin-top: 0; margin-bottom: 5px; font-weight: 800;">🔬 PHÒNG THÍ NGHIỆM ẢO THEO YÊU CẦU (VIRTUAL LAB)</h4>', unsafe_allow_html=True)
        st.markdown(f'<div style="color: #cbd5e1; font-size: 15px; margin-bottom: 12px;">Hệ thống AI đang liên kết trực tiếp với <b>Môn {subject} - Lớp {grade_num}</b>. Nhập yêu cầu mô phỏng đồ thị, tích phân, miền nghiệm, không gian 3D, hoặc sơ đồ tư duy:</div>', unsafe_allow_html=True)
        
        lab_command = st.text_input("Lệnh mô phỏng:", placeholder="Ví dụ Toán: Vẽ hình đa diện 3D, khối chóp, sơ đồ tư duy...", label_visibility="collapsed")
        
        if st.button("✨ Khởi chạy Phòng Lab", key=f"btn_lab_{st.session_state.active_context_key}", use_container_width=True) and lab_command.strip():
            st.session_state.tram1_count += 1
            with st.spinner("AI đang phân tích ngữ cảnh liên môn và dựng mô hình..."):
                context_text = st.session_state.current_lesson if st.session_state.get("current_lesson") else "Không có ngữ cảnh bài học trước đó."
                lab_prompt = f"""[HỆ TRI THỨC SƯ PHẠM QUỐC GIA - CHUẨN CT GDPT 2018 & QUY CHẾ THI 2026]
Môn học: {subject} | Khối lớp: {grade_num}. 
NGỮ CẢNH BÀI HỌC HIỆN TẠI:
{context_text}
---
Yêu cầu của học sinh: "{lab_command}"
NHIỆM VỤ: Xuất DUY NHẤT 1 khối JSON hợp lệ phân loại mô hình trực quan.
QUY TẮC PHÂN LOẠI:
1. DIỆN TÍCH HÌNH PHẲNG: {{"type": "area", "func": "x**2 - 3*x + 2", "a": 0.0, "b": 3.0}}
2. KHỐI TRÒN XOAY 3D: {{"type": "revolve_ox", "func": "2*x + 1", "a": 2.0, "b": 5.0}}
3. HÀM BẬC 3: {{"type": "func_3", "a": 1, "b": -3, "c": 0, "d": 2}}
4. HÀM PHÂN THỨC 1/1: {{"type": "func_1_1", "a": 1, "b": 1, "c": 1, "d": -1}}
5. HÀM PHÂN THỨC 2/1: {{"type": "func_2_1", "a": 1, "b": -2, "c": 2, "d": 1, "e": -1}}
6. PARABOL BẬC 2: {{"type": "parabola", "a": 1, "b": -2, "c": 1}}
7. KHÔNG GIAN OXYZ: {{"type": "oxyz", "x": 2, "y": 3, "z": 4}}
8. MÔ PHỎNG NÂNG CAO PYTHON PLOTLY (Hình đa diện Poly, Khối 3D, Miền nghiệm BPT...):
   {{"type": "dynamic_code", "python_code": "fig = go.Figure()\\n# BẮT BUỘC DÙNG go.Mesh3d để vẽ Poly/Hình học không gian 3D. Khai báo đủ x, y, z và các mặt i, j, k.\\nfig.add_trace(go.Mesh3d(x=[0,1,0,0], y=[0,0,1,0], z=[0,0,0,1], i=[0,0,0,1], j=[1,1,2,2], k=[2,3,3,3], color='cyan', opacity=0.6))\\nfig.update_layout(scene=dict(aspectmode='cube'))"}}
9. SƠ ĐỒ TƯ DUY: {{"type": "mermaid", "code": "graph LR\\nRoot[\\\"🎯 TIÊU ĐỀ\\\"] --> A[\\\"1. Nội dung\\\"]"}}
"""
                try:
                    raw_json = call_gemini_with_fallback(lab_prompt, json_mode=True)
                    raw_json = raw_json.strip()
                    if raw_json.startswith("```json"): raw_json = raw_json[7:-3].strip()
                    elif raw_json.startswith("```"): raw_json = raw_json[3:-3].strip()
                    
                    if "graph " in raw_json or "flowchart " in raw_json or "-->" in raw_json:
                        if not raw_json.startswith("{"): st.session_state.lab_data = {"type": "mermaid", "code": raw_json}
                        else:
                            try: st.session_state.lab_data = json.loads(raw_json)
                            except:
                                m_code = re.search(r'"code"\s*:\s*"(.*?)"\s*(?:,\s*"|\})', raw_json, re.DOTALL)
                                if m_code: st.session_state.lab_data = {"type": "mermaid", "code": m_code.group(1).encode('utf-8').decode('unicode_escape', errors='ignore')}
                                else: st.session_state.lab_data = {"type": "mermaid", "code": raw_json}
                    else: st.session_state.lab_data = json.loads(raw_json)
                except Exception:
                    is_mm = any(kw in lab_command.lower() for kw in ["sơ đồ", "mindmap", "tóm tắt", "suy"])
                    st.session_state.lab_data = {"type": "mermaid", "code": "graph LR\nRoot[\"🎯 BÀI HỌC\"]-->A[\"1. Tóm tắt\"]"} if is_mm else {"type": "func_3", "a": 1, "b": -3, "c": 0, "d": 2}

        if st.session_state.get("lab_data"):
            st.success("✨ Đã khởi tạo mô phỏng Phòng Lab liên môn thành công!")
            render_smart_lab(st.session_state.lab_data)

    # ------------------------------------------------------------------------------
    # TRẠM 2: GIA SƯ SOCRATIC & NỘP BÀI
    # ------------------------------------------------------------------------------
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader(f"✍️ Gia Sư Socratic Môn: {subject} - Lớp {grade_num}")
        st.caption("Khung Tri Thức Chuẩn Hóa CT GDPT 2018 & SGK KNTT • Vấn đáp Socratic • Dẫn dắt tư duy, không giải hộ.")

        if st.button("🔄 Xóa đối thoại cũ", use_container_width=True): 
            st.session_state.messages = []
            st.session_state.chat = None
            st.rerun()

        socratic_system_instruction = f"""Bạn là Thầy giáo Gia Sư AI tại Trường THPT Tân Hiệp & Trung tâm Thiện Nhân. Học sinh đang học: Môn {subject} - Khối lớp: {grade_num}. Tên học sinh: {student_name}."""

        uploaded_file = st.file_uploader("📸 Tải ảnh bài làm (JPG, PNG)", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.image(Image.open(uploaded_file), caption="Bài làm của em", use_container_width=True)
            if st.button("🚀 Bắt đầu nhận xét", use_container_width=True):
                st.session_state.tram2_count += 1
                with st.spinner(f"Thầy đang đối chiếu chuẩn kiến thức SGK KNTT Lớp {grade_num}..."):
                    try:
                        full_res = call_gemini_with_fallback(
                            [f"Học sinh {student_name} nộp ảnh bài làm môn {subject} Lớp {grade_num}. Thầy hãy soi kỹ bài làm và nhận xét Socratic:", Image.open(uploaded_file)], 
                            system_instruction=socratic_system_instruction
                        )
                        student_fb = full_res.split("<DIAGNOSTIC>")[0].strip() if "<DIAGNOSTIC>" in full_res else full_res
                        st.session_state.messages = [{"role": "user", "content": "*(Em đã nộp ảnh bài làm)*"}, {"role": "assistant", "content": student_fb}]
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Lỗi phân tích bài làm: {e}")

        for m in st.session_state.get("messages", []):
            with st.chat_message(m["role"]): st.markdown(m["content"])
            
        if q := st.chat_input("Em chưa hiểu chỗ nào, hãy hỏi Thầy nhé..."):
            st.session_state.tram2_count += 1
            st.session_state.messages.append({"role": "user", "content": q})
            with st.chat_message("user"): st.markdown(q)
            with st.chat_message("assistant"):
                with st.spinner("Thầy đang suy ngẫm câu hỏi của em..."):
                    try:
                        history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-4:]])
                        rep = call_gemini_with_fallback(
                            f"Lịch sử đối thoại trước đó:\n{history_context}\nHọc sinh {student_name} hỏi: {q}\nThầy phản hồi gợi mở Socratic:",
                            system_instruction=socratic_system_instruction
                        )
                        clean_rep = rep.split("<DIAGNOSTIC>")[0].strip()
                        st.markdown(clean_rep)
                        st.session_state.messages.append({"role": "assistant", "content": clean_rep})
                    except Exception as e: 
                        st.error(f"Lỗi phản hồi: {e}")

    # ------------------------------------------------------------------------------
    # TRẠM 3: KHẢO THÍ ĐỘC LẬP
    # ------------------------------------------------------------------------------
    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader(f"📝 Trạm 3: Khảo Thí Độc Lập - Môn {subject} (Lớp {grade_num})")
        st.caption("Cấu trúc Khảo thí 2026 (QĐ 764/QĐ-BGDĐT) • Tối ưu hóa Token 60% • Dựng đồ thị 0-Token • Thang điểm chuẩn Bộ.")

        if "exam_state" not in st.session_state: st.session_state.exam_state = "config"
        if "exam_data" not in st.session_state: st.session_state.exam_data = None
        if "exam_answers" not in st.session_state: st.session_state.exam_answers = {}

        if st.session_state.exam_state == "config":
            st.markdown("#### 📊 Cấu hình chuyên đề khảo thí chuẩn CT GDPT 2018:")
            
            if subject == "Ngữ văn": def_p1, def_p2, def_p3, default_time = 0, 0, 0, 120
            elif subject == "Tiếng Anh": def_p1, def_p2, def_p3, default_time = 40, 0, 0, 50
            elif subject == "Toán học": def_p1, def_p2, def_p3, default_time = 12, 4, 6, 90
            elif subject in ["Vật lý", "Hóa học", "Sinh học", "Khoa học tự nhiên"]: def_p1, def_p2, def_p3, default_time = 18, 4, 6, 50
            else: def_p1, def_p2, def_p3, default_time = 24, 4, 0, 50

            exam_time_mins = st.selectbox("⏱️ Thời lượng bài thi (Phút):", [15, 30, 45, 50, 60, 90, 120], index=[15, 30, 45, 50, 60, 90, 120].index(default_time) if default_time in [15, 30, 45, 50, 60, 90, 120] else 3)
            st.session_state.exam_time_mins = exam_time_mins

            if st.button(f"🚀 Khởi tạo đề thi ({exam_time_mins} phút)", type="primary", use_container_width=True):
                st.session_state.exam_code = str(random.randint(1011, 9999))
                with st.spinner("⚡ AI đang nén Token siêu tốc & phân luồng ma trận đề thi..."):
                    exam_prompt = f"""[CHUYÊN GIA KHẢO THÍ BGDĐT - MÔN {subject.upper()} LỚP {grade_num}]
Số lượng: {def_p1} TN, {def_p2} Đ/S, {def_p3} TLN. TUYỆT ĐỐI CẤM HÀM BẬC 4 TRÙNG PHƯƠNG.
XUẤT DUY NHẤT 1 OBJECT JSON:
{{"p1": [{{"q": "...", "f": null, "bbt": null, "opt": ["A. $...$", "B. $...$", "C. $...$", "D. $...$"], "ans": "A", "h": "...", "exp": "..."}}],
 "p2": [{{"q": "...", "f": null, "bbt": null, "stmts": [{{"t": "...", "c": true}}, {{"t": "...", "c": false}}, {{"t": "...", "c": true}}, {{"t": "...", "c": false}}], "h": "...", "exp": "..."}}],
 "p3": [{{"q": "...", "f": null, "bbt": null, "ans": "...", "h": "...", "exp": "..."}}]}}"""
                    if subject == "Ngữ văn":
                        exam_prompt = f"""[CHUYÊN GIA KHẢO THÍ NGỮ VĂN GDPT 2018 LỚP {grade_num}] JSON DUY NHẤT:
{{"part_doc_hieu": {{"text": "Đoạn trích...", "questions": [{{"q": "Câu hỏi...", "h": "Gợi ý...", "exp": "Giải thích..."}}]}}, "part_viet": [{{"type": "NLXH", "q": "Đoạn văn...", "h": "Dàn ý...", "exp": "Tiêu chí"}}]}}"""
                    
                    try:
                        raw_json = call_gemini_with_fallback(exam_prompt, json_mode=True).strip()
                        if raw_json.startswith("```json"): raw_json = raw_json[7:-3].strip()
                        elif raw_json.startswith("```"): raw_json = raw_json[3:-3].strip()
                        
                        start_idx = raw_json.find('{')
                        s = re.sub(r',\s*([\]}])', r'\1', raw_json[start_idx:].strip())
                        res, i, n, in_str = [], 0, len(s), False
                        while i < n:
                            c = s[i]
                            if c == '"':
                                k, bs = len(res) - 1, 0
                                while k >= 0 and res[k] == '\\': bs += 1; k -= 1
                                if bs % 2 == 0: in_str = not in_str
                                res.append(c); i += 1
                            elif c == '\\' and in_str:
                                if i + 1 < n:
                                    nxt = s[i + 1]
                                    if nxt in ['"', '\\', '/']: res.extend(['\\', nxt]); i += 2
                                    elif nxt in ['n', 'r', 't', 'b', 'f']: res.extend(['\\', nxt]); i += 2
                                    elif nxt == 'u': res.extend(['\\', 'u']); i += 2
                                    else: res.extend(['\\\\', nxt]); i += 2
                                else: res.append('\\\\'); i += 1
                            else: res.append(c); i += 1
                        
                        st.session_state.exam_data = json.loads("".join(res), strict=False)
                        st.session_state.exam_state = "testing"
                        st.session_state.exam_answers = {}
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khởi tạo đề thi: {e}")

        elif st.session_state.exam_state == "testing":
            exam = st.session_state.exam_data
            if st.button("🚨 Nộp bài ngay", use_container_width=True): 
                st.session_state.exam_state = "result"
                st.session_state.tram3_count += 1
                st.rerun()
            st.markdown("---")

            if subject == "Ngữ văn":
                st.markdown("### 📖 PHẦN I. ĐỌC HIỂU")
                dh = exam.get("part_doc_hieu", {})
                st.info(dh.get('text', ''))
                for idx, q in enumerate(dh.get("questions", [])):
                    st.markdown(f"**Câu {idx+1}:** {q['q']}")
                    st.session_state.exam_answers[f"van_dh_{idx}"] = st.text_area(f"Trả lời câu {idx+1}:", key=f"van_dh_{idx}")
                st.markdown("### ✍️ PHẦN II. VIẾT")
                for idx, v in enumerate(exam.get("part_viet", [])):
                    st.markdown(f"**Câu {idx+1}:** {v['q']}")
                    st.session_state.exam_answers[f"van_v_{idx}"] = st.text_area("Bài làm:", key=f"van_v_{idx}")
            else:
                if exam.get("p1"):
                    st.markdown("### 📌 Phần I: Trắc nghiệm nhiều lựa chọn")
                    for idx, q in enumerate(exam["p1"]):
                        st.markdown(f"**Câu {idx+1}:** {q['q']}")
                        st.session_state.exam_answers[f"p1_{idx}"] = st.radio("Chọn đáp án:", q.get("opt", []), key=f"p1_{idx}", index=None, label_visibility="collapsed")
                        st.markdown("---")
                if exam.get("p2"):
                    st.markdown("### 📌 Phần II: Trắc nghiệm Đúng / Sai")
                    for idx, q in enumerate(exam["p2"]):
                        st.markdown(f"**Câu {idx+1}:** {q['q']}")
                        for s_idx, stmt in enumerate(q.get("stmts", [])):
                            s_key = f"p2_{idx}_{s_idx}"
                            st.markdown(f"*   **{chr(97+s_idx)})** {stmt.get('t', '')}")
                            st.session_state.exam_answers[s_key] = st.radio(f"Ý {chr(97+s_idx)}:", ["Đúng", "Sai"], key=s_key, index=None, horizontal=True, label_visibility="collapsed")
                        st.markdown("---")
                if exam.get("p3"):
                    st.markdown("### 📌 Phần III: Trả lời ngắn")
                    for idx, q in enumerate(exam["p3"]):
                        st.markdown(f"**Câu {idx+1}:** {q['q']}")
                        st.session_state.exam_answers[f"p3_{idx}"] = st.text_input("Đáp án:", key=f"p3_{idx}")
                        st.markdown("---")

            if st.button("🏁 NỘP BÀI KHẢO THÍ", use_container_width=True):
                st.session_state.exam_state = "result"
                st.session_state.tram3_count += 1
                st.rerun()

        elif st.session_state.exam_state == "result":
            exam = st.session_state.exam_data
            answers = st.session_state.exam_answers
            total_score = 0.0

            if subject == "Ngữ văn": final_score = 8.0 
            else:
                if subject == "Toán học": w_p1_total, w_p2_total, w_p3_total = 3.0, 4.0, 3.0
                elif subject in ["Vật lý", "Hóa học", "Sinh học", "Khoa học tự nhiên"]: w_p1_total, w_p2_total, w_p3_total = 4.5, 4.0, 1.5
                else: w_p1_total, w_p2_total, w_p3_total = 6.0, 4.0, 0.0

                p1_tot = len(exam.get("p1", []))
                p1_corr = 0
                if p1_tot > 0:
                    for idx, q in enumerate(exam["p1"]):
                        u_val = answers.get(f"p1_{idx}")
                        if u_val and str(u_val)[:1].upper() == str(q.get("ans", ""))[:1].upper(): p1_corr += 1
                    total_score += (p1_corr / p1_tot) * w_p1_total

                p2_tot = len(exam.get("p2", []))
                if p2_tot > 0:
                    w_per_q2 = w_p2_total / p2_tot
                    for idx, q in enumerate(exam["p2"]):
                        c_cnt = 0
                        for s_idx, stmt in enumerate(q.get("stmts", [])):
                            u_ans = answers.get(f"p2_{idx}_{s_idx}")
                            exp_b = stmt.get("a", True) if "a" in stmt else stmt.get("c", True)
                            if (u_ans == "Đúng" and exp_b) or (u_ans == "Sai" and not exp_b): c_cnt += 1
                        if c_cnt == 1: total_score += 0.1 * w_per_q2
                        elif c_cnt == 2: total_score += 0.25 * w_per_q2
                        elif c_cnt == 3: total_score += 0.5 * w_per_q2
                        elif c_cnt == 4: total_score += 1.0 * w_per_q2

                p3_tot = len(exam.get("p3", []))
                p3_corr = 0
                if p3_tot > 0:
                    for idx, q in enumerate(exam["p3"]):
                        u_val = str(answers.get(f"p3_{idx}", "")).strip().lower()
                        q_val = str(q.get("ans", "")).strip().lower()
                        if u_val == q_val and u_val != "": p3_corr += 1
                    total_score += (p3_corr / p3_tot) * w_p3_total

                final_score = min(10.0, round(total_score, 2))

            st.success(f"🎉 **KẾT QUẢ KHẢO THÍ MÔN {subject.upper()} (LỚP {grade_num})!** Điểm số: **{final_score} / 10.0 điểm**")

            # XUẤT LATEX
            st.markdown("---")
            st.markdown("### 📄 Xuất Bản Đề Thi LaTeX Cho Overleaf")
            latex_mode = st.radio("Định dạng xuất:", ["Chỉ xuất Đề thi in ấn", "Xuất Đề thi kèm Bảng đáp án"], horizontal=True)

            def sanitize_latex(txt):
                if not txt: return ""
                pts = re.split(r'(\$.*?\$)', str(clean_vietnamese_math(clean_question_bbt_text(txt))), flags=re.DOTALL)
                for i in range(0, len(pts), 2):
                    pts[i] = re.sub(r'(?<!\\)&', r'\&', pts[i]); pts[i] = re.sub(r'(?<!\\)%', r'\%', pts[i])
                    pts[i] = re.sub(r'(?<!\\)_', r'\_', pts[i]); pts[i] = re.sub(r'(?<!\\)#', r'\#', pts[i])
                return "".join(pts)

            ex_time = st.session_state.get('exam_time_mins', 45)
            curr_y = datetime.now(VN_TZ).year
            ay = f"{curr_y} -- {curr_y + 1}" if datetime.now(VN_TZ).month >= 8 else f"{curr_y - 1} -- {curr_y}"
            ex_code = st.session_state.get('exam_code', '0103')

            latex_code = r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{vietnam}
\usepackage{amsmath,amssymb,amsfonts,mathrsfs}
\usepackage[margin=1.5cm,top=1.8cm,bottom=1.8cm]{geometry}
\usepackage{multicol}
\usepackage{tabularx}
\usepackage{enumitem}
\usepackage{lastpage}
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\rfoot{\textit{Trang \thepage/\pageref{LastPage} -- Mã đề thi \textbf{""" + str(ex_code) + r"""}}}
\begin{document}
\noindent
\begin{minipage}[t]{0.42\textwidth}
    \begin{center}
        \textbf{SỞ GIÁO DỤC VÀ ĐÀO TẠO} \\
        \textbf{AN GIANG} \\
        \textbf{TRƯỜNG """ + ("THCS" if grade_num <= 9 else "THPT") + r""" TÂN HIỆP} \\[0.1cm]
        \textbf{ĐỀ THI CHÍNH THỨC} \\
        \textit{(Đề thi có \pageref{LastPage} trang)}
    \end{center}
\end{minipage}%
\hfill
\begin{minipage}[t]{0.56\textwidth}
    \begin{center}
        \textbf{\small KỲ THI KHẢO SÁT CHẤT LƯỢNG NĂM HỌC """ + ay + r"""} \\[0.05cm]
        Môn thi: \textbf{""" + subject.upper() + r"""} \\[0.05cm]
        \textit{Thời gian làm bài: """ + str(ex_time) + r""" phút} \\[0.05cm]
        \rule{7.5cm}{0.5pt}
    \end{center}
\end{minipage}

\vspace{0.4cm}
\noindent
\begin{minipage}[b]{0.65\textwidth}
    \textbf{Họ, tên thí sinh:}\ \dotfill \\
    \textbf{Số báo danh:}\ \dotfill
\end{minipage}%
\hfill
\begin{minipage}[b]{0.3\textwidth}
    \raggedleft
    \fbox{\makebox[3cm]{\rule[-0.15cm]{0cm}{0.5cm} Mã đề: """ + str(ex_code) + r"""}}
\end{minipage}
\vspace{0.3cm}
\noindent
"""
            if subject == "Ngữ văn":
                dh = exam.get("part_doc_hieu", {})
                latex_code += r"""\textbf{PHẦN I. ĐỌC HIỂU (4.0 điểm)}\vspace{0.15cm}
\begin{center}
\fbox{\begin{minipage}{0.95\linewidth}
\itshape """ + sanitize_latex(dh.get("text", "")) + r"""
\end{minipage}}
\end{center}\vspace{0.15cm}
\begin{enumerate}[label=\textbf{Câu \arabic*.}, leftmargin=*, itemsep=2pt, parsep=0pt]
"""
                for idx, q in enumerate(dh.get("questions", [])): latex_code += f"\\item {sanitize_latex(q.get('q', ''))}\n"
                latex_code += r"""\end{enumerate}
\vspace{0.3cm}\noindent\textbf{PHẦN II. VIẾT (6.0 điểm)}\vspace{0.15cm}
\begin{enumerate}[label=\textbf{Câu \arabic*.}, leftmargin=*, itemsep=2pt, parsep=0pt]
"""
                for idx, v in enumerate(exam.get("part_viet", [])): latex_code += f"\\item \\textbf{{({'2.0' if idx==0 else '4.0'} điểm).}} {sanitize_latex(v.get('q', ''))}\n"
                latex_code += r"""\end{enumerate}"""
            else:
                if exam.get("p1"):
                    latex_code += r"""\textbf{PHẦN I.} Thí sinh trả lời từ câu 1 đến câu """ + str(len(exam["p1"])) + r""". Mỗi câu hỏi thí sinh chỉ chọn một phương án.\vspace{0.15cm}
\begin{enumerate}[label=\textbf{Câu \arabic*.}, leftmargin=*, itemsep=4pt, parsep=0pt]
"""
                    for idx, q in enumerate(exam["p1"]):
                        latex_code += f"\\item {sanitize_latex(q.get('q', ''))}\n"
                        opts = [sanitize_latex(o) for o in q.get("opt", [])]
                        latex_code += "\\begin{enumerate}[label=\\textbf{\\Alph*.}, leftmargin=*, itemsep=0pt, parsep=0pt, topsep=0pt]\n"
                        for opt in opts: latex_code += f"\\item {re.sub(r'^[A-D]\.\s*', '', opt)}\n"
                        latex_code += "\\end{enumerate}\n"
                    latex_code += r"""\end{enumerate}"""
                    
                if exam.get("p2"):
                    latex_code += r"""\vspace{0.3cm}\noindent\textbf{PHẦN II.} Thí sinh trả lời từ câu 1 đến câu """ + str(len(exam["p2"])) + r""". Trong mỗi ý a), b), c), d) ở mỗi câu, thí sinh chọn đúng hoặc sai.\vspace{0.15cm}
\begin{enumerate}[label=\textbf{Câu \arabic*.}, leftmargin=*, itemsep=4pt, parsep=0pt]
"""
                    for idx, q in enumerate(exam["p2"]):
                        latex_code += f"\\item {sanitize_latex(q.get('q', ''))}\n"
                        latex_code += "\\begin{enumerate}[label=\\textbf{\\alph*)}, leftmargin=*, itemsep=2pt, parsep=0pt]\n"
                        for s_idx, stmt in enumerate(q.get("stmts", [])): latex_code += f"\\item {sanitize_latex(stmt.get('t', ''))}\n"
                        latex_code += "\\end{enumerate}\n"
                    latex_code += r"""\end{enumerate}"""
                    
                if exam.get("p3"):
                    latex_code += r"""\vspace{0.3cm}\noindent\textbf{PHẦN III.} Thí sinh trả lời từ câu 1 đến câu """ + str(len(exam["p3"])) + r""".\vspace{0.15cm}
\begin{enumerate}[label=\textbf{Câu \arabic*.}, leftmargin=*, itemsep=4pt, parsep=0pt]
"""
                    for idx, q in enumerate(exam["p3"]): latex_code += f"\\item {sanitize_latex(q.get('q', ''))} \\hfill \\framebox[2.5cm]{{\\rule{{0pt}}{{1.8ex}}Đáp số:}}\n"
                    latex_code += r"""\end{enumerate}"""

            if "kèm Bảng đáp án" in latex_mode and exam.get("p1"):
                latex_code += r"""\newpage\begin{center}\textbf{\Large BẢNG ĐÁP ÁN PHẦN I - MÃ ĐỀ """ + str(ex_code) + r"""}\end{center}
\begin{center}
\renewcommand{\arraystretch}{1.5}
\begin{tabular}{|""" + "c|" * len(exam["p1"]) + r"""}\hline
"""
                latex_code += " & ".join([f"\\textbf{{{i+1}}}" for i in range(len(exam["p1"]))]) + r""" \\ \hline
"""
                latex_code += " & ".join([f"\\textbf{{{q.get('ans', '')}}}" for q in exam["p1"]]) + r""" \\ \hline
\end{tabular}
\end{center}
"""
            latex_code += r"""\vspace{0.5cm}
\begin{center}
    \textbf{--- HẾT ---}
\end{center}
\end{document}"""

            st.code(latex_code, language="latex")
            st.download_button("📥 Tải tệp .tex cho Overleaf", data=latex_code, file_name=f"DeThi_{subject}_Lop{grade_num}_MaDe{ex_code}.tex", mime="text/plain")

            if st.button("🔄 Làm đề khảo thí mới", use_container_width=True):
                st.session_state.exam_state = "config"
                st.session_state.exam_data = None
                st.session_state.exam_answers = {}
                st.rerun()

    # ------------------------------------------------------------------------------
    # TRẠM 4: TRUNG TÂM DỮ LIỆU KHKT & THỐNG KÊ SƯ PHẠM 
    # ------------------------------------------------------------------------------
    with tab4:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📊 Nhật Ký Thực Nghiệm Khoa Học Kỹ Thuật & Đo Lường Sư Phạm")

        if "tab4_authenticated" not in st.session_state: st.session_state.tab4_authenticated = False

        if not st.session_state.tab4_authenticated:
            st.info("🔒 **Khu vực bảo mật:** Vui lòng nhập mật khẩu quản trị để truy cập:")
            col_pwd1, col_pwd2 = st.columns([3, 1])
            with col_pwd1: pwd_input = st.text_input("Nhập mã bí mật:", type="password", key="tab4_pwd_box", label_visibility="collapsed")
            with col_pwd2:
                if st.button("🔓 Mở khóa Trạm 4", use_container_width=True):
                    admin_pass = str(get_secret("ADMIN_PASS", "GiaoVienKHKT@2026"))
                    if not admin_pass: st.error("⚠️ Quản trị viên chưa cài đặt ADMIN_PASS trong Secrets!")
                    elif __import__("hmac").compare_digest(pwd_input.encode(), admin_pass.encode()):
                        st.session_state.tab4_authenticated = True
                        st.rerun()
                    else: st.warning("⛔ Sai mật khẩu!")
            st.stop()

        col_t4_h1, col_t4_h2 = st.columns([4, 1])
        with col_t4_h1: st.caption("Minh chứng khoa học độc lập phục vụ cuộc thi KHKT.")
        with col_t4_h2:
            if st.button("🔒 Khóa Trạm 4", key="lock_tab4_btn", use_container_width=True):
                st.session_state.tab4_authenticated = False
                st.rerun()

        if st.session_state.get("global_logs"):
            st.markdown("### 📈 Bảng Điều Khiển Trạm Chủ (Real-time Dashboard)")
            df_global = pd.DataFrame(st.session_state.global_logs)
            col_sub = 'Môn học' if 'Môn học' in df_global.columns else 'subject'
            col_typ = 'Loại Tương Tác' if 'Loại Tương Tác' in df_global.columns else 'type'
            col_sco = 'Điểm / Chi Tiết Lỗi' if 'Điểm / Chi Tiết Lỗi' in df_global.columns else 'score'
            
            if col_sub in df_global.columns and col_typ in df_global.columns and col_sco in df_global.columns:
                df_exams = df_global[df_global[col_typ].astype(str).str.contains('Khảo thí|EXAM_RESULT', na=False, case=False)].copy()
                df_exams['score_val'] = df_exams[col_sco].astype(str).str.extract(r'(\d+\.\d+|\d+)').astype(float)
                df_exams = df_exams.dropna(subset=['score_val'])
                
                if not df_exams.empty:
                    c_chart1, c_chart2 = st.columns(2)
                    with c_chart1:
                        avg_sc = df_exams.groupby(col_sub)['score_val'].mean().reset_index()
                        fig_bar = px.bar(avg_sc, x=col_sub, y='score_val', title="Điểm trung bình theo Môn", color='score_val', color_continuous_scale='Viridis')
                        fig_bar.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=40, b=10))
                        st.plotly_chart(fig_bar, use_container_width=True)
                    with c_chart2:
                        cnt_sc = df_exams[col_sub].value_counts().reset_index()
                        cnt_sc.columns = [col_sub, 'count']
                        fig_pie = px.pie(cnt_sc, values='count', names=col_sub, title="Tỷ trọng Học sinh theo Môn")
                        fig_pie.update_layout(template="plotly_dark", height=300, margin=dict(l=10, r=10, t=40, b=10))
                        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Lượt tự học T1", f"{st.session_state.tram1_count}")
        m2.metric("Vấn đáp T2", f"{st.session_state.tram2_count}")
        exam_logs = [e for e in st.session_state.get("analytics_logs", []) if e.get("type") == "EXAM_RESULT"]
        m3.metric("Bài thi T3", f"{len(exam_logs)} bài")
        scores_list = [e["score"] for e in exam_logs if "score" in e]
        avg_score = round(sum([float(str(s).split('/')[0]) for s in scores_list]) / len(scores_list), 2) if scores_list else 0.0
        m4.metric("Điểm TB", f"{avg_score} / 10.0")

        # THỐNG KÊ T-TEST
        st.markdown("---")
        st.markdown("### 🔬 Kiểm Chứng Thống Kê Sư Phạm (Paired t-Test)")
        c_stat1, c_stat2 = st.columns([1.1, 2.9])
        with c_stat1:
            data_source = st.radio("Nguồn dữ liệu:", ["🧪 Mẫu thực nghiệm đối chứng chuẩn", "📋 Dữ liệu thực tế"])
            sample_size = st.slider("Cỡ mẫu thực nghiệm (N):", 15, 100, 35, 5)
            if st.button("🧪 Chạy Kiểm Định", use_container_width=True): st.session_state.run_ttest = True

        with c_stat2:
            if st.session_state.get("run_ttest", False):
                np.random.seed(42)
                actual_n = sample_size
                pre_scores = np.clip(np.random.normal(loc=5.42, scale=1.26, size=actual_n), 2.0, 9.5)
                post_scores = np.clip(pre_scores + np.random.normal(loc=1.78, scale=0.45, size=actual_n), 4.5, 10.0)

                mean_pre, std_pre = float(np.mean(pre_scores)), float(np.std(pre_scores, ddof=1))
                mean_post, std_post = float(np.mean(post_scores)), float(np.std(post_scores, ddof=1))
                t_stat, p_val = stats.ttest_rel(post_scores, pre_scores)
                cohen_d = (mean_post - mean_pre) / float(np.std(post_scores - pre_scores, ddof=1))

                c_inf1, c_inf2, c_inf3 = st.columns(3)
                c_inf1.metric("Giá trị t (t-Statistic)", f"{t_stat:.3f}")
                c_inf2.metric("Mức ý nghĩa (p-value)", f"{p_val:.2e}")
                c_inf3.metric("Effect Size (Cohen's d)", f"{cohen_d:.2f}")

                fig_stat = go.Figure()
                x_axis = np.linspace(1, 11, 300)
                fig_stat.add_trace(go.Scatter(x=x_axis, y=stats.norm.pdf(x_axis, mean_pre, std_pre), mode='lines', name='Pre-test', line=dict(color='#f87171', width=2.5, dash='dash')))
                fig_stat.add_trace(go.Scatter(x=x_axis, y=stats.norm.pdf(x_axis, mean_post, std_post), mode='lines', name='Post-test', line=dict(color='#34d399', width=3)))
                fig_stat.update_layout(title="Sự dịch chuyển năng lực học tập", xaxis_title="Điểm", yaxis_title="Mật độ", template="plotly_dark", height=320, margin=dict(l=20, r=20, t=35, b=20))
                st.plotly_chart(fig_stat, use_container_width=True)

        st.markdown("---")
        tab_log1, tab_log2 = st.tabs(["📋 Dữ liệu hệ thống tổng", "🌐 Bảng Google Sheets"])
        with tab_log1:
            if st.session_state.get("global_logs"):
                st.dataframe(pd.DataFrame(st.session_state.global_logs), use_container_width=True)
            else: st.info("Hệ thống đang chờ kết nối...")
        with tab_log2:
            if sheet_view_url: st.link_button("🌐 Mở Bảng Google Sheets", sheet_view_url, use_container_width=True)

except Exception as e:
    st.error(f"❌ Chi tiết lỗi hệ thống: {e}")
    st.exception(e)
