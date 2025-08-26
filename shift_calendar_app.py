import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="Shift Kalender Calculator", page_icon="🗓️", layout="wide")

# ------------------ Helpers ------------------
DUTCH_DAYNAMES = {
    0: "maandag", 1: "dinsdag", 2: "woensdag",
    3: "donderdag", 4: "vrijdag", 5: "zaterdag", 6: "zondag"
}

def parse_hhmm(s: str) -> time:
    if not s:
        return None
    h, m = s.split(":")
    return time(int(h), int(m))

def hours_between(start: time, end: time) -> float:
    dt0 = datetime.combine(date.today(), start)
    dt1 = datetime.combine(date.today(), end)
    if dt1 <= dt0:
        dt1 += timedelta(days=1)
    return (dt1 - dt0).total_seconds() / 3600.0

def month_dates(year: int, month: int):
    d0 = date(year, month, 1)
    d1 = d0 + relativedelta(months=1)
    d = d0
    while d < d1:
        yield d
        d += timedelta(days=1)

def fmt_date(d: pd.Timestamp) -> str:
    return d.strftime("%d-%m-%Y")

def ensure_session():
    if "shiftcodes" not in st.session_state:
        st.session_state.shiftcodes = {
            "v4.5":   {"start": "07:00", "end": "11:00", "pauze": 0,  "label": "Vroege shift 4,5u"},
            "vv6":    {"start": "06:45", "end": "13:15", "pauze": 0,  "label": "Vroege shift 6u (pauze betaald)"},
            "vv7.6":  {"start": "06:45", "end": "14:51", "pauze": 30, "label": "Vroege shift 7,6u"},
            "ll7.6":  {"start": "13:09", "end": "21:15", "pauze": 30, "label": "Late shift 7,6u"},
            "ll6.25": {"start": "14:45", "end": "21:15", "pauze": 0,  "label": "Late shift 6,25u"},
            "ll3,8":  {"start": "16:00", "end": "20:03", "pauze": 0,  "label": "Late shift 3,8u"},
            "ln7,6":  {"start": "15:00", "end": "23:00", "pauze": 30, "label": "Late nacht 7,6u"},
            "ln6":    {"start": "16:30", "end": "23:00", "pauze": 0,  "label": "Late nacht 6u"},
            "n10":    {"start": "21:00", "end": "07:01", "pauze": 0,  "label": "Nacht 10u (over middernacht)"},
            "bijs":   {"start": None, "end": None, "pauze": 0, "label": "Bijscholing (uren invullen)"},
            "fdrecup": {"start": None, "end": None, "pauze": 0, "label": "Betaalde feestdag (0u)"}
        }
    if "data" not in st.session_state:
        st.session_state.data = pd.DataFrame()

ensure_session()

# ------------------ Sidebar ------------------
with st.sidebar:
    st.header("📅 Maand kiezen")
    today = date.today()
    c1, c2 = st.columns(2)
    year = c1.number_input("Jaar", min_value=2000, max_value=2100, value=today.year, step=1)
    month = c2.number_input("Maand", min_value=1, max_value=12, value=today.month, step=1)

    st.divider()
    st.header("⚙️ Shiftcodes beheren")
    with st.form("shift_form", clear_on_submit=False):
        code = st.text_input("Afkorting (bv. vv7.6, ll3,8, n10)").strip().lower()
        colA, colB = st.columns(2)
        s = colA.text_input("Start (HH:MM of leeg)", value="")
        e = colB.text_input("Einde (HH:MM of leeg)", value="")
        pauze = st.number_input("Pauze (minuten)", min_value=0, max_value=180, value=0, step=5)
        label = st.text_input("Betekenis (legende)", value="")
        submitted = st.form_submit_button("Toevoegen / Updaten")
        if submitted and code:
            st.session_state.shiftcodes[code] = {
                "start": (s.strip() or None),
                "end": (e.strip() or None),
                "pauze": int(pauze),
                "label": label or code
            }
            st.success(f"Shiftcode '{code}' opgeslagen.")

    st.markdown("### 📖 Legende")
    for c, info in st.session_state.shiftcodes.items():
        if info["start"] and info["end"]:
            st.write(f"**{c}** → {info['label']} • {info['start']}–{info['end']} • pauze {info['pauze']}m")
        else:
            st.write(f"**{c}** → {info['label']} • variabel / 0u")

# ------------------ Hoofdsectie ------------------
st.title("🗓️ Shift Kalender Calculator")

# Init maandtabel
key_for_month = f"{year}-{month:02d}"
if st.session_state.data.empty or st.session_state.data.get("MaandKey", pd.Series(dtype=str)).ne(key_for_month).all():
    rows = []
    for d in month_dates(year, month):
        rows.append({
            "Datum": pd.to_datetime(d),
            "DagNr": d.weekday(),
            "Dag": DUTCH_DAYNAMES[d.weekday()],
            "Code": "",
            "BIJSuren": 0.0,
            "OverurenMin": 0,
            "Notities": "",
        })
    df = pd.DataFrame(rows)
    df["MaandKey"] = key_for_month
    st.session_state.data = df
else:
    df = st.session_state.data.copy()

st.markdown("### 📝 Maandoverzicht (invullen)")
st.caption("Tip: gebruik codes (zie legende). Bijscholing → uren invullen in 'BIJSuren'. Overuren altijd in minuten!")

# Editor
df_display = df.copy()
df_display["Datum"] = df_display["Datum"].dt.strftime("%d-%m-%Y")
edited = st.data_editor(
    df_display[["Datum", "Dag", "Code", "BIJSuren", "OverurenMin", "Notities"]],
    num_rows="fixed",
    hide_index=True,
    use_container_width=True,
    key="editor"
)

# Terugschrijven
df["Code"] = edited["Code"].str.strip().str.lower()
df["BIJSuren"] = pd.to_numeric(edited["BIJSuren"], errors="coerce").fillna(0.0)
df["OverurenMin"] = pd.to_numeric(edited["OverurenMin"], errors="coerce").fillna(0)
df["Notities"] = edited["Notities"]

# Berekeningen
def calc_hours_for_row(row) -> float:
    code = (row["Code"] or "").strip().lower()
    if code == "bijs":
        return row.get("BIJSuren", 0.0)
    info = st.session_state.shiftcodes.get(code)
    if not info:
        return 0.0
    start, end, pauze = info["start"], info["end"], info["pauze"]
    if not start and not end:
        return 0.0
    bruto = hours_between(parse_hhmm(start), parse_hhmm(end))
    return max(0.0, round(bruto - (pauze / 60.0), 2))

df["ShiftUren"] = df.apply(calc_hours_for_row, axis=1)
df["OverurenUur"] = df["OverurenMin"] / 60.0
df["TotaalUren"] = (df["ShiftUren"] + df["OverurenUur"]).round(2)

# ------------------ Samenvatting ------------------
st.subheader("📊 Samenvatting maand")
c1, c2, c3 = st.columns(3)
c1.metric("Maandtotaal (uren)", f"{df['TotaalUren'].sum():.2f}")
c2.metric("Gem. per gewerkte dag", f"{df.loc[df['TotaalUren']>0,'TotaalUren'].mean():.2f}" if (df["TotaalUren"]>0).any() else "0.00")
c3.metric("Aantal gewerkte dagen", int((df["TotaalUren"]>0).sum()))

# ------------------ Weekoverzicht ------------------
st.markdown("### 🗂️ Overzicht per week")
iso = df["Datum"].dt.isocalendar()
df["Week"] = iso.week.astype(int)
df["Jaar"] = iso.year.astype(int)

for (jaar, week), groep in df.sort_values("Datum").groupby(["Jaar", "Week"]):
    monday = groep["Datum"].min() - timedelta(days=groep["Datum"].min().weekday())
    sunday = monday + timedelta(days=6)
    st.markdown(f"#### Week {week} ({fmt_date(pd.Timestamp(monday))} – {fmt_date(pd.Timestamp(sunday))})")
    blok = groep.copy()
    blok["Datum"] = blok["Datum"].dt.strftime("%d-%m-%Y")
    blok = blok[["Datum", "Dag", "Code", "ShiftUren", "BIJSuren", "OverurenMin", "OverurenUur", "TotaalUren", "Notities"]]
    st.dataframe(blok, use_container_width=True)
    st.write(f"**Totaal Week {week}: {groep['TotaalUren'].sum():.2f} u**")
    st.divider()

# ------------------ Detail + Export ------------------
st.markdown("### 🔎 Detail (alle dagen)")
detail = df.copy()
detail["Datum"] = detail["Datum"].dt.strftime("%d-%m-%Y")
detail = detail[["Datum", "Dag", "Code", "ShiftUren", "BIJSuren", "OverurenMin", "OverurenUur", "TotaalUren", "Week", "Notities"]]
st.dataframe(detail.sort_values(["Week", "Datum"]), use_container_width=True)

csv_bytes = detail.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download CSV",
    data=csv_bytes,
    file_name=f"shift_overzicht_{year}_{month:02d}.csv",
    mime="text/csv"
)

# ------------------ Warnings ------------------
unknown = sorted({c for c in df["Code"] if c and c not in st.session_state.shiftcodes})
if unknown:
    st.warning("Onbekende codes aangetroffen: " + ", ".join(unknown) + ". Voeg ze toe in de sidebar bij Shiftcodes beheren.")
