"""PDF export utilities for reports and executive summaries."""

from typing import Optional, Dict, Any
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO


class StaxxPDFReport:
    """Generate professional PDF reports for Staxx insights."""

    def __init__(self, title: str, org_name: str):
        """Initialize PDF report generator."""
        self.title = title
        self.org_name = org_name
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Set up custom paragraph styles matching Staxx branding."""
        # Title style
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#0ea5e9"),
                spaceAfter=12,
            )
        )

        # Subtitle style
        self.styles.add(
            ParagraphStyle(
                name="CustomSubtitle",
                parent=self.styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#6b7280"),
                spaceAfter=6,
            )
        )

        # Metric style
        self.styles.add(
            ParagraphStyle(
                name="Metric",
                parent=self.styles["Normal"],
                fontSize=12,
                textColor=colors.HexColor("#111827"),
                spaceAfter=4,
            )
        )

    def generate_executive_summary(
        self,
        current_spend: float,
        projected_savings: float,
        confidence: float,
        top_swaps: list[Dict[str, Any]],
        roi_multiple: float,
        date_range: str = "Last 30 days",
    ) -> BytesIO:
        """Generate an executive summary PDF."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        story = []

        # Header
        story.append(
            Paragraph(f"LLM Cost Optimization Report", self.styles["CustomTitle"])
        )
        story.append(
            Paragraph(f"Organization: {self.org_name}", self.styles["CustomSubtitle"])
        )
        story.append(Paragraph(f"Period: {date_range}", self.styles["CustomSubtitle"]))
        story.append(Spacer(1, 0.3 * inch))

        # Key metrics section
        story.append(Paragraph("Key Metrics", self.styles["Heading2"]))
        metrics_data = [
            ["Metric", "Value"],
            ["Current Monthly Spend", f"${current_spend:,.2f}"],
            ["Projected Savings (12mo)", f"${projected_savings * 12:,.2f}"],
            ["Average Confidence", f"{confidence:.1%}"],
            ["ROI Multiple", f"{roi_multiple:.2f}x"],
        ]

        metrics_table = Table(metrics_data, colWidths=[3 * inch, 2 * inch])
        metrics_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0ea5e9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        story.append(metrics_table)
        story.append(Spacer(1, 0.3 * inch))

        # Top swaps section
        if top_swaps:
            story.append(Paragraph("Recommended Model Swaps", self.styles["Heading2"]))
            swaps_data = [["Task Type", "Current → Recommended", "Monthly Savings", "Confidence"]]

            for swap in top_swaps[:5]:  # Top 5 swaps
                swaps_data.append(
                    [
                        swap.get("task_type", "—"),
                        f"{swap.get('current_model', '—')} → {swap.get('recommended_model', '—')}",
                        f"${swap.get('monthly_savings', 0):,.0f}",
                        f"{swap.get('confidence', 0):.0%}",
                    ]
                )

            swaps_table = Table(swaps_data, colWidths=[1.5 * inch, 2 * inch, 1.5 * inch, 1 * inch])
            swaps_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#22c55e")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 11),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ]
                )
            )

            story.append(swaps_table)
            story.append(Spacer(1, 0.3 * inch))

        # Footer
        story.append(Spacer(1, 0.5 * inch))
        story.append(
            Paragraph(
                f'<i>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} by Staxx Intelligence</i>',
                self.styles["Normal"],
            )
        )

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_cost_analysis(
        self,
        daily_costs: list[Dict[str, Any]],
        cost_by_model: Dict[str, float],
        cost_by_task: Dict[str, float],
    ) -> BytesIO:
        """Generate a detailed cost analysis PDF."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        story = []

        # Header
        story.append(Paragraph("Cost Analysis Report", self.styles["CustomTitle"]))
        story.append(Paragraph(f"Organization: {self.org_name}", self.styles["CustomSubtitle"]))
        story.append(Spacer(1, 0.3 * inch))

        # Cost by model
        story.append(Paragraph("Spend by Model", self.styles["Heading2"]))
        model_data = [["Model", "Monthly Cost", "Percentage"]]
        total_model_cost = sum(cost_by_model.values())

        for model, cost in sorted(cost_by_model.items(), key=lambda x: x[1], reverse=True):
            pct = (cost / total_model_cost * 100) if total_model_cost > 0 else 0
            model_data.append([model, f"${cost:,.2f}", f"{pct:.1f}%"])

        model_table = Table(model_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch])
        model_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ]
            )
        )

        story.append(model_table)
        story.append(Spacer(1, 0.3 * inch))

        # Cost by task type
        story.append(Paragraph("Spend by Task Type", self.styles["Heading2"]))
        task_data = [["Task Type", "Monthly Cost", "Percentage"]]
        total_task_cost = sum(cost_by_task.values())

        for task, cost in sorted(cost_by_task.items(), key=lambda x: x[1], reverse=True):
            pct = (cost / total_task_cost * 100) if total_task_cost > 0 else 0
            task_data.append([task, f"${cost:,.2f}", f"{pct:.1f}%"])

        task_table = Table(task_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch])
        task_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8b5cf6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ]
            )
        )

        story.append(task_table)

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
