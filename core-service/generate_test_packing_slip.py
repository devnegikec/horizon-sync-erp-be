"""
Generate a combined PDF packing slip from the TTK Prestige order data.
This PDF can be used for testing the order import → pick list generation flow.

Usage:
    python generate_test_packing_slip.py

Requires:
    pip install fpdf2
"""

from fpdf import FPDF


class PackingSlipPDF(FPDF):
    """Custom PDF with TTK Prestige packing slip formatting."""

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 8, "TTK Prestige Limited", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "Packing Slip / Delivery Challan", align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def add_packing_slip(self, invoice_no, date, dealer, items):
        """Add a packing slip section."""
        self.set_font("Helvetica", "B", 10)
        self.cell(60, 6, f"Invoice No: {invoice_no}")
        self.cell(60, 6, f"Date: {date}", new_x="LMARGIN", new_y="NEXT")
        self.cell(60, 6, f"Dealer: {dealer}", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

        # Table header
        self.set_fill_color(230, 230, 230)
        self.set_font("Helvetica", "B", 8)
        col_widths = [10, 60, 70, 20, 25]
        headers = ["#", "Item Code", "Description", "Qty", "UOM"]
        for i, (header, w) in enumerate(zip(headers, col_widths)):
            self.cell(w, 6, header, border=1, fill=True, align="C")
        self.ln()

        # Table rows
        self.set_font("Helvetica", "", 8)
        for idx, item in enumerate(items, 1):
            self.cell(col_widths[0], 5, str(idx), border=1, align="C")
            self.cell(col_widths[1], 5, item["code"], border=1)
            self.cell(col_widths[2], 5, item["desc"], border=1)
            self.cell(col_widths[3], 5, str(item["qty"]), border=1, align="C")
            self.cell(col_widths[4], 5, item["uom"], border=1, align="C")
            self.ln()

        total = sum(item["qty"] for item in items)
        self.set_font("Helvetica", "B", 8)
        self.cell(140, 6, "Total Items:", border=1, align="R")
        self.cell(20, 6, str(total), border=1, align="C")
        self.cell(25, 6, "Nos", border=1, align="C")
        self.ln(8)


def generate():
    pdf = PackingSlipPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ---- Packing Slip 1: Invoice 5261520051 ----
    pdf.add_packing_slip(
        invoice_no="5261520051",
        date="07.05.2026",
        dealer="SRI ESHWARA ENTERPRISES",
        items=[
            {"code": "SVACHH-SS-POP-2L", "desc": "Svachh SS Popular 2L Pressure Cooker", "qty": 2, "uom": "Nos"},
            {"code": "SVACHH-SS-POP-1.5L", "desc": "Svachh SS Popular 1.5L Pressure Cooker", "qty": 3, "uom": "Nos"},
            {"code": "DLX-ALPHA-SVACHH-5.5L", "desc": "DLX Alpha Svachh 5.5L Pressure Cooker", "qty": 1, "uom": "Nos"},
            {"code": "PRESTIGE-CI-TAWA", "desc": "Prestige Cast Iron Tawa", "qty": 2, "uom": "Nos"},
            {"code": "OMEGA-SLT-PLUS-FP", "desc": "Omega SLT Plus Fry Pan", "qty": 2, "uom": "Nos"},
            {"code": "TRIPLY-TADKA-110", "desc": "Prestige Triply Dia 110mm Tadka Pan", "qty": 3, "uom": "Nos"},
            {"code": "TRIPLY-SPLENDID-32", "desc": "Prestige Triply Splendid 32cm Kadai", "qty": 1, "uom": "Nos"},
            {"code": "VECTRA-GLASTOP-3B", "desc": "Prestige Vectra Glasstop 3 Burner", "qty": 1, "uom": "Nos"},
            {"code": "ENDURA-3J-MIXER", "desc": "Prestige Endura 3 Jar Mixer Grinder", "qty": 1, "uom": "Nos"},
            {"code": "PRISM-PLUS-1000W", "desc": "Prestige Prism Plus 1000W 3 Jar Mixer", "qty": 1, "uom": "Nos"},
        ],
    )

    # ---- Packing Slip 2: Invoice 5261520479 ----
    pdf.add_packing_slip(
        invoice_no="5261520479",
        date="07.05.2026",
        dealer="SRI ESHWARA ENTERPRISES",
        items=[
            {"code": "KETTLE-1.5L-SS", "desc": "Prestige Kettle 1.5L Stainless Steel", "qty": 5, "uom": "Nos"},
            {"code": "PIC-20-IND-1600W", "desc": "Prestige PIC 20 Induction 1600W", "qty": 3, "uom": "Nos"},
            {"code": "PIC-15-PLUS-IND", "desc": "Prestige PIC 15.0 Plus Induction Cooktop", "qty": 4, "uom": "Nos"},
            {"code": "NUTRIFRY-DIGI-4.5L", "desc": "Prestige NutriFry Digital Air Fryer 4.5L", "qty": 2, "uom": "Nos"},
            {"code": "JUDGE-INSTA-AF-4L", "desc": "Judge Insta Air Fryer 4L", "qty": 2, "uom": "Nos"},
            {"code": "ENDURA-1000W-MIX", "desc": "Prestige Endura 1000W Mixer Grinder", "qty": 3, "uom": "Nos"},
        ],
    )

    # ---- Packing Slip 3: Invoice 5261520470 ----
    pdf.add_packing_slip(
        invoice_no="5261520470",
        date="07.05.2026",
        dealer="SRI ESHWARA ENTERPRISES",
        items=[
            {"code": "SVACHH-HA-3.5L-PAN", "desc": "Svachh HA 3.5L Pressure Pan", "qty": 4, "uom": "Nos"},
        ],
    )

    # ---- Packing Slip 4: Shipping Sheet TND2-0002 ----
    pdf.add_packing_slip(
        invoice_no="TND2-0002",
        date="19.05.2026",
        dealer="SRI ESHWARA ENTERPRISES (Shipping)",
        items=[
            {"code": "KETTLE-1.5L-SS", "desc": "Prestige Kettle 1.5L Stainless Steel", "qty": 10, "uom": "Nos"},
            {"code": "PIC-20-IND-1600W", "desc": "Prestige PIC 20 Induction 1600W", "qty": 5, "uom": "Nos"},
            {"code": "PIC-15-PLUS-IND", "desc": "Prestige PIC 15.0 Plus Induction Cooktop", "qty": 2, "uom": "Nos"},
            {"code": "NUTRIFRY-DIGI-4.5L", "desc": "Prestige NutriFry Digital Air Fryer 4.5L", "qty": 3, "uom": "Nos"},
            {"code": "ENDURA-1000W-MIX", "desc": "Prestige Endura 1000W Mixer Grinder", "qty": 2, "uom": "Nos"},
        ],
    )

    output_path = "seed_data/ttk_prestige_packing_slips.pdf"
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")


if __name__ == "__main__":
    generate()
