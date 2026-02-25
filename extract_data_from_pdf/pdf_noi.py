from pypdf import PdfReader, PdfWriter
import os

pdf_folder = "pdfs"        # thư mục chứa các file PDF
output_file = "merged.pdf"

writer = PdfWriter()

pdf_files = sorted([
    f for f in os.listdir(pdf_folder)
    if f.lower().endswith(".pdf")
])

for pdf in pdf_files:
    reader = PdfReader(os.path.join(pdf_folder, pdf))
    for page in reader.pages:
        writer.add_page(page)

with open(output_file, "wb") as f:
    writer.write(f)

print("Đã nối xong:", output_file)
