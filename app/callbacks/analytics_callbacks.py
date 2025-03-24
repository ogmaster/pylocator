"""
Callbacks for the analytics functionality.
"""
from dash import Input, Output, State, callback
import plotly.graph_objects as go
import numpy as np

# These will be set by app.py
object_store = None
api_service_url = None

@callback(
    Output('activity-heatmap', 'figure'),
    Input('generate-heatmap-button', 'n_clicks'),
    State('analytics-timeframe', 'value'),
    State('heatmap-resolution', 'value'),
)
def generate_activity_heatmap(n_clicks, timeframe, resolution):
    """Generate a heatmap of object activity."""
    global object_store
    
    if not n_clicks:
        return go.Figure()
    
    try:
        # Convert resolution to int
        grid_size = int(resolution)
        
        # Create empty grid
        heatmap_data = np.zeros((grid_size, grid_size))
        
        # Get active objects and populate heatmap
        if object_store:
            active_objects = object_store.get_active_objects()
            
            for obj_id, data in active_objects.items():
                # Get history points
                history = data['history']
                
                # Add each history point to the heatmap
                for point in history:
                    x, y, _ = point
                    # Convert x,y to grid coordinates
                    grid_x = min(grid_size-1, max(0, int(x / 100 * grid_size)))
                    grid_y = min(grid_size-1, max(0, int(y / 100 * grid_size)))
                    
                    # Increment count at this location
                    heatmap_data[grid_y, grid_x] += 1
            
            # Create heatmap figure
            fig = go.Figure(data=go.Heatmap(
                z=heatmap_data,
                x=np.linspace(0, 100, grid_size),
                y=np.linspace(0, 100, grid_size),
                colorscale='Viridis',
                hoverongaps=False,
                hoverinfo='x+y+z'
            ))
            
            fig.update_layout(
                title=f"Object Activity Heatmap ({timeframe} timeframe)",
                xaxis_title="X Position",
                yaxis_title="Y Position",
            )
            
            return fig
    except Exception as e:
        print(f"Error generating heatmap: {e}")
    
    return go.Figure().update_layout(
        title="Error generating heatmap"
    ) 