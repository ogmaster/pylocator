"""
Callbacks for the events browser functionality.
"""
from dash import Input, Output, State, callback, html
import requests

# These will be set by app.py
api_service_url = None

@callback(
    Output('events-table-container', 'children'),
    Input('load-events-button', 'n_clicks'),
    State('event-type-filter', 'value'),
    State('event-date-range', 'start_date'),
    State('event-date-range', 'end_date'),
)
def load_events(n_clicks, event_type, start_date, end_date):
    """Load and display event data."""
    global api_service_url
    
    if not n_clicks:
        return html.Div("Click 'Load Events' to view event data")
    
    try:
        if api_service_url:
            # Format dates
            start_time = f"{start_date}T00:00:00"
            end_time = f"{end_date}T23:59:59"
            
            # Build query parameters
            params = {
                'start': start_time,
                'end': end_time,
                'limit': 100
            }
            
            if event_type and event_type != 'all':
                params['event_type'] = event_type
            
            # Get events from API
            response = requests.get(f"{api_service_url}/events", params=params)
            
            if response.status_code == 200:
                events = response.json()
                
                if events:
                    # Create table
                    return html.Div([
                        html.H5(f"Found {len(events)} events"),
                        html.Table(
                            # Header
                            [html.Tr([html.Th(col) for col in ['Timestamp', 'Object ID', 'Event Type', 'Details']])] +
                            # Rows
                            [html.Tr([
                                html.Td(event.get('timestamp', '')),
                                html.Td(event.get('object_id', '')),
                                html.Td(event.get('event_type', '')),
                                html.Td(str(event.get('details', {})))
                            ]) for event in events],
                            className="table table-striped"
                        )
                    ])
                else:
                    return html.Div("No events found for the selected criteria")
    except Exception as e:
        return html.Div(f"Error loading events: {str(e)}")
    
    return html.Div("No events found") 