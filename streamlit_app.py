import plotly.graph_objects as go
import requests
import streamlit as st

from core.calculations import GridSummary
from core.config import load_config
from core.summary import load_summary

LABELS = {"green": "Green", "neutral": "Neutral", "not_green": "Not green"}
COLOURS = {"green": "#2e7d32", "neutral": "#9e9e9e", "not_green": "#c62828"}


def render_verdict(summary: GridSummary) -> None:
    """Show the headline advice as a coloured banner."""
    if summary.above_baseline:
        st.error("**Try to reduce or delay your energy use**\n\nFossil fuel use is higher than normal right now.")
    else:
        st.success("**Good time to use energy**\n\nFossil fuel use is at or below normal right now.")


def render_donut(summary: GridSummary) -> None:
    """Draw the green / neutral / not green mix with the green % in the centre."""
    donut = go.Pie(
        labels=[LABELS[rating] for rating in summary.percentages],
        values=list(summary.percentages.values()),
        marker_colors=[COLOURS[rating] for rating in summary.percentages],
        hole=0.65, sort=False, textinfo="none", hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
    )
    figure = go.Figure(donut).update_layout(
        title="How green is the grid right now?", height=300, margin={"t": 40, "b": 0, "l": 0, "r": 0},
        legend={"orientation": "h", "y": -0.05},
        annotations=[{"text": f"{summary.percentages['green']:.1f}%<br>green", "showarrow": False, "font_size": 24}],
    )
    st.plotly_chart(figure)


def render_fossil_scale(summary: GridSummary) -> None:
    """Show where the Not green % sits on a below/above-normal scale."""
    now, baseline = summary.percentages["not_green"], summary.baseline_percent
    top = max(60, now + 5, baseline + 10)  # room for the marker and both zones
    figure = go.Figure(go.Scatter(
        x=[now], y=[1.2], mode="markers+text", text=[f"Now: {now:.1f}%"], textposition="top center",
        marker={"symbol": "triangle-down", "size": 18, "color": "black"}, hoverinfo="skip",
    ))
    for x0, x1, colour, label in [(0, baseline, "#c8e6c9", "Lower than normal"),
                                  (baseline, top, "#ffcdd2", "Higher than normal")]:
        figure.add_shape(type="rect", x0=x0, x1=x1, y0=0, y1=1, fillcolor=colour, line_width=0)
        figure.add_annotation(x=(x0 + x1) / 2, y=0.5, text=label, showarrow=False)
    figure.add_shape(type="line", x0=baseline, x1=baseline, y0=-0.1, y1=1.1, line={"dash": "dash"})
    figure.add_annotation(x=baseline, y=-0.35, text=f"normal {baseline:.0f}%", showarrow=False)
    figure.update_layout(
        title="Fossil fuels right now", height=220, showlegend=False,
        margin={"t": 40, "b": 10, "l": 10, "r": 10},
        xaxis={"range": [0, top], "ticksuffix": "%", "showgrid": False},
        yaxis={"range": [-0.6, 1.9], "visible": False},
    )
    st.plotly_chart(figure)


@st.cache_data(ttl=300, show_spinner="Fetching grid data...")
def get_summary() -> GridSummary | None:
    """Load the summary, cached for 5 minutes (failures aren't cached, so they retry)."""
    return load_summary(load_config())


def main() -> None:
    """Load config and data, summarise them, and render the widget."""
    st.set_page_config(page_title="Grid greenness")
    try:
        summary = get_summary()
    except (requests.RequestException, OSError, ValueError, KeyError):
        st.error("Grid data is unavailable right now. Please try again later.")
        return
    if summary is None:
        st.info("No data available.")
        return
    st.caption(f"Latest data: {summary.period_label}")
    render_verdict(summary)
    donut_column, scale_column = st.columns(2, vertical_alignment="center")
    with donut_column:
        render_donut(summary)
    with scale_column:
        render_fossil_scale(summary)


main()
