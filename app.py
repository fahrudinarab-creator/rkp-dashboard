import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard RKP", page_icon="🌴", layout="wide")

RUPIAH = lambda x: f"Rp {x:,.0f}".replace(",", ".")
ANGKA = lambda x: f"{x:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

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


def generate_insights(df, proyek_name):
    insights = []
    total_target_biaya = df["Target Biaya"].sum()
    total_realisasi_biaya = df["Realisasi Biaya"].sum()
    total_target_ha = df["Target Ha"].sum()
    total_realisasi_ha = df["Realisasi Ha"].sum()

    capaian_biaya = pct(total_realisasi_biaya, total_target_biaya)
    capaian_fisik = pct(total_realisasi_ha, total_target_ha)

    if total_realisasi_biaya == 0 and total_realisasi_ha == 0:
        insights.append(
            f"ℹ️ Untuk **{proyek_name}**, kolom Realisasi Biaya dan Realisasi Fisik (Ha) "
            "masih kosong (0). Begitu data ini diisi di Excel dan file di-upload ulang, "
            "seluruh analisa di bawah (termasuk item yang *over budget*) akan otomatis muncul."
        )
    else:
        insights.append(
            f"📊 **{proyek_name}**: capaian biaya **{capaian_biaya:.1f}%** "
            f"({RUPIAH(total_realisasi_biaya)} dari target {RUPIAH(total_target_biaya)}), "
            f"capaian fisik **{capaian_fisik:.1f}%** "
            f"({ANGKA(total_realisasi_ha)} Ha dari target {ANGKA(total_target_ha)} Ha)."
        )
        if capaian_fisik > 0 and capaian_biaya > capaian_fisik + 10:
            insights.append(
                "⚠️ Penyerapan biaya berjalan **lebih cepat** dibanding progres fisik di lapangan "
                "— perlu dicek apakah ada pemborosan atau kegiatan yang dibayar di muka."
            )
        elif capaian_biaya > 0 and capaian_fisik > capaian_biaya + 10:
            insights.append(
                "✅ Progres fisik lebih cepat dari penyerapan biaya — efisiensi biaya cukup baik."
            )

    # Item yang over budget (Realisasi Biaya > Target Biaya)
    over = df[(df["Realisasi Biaya"] > df["Target Biaya"]) & (df["Target Biaya"] > 0)].copy()
    if not over.empty:
        over["Selisih (%)"] = (over["Realisasi Biaya"] - over["Target Biaya"]) / over["Target Biaya"] * 100
        worst = over.sort_values("Selisih (%)", ascending=False).head(5)
        insights.append(f"🔴 Ditemukan **{len(over)} item** dengan biaya melebihi target, contohnya:")
        for _, row in worst.iterrows():
            nama = row.get("Rincian Kegiatan") or row.get("Sub Kegiatan") or row.get("Kegiatan", "")
            insights.append(
                f"　　⚠️ **{nama}** — melebihi target {RUPIAH(row['Realisasi Biaya'] - row['Target Biaya'])} "
                f"({row['Selisih (%)']:.0f}% di atas target)"
            )

    # Item fisik yang belum tercapai jauh dari target
    if total_target_ha > 0 and "Realisasi Ha" in df.columns:
        lag = df[(df["Target Ha"] > 0) & (df["Realisasi Ha"] < df["Target Ha"])]
        if not lag.empty and total_realisasi_ha > 0:
            insights.append(
                f"🟡 Ada **{len(lag)} item pekerjaan** yang realisasi fisiknya (Ha) masih di bawah target — "
                "perlu jadi prioritas pemantauan lapangan."
            )

    return insights


# ---------------------------------------------------------
# SIDEBAR - UPLOAD
# ---------------------------------------------------------

st.sidebar.title("⚙️ Pengaturan")
uploaded_file = st.sidebar.file_uploader("Upload file Excel RKP (.xlsx)", type=["xlsx"])

if uploaded_file is None:
    st.title("🌴 Dashboard RKP")
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
    st.warning(
        f"Kolom berikut tidak ditemukan di sheet '{sheet_choice}': {', '.join(missing)}. "
        f"Pastikan Anda memilih sheet 'Rekap RKP'."
    )
    st.stop()

# ---------------------------------------------------------
# FILTER UTAMA: PILIH 1 PROYEK
# ---------------------------------------------------------

st.sidebar.markdown("### 🏗️ Pilih Proyek")
daftar_proyek = sorted(df["Proyek"].dropna().unique().tolist())
proyek_pilihan = st.sidebar.selectbox("Proyek", daftar_proyek, index=0)

df_proyek = df[df["Proyek"] == proyek_pilihan].copy()

st.sidebar.markdown("### 🔍 Filter Tambahan (opsional)")

def multiselect_filter(col_name, label, data):
    if col_name in data.columns:
        options = sorted(data[col_name].dropna().unique().tolist())
        selected = st.sidebar.multiselect(label, options, default=options)
        return selected
    return None

tahun_sel = multiselect_filter("Tahun", "Tahun", df_proyek)
kegiatan_sel = multiselect_filter("Kegiatan", "Kegiatan", df_proyek)
bulan_sel = multiselect_filter("Bulan", "Bulan / Cawu", df_proyek)

df_f = df_proyek.copy()
if tahun_sel is not None:
    df_f = df_f[df_f["Tahun"].isin(tahun_sel)]
if kegiatan_sel is not None:
    df_f = df_f[df_f["Kegiatan"].isin(kegiatan_sel)]
if bulan_sel is not None:
    df_f = df_f[df_f["Bulan"].isin(bulan_sel)]

st.title(f"🌴 Dashboard RKP — {proyek_pilihan}")
st.caption("Semua kartu, grafik, dan analisa di bawah mengikuti proyek & filter yang dipilih di sidebar.")

if df_f.empty:
    st.warning("Tidak ada data untuk kombinasi filter ini.")
    st.stop()

# ---------------------------------------------------------
# REKAP PROYEK — KPI
# ---------------------------------------------------------

total_target_biaya = df_f["Target Biaya"].sum()
total_realisasi_biaya = df_f["Realisasi Biaya"].sum()
sisa_biaya = total_target_biaya - total_realisasi_biaya
capaian_biaya = pct(total_realisasi_biaya, total_target_biaya)

total_target_ha = df_f["Target Ha"].sum() if "Target Ha" in df_f.columns else 0
total_realisasi_ha = df_f["Realisasi Ha"].sum() if "Realisasi Ha" in df_f.columns else 0
sisa_ha = total_target_ha - total_realisasi_ha
capaian_fisik = pct(total_realisasi_ha, total_target_ha)

st.subheader("📊 Rekap Proyek")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Target Biaya", RUPIAH(total_target_biaya))
c2.metric("Realisasi Biaya", RUPIAH(total_realisasi_biaya))
c3.metric("Sisa Biaya", RUPIAH(sisa_biaya))
c4.metric("% Capaian Biaya", f"{capaian_biaya:.1f}%")

c5, c6, c7, c8 = st.columns(4)
c5.metric("Target Fisik (Ha)", f"{ANGKA(total_target_ha)} Ha")
c6.metric("Realisasi Fisik (Ha)", f"{ANGKA(total_realisasi_ha)} Ha")
c7.metric("Sisa Fisik (Ha)", f"{ANGKA(sisa_ha)} Ha")
c8.metric("% Capaian Fisik", f"{capaian_fisik:.1f}%")

st.divider()

# ---------------------------------------------------------
# ANALISA OTOMATIS
# ---------------------------------------------------------

st.subheader("🧠 Analisa Otomatis")
for insight in generate_insights(df_f, proyek_pilihan):
    st.markdown(insight)

st.divider()

# ---------------------------------------------------------
# GRAFIK
# ---------------------------------------------------------

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Rp/Ha — Target vs Realisasi")
    target_rp_ha = df_f["Target Rp/Ha"].dropna().iloc[0] if "Target Rp/Ha" in df_f.columns and not df_f["Target Rp/Ha"].dropna().empty else 0
    realisasi_rp_ha = (total_realisasi_biaya / total_realisasi_ha) if total_realisasi_ha > 0 else 0
    rp_ha_df = pd.DataFrame({
        "Jenis": ["Target Rp/Ha", "Realisasi Rp/Ha"],
        "Nilai": [target_rp_ha, realisasi_rp_ha],
    })
    fig_rp_ha = px.bar(rp_ha_df, x="Jenis", y="Nilai", text="Nilai", color="Jenis")
    fig_rp_ha.update_traces(texttemplate="Rp %{text:,.0f}", textposition="outside")
    fig_rp_ha.update_layout(showlegend=False, yaxis_title="Rp per Ha")
    st.plotly_chart(fig_rp_ha, use_container_width=True)
    st.caption(
        "Realisasi Rp/Ha dihitung otomatis = Total Realisasi Biaya ÷ Total Realisasi Fisik (Ha) "
        "pada proyek & filter terpilih."
    )

with col_b:
    st.subheader("Target vs Realisasi Biaya per Kegiatan")
    by_keg = df_f.groupby("Kegiatan", dropna=True)[["Target Biaya", "Realisasi Biaya"]].sum().reset_index()
    by_keg = by_keg.sort_values("Target Biaya", ascending=False)
    fig_keg = px.bar(
        by_keg, x="Kegiatan", y=["Target Biaya", "Realisasi Biaya"],
        barmode="group", labels={"value": "Biaya (Rp)", "variable": ""},
    )
    st.plotly_chart(fig_keg, use_container_width=True)

st.subheader("Target vs Realisasi per Sub Kegiatan (Top 15 berdasarkan Target Biaya)")
if "Sub Kegiatan" in df_f.columns:
    by_sub = (
        df_f.groupby("Sub Kegiatan", dropna=True)[["Target Biaya", "Realisasi Biaya"]]
        .sum()
        .reset_index()
        .sort_values("Target Biaya", ascending=False)
        .head(15)
    )
    fig_sub = go.Figure()
    fig_sub.add_bar(name="Target Biaya", x=by_sub["Sub Kegiatan"], y=by_sub["Target Biaya"])
    fig_sub.add_bar(name="Realisasi Biaya", x=by_sub["Sub Kegiatan"], y=by_sub["Realisasi Biaya"])
    fig_sub.update_layout(barmode="group", xaxis_tickangle=-40)
    st.plotly_chart(fig_sub, use_container_width=True)

st.divider()

# ---------------------------------------------------------
# TABEL DETAIL DENGAN HIGHLIGHT
# ---------------------------------------------------------

st.subheader("📋 Detail Data")

display_cols = [c for c in [
    "Proyek", "PT", "Tahun", "Bulan", "Kegiatan", "Sub Kegiatan",
    "Rincian Kegiatan", "Target Ha", "Realisasi Ha",
    "Target Biaya", "Realisasi Biaya", "Selisih Biaya", "% Realisasi",
] if c in df_f.columns]

def highlight_over_budget(row):
    if row.get("Realisasi Biaya", 0) > row.get("Target Biaya", 0) and row.get("Target Biaya", 0) > 0:
        return ["background-color: #ffe1e1"] * len(row)
    return [""] * len(row)

fmt = {c: RUPIAH for c in ["Target Biaya", "Realisasi Biaya", "Selisih Biaya"] if c in display_cols}
fmt.update({c: ANGKA for c in ["Target Ha", "Realisasi Ha"] if c in display_cols})

styled = df_f[display_cols].style.apply(highlight_over_budget, axis=1).format(fmt)
st.dataframe(styled, use_container_width=True, height=450)

st.caption("🔴 Baris merah = Realisasi Biaya melebihi Target Biaya.")
