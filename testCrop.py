import streamlit as st
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
import tempfile
import shutil
import os
import zipfile
from difflib import get_close_matches

# ระบุ path ของ tesseract หากจำเป็น (สำหรับ Windows เท่านั้น)
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# หัวข้อในหน้า Streamlit
st.title("โปรแกรมแปลงชื่อไฟล์หนังสือรับรองหักภาษี ณ ที่จ่าย")
st.write("อัปโหลดไฟล์ PDF เพื่อแปลงข้อความและเปลี่ยนชื่อไฟล์ตามฐานข้อมูล")

# โหลดฐานข้อมูลจากไฟล์ CSV
csv_file = "database.csv"  # ชื่อไฟล์ฐานข้อมูล
df = pd.read_csv(csv_file)  # อ่านไฟล์ CSV
df['ชื่อ'] = df['ชื่อ'].str.strip()  # ลบช่องว่างในชื่อ

# ฟังก์ชันสำหรับค้นหาความคล้ายคลึง
def find_id_from_name(text, df):
    matches = get_close_matches(text, df['ชื่อ'], n=1, cutoff=0.6)  # เปลี่ยน cutoff ตามความเหมาะสม
    if matches:
        matched_name = matches[0]
        id_card = df.loc[df['ชื่อ'] == matched_name, 'เลขบัตรประชาชน'].values[0]
        return id_card
    return None

# อัปโหลดไฟล์หลายไฟล์
uploaded_files = st.file_uploader("เลือกไฟล์ PDF", type=["pdf"], accept_multiple_files=True)

# ถ้ามีการอัปโหลดไฟล์
if uploaded_files is not None:
    temp_dir = tempfile.mkdtemp()  # สร้างโฟลเดอร์ชั่วคราวสำหรับไฟล์ที่เปลี่ยนชื่อแล้ว
    zip_filename = "/tmp/converted_files.zip"  # ชื่อไฟล์ ZIP ที่จะเก็บไฟล์ทั้งหมด

    # ลูปผ่านไฟล์ที่อัปโหลด
    for uploaded_file in uploaded_files:
        file_type = uploaded_file.type

        if file_type == "application/pdf":
            # ประมวลผลไฟล์ PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                temp_pdf.write(uploaded_file.read())
                temp_pdf_path = temp_pdf.name

            # แปลง PDF เป็นรูปภาพ
            images = convert_from_path(temp_pdf_path, dpi=100)
            st.write(f"พบ {len(images)} หน้าในไฟล์ PDF")

            # แสดงภาพจาก PDF และแปลงข้อความ
            all_text_pdf = ""
            for i, image in enumerate(images):
                st.image(image, caption=f"หน้า {i + 1} จากไฟล์ {uploaded_file.name}", use_container_width=True)
                st.write(f"กำลังประมวลผลหน้า {i + 1}...")

                # ตัวอย่างการ crop ภาพตามแกน x และ y: (x1, y1, x2, y2)
                x1, y1, x2, y2 = 45, 225, 200, 250  # กำหนดพิกัดตามต้องการ

                # Crop ภาพ
                cropped_image = image.crop((x1, y1, x2, y2))

                # แสดงผลภาพที่ crop ออกมา
                st.image(cropped_image, caption=f"ภาพที่ถูก crop จากหน้า {i + 1}", use_container_width=True)

                # ใช้ Tesseract OCR แปลงข้อความจากภาพที่ถูก crop
                text = pytesseract.image_to_string(cropped_image, lang="tha")  # เปลี่ยน "tha" ตามภาษาที่ต้องการ

                # แสดงผลข้อความที่ OCR ได้
                st.write(f"ข้อความที่ได้จากหน้า {i + 1}:")
                st.code(text, language="text")

                # ตัดคำ "นาย" ออกจากข้อความที่แปลงมา
                text = text.replace("นาย", "").strip()

                all_text_pdf += f"{text}\n"

            # เปรียบเทียบข้อความและใช้หมายเลขบัตรประชาชนเป็นชื่อไฟล์
            new_id = find_id_from_name(all_text_pdf, df)
            if new_id:
                new_filename = f"{new_id}.pdf"  # ใช้เลขบัตรประชาชนเป็นชื่อไฟล์
            else:
                new_filename = f"{all_text_pdf[:50].replace(' ', '_').replace('\n', '')}.pdf"  # ใช้ข้อความเดิมถ้าไม่พบในฐานข้อมูล
            new_pdf_path = os.path.join(temp_dir, new_filename)

            # คัดลอกไฟล์ PDF เดิมไปยังไฟล์ใหม่
            shutil.copy(temp_pdf_path, new_pdf_path)

    # สร้างไฟล์ ZIP
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.basename(file))

    # ปุ่มดาวน์โหลดไฟล์ ZIP
    with open(zip_filename, "rb") as f:
        st.download_button(
            label="ดาวน์โหลดไฟล์ PDF ที่เปลี่ยนชื่อทั้งหมด",
            data=f,
            file_name="converted_files.zip",
            mime="application/zip"
        )

    # ลบไฟล์ชั่วคราวหลังจากดาวน์โหลด
    shutil.rmtree(temp_dir)
    os.remove(zip_filename)
