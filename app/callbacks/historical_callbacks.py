"""
Callbacks for the historical data functionality.
"""
from dash import Input, Output, State, callback
import plotly.graph_objects as go
import pandas as pd
import requests
import plotly.express as px
from dash.exceptions import PreventUpdate
import dash
from dash import html, dcc
import json

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
    Input('history-viz-type', 'value'),
    Input('load-history-button', 'n_clicks'),
    Input('movement-slider', 'value'),
    State('history-object-selector', 'value'),
    State('history-date-range', 'start_date'),
    State('history-date-range', 'end_date'),
    State('history-resolution', 'value'),
)
def update_viz_type(viz_type, n_clicks, slider_position, object_id, start_date, end_date, resolution):
    """Update visualization based on selected type and slider position."""
    if not n_clicks or not object_id:
        return go.Figure()
    
    try:
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
                fig = go.Figure()
                
                # Choose visualization based on type
                if viz_type == "trail":
                    # Calculate how many points to show based on slider position
                    if slider_position < 100:  # If slider is not at max
                        points_to_show = max(1, int(len(df) * slider_position / 100))
                        df_visible = df.iloc[:points_to_show]
                    else:
                        df_visible = df
                    
                    # Create smoother interpolation for animation
                    if len(df_visible) > 1:
                        # Determine the exact position based on fractional slider value
                        exact_point_index = len(df) * slider_position / 100
                        integer_part = int(exact_point_index)
                        fraction_part = exact_point_index - integer_part
                        
                        # Ensure we're not at the last point or beyond
                        if integer_part < len(df) - 1:
                            # Get the current point and next point for interpolation
                            current_point = df.iloc[integer_part]
                            next_point = df.iloc[integer_part + 1]
                            
                            # Calculate interpolated position
                            interp_x = current_point['x'] + fraction_part * (next_point['x'] - current_point['x'])
                            interp_y = current_point['y'] + fraction_part * (next_point['y'] - current_point['y'])
                            
                            # Save interpolated position for animation
                            current_interp_pos = (interp_x, interp_y)
                        else:
                            # At or beyond the last point
                            if integer_part >= len(df):
                                integer_part = len(df) - 1
                            current_interp_pos = (df.iloc[integer_part]['x'], df.iloc[integer_part]['y'])
                    else:
                        # Only one point, no interpolation
                        current_interp_pos = (df_visible['x'].iloc[0], df_visible['y'].iloc[0]) if not df_visible.empty else (0, 0)
                    
                    # Add sequential path trace (2D trail)
                    fig.add_trace(go.Scatter(
                        x=df_visible['x'],
                        y=df_visible['y'],
                        mode='lines+markers',
                        line=dict(
                            width=2,
                            color='rgba(50, 100, 200, 0.7)'
                        ),
                        marker=dict(
                            size=8,
                            color=df_visible.index,  # Color points by sequence
                            colorscale='Viridis',
                            showscale=True,
                            colorbar=dict(
                                title="Sequence",
                                tickvals=[0, len(df_visible)-1] if len(df_visible) > 1 else [0],
                                ticktext=["Start", "Current"] if len(df_visible) > 1 else ["Start"],
                                lenmode="fraction",
                                len=0.6,  # Make colorbar shorter
                                y=0,     # Move to bottom
                                yanchor="bottom"
                            ),
                            line=dict(width=1, color='DarkSlateGrey')
                        ),
                        text=[f"Time: {t}<br>Position: ({x:.2f}, {y:.2f})" 
                              for t, x, y in zip(df_visible['time'], df_visible['x'], df_visible['y'])],
                        hoverinfo='text',
                        name=f"Path of {object_id}"
                    ))
                    
                    # Add arrow markers to show direction
                    arrow_step = max(1, len(df_visible)//10)  # Adjust for fewer arrows
                    for i in range(0, len(df_visible)-1, arrow_step):
                        if i+1 < len(df_visible):
                            fig.add_annotation(
                                x=df_visible['x'].iloc[i],
                                y=df_visible['y'].iloc[i],
                                ax=df_visible['x'].iloc[i+1],
                                ay=df_visible['y'].iloc[i+1],
                                xref="x", yref="y",
                                axref="x", ayref="y",
                                showarrow=True,
                                arrowhead=2,
                                arrowsize=1,
                                arrowwidth=1,
                                arrowcolor="rgba(50, 100, 200, 0.7)"
                            )
                    
                    # Add start point
                    if len(df_visible) > 0:
                        fig.add_trace(go.Scatter(
                            x=[df_visible['x'].iloc[0]],
                            y=[df_visible['y'].iloc[0]],
                            mode='markers',
                            marker=dict(size=15, color='green', symbol='circle-open'),
                            name="Start"
                        ))
                    
                    # Add smoothly animated current position using interpolation
                    if len(df_visible) > 0:
                        # Add an animated marker at the interpolated position
                        fig.add_trace(go.Scatter(
                            x=[current_interp_pos[0]],
                            y=[current_interp_pos[1]],
                            mode='markers',
                            marker=dict(
                                size=16,
                                color='red',
                                symbol='diamond',
                                line=dict(width=2, color='black')
                            ),
                            name="Current Position",
                            hoverinfo='none'
                        ))
                    
                    # Add the full path in lighter color
                    if slider_position < 100 and len(df) > len(df_visible):
                        fig.add_trace(go.Scatter(
                            x=df['x'],
                            y=df['y'],
                            mode='lines',
                            line=dict(width=1, color='rgba(100, 100, 100, 0.2)'),
                            name="Full Path",
                            showlegend=True,
                        ))
                    
                    # Update layout
                    fig.update_layout(
                        title=f"Movement Path for Object {object_id}",
                        xaxis_title="X Position",
                        yaxis_title="Y Position",
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.2,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=50, b=100),  # Add more margin at the bottom
                        hovermode='closest',
                        # Make the plot square to avoid distortion
                        yaxis=dict(
                            scaleanchor="x",
                            scaleratio=1,
                        )
                    )
                    
                    # Add info about the current progress
                    if len(df_visible) > 0:
                        # Get exact time through interpolation if possible
                        if len(df) > 1:
                            exact_point_index = len(df) * slider_position / 100
                            integer_part = int(exact_point_index)
                            fraction_part = exact_point_index - integer_part
                            
                            if integer_part < len(df) - 1:
                                # Interpolate between timestamps if they are datetime objects
                                try:
                                    current_time = df['time'].iloc[integer_part]
                                    next_time = df['time'].iloc[integer_part + 1]
                                    # Just use the closest time point for display - interpolating time is complex
                                    current_time_str = current_time
                                except:
                                    current_time_str = df_visible['time'].iloc[-1] if not df_visible.empty else "N/A"
                            else:
                                current_time_str = df_visible['time'].iloc[-1] if not df_visible.empty else "N/A"
                        else:
                            current_time_str = df_visible['time'].iloc[-1] if not df_visible.empty else "N/A"
                        
                        progress_text = f"Showing {len(df_visible)} of {len(df)} points ({slider_position:.1f}%)"
                        
                        fig.add_annotation(
                            text=f"{progress_text}<br>Current Time: {current_time_str}<br>Position: ({current_interp_pos[0]:.2f}, {current_interp_pos[1]:.2f})",
                            xref="paper", yref="paper",
                            x=0.5, y=1.05, 
                            showarrow=False,
                            font=dict(size=12)
                        )
                
                elif viz_type == "heatmap":
                    # Create a heatmap of positions
                    x_range = [df['x'].min(), df['x'].max()]
                    y_range = [df['y'].min(), df['y'].max()]
                    
                    # Create 2D histogram
                    fig = px.density_heatmap(
                        df, x='x', y='y', 
                        nbinsx=50, nbinsy=50,
                        title=f"Position Density for Object {object_id}"
                    )
                    
                    # Improve layout
                    fig.update_layout(
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.2,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=50, b=100)
                    )
                
                elif viz_type == "position_time":
                    # Calculate how many points to show based on slider
                    if slider_position < 100:
                        points_to_show = max(1, int(len(df) * slider_position / 100))
                        df_visible = df.iloc[:points_to_show]
                    else:
                        df_visible = df
                    
                    # Create position vs time plot
                    fig.add_trace(go.Scatter(
                        x=df_visible['time'],
                        y=df_visible['x'],
                        mode='lines+markers',
                        name='X Position'
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=df_visible['time'],
                        y=df_visible['y'],
                        mode='lines+markers',
                        name='Y Position'
                    ))
                    
                    # Add current position marker
                    if len(df_visible) > 0:
                        last_time = df_visible['time'].iloc[-1]
                        fig.add_trace(go.Scatter(
                            x=[last_time, last_time],
                            y=[df_visible['x'].iloc[-1], df_visible['y'].iloc[-1]],
                            mode='markers',
                            marker=dict(size=10, color='red', symbol='star'),
                            name="Current Position"
                        ))
                    
                    # Update layout
                    fig.update_layout(
                        title=f"Position vs Time for Object {object_id}",
                        xaxis_title="Time",
                        yaxis_title="Position",
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.2,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(l=20, r=20, t=50, b=100),
                        hovermode='closest'
                    )
                
                return fig
    except Exception as e:
        print(f"Error updating visualization: {e}")
    
    return go.Figure().update_layout(
        title="No history data available for this selection"
    ) 

# Define state stores for animation
@callback(
    Output('movement-slider', 'max'),
    Output('movement-slider', 'marks'),
    Output('movement-slider', 'step'),
    Input('load-history-button', 'n_clicks'),
    State('history-object-selector', 'value'),
    State('history-date-range', 'start_date'),
    State('history-date-range', 'end_date'),
    State('history-resolution', 'value'),
)
def setup_slider(n_clicks, object_id, start_date, end_date, resolution):
    """Setup the slider based on available data points with finer step size."""
    if not n_clicks or not object_id:
        return 100, {}, 0.25
    
    try:
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
            
            # Get the number of points
            num_points = len(history_data)
            
            if num_points > 0:
                # Create marks for the slider - show some important percentages
                marks = {
                    0: '0%',
                    25: '25%',
                    50: '50%',
                    75: '75%',
                    100: '100%'
                }
                
                # Use a smaller step size for smoother animation
                return 100, marks, 0.25
    
    except Exception as e:
        print(f"Error setting up slider: {e}")
    
    # Default values with finer step size
    return 100, {0: '0%', 100: '100%'}, 0.25

# Update the animation interval for smoother movement
@callback(
    Output('movement-slider', 'value'),
    Input('play-button', 'n_clicks'),
    Input('pause-button', 'n_clicks'),
    Input('reset-button', 'n_clicks'),
    Input('interval-animation', 'n_intervals'),
    State('movement-slider', 'value'),
    State('playback-speed', 'value'),
    prevent_initial_call=True
)
def control_animation(play, pause, reset, n_intervals, current_value, speed):
    """Control the animation playback of the movement with smoother transitions."""
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return current_value
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'play-button':
        # Start animation - this will trigger the interval
        return current_value
    
    elif button_id == 'pause-button':
        # Pause animation - no change to value
        return current_value
    
    elif button_id == 'reset-button':
        # Reset to beginning
        return 0
    
    elif button_id == 'interval-animation':
        # Use smaller increments for smoother animation
        speed_factor = float(speed)
        # Smaller increment for smoother animation (0.5 instead of 1)
        increment = 0.25 * speed_factor
        new_value = current_value + increment
        
        # Stop at 100%
        if new_value > 100:
            return 100
        
        return new_value
    
    return current_value

# Add this to your layout in the historical_tab.py file:
# Just before the end of the animation-controls div
html.Div([
    dcc.Interval(
        id='interval-animation',
        interval=50,  # 100ms = 0.1 seconds
        n_intervals=0,
        disabled=True
    )
]),

# Control the interval based on play/pause
@callback(
    Output('interval-animation', 'disabled'),
    Input('play-button', 'n_clicks'),
    Input('pause-button', 'n_clicks'),
    Input('reset-button', 'n_clicks'),
    Input('movement-slider', 'value'),
    prevent_initial_call=True
)
def toggle_animation_interval(play, pause, reset, slider_value):
    """Enable or disable the animation interval."""
    ctx = dash.callback_context
    
    if not ctx.triggered:
        # Default: disabled
        return True
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'play-button':
        # Enable interval for animation
        return False
    
    elif button_id in ['pause-button', 'reset-button']:
        # Disable interval
        return True
    
    elif button_id == 'movement-slider' and slider_value >= 100:
        # Automatically stop when reaching the end
        return True
    
    # No change
    return dash.no_update 