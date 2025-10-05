import sys
from pathlib import Path
from PIL import Image
import pytesseract
import streamlit as st

# ======================
# Configuration & Setup
# ======================
# REQUIRED_COLUMNS are used here for display/guidance only
REQUIRED_COLUMNS = ['Date', 'Amount', 'Description']


# Optional: Set Tesseract path if it's not in your system's PATH (e.g., on Windows)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# ======================
# OCR Function
# ======================

def ocr_from_image(uploaded_file) -> str:
    """
    Performs OCR on the uploaded image file and returns the extracted text.
    """
    if uploaded_file is None:
        return ""

    try:
        # Open the image file using PIL (Pillow)
        img = Image.open(uploaded_file)

        # Use Tesseract to perform OCR
        # --psm 6 is recommended for text in a single uniform block, like a table
        # We assume the image is a bank statement or similar table.
        text = pytesseract.image_to_string(img, lang='eng', config='--psm 6')

        return text.strip()

    except pytesseract.TesseractNotFoundError:
        return (
            "Error: Tesseract is not installed or not in your PATH. "
            "Please install the Tesseract program and ensure it's accessible."
        )
    except Exception as e:
        return f"OCR failed: {e}"


# ======================
# Streamlit App
# ======================

def image_to_csv_app():
    """Main Streamlit app for OCR processing."""
    st.set_page_config(page_title="Image to CSV Converter", layout="centered")
    st.title("📸 Image Statement to CSV Text Converter")
    st.markdown("---")

    st.warning(
        "This tool generates raw text. You must **clean, verify, and format** the output before using it in the main expense tracker app.")
    st.info(f"Required CSV Headers: **{', '.join(REQUIRED_COLUMNS)}**")

    # File Uploader
    uploaded_file = st.file_uploader(
        "Upload Bank Statement Image",
        type=['png', 'jpg', 'jpeg']
    )

    if uploaded_file:
        st.image(uploaded_file, caption='Uploaded Image', use_column_width=True)

        # Process Button
        if st.button("✨ Run OCR and Generate CSV Text", use_container_width=True, type="primary"):
            with st.spinner('Extracting text via Tesseract OCR...'):
                extracted_text = ocr_from_image(uploaded_file)

            if extracted_text.startswith("Error"):
                st.error(extracted_text)
            else:
                st.success("Text extraction complete!")

                st.subheader("Raw CSV Text Output")
                st.caption(
                    "Copy this text, clean up any formatting errors, and ensure the headers (Date, Amount, Description) are correct.")

                # Use st.text_area for easy copying/editing
                st.text_area(
                    "CSV Text Data (Editable)",
                    value=extracted_text,
                    height=300
                )

                # Optional: Provide a download button for the raw text
                st.download_button(
                    label="Download Raw Text as CSV",
                    data=extracted_text.encode('utf-8'),
                    file_name="extracted_statement_raw.csv",
                    mime="text/csv"
                )


if __name__ == "__main__":
    image_to_csv_app()