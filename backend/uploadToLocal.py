import os
import pandas as pd
from reportlab.pdfgen import canvas

STORAGE_DIR = "document_storage"

def init_storage_dir():
    if not os.path.exists(STORAGE_DIR):
        print(f"Creating local storage directory: '{STORAGE_DIR}'...")
        os.makedirs(STORAGE_DIR)

def create_physical_pdf(file_path, title):
    p = canvas.Canvas(file_path)
    p.drawString(100, 750, f"Confidential Document: {title}")
    p.drawString(100, 730, "Authorized Role-Based Access Only (Stored on Local File System).")
    p.showPage()
    p.save()

def generate_local_files():
    init_storage_dir()
    csv_path = os.path.join("data", "documents.csv")
    if not os.path.exists(csv_path):
        csv_path = "documents.csv" 
    df = pd.read_csv(csv_path)
    print(f"Generating {len(df)} PDF files into your '{STORAGE_DIR}' directory...")
    for _, row in df.iterrows():
        doc_id = row['DocumentID']
        title = row['DocumentName']
        file_name = f"{doc_id}.pdf"
        file_path = os.path.join(STORAGE_DIR, file_name)
        create_physical_pdf(file_path, title)
    print("All PDF's are created in the directory.")

generate_local_files()