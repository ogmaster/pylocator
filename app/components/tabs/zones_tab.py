"""
Zone management tab component.
"""
import dash_bootstrap_components as dbc
from dash import dcc, html

def create_zone_management_tab():
    """Creates the zone management tab layout."""
    return dbc.Tab(label="Zone Management", children=[
        dbc.Row([
            dbc.Col([
                html.H4("Zone Definition"),
                html.P("Click on the map to create polygon zones. Double-click to complete a zone."),
                dcc.Graph(
                    id='zone-editor-plot',
                    style={'height': '60vh'},
                    config={
                        'displayModeBar': True,
                        'modeBarButtonsToAdd': ['drawrect', 'drawopenpath', 'eraseshape'],
                        'editable': True,
                        'edits': {
                            'shapePosition': True,
                            'annotationPosition': True
                        }
                    }
                ),
            ], width=8),
            dbc.Col([
                html.H4("Zone Properties"),
                html.Div(id="zone-form", children=[
                    html.Label("Zone Name:"),
                    dcc.Input(id="zone-name", type="text", placeholder="Enter zone name", className="form-control"),
                    html.Label("Description:"),
                    dcc.Textarea(id="zone-description", placeholder="Enter description", className="form-control"),
                    html.Label("Zone Color:"),
                    dcc.Input(id="zone-color", type="color", value="#FF5733", className="form-control"),
                    html.Br(),
                    dbc.Button("Save Zone", id="save-zone-button", color="primary"),
                    dbc.Button("Delete Zone", id="delete-zone-button", color="danger", className="ml-2"),
                    html.Br(),
                    html.Hr(),
                    html.H5("Defined Zones"),
                    html.Div(id="zone-list-container")
                ]),
            ], width=4),
        ]),
        dbc.Row([
            dbc.Col([
                html.H4("Zone Events"),
                dbc.Row([
                    dbc.Col([
                        html.Label("Zone:"),
                        dcc.Dropdown(id="zone-event-filter", placeholder="Select zone")
                    ], width=3),
                    dbc.Col([
                        html.Label("Object ID:"),
                        dcc.Input(id="object-event-filter", type="text", placeholder="Object ID", className="form-control")
                    ], width=3),
                    dbc.Col([
                        html.Label("Event Type:"),
                        dcc.Dropdown(
                            id="event-type-zone-filter",
                            options=[
                                {"label": "All", "value": "all"},
                                {"label": "Enter", "value": "enter"},
                                {"label": "Exit", "value": "exit"}
                            ],
                            value="all"
                        )
                    ], width=3),
                    dbc.Col([
                        dbc.Button("Search Events", id="search-zone-events-button", color="primary")
                    ], width=3, className="d-flex align-items-end")
                ]),
                html.Div(id="zone-events-container")
            ], width=12)
        ])
    ]) 