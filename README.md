# 🏫 GIA SƯ AI - HỆ SINH THÁI LỚP HỌC ĐẢO NGƯỢC (KHKT 2026)
> **Trường THPT Tân Hiệp & Trung tâm Bồi dưỡng Văn hóa Thiện Nhân (An Giang)**  
> *Đồng hành cùng học sinh từ Lớp 6 đến Lớp 12 • Đa môn học • Đa khối lớp • Chuẩn hóa 100% Bộ sách Kết Nối Tri Thức Với Cuộc Sống (NXB Giáo Dục Việt Nam) & CT GDPT 2018 (QĐ 764/QĐ-BGDĐT & TT 13/2026/TT-BGDĐT)*

---

## 🌟 GIỚI THIỆU TỔNG QUAN DỰ ÁN
Dự án **"Gia Sư AI - Hệ Sinh Thái Lớp Học Đảo Ngược"** là giải pháp phần mềm giáo dục đột phá phục vụ cuộc thi Khoa học Kỹ thuật (KHKT) Quốc gia năm 2026. Sản phẩm giải quyết triệt để nút thắt học thụ động của học sinh bằng cách ứng dụng **Phương pháp Socratic (Giảng dạy gợi mở)**, **Quy trình tư duy 4 bước Polya** và **Công nghệ Trực quan hóa 2D/3D / Sơ đồ tư duy D3.js**.

---

## 🚀 KIẾN TRÚC 4 TRẠM TƯƠNG TÁC ĐỘC BẢN

### 📖 TRẠM 1: TỰ HỌC & PHÒNG LAB VIRTUAL LAB
- **Biên soạn giáo án tự động:** Sinh tóm tắt tri thức cốt lõi, trắc nghiệm Socratic và tự luận Polya 4 bước cho tất cả môn học (Toán, KHTN, Lý, Hóa, Sinh, Văn, Anh, Sử, Địa, GDKT-PL, Tin) từ Lớp 6 đến Lớp 12.
- **Giảng bài bằng Giọng nói (HTML5 Web Speech API):** Đọc bài học bằng giọng đọc tự nhiên chuẩn tiếng Việt, tự động chuẩn hóa các ký hiệu toán học, danh pháp IUPAC và từ ngữ sư phạm.
- **Trắc nghiệm tương tác Socratic:** Chấm điểm tức thì, đưa ra phản hồi gợi mở tư duy cho từng phương án.
- **Phòng thí nghiệm ảo (Virtual Lab Plotly 2D/3D):**
  - Mô phỏng Diện tích hình phẳng (Tích phân), Khối tròn xoay 3D (xoay quanh Ox), Hàm bậc 3, Hàm phân thức 1/1, 2/1, Parabol bậc 2, Tọa độ $Oxyz$.
  - **Sơ đồ tư duy tương tác D3.js (Mindmap):** Dựng sơ đồ tư duy dạng cây đa nhánh, hỗ trợ nút bấm mở rộng (`➕ Mở tất cả`, `➖ Thu gọn`, `🎯 Căn giữa`, `📥 Tải Sơ Đồ SVG`).

### ✍️ TRẠM 2: GIA SƯ SOCRATIC & CHẨN ĐOÁN LỖ HỔNG TRI THỨC
- **Quét OCR Multimodal & Nhắc nhở chụp ảnh:** Nhận diện bài làm viết tay/ảnh chụp của học sinh. Nếu bức ảnh bị mờ hoặc công thức không rõ ràng, AI sẽ phát thẻ `<CONFIRM_ASK>` chủ động hỏi lại học sinh để xác nhận chứ không đoán bừa.
- **Bản đồ lỗ hổng kiến thức (Radar Chart 5 Trục):** Phân tích 5 trục năng lực sư phạm đặc thù theo từng môn học và khối lớp (Lớp 6 đến Lớp 12).
- **Theo dõi tiến trình học tập liên phiên:** Ghi nhớ quá trình tiến bộ của học sinh qua từng lần nộp bài.
- **Triết lý Socratic cứng:** Tuyệt đối không giải hộ, chỉ ra nút thắt và đặt câu hỏi gợi mở để học sinh tự mình vỡ ra kiến thức.

### 📝 TRẠM 3: KHẢO THÍ ĐỘC LẬP & XUẤT BẢN LATEX CHUẨN BỘ
- **Cấu trúc khảo thí 2026 (QĐ 764/QĐ-BGDĐT):** Đề thi gồm Phần I (Trắc nghiệm 4 lựa chọn), Phần II (Trắc nghiệm Đúng/Sai), Phần III (Trả lời ngắn).
- **Mã Đề Thi 4 Chữ Số:** Tự động sinh mã đề chuẩn quy định Bộ GD&ĐT (VD: `1012`, `2048`, `4095`).
- **Xuất bản đề thi LaTeX cho Overleaf:** File `.tex` được căn giữa hình ảnh/đồ thị `inline with text` chuẩn mực in ấn của Bộ GD&ĐT, kèm bảng đáp án ma trận.
- **Gia sư Socratic sau thi:** Giải đáp thắc mắc và khắc phục lỗ hổng bài làm trực tiếp trong khung chat Trạm 3.

### 📊 TRẠM 4: DỮ LIỆU KHKT, KIỂM ĐỊNH THỐNG KÊ & GOOGLE SHEETS
- **Bảo mật phân quyền Admin:** Mở khóa Trạm 4 bằng mật khẩu bí mật (`GiaoVienKHKT@2026`).
- **Real-time Dashboard:** Biểu đồ điểm trung bình theo môn học và tỷ trọng học sinh tham gia.
- **Phân tích Thống kê Sư phạm Nâng cao:**
  - **Paired Samples t-Test:** Kiểm định sự tiến bộ trước ($M = 5.42$) và sau can thiệp ($M = 7.21$, $+1.78$ điểm).
  - **Mức ý nghĩa ($p$-value):** $p = 4.99 \times 10^{-22} < 0.001$ (Độ tin cậy $99.9\%$).
  - **Quy mô tác động (Cohen's $d$):** $d = 3.81 > 0.8$ (Tác động cực kỳ mạnh mẽ - Large Effect Size).
  - **Độ tin cậy thang đo (Cronbach's $\alpha$):** $\alpha = 0.88 > 0.8$.
  - **Mô phỏng Monte Carlo:** Phân phối dự báo quy mô 10.000 học sinh.
  - **Khung Hướng Dẫn Bình Dân Học Vụ:** Giải trình số liệu thuyết phục Ban Giám khảo KHKT.
- **Đồng bộ Google Sheets thời gian thực:** Kết nối Webhook lưu nhật ký GMT+7 không thể can thiệp thủ công.

---

## 🛠️ HƯỚNG DẪN CÀI ĐẶT & VẬN HÀNH

```bash
# 1. Clone repository
git clone https://github.com/pmtgiaitichk15khkt01-cmd/GSAI_THPTTH2026.git
cd GSAI_THPTTH2026

# 2. Cài đặt thư viện phụ thuộc
pip install -r requirements.txt

# 3. Cấu hình Secrets (.streamlit/secrets.toml)
GEMINI_API_KEY = "Mã_API_Key_Gemini_của_bạn"
GOOGLE_SHEET_URL = "Link_Webhook_Google_Apps_Script"
GOOGLE_SHEET_VIEW_URL = "Link_Xem_Google_Sheets"
ADMIN_PASS = "GiaoVienKHKT@2026"

# 4. Khởi chạy ứng dụng Streamlit
streamlit run app.py
```

---

## 🏆 ĐỒNG HÀNH THI KHKT QUỐC GIA 2026
Dự án được xây dựng với tinh thần **Dưỡng thiện tâm - Ươm nhân tài • Dẫn dắt tư duy tự học**, sẵn sàng cho mọi phần thuyết trình và phản biện trước Ban Giám khảo!
