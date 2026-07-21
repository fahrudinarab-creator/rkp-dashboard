import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Laporan Monitoring RKP", page_icon="🌴", layout="wide")

# ---------------------------------------------------------
# FORMATTER
# ---------------------------------------------------------

def rupiah_singkat(x):
    if abs(x) >= 1_000_000_000:
        val = f"{x/1_000_000_000:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"Rp {val} M"
    val = f"{x/1_000_000:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Rp {val} jt"

def rupiah(x):
    return f"Rp {x:,.0f}".replace(",", ".")

def angka(x):
    return f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ---------------------------------------------------------
# PALET WARNA
# ---------------------------------------------------------
C_BG = "#0b0e14"
C_CARD = "#141924"
C_BORDER = "#242b3d"
C_TEXT = "#e8eaed"
C_MUTED = "#9aa4b2"
C_ACCENT = "#6366f1"
C_ACCENT2 = "#14b8a6"
C_WARN = "#f59e0b"
C_DANGER = "#ef4444"
C_OK = "#22c55e"

# ---------------------------------------------------------
# CSS
# ---------------------------------------------------------
st.markdown(f"""
<style>
    .stApp {{ background-color: {C_BG}; }}
    html, body, [class*="css"] {{ font-family: 'Inter', 'Segoe UI', sans-serif; }}

    /* Header banner */
    .rkp-header {{
        padding: 22px 28px;
        border-radius: 14px;
        background: linear-gradient(135deg, {C_ACCENT}22 0%, {C_ACCENT2}11 100%);
        border: 1px solid {C_BORDER};
        margin-bottom: 22px;
    }}
    .rkp-header h1 {{
        margin: 0; font-size: 26px; color: {C_TEXT}; font-weight: 700;
    }}
    .rkp-header p {{
        margin: 4px 0 0 0; color: {C_MUTED}; font-size: 14px;
    }}

    /* Section title */
    .rkp-section-title {{
        display: flex; align-items: center; gap: 8px;
        font-size: 16px; font-weight: 700; color: {C_TEXT};
        margin-bottom: 14px; padding-bottom: 8px;
        border-bottom: 2px solid {C_ACCENT}55;
    }}

    /* Card container (via st.container border) */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 14px !important;
        border: 1px solid {C_BORDER} !important;
        background-color: {C_CARD} !important;
    }}

    /* Metric cards */
    div[data-testid="stMetric"] {{
        background-color: {C_CARD};
        border-radius: 10px;
        padding: 14px 16px;
        border: 1px solid {C_BORDER};
    }}
    div[data-testid="stMetricLabel"] {{ color: {C_MUTED}; font-size: 12.5px; }}
    div[data-testid="stMetricValue"] {{ color: {C_TEXT}; font-size: 20px; }}

    /* Dataframe */
    div[data-testid="stDataFrame"] {{ border-radius: 10px; overflow: hidden; }}

    h1, h2, h3 {{ color: {C_TEXT}; }}
    hr {{ border-color: {C_BORDER}; }}

    .insight-box {{
        background-color: {C_CARD};
        border: 1px solid {C_BORDER};
        border-radius: 12px;
        padding: 16px 20px;
    }}
    .insight-item {{
        padding: 8px 0;
        border-bottom: 1px solid {C_BORDER}88;
        font-size: 14.5px; color: {C_TEXT};
    }}
    .insight-item:last-child {{ border-bottom: none; }}
    .insight-sub {{
        padding: 4px 0 4px 22px;
        font-size: 13.5px; color: {C_MUTED};
    }}
    .donut-label {{
        text-align: center; color: {C_MUTED}; font-size: 13px;
        margin-top: -8px; font-weight: 600; letter-spacing: 0.3px;
    }}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data(file, sheet_name="Rekap RKP"):
    df = pd.read_excel(file, sheet_name=sheet_name)
    num_cols = [
        "Target Rp/Ha", "Realisasi Rp/Ha", "Target Ha", "Target Biaya",
        "Realisasi Ha", "Realisasi Biaya", "Selisih Ha", "Selisih Biaya",
        "% Realisasi", "% Sisa",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def pct(numerator, denominator):
    return (numerator / denominator * 100) if denominator else 0.0


def donut(value_pct, color):
    value_pct = max(0, min(100, value_pct))
    fig = go.Figure(data=[go.Pie(
        values=[value_pct, 100 - value_pct],
        hole=0.74,
        marker_colors=[color, C_BORDER],
        textinfo="none",
        sort=False,
        direction="clockwise",
    )])
    fig.update_layout(
        showlegend=False,
        annotations=[dict(text=f"{value_pct:.1f}%", x=0.5, y=0.5, font_size=26,
                           showarrow=False, font_color=C_TEXT, font_family="Inter")],
        margin=dict(t=6, b=6, l=6, r=6),
        paper_bgcolor="rgba(0,0,0,0)",
        height=190,
    )
    return fig


def style_plotly(fig, title=None):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=C_TEXT, size=12.5),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=""),
        margin=dict(t=40 if title else 20, b=20, l=10, r=10),
        title=dict(text=title, font=dict(size=13, color=C_MUTED)) if title else None,
        xaxis=dict(gridcolor=C_BORDER, showgrid=False),
        yaxis=dict(gridcolor=C_BORDER, showgrid=True, zeroline=False),
        bargap=0.3,
    )
    return fig


def generate_insights(df, proyek_name):
    insights = []
    total_target_biaya = df["Target Biaya"].sum()
    total_realisasi_biaya = df["Realisasi Biaya"].sum()
    total_target_ha = df["Target Ha"].sum() if "Target Ha" in df.columns else 0
    total_realisasi_ha = df["Realisasi Ha"].sum() if "Realisasi Ha" in df.columns else 0

    capaian_biaya = pct(total_realisasi_biaya, total_target_biaya)
    capaian_fisik = pct(total_realisasi_ha, total_target_ha)

    main_points = []
    sub_points = []

    if total_realisasi_biaya == 0 and total_realisasi_ha == 0:
        main_points.append(("ℹ️", f"Untuk <b>{proyek_name}</b>, kolom Realisasi Biaya & Realisasi Fisik masih "
                                   "kosong (0). Begitu diisi di Excel dan file di-upload ulang, analisa "
                                   "<i>over budget</i> di bawah akan otomatis muncul."))
    else:
        main_points.append(("📊", f"<b>{proyek_name}</b>: capaian biaya <b>{capaian_biaya:.1f}%</b>, "
                                   f"capaian fisik <b>{capaian_fisik:.1f}%</b>."))
        if capaian_fisik > 0 and capaian_biaya > capaian_fisik + 10:
            main_points.append(("⚠️", "Penyerapan biaya lebih cepat dari progres fisik di lapangan — perlu dicek."))
        elif capaian_biaya > 0 and capaian_fisik > capaian_biaya + 10:
            main_points.append(("✅", "Progres fisik lebih cepat dari penyerapan biaya — efisiensi cukup baik."))

    over = df[(df["Realisasi Biaya"] > df["Target Biaya"]) & (df["Target Biaya"] > 0)].copy()
    if not over.empty:
        over["Selisih (%)"] = (over["Realisasi Biaya"] - over["Target Biaya"]) / over["Target Biaya"] * 100
        worst = over.sort_values("Selisih (%)", ascending=False).head(5)
        main_points.append(("🔴", f"Ditemukan <b>{len(over)} item</b> dengan biaya melebihi target:"))
        for _, row in worst.iterrows():
            nama = row.get("Rincian Kegiatan") or row.get("Sub Kegiatan") or row.get("Kegiatan", "")
            sub_points.append(
                f"⚠️ <b>{nama}</b> — lebih {rupiah(row['Realisasi Biaya'] - row['Target Biaya'])} "
                f"({row['Selisih (%)']:.0f}% di atas target)"
            )
    elif total_realisasi_biaya > 0:
        main_points.append(("✅", "Tidak ada item yang melebihi target biaya pada proyek/filter ini."))

    return main_points, sub_points


# ---------------------------------------------------------
# HEADER + UPLOAD
# ---------------------------------------------------------

st.sidebar.title("⚙️ Pengaturan")
uploaded_file = st.sidebar.file_uploader("Upload file Excel RKP (.xlsx)", type=["xlsx"])

st.markdown("""
<div class="rkp-header">
    <h1>🌴 Laporan Monitoring RKP</h1>
    <p>Klik salah satu baris proyek pada tabel untuk melihat detail, capaian, dan analisa otomatisnya.</p>
</div>
""", unsafe_allow_html=True)

if uploaded_file is None:
    st.info("👈 Silakan upload file Excel RKP (sheet **'Rekap RKP'**) di sidebar untuk mulai.")
    st.stop()

# Placeholder di posisi paling atas — akan diisi kartu KPI setelah proyek dipilih di bawah
kpi_placeholder = st.container()
st.write("")

try:
    xl = pd.ExcelFile(uploaded_file)
    sheet_options = [s for s in xl.sheet_names if s.lower() == "rekap rkp"] or xl.sheet_names
    sheet_choice = st.sidebar.selectbox("Pilih sheet data", options=sheet_options, index=0)
    df = load_data(uploaded_file, sheet_name=sheet_choice)
except Exception as e:
    st.error(f"Gagal membaca file: {e}")
    st.stop()

required_cols = {"Proyek", "Kegiatan", "Target Biaya", "Realisasi Biaya"}
missing = required_cols - set(df.columns)
if missing:
    st.warning(f"Kolom berikut tidak ditemukan di sheet '{sheet_choice}': {', '.join(missing)}.")
    st.stop()

st.sidebar.markdown("### 🔍 Filter Tambahan")
if "Tahun" in df.columns:
    tahun_options = sorted(df["Tahun"].dropna().unique().tolist())
    tahun_sel = st.sidebar.multiselect("Tahun", tahun_options, default=tahun_options)
    df = df[df["Tahun"].isin(tahun_sel)]

# ---------------------------------------------------------
# RINGKASAN PROYEK + GRAFIK RP/HA
# ---------------------------------------------------------

proyek_summary = (
    df.groupby("Proyek", dropna=True)
    .agg(**{
        "Target Biaya": ("Target Biaya", "sum"),
        "Realisasi Biaya": ("Realisasi Biaya", "sum"),
        "Target Ha": ("Target Ha", "sum") if "Target Ha" in df.columns else ("Target Biaya", "sum"),
        "Realisasi Ha": ("Realisasi Ha", "sum") if "Realisasi Ha" in df.columns else ("Realisasi Biaya", "sum"),
    })
    .reset_index()
    .sort_values("Target Biaya", ascending=False)
)
proyek_summary["Target Rp/Ha"] = proyek_summary.apply(
    lambda r: r["Target Biaya"] / r["Target Ha"] if r["Target Ha"] else 0, axis=1)
proyek_summary["Realisasi Rp/Ha"] = proyek_summary.apply(
    lambda r: r["Realisasi Biaya"] / r["Realisasi Ha"] if r["Realisasi Ha"] else 0, axis=1)

col_table, col_chart = st.columns([1, 1.3], gap="medium")

with col_table:
    with st.container(border=True):
        st.markdown('<div class="rkp-section-title">🏗️ Daftar Proyek</div>', unsafe_allow_html=True)
        display_summary = proyek_summary[["Proyek", "Target Biaya", "Realisasi Biaya"]].copy()
        display_summary["Target Biaya"] = display_summary["Target Biaya"].apply(rupiah_singkat)
        display_summary["Realisasi Biaya"] = display_summary["Realisasi Biaya"].apply(rupiah_singkat)

        event = st.dataframe(
            display_summary,
            use_container_width=True,
            hide_index=True,
            height=260,
            on_select="rerun",
            selection_mode="single-row",
            key="proyek_table",
        )
        st.caption("💡 Klik salah satu baris untuk melihat detail proyek.")

selected_rows = []
try:
    selected_rows = event.selection.rows
except Exception:
    selected_rows = event.get("selection", {}).get("rows", []) if isinstance(event, dict) else []

proyek_pilihan = proyek_summary.iloc[selected_rows[0]]["Proyek"] if selected_rows else None

with col_chart:
    with st.container(border=True):
        if proyek_pilihan is None:
            st.markdown('<div class="rkp-section-title">💰 Rp/Ha — Target vs Realisasi (Semua Proyek)</div>', unsafe_allow_html=True)
            rp_ha_chart_df = proyek_summary.melt(
                id_vars="Proyek", value_vars=["Target Rp/Ha", "Realisasi Rp/Ha"],
                var_name="Jenis", value_name="Nilai",
            )
            fig_rp = px.bar(rp_ha_chart_df, x="Proyek", y="Nilai", color="Jenis", barmode="group",
                             color_discrete_map={"Target Rp/Ha": C_WARN, "Realisasi Rp/Ha": C_DANGER})
        else:
            st.markdown(f'<div class="rkp-section-title">💰 Rp/Ha per Kegiatan — {proyek_pilihan}</div>', unsafe_allow_html=True)
            df_scope_chart = df[df["Proyek"] == proyek_pilihan]
            by_keg = df_scope_chart.groupby("Kegiatan", dropna=True).agg(
                **{"Target Biaya": ("Target Biaya", "sum"),
                   "Realisasi Biaya": ("Realisasi Biaya", "sum"),
                   "Target Ha": ("Target Ha", "sum") if "Target Ha" in df.columns else ("Target Biaya", "sum"),
                   "Realisasi Ha": ("Realisasi Ha", "sum") if "Realisasi Ha" in df.columns else ("Realisasi Biaya", "sum")}
            ).reset_index()
            by_keg["Target Rp/Ha"] = by_keg.apply(lambda r: r["Target Biaya"] / r["Target Ha"] if r["Target Ha"] else 0, axis=1)
            by_keg["Realisasi Rp/Ha"] = by_keg.apply(lambda r: r["Realisasi Biaya"] / r["Realisasi Ha"] if r["Realisasi Ha"] else 0, axis=1)
            rp_ha_chart_df = by_keg.melt(
                id_vars="Kegiatan", value_vars=["Target Rp/Ha", "Realisasi Rp/Ha"],
                var_name="Jenis", value_name="Nilai",
            )
            fig_rp = px.bar(rp_ha_chart_df, x="Kegiatan", y="Nilai", color="Jenis", barmode="group",
                             color_discrete_map={"Target Rp/Ha": C_WARN, "Realisasi Rp/Ha": C_DANGER})

        fig_rp = style_plotly(fig_rp)
        st.plotly_chart(fig_rp, use_container_width=True, config={"displayModeBar": False})

st.write("")

# ---------------------------------------------------------
# DETAIL PROYEK TERPILIH
# ---------------------------------------------------------

if proyek_pilihan is None:
    df_scope = df
    judul_detail = "Semua Proyek"
else:
    df_scope = df[df["Proyek"] == proyek_pilihan]
    judul_detail = proyek_pilihan

total_target_biaya = df_scope["Target Biaya"].sum()
total_realisasi_biaya = df_scope["Realisasi Biaya"].sum()
total_target_ha = df_scope["Target Ha"].sum() if "Target Ha" in df_scope.columns else 0
total_realisasi_ha = df_scope["Realisasi Ha"].sum() if "Realisasi Ha" in df_scope.columns else 0
capaian_biaya = pct(total_realisasi_biaya, total_target_biaya)
capaian_fisik = pct(total_realisasi_ha, total_target_ha)

# --- KPI ringkas: ditampilkan di posisi paling atas (via placeholder) ---
with kpi_placeholder:
    k1, k2, k3, k4 = st.columns(4, gap="small")
    k1.metric("Target Biaya", rupiah_singkat(total_target_biaya))
    k2.metric("Realisasi Biaya", rupiah_singkat(total_realisasi_biaya))
    k3.metric("Target Fisik", f"{angka(total_target_ha)} Ha")
    k4.metric("Realisasi Fisik", f"{angka(total_realisasi_ha)} Ha")

col_detail, col_gauge = st.columns([2, 1], gap="medium")

with col_detail:
    with st.container(border=True):
        st.markdown(f'<div class="rkp-section-title">📋 Detail Pekerjaan — {judul_detail}</div>', unsafe_allow_html=True)
        display_cols = [c for c in [
            "Kegiatan", "Sub Kegiatan", "Rincian Kegiatan",
            "Target Biaya", "Realisasi Biaya", "Target Ha", "Realisasi Ha",
        ] if c in df_scope.columns]

        def highlight_over_budget(row):
            if row.get("Realisasi Biaya", 0) > row.get("Target Biaya", 0) and row.get("Target Biaya", 0) > 0:
                return [f"background-color: {C_DANGER}33"] * len(row)
            return [""] * len(row)

        fmt = {c: rupiah for c in ["Target Biaya", "Realisasi Biaya"] if c in display_cols}
        fmt.update({c: angka for c in ["Target Ha", "Realisasi Ha"] if c in display_cols})

        styled = df_scope[display_cols].style.apply(highlight_over_budget, axis=1).format(fmt)
        st.dataframe(styled, use_container_width=True, height=360, hide_index=True)
        st.caption("🔴 Baris merah = Realisasi Biaya melebihi Target Biaya.")

with col_gauge:
    with st.container(border=True):
        st.markdown('<div class="rkp-section-title">🎯 Capaian</div>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1:
            st.plotly_chart(donut(capaian_biaya, C_ACCENT), use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="donut-label">CAPAIAN BIAYA</div>', unsafe_allow_html=True)
        with g2:
            st.plotly_chart(donut(capaian_fisik, C_ACCENT2), use_container_width=True, config={"displayModeBar": False})
            st.markdown('<div class="donut-label">CAPAIAN FISIK</div>', unsafe_allow_html=True)

        st.write("")
        st.markdown(f"""
        <div style="font-size:13px; color:{C_MUTED}; line-height:1.9;">
            Sisa Biaya &nbsp;&nbsp;<b style="color:{C_TEXT};">{rupiah_singkat(total_target_biaya - total_realisasi_biaya)}</b><br>
            Sisa Fisik &nbsp;&nbsp;&nbsp;<b style="color:{C_TEXT};">{angka(total_target_ha - total_realisasi_ha)} Ha</b>
        </div>
        """, unsafe_allow_html=True)

st.write("")

# ---------------------------------------------------------
# ANALISA OTOMATIS
# ---------------------------------------------------------

with st.container(border=True):
    st.markdown('<div class="rkp-section-title">🧠 Analisa Otomatis</div>', unsafe_allow_html=True)
    main_points, sub_points = generate_insights(df_scope, judul_detail)

    html = '<div class="insight-box">'
    for icon, text in main_points:
        html += f'<div class="insight-item">{icon}&nbsp;&nbsp;{text}</div>'
    for text in sub_points:
        html += f'<div class="insight-sub">{text}</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
