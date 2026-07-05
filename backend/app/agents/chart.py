import json
import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from backend.app.agents.base import BaseAgent

logger = logging.getLogger("app.agents.chart")

CHART_SYSTEM_PROMPT = """You are a Data Visualization Specialist Agent.
Your task is to analyze database query records and decide the absolute best chart type (Line, Bar, Pie, Trend, or KPI Card) and configuration to display the insights.
"""

class ChartAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Chart_Agent",
            system_prompt=CHART_SYSTEM_PROMPT
        )

    def generate_chart(self, records: list[dict], session_id: str = "default_session") -> dict:
        """Analyze query records and generate a styled Plotly figure representation."""
        logger.info(f"Generating chart config for {len(records)} records.")
        
        if not records:
            return {
                "chart_type": "None",
                "fig_json": "{}",
                "image_base64": ""
            }

        df = pd.DataFrame(records)
        
        # 1. Infer columns
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        datetime_cols = []
        for col in df.columns:
            # Check if name contains date/time or looks like a string date
            if "date" in col.lower() or "month" in col.lower() or "year" in col.lower():
                datetime_cols.append(col)
                
        object_cols = df.select_dtypes(include=["object"]).columns.tolist()
        # Remove date cols from object cols
        object_cols = [c for c in object_cols if c not in datetime_cols]

        chart_type = "Bar"
        fig = None

        # Style preferences: Dark themed, harmonious palettes
        layout_theme = {
            "template": "plotly_dark",
            "paper_bgcolor": "rgba(22, 28, 45, 0.95)",
            "plot_bgcolor": "rgba(22, 28, 45, 0.95)",
            "font": {"family": "Outfit, Inter, sans-serif", "color": "#E2E8F0"},
            "title": {"font": {"size": 18, "color": "#FFFFFF"}},
            "margin": {"l": 40, "r": 40, "t": 60, "b": 40}
        }
        color_palette = ["#6366F1", "#8B5CF6", "#EC4899", "#10B981", "#F59E0B", "#EF4444"]

        # 2. Heuristic selection
        if len(df) == 1 and numeric_cols:
            # Single value KPI Card
            chart_type = "KPI Card"
            val_col = numeric_cols[0]
            val = df[val_col].iloc[0]
            
            # Format value
            if "revenue" in val_col.lower() or "amount" in val_col.lower() or "sales" in val_col.lower():
                val_str = f"${val:,.2f}"
            else:
                val_str = f"{val:,}" if isinstance(val, (int, float)) else str(val)

            fig = go.Figure()
            fig.add_trace(go.Indicator(
                mode="number",
                value=val,
                number={"prefix": "$", "valueformat": ",.2f"} if "revenue" in val_col.lower() else {"valueformat": ","},
                title={"text": val_col.replace("_", " ").title(), "font": {"size": 16, "color": "#94A3B8"}},
                domain={'x': [0, 1], 'y': [0, 1]}
            ))
            fig.update_layout(
                **layout_theme,
                height=250
            )

        elif datetime_cols and numeric_cols:
            # Line Chart / Trend Chart
            chart_type = "Line"
            x_col = datetime_cols[0]
            y_col = numeric_cols[0]
            
            # Sort by date
            df = df.sort_values(by=x_col)
            
            fig = px.line(
                df, x=x_col, y=y_col,
                title=f"{y_col.replace('_', ' ').title()} Over Time",
                color_discrete_sequence=[color_palette[0]]
            )
            fig.update_layout(**layout_theme)
            fig.update_traces(line=dict(width=3))

        elif object_cols and numeric_cols:
            # Bar Chart or Pie Chart
            x_col = object_cols[0]
            y_col = numeric_cols[0]
            
            if len(df) <= 5:
                chart_type = "Pie"
                fig = px.pie(
                    df, names=x_col, values=y_col,
                    title=f"Distribution of {y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
                    color_discrete_sequence=color_palette
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(**layout_theme)
            else:
                chart_type = "Bar"
                fig = px.bar(
                    df, x=x_col, y=y_col,
                    title=f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
                    color_discrete_sequence=[color_palette[1]]
                )
                fig.update_layout(**layout_theme)
        else:
            # Fallback to tabular/simple Bar
            chart_type = "Bar"
            if len(df.columns) >= 2:
                x_col = df.columns[0]
                y_col = numeric_cols[0] if numeric_cols else df.columns[1]
                fig = px.bar(df, x=x_col, y=y_col, title="Query Visualizer", color_discrete_sequence=[color_palette[2]])
                fig.update_layout(**layout_theme)
            else:
                chart_type = "KPI Card"
                fig = go.Figure()
                fig.update_layout(**layout_theme)

        # 3. Export JSON and Mock static SVG image (to avoid Kaleido system locks)
        fig_json = fig.to_json() if fig else "{}"
        
        # Simple SVG representation for Base64 image export
        svg_mock = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
            <rect width="100%" height="100%" fill="#161C2D"/>
            <text x="50%" y="50%" fill="#E2E8F0" font-family="Outfit, sans-serif" font-size="20" text-anchor="middle">
                {chart_type} Chart: Generated {len(df)} datapoints
            </text>
        </svg>"""
        import base64
        svg_base64 = base64.b64encode(svg_mock.encode('utf-8')).decode('utf-8')
        image_base64 = f"data:image/svg+xml;base64,{svg_base64}"

        return {
            "chart_type": chart_type,
            "fig_json": fig_json,
            "image_base64": image_base64
        }
