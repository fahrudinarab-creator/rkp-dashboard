import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard RKP", page_icon="🌴", layout="wide")

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

RUPIAH = lambda x: f"Rp {x:,.0f}".replace(",", ".")

@st.cache_data
def load_data(file, sheet_name="Rekap RKP"):
    df = pd.read_excel(file, sheet_name=sheet_name)
    # Bersihkan tipe data numerik
    num_cols = ["Target Biaya", "Realisasi Biaya", "Selisih Biaya",
                "Target Ha", "Realisasi Ha", "Selisih Ha",
                "% Realisasi", "% Sisa"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def kpi_card(col, label, value, delta=None, help_text=None):
    col.metric(label, value, delta=delta, help=help_text)


def generate_insights(df):
    """Menghasilkan analisa otomatis berbasis data Target vs Realisasi."""
    insights = []

    total_target = df["Target Biaya"].sum()
    total_realisasi = df["Realisasi Biaya"].sum()
    total_selisih = total_target - total_realisasi
    pct_realisasi = (total_realisasi / total_target * 100) if total_target > 0 else 0

    if total_realisasi == 0:
        insights.append(
            "ℹ️ Belum ada data **Realisasi Biaya** yang terisi (semua bernilai 0). "
            "Dashboard ini sudah lengkap dengan logika analisa otomatis (biaya melebihi "
            "target, progres per kegiatan, dll) — begitu kolom *Realisasi Biaya* diisi di "
            "Excel dan file di-upload ulang, semua insight di bawah akan otomatis muncul."
        )
    else:
        insights.append(
            f"📊 Realisasi biaya saat ini mencapai **{pct_realisasi:.1f}%** dari total target "
            f"({RUPIAH(total_realisasi)} dari {RUPIAH(total_target)})."
        )

    # Item yang melebihi target (over budget)
    over_budget = df[df["Realisasi Biaya"] > df["Target Biaya"]].copy()
    if not over_budget.empty:
        over_budget["Selisih (%)"] = (
            (over_budget["Realisasi Biaya"] - over_budget["Target Biaya"])
            / over_budget["Target Biaya"].replace(0, pd.NA) * 100
        )
        worst = over_budget.sort_values("Selisih Biaya", ascending=True).head(3)
        for _, row in worst.iterrows():
            insights.append(
                f"⚠️ **{row.get('Rincian Kegiatan', row.get('Kegiatan',''))}** "
                f"({row.get('Proyek','')}) melebihi target sebesar "
                f"{RUPIAH(abs(row['Realisasi Biaya'] - row['Target Biaya']))} "
                f"({row['Selisih (%)']:.0f}% di atas target)."
            )

    # Kegiatan dengan target terbesar (paling berisiko/penting dipantau)
    by_kegiatan = df.groupby("Kegiatan", dropna=True)["Target Biaya"].sum().sort_values(ascending=False)
    if not by_kegiatan.empty and by_kegiatan.iloc[0] > 0:
        top_kegiatan = by_kegiatan.index[0]
        insights.append(
            f"🏗️ Kegiatan dengan alokasi anggaran terbesar adalah **{top_kegiatan}** "
            f"senilai {RUPIAH(by_kegiatan.iloc[0])} "
            f"({by_kegiatan.iloc[0] / df['Target Biaya'].sum() * 100:.0f}% dari total target)."
        )

    return insights


# ---------------------------------------------------------
# SIDEBAR - UPLOAD & FILTER
# ---------------------------------------------------------

st.sidebar.title("⚙️ Pengaturan")
uploaded_file = st.sidebar.file_uploader("Upload file Excel RKP (.xlsx)", type=["xlsx"])

st.title("🌴 Dashboard RKP — Target vs Realisasi Biaya")
st.caption("Upload file Master RKP untuk melihat dashboard dan analisa otomatis.")

if uploaded_file is None:
    st.info("👈 Silakan upload file Excel RKP (sheet **'Rekap RKP'**) di sidebar untuk mulai.")
    st.stop()

try:
    xl = pd.ExcelFile(uploaded_file)
    sheet_choice = st.sidebar.selectbox(
        "Pilih sheet data",
        options=[s for s in xl.sheet_names if s.lower() in ("rekap rkp",)] or xl.sheet_names,
        index=0,
    )
    df = load_data(uploaded_file, sheet_name=sheet_choice)
except Exception as e:
    st.error(f"Gagal membaca file: {e}")
    st.stop()

required_cols = {"Proyek", "Kegiatan", "Target Biaya", "Realisasi Biaya"}
missing = required_cols - set(df.columns)
if missing:
    st.warning(f"Kolom berikut tidak ditemukan di sheet '{sheet_choice}': {', '.join(missing)}. "
               f"Pastikan Anda memilih sheet 'Rekap RKP'.")

# --- Filters ---
st.sidebar.markdown("### 🔍 Filter Data")

def multiselect_filter(col_name, label):
    if col_name in df.columns:
        options = sorted(df[col_name].dropna().unique().tolist())
        selected = st.sidebar.multiselect(label, options, default=options)
        return selected
    return None

proyek_sel = multiselect_filter("Proyek", "Proyek")
tahun_sel = multiselect_filter("Tahun", "Tahun")
kegiatan_sel = multiselect_filter("Kegiatan", "Kegiatan")
bulan_sel = multiselect_filter("Bulan", "Bulan / Cawu")

df_f = df.copy()
if proyek_sel is not None:
    df_f = df_f[df_f["Proyek"].isin(proyek_sel)]
if tahun_sel is not None:
    df_f = df_f[df_f["Tahun"].isin(tahun_sel)]
if kegiatan_sel is not None:
    df_f = df_f[df_f["Kegiatan"].isin(kegiatan_sel)]
if bulan_sel is not None:
    df_f = df_f[df_f["Bulan"].isin(bulan_sel)]

if df_f.empty:
    st.warning("Tidak ada data untuk kombinasi filter ini.")
    st.stop()

# ---------------------------------------------------------
# KPI CARDS
# ---------------------------------------------------------

total_target = df_f["Target Biaya"].sum()
total_realisasi = df_f["Realisasi Biaya"].sum()
total_selisih = total_target - total_realisasi
pct_realisasi = (total_realisasi / total_target * 100) if total_target > 0 else 0

c1, c2, c3, c4 = st.columns(4)
kpi_card(c1, "Total Target Biaya", RUPIAH(total_target))
kpi_card(c2, "Total Realisasi Biaya", RUPIAH(total_realisasi))
kpi_card(c3, "Sisa Anggaran", RUPIAH(total_selisih))
kpi_card(c4, "% Realisasi", f"{pct_realisasi:.1f}%")

st.divider()

# ---------------------------------------------------------
# ANALISA OTOMATIS
# ---------------------------------------------------------

st.subheader("🧠 Analisa Otomatis")
for insight in generate_insights(df_f):
    st.markdown(f"- {insight}")

st.divider()

# ---------------------------------------------------------
# CHARTS
# ---------------------------------------------------------

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Target Biaya per Kegiatan")
    by_keg = df_f.groupby("Kegiatan", dropna=True)[["Target Biaya", "Realisasi Biaya"]].sum().reset_index()
    by_keg = by_keg.sort_values("Target Biaya", ascending=False)
    fig = px.bar(
        by_keg, x="Kegiatan", y=["Target Biaya", "Realisasi Biaya"],
        barmode="group", labels={"value": "Biaya (Rp)", "variable": ""},
    )
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Komposisi Target Biaya per Proyek")
    by_proyek = df_f.groupby("Proyek", dropna=True)["Target Biaya"].sum().reset_index()
    fig2 = px.pie(by_proyek, names="Proyek", values="Target Biaya", hole=0.4)
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Target vs Realisasi per Sub Kegiatan (Top 15 berdasarkan Target)")
if "Sub Kegiatan" in df_f.columns:
    by_sub = (
        df_f.groupby("Sub Kegiatan", dropna=True)[["Target Biaya", "Realisasi Biaya"]]
        .sum()
        .reset_index()
        .sort_values("Target Biaya", ascending=False)
        .head(15)
    )
    fig3 = go.Figure()
    fig3.add_bar(name="Target Biaya", x=by_sub["Sub Kegiatan"], y=by_sub["Target Biaya"])
    fig3.add_bar(name="Realisasi Biaya", x=by_sub["Sub Kegiatan"], y=by_sub["Realisasi Biaya"])
    fig3.update_layout(barmode="group", xaxis_tickangle=-40)
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# TABEL DETAIL DENGAN HIGHLIGHT
# ---------------------------------------------------------

st.subheader("📋 Detail Data")

display_cols = [c for c in [
    "Proyek", "PT", "Tahun", "Bulan", "Kegiatan", "Sub Kegiatan",
    "Rincian Kegiatan", "Target Biaya", "Realisasi Biaya",
    "Selisih Biaya", "% Realisasi",
] if c in df_f.columns]

def highlight_over_budget(row):
    if "Realisasi Biaya" in row and "Target Biaya" in row:
        if row["Realisasi Biaya"] > row["Target Biaya"] and row["Target Biaya"] > 0:
            return ["background-color: #ffe1e1"] * len(row)
    return [""] * len(row)

styled = df_f[display_cols].style.apply(highlight_over_budget, axis=1).format(
    {c: RUPIAH for c in ["Target Biaya", "Realisasi Biaya", "Selisih Biaya"] if c in display_cols}
)

st.dataframe(styled, use_container_width=True, height=450)

st.caption("🔴 Baris berwarna merah = Realisasi Biaya melebihi Target Biaya.")
