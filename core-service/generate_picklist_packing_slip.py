"""Generate a packing-slip PDF in the incoming-order format for testing pick-list import.

Mimics the real TTK Prestige packing slip with the extended columns:
    SL | PARTICULARS | UOM | INV QTY | PER CASE QTY | NO OF CASES | CASE QTY
       | LOOSE QTY | LOOSE BOXES | BATCH NUMBER

Rendered as a real columned table (landscape A4) so the columns are visually
separated, while keeping the UOM + numeric columns on one line so the importer
still parses them correctly.

Uses existing item SKUs (PPI-SKO-89, PPI-SKO-90) so the import resolves them
against the item master. Values exercise per-case / cases / loose combinations:

    PPI-SKO-89 : 12 pcs = 3 cases x 4  (case-only pick, 0 loose)
    PPI-SKO-90 : 10 pcs = 1 case  x 6  + 4 loose (case + loose coexist)

Usage:
    python generate_picklist_packing_slip.py
Output:
    seed_data/picklist_packing_slip_test.pdf
"""

import os

from fpdf import FPDF

OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "seed_data", "picklist_packing_slip_test_columned.pdf"
)

# Column definitions: (header label, width in mm). Order matters for parsing.
COLS = [
    ("SL", 9),
    ("PARTICULARS", 90),
    ("UOM", 15),
    ("INV QTY", 19),
    ("PER CASE QTY", 22),
    ("NO OF CASES", 22),
    ("CASE QTY", 18),
    ("LOOSE QTY", 18),
    ("LOOSE BOXES", 22),
    ("BATCH NUMBER", 32),
]


class PackingSlipPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(
            0, 8, "TTK PRESTIGE LIMITED", align="C", new_x="LMARGIN", new_y="NEXT"
        )
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 6, "PACKING SLIP", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "Doc.Number : TEST-PICK-0001", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, "Doc.Date   : 18.08.2026", new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, "Invoice Nos : INV-PICK-0001", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.cell(
            0,
            5,
            "Dealer : 1000040082 - SRI ESHWARA ENTERPRISES, BENGALURU",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.ln(3)

    def _row(self, cells, bold=False):
        """Draw one table row with per-column borders and separators."""
        line_h = 4.5
        self.set_font("Helvetica", "B" if bold else "", 7)
        widths = [w for _, w in COLS]

        # Height required by the (possibly wrapping) particulars column.
        split = self.multi_cell(
            widths[1], line_h, cells[1], dry_run=True, output="LINES"
        )
        row_h = max(line_h, line_h * len(split))

        x = self.l_margin
        y = self.get_y()
        if y + row_h > self.page_break_trigger:
            self.add_page()
            y = self.get_y()

        # SL
        self.set_xy(x, y)
        self.cell(widths[0], row_h, cells[0], border=1, align="C")
        # PARTICULARS (may wrap)
        self.set_xy(x + widths[0], y)
        self.multi_cell(widths[1], line_h, cells[1], border=1, align="L")
        # UOM + numeric columns (drawn at the row's top baseline)
        xx = x + widths[0] + widths[1]
        for i in range(2, len(cells)):
            self.set_xy(xx, y)
            align = "R" if i >= 3 else "C"
            self.cell(widths[i], row_h, cells[i], border=1, align=align)
            xx += widths[i]
        self.set_y(y + row_h)


def generate():
    pdf = PackingSlipPDF(orientation="L", format="A4")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()

    pdf._row([name for name, _ in COLS], bold=True)

    pdf._row(
        [
            "1",
            "(PPI-SKO-89) Prestige Digi Kettle 2.0 Litre with 6 Preset Modes",
            "NOS",
            "12",
            "4",
            "3",
            "12",
            "0",
            "0",
            "BATCH-K89-001",
        ]
    )

    pdf._row(
        [
            "2",
            "(PPI-SKO-90) Prestige Deluxe Plus Aluminium Outer Lid Pressure Pan, Silver",
            "NOS",
            "10",
            "6",
            "1",
            "6",
            "4",
            "1",
            "BATCH-P90-002",
        ]
    )

    pdf._row(["", "GRAND TOTAL", "", "22", "", "4", "7", "4", "", ""], bold=True)

    pdf.ln(6)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(
        0,
        5,
        "Before taking delivery of the consignment from the carrier, Please "
        "ensure that the packages are intact. In case of discrepancy, Please "
        "revert to us along with this packing slip.",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    pdf.output(OUTPUT_PATH)
    print(f"PDF generated: {OUTPUT_PATH}")


if __name__ == "__main__":
    generate()
