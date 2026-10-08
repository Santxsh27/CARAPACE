"""Create a clearly marked artificial PDF bill for live multimodal testing."""
import argparse
from pathlib import Path


def main():
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--amount-minor", type=int, required=True)
    parser.add_argument("--payee", default="fridaydocs@upi")
    args = parser.parse_args()
    if not 0 < args.amount_minor <= 10_000_000:
        parser.error("amount must fit the artificial test provider")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(args.output), pagesize=A4)
    pdf.setTitle("Financial Friday artificial test bill")
    pdf.setFillColor(HexColor("#10233f"))
    pdf.rect(0, 715, 595, 127, fill=1, stroke=0)
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(48, 784, "Friday Test Power")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(48, 750, "ARTIFICIAL BILL - NO REAL UTILITY OR MONEY")
    pdf.setFillColor(HexColor("#10233f"))
    y = 656
    for label, value in (
        ("Bill reference", args.reference),
        ("Provider", "Friday Test Power"),
        ("Amount", f"INR {args.amount_minor // 100}.{args.amount_minor % 100:02d}"),
        ("Payee", args.payee),
        ("Due date", "2026-10-28"),
        ("Payment type", "One-time payment. No subscription or recurring mandate."),
    ):
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(48, y, label)
        pdf.setFont("Helvetica", 12)
        pdf.drawString(48, y - 24, value)
        y -= 76
    pdf.setFont("Helvetica", 10)
    pdf.drawString(48, 108, "Verification fixture only. This document grants no permission to pay.")
    pdf.save()
    print(str(args.output))


if __name__ == "__main__":
    main()
