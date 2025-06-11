import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# 1) Read your CSV file (with exactly these four column headers):
#    "Organization Name,Customer Type,State,Org Specialty"
df = pd.read_csv("customers.csv")

# 2) If any rows have multiple states comma‐separated in "State" (e.g. "MI, IL, IA"),
#    split them into individual rows so each row has a single two‐letter code.
#    If your CSV already lists one state per row, you can skip this step.
df = (
    df
    .assign(State=df["State"].str.split(r"\s*,\s*"))
    .explode("State")
    .reset_index(drop=True)
)

# Initialize geocoder
geolocator = Nominatim(user_agent="my_customer_map")

# Function to get coordinates
def get_coordinates(city, state):
    try:
        location = geolocator.geocode(f"{city}, {state}, USA")
        if location:
            return location.latitude, location.longitude
        return None, None
    except GeocoderTimedOut:
        return None, None

# Add coordinates to your dataframe
df['latitude'] = None
df['longitude'] = None

for idx, row in df.iterrows():
    lat, lon = get_coordinates(row['City'], row['State'])
    df.at[idx, 'latitude'] = lat
    df.at[idx, 'longitude'] = lon

# 3) Define a helper that takes one group (all rows for a given state)
#    and returns a Series with:
#      - "Count": number of customers in that state
#      - "HoverInfo": one HTML‐formatted string with each line like:
#         Organization Name ( Customer Type ; Org Specialty )
def make_tooltip(group: pd.DataFrame) -> pd.Series:
    count = group.shape[0]
    lines = []
    for _, row in group.iterrows():
        org = row["Organization Name"]
        ctype = row["Customer Type"] or "—"
        spec = row["Org Specialty"] or "—"
        # build a single line, e.g.:
        #   "Alliance Spine and Pain Centers (Pain Management; Nephrology)"
        line = f"{org} ({ctype}; {spec})"
        lines.append(line)
    # join with <br> so Plotly will render as multiple lines in the hover tooltip
    tooltip_str = "<br>".join(lines)
    return pd.Series({"Count": count, "HoverInfo": tooltip_str})

# 4) Group by "State" and apply the helper to create columns "Count" and "HoverInfo".
agg = (
    df
    .groupby("State", as_index=False)
    .apply(make_tooltip)
    .reset_index()
)

# 5) Build the choropleth with Plotly Express.
#    - locations="State" → two‐letter US state codes
#    - color="Count"      → number of customers in that state
#    - hover_data={"HoverInfo": True, "Count": False}
#         → show only our multi‐line HoverInfo on hover (hide the raw Count)
fig = px.choropleth(
    agg,
    locations="State",
    locationmode="USA-states",
    color="Count",
    hover_name="State",                # display state code on hover
    hover_data={"HoverInfo": True, "Count": False},
    scope="usa",
    color_continuous_scale="Viridis",
    title="Customer Map by State (hover to see all orgs)"
)

# 6) Add city markers
# You'll need to add latitude and longitude for each city
# You can use a geocoding service or add these columns to your CSV
fig.add_trace(go.Scattergeo(
    lon=df['longitude'],  # Add this column to your CSV
    lat=df['latitude'],   # Add this column to your CSV
    text=df['City'],      # Your city column
    mode='markers',
    marker=dict(
        size=8,
        color='red',
        opacity=0.7
    ),
    name='Cities'
))

fig.update_layout(
    title_x=0.5,
    margin={"r":0, "t":50, "l":0, "b":0}
)

# Save the map as an HTML file
fig.write_html("customer_map.html")

# Add this line at the end of your script
fig.show()
