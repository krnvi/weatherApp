#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun  8 11:01:29 2025

@author: vkvalappil
"""
import warnings
warnings.filterwarnings("ignore", message=".*day of month without a year specified.*")
warnings.filterwarnings("ignore", message="pkg_resources is deprecated.*")
import streamlit as st
import ee
import geemap.foliumap as geemap
import geemap.colormaps as cm
import json
from datetime import datetime, timedelta,timezone
import pytz
import folium
from ee import Filter, Kernel
import calendar
import pandas as pd 
#from streamlit_js_eval import streamlit_js_eval
from st_screen_stats import ScreenData
import streamlit.components.v1 as components


##########################################################################################################################################################
utc = pytz.utc
ist = pytz.timezone('Asia/Kolkata')
##########################################################################################################################################################

#ee.Authenticate()
# Initialize Earth Engine
#ee.Initialize(project="ee-pkvineethkrishnan")

#key_data = dict(st.secrets["GEE"])  
#json_str = json.dumps(key_data)

#key_dict = json.loads(json.dumps(dict(st.secrets["GEE"])))

#credentials = ee.ServiceAccountCredentials(
#    st.secrets["GEE"]["client_email"],
#    key_data=key_dict)  
service_account_json_str  = st.secrets["gcp_service_account"]
service_account_info = json.loads(service_account_json_str)

credentials = ee.ServiceAccountCredentials(
    service_account_info["client_email"],
    key_data=service_account_json_str  # pass JSON string here, NOT dict
)

# Initialize Earth Engine
ee.Initialize(credentials)
##########################################################################################################################################################
def apply_spatial_smoothing(image, radius=3):
    kernel = ee.Kernel.square(radius=radius, units='pixels')
    return image.convolve(kernel)

def round_hour_to_nearest_block(current_hour):
        """Round hour to nearest 0, 6, 12, or 18."""
        blocks = [0, 6, 12, 18]
        return min(blocks, key=lambda x: abs(x - current_hour))
   
def floor_to_previous_block(current_hour):
        for h in reversed([0, 6, 12, 18]):
            if current_hour >= h:
                return h
        return 0  # Fallback  
    
##########################################################################################################################################################
#bounds=[70, 00, 90, 20]
bounds=[60, 00, 100, 40]
region = ee.Geometry.Rectangle(bounds)

kerala_geometry = ee.FeatureCollection("FAO/GAUL/2015/level1") \
    .filter(ee.Filter.eq('ADM1_NAME', 'Kerala')) \
    .geometry()
    

##########################################################################################################################################################
st.set_page_config(
    page_title="Vweather",
    layout="centered",  # Options: "centered" or "wide"
    initial_sidebar_state="expanded",
    page_icon="🌧️"
)

st.markdown(
    """
    <style>
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {
            padding: 0 !important;
            margin: 0 !important;
            max-width: 100% !important;
            width: 100% !important;
        }
        .main {
            padding: 0 !important;
            margin: 0 !important;
            height: 100vh; 
        }
        .css-1aumxhk {
            margin-top: 0 !important;
        }
                
        .custom-title {
            color: #222;
            font-size: 36px;
            font-weight: bold;
            text-align:  center;
            background-color: #ADD8E6;
            border-radius: 0px;
            font-family: 'Segoe UI', sans-serif;
            margin:0; #auto
            padding: 0;
            width: 100%;
        }
        /* Optional: Remove white background behind sidebar/main */
        .css-18e3th9 {
            background-color: transparent !important;
            }

        /* Remove spacing around components */
        .element-container {
            padding: 0 !important;
            margin: 0 !important;
         }
        
        /* Sidebar width */
        section[data-testid="stSidebar"] {
            width: 400px !important;

        }

        /* Sidebar background color */
        section[data-testid="stSidebar"] > div:first-child {
            background-color: #ADD8E6;
        }

        /* Sidebar text styling */
        section[data-testid="stSidebar"] * {
            color: #000000;
            font-size: 12px;
        }
        /* Style the date_input background and text color */
        section[data-testid="stSidebar"] input[type="text"] {
        background-color: white !important;
        color: black !important;
        }

        section[data-testid="stSidebar"] input[type="date"] {
            background-color: white !important;
            color: black !important;
        }
        
        /* Change label color for date input in sidebar */
        section[data-testid="stSidebar"] label {
            color: #000000;  
            font-weight: bold;
        }
    
        /* Force white background on selectbox */
        div[data-baseweb="select"] > div {
            background-color: white !important;
            color: black !important;
        }

        /* Also style the dropdown menu */
        div[data-baseweb="select"] div[role="listbox"] {
            background-color: white !important;
            color: black !important;
        }

        /* Adjust main area when sidebar width changes */
        .main {
            margin-left: 2px;
        }        
        /* Allow the main content to adapt */
        div.block-container {
            padding-left: 1rem !important;
        }
        
    </style>
    <h1 class="custom-title">🌧️ Weather wise </h1>
    """,
    unsafe_allow_html=True,
)
##########################################################################################################################################################
screenD = ScreenData(setTimeout=1000)
screen_d = screenD.st_screen_data()
    
wh=screen_d['innerWidth']
ht=screen_d['innerHeight']
##########################################################################################################################################################

# Sidebar controls
with st.sidebar:
    st.header("Select Date")

    forecast_date = st.date_input("Forecast date", datetime.now(timezone.utc).date())
    # datetime.utcnow().date())
    #print(forecast_date)
    init_time = datetime.combine(forecast_date, datetime.min.time())
    
    # Base UTC time (rounded to nearest past 3-hour step)
    #now_utc = datetime.utcnow() #.replace(minute=0, second=0, microsecond=0)
    now_utc = datetime.now(timezone.utc)
    #init_time

    current_hour = now_utc.hour

    # Round to nearest forecast block
    nearest_block = round_hour_to_nearest_block(current_hour)

    # Construct the adjusted datetime
    next_time = now_utc.replace(hour=nearest_block, minute=0, second=0, microsecond=0)

    previous_block = floor_to_previous_block(current_hour)
    prev_time = next_time-timedelta(hours=(previous_block))
     
    #print(next_time)
    #print(prev_time)

    #now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    
    start_hour = now.hour - (now.hour % 1)
    base_time = now.replace(hour=start_hour)

    # Generate 3-hour forecast steps for 48 hours
    forecast_steps_utc = [base_time + timedelta(hours=i) for i in range(0, 24, 1)]

    # Convert to IST and format labels
    forecast_labels_ist = [
        utc_dt.replace(tzinfo=utc).astimezone(ist).strftime("%Y-%m-%d %H:%M IST")
        for utc_dt in forecast_steps_utc
        ]

    # Show IST labels in dropdown
    selected_ist_label = st.sidebar.selectbox("Select forecast date/time (IST)", forecast_labels_ist)

    # Convert selected IST label back to corresponding UTC datetime
    # (We rely on index matching here)
    selected_index = forecast_labels_ist.index(selected_ist_label)
    forecast_time_utc = forecast_steps_utc[selected_index]
    forecast_hour = (forecast_time_utc - forecast_steps_utc[0]).seconds // 3600
    init_time_utc = forecast_steps_utc[0]

    # Format for GEE
    init_time_iso = init_time.isoformat(timespec='seconds')
    next_time_iso = (init_time + timedelta(hours=6)).isoformat(timespec='seconds')  # wider window to catch image
    
    #print(init_time_iso)
    #print(next_time_iso)

    # # Get date and hour from Streamlit UI
    # forecast_date = st.date_input("Select date", datetime.utcnow().date())
    # forecast_hour = st.selectbox("Select hour (UTC)", [0, 3, 6, 9, 12, 15, 18, 21])

    # # Construct ISO datetime string for GEE
    # forecast_datetime = datetime.combine(forecast_date, datetime.min.time()) + timedelta(hours=forecast_hour)
    # start_time = forecast_datetime.isoformat(timespec='seconds')  
    # end_time = (forecast_datetime + timedelta(hours=1)).isoformat(timespec='seconds')

    # print(start_time)
    # print(end_time)
    # Parameter selection
    param = st.selectbox("Select parameter", ["Temperature", "Rainfall"])

# Load the most recent initialized image
collection = ee.ImageCollection("NOAA/GFS0P25")\
             .filterDate(prev_time, next_time)\
             .filterBounds(region)\
             .filterMetadata("forecast_hours", "equals",forecast_hour)

# Get size (number of forecast images)
#size = collection.size().getInfo()
#print(f"Number of images: {size}")

    
#image = collection.first()
image = collection.sort('system:time_start', False).first()
if image is None:
    st.error("No forecast data available for selected time.")
    st.stop()


def add_legend_from_vis(m, title, vis, bottom_px=50, left_px=50):
    palette = vis['palette']
    min_val = vis['min']
    max_val = vis['max']
    steps = len(palette)
    
    labels = [f"{min_val + i*(max_val - min_val)/(steps - 1):.1f}" for i in range(steps)]

    colors_html = ""
    for color, label in zip(palette, labels):
        colors_html += f"""
        <div style="display: flex; align-items: center; margin-bottom: 3px;">
            <div style="background-color:{color}; width:20px; height:10px; border:1px solid #000; margin-right:6px;"></div>
            <div>{label}</div>
        </div>
        """

    legend_html = f"""
    <div style="
        position: fixed;
        bottom: {bottom_px}px; left: {left_px}px; z-index:9999;
        background-color: white;
        padding: 10px;
        border: 2px solid grey;
        border-radius: 5px;
        font-size: 13px;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
        <strong>{title}</strong><br>
        {colors_html}
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend_html))

def reclassify_to_intervals(img,breaks):
    bins = ee.List(breaks)
    # Classify image based on bins
    classified = ee.Image(0)
    for i in range(len(breaks) - 1):
        lower = breaks[i]
        upper = breaks[i + 1]
        mask = img.gte(lower).And(img.lt(upper))
        classified = classified.where(mask, i)
    return classified


# Set visualization parameters
if param == "Temperature":
    
    band = "temperature_2m_above_ground"
    
    image_tmp = apply_spatial_smoothing(image.select(band)) #.subtract(273.15)
    
    cmap=cm.get_palette("jet")
                
    vis = {"min": 0, "max": 40, "palette": cmap }
           #["blue", "green", "yellow", "red"]}
    #layer = image_tmp.clip(kerala_geometry).visualize(**vis)
    layer = image_tmp.visualize(**vis)
    lbl='deg C'
    
elif param=='Rainfall':
    band = "precipitation_rate"
    image_mm= image.select(band).multiply(3600)
    img_mm=apply_spatial_smoothing(image_mm)
    
    #clevs=[1,10, 20 ,30, 40 ,50, 60, 70, 80, 90 ,100, 110,120,130]
    #discrete_img = reclassify_to_intervals(image_mm,clevs)
    
    vis = {"min": 1,"max": 30,"palette": ['white','lime','limegreen','greenyellow','yellow','gold','orange','indianred','brown','firebrick', \
                  'darkred','lightskyblue','deepskyblue','royalblue','blue']}
        
           #['#cccccc','#f9f3d5','#dce2a8','#a8c58d','#77a87d','#ace8f8','#4cafd9','#1d5ede','#001bc0','#9131f1','#e983f3','#f6c7ec'  ] } 
    #["white", "lightblue", "blue", "darkblue", "purple"]}
    #palette=['white','lime','limegreen','greenyellow','yellow','gold','orange','indianred','brown','firebrick', \
    #              'darkred','lightskyblue','deepskyblue','royalblue','blue']
    #vis_params = {'min': 0, 'max': len(palette) - 1, 'palette': palette}
    
    #layer = image_mm.clip(kerala_geometry).visualize(**vis)
    layer = image_mm.visualize(**vis)
    #layer = discrete_img.clip(kerala_geometry).visualize(**vis_params)
    
    lbl='mm'
    
layer_title = f"{param} @ {selected_ist_label}" #f"{param} @ {forecast_date.strftime('%Y-%m-%d %H:%M UTC')}"


m = geemap.Map() #basemap='ROADMAP') #center=[10, 77.5], zoom=7)
m.centerObject(kerala_geometry, 6)

# Fit the map to this region
#m.fit_bounds(bounds)

# Restrict panning outside the bounds
#m.options['maxBounds'] = bounds

# Optional: Set minimum and maximum zoom levels
m.options['minZoom'] = 1
m.options['maxZoom'] = 15

m.addLayer(kerala_geometry,{'color': 'black', 'fillColor': '00000000'}, "Kerala")

m.addLayer(layer,{}, layer_title,opacity=0.7)

#m.add_colormap(width=7.0, height=0.3,vmin=vis['min'],vmax=vis['max'],palette=vis['palette'],vis_params=None,discrete=False,\
#               label=lbl, label_size=10, label_weight='bold', tick_size=15, bg_color='white', orientation='horizontal', dpi='figure',\
#               transparent=True, position=(50, 15))
 
m.add_colormap(width=0.3, height=5,vmin=vis['min'],vmax=vis['max'],palette=vis['palette'],vis_params=None,discrete=False,\
               label=lbl, label_size=10, label_weight='bold', tick_size=15, bg_color='white', orientation='vertical', dpi='figure',\
               transparent=True, position=(72, 25))
    
#add_legend_from_vis(m, param, vis, bottom_px=50, left_px=20)

m.addLayerControl()

html = m.get_root().render()

components.html(f"""
<div style="height: 100vh; width: 100%; position: relative;">
    {html}
</div>
""", height=ht,width=wh, scrolling=False)

#m.to_streamlit(height=700)


