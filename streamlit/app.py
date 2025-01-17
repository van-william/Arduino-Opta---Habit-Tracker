import streamlit as st
import pandas as pd
import plotly.express as px
from influxdb_client import InfluxDBClient
from openai import ChatCompletion
import os

# Streamlit app layout
st.title("Status Dashboard with Recommendations")
st.sidebar.header("Configuration")

# NOTE: Need to understand difference of using config sidebar vs. env variables...
# Why use config variables? balance of public facing app with easy config options?


# env variables
INFLUXDB_URL = os.getenv('INFLUXDB_URL')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
OPENAI_API = os.getenv('OPENAIAPI')

# Input configuration
influxdb_url = st.sidebar.text_input("InfluxDB URL", "http://localhost:8086")
influxdb_token = st.sidebar.text_input("InfluxDB Token", type="password")
influxdb_org = st.sidebar.text_input("InfluxDB Organization")
influxdb_bucket = st.sidebar.text_input("InfluxDB Bucket")

openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
st.sidebar.write("Enter credentials and refresh the app.")

# Function to query historical data from InfluxDB
def query_historical_data():
    query = f"""
    SELECT status, time
    FROM {influxdb_bucket}
    WHERE time > now() - 7d
    """
    with InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org) as client:
        tables = client.query_api().query(query)
        data = []
        for table in tables:
            for record in table.records:
                data.append({"time": record.get_time(), "status": record.get_value()})
        return pd.DataFrame(data)

# Function to query the current status
def query_current_status():
    query = f"""
    SELECT status
    FROM {influxdb_bucket}
    ORDER BY time DESC
    LIMIT 1
    """
    with InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org) as client:
        tables = client.query_api().query(query)
        for table in tables:
            for record in table.records:
                return record.get_value()

# Function to analyze habit patterns with an LLM
def analyze_patterns(data):
    prompt = f"""
    Here is a dataset of status patterns by minute:\n{data}\n
    Please analyze the patterns and provide recommendations for optimization.
    """
    openai.api_key = openai_api_key
    response = ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an expert data analyst."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message["content"]

# Main application logic
if influxdb_url and influxdb_token and influxdb_org and influxdb_bucket:
    # Query historical data
    historical_data = query_historical_data()

    if not historical_data.empty:
        # Process data for visualization
        historical_data["time"] = pd.to_datetime(historical_data["time"])
        historical_data["minute"] = historical_data["time"].dt.floor("T")
        aggregated_data = historical_data.groupby(["minute", "status"]).size().reset_index(name="count")
        aggregated_data = aggregated_data.pivot(index="minute", columns="status", values="count").fillna(0)

        # Plot stacked bar chart
        st.subheader("Historical Status Distribution")
        fig = px.bar(
            aggregated_data,
            x=aggregated_data.index,
            y=aggregated_data.columns,
            title="Status by Minute",
            labels={"minute": "Time", "value": "Count", "variable": "Status"},
        )
        st.plotly_chart(fig)

        # Analyze patterns using LLM
        if openai_api_key:
            st.subheader("Recommendations")
            recommendations = analyze_patterns(aggregated_data.to_csv())
            st.write(recommendations)

    else:
        st.warning("No historical data available.")

    # Query and display the current status
    st.subheader("Current Status")
    current_status = query_current_status()
    if current_status:
        st.success(f"Current Status: {current_status}")
    else:
        st.warning("No current status available.")
else:
    st.error("Please provide all required InfluxDB credentials.")