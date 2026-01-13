import pandas as pd
import requests
import pydeck as pdk
import streamlit as st
import altair as alt

st.set_page_config(layout="wide")

st.markdown(
    """
    <style>
    .main {
        background-color: #f0f2f6; padding: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)


st.title("MunicipalHub Analytics Dashboard")
st.markdown("Welcome, Super User! This dashboard provides a comprehensive overview of municipal queries, their geographical distribution, and key analytics.")

API_URL = "https://unwittingly-littlish-riva.ngrok-free.dev/super/geocode"

try:
    response = requests.get(API_URL)
    response.raise_for_status()
    data = response.json()
except (requests.exceptions.RequestException, ValueError) as e:
    st.error(f"Could not fetch or parse data from API: {e}")
    st.stop()

df = pd.DataFrame(
    data,
)

# Check if the dataframe has data and the column exists
if not df.empty and "geocode" in df.columns:
    df["lat"] = df["geocode"].apply(lambda x: x["lat"] if x and "lat" in x else None)
    df["lon"] = df["geocode"].apply(lambda x: x["lng"] if x and "lng" in x else None)
else:
    st.info("Waiting for data... No active geocode queries found at the moment.")
    st.stop()
df = df.dropna(subset=["lat", "lon"])
if df.empty:
    st.warning("No data with valid geocodes to display.")
    st.stop()


def priority_to_color(priority):
    if priority == 'urgent':
        return [255, 0, 0, 200]
    if priority == 'high':
        return [255, 255, 0, 200]
    if priority == 'medium':
        return [255, 165, 0, 200]
    return [0, 200, 0, 200]

df["tooltip"] = df.apply(
    lambda x: f"ID: {x['query_id']}\n"
              f"Address: {x['query_address']}\n"
              f"Region: {x['region']}\n"
              f"Status: {x['query_status']}\n"
              f"Priority: {x['priority_status']}\n"
              f"description: {x['query_description']} ",
    axis=1
)

df['color'] = df['priority_status'].apply(priority_to_color)

scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df,
    get_position=["lon", "lat"],
    get_fill_color="color",
    get_radius=200,
    pickable=True,
)

st.header("Query Data")
st.dataframe(df[['query_id', 'query_address', 'region', 'query_status', 'priority_status', 'query_description', 'lat', 'lon']])

@st.cache_data
def convert_df_to_csv(df_to_convert):
    return df_to_convert.to_csv(index=False).encode('utf-8')

csv = convert_df_to_csv(df[['query_id', 'query_address', 'region', 'query_status', 'priority_status', 'query_description', 'lat', 'lon']])

st.download_button(
   "Download Data as CSV",
   csv,
   "query_data.csv",
   "text/csv",
   key='download-csv'
)

st.header("Analytics Dashboard")

# --- Analytics Section ---

st.subheader("Key Metrics")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Queries", len(df))
with col2:
    st.metric("Number of Regions", df['region'].nunique())
with col3:
    st.metric("Urgent Queries", df[df['priority_status'] == 'urgent'].shape[0])

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Query Priority Distribution")
    priority_counts = df['priority_status'].value_counts().reset_index()
    priority_counts.columns = ['priority_status', 'count']
    pie_chart = alt.Chart(priority_counts).mark_arc(innerRadius=5, cornerRadius=10, padAngle=0.02).encode(
        theta=alt.Theta('count:Q', stack='normalize'),
        color=alt.Color('priority_status:N', title='Priority', scale=alt.Scale(
            domain=['urgent', 'high', 'medium', 'low'],
            range=['#FF4B4B', '#FFD700', '#FFA500', '#4CAF50',"#c8000c"]
        ))
    )
    st.altair_chart(pie_chart, use_container_width=True)

with chart_col2:
    st.subheader("Query Status Distribution")
    status_counts = df['query_status'].value_counts().reset_index()
    status_counts.columns = ['query_status', 'count']
    status_pie_chart = alt.Chart(status_counts).mark_arc(innerRadius=0.5, cornerRadius=10, padAngle=0.02).encode(
        theta=alt.Theta(field="count", type="quantitative", stack='normalize'),
        color=alt.Color(field="query_status", type="nominal", title="Status")
    )
    st.altair_chart(status_pie_chart, use_container_width=True)

st.subheader("Queries by Region")
region_counts = df['region'].value_counts()
st.bar_chart(region_counts)

st.subheader("Queries by Region and Priority")
crosstab = pd.crosstab(df['region'], df['priority_status'])
st.dataframe(crosstab)

st.header("Map")
st.pydeck_chart(
    pdk.Deck(
        initial_view_state=pdk.ViewState(
            latitude=-30.0,
            longitude=24.0, 
            zoom=5,
            pitch=30,
        ),
        layers=[scatter_layer],
        tooltip={"text": "{tooltip}"},
    )
)
