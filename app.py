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
# 1. ĐỒNG BỘ GIỜ VIỆT NAM (GMT+7) CHUẨN XÁC
# ==============================================================================
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

# ==============================================================================
# 2. KHỞI TẠO BỘ NHỚ PHIÊN & BỘ ĐẾM THỰC NGHIỆM TỰ ĐỘNG
# ==============================================================================
for key in ["messages", "analytics_logs", "feedback_logs", "parsed_quiz", "va_loi_logs"]:
    if key not in st.session_state: st.session_state[key] = []
if "tram1_count" not in st.session_state: st.session_state.tram1_count = 0
if "tram2_count" not in st.session_state: st.session_state.tram2_count = 0
if "chat" not in st.session_state: st.session_state.chat = None
if "current_lesson" not in st.session_state: st.session_state.current_lesson = ""
if "current_topic" not in st.session_state: st.session_state.current_topic = ""
if "lab_data" not in st.session_state: st.session_state.lab_data = None
if "quiz_states" not in st.session_state: st.session_state.quiz_states = {}
if "global_stats_loaded" not in st.session_state: st.session_state.global_stats_loaded = False
if "global_exam_count" not in st.session_state: st.session_state.global_exam_count = 0
if "global_logs" not in st.session_state: st.session_state.global_logs = []
if "student_progress_history" not in st.session_state: st.session_state.student_progress_history = []

# ==============================================================================
# 3. CẤU HÌNH TRANG WEB & LINK CHÍNH CHỦ
# ==============================================================================
st.set_page_config(
    page_title="Gia Sư AI - Hệ Sinh Thái Lớp Học Đảo Ngược",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_URL = get_secret("APP_URL", "https://gsaithptth-khkt2026.streamlit.app")

# ==============================================================================
# TÂN TRANG GIAO DIỆN (UI/UX NÂNG CẤP DÀNH CHO KHKT)
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
        background: linear-gradient(145deg, #0f172a, #1e293b); 
        border: 2px solid #0ea5e9; 
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
    
    .stRadio > div { background-color: rgba(30, 41, 59, 0.6); padding: 15px; border-radius: 10px; border: 1px solid #334155; }
    .short-link-badge { background-color: #1e293b; border: 1px dashed #38bdf8; padding: 8px 12px; border-radius: 8px; font-family: 'Courier New', Courier, monospace; font-size: 0.8rem; color: #38bdf8; text-align: center; margin: 10px 0; word-break: break-all; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 4. THANH BÊN (SIDEBAR) & LIÊN KẾT MÔN HỌC
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
    - 💻 **Máy tính (Chrome/Edge):** Bấm biểu tượng màn hình ⬇️ hoặc Cài đặt trên thanh địa chỉ để cài app vào Desktop.
    
    *Hệ thống tự động lưu API Key & Tên của em vào bộ nhớ thiết bị (`localStorage`) cho mọi lần học sau!*
    """)

# JAVASCRIPT ĐỒNG BỘ LOCALSTORAGE CHO THIẾT BỊ HỌC SINH
st.markdown("""
<script>
document.addEventListener("DOMContentLoaded", function() {
    try {
        const savedKey = localStorage.getItem("GSAI_USER_CUSTOM_KEY");
        const savedName = localStorage.getItem("GSAI_STUDENT_NAME");
        if (savedKey && !window.keyRestored) {
            window.keyRestored = true;
            console.log("GSAI: Đã phục hồi cấu hình cá nhân từ thiết bị.");
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
# 5. ĐIỀU PHỐI AI BỀN BỈ (GIA PHẢ 3.X TỐI THƯỢNG THEO LỆNH GOOGLE)
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
# 6. PHÒNG LAB LAI & BỘ LỌC AN TOÀN AST
# ==============================================================================
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
                },
                {
                    id: "N4",
                    name: "🌐 4. Ứng dụng & Mối liên hệ thực tiễn",
                    depth: 1,
                    children: [
                        { id: "N4_1", name: "Mô hình hóa thực tế trong đời sống", depth: 2 },
                        { id: "N4_2", name: "Liên hệ các môn KHTN & Công nghệ", depth: 2 }
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

def setup_pedagogical_oxy(fig, x_range, y_range):
    x_min, x_max = x_range
    y_min, y_max = y_range

    fig.add_trace(go.Scatter(x=[x_min, x_max], y=[0, 0], mode='lines', line=dict(color='#cbd5e1', width=1.5), hoverinfo='skip', showlegend=False))
    fig.add_trace(go.Scatter(x=[0, 0], y=[y_min, y_max], mode='lines', line=dict(color='#cbd5e1', width=1.5), hoverinfo='skip', showlegend=False))

    fig.add_annotation(x=x_max, y=0, ax=-18, ay=0, xref='x', yref='y', axref='pixel', ayref='pixel', showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor='#cbd5e1')
    fig.add_annotation(x=x_max - 0.1, y=-0.5, text='<b>x</b>', showarrow=False, font=dict(color='#f8fafc', size=15, family='Times New Roman'))

    fig.add_annotation(x=0, y=y_max, ax=0, ay=18, xref='x', yref='y', axref='pixel', ayref='pixel', showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor='#cbd5e1')
    fig.add_annotation(x=-0.4, y=y_max - 0.1, text='<b>y</b>', showarrow=False, font=dict(color='#f8fafc', size=15, family='Times New Roman'))

    fig.add_annotation(x=-0.35, y=-0.45, text='<i>O</i>', showarrow=False, font=dict(color='#94a3b8', size=15, family='Times New Roman'))

    fig.update_layout(
        template="plotly_dark",
        xaxis=dict(range=[x_min, x_max], zeroline=False, gridcolor="#1e293b", dtick=1),
        yaxis=dict(range=[y_min, y_max], zeroline=False, gridcolor="#1e293b", dtick=1),
        margin=dict(l=15, r=15, t=30, b=15),
        showlegend=False
    )

_SAFE_NAMES = {"x", "np", "math", "pd", "px", "pi", "e", "abs", "min", "max", "pow", "round", "float", "int"}
_SAFE_CALL_ROOTS = {"np", "math", "pd", "px"}

def _check_math_ast(node):
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id not in _SAFE_NAMES:
            raise ValueError(f"Tên không được phép: {n.id}")
        if isinstance(n, ast.Attribute):
            if n.attr.startswith("_"):
                raise ValueError("Thuộc tính không được phép")
            root = n
            while isinstance(root, ast.Attribute):
                root = root.value
            if not (isinstance(root, ast.Name) and root.id in _SAFE_CALL_ROOTS):
                raise ValueError("Chỉ cho phép gọi hàm từ np, math, pd, px")
        if isinstance(n, (ast.Lambda, ast.Subscript, ast.Starred, ast.comprehension, ast.NamedExpr)) and not isinstance(n, ast.Subscript):
            raise ValueError("Cấu trúc không được phép")

def safe_eval_func(expr, x_val):
    tree = ast.parse(expr.strip(), mode="eval")
    _check_math_ast(tree)
    env = {"__builtins__": {}, "x": x_val, "np": np, "math": math, "pd": pd, "px": px, "pi": math.pi, "e": math.e,
           "abs": abs, "min": min, "max": max, "pow": pow, "round": round, "float": float, "int": int}
    return eval(compile(tree, "<ham_so>", "eval"), env)

_BLOCKED_NAMES = {"exec", "eval", "compile", "open", "input", "globals", "locals", "vars", "getattr",
                  "setattr", "delattr", "__import__", "os", "sys", "subprocess", "st", "builtins",
                  "importlib", "socket", "requests", "shutil", "pathlib"}
_SAFE_BUILTINS = {k: __builtins__[k] if isinstance(__builtins__, dict) else getattr(__builtins__, k)
                  for k in ["range", "len", "min", "max", "abs", "sum", "round", "float", "int", "list", "dict",
                            "tuple", "zip", "enumerate", "str", "pow", "sorted", "bool", "map", "any", "all",
                            "set", "reversed", "isinstance", "True", "False", "None"]}

def render_dynamic_python_lab(python_code: str):
    try:
        clean_code = re.sub(r'st\.plotly_chart\(.*?\)', '', python_code)
        clean_code = re.sub(r'(?m)^\s*(?:import|from)\s+.*$', '', clean_code)
        tree = ast.parse(clean_code)
        for n in ast.walk(tree):
            if isinstance(n, ast.Name) and (n.id in _BLOCKED_NAMES or n.id.startswith("__")):
                raise ValueError(f"Mã mô phỏng dùng tên bị cấm: {n.id}")
            if isinstance(n, ast.Attribute) and n.attr.startswith("_"):
                raise ValueError("Mã mô phỏng dùng thuộc tính bị cấm")
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                raise ValueError("Không cho phép import trong mã mô phỏng")
        local_env = {"__builtins__": _SAFE_BUILTINS, "go": go, "np": np, "math": math, "pd": pd, "px": px,
                     "setup_pedagogical_oxy": setup_pedagogical_oxy}
        exec(compile(tree, "<mo_phong>", "exec"), local_env)
        if "fig" in local_env and isinstance(local_env["fig"], go.Figure):
            unique_plot_id = f"dynamic_plot_{int(time.time() * 1000)}_{random.randint(1, 1000)}"
            st.plotly_chart(local_env["fig"], use_container_width=True, key=unique_plot_id)
    except Exception as e:
        st.error(f"Lỗi biên dịch mô phỏng nâng cao Plotly: {e}")

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
        clean_f = clean_f.replace('\\sin', 'np.sin').replace('\\cos', 'np.cos').replace('\\tan', 'np.tan')
        clean_f = clean_f.replace('\\ln', 'np.log').replace('\\pi', 'np.pi')
        clean_f = re.sub(r'\be\^\{([^{}]*)\}', r'np.exp(\1)', clean_f)
        clean_f = re.sub(r'\be\^(\([^()]*\)|[\w\.]+)', r'np.exp(\1)', clean_f)
        
        clean_f = clean_f.replace('^', '**').replace('y=', '').replace('f(x)=', '').strip()
        clean_f = re.sub(r'(?<![\w.])(\d+(?:\.\d+)?)\s*([a-zA-Z\(])', r'\1*\2', clean_f)
        clean_f = re.sub(r'(\))\s*([a-zA-Z0-9\(])', r'\1*\2', clean_f)
        clean_f = clean_f.replace('{', '(').replace('}', ')')
        
        math_str = func_str.replace('**', '^').replace('*', '').replace(' ', '')
        
        sa_def = float(data.get("a", 0.0))
        sb_def = float(data.get("b", 3.0))

        with c1:
            st.caption("⚙️ **Thông số Diện tích hình phẳng:**")
            st.info(f"**Hàm số:** $y = {math_str}$")
            sa = st.slider("Cận dưới a:", -10.0, 10.0, sa_def, 0.5, key="lab_area_a")
            sb = st.slider("Cận trên b:", -10.0, 10.0, sb_def, 0.5, key="lab_area_b")

            if sa >= sb:
                st.warning("⚠️ Cận a phải nhỏ hơn cận b!")
                sb = sa + 0.5

            try:
                x_area = np.linspace(sa, sb, 400)
                y_area = safe_eval_func(clean_f, x_area)
                if isinstance(y_area, (int, float)): y_area = np.full_like(x_area, float(y_area))
                area_val = _trapz(np.abs(y_area), x_area)
                st.success(f"📐 **Diện tích (S):**\n\n$$S = \int_{{{sa}}}^{{{sb}}} |{math_str}| dx \\approx {abs(area_val):.2f}$$")
            except Exception:
                pass

        with c2:
            try:
                fig_area = go.Figure()
                
                x_full = np.linspace(sa - 3, sb + 3, 600)
                y_full = safe_eval_func(clean_f, x_full)
                if isinstance(y_full, (int, float)): y_full = np.full_like(x_full, float(y_full))
                
                fig_area.add_trace(go.Scatter(x=x_full, y=y_full, mode='lines', line=dict(color='#38bdf8', width=3), name='Đồ thị hàm số'))
                
                y_area_fill = safe_eval_func(clean_f, x_area)
                if isinstance(y_area_fill, (int, float)): y_area_fill = np.full_like(x_area, float(y_area_fill))
                
                fig_area.add_trace(go.Scatter(x=np.concatenate([x_area, x_area[::-1]]), 
                                              y=np.concatenate([y_area_fill, np.zeros_like(y_area_fill)]), 
                                              fill='toself', fillcolor='rgba(236, 72, 153, 0.4)', 
                                              line=dict(color='rgba(255,255,255,0)'), hoverinfo="skip", name='Diện tích (S)'))
                
                y_view_min, y_view_max = min(y_full), max(y_full)
                y_pad = (y_view_max - y_view_min) * 0.15 
                if y_pad == 0: y_pad = 2
                y_min, y_max = y_view_min - y_pad, y_view_max + y_pad
                if y_min > 0: y_min = -y_pad
                if y_max < 0: y_max = y_pad

                y_sa = safe_eval_func(clean_f, sa)
                y_sb = safe_eval_func(clean_f, sb)
                fig_area.add_trace(go.Scatter(x=[sa, sa], y=[0, float(y_sa)], mode='lines', line=dict(color='#f59e0b', width=2, dash='dash'), name='Cận a'))
                fig_area.add_trace(go.Scatter(x=[sb, sb], y=[0, float(y_sb)], mode='lines', line=dict(color='#10b981', width=2, dash='dash'), name='Cận b'))
                
                setup_pedagogical_oxy(fig_area, [min(x_full), max(x_full)], [y_min, y_max])
                fig_area.update_layout(title="Mô phỏng Diện tích hình phẳng (Tích phân)", height=500, showlegend=True)
                st.plotly_chart(fig_area, use_container_width=True)
            except Exception as err:
                st.error(f"Lỗi vẽ đồ thị diện tích: {err}")
        return
        
    if dtype == "revolve_ox":
        func_str = str(data.get("func", "2*x + 1")).replace('$', '').strip()
        
        clean_f = re.sub(r'\\frac{(.*?)}{(.*?)}', r'((\1)/(\2))', func_str)
        clean_f = clean_f.replace('\\sin', 'np.sin').replace('\\cos', 'np.cos').replace('\\tan', 'np.tan')
        clean_f = clean_f.replace('\\ln', 'np.log').replace('\\pi', 'np.pi')
        clean_f = re.sub(r'\be\^\{([^{}]*)\}', r'np.exp(\1)', clean_f)
        clean_f = re.sub(r'\be\^(\([^()]*\)|[\w\.]+)', r'np.exp(\1)', clean_f)
        
        clean_f = clean_f.replace('^', '**').replace('y=', '').replace('f(x)=', '').strip()
        clean_f = re.sub(r'(?<![\w.])(\d+(?:\.\d+)?)\s*([a-zA-Z\(])', r'\1*\2', clean_f)
        clean_f = re.sub(r'(\))\s*([a-zA-Z0-9\(])', r'\1*\2', clean_f)
        clean_f = clean_f.replace('{', '(').replace('}', ')')

        a_def = float(data.get("a", 2.0))
        b_def = float(data.get("b", 5.0))

        c1, c2 = st.columns([1.2, 2.8])
        with c1:
            st.caption("⚙️ **Thông số Khối tròn xoay quanh trục Ox:**")
            math_str = func_str.replace('**', '^').replace('*', '')
            st.info(f"**Đường giới hạn:** $y = {math_str}$")
            sa = st.slider("Cận dưới a:", -8.0, 8.0, a_def, 0.5, key="lab_revolve_a")
            sb = st.slider("Cận trên b:", -8.0, 8.0, b_def, 0.5, key="lab_revolve_b")
            angle_deg = st.slider("Góc quay quanh trục Ox:", 30, 360, 360, 15, key="lab_revolve_angle")

            if sa >= sb:
                st.warning("⚠️ Cận a phải nhỏ hơn cận b!")
                sb = sa + 0.5

            try:
                x_num = np.linspace(sa, sb, 400)
                y_num = safe_eval_func(clean_f, x_num)
                if isinstance(y_num, (int, float)): y_num = np.full_like(x_num, float(y_num))
                vol_val = _trapz(y_num**2, x_num) * np.pi
                st.success(f"📐 **Thể tích khối tròn xoay:**\n\n$$V = \\pi \\int_{{{sa}}}^{{{sb}}} [{math_str}]^2 dx \\approx {abs(vol_val):.2f}\\text{{ (đvtt)}}$$")
            except Exception:
                pass

        with c2:
            try:
                u = np.linspace(sa, sb, 60)
                v = np.linspace(0, np.radians(angle_deg), 60)
                U, V = np.meshgrid(u, v)

                R = safe_eval_func(clean_f, U)
                if isinstance(R, (int, float)): R = np.full_like(U, float(R))

                X_3d = U
                Y_3d = R * np.cos(V)
                Z_3d = R * np.sin(V)

                fig_3d = go.Figure()
                fig_3d.add_trace(go.Surface(x=X_3d, y=Y_3d, z=Z_3d, colorscale='Viridis', opacity=0.82, showscale=False, name='Khối tròn xoay'))

                ox_min, ox_max = min(sa - 1.5, -2), max(sb + 1.5, 2)
                fig_3d.add_trace(go.Scatter3d(x=[ox_min, ox_max], y=[0, 0], z=[0, 0], mode='lines+text', line=dict(color='#ffffff', width=4), text=["", "Trục Ox"], textposition="top right", name="Trục Ox"))

                y_gen = safe_eval_func(clean_f, u)
                if isinstance(y_gen, (int, float)): y_gen = np.full_like(u, float(y_gen))
                fig_3d.add_trace(go.Scatter3d(x=u, y=y_gen, z=np.zeros_like(u), mode='lines', line=dict(color='#f43f5e', width=5), name='Đường sinh y=f(x)'))

                fig_3d.update_layout(
                    title=f"Mô hình 3D Khối tròn xoay: $y = {math_str}$ quay quanh Ox",
                    template="plotly_dark",
                    scene=dict(
                        xaxis=dict(title="Trục Ox", backgroundcolor="#0f172a", gridcolor="#1e293b"),
                        yaxis=dict(title="Trục Oy", backgroundcolor="#0f172a", gridcolor="#1e293b"),
                        zaxis=dict(title="Trục Oz", backgroundcolor="#0f172a", gridcolor="#1e293b"),
                        aspectmode='auto' # ĐÃ FIX LỖI LÉP XẸP HÌNH 3D: CHUYỂN TỪ 'data' SANG 'auto' 
                    ),
                    height=520,
                    margin=dict(l=10, r=10, t=35, b=10)
                )
                st.plotly_chart(fig_3d, use_container_width=True)
            except Exception as err:
                st.error(f"Lỗi tính toán mô phỏng 3D: {err}")
        return

    if dtype == "dynamic_code":
        st.markdown("### 🎨 Mô Phỏng Đồ Họa Động / Không Gian Nâng Cao (Sức mạnh Plotly)")
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
            y_min, y_max = min(y_vals) - y_pad, max(y_vals) + y_pad
            
            setup_pedagogical_oxy(fig, [-6, 6], [y_min, y_max])
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
            
            x_tc_dung = -fd / fc
            y_tc_ngang = fa / fc
            st.info(f"**$y = \\frac{{{fa}x + {fb}}}{{{fc}x + {fd}}}$**")
            st.caption(f"📌 **Tiệm cận đứng:** $x = {x_tc_dung:.2f}$<br>📌 **Tiệm cận ngang:** $y = {y_tc_ngang:.2f}$", unsafe_allow_html=True)
        with c2:
            x_left = np.linspace(-7, x_tc_dung - 0.05, 400)
            x_right = np.linspace(x_tc_dung + 0.05, 7, 400)
            y_left = (fa * x_left + fb) / (fc * x_left + fd)
            y_right = (fa * x_right + fb) / (fc * x_right + fd)
            y_left[np.abs(y_left) > 15] = np.nan
            y_right[np.abs(y_right) > 15] = np.nan

            fig.add_trace(go.Scatter(x=x_left, y=y_left, mode='lines', line=dict(color='#38bdf8', width=3), name='Nhánh trái'))
            fig.add_trace(go.Scatter(x=x_right, y=y_right, mode='lines', line=dict(color='#38bdf8', width=3), name='Nhánh phải'))
            fig.add_trace(go.Scatter(x=[x_tc_dung, x_tc_dung], y=[-15, 15], mode='lines', line=dict(color='#f59e0b', width=1.8, dash='dash'), name='TC Đứng'))
            fig.add_trace(go.Scatter(x=[-7, 7], y=[y_tc_ngang, y_tc_ngang], mode='lines', line=dict(color='#10b981', width=1.8, dash='dash'), name='TC Ngang'))
            setup_pedagogical_oxy(fig, [-7, 7], [-8, 8])
            fig.update_layout(title="Đồ thị Hàm phân thức Bậc 1 / Bậc 1 (Kèm Tiệm cận)", height=500)
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
            
            x_tc_dung = -fe / fd
            m_slope = fa / fd
            n_intercept = (fb - m_slope * fe) / fd
            st.info(f"**$y = \\frac{{{fa}x^2 + {fb}x + {fc}}}{{{fd}x + {fe}}}$**")
            st.caption(f"📌 **Tiệm cận đứng:** $x = {x_tc_dung:.2f}$<br>📌 **Tiệm cận xiên:** $y = {m_slope:.2f}x + ({n_intercept:.2f})$", unsafe_allow_html=True)
        with c2:
            x_left = np.linspace(-7, x_tc_dung - 0.05, 400)
            x_right = np.linspace(x_tc_dung + 0.05, 7, 400)
            y_left = (fa * x_left**2 + fb * x_left + fc) / (fd * x_left + fe)
            y_right = (fa * x_right**2 + fb * x_right + fc) / (fd * x_right + fe)
            y_left[np.abs(y_left) > 18] = np.nan
            y_right[np.abs(y_right) > 18] = np.nan

            fig.add_trace(go.Scatter(x=x_left, y=y_left, mode='lines', line=dict(color='#38bdf8', width=3), name='Đồ thị'))
            fig.add_trace(go.Scatter(x=x_right, y=y_right, mode='lines', line=dict(color='#38bdf8', width=3), name='Đồ thị'))
            fig.add_trace(go.Scatter(x=[x_tc_dung, x_tc_dung], y=[-18, 18], mode='lines', line=dict(color='#f59e0b', width=1.8, dash='dash'), name='TC Đứng'))
            
            x_slant = np.linspace(-7, 7, 100)
            y_slant = m_slope * x_slant + n_intercept
            fig.add_trace(go.Scatter(x=x_slant, y=y_slant, mode='lines', line=dict(color='#ec4899', width=1.8, dash='dash'), name='TC Xiên'))
            setup_pedagogical_oxy(fig, [-7, 7], [-10, 10])
            fig.update_layout(title="Đồ thị Hàm phân thức Bậc 2 / Bậc 1 (Kèm Tiệm cận xiên)", height=500)
            st.plotly_chart(fig, use_container_width=True)

    elif dtype in ["parabola", "func_2"]:
        c1, c2 = st.columns([1.2, 2.8])
        with c1:
            st.caption("⚙️ **Hệ số Parabol bậc 2 ($y = ax^2 + bx + c$):**")
            fa = st.slider("Hệ số a:", -4.0, 4.0, float(data.get("a", 1.0)), 0.5, key="lab_p2_a")
            if fa == 0: fa = 1.0
            fb = st.slider("Hệ số b:", -6.0, 6.0, float(data.get("b", -2.0)), 0.5, key="lab_p2_b")
            fc = st.slider("Hệ số c:", -6.0, 6.0, float(data.get("c", -1.0)), 0.5, key="lab_p2_c")
            
            x_dinh = -fb / (2 * fa)
            y_dinh = fa * x_dinh**2 + fb * x_dinh + fc
            st.info(f"**$y = {fa}x^2 + ({fb})x + ({fc})$**")
            st.caption(f"📌 **Đỉnh:** $I({x_dinh:.2f}; {y_dinh:.2f})$<br>📌 **Trục đối xứng:** $x = {x_dinh:.2f}$", unsafe_allow_html=True)
        with c2:
            x_vals = np.linspace(-6, 6, 600)
            y_vals = fa * x_vals**2 + fb * x_vals + fc
            fig.add_trace(go.Scatter(x=x_vals, y=y_vals, mode='lines', line=dict(color='#38bdf8', width=3), name='Parabol'))
            fig.add_trace(go.Scatter(x=[x_dinh, x_dinh], y=[-12, 12], mode='lines', line=dict(color='#f59e0b', width=1.5, dash='dash'), name='Trục đối xứng'))
            fig.add_trace(go.Scatter(x=[x_dinh], y=[y_dinh], mode='markers+text', marker=dict(size=8, color='gold'), text=[f'I({x_dinh:.1f}; {y_dinh:.1f})'], textposition="top center"))
            
            y_pad = (max(y_vals) - min(y_vals)) * 0.15
            y_min, y_max = min(y_vals) - y_pad, max(y_vals) + y_pad
            
            setup_pedagogical_oxy(fig, [-6, 6], [y_min, y_max])
            fig.update_layout(title="Đồ thị Parabol Bậc 2 (Toán Lớp 10)", height=500)
            st.plotly_chart(fig, use_container_width=True)

    elif dtype == "oxyz":
        c1, c2 = st.columns([1, 3])
        with c1:
            st.caption("⚙️ **Thay đổi tọa độ điểm M(x; y; z):**")
            mx = st.slider("x:", -4.0, 5.0, float(data.get("x", 2.0)), 0.5, key="lab_3d_x")
            my = st.slider("y:", -4.0, 5.0, float(data.get("y", 3.0)), 0.5, key="lab_3d_y")
            mz = st.slider("z:", -4.0, 5.0, float(data.get("z", 4.0)), 0.5, key="lab_3d_z")
            st.info(f"**Điểm $M({mx}; {my}; {mz})$**")
        with c2:
            fig.add_trace(go.Scatter3d(x=[mx], y=[my], z=[mz], mode='markers+text', marker=dict(size=9, color='#38bdf8'), text=[f'M({mx}; {my}; {mz})'], textposition="top center"))
            fig.add_trace(go.Scatter3d(x=[0, mx, mx], y=[0, 0, my], z=[0, 0, 0], mode='lines', line=dict(color='#94a3b8', width=3, dash='dash'), hoverinfo='skip'))
            fig.add_trace(go.Scatter3d(x=[mx, mx], y=[my, my], z=[0, mz], mode='lines', line=dict(color='#f59e0b', width=3, dash='dash'), hoverinfo='skip'))
            fig.update_layout(
                title="Không gian Oxyz: Biểu diễn toạ độ điểm",
                template="plotly_dark",
                scene=dict(
                    xaxis=dict(range=[-5, 5], backgroundcolor="#0f172a"),
                    yaxis=dict(range=[-5, 5], backgroundcolor="#0f172a"),
                    zaxis=dict(range=[-5, 5], backgroundcolor="#0f172a"),
                    aspectmode='cube'
                ),
                height=500,
                margin=dict(l=10, r=10, t=30, b=10)
            )
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("💡 Đã tiếp nhận yêu cầu. Kéo thanh trượt hoặc nhập tham số để mô phỏng tương tác!")

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

# ==============================================================================
# 7. TIÊU ĐỀ TRANG VÀ BANNER CHÍNH
# ==============================================================================
st.markdown('<div class="main-header"><div class="main-title">🏫 GIA SƯ AI - HỆ SINH THÁI LỚP HỌC ĐẢO NGƯỢC</div><div class="sub-title">Trường THPT Tân Hiệp & Trung tâm Thiện Nhân • Đồng hành từ Lớp 6 đến Lớp 12</div><div style="margin-top: 8px;"><span class="badge-tag">Bộ sách: Kết Nối Tri Thức Với Cuộc Sống</span><span class="badge-tag" style="border-color: #34d399; color: #34d399; margin-left: 8px;">Chuẩn CT GDPT 2018 & Quy chế 2026</span></div></div>', unsafe_allow_html=True)

# ==============================================================================


# ==============================================================================
# HỆ THỐNG PHÁT ÂM TIẾNG ANH BẢN NGỮ CHUẨN QUỐC TẾ (IELTS / TOEFL / PTE)
# ==============================================================================
# ==============================================================================
# HỆ THỐNG PHÁT ÂM TIẾNG ANH BẢN NGỮ CHUẨN QUỐC TẾ (IELTS / TOEFL / PTE)
# ==============================================================================
def create_pedagogical_tts_component(raw_text: str, subject_name: str, comp_key: str):
    # CHỈ KÍCH HOẠT DUY NHẤT CHO MÔN TIẾNG ANH (KHÔNG TẠO BANNER RÁC)
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

# ==============================================================================
# BỘ CÔNG CỤ PHÒNG LUYỆN NÓI TIẾNG ANH PHẢN XẠ 1-1 (CHỈ HIỂN THỊ KHI CHỌN MÔN TIẾNG ANH)
# ==============================================================================
def render_voice_speech_tex_and_english_evaluator(stage_id: str, current_subject: str, current_grade: int):
    # CHỈ HIỂN THỊ DUY NHẤT CHO MÔN TIẾNG ANH TẠI TRẠM 1 (CÁC MÔN KHÁC TUYỆT ĐỐI KHÔNG HIỂN THỊ)
    if current_subject != "Tiếng Anh" or stage_id != 'Tram 1':
        return

    st.markdown("---")
    
    # GIAO DIỆN PHÒNG LUYỆN NÓI TIẾNG ANH PHẢN XẠ 1-1 (AI SPEAKING LAB 50/50 CÂN ĐỐI)
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

    # Tiêm script nghe phát âm 1 lần
    create_pedagogical_tts_component("", "Tiếng Anh", f"init_{stage_id}")

    # Ngân hàng từ vựng & đoạn văn mẫu theo từng Unit chuẩn SGK KNTT
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
        },
        "Unit 3: Music & Cultural Traditions": {
            "vocab": [
                {"word": "Heritage", "ipa": "/ˈherɪtɪdʒ/", "meaning": "Di sản văn hóa"},
                {"word": "Melody", "ipa": "/ˈmelədi/", "meaning": "Giai điệu âm nhạc"},
                {"word": "Traditional", "ipa": "/trəˈdɪʃənl/", "meaning": "Thuộc về truyền thống"},
                {"word": "Instrument", "ipa": "/ˈɪnstrəmənt/", "meaning": "Nhạc cụ biểu diễn"}
            ],
            "passage": "Traditional Vietnamese music like Quan Ho and Ca Tru reflects our profound spiritual identity and unique poetic heritage.",
            "q_reflex": "Do you prefer listening to traditional folk music or modern pop songs? Share your personal reasons."
        },
        "Unit 4: Global Technology & AI Revolution": {
            "vocab": [
                {"word": "Artificial Intelligence", "ipa": "/ˌɑːtɪˈfɪʃl ɪnˈtelɪdʒəns/", "meaning": "Trí tuệ nhân tạo"},
                {"word": "Automation", "ipa": "/ˌɔːtəˈmeɪʃn/", "meaning": "Sự tự động hóa"},
                {"word": "Breakthrough", "ipa": "/ˈbreɪkθruː/", "meaning": "Bước đột phá công nghệ"},
                {"word": "Cybersecurity", "ipa": "/ˈsaɪbəsɪkjʊərəti/", "meaning": "An ninh mạng bảo mật"}
            ],
            "passage": "Artificial intelligence empowers modern teenagers to solve real-world problems and pursue self-directed scientific research.",
            "q_reflex": "How can high school students utilize artificial intelligence responsibly without becoming over-dependent?"
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
        
        # Bảng từ vựng New Words kèm IPA và nút Loa đọc chuẩn không rác UI
        for v in unit_info["vocab"]:
            v_word = v['word']
            v_ipa = v['ipa']
            v_meaning = v['meaning']
            
            # Render từ vựng kèm nút Loa phát âm trực tiếp
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
        
        # Tình huống đối thoại 1-1 với nút đọc câu hỏi
        q_code = f"""
        <div style="background: rgba(30, 41, 59, 0.95); border: 1.5px solid #38bdf8; border-radius: 10px; padding: 12px 14px; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 8px;">
                <div style="color: #38bdf8; font-weight: 800; font-size: 13px;">🤖 CÂU HỎI PHẢN XẠ CỦA GIA SƯ AI:</div>
                <button class="custom-speak-btn" data-text="{unit_info['q_reflex']}" style="background: #1e293b; color: #38bdf8; border: 1px solid #38bdf8; padding: 2px 8px; border-radius: 5px; font-size: 11px; font-weight: 700; cursor: pointer;">
                    🔊 Nghe phát âm
                    <span style="display:none;" class="hidden-speak-text">{unit_info['q_reflex']}</span>
                </button>
            </div>
            <div style="color: #ffffff; font-size: 13.5px; font-weight: 600; margin-top: 6px; line-height: 1.5;">"{unit_info['q_reflex']}"</div>
        </div>
        """
        st.markdown(q_code, unsafe_allow_html=True)

        # Micro Widget Đè để nói: Bình thường XANH LÁ, Đè lên chuyển ĐỎ RỰC rực rỡ kèm hiệu ứng sóng âm!
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
                        stat.innerText = '⚠️ Lỗi Mic: ' + e.error + ' (Nhấn Cho Phép Mic trên trình duyệt)';
                        stat.style.color = '#f87171';
                        isRecording = false;
                    }};

                    rec.onend = function() {{
                        if (isRecording) {{
                            stopRec();
                        }}
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
            with st.spinner("AI Giám khảo IELTS & Giáo viên THPT đang phân tích âm vị, ngữ pháp và độ trôi chảy..."):
                try:
                    rubric_prompt = f"""Bạn là Giám khảo Khảo thí IELTS Quốc tế kiêm Giáo viên Tiếng Anh THPT theo CT GDPT 2018.
Chủ đề bài học SGK: {sel_unit}
Câu hỏi bối cảnh của Thầy AI: '{unit_info['q_reflex']}'
Đoạn văn đọc mẫu SGK: '{unit_info['passage']}'
Bài nói/phát âm thực tế của học sinh: '{student_speech}'

YÊU CẦU ĐÁNH GIÁ CHI TIẾT & CHUẨN SƯ PHẠM:
1. OVERALL BAND SCORE (Thang điểm 0 - 9.0)
2. BẢNG ĐIỂM 4 TIÊU CHÍ CHUẨN QUỐC TẾ:
   - 🗣️ Fluency & Coherence (0-9đ): Độ mạch lạc, tốc độ phản xạ.
   - 📚 Lexical Resource (0-9đ): Mức độ sử dụng từ vựng bài học.
   - ✍️ Grammatical Accuracy (0-9đ): Độ chuẩn thì, cấu trúc câu.
   - 🔊 Pronunciation & Intonation (0-9đ): Trọng âm, âm đuôi (/s/, /ed/).
3. SOI LỖI CỤ THỂ VÀ BẢN NÂNG CẤP (UPGRADED VERSION):
   - Chỉ ra 2 từ/câu cần sửa ngay.
   - Đưa ra phiên bản mẫu nâng cấp Band 8.0 để học sinh ghi nhớ.
4. LƯỢT HỎI PHẢN XẠ TIẾP THEO (FOLLOW-UP QUESTION):
   - Đặt 1 câu hỏi phản xạ nối tiếp bằng tiếng Anh để học sinh tiếp tục nói."""
                    eval_ielts_res = call_gemini_with_fallback(rubric_prompt)
                    st.success("🏆 BẢNG ĐÁNH GIÁ NĂNG LỰC NÓI TIẾNG ANH CHUẨN QUỐC TẾ:")
                    st.markdown(eval_ielts_res)
                except Exception as e:
                    st.error(f"Lỗi chấm điểm: {e}")



# 8. CÁC TRẠM CHÍNH NÂNG CẤP
# ==============================================================================
tab1, tab2, tab3, tab4 = st.tabs(["📖 Trạm 1: Học Tập & Phòng Lab", "✍️ Trạm 2: Gia Sư Socratic & Nộp Bài", "📝 Trạm 3: Khảo Thí Độc Lập", "📊 Trạm 4: Dữ Liệu KHKT & Tự Động Vá Lỗi"])

# ------------------------------------------------------------------------------
# TRẠM 1: TỰ HỌC & PHÒNG LAB
# ------------------------------------------------------------------------------
with tab1:
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader(f"📖 Tự học & Chiếm lĩnh kiến thức môn {subject} - Lớp {grade_num}")

    # GỢI Ý CHỦ ĐỀ CHUẨN XÁC THEO TỪNG MÔN HỌC & KHỐI LỚP (GDPT 2018)
    subject_placeholders = {
        "Toán học": "Ví dụ: Khảo sát hàm số bậc ba, Nguyên hàm và Tích phân, Khối tròn xoay, Tọa độ Oxyz...",
        "Tiếng Anh": "Ví dụ: Unit 1: Life stories, Conditional sentences, Passive voice, IELTS Speaking...",
        "Vật lý": "Ví dụ: Dao động điều hòa, Sóng cơ và sóng âm, Từ trường, Quang hình học, Vật lý hạt nhân...",
        "Hóa học": "Ví dụ: Ester - Lipid, Glucose và Fructose, Amine và Amino acid, Polyme, Cân bằng hóa học...",
        "Sinh học": "Ví dụ: Cơ chế di truyền và biến dị, Quy luật Menđen, Di truyền học người, Hệ sinh thái...",
        "Ngữ văn": "Ví dụ: Đọc hiểu văn bản nghị luận xã hội, Thơ trữ tình hiện đại, Kỹ năng viết bài nghị luận văn học...",
        "Lịch sử": "Ví dụ: Cách mạng tháng Tám 1945, Chiến dịch Điện Biên Phủ, Công cuộc Đổi mới đất nước, Toàn cầu hóa...",
        "Địa lý": "Ví dụ: Chuyển dịch cơ cấu kinh tế, Vùng Đông Nam Bộ, Phát triển kinh tế biển đảo Việt Nam...",
        "Tin học": "Ví dụ: Lập trình Python cơ bản, Thuật toán sắp xếp, Cơ sở dữ liệu quan hệ SQL, Mạng máy tính...",
        "Giáo dục kinh tế và pháp luật": "Ví dụ: Quy luật cung - cầu, Lạm phát và thị trường lao động, Quyền tự do kinh doanh...",
        "Khoa học tự nhiên": "Ví dụ: Cấu tạo nguyên tử, Tế bào nhân thực, Lực và chuyển động, Năng lượng tái tạo...",
        "Lịch sử & Địa lý": "Ví dụ: Các cuộc cách mạng công nghiệp, Văn minh sông Hồng, Khí hậu nhiệt đới ẩm gió mùa...",
        "Giáo dục công dân": "Ví dụ: Tôn trọng sự thật, Phòng chống bạo lực học đường, Quyền và nghĩa vụ học tập..."
    }
    curr_ph = subject_placeholders.get(subject, f"Ví dụ: Bài học trọng tâm môn {subject} Lớp {grade_num}...")

    # Quick topics gợi ý chọn nhanh cho từng môn
    quick_topics_dict = {
        "Toán học": ["Khảo sát hàm số bậc ba", "Nguyên hàm & Tích phân", "Phương pháp tọa độ Oxyz"],
        "Tiếng Anh": ["Unit 1: Life stories", "Conditional sentences", "IELTS Speaking & Vocabulary"],
        "Vật lý": ["Dao động điều hòa", "Sóng cơ & Sóng âm", "Dòng điện xoay chiều"],
        "Hóa học": ["Ester và Lipid", "Glucose & Fructose", "Amine & Amino acid"],
        "Sinh học": ["Cơ chế di truyền", "Quy luật Menđen", "Di truyền học quần thể"],
        "Ngữ văn": ["Nghị luận xã hội", "Thơ hiện đại 1975 nay", "Nghị luận văn học"],
        "Lịch sử": ["Cách mạng tháng Tám", "Chiến dịch Điện Biên Phủ", "Công cuộc Đổi mới"],
        "Địa lý": ["Cơ cấu kinh tế", "Vùng Đông Nam Bộ", "Kinh tế biển đảo"],
        "Tin học": ["Lập trình Python", "Thuật toán sắp xếp", "Cơ sở dữ liệu SQL"],
        "Giáo dục kinh tế và pháp luật": ["Quy luật cung - cầu", "Thị trường lao động", "Pháp luật kinh doanh"]
    }

    col_inp, col_btn = st.columns([3.8, 1.2])
    with col_inp:
        topic_input = st.text_input(
            "📝 Nhập bài học cần chiếm lĩnh kiến thức:", 
            placeholder=curr_ph,
            key=f"topic_input_{current_context_key}"
        )
    with col_btn:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        btn_submit_lesson = st.button("🚀 Soạn bài học", key=f"btn_soan_{current_context_key}")

    q_topics = quick_topics_dict.get(subject, ["Chuyên đề trọng tâm 1", "Chuyên đề trọng tâm 2"])
    st.caption("💡 **Chủ đề gợi ý học nhanh:** " + " • ".join([f"`{t}`" for t in q_topics]))

    if btn_submit_lesson and topic_input.strip():
        st.session_state.tram1_count += 1
        with st.spinner("Đang biên soạn chuẩn ngữ liệu SGK KNTT và cấu trúc Socratic..."):
            study_prompt = f"""[HỆ THỐNG BIÊN SOẠN BÀI HỌC CHUẨN QUỐC GIA - CT GDPT 2018 & QUY CHẾ THI 2026 (Cập nhật QĐ 764/QĐ-BGDĐT & TT 13/2026/TT-BGDĐT)]
Môn học: {subject} | Khối lớp: {grade_num}. Chủ đề bài học: '{topic_input}'.

YÊU CẦU PHÁP LÝ & HỌC THUẬT BẮT BUỘC:
1. BÁM SÁT 100% NGỮ LIỆU & BẢN QUYỀN SGK KẾT NỐI TRI THỨC VỚI CUỘC SỐNG:
   - TOÁN HỌC: TUYỆT ĐỐI CẤM đưa các kiến thức chương trình cũ (2006) vào bài học như: Tích phân từng phần, Tích phân đổi biến số, Đồ thị hàm bậc 4 trùng phương. Chỉ sử dụng tích phân cơ bản và ứng dụng thực tế. VỚI HÀM SỐ, TUYỆT ĐỐI TUÂN THỦ 3 BƯỚC KHẢO SÁT CHUẨN KNTT LỚP 12.
   - HÓA HỌC & KHTN: DÙNG 100% DANH PHÁP QUỐC TẾ IUPAC.
   - NGỮ VĂN: Tiếp cận theo ĐẶC TRƯNG THỂ LOẠI. TUYỆT ĐỐI KHÔNG phân tích cơ học bổ dọc. Ngữ liệu ngoài SGK.
   - VẬT LÝ & SINH HỌC: Tuân thủ đúng bản chất hiện tượng, chuẩn SI.
   - TIẾNG ANH: TUYỆT ĐỐI BẮT BUỘC toàn bộ từ vựng, đoạn văn, câu hỏi trắc nghiệm, các phương án A/B/C/D, và bài tập ngữ pháp phải viết 100% bằng TIẾNG ANH. Chỉ dùng tiếng Việt khi giải thích hoặc gợi ý tư duy Socratic.
2. QUY ĐỊNH CẤU TRÚC KỸ THUẬT:
   - BBT: DÙNG BẢNG MARKDOWN TIÊU CHUẨN. (Sử dụng \\nearrow, \\searrow, || cho tiệm cận đứng).
   - ĐỒ THỊ: Mô tả bằng lời, ghi chú: "(Kéo xuống Phòng Lab ảo bên dưới để trực quan hóa nhé!)".
   - TRẮC NGHIỆM SOCRATIC: Sinh chính xác 3 câu hỏi trắc nghiệm đánh giá năng lực. 
     + Bắt đầu mỗi câu bằng chữ "Câu 1:", "Câu 2:", "Câu 3:".
     + 4 phương án A, B, C, D trên 4 dòng riêng biệt.
     + Kèm dòng "ĐÁP ÁN: [A/B/C/D]" và dòng "GIẢI THÍCH: [Gợi ý tư duy Socratic]".
   - TỰ LUẬN: Sinh 2 bài tập vận dụng kèm HƯỚNG DẪN TƯ DUY 4 BƯỚC (PHƯƠNG PHÁP POLYA). LỆNH CẤM KỴ: TUYỆT ĐỐI KHÔNG GIẢI CHI TIẾT, KHÔNG VIẾT ĐÁP SỐ. MỖI BƯỚC CHỈ ĐẶT 1 CÂU HỎI GỢI MỞ ĐỂ HỌC SINH TỰ TƯ DUY!

TIÊU ĐỀ BẮT BUỘC (Phải giữ đúng text này để hệ thống nhận diện):
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
        
        # In Phần 1 kèm nút đọc Giảng bài bằng Giọng nói sư phạm
        if len(part2_split) > 0 and part2_split[0].strip():
            cleaned_p1 = re.sub(r'\n\s*\n', '\n\n', part2_split[0].strip())
            cleaned_p1 = re.sub(r'(?:\s*\-\-\-\s*)+$', '', cleaned_p1)
            st.markdown(cleaned_p1)

            # --- NÚT ĐỌC BÀI GIẢNG TTS SƯ PHẠM CHUẨN GDPT 2018 & TIẾNG ANH BẢN NGỮ ---
            create_pedagogical_tts_component(cleaned_p1, subject, "tram1_lesson")

        # In Phần 2 (Trắc nghiệm tương tác)
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
                    else:
                        st.warning("Vui lòng chọn một đáp án!")
                if idx in st.session_state.quiz_states:
                    status, msg = st.session_state.quiz_states[idx]
                    if status == "correct": st.success(msg)
                    else: st.warning("🤔 Suy ngẫm thêm gợi ý dưới đây nhé:"); st.info(msg)
                st.markdown("---")
        elif len(part2_split) > 1 and "PHẦN 3" in part2_split[1].upper():
            st.warning("💡 Hệ thống AI vừa sinh ra một định dạng trắc nghiệm mới. Đang hiển thị ở chế độ xem tĩnh:")
            fallback_p2 = re.split(r'(?i)###\s*PHẦN\s*3', part2_split[1])[0]
            st.markdown(fallback_p2.strip())
        
        # In Phần 3
        if len(part3_split) > 1 and part3_split[-1].strip():
            st.markdown("### ✍️ Phần 3: Bài tập tự luận & Hướng dẫn tư duy")
            st.markdown(part3_split[-1].strip())

    
    render_voice_speech_tex_and_english_evaluator('Tram 1', subject, grade_num)

    # PHÒNG LAB VIRTUAL LAB
    st.markdown("---")
    st.markdown('<h4 style="color: #38bdf8; margin-top: 0; margin-bottom: 5px; font-weight: 800;">🔬 PHÒNG THÍ NGHIỆM ẢO THEO YÊU CẦU (VIRTUAL LAB)</h4>', unsafe_allow_html=True)
    st.markdown(f'<div style="color: #cbd5e1; font-size: 15px; margin-bottom: 12px;">Hệ thống AI đang liên kết trực tiếp với <b>Môn {subject} - Lớp {grade_num}</b>. Nhập yêu cầu mô phỏng đồ thị, tích phân, miền nghiệm, không gian 3D, hoặc sơ đồ tư duy:</div>', unsafe_allow_html=True)
    
    lab_ph = f"Ví dụ Tiếng Anh: Vẽ sơ đồ tư duy thì động từ, sơ đồ từ vựng Topic Education..." if subject == "Tiếng Anh" else (f"Ví dụ Toán: Vẽ đồ thị, diện tích tích phân, sơ đồ tư duy..." if subject == "Toán học" else "Ví dụ: Mô phỏng quy trình, sơ đồ tư duy bài học...")
    lab_command = st.text_input("Lệnh mô phỏng:", placeholder=lab_ph, key=f"lab_cmd_{current_context_key}", label_visibility="collapsed")
    
    if st.button("✨ Khởi chạy Phòng Lab", key=f"btn_lab_{current_context_key}") and lab_command.strip():
        st.session_state.tram1_count += 1
        with st.spinner("AI đang phân tích ngữ cảnh liên môn và dựng mô hình..."):
            # TRÍCH XUẤT ĐẦY ĐỦ 100% NGỮ CẢNH BÀI HỌC, TRẮC NGHIỆM VÀ TỰ LUẬN PHÍA TRÊN
            full_context_blocks = []
            if st.session_state.get("current_lesson"):
                full_context_blocks.append("=== TOÀN BỘ NỘI DUNG BÀI HỌC VỪA SINH RA TRÊN MÀN HÌNH ===\n" + st.session_state.current_lesson)
            if st.session_state.get("parsed_quiz"):
                q_text = "=== DANH SÁCH CÂU HỎI TRẮC NGHIỆM (PHẦN 2) ===\n"
                for q_i, q_val in enumerate(st.session_state.parsed_quiz):
                    q_text += f"Câu {q_i+1}: {q_val.get('question')} | Đáp án: {q_val.get('correct')} | Gợi ý: {q_val.get('explain')}\n"
                full_context_blocks.append(q_text)
            
            # TẦNG 1: TỰ ĐỘNG BƠM NGỮ CẢNH NẾU CHƯA CÓ BÀI HỌC (CHỐNG MÙ 100%)
            if not full_context_blocks:
                topic_hint = st.session_state.get("current_topic", "") or lab_command.strip()
                full_context_blocks.append(f"""=== THÔNG TIN CHỦ ĐỀ HỌC TẬP (TỰ ĐỘNG BƠM TỪ YÊU CẦU CỦA HỌC SINH) ===
Môn học: {subject} - Lớp {grade_num}.
Chủ đề trọng tâm học sinh đang học: '{topic_hint}'.
Hệ thống AI BẮT BUỘC dựa vào toàn bộ kiến thức chuẩn SGK Kết Nối Tri Thức (NXB Giáo Dục Việt Nam) của môn {subject} Lớp {grade_num} về chủ đề này để phân tích yêu cầu của học sinh và chọn ĐÚNG 1 loại mô hình (đồ thị 2D, 3D, diện tích, hoặc sơ đồ tư duy) phù hợp nhất!""")

            context_text = "\n\n".join(full_context_blocks)
            
            lab_prompt = f"""[HỆ TRI THỨC SƯ PHẠM QUỐC GIA - CHUẨN CT GDPT 2018 & QUY CHẾ THI 2026 (Cập nhật QĐ 764/QĐ-BGDĐT & TT 13/2026/TT-BGDĐT)]
Môn học: {subject} | Khối lớp: {grade_num}. 
NGỮ CẢNH BÀI HỌC, TRẮC NGHIỆM VÀ TỰ LUẬN HIỆN TẠI (BẮT BUỘC THAM CHIẾU KHI HỌC SINH NÓI 'CÂU 1', 'CÂU 2', 'BÀI TỰ LUẬN TRÊN', 'HÌNH Ở TRÊN'...):
{context_text}

QUY TẮC BẮT BUỘC VỀ SỰ KHỚP NỐI NGỮ CẢNH (CỰC KỲ QUAN TRỌNG):
- NẾU học sinh yêu cầu mô phỏng hoặc vẽ hình từ một câu trong bài học/tự luận phía trên (Ví dụ: "vẽ khối tròn xoay trong câu 2 tự luận", "vẽ đồ thị câu 1 trắc nghiệm", "mô phỏng hình ở trên"...):
  AI BẮT BUỘC trích xuất CHÍNH XÁC hàm số f(x), các cận tích phân a, b hoặc phương trình có trong đúng câu đó ở ngữ cảnh bài học!
  TUYỆT ĐỐI KHÔNG TỰ Ý BỊA RA HÀM MỚI khi bài học đã có sẵn hàm số cụ thể!
- Ví dụ: Nếu câu 2 tự luận có hàm y = sqrt(x) xoay quanh Ox từ 1 đến 4:
  -> PHẢI xuất chính xác {{"type": "revolve_ox", "func": "sqrt(x)", "a": 1.0, "b": 4.0}}

QUY TẮC CHỌN MÔ HÌNH SƯ PHẠM:
- NẾU học sinh yêu cầu "vẽ đồ thị", "vẽ hình", "mô phỏng 2D/3D", "vẽ miền nghiệm": BẮT BUỘC dùng type "dynamic_code" hoặc "func_...". TUYỆT ĐỐI KHÔNG vẽ sơ đồ tư duy (mermaid)!
- CHỈ TRẢ VỀ sơ đồ tư duy (mermaid) khi học sinh CÓ RÕ RÀNG các từ khóa: "sơ đồ", "tư duy", "tóm tắt", "mindmap".

---
Yêu cầu của học sinh: "{lab_command}"

NHIỆM VỤ: Xuất DUY NHẤT 1 khối JSON hợp lệ phân loại mô hình trực quan (KHÔNG VIẾT CHỮ NGOÀI JSON).

QUY TẮC PHÂN LOẠI MÔ HÌNH:
1. DIỆN TÍCH HÌNH PHẲNG TÍCH PHÂN TỪ A ĐẾN B (Toán 12):
   {{"type": "area", "func": "x**2 - 3*x + 2", "a": 0.0, "b": 3.0}}
2. KHỐI TRÒN XOAY 3D TÍCH PHÂN QUANH OX (Toán 12):
   {{"type": "revolve_ox", "func": "2*x + 1", "a": 2.0, "b": 5.0}}
3. HÀM BẬC 3 (ax^3+bx^2+cx+d):
   {{"type": "func_3", "a": 1, "b": -3, "c": 0, "d": 2}}
4. HÀM PHÂN THỨC 1/1 ((ax+b)/(cx+d)):
   {{"type": "func_1_1", "a": 1, "b": 1, "c": 1, "d": -1}}
5. HÀM PHÂN THỨC 2/1 ((ax^2+bx+c)/(dx+e)):
   {{"type": "func_2_1", "a": 1, "b": -2, "c": 2, "d": 1, "e": -1}}
6. PARABOL BẬC 2 (ax^2+bx+c):
   {{"type": "parabola", "a": 1, "b": -2, "c": 1}}
7. KHÔNG GIAN OXYZ:
   {{"type": "oxyz", "x": 2, "y": 3, "z": 4}}
8. MÔ PHỎNG ĐỒ THỊ ĐỘNG PLOTLY (Miền nghiệm BPT, Đồ thị Tùy biến, Vật lý, Hóa học...):
   {{"type": "dynamic_code", "python_code": "fig = go.Figure()\\nfig.add_trace(go.Scatter(x=[-5,5], y=[-5,5]))\\nsetup_pedagogical_oxy(fig, [-5, 5], [-5, 5])"}}
   (Lưu ý: Chỉ sử dụng các thư viện go, np, math, pd, px. Gọi setup_pedagogical_oxy ở cuối).
9. SƠ ĐỒ TƯ DUY TƯƠNG TÁC THUYẾT TRÌNH (CHO TẤT CẢ CÁC MÔN VÀ CÁC KHỐI LỚP 6-12 CHUẨN KNTT):
   QUY CHUẨN SƠ ĐỒ BẮT BUỘC:
   - ĐỘ SÂU & TOÀN DIỆN: Phải tóm tắt ĐẦY ĐỦ VÀ SÂU SẮC toàn bộ kiến thức cốt lõi, công thức, định lý ở bài học phía trên. Tối thiểu 3-5 nhánh chính cấp 1, mỗi nhánh chính bắt buộc có 2-4 nhánh con chi tiết. Tuyệt đối không vẽ sơ sài 1-2 nhánh!
   - HỖ TRỢ ĐA NGÔN NGỮ (VIỆT - ANH): Học sinh có thể ra lệnh bằng Tiếng Việt hoặc Tiếng Anh (Ví dụ: 'summarize', 'mindmap', 'key vocabulary', 'grammar', 'draw a mindmap about...'). Khi môn học là Tiếng Anh, sơ đồ tư duy phải được trình bày chuẩn phong cách Tiếng Anh học thuật CEFR/IELTS, các nhánh từ vựng kèm loại từ (n, v, adj) và câu ví dụ ngữ cảnh rõ ràng.
   - NGUYÊN TẮC GỌN GÀNG - MỖI NHÁNH CON 1 CÔNG THỨC: Tuyệt đối KHÔNG gộp nhiều công thức dài vào chung 1 ô làm dài dòng. Tách rõ ràng từng nhánh con riêng biệt, ví dụ:
     + Nhánh 1: A1[\"Cận trùng nhau: $\\int_a^a f(x)dx = 0$\"]
     + Nhánh 2: A2[\"Đổi cận đảo dấu: $\\int_a^b f(x)dx = -\\int_b^a f(x)dx$\"]
     + Nhánh 3: A3[\"Tính cộng đoạn: $\\int_a^b f(x)dx + \\int_b^c f(x)dx = \\int_a^c f(x)dx$\"]
   - TOÀN VẸN CÔNG THỨC TOÁN HỌC: Mọi công thức PHẢI có ĐẦY ĐỦ hàm số f(x)dx, dấu phép tính (đặc biệt là dấu trừ - trong công thức đổi cận) và các cận a, b. TUYỆT ĐỐI NGHIÊM CẤM VIẾT TẮT DẤU BA CHẤM '...' TRONG CÔNG THỨC TOÁN!
   - CÔNG THỨC TOÁN / KHTN: Mọi công thức toán (tích phân, nguyên hàm, đạo hàm, diện tích, thể tích, phân số, cận [a, b]...) PHẢI BỌC TRONG DẤU $...$ chuẩn LaTeX (ví dụ: $\\int_a^b f(x)dx = F(b)-F(a)$, $S = \\int_a^b |f(x)|dx$, $V = \\pi \\int_a^b [f(x)]^2 dx$).
   - LIÊN KẾT BÀI TẬP: Nếu học sinh yêu cầu sơ đồ kèm ví dụ/câu hỏi ở trên, trích xuất nhánh con nối trực tiếp với ví dụ/câu hỏi đó!
   Mẫu chuẩn: {{\"type\": \"mermaid\", \"code\": \"graph LR\\n   Root[\\\"🎯 TIÊU ĐỀ CHỦ ĐỀ CHÍNH\\\"] --> A[\\\"1. Khái niệm trọng tâm\\\"]\\n   Root --> B[\\\"2. Các tính chất cơ bản\\\"]\\n   Root --> C[\\\"3. Ứng dụng thực tiễn\\\"]\\n   A --> A1[\\\"Định nghĩa: $\\\\int_a^b f(x)dx = F(b)-F(a)$\\\"]\\n   B --> B1[\\\"Cận trùng nhau: $\\\\int_a^a f(x)dx = 0$\\\"]\\n   B --> B2[\\\"Đổi cận đảo dấu: $\\\\int_a^b f(x)dx = -\\\\int_b^a f(x)dx$\\\"]\\n   B --> B3[\\\"Tính cộng đoạn: $\\\\int_a^b f(x)dx + \\\\int_b^c f(x)dx = \\\\int_a^c f(x)dx$\\\"]\\n   C --> C1[\\\"Diện tích hình phẳng: $S = \\\\int_a^b |f(x)|dx$\\\"]\\n   C --> C2[\\\"Thể tích tròn xoay: $V = \\\\pi \\\\int_a^b [f(x)]^2 dx$\\\"]\"}}
"""

            try:
                raw_json = call_gemini_with_fallback(lab_prompt, json_mode=True)
                raw_json = raw_json.strip()
                if raw_json.startswith("```json"): raw_json = raw_json[7:-3].strip()
                elif raw_json.startswith("```"): raw_json = raw_json[3:-3].strip()

                # BỘ LỌC THÔNG MINH BẮT TRỰC TIẾP MERMAID KHI AI TRẢ VỀ RAW HOẶC JSON LỖI NHÁY KÉP
                if "graph " in raw_json or "flowchart " in raw_json or "-->" in raw_json:
                    if not raw_json.startswith("{"):
                        st.session_state.lab_data = {"type": "mermaid", "code": raw_json}
                    else:
                        try:
                            st.session_state.lab_data = json.loads(raw_json)
                        except Exception:
                            m_code = re.search(r'"code"\s*:\s*"(.*?)"\s*(?:,\s*"|\})', raw_json, re.DOTALL)
                            if m_code:
                                try:
                                    extracted = m_code.group(1).encode('utf-8').decode('unicode_escape', errors='ignore')
                                except Exception:
                                    extracted = m_code.group(1)
                                st.session_state.lab_data = {"type": "mermaid", "code": extracted}
                            else:
                                st.session_state.lab_data = {"type": "mermaid", "code": raw_json}
                else:
                    st.session_state.lab_data = json.loads(raw_json)
            except Exception as e:
                # KIỂM TRA NẾU HỌC SINH YÊU CẦU VẼ SƠ ĐỒ TƯ DUY -> FALLBACK SƠ ĐỒ CỨU HỘ CHUẨN KNTT THAY VÌ ĐỒ THỊ BẬC 3!
                is_mindmap_req = any(kw in lab_command.lower() for kw in [
                    "sơ đồ", "tư duy", "mindmap", "tóm tắt", "cây thư mục", "hệ thống hóa",
                    "mind map", "diagram", "summarize", "summary", "tree", "vocabulary", "grammar"
                ])
                if is_mindmap_req:
                    topic_title = st.session_state.get("current_topic", "") or f"CHỦ ĐỀ {subject.upper()} LỚP {grade_num}"
                    if subject == "Tiếng Anh":
                        fallback_mermaid = f"""graph LR
    Root["🎯 {topic_title.upper()}"] --> A["📖 1. Key Vocabulary (Từ vựng cốt lõi)"]
    Root --> B["⚡ 2. Core Grammar (Ngữ pháp trọng tâm)"]
    Root --> C["🔍 3. Reading & Language Skills"]
    Root --> D["🌐 4. IELTS / TOEFL Speaking & Usage"]
    A --> A1["Topic Vocabulary & Phonetics"]
    A --> A2["Collocations & Phrasal Verbs"]
    B --> B1["Sentence Structures & Rules"]
    B --> B2["Common Errors to Avoid"]
    C --> C1["Main Ideas & Key Details"]
    C --> C2["Contextual Comprehension"]
    D --> D1["Natural Intonation & Fluency"]
    D --> D2["Practical Daily Communication"]"""
                    else:
                        fallback_mermaid = f"""graph LR
    Root["🎯 {topic_title.upper()}"] --> A["📖 1. Định nghĩa & Khái niệm cốt lõi"]
    Root --> B["⚡ 2. Công thức & Quy tắc trọng tâm"]
    Root --> C["🔍 3. Phương pháp giải & Dạng bài tập"]
    Root --> D["🌐 4. Ứng dụng thực tiễn & Liên môn"]
    A --> A1["Khái niệm cơ bản chuẩn SGK Kết Nối Tri Thức"]
    A --> A2["Điều kiện áp dụng & Phạm vi xác định"]
    B --> B1["Công thức nền tảng"]
    B --> B2["Các tính chất biến đổi quan trọng"]
    C --> C1["Dạng 1: Nhận biết & Thông hiểu"]
    C --> C2["Dạng 2: Vận dụng & Liên hệ các câu hỏi trên"]
    D --> D1["Mô hình hóa thực tiễn đời sống"]
    D --> D2["Ý nghĩa liên môn Toán - KHTN - Công nghệ"]"""
                    st.session_state.lab_data = {"type": "mermaid", "code": fallback_mermaid}
                else:
                    st.warning("⚠️ AI trả về định dạng chưa chuẩn nên hệ thống hiển thị mô hình mẫu. Em thử diễn đạt lại yêu cầu rõ hơn nhé!")
                    st.session_state.lab_data = {"type": "func_3", "a": 1, "b": -3, "c": 0, "d": 2}

    if st.session_state.get("lab_data"):
        data = st.session_state.lab_data
        st.success("✨ Đã khởi tạo mô phỏng Phòng Lab liên môn thành công!")
        render_smart_lab(data)

# ------------------------------------------------------------------------------
# TRẠM 2: GIA SƯ SOCRATIC & NỘP BÀI (CHUẨN CHẨN ĐOÁN VÁ LỖ HỔNG ĐA MÔN LỚP 6-12)
# ------------------------------------------------------------------------------
with tab2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader(f"✍️ Gia Sư Socratic Môn: {subject} - Lớp {grade_num}")
    st.caption("Khung Tri Thức Chuẩn Hóa CT GDPT 2018 & SGK Kết Nối Tri Thức (NXBGDVN) • Vấn đáp Socratic • Chẩn đoán lỗ hổng kiến thức • Dẫn dắt tư duy, không giải hộ.")

    if st.button("🔄 Xóa đối thoại cũ"): 
        st.session_state.messages = []
        st.session_state.chat = None
        st.rerun()

    socratic_system_instruction = f"""Bạn là Thầy giáo Gia Sư AI tại Trường THPT Tân Hiệp & Trung tâm Bồi dưỡng Văn hóa Thiện Nhân (An Giang).
Học sinh đang học: Môn {subject} - Khối lớp: {grade_num} ({'Cấp THCS' if grade_num <= 9 else 'Cấp THPT'}). Tên của học sinh là: {student_name}.

TRIẾT LÝ HỌC THUẬT BẮT BUỘC: "NÚT THẮT CỔ CHAI CHUẨN HÓA TRI THỨC"
Mọi tri thức nhân loại khi hướng dẫn cho học sinh BẮT BUỘC phải đi qua bộ lọc của Chương trình GDPT 2018 (Thông tư 32/2018/TT-BGDĐT), Quy chế thi 2026 và SGK Kết Nối Tri Thức Với Cuộc Sống (NXB Giáo Dục Việt Nam). TUYỆT ĐỐI KHÔNG đem kiến thức vượt khung áp đặt cho học sinh.

QUY TẮC NHẬN DIỆN ẢNH & XÁC NHẬN KÝ TỰ MỜ:
- Sử dụng khả năng OCR Multimodal chính xác 100%. Đọc kỹ từng công thức, danh pháp IUPAC, thể loại văn bản.
- NẾU ẢNH BỊ MỜ HOẶC CÓ KÝ TỰ/CÔNG THỨC KHÔNG CHẮC CHẮN 100%: TUYỆT ĐỐI KHÔNG ĐOÁN BỪA. Chủ động hỏi lại học sinh để xác nhận: "Thầy thấy ở bước 2 công thức em viết bị mờ chỗ..., em xác nhận lại giúp Thầy xem đó là... hay là... nhé!".
- Nếu ảnh bị mờ hoàn toàn, yêu cầu học sinh chụp lại góc thẳng, đủ ánh sáng.

QUY TẮC SƯ PHẠM SOCRATIC:
- TUYỆT ĐỐI KHÔNG giải hộ, KHÔNG viết toàn bộ lời giải sẵn, KHÔNG đưa ngay đáp số cuối cùng.
- Khen ngợi phần học sinh đã làm đúng để tạo động lực. Gọi tên học sinh thân thiện: {student_name}.
- Chỉ ra nút thắt hoặc chỗ nhầm lẫn công thức.
- Đặt từ 1 đến 2 câu hỏi gợi mở ngắn (Scaffolding) để học sinh tự mình tư duy và sửa lại bài.

ĐỊNH DẠNG CHẨN ĐOÁN BẮT BUỘC (Khi nhận xét ảnh bài làm):
Cuối phản hồi PHẢI có khối JSON:
<DIAGNOSTIC>{{"topic":"Tên bài học SGK KNTT Lớp {grade_num}","error_type":"Lỗi khái niệm/Lỗi tính toán/Lỗi phương pháp/Lỗi diễn đạt","evaluation":"Đạt/Cần rèn luyện thêm","scores":{{"truc1":80,"truc2":65,"truc3":90,"truc4":70,"truc5":85}}}}</DIAGNOSTIC>"""

    st.info("💡 **Mẹo chụp ảnh bài làm tối ưu:** Hãy chụp thẳng góc, đủ ánh sáng và chữ viết rõ nét. Nếu có ký tự mờ, Thầy AI sẽ chủ động hỏi lại em để xác nhận chứ không đoán bừa!")
    
    uploaded_file = st.file_uploader("📸 Tải ảnh bài làm (JPG, PNG)", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        st.image(Image.open(uploaded_file), caption="Bài làm của em", use_container_width=True)
        if st.button("🚀 Bắt đầu nhận xét"):
            st.session_state.tram2_count += 1
            with st.spinner(f"Thầy đang đối chiếu chuẩn kiến thức SGK KNTT Lớp {grade_num} và soi từng bước làm của {student_name}..."):
                try:
                    full_res = call_gemini_with_fallback(
                        [f"Học sinh {student_name} nộp ảnh bài làm môn {subject} Lớp {grade_num}. Thầy hãy soi kỹ bài làm và nhận xét Socratic:", Image.open(uploaded_file)], 
                        system_instruction=socratic_system_instruction
                    )
                    student_fb = full_res.split("<DIAGNOSTIC>")[0].strip() if "<DIAGNOSTIC>" in full_res else full_res
                    if "<DIAGNOSTIC>" in full_res:
                        try:
                            diag = json.loads(full_res.split("<DIAGNOSTIC>")[1].split("</DIAGNOSTIC>")[0].strip())
                            entry = {
                                "time": get_vn_time(), 
                                "name": student_name,
                                "grade": grade, 
                                "subject": subject, 
                                "topic": diag.get("topic", "Kiến thức SGK KNTT"), 
                                "error_type": diag.get("error_type", "Chưa rõ"),
                                "evaluation": diag.get("evaluation", "Cần theo dõi"),
                                "scores": diag.get("scores", {"truc1":75,"truc2":80,"truc3":70,"truc4":85,"truc5":90}),
                                "type": "SOCRATIC_DIAGNOSTIC"
                            }
                            st.session_state.analytics_logs.append(entry)
                            st.session_state.student_progress_history.append(entry)
                            if sheet_webhook_url: 
                                requests.post(sheet_webhook_url, json=entry, timeout=5)
                        except Exception: 
                            pass
                    st.session_state.messages = [{"role": "user", "content": "*(Em đã nộp ảnh bài làm)*"}, {"role": "assistant", "content": student_fb}]
                    st.rerun()
                except Exception as e: 
                    st.error(f"Lỗi phân tích bài làm: {e}")

    # BẢN ĐỒ LỖ HỔNG KHIẾN THỨC RADAR CHART ĐA MÔN LỚP 6-12
    if st.session_state.get("student_progress_history"):
        with st.expander("🕸️ Bản Đồ Lỗ Hổng Kiến Thức & Năng Lực Sư Phạm (Radar Chart Đa Môn)", expanded=True):
            latest_entry = st.session_state.student_progress_history[-1]
            sc = latest_entry.get("scores", {"truc1":75,"truc2":80,"truc3":70,"truc4":85,"truc5":90})
            
            # Chọn nhãn 5 trục năng lực theo môn học
            if subject == "Toán học":
                categories = ['Đại số / Giải tích', 'Hình học / Oxyz', 'Xác suất / Thống kê', 'Tư duy logic', 'Kỹ năng tính toán']
            elif subject in ["Vật lý", "Hóa học", "Sinh học", "Khoa học tự nhiên"]:
                categories = ['Lý thuyết cốt lõi', 'Phương pháp thí nghiệm', 'Công thức & Tính toán', 'Chuẩn danh pháp IUPAC/SI', 'Vận dụng thực tiễn']
            elif subject == "Ngữ văn":
                categories = ['Đọc hiểu thể loại', 'Thi pháp & Tác phẩm', 'Nghị luận xã hội', 'Nghị luận văn học', 'Ngôn ngữ & Diễn đạt']
            elif subject == "Tiếng Anh":
                categories = ['Grammar & Structure', 'Vocabulary in Context', 'Reading Comprehension', 'Pronunciation & Phonetics', 'Writing Skills']
            else:
                categories = ['Khái niệm cốt lõi', 'Tiến trình / Tọa độ', 'Phân tích số liệu', 'Vận dụng thực tế', 'Tư duy hệ thống']

            r_vals = [sc.get("truc1", 75), sc.get("truc2", 80), sc.get("truc3", 70), sc.get("truc4", 85), sc.get("truc5", 90)]
            r_vals.append(r_vals[0])
            categories.append(categories[0])

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=r_vals, theta=categories, fill='toself', name=student_name,
                fillcolor='rgba(56, 189, 248, 0.35)', line=dict(color='#38bdf8', width=3)
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100], color='#94a3b8'), bgcolor="#0f172a"),
                showlegend=False, template="plotly_dark", height=380, margin=dict(l=40, r=40, t=30, b=30)
            )
            st.plotly_chart(fig_radar, use_container_width=True)
            st.caption(f"📌 **Chẩn đoán gần nhất:** Chủ đề `{latest_entry.get('topic')}` | Phân loại lỗi: `{latest_entry.get('error_type')}` | Đánh giá: `{latest_entry.get('evaluation')}`")

    for idx_m, m in enumerate(st.session_state.get("messages", [])):
        with st.chat_message(m["role"]): 
            st.markdown(m["content"])
            if m["role"] == "assistant" and len(m.get("content", "")) > 15:
                create_pedagogical_tts_component(m["content"], subject, f"t2_msg_{idx_m}")
        
    if len(st.session_state.get("messages", [])) > 0:
        # Micro trợ lý giọng nói trực tiếp cho Khung Chat Socratic
        t2_mic_html = f"""
        <div style="margin: 10px 0 6px 0; display: flex; align-items: center; justify-content: flex-end; gap: 8px;">
            <button id="btn_rec_t2_chat" onclick="toggleRec_t2_chat()" style="background: linear-gradient(135deg, #0284c7, #0369a1); color: #ffffff; border: 1.5px solid #38bdf8; padding: 5px 12px; border-radius: 20px; font-weight: 700; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 6px; box-shadow: 0 2px 8px rgba(56,189,248,0.25);">
                <span id="icon_t2_chat">🎙️</span> <span id="label_t2_chat">Nói câu hỏi vào Mic</span>
            </button>
            <span id="status_t2_chat" style="color: #94a3b8; font-size: 11.5px; font-style: italic;">(Bấm mic để nói câu hỏi rảnh tay)</span>
        </div>
        <script>
        (function() {{
            let recognizing = false;
            let recognition = null;
            const btn = document.getElementById('btn_rec_t2_chat');
            const lbl = document.getElementById('label_t2_chat');
            const icon = document.getElementById('icon_t2_chat');
            const status = document.getElementById('status_t2_chat');

            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {{
                const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
                recognition = new SpeechRec();
                recognition.continuous = false;
                recognition.interimResults = false;
                recognition.lang = '{('en-US' if subject == 'Tiếng Anh' else 'vi-VN')}';

                recognition.onstart = function() {{
                    recognizing = true;
                    btn.style.background = 'linear-gradient(135deg, #e11d48, #be123c)';
                    lbl.innerText = 'Đang nghe...';
                    icon.innerText = '🔴';
                    status.innerText = 'Hãy nói câu hỏi của em...';
                    status.style.color = '#f43f5e';
                }};

                recognition.onresult = function(event) {{
                    const transcript = event.results[0][0].transcript;
                    status.innerText = 'Đã nhận: "' + transcript + '"';
                    status.style.color = '#34d399';
                    try {{
                        const targetDoc = window.parent.document || document;
                        const chatInput = targetDoc.querySelector('textarea[data-testid="stChatInputTextArea"]') || targetDoc.querySelector('[data-testid="stChatInput"] textarea');
                        if (chatInput) {{
                            chatInput.value = transcript;
                            chatInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            chatInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            chatInput.focus();
                        }}
                    }} catch(e) {{ console.warn(e); }}
                }};

                recognition.onerror = function(event) {{
                    recognizing = false;
                    btn.style.background = 'linear-gradient(135deg, #0284c7, #0369a1)';
                    lbl.innerText = 'Nói câu hỏi vào Mic';
                    icon.innerText = '🎙️';
                    status.innerText = 'Lỗi mic: ' + event.error;
                    status.style.color = '#f87171';
                }};

                recognition.onend = function() {{
                    recognizing = false;
                    btn.style.background = 'linear-gradient(135deg, #0284c7, #0369a1)';
                    lbl.innerText = 'Nói câu hỏi vào Mic';
                    icon.innerText = '🎙️';
                }};
            }}

            window.toggleRec_t2_chat = function() {{
                if (!recognition) return;
                if (recognizing) recognition.stop();
                else recognition.start();
            }};
        }})();
        </script>
        """
        components.html(t2_mic_html, height=42)

        if q := st.chat_input("Em chưa hiểu chỗ nào, hãy hỏi Thầy nhé..."):
            st.session_state.tram2_count += 1
            st.session_state.messages.append({"role": "user", "content": q})
            with st.chat_message("user"): 
                st.markdown(q)
            with st.chat_message("assistant"):
                with st.spinner("Thầy đang suy ngẫm câu hỏi của em..."):
                    try:
                        history_context = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-4:]])
                        rep = call_gemini_with_fallback(
                            f"Lịch sử đối thoại trước đó:\n{history_context}\nHọc sinh {student_name} hỏi: {q}\nThầy phản hồi gợi mở Socratic (tuyệt đối không giải hộ, bám sát SGK KNTT Lớp {grade_num}):",
                            system_instruction=socratic_system_instruction
                        )
                        clean_rep = rep.split("<DIAGNOSTIC>")[0].strip()
                        st.markdown(clean_rep)
                        st.session_state.messages.append({"role": "assistant", "content": clean_rep})
                    except Exception as e: 
                        st.error(f"Lỗi phản hồi: {e}")

# ==============================================================================
# NGÂN HÀNG MA TRẬN CHUYÊN ĐỀ KNTT LỚP 6 ĐẾN LỚP 12
# ==============================================================================
BIGDATA_CURRICULUM = {
    "Toán học": {
        12: [
            "Chuyên đề 1: Ứng dụng đạo hàm khảo sát & vẽ đồ thị hàm số (KSHS chuẩn KNTT)",
            "Chuyên đề 2: Vectơ và tọa độ trong không gian Oxyz",
            "Chuyên đề 3: Các số đặc trưng đo mức độ phân tán (Mẫu ghép nhóm)",
            "Chuyên đề 4: Nguyên hàm, Tích phân và ứng dụng thực tiễn",
            "Chuyên đề 5: Phương pháp tọa độ Oxyz (Mặt phẳng, Đường thẳng, Mặt cầu)",
            "Chuyên đề 6: Xác suất có điều kiện, Công thức Bayes"
        ],
        11: [
            "Chuyên đề 1: Hàm số lượng giác và phương trình lượng giác",
            "Chuyên đề 2: Dãy số, Cấp số cộng và Cấp số nhân",
            "Chuyên đề 3: Các số đặc trưng đo xu thế trung tâm của mẫu số liệu ghép nhóm",
            "Chuyên đề 4: Quan hệ song song trong không gian",
            "Chuyên đề 5: Giới hạn và Hàm số liên tục",
            "Chuyên đề 6: Hàm số mũ và hàm số lôgarit",
            "Chuyên đề 7: Đạo hàm và ứng dụng tiếp tuyến",
            "Chuyên đề 8: Quan hệ vuông góc trong không gian",
            "Chuyên đề 9: Xác suất: Biến cố giao và quy tắc nhân xác suất"
        ],
        10: [
            "Chuyên đề 1: Mệnh đề, Tập hợp & BPT bậc nhất hai ẩn",
            "Chuyên đề 2: Hệ thức lượng trong tam giác & Vectơ Oxy",
            "Chuyên đề 3: Hàm số bậc hai, Dấu tam thức bậc hai",
            "Chuyên đề 4: Phương pháp tọa độ Oxy (Đường thẳng, Đường tròn, Conic)",
            "Chuyên đề 5: Đại số tổ hợp (Quy tắc đếm, Hoán vị - Chỉnh hợp - Tổ hợp, Nhị thức Newton)",
            "Chuyên đề 6: Số đặc trưng đo xu thế trung tâm & mức độ phân tán"
        ],
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

# ------------------------------------------------------------------------------
# TRẠM 3: KHẢO THÍ ĐỘC LẬP (MÃ ĐỀ 4 CHỮ SỐ & LATEX IN ẤN CHUẨN BỘ)
# ------------------------------------------------------------------------------
with tab3:
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader(f"📝 Trạm 3: Khảo Thí Độc Lập - Môn {subject} (Lớp {grade_num})")
    st.caption("Cấu trúc Khảo thí 2026 (Theo QĐ 764/QĐ-BGDĐT) • Mã đề 4 chữ số chuẩn Bộ • Tệp in ấn LaTeX căn giữa inline with text • Chấm điểm tức thì.")

    if "exam_state" not in st.session_state: st.session_state.exam_state = "config"
    if "exam_data" not in st.session_state: st.session_state.exam_data = None
    if "violation_count" not in st.session_state: st.session_state.violation_count = 0
    if "exam_answers" not in st.session_state: st.session_state.exam_answers = {}
    if "tram3_chat_messages" not in st.session_state: st.session_state.tram3_chat_messages = []
    if "exam_code" not in st.session_state: st.session_state.exam_code = str(random.randint(1011, 9999))

    def enrich_exam_data(exam):
        if not isinstance(exam, dict): return exam
        for p_key in ["p1", "p2", "p3"]:
            for q in exam.get(p_key, []):
                q_text = str(q.get("q", ""))
                q_lower = q_text.lower()
                
                # QUY TẮC CỐT LÕI CT GDPT 2018: LOẠI BỎ TRIỆT ĐỂ HÀM SỐ BẬC BỐN TRÙNG PHƯƠNG
                if "x^4" in q_text or "x^4" in str(q) or "trùng phương" in q_lower or "bậc 4" in q_lower or "bậc bốn" in q_lower:
                    q["q"] = re.sub(r'x\^4\s*-\s*2mx\^2', r'x^3 - 3mx^2', q.get("q", ""))
                    q["q"] = re.sub(r'x\^4\s*-\s*2x\^2', r'x^3 - 3x^2', q.get("q", ""))
                    q["q"] = re.sub(r'x\^4', r'x^3', q.get("q", ""))
                    q["q"] = re.sub(r'[tT]rùng phương', 'bậc ba', q.get("q", ""))
                    q["q"] = re.sub(r'[bB]ậc 4|[bB]ậc bốn', 'bậc ba', q.get("q", ""))
                    for s in q.get("stmts", []):
                        s["t"] = re.sub(r'x\^4\s*-\s*2mx\^2', r'x^3 - 3mx^2', s.get("t", ""))
                        s["t"] = re.sub(r'x\^4\s*-\s*2x\^2', r'x^3 - 3x^2', s.get("t", ""))
                        s["t"] = re.sub(r'x\^4', r'x^3', s.get("t", ""))
                        s["t"] = re.sub(r'[tT]rùng phương', 'bậc ba', s.get("t", ""))
                        s["t"] = re.sub(r'[bB]ậc 4|[bB]ậc bốn', 'bậc ba', s.get("t", ""))
                    if q.get("opt"):
                        q["opt"] = [re.sub(r'x\^4', 'x^3', str(o)) for o in q["opt"]]
                
                # Làm sạch nội dung câu hỏi nếu AI chèn chuỗi mô tả BBT thô dạng text vào q
                if "bảng biến thiên như sau:" in q_text and ("chạy từ" in q_text or "mang dấu" in q_text or "tăng từ" in q_text):
                    parts = q_text.split("bảng biến thiên như sau:")
                    lead = parts[0].strip() + " có bảng biến thiên như sau:"
                    tail = parts[1].strip()
                    match_ask = re.search(r'([A-ZÀ-Ỹ][^\.\n]*?(?:Có bao nhiêu|Hàm số|Tìm|Điểm|Mệnh đề|Khẳng định|Giá trị|Tập hợp)[^\.\n]*?\?.*)$', tail, re.DOTALL)
                    if match_ask:
                        q["q"] = f"{lead} {match_ask.group(1).strip()}"
                    elif "." in tail:
                        sub_s = [s.strip() for s in tail.split(".") if s.strip()]
                        if len(sub_s) >= 2:
                            q["q"] = f"{lead} {sub_s[-1]}."
                    q["bbt"] = "x | -inf | -1 | 1 | +inf\ny' | | + | 0 | - | 0 | +\ny | -inf | ↗ | 2 | ↘ | -2 | ↗ | +inf"

                if ("bảng biến thiên" in q_lower or "bbt" in q_lower) and not q.get("bbt"):
                    q["bbt"] = "x | -inf | -1 | 1 | +inf\ny' | | + | 0 | - | 0 | +\ny | -inf | ↗ | 2 | ↘ | -2 | ↗ | +inf"
                
                if ("parabol" in q_lower or "đạo hàm" in q_lower) and ("đỉnh" in q_lower or "cắt trục" in q_lower) and not q.get("f"):
                    q["f"] = {"type": "parabola_fprime", "a": 1, "b": -2, "c": -3, "vertex": [1, -4], "roots": [-1, 3]}
                elif ("đồ thị" in q_lower or "hình vẽ" in q_lower or "như hình" in q_lower) and not q.get("f") and not q.get("bbt"):
                    q["f"] = {"type": "func_3", "a": 1, "b": 0, "c": -3, "d": 2}

                if ("ghép nhóm" in q_lower or "mẫu số liệu" in q_lower) and not q.get("mslgn_data"):
                    q["mslgn_data"] = {
                        "title": "Mẫu số liệu ghép nhóm khảo sát thực tế:",
                        "groups": ["[0; 20)", "[20; 40)", "[40; 60)", "[60; 80)", "[80; 100)"],
                        "freq": [5, 12, 18, 10, 5]
                    }

                if not q.get("explain") or len(str(q.get("explain")).strip()) < 10:
                    ans_val = q.get("ans", "")
                    q["explain"] = f"Phân tích bản chất sư phạm SGK Kết Nối Tri Thức: Nhận dạng cấu trúc, loại trừ các phương án nhiễu sai lầm và áp dụng trực tiếp định lý/tính chất cốt lõi để chọn đáp án chuẩn {ans_val}."
        return exam

    def render_fast_visual(q):
        # 1. HIỂN THỊ BẢNG BIẾN THIÊN (BBT) CHUẨN SƯ PHẠM
        if q.get("bbt"):
            raw_bbt = str(q["bbt"])
            raw_bbt = re.sub(r'\\+nearrow\b', '↗', raw_bbt)
            raw_bbt = re.sub(r'\\+searrow\b', '↘', raw_bbt)
            raw_bbt = re.sub(r'[\r\n]+\s*earrow\b', ' ↗ ', raw_bbt)
            raw_bbt = raw_bbt.replace('>>', '↗').replace('>', '↗').replace('\\n', '\n').strip()
            
            lines = [l.strip() for l in raw_bbt.split('\n') if l.strip() and '---' not in l]
            rows = []
            for line in lines:
                parts = [p.strip() for p in line.split('|')]
                parts = [p for p in parts if p]
                if parts: rows.append(parts)

            if rows:
                max_cols = max(len(r) for r in rows)
                for r in rows:
                    while len(r) < max_cols: r.append("")

                st.caption("📋 **Bảng biến thiên:**")
                html = '<div style="background-color: #0f172a; padding: 8px 12px; border-radius: 8px; border: 1.5px solid #334155; margin: 6px 0 10px 0; overflow-x: auto; max-width: 650px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">'
                html += '<table style="width: 100%; border-collapse: collapse; text-align: center; color: #f8fafc; font-size: 13.5px; font-family: Times New Roman, serif;">'
                for r_i, row in enumerate(rows):
                    html += '<tr style="border-bottom: 1px solid #1e293b;">'
                    for c_idx, cell in enumerate(row):
                        c_disp = cell.replace('+\\infty', '+∞').replace('-\\infty', '-∞').replace('+inf', '+∞').replace('-inf', '-∞').replace('$', '').strip()
                        if '||' in c_disp: c_disp = '<span style="color:#f59e0b; font-weight:bold;">||</span>'
                        elif '↗' in c_disp: c_disp = f'<span style="color:#38bdf8; font-weight:bold; font-size:15px;">{c_disp}</span>'
                        elif '↘' in c_disp: c_disp = f'<span style="color:#f87171; font-weight:bold; font-size:15px;">{c_disp}</span>'
                        border_r = "border-right: 1.5px solid #334155;" if c_idx == 0 else "border-right: 1px dashed #1e293b;"
                        bg_h = "background-color: #1e293b; font-weight: bold; width: 50px; color: #38bdf8;" if c_idx == 0 else "min-width: 45px;"
                        html += f'<td style="padding: 6px 10px; {border_r} {bg_h}">{c_disp}</td>'
                    html += '</tr>'
                html += '</table></div>'
                st.markdown(html, unsafe_allow_html=True)

        # 2. HIỂN THỊ BẢNG MẪU SỐ LIỆU GHÉP NHÓM (MSLGN - CHUẨN THỐNG KÊ KNTT)
        if q.get("mslgn_data"):
            ms_info = q["mslgn_data"]
            grps = ms_info.get("groups", [])
            freqs = ms_info.get("freq", [])
            if grps and freqs and len(grps) == len(freqs):
                st.caption(f"📊 **{ms_info.get('title', 'Bảng mẫu số liệu ghép nhóm:')}**")
                ms_html = '<div style="background-color: #0f172a; padding: 8px 12px; border-radius: 8px; border: 1.5px solid #334155; margin: 6px 0 10px 0; overflow-x: auto; max-width: 650px;">'
                ms_html += '<table style="width: 100%; border-collapse: collapse; text-align: center; color: #f8fafc; font-size: 13.5px; font-family: Times New Roman, serif;">'
                ms_html += '<tr style="background-color: #1e293b; color: #38bdf8; font-weight: bold; border-bottom: 1.5px solid #334155;"><td style="padding: 6px; border-right: 1.5px solid #334155;">Nhóm giá trị</td>'
                for g in grps: ms_html += f'<td style="padding: 6px; border-right: 1px dashed #1e293b;">{g}</td>'
                ms_html += '</tr><tr style="border-bottom: 1px solid #1e293b;"><td style="padding: 6px; font-weight: bold; background-color: #1e293b; color: #34d399; border-right: 1.5px solid #334155;">Tần số (m)</td>'
                for f_val in freqs: ms_html += f'<td style="padding: 6px; border-right: 1px dashed #1e293b;">{f_val}</td>'
                ms_html += '</tr></table></div>'
                st.markdown(ms_html, unsafe_allow_html=True)

        # 3. HIỂN THỊ ĐỒ THỊ HÀM SỐ PLOTLY 2D/3D TỐI ƯU
        if q.get("f"):
            f_data = q["f"]
            if isinstance(f_data, dict):
                with st.expander("📈 Xem Đồ thị Hàm số Minh họa (Trực quan hóa chuẩn xác)", expanded=True):
                    try:
                        dtype = f_data.get("type")
                        fig_mini = go.Figure()
                        if dtype == "func_3":
                            fa, fb, fc, fd = float(f_data.get("a", 1)), float(f_data.get("b", -3)), float(f_data.get("c", 0)), float(f_data.get("d", 2))
                            xv = np.linspace(-3.5, 3.5, 300)
                            yv = fa*xv**3 + fb*xv**2 + fc*xv + fd
                            fig_mini.add_trace(go.Scatter(x=xv, y=yv, mode='lines', line=dict(color='#38bdf8', width=2.5), name='y = f(x)'))
                            setup_pedagogical_oxy(fig_mini, [-3.5, 3.5], [min(yv)-1, max(yv)+1])
                        elif dtype in ["parabola", "parabola_fprime"]:
                            fa, fb, fc = float(f_data.get("a", 1)), float(f_data.get("b", -2)), float(f_data.get("c", -3 if dtype=="parabola_fprime" else 1))
                            xv = np.linspace(-2.5, 4.5, 300)
                            yv = fa*xv**2 + fb*xv + fc
                            curve_lbl = "y = f'(x)" if dtype == "parabola_fprime" else "y = f(x)"
                            fig_mini.add_trace(go.Scatter(x=xv, y=yv, mode='lines', line=dict(color='#38bdf8', width=2.5), name=curve_lbl))
                            if dtype == "parabola_fprime":
                                fig_mini.add_trace(go.Scatter(x=[1, -1, 3], y=[-4, 0, 0], mode='markers+text', 
                                    text=['I(1;-4)', 'x=-1', 'x=3'], textposition=['bottom right', 'top left', 'top right'],
                                    marker=dict(color='#f43f5e', size=8), name='Điểm đặc biệt'))
                                setup_pedagogical_oxy(fig_mini, [-2.5, 4.5], [-5.5, 4])
                            else:
                                setup_pedagogical_oxy(fig_mini, [-3.5, 3.5], [min(yv)-1, max(yv)+1])
                        fig_mini.update_layout(height=260, margin=dict(l=5, r=5, t=20, b=5), template="plotly_dark")
                        st.plotly_chart(fig_mini, use_container_width=True, key=f"mini_chart_{random.randint(1, 99999)}")
                    except Exception:
                        pass

    if st.session_state.exam_state == "config":
        col_ex1, col_ex2 = st.columns([1.15, 0.95], gap="medium")
        
        with col_ex1:
            st.markdown("#### ⚙️ Cấu hình Ngữ liệu & Ma trận Chuyên đề:")
            st.info(f"🏷️ **Mã đề thi tự động:** `MÃ ĐỀ {st.session_state.exam_code}` (Chuẩn 4 chữ số Bộ GD&ĐT)")
            
            # GIAO DIỆN CHỌN CHUYÊN ĐỀ THEO TABS & CHECKBOXES NHỎ GỌN, THANH LỊCH (KHÔNG DÙNG THẺ ĐỎ CHÓI MẮT)
            subj_curr = BIGDATA_CURRICULUM.get(subject, {})
            st.markdown("##### 📚 Chọn Chuyên đề Khảo thí theo Khối lớp:")
            
            chosen_topics = []
            if grade_num == 12:
                t12_tab, t11_tab, t10_tab = st.tabs(["🏷️ Lớp 12 (Trọng tâm)", "🏷️ Lớp 11 (Ôn tập)", "🏷️ Lớp 10 (Nền tảng)"])
                with t12_tab:
                    l12 = subj_curr.get(12, [])
                    st.caption("Chọn các chuyên đề trọng tâm Lớp 12:")
                    for idx_t, t_name in enumerate(l12):
                        if st.checkbox(t_name, value=(idx_t == 0), key=f"cb_12_{idx_t}"):
                            chosen_topics.append(f"[Lớp 12] {t_name}")
                with t11_tab:
                    l11 = subj_curr.get(11, [])
                    st.caption("Chọn các chuyên đề ôn tập Lớp 11:")
                    for idx_t, t_name in enumerate(l11):
                        if st.