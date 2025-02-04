import streamlit as st
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import pandas as pd
import tempfile
import shutil
import os
import zipfile
from PyPDF2 import PdfReader, PdfWriter
from difflib import get_close_matches

# ฟังก์ชันสำหรับโหลดฐานข้อมูล CSV ใหม่ทุกครั้ง 
def load_database():
    csv_file = "database.csv"  # ชื่อไฟล์ฐานข้อมูล
    df = pd.read_csv(csv_file, encoding='utf-8')
    df['ชื่อ'] = df['ชื่อ'].str.strip()  # ลบช่องว่างในชื่อ
    return df

# หัวข้อในหน้า Streamlit
st.title("โปรแกรมแปลงชื่อไฟล์หนังสือรับรองหักภาษี ณ ที่จ่าย")
st.write("อัปโหลดไฟล์ PDF หนังสือรับรองหักภาษี ณ ที่จ่าย เพื่อแยกแต่ละหน้าและเปลี่ยนชื่อไฟล์เป็นเลขบัตรประชาชน")

# โหลดฐานข้อมูล
df = load_database()

# ฟังก์ชันสำหรับค้นหาความคล้ายคลึง
def find_id_from_name(text, df):
    matches = get_close_matches(text, df['ชื่อ'], n=1, cutoff=0.6)
    if matches:
        matched_name = matches[0]
        id_card = df.loc[df['ชื่อ'] == matched_name, 'เลขบัตรประชาชน'].values[0]
        return id_card, matched_name
    return None, None

# อัปโหลดไฟล์ PDF
uploaded_file = st.file_uploader("เลือกไฟล์ PDF", type=["pdf"])

# ถ้ามีการอัปโหลดไฟล์
if uploaded_file is not None:
    results = []  # เก็บผลลัพธ์เป็น list
    unmatched_pages = []  # เก็บหน้าที่ไม่พบในฐานข้อมูล
    temp_dir = tempfile.mkdtemp()  # สร้างโฟลเดอร์ชั่วคราวสำหรับไฟล์ที่เปลี่ยนชื่อแล้ว
    zip_filename = "/tmp/converted_pages.zip"  # ชื่อไฟล์ ZIP ที่จะเก็บไฟล์ทั้งหมด

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(uploaded_file.read())
        temp_pdf_path = temp_pdf.name

    reader = PdfReader(temp_pdf_path)

    # ประมวลผลแต่ละหน้า
    for page_number, page in enumerate(reader.pages, start=1):
        # แปลงหน้า PDF เป็นรูปภาพที่ DPI ต่ำสำหรับ OCR
        images = convert_from_path(temp_pdf_path, dpi=100, first_page=page_number, last_page=page_number)
        cropped_image = images[0].crop((45, 225, 200, 250))  # Crop สำหรับ OCR
        text = pytesseract.image_to_string(cropped_image, lang="tha").replace("นาย", "").strip()

        # ค้นหาหมายเลขบัตรประชาชน
        id_card, matched_name = find_id_from_name(text, df)
        if id_card:
            results.append({"หน้า": page_number, "ชื่อ": matched_name, "เลขบัตรประชาชน": str(id_card)})
            new_filename = f"{id_card}.pdf"  # ชื่อไฟล์เป็นหมายเลขบัตรประชาชน
        else:
            unmatched_pages.append(page_number)
            results.append({"หน้า": page_number, "ชื่อ": "ไม่พบข้อมูล", "เลขบัตรประชาชน": "ไม่พบข้อมูล"})
            new_filename = f"unmatched_{page_number}.pdf"

        # บันทึกแต่ละหน้าเป็นไฟล์ PDF แยก
        writer = PdfWriter()
        writer.add_page(page)
        page_pdf_path = os.path.join(temp_dir, new_filename)
        with open(page_pdf_path, "wb") as output_pdf:
            writer.write(output_pdf)

    # สร้างไฟล์ ZIP
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.basename(file))

    # แสดงผลลัพธ์ในตาราง
    results_df = pd.DataFrame(results)
    results_df.index = results_df.index + 1
    st.write("ผลลัพธ์การแปลงข้อมูล:")
    st.dataframe(results_df, use_container_width=True)

    # แสดงหน้าที่ไม่พบข้อมูลในฐานข้อมูล
    if unmatched_pages:
        st.warning("หน้าต่อไปนี้ไม่พบข้อมูลในฐานข้อมูล:")
        st.write(", ".join(map(str, unmatched_pages)))

    # ปุ่มดาวน์โหลดไฟล์ ZIP
    with open(zip_filename, "rb") as f:
        st.download_button(
            label="ดาวน์โหลดไฟล์ PDF ที่เปลี่ยนชื่อทั้งหมด",
            data=f,
            file_name="converted_pages.zip",
            mime="application/zip"
        )

    # ลบไฟล์ชั่วคราวหลังจากดาวน์โหลด
    shutil.rmtree(temp_dir)
    os.remove(zip_filename)
    os.remove(temp_pdf_path)