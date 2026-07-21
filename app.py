import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Laporan Monitoring RKP", page_icon="🌴", layout="wide")

RUPIAH_M = lambda x: f"{x/1_000_000_000:,.1f} M".replace(",", "X").replace(".", ",").replace("X", ".") if abs(x) >= 1_000_000_000 else f"{x/1_000_000:,.1f} jt".replace(",", "X").replace(".", ",").replace("X", ".")
RUPIAH = lambda x: f"Rp {x:,.0f}".replace(",", ".")
ANGKA = lambda x: f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ---------------------------------------------------------
# CSS - nuansa gelap ala Data Studio
# ---------------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: #1a1f2e;
        border-radius: 8px;
        padding: 12px 16px;
        border: 1px solid #2a2f45;
    }
    h1, h2, h3 { color: #fafafa; }
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


def donut(value_pct, color="#5b6fd8"):
    value_pct = max(0, min(100, value_pct))
    fig = go.Figure(data=[go.Pie(
        values=[value_pct, 100 - value_pct],
        hole=0.72,
        marker_colors=[color, "#2a2f45"],
        textinfo="none",
        sort=False,
        direction="clockwise",
    )])
    fig.update_layout(
        showlegend=False,
        annotations=[dict(text=f"{value_pct:.2f}", x=0.5, y=0.5, font_size=30,
                           showarrow=False, font_color="white")],
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        height=230,
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

    if total_realisasi_biaya == 0 and total_realisasi_ha == 0:
        insights.append(
            f"ℹ️ Untuk **{proyek_name}**, kolom Realisasi Biaya & Realisasi Fisik masih kosong (0). "
            "Begitu diisi di Excel dan file di-upload ulang, analisa *over budget* di bawah akan otomatis muncul."
        )
    else:
        insights.append(
            f"📊 **{proyek_name}**: capaian biaya **{capaian_biaya:.1f}%**, capaian fisik **{capaian_fisik:.1f}%**."
        )
        if capaian_fisik > 0 and capaian_biaya > capaian_fisik + 10:
            insights.append("⚠️ Penyerapan biaya lebih cepat dari progres fisik di lapangan — perlu dicek.")
        elif capaian_biaya > 0 and capaian_fisik > capaian_biaya + 10:
            insights.append("✅ Progres fisik lebih cepat dari penyerapan biaya — efisiensi cukup baik.")

    over = df[(df["Realisasi Biaya"] > df["Target Biaya"]) & (df["Target Biaya"] > 0)].copy()
    if not over.empty:
        over["Selisih (%)"] = (over["Realisasi Biaya"] - over["Target Biaya"]) / over["Target Biaya"] * 100
        worst = over.sort_values("Selisih (%)", ascending=False).head(5)
        insights.append(f"🔴 **{len(over)} item** melebihi target biaya, contoh:")
        for _, row in worst.iterrows():
            nama = row.get("Rincian Kegiatan") or row.get("Sub Kegiatan") or row.get("Kegiatan", "")
            insights.append(
                f"&nbsp;&nbsp;&nbsp;⚠️ **{nama}** — lebih {RUPIAH(row['Realisasi Biaya'] - row['Target Biaya'])} "
                f"({row['Selisih (%)']:.0f}% di atas target)"
            )
    else:
        if total_realisasi_biaya > 0:
            insights.append("✅ Tidak ada item yang melebihi target biaya pada proyek/filter ini.")

    return insights


# ---------------------------------------------------------
# HEADER + UPLOAD
# ---------------------------------------------------------

st.sidebar.title("⚙️ Pengaturan")
uploaded_file = st.sidebar.file_uploader("Upload file Excel RKP (.xlsx)", type=["xlsx"])

col_logo, col_title = st.columns([1, 6])
with col_title:
    st.title("🌴 Laporan Monitoring RKP")
    st.caption("Klik salah satu baris proyek pada tabel untuk melihat detail & analisanya.")

if uploaded_file is None:
    st.info("👈 Silakan upload file Excel RKP (sheet **'Rekap RKP'**) di sidebar untuk mulai.")
    st.stop()

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

# Filter tahun (opsional, mempengaruhi semua proyek)
st.sidebar.markdown("### 🔍 Filter Tambahan")
if "Tahun" in df.columns:
    tahun_options = sorted(df["Tahun"].dropna().unique().tolist())
    tahun_sel = st.sidebar.multiselect("Tahun", tahun_options, default=tahun_options)
    df = df[df["Tahun"].isin(tahun_sel)]

# ---------------------------------------------------------
# TABEL RINGKASAN PROYEK (KLIK UNTUK FILTER)
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

col_table, col_chart = st.columns([1, 1.3])

with col_table:
    st.subheader("Proyek")
    display_summary = proyek_summary[["Proyek", "Target Biaya", "Realisasi Biaya"]].copy()
    display_summary["Target Biaya"] = display_summary["Target Biaya"].apply(RUPIAH_M)
    display_summary["Realisasi Biaya"] = display_summary["Realisasi Biaya"].apply(RUPIAH_M)

    event = st.dataframe(
        display_summary,
        use_container_width=True,
        hide_index=True,
        height=280,
        on_select="rerun",
        selection_mode="single-row",
        key="proyek_table",
    )

selected_rows = []
try:
    selected_rows = event.selection.rows
except Exception:
    selected_rows = event.get("selection", {}).get("rows", []) if isinstance(event, dict) else []

if selected_rows:
    proyek_pilihan = proyek_summary.iloc[selected_rows[0]]["Proyek"]
else:
    proyek_pilihan = None  # mode overview: semua proyek dibandingkan

with col_chart:
    st.subheader("Rp/Ha — Target vs Realisasi")
    if proyek_pilihan is None:
        rp_ha_chart_df = proyek_summary.melt(
            id_vars="Proyek", value_vars=["Target Rp/Ha", "Realisasi Rp/Ha"],
            var_name="Jenis", value_name="Nilai",
        )
        fig_rp = px.bar(rp_ha_chart_df, x="Proyek", y="Nilai", color="Jenis", barmode="group",
                         color_discrete_map={"Target Rp/Ha": "#f5a623", "Realisasi Rp/Ha": "#d0392b"})
    else:
        df_scope = df[df["Proyek"] == proyek_pilihan]
        by_keg = df_scope.groupby("Kegiatan", dropna=True).agg(
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
                         color_discrete_map={"Target Rp/Ha": "#f5a623", "Realisasi Rp/Ha": "#d0392b"})
        fig_rp.update_layout(title=f"Rincian Kegiatan — {proyek_pilihan}")

    fig_rp.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                          plot_bgcolor="rgba(0,0,0,0)", legend_title="")
    st.plotly_chart(fig_rp, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# DETAIL PROYEK TERPILIH
# ---------------------------------------------------------

if proyek_pilihan is None:
    st.info("💡 Klik salah satu baris proyek di atas untuk melihat detail kegiatan, capaian, dan analisa over budget-nya.")
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

col_detail, col_gauge = st.columns([2, 1])

with col_detail:
    st.subheader(f"📋 Detail — {judul_detail}")
    display_cols = [c for c in [
        "Kegiatan", "Sub Kegiatan", "Rincian Kegiatan",
        "Target Biaya", "Realisasi Biaya", "Target Ha", "Realisasi Ha",
    ] if c in df_scope.columns]

    def highlight_over_budget(row):
        if row.get("Realisasi Biaya", 0) > row.get("Target Biaya", 0) and row.get("Target Biaya", 0) > 0:
            return ["background-color: #4a1f1f"] * len(row)
        return [""] * len(row)

    fmt = {c: RUPIAH for c in ["Target Biaya", "Realisasi Biaya"] if c in display_cols}
    fmt.update({c: ANGKA for c in ["Target Ha", "Realisasi Ha"] if c in display_cols})

    styled = df_scope[display_cols].style.apply(highlight_over_budget, axis=1).format(fmt)
    st.dataframe(styled, use_container_width=True, height=380)
    st.caption("🔴 Baris merah = Realisasi Biaya melebihi Target Biaya.")

with col_gauge:
    st.subheader("Capaian")
    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(donut(capaian_biaya, "#5b6fd8"), use_container_width=True)
        st.markdown("<p style='text-align:center;'>Capaian Biaya</p>", unsafe_allow_html=True)
    with g2:
        st.plotly_chart(donut(capaian_fisik, "#5bc0be"), use_container_width=True)
        st.markdown("<p style='text-align:center;'>Capaian Fisik</p>", unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------
# ANALISA OTOMATIS
# ---------------------------------------------------------

st.subheader("🧠 Analisa Otomatis")
for insight in generate_insights(df_scope, judul_detail):
    st.markdown(insight, unsafe_allow_html=True)
