import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os, time
from influxdb_client_3 import InfluxDBClient3, Point
from openai import ChatCompletion

import os

# Streamlit app layout
# st.title("Status Dashboard with Recommendations")
#st.sidebar.header("Configuration")

# NOTE: Need to understand difference of using config sidebar vs. env variables...
# Why use config variables? balance of public facing app with easy config options?


# env variables
INFLUXDB_URL = os.getenv('INFLUXDB_URL')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
OPENAI_API = os.getenv('OPENAIAPI')

# Input configuration
# influxdb_url = st.sidebar.text_input("InfluxDB URL", "http://localhost:8086")
# influxdb_token = st.sidebar.text_input("InfluxDB Token", type="password")
# influxdb_org = st.sidebar.text_input("InfluxDB Organization")
# influxdb_bucket = st.sidebar.text_input("InfluxDB Bucket")

# openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
# st.sidebar.write("Enter credentials and refresh the app.")

# Function to query historical data from InfluxDB
def query_historical_data(duration):
    query = f"""
    SELECT status, time
    FROM 'habit_tracker'
    WHERE time > now() - interval '{duration}'
    """

    with InfluxDBClient3(host=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG) as client:
        # Execute the query
        table = client.query(query=query, database="personal_projects", language='sql')
        # Convert to dataframe
        df = table.to_pandas().sort_values(by="time")
        return df
    

# Function to query the current status
def query_current_status():
    query = f"""
    SELECT status
    FROM 'habit_tracker'
    ORDER BY time DESC
    LIMIT 1
    """
    with InfluxDBClient3(host=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG) as client:
        # Execute the query
        table = client.query(query=query, database="personal_projects", language='sql')
        # Convert to dataframe
        df = table.to_pandas()
        return df['status'][0]

# Function to analyze habit patterns with an LLM
def analyze_patterns(data):
    prompt = f"""
    Here is a dataset of status patterns by minute:\n{data}\n
    Please analyze the patterns and provide recommendations for optimization.
    """
    openai.api_key = OPENAI_API
    response = ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an expert data analyst."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message["content"]

# Main application logic
if INFLUXDB_URL and INFLUXDB_TOKEN and INFLUXDB_ORG and INFLUXDB_BUCKET:
    # Query and display the current status
    st.subheader("Current Status")
    current_status = query_current_status()
    if current_status:
        st.success(f"Current Status: {current_status}")
    else:
        st.warning("No current status available.")
    # Query historical data
    historical_long = query_historical_data('2 days')
    historical_short = query_historical_data('1 hour')

    if not historical_long.empty:
        # Process data for visualization
        historical_long["minute"] = historical_long["time"].dt.floor("min")
        historical_long["hour"] = historical_long["time"].dt.floor("h")
        aggregated_data_hourly = historical_long.groupby(["hour", "status"]).size().reset_index(name="count")
        aggregated_data_hourly = aggregated_data_hourly.pivot(index="hour", columns="status", values="count").fillna(0)
        # Convert datetime columns to strings for Plotly, if needed
        aggregated_data_hourly.index = aggregated_data_hourly.index.strftime("%Y-%m-%d %H:%M:%S")

        # Process data for visualization
        historical_short["minute"] = historical_short["time"].dt.floor("min")
        historical_short["hour"] = historical_short["time"].dt.floor("h")
        aggregated_data_minutes = historical_short.groupby(["minute", "status"]).size().reset_index(name="count")
        aggregated_data_minutes = aggregated_data_minutes.pivot(index="minute", columns="status", values="count").fillna(0)
        # Convert datetime columns to strings for Plotly, if needed
        aggregated_data_minutes.index = aggregated_data_minutes.index.strftime("%Y-%m-%d %H:%M:%S")

        # Plot stacked bar chart
        st.subheader("Hour Summary")
        fig1 = px.bar(
            aggregated_data_minutes,
            x=aggregated_data_minutes.index,
            y=aggregated_data_minutes.columns,
            title="Status by Minute",
            labels={"minute": "Time", "value": "Count", "variable": "Status"},
        )
        fig1.update_yaxes(showticklabels=False, title=None)
        st.plotly_chart(fig1)
        # Plot stacked bar chart
        st.subheader("2 Day Summary")
        fig2 = px.bar(
            aggregated_data_hourly,
            x=aggregated_data_hourly.index,
            y=aggregated_data_hourly.columns,
            title="Status by Hour",
            labels={"hour": "Time", "value": "Count", "variable": "Status"},
        )
        fig2.update_yaxes(showticklabels=False, title=None)
        st.plotly_chart(fig2)


        


        
        # Analyze patterns using LLM
        if OPENAI_API:
            st.subheader("Recommendations")
            recommendations = analyze_patterns(aggregated_data.to_csv())
            st.write(recommendations)

    else:
        st.warning("No historical data available.")

    
else:
    st.error("Please provide all required InfluxDB credentials.")