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

# ฟังก์ชันสำหรับโหลดฐานข้อมูล CSV ใหม่ทุกครั้ง
def load_database():
    csv_file = "database.csv"  # ชื่อไฟล์ฐานข้อมูล
    df = pd.read_csv(csv_file)
    df['ชื่อ'] = df['ชื่อ'].str.strip()  # ลบช่องว่างในชื่อ
    return df

# หัวข้อในหน้า Streamlit
st.title("โปรแกรมแปลงชื่อไฟล์หนังสือรับรองหักภาษี ณ ที่จ่าย")
st.write("อัปโหลดไฟล์ PDF หนังสือรับรองหักภาษี ณ ที่จ่าย เพื่อแปลงชื่อไฟล์ให้เป็นเลขบัตรประชาชน")

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
uploaded_files = st.file_uploader("เลือกไฟล์ PDF", type=["pdf"], accept_multiple_files=True)

# ถ้ามีการอัปโหลดไฟล์
if uploaded_files is not None:
    results = []  # เก็บผลลัพธ์เป็น list
    unmatched_files = []  # เก็บชื่อไฟล์ที่ไม่พบในฐานข้อมูล
    temp_dir = tempfile.mkdtemp()  # สร้างโฟลเดอร์ชั่วคราวสำหรับไฟล์ที่เปลี่ยนชื่อแล้ว
    zip_filename = "/tmp/converted_files.zip"  # ชื่อไฟล์ ZIP ที่จะเก็บไฟล์ทั้งหมด

    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(uploaded_file.read())
            temp_pdf_path = temp_pdf.name

        # แปลง PDF เป็นรูปภาพ
        images = convert_from_path(temp_pdf_path, dpi=300)

        # อ่านข้อความจากทุกหน้า
        all_text_pdf = ""
        for image in images:
            x1, y1, x2, y2 = 132, 670, 550, 750  # พิกัด cropping
            cropped_image = image.crop((x1, y1, x2, y2))
            text = pytesseract.image_to_string(cropped_image, lang="tha")
            text = text.replace("นาย", "").strip()
            all_text_pdf += f"{text}\n"

        # ค้นหาหมายเลขบัตรประชาชน
        id_card, matched_name = find_id_from_name(all_text_pdf, df)
        if id_card and matched_name:
            results.append({"ชื่อ": matched_name, "เลขบัตรประชาชน": str(id_card)})
            new_filename = f"{id_card}.pdf"  # ใช้เลขบัตรประชาชนเป็นชื่อไฟล์
        else:
            unmatched_files.append(uploaded_file.name)  # เพิ่มชื่อไฟล์ที่ไม่พบข้อมูลในฐานข้อมูล
            results.append({"ชื่อ": "ไม่พบข้อมูล", "เลขบัตรประชาชน": "ไม่พบข้อมูล"})
            new_filename = f"{all_text_pdf[:50].replace(' ', '_').replace('\n', '')}.pdf"  # ใช้ข้อความเดิมถ้าไม่พบในฐานข้อมูล

        # คัดลอกไฟล์ PDF เดิมไปยังไฟล์ใหม่
        new_pdf_path = os.path.join(temp_dir, new_filename)
        shutil.copy(temp_pdf_path, new_pdf_path)

        # ลบไฟล์ PDF ชั่วคราว
        os.remove(temp_pdf_path)

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

    # แสดงรายชื่อไฟล์ที่ไม่พบข้อมูลในฐานข้อมูล
    if unmatched_files:
        st.warning("ไฟล์ต่อไปนี้ไม่พบข้อมูลในฐานข้อมูล:")
        for file in unmatched_files:
            st.write(f"- {file}")

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
