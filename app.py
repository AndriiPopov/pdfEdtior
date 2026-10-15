import fitz  # PyMuPDF
import streamlit as st

st.set_page_config(page_title="Black Earth - Proposal Generator", page_icon="🌱", layout="wide")

st.title("🌱 Black Earth Proposal & Pricing Generator")
st.markdown("Upload the master PDF, select the product rows to keep, and download a pixel-perfect customized proposal.")

MASTER_FILE = "2026–27 Canadian Manufacturer -Multi Pick up Version _1014-full.pdf"

# Exact product codes found on the last page (Page 12) of your PDF
PRODUCT_ROWS = [
    # Note: the codes use the digit zero ("AG0"), not the letter O
    {"id": 0, "name": "GRANULAR — Humalite AG4 (25 KG / 55 LB)", "code": "AG0-B00025-000"},
    {"id": 1, "name": "GRANULAR — Humalite AG4 (907 KG / 2000 LB)", "code": "AG0-TL0907-000"},
    {"id": 2, "name": "GRANULAR — Humalite GG16 (25 KG / 55 LB)", "code": "GG0-B00025-000"},
    {"id": 3, "name": "GRANULAR — Humalite GG16 (907 KG / 2000 LB)", "code": "GG0-TL0907-000"},
    {"id": 4, "name": "POWDER — Humalite MP30 (907 KG / 2000 LB)", "code": "MP0-TL0907-000"},
    {"id": 5, "name": "POWDER — Humalite MP30 (25 KG / 55 LB)", "code": "MP0-B00025-000"},
    {"id": 6, "name": "POWDER — Humalite XP100 (907 KG / 2000 LB)", "code": "XP0-TL0907-000"},
    {"id": 7, "name": "POWDER — Humalite XP100 (25 KG / 55 LB)", "code": "XP0-B00025-000"},
]

uploaded_file = st.file_uploader("Upload Master Proposal PDF", type=["pdf"])

pdf_bytes = None
if uploaded_file is not None:
    pdf_bytes = uploaded_file.read()
else:
    try:
        with open(MASTER_FILE, "rb") as f:
            pdf_bytes = f.read()
    except FileNotFoundError:
        pdf_bytes = None

if pdf_bytes:
    st.subheader("1. Client Name")
    client_name = st.text_input("Client / Company Name", placeholder="e.g., Acme Agriculture Ltd.")

    st.subheader("2. Select Products to Include")
    st.markdown("Uncheck any rows you want to **remove** from the pricing table:")

    selected_indices = []
    for item in PRODUCT_ROWS:
        is_checked = st.checkbox(f"**{item['name']}** (`{item['code']}`)", value=True, key=f"row_{item['id']}")
        if is_checked:
            selected_indices.append(item["id"])

    def create_masked_pdf(input_pdf_bytes, keep_indices):
        src = fitz.open(stream=input_pdf_bytes, filetype="pdf")

        # Target the very last page (Page 12, Index 11) where the pricing table lives
        last = len(src) - 1
        page = src[last]
        width, height = page.rect.width, page.rect.height

        # Locate each row by its product code; fail loudly instead of silently skipping
        centers = {}
        for item in PRODUCT_ROWS:
            rects = page.search_for(item["code"])
            if not rects:
                raise ValueError(f"Product code {item['code']} not found on the pricing page")
            centers[item["id"]] = (rects[0].y0 + rects[0].y1) / 2

        # Rows are evenly spaced, so each row's band is its center +/- half the row pitch
        ordered = sorted(centers, key=centers.get)
        pitch = (centers[ordered[-1]] - centers[ordered[0]]) / (len(ordered) - 1)
        bands = {i: (centers[i] - pitch / 2, centers[i] + pitch / 2) for i in ordered}
        table_top, table_bottom = bands[ordered[0]][0], bands[ordered[-1]][1]

        # Delete the text of removed rows so their prices are not left in the file
        for i in ordered:
            if i not in keep_indices:
                y0, y1 = bands[i]
                page.add_redact_annot(fitz.Rect(0, y0 + 2, width, y1 - 2))
        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)

        # Rebuild the pricing page: header, then kept rows stacked with no gaps, then footer
        out = fitz.open()
        out.insert_pdf(src, to_page=last - 1)
        new_page = out.new_page(width=width, height=height)

        def copy_strip(y0, y1, dest_y):
            new_page.show_pdf_page(fitz.Rect(0, dest_y, width, dest_y + y1 - y0), src, last,
                                   clip=fitz.Rect(0, y0, width, y1))

        copy_strip(0, table_top, 0)
        y = table_top
        for i in ordered:
            if i in keep_indices:
                copy_strip(*bands[i], y)
                y += pitch
        # Start a little below the table so its original bottom border isn't copied
        copy_strip(table_bottom + 3, height, table_bottom + 3)

        output_bytes = out.write(garbage=3, deflate=True)
        out.close()
        src.close()
        return output_bytes

    st.markdown("---")
    if st.button("Generate Clean Proposal PDF", type="primary", use_container_width=True):
        if not selected_indices:
            st.error("Please keep at least one product row selected.")
        else:
            try:
                final_pdf = create_masked_pdf(pdf_bytes, selected_indices)
                filename = f"Black_Earth_Proposal_{client_name.replace(' ', '_') if client_name else 'Client'}.pdf"
                
                st.success("Custom PDF generated successfully!")
                st.download_button(
                    label="📥 Download Customized PDF",
                    data=final_pdf,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error generating PDF: {e}")
else:
    st.info("Please place your master PDF in the directory or upload it above.")