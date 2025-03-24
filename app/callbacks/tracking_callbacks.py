"""
Callbacks for the real-time tracking functionality.
"""
from dash import Input, Output, State, callback
import plotly.graph_objects as go
import dash
import requests
import time
from dash.dependencies import Input, Output
from dash import html

# Import object_store instance from main app
# This will be set by app.py
object_store = None
api_service_url = None  # Add this line to store API URL


@callback(
    Output('interval-component', 'interval'),
    Input('update-frequency', 'value')
)
def update_interval(value):
    """Updates the refresh interval based on selected frequency."""
    return (1000 / value)


@callback(
    Output('object-timeout', 'value'),
    Input('object-timeout', 'value')
)
def update_timeout(value):
    """Updates the object timeout in the store."""
    global object_store
    if object_store:
        object_store.timeout = value
    return value


@callback(
    Output('trail-length', 'disabled'),
    Input('show-trails', 'value')
)
def toggle_trail_length(show_trails):
    """Toggles the trail length slider based on show trails checkbox."""
    return 'show' not in show_trails


@callback(
    Output('tracking-plot', 'figure'),
    Input('interval-component', 'n_intervals'),
    Input('show-trails', 'value'),
    Input('trail-length', 'value'),
    Input('min-x', 'value'),
    Input('min-y', 'value'),
    Input('max-x', 'value'),
    Input('max-y', 'value'),
    Input('background-image-store', 'data'),
    Input('show-zones', 'value'),
)
def update_graph(n, show_trails, trail_length, min_x, min_y, max_x, max_y, bg_image, show_zones):
    """Updates the tracking plot with real-time data."""
    global object_store, api_service_url
    if not object_store:
        return go.Figure()
    
    # Create base figure
    fig = go.Figure()
    
    # Add background image if available
    if bg_image:
        # Add image as layout
        fig.add_layout_image(
            dict(
                source=bg_image,
                xref="x",
                yref="y",
                x=min_x,
                y=max_y,
                sizex=max_x - min_x,
                sizey=max_y - min_y,
                sizing="stretch",
                opacity=0.5,
                layer="below"
            )
        )
    
    # Add zones if enabled
    if 'show' in show_zones and api_service_url:
        try:
            response = requests.get(f"{api_service_url}/zones")
            if response.status_code == 200:
                zones = response.json()
                
                for zone in zones:
                    polygon = zone['polygon']
                    x_vals = [p['x'] for p in polygon]
                    y_vals = [p['y'] for p in polygon]
                    
                    # Close the polygon
                    x_vals.append(x_vals[0])
                    y_vals.append(y_vals[0])
                    
                    # Convert hex color to rgba for transparency
                    hex_color = zone.get('color', '#FF5733')
                    # Remove # if present
                    if hex_color.startswith('#'):
                        hex_color = hex_color[1:]
                    
                    # Convert hex to rgb
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    
                    # Create rgba string with 0.3 opacity
                    rgba_color = f'rgba({r},{g},{b},0.3)'
                    
                    fig.add_trace(go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        fill="toself",
                        fillcolor=rgba_color,  # Use rgba format
                        line=dict(color=f'rgb({r},{g},{b})'),
                        name=zone.get('name', 'Unnamed Zone'),
                        text=zone.get('description', ''),
                        hoverinfo='text',
                        showlegend=False,
                    ))
        except Exception as e:
            print(f"Error loading zones: {e}")
    
    # Get active objects
    active_objects = object_store.get_active_objects()
    
    # Plot points for each object
    x_vals = []
    y_vals = []
    ids = []
    
    for obj_id, data in active_objects.items():
        x_vals.append(data['x'])
        y_vals.append(data['y'])
        ids.append(obj_id)
    
    # Add scatter plot for current positions
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=y_vals,
        mode='markers',
        marker=dict(size=10),
        text=ids,
        name='Objects',
        customdata=ids,
        hoverinfo='text'
    ))
    
    # Add trails if enabled
    if 'show' in show_trails:
        trails = object_store.get_object_trails(max_trail_points=trail_length)
        
        for obj_id, trail in trails.items():
            if len(trail['x']) > 1:  # Only add trails with more than one point
                fig.add_trace(go.Scatter(
                    x=trail['x'],
                    y=trail['y'],
                    mode='lines',
                    line=dict(width=1, dash='dot'),
                    name=f"Trail-{obj_id}",
                    showlegend=False,
                    hoverinfo='none'
                ))
    
    # Update layout with boundary settings
    fig.update_layout(
        xaxis=dict(range=[min_x, max_x], title="X Position"),
        yaxis=dict(range=[min_y, max_y], title="Y Position"),
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=False,
        uirevision='constant',  # keeps zoom level consistent
        hovermode='closest',
    )
    
    return fig 

@callback(
    [Output('background-image-store', 'data'),
     Output('upload-output', 'children')],
    Input('upload-image', 'contents'),
    State('upload-image', 'filename')
)
def update_background(contents, filename):
    if contents is not None:
        # Return the image data and success message
        return contents, html.Div(f"Uploaded: {filename}")
    return dash.no_update, dash.no_update

@callback(
    Output('selected-object', 'data'),
    Input('tracking-plot', 'clickData')
)
def update_selected_object(clickData):
    if clickData:
        # Get the object ID from the clicked point
        point = clickData['points'][0]
        if 'customdata' in point:
            return point['customdata']
    return None

@callback(
    Output('object-details', 'children'),
    Input('selected-object', 'data'),
    Input('interval-component', 'n_intervals')
)
def display_object_details(obj_id, n):
    global object_store, api_service_url
    
    if not obj_id:
        return html.Div("Click on an object to see details")
    
    # Try to get API data
    try:
        if api_service_url:
            response = requests.get(f"{api_service_url}/objects/{obj_id}")
            zones_response = requests.get(f"{api_service_url}/objects/{obj_id}/zones?limit=5")
            
            details = []
            
            if response.status_code == 200:
                api_data = response.json()
                details.extend([
                    html.H5(f"Object ID: {obj_id}"),
                    html.P(f"Status: {api_data.get('status', 'Unknown')}"),
                    html.P(f"First Seen: {api_data.get('first_seen', 'Unknown')}"),
                    html.P(f"Last Position: ({api_data.get('last_position', {}).get('x', 0):.2f}, {api_data.get('last_position', {}).get('y', 0):.2f})"),
                    html.P(f"Last Update: {api_data.get('last_updated', 'Unknown')}"),
                ])
            
            # Add zone information
            if zones_response.status_code == 200:
                zone_events = zones_response.json()
                
                if zone_events:
                    # Find current zones (those with enter but no matching exit)
                    current_zones = set()
                    for event in reversed(zone_events):
                        if event['event_type'] == 'enter':
                            current_zones.add(event['zone_name'])
                        elif event['event_type'] == 'exit' and event['zone_name'] in current_zones:
                            current_zones.remove(event['zone_name'])
                    
                    if current_zones:
                        details.append(html.H6("Current Zones:"))
                        details.append(html.Ul([
                            html.Li(zone) for zone in current_zones
                        ]))
                    
                    details.append(html.H6("Recent Zone Activity:"))
                    details.append(html.Ul([
                        html.Li(f"{event['timestamp'].split('T')[1][:8]} - {event['event_type']} {event['zone_name']}")
                        for event in zone_events[:5]
                    ]))
            
            details.append(html.A("View All Zone Events", href="#", id=f"view-events-{obj_id}", 
                                  className="btn btn-sm btn-info"))
            
            return html.Div(details)
            
    except Exception as e:
        # Fallback to local store
        print(f"Error fetching object details: {e}")
    
    # Use local store as fallback
    active_objects = object_store.get_active_objects()
    if obj_id in active_objects:
        obj = active_objects[obj_id]
        return html.Div([
            html.H5(f"Object ID: {obj_id}"),
            html.P(f"Current Position: ({obj['x']:.2f}, {obj['y']:.2f})"),
            html.P(f"Last Update: {time.strftime('%H:%M:%S', time.localtime(obj['last_update']))}"),
            html.P(f"History Points: {len(obj['history'])}")
        ])
    else:
        return html.Div(f"Object {obj_id} is no longer active") 