"""
Callbacks for the historical data functionality.
"""
from dash import Input, Output, State, callback
import plotly.graph_objects as go
import pandas as pd
import requests

# These will be set by app.py
object_store = None
api_service_url = None

@callback(
    Output('history-object-selector', 'options'),
    Input('interval-component', 'n_intervals')
)
def update_object_dropdown(n):
    """Update the dropdown with available objects."""
    global api_service_url, object_store
    
    try:
        # Get objects from API
        if api_service_url:
            response = requests.get(f"{api_service_url}/objects?limit=100")
            if response.status_code == 200:
                objects = response.json()
                options = [{'label': obj['_id'], 'value': obj['_id']} for obj in objects]
                return options
    except Exception as e:
        print(f"Error fetching objects for dropdown: {e}")
    
    # Fallback to local store
    if object_store:
        active_objects = object_store.get_active_objects()
        return [{'label': obj_id, 'value': obj_id} for obj_id in active_objects.keys()]
    
    return []

@callback(
    Output('history-plot', 'figure'),
    Input('load-history-button', 'n_clicks'),
    State('history-object-selector', 'value'),
    State('history-date-range', 'start_date'),
    State('history-date-range', 'end_date'),
    State('history-resolution', 'value'),
)
def load_object_history(n_clicks, object_id, start_date, end_date, resolution):
    """Load and display historical object data."""
    global api_service_url
    
    if not n_clicks or not object_id:
        return go.Figure()
    
    try:
        if api_service_url:
            # Format dates
            start_time = f"{start_date}T00:00:00"
            end_time = f"{end_date}T23:59:59"
            
            # Add interval parameter if not raw data
            interval_param = f"&interval={resolution}" if resolution != 'raw' else ""
            
            # Get history from API
            response = requests.get(
                f"{api_service_url}/objects/{object_id}/history?start={start_time}&end={end_time}{interval_param}"
            )
            
            if response.status_code == 200:
                history_data = response.json()
                
                # Convert to DataFrame
                df = pd.DataFrame(history_data)
                
                if not df.empty:
                    # Create figure
                    fig = go.Figure()
                    
                    # Add position trace
                    fig.add_trace(go.Scatter(
                        x=df['time'],
                        y=df['x'],
                        mode='lines+markers',
                        name='X Position'
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=df['time'],
                        y=df['y'],
                        mode='lines+markers',
                        name='Y Position'
                    ))
                    
                    # Update layout
                    fig.update_layout(
                        title=f"Position History for Object {object_id}",
                        xaxis_title="Time",
                        yaxis_title="Position",
                        legend_title="Coordinate",
                        hovermode="x unified"
                    )
                    
                    return fig
    except Exception as e:
        print(f"Error loading history: {e}")
    
    # Return empty figure if there's an error or no data
    return go.Figure().update_layout(
        title="No history data available for this selection"
    ) 