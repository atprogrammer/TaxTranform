import streamlit as st
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import tempfile

# ระบุ path ของ tesseract หากจำเป็น (สำหรับ Windows เท่านั้น)
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# หัวข้อในหน้า Streamlit
st.title("ทดสอบโปรแกรมแปลงข้อความจากภาพและ PDF ด้วย OCR")
st.write("อัปโหลดไฟล์รูปภาพหรือ PDF เพื่อแปลงข้อความ")

# อัปโหลดไฟล์
uploaded_file = st.file_uploader("เลือกไฟล์รูปภาพหรือ PDF", type=["png", "jpg", "jpeg", "pdf"])

if uploaded_file is not None:
    file_type = uploaded_file.type

    if file_type == "application/pdf":
        # ประมวลผลไฟล์ PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(uploaded_file.read())
            temp_pdf_path = temp_pdf.name

        # แปลง PDF เป็นรูปภาพ
        images = convert_from_path(temp_pdf_path, dpi=300)
        st.write(f"พบ {len(images)} หน้าในไฟล์ PDF")

        # แสดงภาพจาก PDF และแปลงข้อความ
        all_text = ""
        for i, image in enumerate(images):
            st.image(image, caption=f"หน้า {i + 1}", use_container_width=True)
            st.write(f"กำลังประมวลผลหน้า {i + 1}...")
            text = pytesseract.image_to_string(image, lang="tha")  # เปลี่ยน "tha" ตามภาษาที่ต้องการ
            all_text += f"\n--- หน้า {i + 1} ---\n{text}"

        st.subheader("ข้อความที่แปลงได้จาก PDF:")
        st.text_area("ผลลัพธ์", all_text, height=400)

    else:
        # ประมวลผลไฟล์รูปภาพ
        image = Image.open(uploaded_file)
        st.image(image, caption="รูปภาพที่อัปโหลด", use_container_width=True)

        # ปุ่มสำหรับเริ่ม OCR
        if st.button("เริ่มการแปลงข้อความ"):
            st.write("กำลังประมวลผล...")
            text = pytesseract.image_to_string(image, lang="tha")  # เปลี่ยน "tha" เป็นภาษาอื่นหากต้องการ
            st.subheader("ข้อความที่แปลงได้:")
            st.text_area("ผลลัพธ์", text, height=200)

# หมายเหตุ:
# 1. หากไม่มีภาษาไทยใน Tesseract OCR ให้ติดตั้งด้วยคำสั่ง:
#    sudo apt install tesseract-ocr-tha
# 2. ติดตั้ง pdf2image และ Pillow ด้วยคำสั่ง:
#    pip install pdf2image pillow
# 3. สำหรับระบบ Windows อาจต้องติดตั้ง Poppler และระบุ path ด้วย:
#    - ดาวน์โหลด Poppler: https://github.com/oschwartz10612/poppler-windows/releases/
#    - เพิ่ม path ของ `poppler/bin` ลงใน environment variables
