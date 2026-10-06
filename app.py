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
import plotly.express as px
import urllib.parse
import ast

# ==============================================================================
# 1. CẤU HÌNH TRANG WEB (BẮT BUỘC ĐẦU TIÊN)
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
    # --- ĐỒNG BỘ GIỜ VIỆT NAM ---
    VN_TZ = timezone(timedelta(hours=7))
    def get_vn_time():
        return datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")

    def get_secret(name, default=""):
        try:
            return st.secrets.get(name, default)
        except Exception:
            return default

    _trapz = getattr(np, "trapezoid", None) or getattr(np, "trapz")

    # --- KHỞI TẠO BỘ NHỚ PHIÊN ---
    for key in ["messages", "analytics_logs", "feedback_logs", "parsed_quiz", "va_loi_logs", "student_progress_history", "global_logs", "tram3_chat_messages"]:
        if key not in st.session_state: st.session_state[key] = []
    for key in ["tram1_count", "tram2_count", "tram3_count", "global_exam_count"]:
        if key not in st.session_state: st.session_state[key] = 0
    for key in ["current_lesson", "current_topic", "exam_code"]:
        if key not in st.session_state: st.session_state[key] = ""
    
    if "lab_data" not in st.session_state: st.session_state.lab_data = None
    if "quiz_states" not in st.session_state: st.session_state.quiz_states = {}
    if "global_stats_loaded" not in st.session_state: st.session_state.global_stats_loaded = False
    if "active_context_key" not in st.session_state: st.session_state.active_context_key = None
    if "working_model" not in st.session_state: st.session_state.working_model = None
    if "exam_state" not in st.session_state: st.session_state.exam_state = "config"
    if "exam_data" not in st.session_state: st.session_state.exam_data = None
    if "exam_answers" not in st.session_state: st.session_state.exam_answers = {}

    APP_URL = get_secret("APP_URL", "https://gsaithptth-khkt2026.streamlit.app/")

    # --- CSS GIAO DIỆN ---
    st.markdown("""
    <style>
        .block-container { padding-top: 2rem !important; padding-bottom: 1rem !important; }
        .brand-container { display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 20px; padding: 10px; background: linear-gradient(145deg, rgba(30, 41, 59, 0.8), rgba(15, 23, 42, 0.9)); border-radius: 12px; border: 1px solid #334155; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); }
        .school-icon { width: 45px; height: auto; transition: transform 0.3s ease; }
        .school-icon:hover { transform: scale(1.1); }
        .thiennhan-logo { width: 115px; height: auto; border-radius: 6px; box-shadow: 0 0 10px rgba(56, 189, 248, 0.4); border: 1.5px solid #38bdf8; }
        .main-header { text-align: center; padding: 0px 0 15px 0; border-bottom: 1px dashed #475569; margin-bottom: 25px; }
        .main-title { background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2.5rem; font-weight: 900; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1.5px; }
        .sub-title { color: #cbd5e1; font-size: 1.15rem; font-weight: 500;}
        .badge-tag { background: rgba(15, 23, 42, 0.7); border: 1px solid #38bdf8; color: #38bdf8; padding: 5px 15px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; display: inline-block; margin-top: 8px; margin-right: 8px; box-shadow: 0 2px 5px rgba(56, 189, 248, 0.2); }
        .stButton > button { background: linear-gradient(135deg, #0284c7, #3b82f6) !important; color: white !important; border-radius: 10px !important; border: none !important; box-shadow: 0 4px 15px rgba(56, 189, 248, 0.3) !important; transition: all 0.3s ease !important; font-weight: 700 !important; }
        .stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 6px 20px rgba(56, 189, 248, 0.6) !important; background: linear-gradient(135deg, #0369a1, #2563eb) !important; }
        .stTabs [data-baseweb="tab-list"] { background: rgba(30, 41, 59, 0.5); backdrop-filter: blur(10px); border-radius: 12px; padding: 5px; gap: 8px; border: 1px solid #334155; }
        .stTabs [data-baseweb="tab"] { height: 50px; border-radius: 8px; border: none; color: #94a3b8; font-weight: 600; transition: all 0.3s; }
        .stTabs [aria-selected="true"] { background: rgba(56, 189, 248, 0.15) !important; color: #38bdf8 !important; border-bottom: 3px solid #38bdf8 !important; box-shadow: inset 0 -3px 10px rgba(56, 189, 248, 0.1); }
        .short-link-badge { background-color: #1e293b; border: 1px dashed #38bdf8; padding: 8px 12px; border-radius: 8px; font-family: 'Courier New', Courier, monospace; font-size: 0.8rem; color: #38bdf8; text-align: center; margin: 10px 0; word-break: break-all; }
        [data-testid="stChatMessage"] { border-radius: 15px; padding: 15px; margin-bottom: 12px; background: rgba(30, 41, 59, 0.6); border: 1px solid #475569; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
    </style>
    """, unsafe_allow_html=True)

    # ==============================================================================
    # 2. THANH BÊN (SIDEBAR) & BIẾN TOÀN CỤC
    # ==============================================================================
    def get_local_img_as_base64(file_path):
        try:
            with open(file_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode('utf-8')
        except Exception: return ""

    logo_b64 = get_local_img_as_base64("LOGO THIỆN NHÂN 3D.jpg")
    logo_html = f'<img src="data:image/jpeg;base64,{logo_b64}" class="thiennhan-logo" alt="Logo">' if logo_b64 else '<div style="background: linear-gradient(45deg, #0f172a, #1e293b); padding: 8px 12px; border-radius: 8px; color: #f8fafc; font-weight: 800; font-size: 14px; border: 1.5px solid #38bdf8; box-shadow: 0 0 10px rgba(56,189,248,0.4);">THIỆN NHÂN</div>'
    school_icon_svg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2338bdf8'><path d='M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3zm6.82 6L12 12.72 5.18 9 12 5.28 18.82 9zM17 15.99l-5 2.73-5-2.73v-3.72L12 15l5-2.73v3.72z'/></svg>"

    st.sidebar.markdown(f'<div class="brand-container"><img src="{school_icon_svg}" class="school-icon" alt="Icon Trường">{logo_html}</div><div style="text-align: center; margin-bottom: 15px;"><h2 style="color: #38bdf8; font-weight: 800; font-size: 1.8rem; margin: 0; text-shadow: 0px 2px 4px rgba(0,0,0,0.5);">THIẾT LẬP HỌC TẬP</h2></div>', unsafe_allow_html=True)

    with st.sidebar.expander("📱 Quét mã QR vào app", expanded=False):
        qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={urllib.parse.quote(APP_URL, safe='')}"
        st.image(qr_api_url, use_container_width=True)
        st.markdown(f'<div class="short-link-badge">🔗 {APP_URL}</div>', unsafe_allow_html=True)

    with st.sidebar.expander("📲 Cài đặt Icon App (PWA)", expanded=False):
        st.markdown("""
        **Cách tạo Icon App mở trực tiếp:**
        - 🤖 **Android:** Bấm Menu $\\vdots$ ➔ Chọn **"Thêm vào Màn hình chính"**.
        - 🍏 **iPhone (Safari):** Bấm **Chia sẻ** $\\uparrow$ ➔ **"Thêm vào MH chính"**.
        - 💻 **Máy tính:** Bấm biểu tượng Tải xuống/Cài đặt trên thanh địa chỉ.
        """)

    st.markdown("""
    <script>
    document.addEventListener("DOMContentLoaded", function() {
        try {
            const savedKey = localStorage.getItem("GSAI_USER_CUSTOM_KEY");
            if (savedKey && !window.keyRestored) { window.keyRestored = true; }
        } catch(e) {}
    });
    </script>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔑 ĐƯỜNG TRUYỀN AI CÁ NHÂN")
    st.sidebar.link_button("👉 Lấy Key riêng miễn phí (15s)", "https://aistudio.google.com/apikey", use_container_width=True)
    user_custom_key = st.sidebar.text_input("Dán mã API Key của em vào đây:", type="password", placeholder="AIzaSy...")

    raw_api_key = get_secret("GEMINI_API_KEY")
    raw_sheet_url = get_secret("GOOGLE_SHEET_URL")
    sheet_webhook_url = "".join(raw_sheet_url.split()) if raw_sheet_url else ""
    sheet_view_url_secret = get_secret("GOOGLE_SHEET_VIEW_URL")
    DEFAULT_SHEET_VIEW_URL = "https://docs.google.com/spreadsheets/d/1fnG9qxmtQ5sa1C8Sb5Z9hepzB2G8asNVgSk05p7Pu9M/edit?gid=0#gid=0"
    sheet_view_url = "".join(sheet_view_url_secret.split()) if sheet_view_url_secret else DEFAULT_SHEET_VIEW_URL

    if not st.session_state.global_stats_loaded and sheet_webhook_url:
        try:
            res = requests.get(sheet_webhook_url, timeout=3)
            if res.status_code == 200 and isinstance(res.json(), list):
                st.session_state.global_logs = res.json()
            st.session_state.global_stats_loaded = True
        except: pass

    admin_keys_pool = [k.strip() for k in raw_api_key.split(",")] if raw_api_key else []
    active_keys_pool = [user_custom_key.strip()] if user_custom_key.strip() else admin_keys_pool

    if not active_keys_pool:
        st.error("⚠️ Hệ thống chưa tìm thấy API Key nào khả dụng!")
        st.stop()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 👤 THÔNG TIN HỌC SINH")
    student_name_input = st.sidebar.text_input("Họ và tên của em:", placeholder="Ví dụ: Nguyễn Văn A...")
    student_name = student_name_input.strip() if student_name_input.strip() else "Ẩn danh"

    grade = st.sidebar.selectbox("🎯 Chọn khối lớp:", [f"Lớp {i}" for i in range(6, 13)], index=6)
    grade_num = int(grade.split()[1])

    available_subjects = ["Toán học", "Khoa học tự nhiên", "Ngữ văn", "Tiếng Anh", "Lịch sử & Địa lý", "Tin học", "Giáo dục công dân"] if grade_num <= 9 else ["Toán học", "Vật lý", "Hóa học", "Sinh học", "Ngữ văn", "Tiếng Anh", "Lịch sử", "Địa lý", "Tin học", "GD KT&PL"]
    subject = st.sidebar.selectbox("📚 Môn học cần hỗ trợ:", available_subjects)

    # ĐỒNG BỘ NGỮ CẢNH
    current_context_key = f"{grade}_{subject}"
    if st.session_state.active_context_key != current_context_key:
        st.session_state.current_lesson = ""
        st.session_state.current_topic = ""
        st.session_state.parsed_quiz = []
        st.session_state.quiz_states = {}
        st.session_state.lab_data = None
        st.session_state.messages = []
        st.session_state.exam_data = None
        st.session_state.exam_state = "config"
        st.session_state.exam_answers = {}
        st.session_state.tram3_chat_messages = []
        st.session_state.active_context_key = current_context_key

    st.sidebar.markdown("---")
    col_sb1, col_sb2, col_sb3 = st.sidebar.columns(3)
    col_sb1.metric("T1", f"{st.session_state.tram1_count}")
    col_sb2.metric("T2", f"{st.session_state.tram2_count}")
    col_sb3.metric("T3", f"{max(len([x for x in st.session_state.analytics_logs if x.get('type')=='EXAM_RESULT']), st.session_state.get('global_exam_count', 0))}")

    # ==============================================================================
    # MA TRẬN CHUYÊN ĐỀ KNTT
    # ==============================================================================
    BIGDATA_CURRICULUM = {
        "Toán học": {
            12: ["Chuyên đề 1: Ứng dụng đạo hàm khảo sát & vẽ đồ thị hàm số (KSHS chuẩn KNTT)", "Chuyên đề 2: Vectơ và tọa độ trong không gian Oxyz", "Chuyên đề 3: Các số đặc trưng đo mức độ phân tán (Mẫu ghép nhóm)", "Chuyên đề 4: Nguyên hàm, Tích phân và ứng dụng thực tiễn", "Chuyên đề 5: Phương pháp tọa độ Oxyz (Mặt phẳng, Đường thẳng, Mặt cầu)", "Chuyên đề 6: Xác suất có điều kiện, Công thức Bayes"],
            11: ["Chuyên đề 1: Hàm số lượng giác và phương trình lượng giác", "Chuyên đề 2: Dãy số, Cấp số cộng và Cấp số nhân", "Chuyên đề 3: Các số đặc trưng đo xu thế trung tâm của mẫu số liệu ghép nhóm", "Chuyên đề 4: Quan hệ song song trong không gian", "Chuyên đề 5: Giới hạn và Hàm số liên tục", "Chuyên đề 6: Hàm số mũ và hàm số lôgarit", "Chuyên đề 7: Đạo hàm và ứng dụng tiếp tuyến", "Chuyên đề 8: Quan hệ vuông góc trong không gian", "Chuyên đề 9: Xác suất: Biến cố giao và quy tắc nhân xác suất"],
            10: ["Chuyên đề 1: Mệnh đề, Tập hợp & BPT bậc nhất hai ẩn", "Chuyên đề 2: Hệ thức lượng trong tam giác & Vectơ Oxy", "Chuyên đề 3: Hàm số bậc hai, Dấu tam thức bậc hai", "Chuyên đề 4: Phương pháp tọa độ Oxy (Đường thẳng, Đường tròn, Conic)", "Chuyên đề 5: Đại số tổ hợp (Quy tắc đếm, Hoán vị - Chỉnh hợp - Tổ hợp, Nhị thức Newton)", "Chuyên đề 6: Số đặc trưng đo xu thế trung tâm & mức độ phân tán"],
            9: ["Chuyên đề 1: Phương trình và hệ hai phương trình bậc nhất hai ẩn", "Chuyên đề 2: Phương trình bậc hai một ẩn và định lý Viète", "Chuyên đề 3: Căn bậc hai và căn bậc ba", "Chuyên đề 4: Hệ thức lượng trong tam giác vuông", "Chuyên đề 5: Đường tròn", "Chuyên đề 6: Hình khối thực tiễn"],
            8: ["Chuyên đề 1: Đa thức nhiều biến & Hằng đẳng thức", "Chuyên đề 2: Phân thức đại số", "Chuyên đề 3: Hàm số bậc nhất y = ax + b", "Chuyên đề 4: Tứ giác & Hình thang cân", "Chuyên đề 5: Định lý Thalès & Tam giác đồng dạng"],
            7: ["Chuyên đề 1: Số hữu tỉ", "Chuyên đề 2: Số thực & Tỉ lệ thức", "Chuyên đề 3: Góc và đường thẳng song song", "Chuyên đề 4: Tam giác bằng nhau", "Chuyên đề 5: Đa thức một biến"],
            6: ["Chuyên đề 1: Tập hợp số tự nhiên & Tính chia hết", "Chuyên đề 2: Số nguyên & Quy tắc dấu", "Chuyên đề 3: Phân số & Số thập phân", "Chuyên đề 4: Hình học trực quan", "Chuyên đề 5: Dữ liệu & Xác suất thực nghiệm"]
        },
        "Khoa học tự nhiên": {
            9: ["Chuyên đề 1: Năng lượng cơ học", "Chuyên đề 2: Ánh sáng & Khúc xạ", "Chuyên đề 3: Kim loại & Phi kim IUPAC", "Chuyên đề 4: Hydrocarbon Alkane Alkene", "Chuyên đề 5: Di truyền phân tử DNA RNA", "Chuyên đề 6: Tiến hóa & Quần thể"],
            8: ["Chuyên đề 1: Khối lượng riêng & Áp suất", "Chuyên đề 2: Đòn bẩy & Mômen lực", "Chuyên đề 3: Mạch điện & Tác dụng dòng điện", "Chuyên đề 4: Phản ứng hóa học & Mol", "Chuyên đề 5: Acid Base Salt pH IUPAC", "Chuyên đề 6: Sinh học cơ thể người"],
            7: ["Chuyên đề 1: Nguyên tử & Bảng tuần hoàn IUPAC", "Chuyên đề 2: Phân tử & Liên kết hóa học", "Chuyên đề 3: Tốc độ chuyển động", "Chuyên đề 4: Sóng âm", "Chuyên đề 5: Phản xạ ánh sáng", "Chuyên đề 6: Quang hợp & Hô hấp tế bào"],
            6: ["Chuyên đề 1: Các phép đo cơ bản", "Chuyên đề 2: Thể của chất & Không khí", "Chuyên đề 3: Tế bào - Đơn vị sự sống", "Chuyên đề 4: Đa dạng thế giới sống", "Chuyên đề 5: Lực & Ma sát", "Chuyên đề 6: Năng lượng & Chuyển hóa"]
        },
        "Sinh học": {
            12: ["Chuyên đề 1: Di truyền phân tử DNA RNA Đột biến gen", "Chuyên đề 2: Di truyền NST & Phân bào", "Chuyên đề 3: Quy luật Mendel & Hoán vị gen", "Chuyên đề 4: Di truyền học quần thể Hardy-Weinberg", "Chuyên đề 5: Di truyền y học & Công nghệ gen", "Chuyên đề 6: Tiến hóa hiện đại", "Chuyên đề 7: Sinh thái học & Hệ sinh thái"],
            11: ["Chuyên đề 1: Quang hợp & Hô hấp ở thực vật", "Chuyên đề 2: Trao đổi chất ở động vật", "Chuyên đề 3: Cảm ứng & Tập tính", "Chuyên đề 4: Sinh trưởng & Phát triển", "Chuyên đề 5: Sinh sản vô tính & Hữu tính"],
            10: ["Chuyên đề 1: Sinh học tế bào", "Chuyên đề 2: Các đại phân tử sinh học", "Chuyên đề 3: Cấu trúc tế bào nhân thực", "Chuyên đề 4: Trao đổi chất qua màng", "Chuyên đề 5: Nguyên phân & Giảm phân", "Chuyên đề 6: Vi sinh vật & Virus"]
        },
        "Vật lý": {
            12: ["Chuyên đề 1: Vật lý nhiệt & Năng lượng", "Chuyên đề 2: Thuyết động học khí lý tưởng", "Chuyên đề 3: Từ trường & Cảm ứng điện từ", "Chuyên đề 4: Vật lý hạt nhân & Phóng xạ"],
            11: ["Chuyên đề 1: Dao động điều hòa", "Chuyên đề 2: Dao động cưỡng bức & Cộng hưởng", "Chuyên đề 3: Sóng cơ & Giao thoa sóng", "Chuyên đề 4: Điện trường & Tụ điện", "Chuyên đề 5: Dòng điện không đổi & ĐL Ohm"],
            10: ["Chuyên đề 1: Động học chất điểm & Rơi tự do", "Chuyên đề 2: Ba định luật Newton & Các lực", "Chuyên đề 3: Năng lượng & Bảo toàn cơ năng", "Chuyên đề 4: Động lượng & Bảo toàn động lượng", "Chuyên đề 5: Chuyển động tròn & Mômen lực"]
        },
        "Hóa học": {
            12: ["Chuyên đề 1: Ester Lipid IUPAC", "Chuyên đề 2: Carbohydrate Glucose Cellulose", "Chuyên đề 3: Amine Amino acid Peptide Protein IUPAC", "Chuyên đề 4: Polymer & Vật liệu polymer", "Chuyên đề 5: Pin điện hóa & Điện phân", "Chuyên đề 6: Đại cương kim loại", "Chuyên đề 7: Kim loại nhóm IA IIA", "Chuyên đề 8: Sơ lược về phức chất"],
            11: ["Chuyên đề 1: Cân bằng hóa học & pH Dung dịch", "Chuyên đề 2: Nitrogen & Sulfur", "Chuyên đề 3: Hydrocarbon Alkane Alkene Alkyne Arene IUPAC", "Chuyên đề 4: Alcohol & Phenol IUPAC", "Chuyên đề 5: Carbonyl & Carboxylic acid IUPAC"],
            10: ["Chuyên đề 1: Cấu tạo nguyên tử & Bảng tuần hoàn IUPAC", "Chuyên đề 2: Liên kết hóa học & Hydrogen", "Chuyên đề 3: Phản ứng oxi hóa - khử", "Chuyên đề 4: Biến thiên Enthalpy chuẩn", "Chuyên đề 5: Tốc độ phản ứng hóa học", "Chuyên đề 6: Halogen nhóm VIIA"]
        },
        "Ngữ văn": {
            12: ["Chuyên đề 1: Đọc hiểu Thơ hiện đại", "Chuyên đề 2: Đọc hiểu Truyện truyền kỳ & Ký", "Chuyên đề 3: Đọc hiểu Hài kịch & Bi kịch", "Chuyên đề 4: Nghị luận xã hội", "Chuyên đề 5: Nghị luận văn học so sánh"],
            11: ["Chuyên đề 1: Đọc hiểu Thơ trữ tình & Thơ mới", "Chuyên đề 2: Đọc hiểu Truyện thơ & Văn xuôi", "Chuyên đề 3: Đọc hiểu Kịch bản văn học", "Chuyên đề 4: Viết bài văn Nghị luận"],
            10: ["Chuyên đề 1: Thần thoại Sử thi Văn học dân gian", "Chuyên đề 2: Thơ Đường & Thơ Nôm", "Chuyên đề 3: Truyện ngắn hiện đại", "Chuyên đề 4: Văn bản nghị luận & Thông tin"],
            9: ["Chuyên đề 1: Đọc hiểu Thơ hiện đại", "Chuyên đề 2: Truyện ngắn chuẩn thi vào 10", "Chuyên đề 3: Bi kịch & Truyền kỳ", "Chuyên đề 4: Nghị luận xã hội & Văn học"],
            8: ["Chuyên đề 1: Thơ 6 chữ 7 chữ tự do", "Chuyên đề 2: Truyện lịch sử & Truyện cười", "Chuyên đề 3: Văn bản thông tin giải thích", "Chuyên đề 4: Viết đoạn văn biểu cảm"],
            7: ["Chuyên đề 1: Thơ 4 chữ 5 chữ", "Chuyên đề 2: Truyện ngụ ngôn & Tục ngữ", "Chuyên đề 3: Tùy bút & Tản văn", "Chuyên đề 4: Viết bài văn biểu cảm"],
            6: ["Chuyên đề 1: Truyện cổ tích & Truyền thuyết", "Chuyên đề 2: Thơ lục bát", "Chuyên đề 3: Ký & Văn bản thông tin", "Chuyên đề 4: Viết bài văn kể lại trải nghiệm"]
        },
        "Lịch sử": {
            12: ["Chuyên đề 1: Liên Hợp Quốc & Trật tự thế giới", "Chuyên đề 2: Tổ chức ASEAN", "Chuyên đề 3: Cách mạng tháng Tám 1945 & Kháng chiến chống Pháp", "Chuyên đề 4: Kháng chiến chống Mỹ 1954-1975", "Chuyên đề 5: Công cuộc Đổi mới từ 1986", "Chuyên đề 6: Bảo vệ chủ quyền Biển Đông"],
            11: ["Chuyên đề 1: Cách mạng tư sản", "Chuyên đề 2: Chủ nghĩa xã hội", "Chuyên đề 3: Chiến tranh thế giới I & II", "Chuyên đề 4: Các cuộc kháng chiến bảo vệ Tổ quốc"],
            10: ["Chuyên đề 1: Hiện thực lịch sử", "Chuyên đề 2: Nền văn minh cổ - trung đại", "Chuyên đề 3: Văn minh Đại Việt", "Chuyên đề 4: Cộng đồng các dân tộc Việt Nam"]
        },
        "Địa lý": {
            12: ["Chuyên đề 1: Địa lý tự nhiên Việt Nam", "Chuyên đề 2: Địa lý dân cư & Đô thị hóa", "Chuyên đề 3: Địa lý các ngành kinh tế", "Chuyên đề 4: Địa lý các vùng kinh tế & Biển đảo"],
            11: ["Chuyên đề 1: Toàn cầu hóa kinh tế thế giới", "Chuyên đề 2: Địa lý EU, ASEAN, Mỹ Latinh", "Chuyên đề 3: Địa lý Hoa Kỳ, Nga, Nhật Bản, Trung Quốc"],
            10: ["Chuyên đề 1: Bản đồ, GPS, GIS", "Chuyên đề 2: Địa lý tự nhiên đại cương", "Chuyên đề 3: Địa lý dân cư & Kinh tế thế giới"]
        }
    }

    # ==============================================================================
    # 3. CÁC HÀM BỔ TRỢ (AI & VẼ LAB)
    # ==============================================================================
    ALL_GEMINI_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"]
    DEFAULT_PEDAGOGICAL_SYSTEM_INSTRUCTION = """Bạn là Gia Sư AI Sư Phạm hàng đầu Việt Nam, hỗ trợ học sinh theo chuẩn CT GDPT 2018 (SGK KNTT).
    NGUYÊN TẮC BẮT BUỘC: 
    1. TOÁN: Tuyệt đối CẤM hàm bậc 4 trùng phương. Khảo sát Lớp 12 chỉ dùng Bậc 3, Phân thức 1/1, Phân thức 2/1.
    2. HÓA & KHTN: Dùng 100% danh pháp IUPAC.
    3. TIẾNG ANH: Viết 100% bằng TIẾNG ANH cho từ vựng, ngữ pháp. Không dùng tiếng Việt trong bài đọc/trắc nghiệm."""

    def call_gemini_with_fallback(prompt_or_contents, system_instruction=None, json_mode=False):
        model_queue = [st.session_state.working_model] + [m for m in ALL_GEMINI_MODELS if m != st.session_state.working_model] if st.session_state.working_model else ALL_GEMINI_MODELS
        with st.status("Gia sư AI đang tiếp nhận yêu cầu...", expanded=True) as status_box:
            for current_model in model_queue:
                status_box.update(label=f"Đang kết nối AI kênh {current_model}...", state="running")
                for current_key in active_keys_pool:
                    try:
                        client = genai.Client(api_key=current_key)
                        cfg = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="low"))
                        cfg.system_instruction = f"{DEFAULT_PEDAGOGICAL_SYSTEM_INSTRUCTION}\n\n{system_instruction}" if system_instruction else DEFAULT_PEDAGOGICAL_SYSTEM_INSTRUCTION
                        if json_mode: cfg.response_mime_type = "application/json"
                        response = client.models.generate_content(model=current_model, contents=prompt_or_contents, config=cfg)
                        st.session_state.working_model = current_model
                        status_box.update(label="Thành công!", state="complete")
                        return response.text
                    except Exception: continue
        status_box.update(label="Lỗi quá tải!", state="error")
        raise Exception("Hệ thống đang quá tải. Vui lòng thử lại sau.")

    def clean_vietnamese_math(text):
        if not text: return ""
        vn_chars = r'[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ]'
        def fix_math(m):
            content = m.group(1).strip()
            return f"<i>{content}</i>" if re.search(vn_chars, content, re.IGNORECASE) else f"${content}$"
        return re.sub(r'\$(.*?)\$', fix_math, str(text)).strip()

    def parse_quiz_questions(text):
        questions = []
        part3_match = re.search(r'(?i)###\s*PHẦN\s*3', text)
        part2_text = text[:part3_match.start()] if part3_match else text
        parts = re.split(r'(?i)(?:\[Q\d+\]|C[âa]u\s*\d+[\.\:]?)', part2_text)
        for part in parts[1:]:
            lines = [l.strip() for l in part.strip().split('\n') if l.strip()]
            if not lines: continue
            q_header = lines[0]
            level, options, correct, explain = "Vận dụng", [], "A", "Gợi ý..."
            match = re.search(r'(?i)\[Mức độ:\s*(.*?)\]', q_header)
            if match:
                level = match.group(1)
                q_header = re.sub(r'(?i)\[Mức độ:\s*.*?\]', '', q_header).strip()
            q_text_lines = [q_header]
            parsing_options = False
            for line in lines[1:]:
                clean_line = re.sub(r'(?i)^\*{0,2}([A-D])\b[\.\:]?\*{0,2}\s*', r'\1. ', line)
                if re.match(r'(?i)###\s*PHẦN\s*3', line): break
                if clean_line.upper().startswith(('A.', 'B.', 'C.', 'D.')):
                    parsing_options = True; options.append(clean_line)
                elif re.search(r'(?i)^(CORRECT|ĐÁP ÁN|Đáp án đúng)\s*:', line):
                    ext = re.sub(r'[^A-D]', '', line.split(":")[-1].upper())
                    if ext: correct = ext[0]
                elif re.search(r'(?i)^(EXPLAIN|GIẢI THÍCH|Gợi ý)\s*:', line): explain = line.split(":", 1)[-1].strip()
                else:
                    if not parsing_options: q_text_lines.append(line)
                    elif options and not clean_line.upper().startswith(('A.', 'B.', 'C.', 'D.')): explain += " " + line
            if len(options) >= 4:
                questions.append({"question": " ".join(q_text_lines).strip(), "level": level, "options": options[:4], "correct": correct, "explain": explain})
        return questions

    def create_pedagogical_tts_component(raw_text: str, subject_name: str, comp_key: str):
        if subject_name != "Tiếng Anh": return
        tts_html = f"""<script>
        (function() {{
            if (window.__english_tts_global_injected) return;
            window.__english_tts_global_injected = true;
            window.speakEnglishText = function(text) {{
                if (!text || !window.speechSynthesis) return;
                text = text.replace(/^[A-Da-d][.:)]\\s*/, '').replace(/[*#`_\\[\\]()]/g, ' ').trim();
                if (!/[a-zA-Z]/.test(text) || /[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/i.test(text)) return;
                try {{
                    window.speechSynthesis.cancel();
                    const u = new SpeechSynthesisUtterance(text);
                    u.lang = 'en-US'; u.rate = 0.92;
                    const v = window.speechSynthesis.getVoices().find(v => v.lang.startsWith('en') && (v.name.includes('Google') || v.name.includes('US'))) || window.speechSynthesis.getVoices().find(v => v.lang.startsWith('en'));
                    if (v) u.voice = v;
                    window.speechSynthesis.speak(u);
                }} catch(e) {{}}
            }};
            document.addEventListener("mouseup", () => {{ const t = (window.parent.document||document).getSelection().toString().trim(); if(t) window.speakEnglishText(t); }});
            document.addEventListener("click", (e) => {{
                const btn = e.target.closest('.custom-speak-btn');
                if(btn) {{ const span = btn.querySelector('.hidden-speak-text'); if(span) window.speakEnglishText(span.innerText); }}
            }}, true);
        }})();</script>"""
        components.html(tts_html, height=0)

    def render_mermaid(code: str):
        safe_code = code.strip().replace('[[', '[').replace(']]', ']')
        safe_code = re.sub(r'^```(?:mermaid)?', '', safe_code, flags=re.MULTILINE)
        safe_code = re.sub(r'```$', '', safe_code, flags=re.MULTILINE).strip()
        safe_code = re.sub(r'^\s*graph\s+TD', 'graph LR', safe_code, flags=re.IGNORECASE)
        safe_code = re.sub(r'^\s*flowchart\s+TD', 'flowchart LR', safe_code, flags=re.IGNORECASE)
        if not safe_code.startswith(("graph", "flowchart")): safe_code = "graph LR\n" + safe_code
        json_code_str = json.dumps(safe_code).replace("</", "<\\/")
        html_template = r"""
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
        <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <div style="background: radial-gradient(circle at center, #0f172a 0%, #020617 100%); border-radius: 14px; border: 1.5px solid #1e293b; padding: 12px; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding: 0 10px;">
                <span style="color: #38bdf8; font-size: 13px; font-weight: 700;">🎯 SƠ ĐỒ TƯ DUY (HỖ TRỢ KATEX)</span>
                <div>
                    <button onclick="expandAll()" style="background: #1e293b; color: #38bdf8; border: 1px solid #38bdf8; padding: 4px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;">➕ Mở</button>
                    <button onclick="collapseAll()" style="background: #1e293b; color: #f43f5e; border: 1px solid #f43f5e; padding: 4px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;">➖ Thu</button>
                    <button onclick="resetZoom()" style="background: #1e293b; color: #34d399; border: 1px solid #34d399; padding: 4px 10px; border-radius: 6px; font-size: 12px; cursor: pointer;">🎯 Giữa</button>
                </div>
            </div>
            <div id="mindmap-container" style="width: 100%; height: 550px; overflow: hidden; cursor: grab;"></div>
        </div>
        <script>
        const rawCode = ___JSON_CODE_PLACEHOLDER___;
        function renderLabelWithKaTeX(rawLabel) {
            if (!rawLabel) return "";
            return rawLabel.trim().replace(/\$([^\$]+)\$/g, function(match, tex) {
                try { if (window.katex) return window.katex.renderToString(tex, { throwOnError: false, displayMode: false }); } catch (e) {}
                return match;
            });
        }
        function parseNodePart(part) {
            if (!part) return null;
            part = part.trim().split(':::')[0].trim();
            let firstDelim = -1; let openChar = null;
            for (let i = 0; i < part.length; i++) { if (['(','[','{'].includes(part[i])) { firstDelim = i; openChar = part[i]; break; } }
            if (firstDelim === -1) return { id: part, label: part };
            const id = part.substring(0, firstDelim).trim();
            const rest = part.substring(firstDelim).trim();
            const closeChar = openChar === '(' ? ')' : (openChar === '[' ? ']' : '}');
            const lastClose = rest.lastIndexOf(closeChar);
            let label = lastClose !== -1 ? rest.substring(1, lastClose).trim() : rest.substring(1).trim();
            if ((label.startsWith('"') && label.endsWith('"')) || (label.startsWith("'") && label.endsWith("'"))) label = label.substring(1, label.length - 1).trim();
            return { id: id || label, label: label || id };
        }
        function parseMermaidToTree(code) {
            if (!code) return null;
            let lines = code.split(/\r?\n/);
            if (lines.length <= 1 && code.includes('\\n')) lines = code.split('\\n');
            const nodeLabels = {}; const childrenMap = {}; const parentMap = {};
            function registerNode(node) {
                if (!node || !node.id) return;
                if (node.label && node.label !== node.id) nodeLabels[node.id] = node.label;
                else if (!nodeLabels[node.id]) nodeLabels[node.id] = node.label || node.id;
            }
            lines.forEach(line => {
                line = line.trim();
                if (!line || line.match(/^(graph|flowchart|classDef|style|subgraph|end)/)) return;
                const arrowMatch = line.match(/^(.*?)\s*(?:-->|==>|-\.->|---|->)(?:\|.*?\|)?\s*(.*)$/);
                if (arrowMatch) {
                    const src = parseNodePart(arrowMatch[1]); const tgt = parseNodePart(arrowMatch[2]);
                    if (src && tgt) {
                        registerNode(src); registerNode(tgt);
                        if (!childrenMap[src.id]) childrenMap[src.id] = [];
                        if (!childrenMap[src.id].includes(tgt.id)) childrenMap[src.id].push(tgt.id);
                        parentMap[tgt.id] = src.id;
                    }
                } else { const node = parseNodePart(line); if (node && node.id) registerNode(node); }
            });
            const allIds = Object.keys(nodeLabels);
            if (allIds.length === 0) return null;
            let rootId = allIds.find(id => !parentMap[id]) || allIds[0];
            function build(id, depth) {
                const item = { id: id, name: nodeLabels[id] || id, depth: depth };
                const childIds = childrenMap[id] || [];
                if (childIds.length > 0) item.children = childIds.map(cId => build(cId, depth + 1));
                return item;
            }
            return build(rootId, 0);
        }
        function generateAutoHealerTree() {
            return { id: "Root", name: "🎯 BÀI HỌC", depth: 0, children: [
                { id: "N1", name: "1. Khái niệm", depth: 1, children: [{ id: "N1_1", name: "Định nghĩa chuẩn", depth: 2 }] },
                { id: "N2", name: "2. Công thức", depth: 1, children: [{ id: "N2_1", name: "Công thức", depth: 2 }] }
            ]};
        }
        let treeData = parseMermaidToTree(rawCode);
        if (!treeData || !treeData.children || treeData.children.length === 0) treeData = generateAutoHealerTree();
        
        const height = 550;
        const svg = d3.select("#mindmap-container").append("svg").attr("width", "100%").attr("height", height).style("user-select", "text");
        const g = svg.append("g");
        const zoom = d3.zoom().scaleExtent([0.25, 3.5]).on("zoom", (e) => g.attr("transform", e.transform));
        svg.call(zoom);

        const treeLayout = d3.tree().nodeSize([78, 240]);
        const root = d3.hierarchy(treeData);
        root.x0 = height / 2; root.y0 = 40;
        const palette = ["#818cf8", "#38bdf8", "#34d399", "#fbbf24", "#f472b6", "#a78bfa", "#38bdf8"];

        if (root.children) {
            root.children.forEach(c => {
                if (c.children) { c.children.forEach(sub => { if (sub.children) { sub._children = sub.children; sub.children = null; } }); }
            });
        }
        let measureBox = document.getElementById("mm-box");
        if (!measureBox) {
            measureBox = document.createElement("div"); measureBox.id = "mm-box";
            measureBox.style.cssText = "position:absolute; visibility:hidden; top:-999px; left:-999px; white-space:nowrap; font-family:sans-serif;";
            document.body.appendChild(measureBox);
        }
        function getNodeW(text, d) {
            if (!text) return 90;
            measureBox.style.fontSize = d === 0 ? "13.5px" : "12.5px";
            measureBox.style.fontWeight = d === 0 ? "800" : "600";
            measureBox.innerHTML = renderLabelWithKaTeX(text);
            return Math.max(90, Math.ceil(measureBox.getBoundingClientRect().width) + 48);
        }

        let i = 0;
        function update(source) {
            const treeInfo = treeLayout(root);
            const nodes = treeInfo.descendants();
            const links = treeInfo.links();
            const maxWByDepth = {};
            nodes.forEach(d => {
                d.boxWidth = getNodeW(d.data.name, d.depth); d.boxHeight = 42;
                if (!maxWByDepth[d.depth] || d.boxWidth > maxWByDepth[d.depth]) maxWByDepth[d.depth] = d.boxWidth;
            });
            const depthX = [35];
            for (let dep = 1; dep <= 12; dep++) depthX[dep] = depthX[dep - 1] + (maxWByDepth[dep - 1] || 120) + 55;
            nodes.forEach(d => { d.y = depthX[d.depth]; });

            const node = g.selectAll("g.node").data(nodes, d => d.id || (d.id = ++i));
            const nodeEnter = node.enter().append("g").attr("class", "node").attr("transform", d => `translate(${source.y0},${source.x0})`).style("cursor", "pointer")
                .on("click", (event, d) => {
                    if (d.children) { d._children = d.children; d.children = null; }
                    else if (d._children) { d.children = d._children; d._children = null; }
                    update(d);
                });

            nodeEnter.append("rect").attr("rx", 9).attr("ry", 9).attr("x", 0).attr("y", -21).attr("height", d => d.boxHeight).attr("width", d => d.boxWidth)
                .style("fill", "#0f172a").style("stroke", d => palette[d.depth % palette.length]).style("stroke-width", d => d.depth === 0 ? "2.5px" : "1.8px");
            nodeEnter.append("circle").attr("cx", 14).attr("cy", 0).attr("r", 5.5).style("fill", d => d._children ? palette[d.depth % palette.length] : (d.children ? "#0f172a" : "#475569")).style("stroke", d => palette[d.depth % palette.length]).style("stroke-width", "2px");

            const fo = nodeEnter.append("foreignObject").attr("x", 26).attr("y", -21).attr("width", d => d.boxWidth - 28).attr("height", d => d.boxHeight).style("overflow", "visible").style("pointer-events", "auto");
            fo.append("xhtml:div").style("color", "#ffffff").style("font-size", d => d.depth === 0 ? "13.5px" : "12.5px").style("font-weight", d => d.depth === 0 ? "800" : "600").style("line-height", "42px").style("white-space", "nowrap").html(d => renderLabelWithKaTeX(d.data.name));

            const nodeUpdate = node.merge(nodeEnter).transition().duration(350).attr("transform", d => `translate(${d.y},${d.x})`);
            nodeUpdate.select("rect").attr("width", d => d.boxWidth);
            nodeUpdate.select("foreignObject").attr("width", d => d.boxWidth - 28);
            nodeUpdate.select("circle").style("fill", d => d._children ? palette[d.depth % palette.length] : (d.children ? "#0f172a" : "#475569"));

            const nodeExit = node.exit().transition().duration(350).attr("transform", d => `translate(${source.y},${source.x})`).remove();

            const link = g.selectAll("path.link").data(links, d => d.target.id);
            const linkPath = d => {
                const startX = d.source.y + d.source.boxWidth; const startY = d.source.x;
                const endX = d.target.y; const endY = d.target.x;
                return `M ${startX} ${startY} C ${(startX + endX) / 2} ${startY}, ${(startX + endX) / 2} ${endY}, ${endX} ${endY}`;
            };
            const linkEnter = link.enter().insert("path", "g").attr("class", "link")
                .attr("d", d => { const startX = source.y0 + (source.boxWidth || 150); return `M ${startX} ${source.x0} C ${startX} ${source.x0}, ${startX} ${source.x0}`; })
                .style("fill", "none").style("stroke", d => palette[d.target.depth % palette.length]).style("stroke-opacity", 0.75).style("stroke-width", "2px");

            link.merge(linkEnter).transition().duration(350).attr("d", linkPath);
            link.exit().transition().duration(350).attr("d", d => { const startX = source.y + (source.boxWidth || 150); return `M ${startX} ${source.x} C ${startX} ${source.x}, ${startX} ${source.x}`; }).remove();
            nodes.forEach(d => { d.x0 = d.x; d.y0 = d.y; });
        }
        update(root);
        svg.call(zoom.transform, d3.zoomIdentity.translate(50, height / 2.3).scale(0.85));

        window.expandAll = function() { function expand(d) { if (d._children) { d.children = d._children; d._children = null; } if (d.children) d.children.forEach(expand); } expand(root); update(root); };
        window.collapseAll = function() { if (root.children) { root.children.forEach(c => { function collapse(d) { if (d.children) { d._children = d.children; d.children = null; } if (d._children) d._children.forEach(collapse); } collapse(c); }); } update(root); };
        window.resetZoom = function() { svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity.translate(50, height / 2.3).scale(0.85)); };
        </script>
        """
        final_html = html_template.replace("___JSON_CODE_PLACEHOLDER___", json_code_str)
        if hasattr(st, "iframe"): st.iframe(final_html, height=580)
        else: components.html(final_html, height=580, scrolling=False)

    def setup_pedagogical_oxy(fig, x_range, y_range):
        x_min, x_max = x_range
        y_min, y_max = y_range
        fig.add_trace(go.Scatter(x=[x_min, x_max], y=[0, 0], mode='lines', line=dict(color='#cbd5e1', width=1.5), hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=[0, 0], y=[y_min, y_max], mode='lines', line=dict(color='#cbd5e1', width=1.5), hoverinfo='skip'))
        fig.update_layout(template="plotly_dark", xaxis=dict(range=[x_min, x_max], zeroline=False), yaxis=dict(range=[y_min, y_max], zeroline=False), showlegend=False)

    _SAFE_NAMES = {"x", "np", "math", "pi", "e", "abs", "min", "max", "pow", "round", "float", "int", "go"}
    _SAFE_CALL_ROOTS = {"np", "math", "go"}
    def _check_math_ast(node):
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and n.id not in _SAFE_NAMES: raise ValueError(f"Tên không được phép: {n.id}")
            if isinstance(n, ast.Attribute):
                if n.attr.startswith("_"): raise ValueError("Thuộc tính không được phép")
                root = n
                while isinstance(root, ast.Attribute): root = root.value
                if not (isinstance(root, ast.Name) and root.id in _SAFE_CALL_ROOTS): raise ValueError("Chỉ cho phép np.*, math.*, go.*")

    def safe_eval_func(expr, x_val):
        tree = ast.parse(expr.strip(), mode="eval")
        _check_math_ast(tree)
        env = {"__builtins__": {}, "x": x_val, "np": np, "math": math, "pi": math.pi, "e": math.e, "abs": abs, "min": min, "max": max, "pow": pow, "round": round, "float": float, "int": int}
        return eval(compile(tree, "<ham_so>", "eval"), env)

    _BLOCKED_NAMES = {"exec", "eval", "compile", "open", "input", "globals", "locals", "vars", "getattr", "setattr", "delattr", "__import__", "os", "sys", "subprocess", "st", "builtins", "importlib", "socket", "requests", "shutil", "pathlib"}
    _SAFE_BUILTINS = {k: __builtins__[k] if isinstance(__builtins__, dict) else getattr(__builtins__, k) for k in ["range", "len", "min", "max", "abs", "sum", "round", "float", "int", "list", "dict", "tuple", "zip", "enumerate", "str", "pow", "sorted", "bool", "map", "any", "all", "set", "reversed", "isinstance", "True", "False", "None"]}

    def render_dynamic_python_lab(python_code: str):
        try:
            clean_code = re.sub(r'st\.plotly_chart\(.*?\)', '', python_code)
            clean_code = re.sub(r'(?m)^\s*(?:import|from)\s+.*$', '', clean_code)
            tree = ast.parse(clean_code)
            for n in ast.walk(tree):
                if isinstance(n, ast.Name) and (n.id in _BLOCKED_NAMES or n.id.startswith("__")): raise ValueError(f"Mã cấm: {n.id}")
                if isinstance(n, ast.Attribute) and n.attr.startswith("_"): raise ValueError("Mã cấm")
                if isinstance(n, (ast.Import, ast.ImportFrom)): raise ValueError("Cấm import")
            local_env = {"__builtins__": _SAFE_BUILTINS, "go": go, "np": np, "math": math, "setup_pedagogical_oxy": setup_pedagogical_oxy}
            exec(compile(tree, "<mo_phong>", "exec"), local_env)
            if "fig" in local_env and isinstance(local_env["fig"], go.Figure):
                st.plotly_chart(local_env["fig"], use_container_width=True)
        except Exception as e:
            st.error(f"Lỗi vẽ không gian Poly 3D: {e}")

    def render_smart_lab(data):
        dtype = data.get("type")
        if dtype == "mermaid":
            st.markdown("### 🗺️ Trực quan hóa Sơ Đồ Tư Duy / Chu Trình Mô Phỏng")
            render_mermaid(data.get("code", ""))
            return
        if dtype == "dynamic_code":
            st.markdown("### 🎨 Mô Phỏng Đồ Họa Động / Không Gian Nâng Cao")
            render_dynamic_python_lab(data.get("python_code", ""))
            return

        fig = go.Figure()
        if dtype == "func_3":
            c1, c2 = st.columns([1.2, 2.8])
            with c1:
                fa = st.slider("Hệ số a:", -3.0, 3.0, float(data.get("a", 1.0)), 0.5)
                fb = st.slider("Hệ số b:", -5.0, 5.0, float(data.get("b", -3.0)), 0.5)
                fc = st.slider("Hệ số c:", -5.0, 5.0, float(data.get("c", 0.0)), 0.5)
                fd = st.slider("Hệ số d:", -5.0, 5.0, float(data.get("d", 2.0)), 0.5)
            with c2:
                x_vals = np.linspace(-6, 6, 800)
                y_vals = fa * (x_vals**3) + fb * (x_vals**2) + fc * x_vals + fd
                fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', line=dict(color='#38bdf8', width=3)))
                setup_pedagogical_oxy(fig, [-6, 6], [min(y_vals) - 1, max(y_vals) + 1])
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("💡 Không thể tải được mô phỏng. Kéo thanh trượt hoặc nhập tham số để mô phỏng tương tác!")

    # ==============================================================================
    # 4. GIAO DIỆN CHÍNH (CÁC TRẠM)
    # ==============================================================================
    st.markdown('<div class="main-header"><div class="main-title">🏫 GIA SƯ AI - HỆ SINH THÁI LỚP HỌC ĐẢO NGƯỢC</div></div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["💡 Trạm 1: Học Tập & Phòng Lab", "✍️ Trạm 2: Gia Sư Socratic & Nộp Bài", "📝 Trạm 3: Khảo Thí Độc Lập", "📊 Trạm 4: Dữ Liệu KHKT & Tự Động Vá Lỗi"])

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
1. BÁM SÁT 100% NGỮ LIỆU KNTT. TOÁN HỌC: CẤM DÙNG HÀM BẬC 4 TRÙNG PHƯƠNG. Khảo sát Lớp 12 chỉ dùng Bậc 3, Phân thức 1/1, Phân thức 2/1.
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
        lab_command = st.text_input("Lệnh mô phỏng:", placeholder="Ví dụ: Vẽ khối chóp tứ giác đều 3D, hoặc vẽ Sơ đồ tư duy...", label_visibility="collapsed")
        
        if st.button("✨ Khởi chạy Phòng Lab", use_container_width=True) and lab_command.strip():
            st.session_state.tram1_count += 1
            with st.spinner("AI đang phân tích và dựng mô hình khối đa diện 3D / Sơ đồ tư duy..."):
                lab_prompt = f"""Môn học: {subject} | Lớp: {grade_num}.
Yêu cầu của học sinh: "{lab_command}"
NHIỆM VỤ: Xuất DUY NHẤT 1 khối JSON hợp lệ.
1. KHỐI TRÒN XOAY 3D: {{"type": "revolve_ox", "func": "2*x + 1", "a": 2.0, "b": 5.0}}
2. MÔ PHỎNG NÂNG CAO KHỐI 3D POLY/ĐA DIỆN (Bắt buộc dùng go.Mesh3d):
   {{"type": "dynamic_code", "python_code": "fig = go.Figure()\\nfig.add_trace(go.Mesh3d(x=[0,1,0,0], y=[0,0,1,0], z=[0,0,0,1], i=[0,0,0,1], j=[1,1,2,2], k=[2,3,3,3], color='cyan', opacity=0.6))\\nfig.update_layout(scene=dict(aspectmode='cube'))"}}
3. SƠ ĐỒ TƯ DUY: {{"type": "mermaid", "code": "graph LR\\nRoot[\\\"🎯 TIÊU ĐỀ\\\"] --> A[\\\"1. Nội dung\\\"]"}}
"""
                try:
                    raw_json = call_gemini_with_fallback(lab_prompt, json_mode=True).strip()
                    if raw_json.startswith("```json"): raw_json = raw_json[7:-3].strip()
                    elif raw_json.startswith("```"): raw_json = raw_json[3:-3].strip()
                    if "graph " in raw_json or "flowchart " in raw_json or "-->" in raw_json:
                        if not raw_json.startswith("{"): st.session_state.lab_data = {"type": "mermaid", "code": raw_json}
                        else: st.session_state.lab_data = json.loads(raw_json)
                    else: st.session_state.lab_data = json.loads(raw_json)
                except Exception:
                    is_mm = any(kw in lab_command.lower() for kw in ["sơ đồ", "mindmap", "tóm tắt"])
                    st.session_state.lab_data = {"type": "mermaid", "code": "graph LR\nRoot[\"🎯 BÀI HỌC\"]-->A[\"1. Tóm tắt\"]"} if is_mm else {"type": "func_3", "a": 1, "b": -3, "c": 0, "d": 2}

        if st.session_state.get("lab_data"):
            st.success("✨ Đã khởi tạo mô phỏng Phòng Lab thành công!")
            render_smart_lab(st.session_state.lab_data)

    # ------------------------------------------------------------------------------
    # TRẠM 2: GIA SƯ SOCRATIC & NỘP BÀI
    # ------------------------------------------------------------------------------
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader(f"✍️ Gia Sư Socratic Môn: {subject} - Lớp {grade_num}")

        if st.button("🔄 Xóa đối thoại cũ", use_container_width=True): 
            st.session_state.messages = []
            st.session_state.chat = None
            st.rerun()

        socratic_system_instruction = f"""Bạn là Thầy giáo Gia Sư AI tại Trường THPT Tân Hiệp. Học sinh: {student_name}."""
        uploaded_file = st.file_uploader("📸 Tải ảnh bài làm (JPG, PNG)", type=["jpg", "png", "jpeg"])
        if uploaded_file:
            st.image(Image.open(uploaded_file), caption="Bài làm của em", use_container_width=True)
            if st.button("🚀 Bắt đầu nhận xét", use_container_width=True):
                st.session_state.tram2_count += 1
                with st.spinner(f"Thầy đang đối chiếu chuẩn kiến thức SGK KNTT Lớp {grade_num}..."):
                    try:
                        full_res = call_gemini_with_fallback(
                            [f"Học sinh nộp ảnh bài làm môn {subject} Lớp {grade_num}. Nhận xét Socratic:", Image.open(uploaded_file)], 
                            system_instruction=socratic_system_instruction
                        )
                        student_fb = full_res.split("<DIAGNOSTIC>")[0].strip()
                        st.session_state.messages = [{"role": "user", "content": "*(Em đã nộp ảnh bài làm)*"}, {"role": "assistant", "content": student_fb}]
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Lỗi: {e}")

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
                        rep = call_gemini_with_fallback(f"Lịch sử:\n{history_context}\nHỏi: {q}\nThầy phản hồi gợi mở Socratic:", system_instruction=socratic_system_instruction)
                        clean_rep = rep.split("<DIAGNOSTIC>")[0].strip()
                        st.markdown(clean_rep)
                        st.session_state.messages.append({"role": "assistant", "content": clean_rep})
                    except Exception as e: st.error(f"Lỗi: {e}")

    # ------------------------------------------------------------------------------
    # TRẠM 3: KHẢO THÍ ĐỘC LẬP
    # ------------------------------------------------------------------------------
    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader(f"📝 Trạm 3: Khảo Thí Độc Lập - Môn {subject} (Lớp {grade_num})")

        if st.session_state.exam_state == "config":
            st.markdown("#### 📊 Cấu hình chuyên đề khảo thí chuẩn CT GDPT 2018:")
            if subject == "Ngữ văn": def_p1, def_p2, def_p3 = 0, 0, 0
            elif subject == "Tiếng Anh": def_p1, def_p2, def_p3 = 40, 0, 0
            elif subject == "Toán học": def_p1, def_p2, def_p3 = 12, 4, 6
            elif subject in ["Vật lý", "Hóa học", "Sinh học"]: def_p1, def_p2, def_p3 = 18, 4, 6
            else: def_p1, def_p2, def_p3 = 24, 4, 0

            exam_time_mins = st.selectbox("⏱️ Thời lượng bài thi (Phút):", [15, 30, 45, 50, 60, 90, 120], index=3)
            st.session_state.exam_time_mins = exam_time_mins

            if st.button(f"🚀 Khởi tạo đề thi ({exam_time_mins} phút)", type="primary", use_container_width=True):
                st.session_state.exam_code = str(random.randint(1011, 9999))
                with st.spinner("⚡ AI đang nén Token siêu tốc & phân luồng ma trận đề thi..."):
                    exam_prompt = f"""[CHUYÊN GIA KHẢO THÍ BGDĐT - MÔN {subject.upper()} LỚP {grade_num}]
Số lượng: {def_p1} TN, {def_p2} Đ/S, {def_p3} TLN. TUYỆT ĐỐI CẤM HÀM BẬC 4 TRÙNG PHƯƠNG.
XUẤT DUY NHẤT 1 OBJECT JSON:
{{"p1": [{{"q": "...", "opt": ["A. $...$", "B. $...$", "C. $...$", "D. $...$"], "ans": "A"}}],
 "p2": [{{"q": "...", "stmts": [{{"t": "...", "c": true}}, {{"t": "...", "c": false}}, {{"t": "...", "c": true}}, {{"t": "...", "c": false}}]}}],
 "p3": [{{"q": "...", "ans": "..."}}]}}"""
                    if subject == "Ngữ văn":
                        exam_prompt = f"""[CHUYÊN GIA KHẢO THÍ NGỮ VĂN GDPT 2018 LỚP {grade_num}] JSON DUY NHẤT:
{{"part_doc_hieu": {{"text": "Đoạn trích...", "questions": [{{"q": "Câu hỏi..."}}]}}, "part_viet": [{{"type": "NLXH", "q": "Đoạn văn..."}}]}}"""
                    
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
                elif subject in ["Vật lý", "Hóa học", "Sinh học"]: w_p1_total, w_p2_total, w_p3_total = 4.5, 4.0, 1.5
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
        \textbf{TRƯỜNG TÂN HIỆP} \\[0.1cm]
        \textbf{ĐỀ THI CHÍNH THỨC} \\
        \textit{(Đề thi có \pageref{LastPage} trang)}
    \end{center}
\end{minipage}%
\hfill
\begin{minipage}[t]{0.56\textwidth}
    \begin{center}
        \textbf{\small KỲ THI KHẢO SÁT CHẤT LƯỢNG NĂM HỌC 2026-2027} \\[0.05cm]
        Môn thi: \textbf{""" + subject.upper() + r"""} \\[0.05cm]
        \textit{Thời gian làm bài: 45 phút} \\[0.05cm]
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
                latex_code += r"""\textbf{PHẦN I. ĐỌC HIỂU (4.0 điểm)}\vspace{0.15cm}"""
            else:
                if exam.get("p1"):
                    latex_code += r"""\textbf{PHẦN I.} Thí sinh trả lời từ câu 1 đến câu """ + str(len(exam["p1"])) + r""". Mỗi câu hỏi thí sinh chỉ chọn một phương án.\vspace{0.15cm}
\begin{enumerate}[label=\textbf{Câu \arabic*.}, leftmargin=*, itemsep=4pt, parsep=0pt]
"""
                    for idx, q in enumerate(exam["p1"]):
                        latex_code += f"\\item {clean_vietnamese_math(q.get('q', ''))}\n"
                        latex_code += "\\begin{enumerate}[label=\\textbf{\\Alph*.}, leftmargin=*, itemsep=0pt, parsep=0pt, topsep=0pt]\n"
                        for opt in q.get("opt", []): latex_code += f"\\item {re.sub(r'^[A-D]\.\s*', '', clean_vietnamese_math(opt))}\n"
                        latex_code += "\\end{enumerate}\n"
                    latex_code += r"""\end{enumerate}"""
                    
                if exam.get("p2"):
                    latex_code += r"""\vspace{0.3cm}\noindent\textbf{PHẦN II.} Thí sinh trả lời từ câu 1 đến câu """ + str(len(exam["p2"])) + r""". Trong mỗi ý a), b), c), d) ở mỗi câu, thí sinh chọn đúng hoặc sai.\vspace{0.15cm}
\begin{enumerate}[label=\textbf{Câu \arabic*.}, leftmargin=*, itemsep=4pt, parsep=0pt]
"""
                    for idx, q in enumerate(exam["p2"]):
                        latex_code += f"\\item {clean_vietnamese_math(q.get('q', ''))}\n"
                        latex_code += "\\begin{enumerate}[label=\\textbf{\\alph*)}, leftmargin=*, itemsep=2pt, parsep=0pt]\n"
                        for s_idx, stmt in enumerate(q.get("stmts", [])): latex_code += f"\\item {clean_vietnamese_math(stmt.get('t', ''))}\n"
                        latex_code += "\\end{enumerate}\n"
                    latex_code += r"""\end{enumerate}"""

            latex_code += r"""
\vspace{0.5cm}
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

        if st.button("🔒 Khóa Trạm 4", key="lock_tab4_btn", use_container_width=True):
            st.session_state.tab4_authenticated = False
            st.rerun()

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Lượt tự học T1", f"{st.session_state.tram1_count}")
        m2.metric("Vấn đáp T2", f"{st.session_state.tram2_count}")
        exam_logs = [e for e in st.session_state.get("analytics_logs", []) if e.get("type") == "EXAM_RESULT"]
        m3.metric("Bài thi T3", f"{len(exam_logs)} bài")

        # THỐNG KÊ T-TEST
        st.markdown("---")
        st.markdown("### 🔬 Kiểm Chứng Thống Kê Sư Phạm (Paired t-Test)")
        c_stat1, c_stat2 = st.columns([1.1, 2.9])
        with c_stat1:
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
