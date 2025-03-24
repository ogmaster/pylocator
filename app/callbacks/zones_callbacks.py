"""
Callbacks for the zone management functionality.
"""
from dash import Input, Output, State, callback, html
import plotly.graph_objects as go
import requests
import time
import dash_bootstrap_components as dbc
from dash import dcc

# These will be set by app.py
api_service_url = None

@callback(
    Output('zone-editor-plot', 'figure'),
    Input('interval-component', 'n_intervals'),
    Input('zone-list-container', 'children')
)
def update_zone_editor(n, zone_list):
    """Update the zone editor plot with current zones."""
    global api_service_url
    
    fig = go.Figure()
    
    # Set up the plot area
    fig.update_layout(
        xaxis=dict(range=[0, 100], title="X Position"),
        yaxis=dict(range=[0, 100], title="Y Position"),
        margin=dict(l=20, r=20, t=20, b=20),
        showlegend=True,
        uirevision='constant',  # keeps drawing state
    )
    
    # Try to get zones from API
    try:
        if api_service_url:
            response = requests.get(f"{api_service_url}/zones")
            if response.status_code == 200:
                zones = response.json()
                
                # Add each zone as a filled polygon
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
                    
                    # Create rgba string with 0.5 opacity
                    rgba_color = f'rgba({r},{g},{b},0.5)'
                    
                    fig.add_trace(go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        fill="toself",
                        fillcolor=rgba_color,  # Use rgba format
                        line=dict(color=f'rgb({r},{g},{b})'),  # Use rgb format for line
                        name=zone.get('name', 'Unnamed Zone'),
                        text=zone.get('description', ''),
                        customdata=[zone['_id']],
                    ))
    except Exception as e:
        print(f"Error loading zones: {e}")
    
    return fig

@callback(
    Output('zone-list-container', 'children'),
    Input('interval-component', 'n_intervals'),
    Input('save-zone-button', 'n_clicks'),
    Input('delete-zone-button', 'n_clicks')
)
def update_zone_list(n, save_clicks, delete_clicks):
    """Update the list of zones."""
    global api_service_url
    
    try:
        if api_service_url:
            response = requests.get(f"{api_service_url}/zones")
            if response.status_code == 200:
                zones = response.json()
                
                if zones:
                    # Create selectable list of zones
                    return [
                        html.Div([
                            html.Div(
                                f"{zone['name']}", 
                                style={
                                    "padding": "8px",
                                    "border-left": f"4px solid {zone.get('color', '#FF5733')}",
                                    "margin-bottom": "4px",
                                    "cursor": "pointer",
                                    "background-color": "#f8f9fa"
                                },
                                id=f"zone-item-{zone['_id']}",
                                className="zone-list-item"
                            )
                        ]) for zone in zones
                    ]
                else:
                    return html.Div("No zones defined yet")
    except Exception as e:
        return html.Div(f"Error loading zones: {str(e)}")

@callback(
    Output('save-zone-button', 'n_clicks'),
    Input('save-zone-button', 'n_clicks'),
    State('zone-name', 'value'),
    State('zone-description', 'value'),
    State('zone-color', 'value'),
    State('zone-editor-plot', 'relayoutData')
)
def save_zone(n_clicks, name, description, color, relayout_data):
    """Save a new zone."""
    global api_service_url

    if not n_clicks or not name:
        print(f"No clicks or name: {n_clicks}, {name}")
        return 0
    
    try:
        if api_service_url and relayout_data:
            print(f"Relayout data: {relayout_data}")
            
            # Extract polygon coordinates from relayoutData
            polygon = []
            
            # Check for shapes in relayoutData
            # In Plotly's relayoutData, shapes are defined with keys like 'shapes[0].path'
            shape_keys = [k for k in relayout_data.keys() if 'shapes' in k]
            
            if shape_keys:
                # Look for drawn paths
                path_keys = [k for k in shape_keys if 'path' in k]
                if path_keys:
                    # Get the latest path
                    path_key = sorted(path_keys)[-1]
                    path = relayout_data[path_key]
                    
                    # Parse SVG path
                    if path.startswith('M'):
                        parts = path.replace('M', '').replace('L', ' ').split()
                        
                        for i in range(0, len(parts), 2):
                            if i+1 < len(parts):
                                try:
                                    x = float(parts[i])
                                    y = float(parts[i+1])
                                    polygon.append({"x": x, "y": y})
                                except ValueError:
                                    continue
                
                # Look for rectangles if no paths were found
                if not polygon:
                    rect_x0 = next((relayout_data[k] for k in shape_keys if 'x0' in k), None)
                    rect_y0 = next((relayout_data[k] for k in shape_keys if 'y0' in k), None)
                    rect_x1 = next((relayout_data[k] for k in shape_keys if 'x1' in k), None)
                    rect_y1 = next((relayout_data[k] for k in shape_keys if 'y1' in k), None)
                    
                    if all([rect_x0, rect_y0, rect_x1, rect_y1]):
                        polygon = [
                            {"x": rect_x0, "y": rect_y0},
                            {"x": rect_x1, "y": rect_y0},
                            {"x": rect_x1, "y": rect_y1},
                            {"x": rect_x0, "y": rect_y1}
                        ]
            
            # If still no polygon, check if user manually edited coordinates
            if not polygon and 'shapes' in relayout_data:
                shapes = relayout_data['shapes']
                if shapes and isinstance(shapes, list) and len(shapes) > 0:
                    shape = shapes[-1]
                    if 'path' in shape:
                        # Similar parsing as above
                        path = shape['path']
                        parts = path.replace('M', '').replace('L', ' ').split()
                        
                        for i in range(0, len(parts), 2):
                            if i+1 < len(parts):
                                try:
                                    x = float(parts[i])
                                    y = float(parts[i+1])
                                    polygon.append({"x": x, "y": y})
                                except ValueError:
                                    continue
                    elif all(k in shape for k in ['x0', 'y0', 'x1', 'y1']):
                        # Rectangle
                        polygon = [
                            {"x": shape['x0'], "y": shape['y0']},
                            {"x": shape['x1'], "y": shape['y0']},
                            {"x": shape['x1'], "y": shape['y1']},
                            {"x": shape['x0'], "y": shape['y1']}
                        ]
            
            # Debugging information
            print(f"Extracted polygon: {polygon}")
            
            if not polygon:
                print("No polygon could be extracted from the drawing.")
                print("Try drawing a shape again or check the Dash/Plotly version.")
                return 0
            
            # Prepare zone data
            zone_data = {
                "name": name,
                "description": description,
                "color": color,
                "polygon": polygon
            }
            
            # Send to API
            response = requests.post(f"{api_service_url}/zones", json=zone_data)
            if response.status_code == 200:
                print(f"Zone saved successfully")
                return 0
            else:
                print(f"Zone not saved: {response.status_code}, {response.text}")
                return 0
    except Exception as e:
        print(f"Error saving zone: {e}")
        import traceback
        traceback.print_exc()
    
    return 0

@callback(
    Output('zone-event-filter', 'options'),
    Input('interval-component', 'n_intervals')
)
def update_zone_dropdown(n):
    """Update the zone dropdown options."""
    global api_service_url
    
    try:
        if api_service_url:
            response = requests.get(f"{api_service_url}/zones")
            if response.status_code == 200:
                zones = response.json()
                return [{"label": zone['name'], "value": zone['_id']} for zone in zones]
    except Exception as e:
        print(f"Error updating zone dropdown: {e}")
    
    return []

@callback(
    Output('zone-events-container', 'children'),
    Input('search-zone-events-button', 'n_clicks'),
    State('zone-event-filter', 'value'),
    State('object-event-filter', 'value'),
    State('event-type-zone-filter', 'value')
)
def search_zone_events(n_clicks, zone_id, object_id, event_type):
    """Search for zone events based on filters."""
    global api_service_url
    
    if not n_clicks:
        return html.Div("Select search criteria and click 'Search Events'")
    
    try:
        if api_service_url:
            # Build query parameters
            params = {}
            if zone_id:
                params['zone_id'] = zone_id
            if object_id:
                params['object_id'] = object_id
            if event_type and event_type != 'all':
                params['event_type'] = event_type
            
            # Get zone events from API
            response = requests.get(f"{api_service_url}/zone-events", params=params)
            print(f"zone events response: {response}")
            if response.status_code == 200:
                events = response.json()
                
                if events:
                    # Create zone name lookup
                    zones_response = requests.get(f"{api_service_url}/zones")
                    zones = {z['_id']: z['name'] for z in zones_response.json()} if zones_response.status_code == 200 else {}
                    
                    # Create table of events
                    return html.Div([
                        html.H5(f"Found {len(events)} events"),
                        html.Table(
                            # Header
                            [html.Tr([html.Th(col) for col in ['Time', 'Object', 'Zone', 'Event', 'Duration']])] +
                            # Rows
                            [html.Tr([
                                html.Td(event.get('timestamp', '').split('T')[1][:8]),
                                html.Td(event.get('object_id', '')),
                                html.Td(zones.get(event.get('zone_id', ''), event.get('zone_id', ''))),
                                html.Td(
                                    html.Span(
                                        event.get('event_type', ''),
                                        style={
                                            'background-color': '#d4edda' if event.get('event_type') == 'enter' else '#f8d7da',
                                            'padding': '2px 6px',
                                            'border-radius': '4px'
                                        }
                                    )
                                ),
                                html.Td(f"{event.get('duration', '-')} sec" if event.get('duration') else "-")
                            ]) for event in events],
                            className="table table-striped"
                        )
                    ])
                else:
                    return html.Div("No events found for the selected criteria")
    except Exception as e:
        return html.Div(f"Error searching events: {str(e)}")

@callback(
    Output('zone-form', 'children'),
    Input('zone-editor-plot', 'relayoutData'),
    State('zone-name', 'value'),
    State('zone-description', 'value'),
    State('zone-color', 'value')
)
def update_zone_form(relayout_data, name, description, color):
    """Update zone form with feedback on drawing status."""
    children = [
        html.Label("Zone Name:"),
        dcc.Input(id="zone-name", type="text", placeholder="Enter zone name", value=name, className="form-control"),
        html.Label("Description:"),
        dcc.Textarea(id="zone-description", placeholder="Enter description", value=description, className="form-control"),
        html.Label("Zone Color:"),
        dcc.Input(id="zone-color", type="color", value=color or "#FF5733", className="form-control"),
        html.Br(),
    ]
    
    # Add drawing status indicator
    has_shapes = False
    if relayout_data:
        shape_keys = [k for k in relayout_data.keys() if 'shapes' in k]
        has_shapes = len(shape_keys) > 0
    
    if has_shapes:
        children.append(html.Div("Shape detected! You can save this zone.", 
                                style={'color': 'green', 'margin': '10px 0'}))
    else:
        children.append(html.Div("Draw a shape on the map before saving.", 
                                style={'color': 'orange', 'margin': '10px 0'}))
    
    children.extend([
        dbc.Button("Save Zone", id="save-zone-button", color="primary"),
        dbc.Button("Delete Zone", id="delete-zone-button", color="danger", className="ml-2"),
        html.Br(),
        html.Hr(),
        html.H5("Defined Zones"),
        html.Div(id="zone-list-container")
    ])
    
    return children 