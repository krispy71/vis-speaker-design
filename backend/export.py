import csv
import io
from models import Session

_PDF_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  body {{ font-family: Georgia, serif; margin: 40px; color: #222; }}
  h1 {{ font-size: 22px; border-bottom: 2px solid #333; padding-bottom: 8px; }}
  h2 {{ font-size: 16px; margin-top: 30px; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 13px; }}
  th {{ background: #333; color: white; padding: 6px 10px; text-align: left; }}
  td {{ padding: 5px 10px; border-bottom: 1px solid #ddd; }}
  .total {{ font-weight: bold; background: #f5f5f5; }}
  .rationale {{ background: #f9f9f9; padding: 15px; border-left: 4px solid #333;
               font-style: italic; margin-top: 10px; }}
  .meta {{ color: #666; font-size: 12px; }}
</style>
</head>
<body>
<h1>Speaker Design: {speaker_type} {enclosure_type}</h1>
<p class="meta">Session ID: {session_id} &nbsp;|&nbsp; Generated: {date}</p>

<h2>Design Summary</h2>
<table>
  <tr><th>Parameter</th><th>Value</th></tr>
  <tr><td>Speaker Type</td><td>{speaker_type}</td></tr>
  <tr><td>Enclosure Type</td><td>{enclosure_type}</td></tr>
  <tr><td>Dimensions (H×W×D mm)</td><td>{dim_h}×{dim_w}×{dim_d}</td></tr>
  <tr><td>Internal Volume</td><td>{volume} L</td></tr>
  <tr><td>Crossover Topology</td><td>{xover_topology}</td></tr>
  <tr><td>Crossover Frequency</td><td>{xover_freq} Hz</td></tr>
</table>

<h2>Bill of Materials</h2>
<table>
  <tr><th>Category</th><th>Part</th><th>Manufacturer</th><th>Model</th>
      <th>Qty</th><th>Unit Price</th><th>Extended</th><th>Source</th></tr>
  {bom_rows}
  <tr class="total"><td colspan="6">Drivers</td><td>${sub_drivers:.2f}</td><td></td></tr>
  <tr class="total"><td colspan="6">Crossover</td><td>${sub_crossover:.2f}</td><td></td></tr>
  <tr class="total"><td colspan="6">Hardware</td><td>${sub_hardware:.2f}</td><td></td></tr>
  <tr class="total"><td colspan="6"><strong>Grand Total</strong></td>
      <td><strong>${grand_total:.2f}</strong></td><td></td></tr>
</table>

<h2>Design Rationale</h2>
<div class="rationale">{rationale}</div>
</body>
</html>"""

_BOM_ROW = (
    "<tr><td>{category}</td><td>{part}</td><td>{manufacturer}</td>"
    "<td>{model}</td><td>{qty}</td><td>${unit_price:.2f}</td>"
    "<td>${extended_price:.2f}</td>"
    "<td>{source}</td></tr>"
)


def generate_pdf(session: Session) -> bytes:
    from weasyprint import HTML
    from datetime import date

    d = session.design_output
    b = session.bom

    bom_rows = "".join(
        _BOM_ROW.format(
            **item.model_dump(),
            source=item.source_url or "—",
        )
        for item in b.items
    )

    html = _PDF_TEMPLATE.format(
        session_id=session.id,
        date=date.today().isoformat(),
        speaker_type=d.speaker_type,
        enclosure_type=d.enclosure_type,
        dim_h=d.enclosure_dimensions_mm.get("h", "?"),
        dim_w=d.enclosure_dimensions_mm.get("w", "?"),
        dim_d=d.enclosure_dimensions_mm.get("d", "?"),
        volume=d.internal_volume_liters,
        xover_topology=d.crossover.topology,
        xover_freq=d.crossover.crossover_freq_hz,
        bom_rows=bom_rows,
        sub_drivers=b.subtotals.get("drivers", 0),
        sub_crossover=b.subtotals.get("crossover", 0),
        sub_hardware=b.subtotals.get("hardware", 0),
        grand_total=b.grand_total,
        rationale=b.rationale,
    )
    return HTML(string=html).write_pdf()


def generate_csv(session: Session) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["category", "part", "manufacturer", "model",
                    "qty", "unit_price", "extended_price", "source_url"],
    )
    writer.writeheader()
    for item in session.bom.items:
        writer.writerow(item.model_dump())
    return output.getvalue()
