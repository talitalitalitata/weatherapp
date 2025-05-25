from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import matplotlib
import xarray as xr
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import matplotlib.animation as animation
import matplotlib.dates as mdates
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
import tempfile
import os
import datetime
import pandas as pd
from pathlib import Path

app = FastAPI()

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a directory for static files (for sharing visualizations)
STATIC_DIR = Path("static_maps")
STATIC_DIR.mkdir(exist_ok=True)

# Mount static directory
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Load dataset - fixed path syntax
ds = xr.open_dataset("D:/WeatherApp/myweatherapp/wrfindo_04032025.nc")

# Convert time to datetime objects and extract hours
time_values = []
for t in ds['time'].values:
    dt = pd.to_datetime(t)
    time_values.append(f"{dt.hour:02d}:00")

# Endpoint root (untuk cek apakah backend hidup)
@app.get("/")
def read_root():
    return {"message": "FastAPI backend is running!"}

# Endpoint untuk mendapatkan informasi waktu
@app.get("/time-info")
def get_time_info():
    return {
        "times": time_values,
        "date": "04/03/2025"
    }

# Fungsi setup peta dasar
def setup_base_map(ax, lon, lat):
    ax.set_extent([lon.min(), lon.max(), lat.min(), lat.max()], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.LAND, facecolor='lightgray', edgecolor='black')
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.5)
    ax.add_feature(cfeature.LAKES, facecolor='lightblue')
    ax.add_feature(cfeature.RIVERS)

# Map parameter names to display names
parameter_labels = {
    'rain': 'Curah Hujan',
    'pm25': 'PM2.5',
    'no2': 'NO₂',
    'o3': 'O₃',
    'u10': 'U10 (Angin Barat-Timur)',
    'v10': 'V10 (Angin Utara-Selatan)',
    'wind_vector': 'Vektor Angin'
}

# Endpoint untuk gambar statis
@app.get("/static-image")
def get_static_image(parameter: str, time_index: int = 0, include_wind: bool = False):
    lon = ds['lon'].values
    lat = ds['lat'].values
    lon2d, lat2d = np.meshgrid(lon, lat)
    
    # Handle special case for wind vector
    if parameter == "wind_vector":
        u = ds['u10'][time_index, 0, :, :].values
        v = ds['v10'][time_index, 0, :, :].values
        data = np.sqrt(u**2 + v**2)  # Calculate wind speed
    else:
        data = ds[parameter][time_index, 0, :, :].values

    fig = plt.figure(figsize=(13, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())
    setup_base_map(ax, lon, lat)
    
    # Add data visualization
    cmap = 'Blues' if parameter == 'rain' else 'viridis'
    contour = ax.contourf(lon2d, lat2d, data, cmap=cmap, transform=ccrs.PlateCarree(), alpha=0.8)
    cbar = plt.colorbar(contour, ax=ax, orientation='vertical', pad=0.02)
    cbar.set_label(parameter_labels.get(parameter, parameter.upper()))
    
    # Overlay wind vectors if requested
    if include_wind and parameter != "wind_vector":
        step = 5  # Skip factor for quiver plot
        lon_skip = lon2d[::step, ::step]
        lat_skip = lat2d[::step, ::step]
        
        u = ds['u10'][time_index, 0, :, :].values
        v = ds['v10'][time_index, 0, :, :].values
        u_skip = u[::step, ::step]
        v_skip = v[::step, ::step]
        
        ax.quiver(
            lon_skip, lat_skip, u_skip, v_skip,
            transform=ccrs.PlateCarree(), color='black', scale=700,
            regrid_shape=20, width=0.0025, alpha=0.7
        )
    
    # Add timestamp and date
    time_str = time_values[time_index] if time_index < len(time_values) else f"Time {time_index}"
    param_title = parameter_labels.get(parameter, parameter.upper())
    ax.set_title(f"{param_title} - 04/03/2025 {time_str}")
    
    # Add watermark
    plt.figtext(0.01, 0.01, "WRF Indonesia Weather Visualization", fontsize=8)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig.savefig(tmp.name, bbox_inches='tight', dpi=150)
    plt.close(fig)
    return FileResponse(tmp.name, media_type="image/png", filename=f"{parameter}_{time_index}.png")

# Endpoint untuk animasi parameter
@app.get("/parameter-animation")
def get_parameter_animation(parameter: str, include_wind: bool = False):
    lon = ds['lon'].values
    lat = ds['lat'].values
    lon2d, lat2d = np.meshgrid(lon, lat)
    time_len = len(ds['time'])
    
    step = 5  # Skip factor for quiver plot
    lon_skip = lon2d[::step, ::step]
    lat_skip = lat2d[::step, ::step]

    fig = plt.figure(figsize=(13, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())
    
    # Select appropriate colormap
    cmap = 'Blues' if parameter == 'rain' else 'viridis'
    
    def animate(i):
        ax.clear()
        setup_base_map(ax, lon, lat)
        
        # Plot main parameter
        if parameter == "wind_vector":
            u = ds['u10'][i, 0, :, :].values
            v = ds['v10'][i, 0, :, :].values
            data = np.sqrt(u**2 + v**2)  # Calculate wind speed
        else:
            data = ds[parameter][i, 0, :, :].values
        
        contour = ax.contourf(
            lon2d, lat2d, data, cmap=cmap,
            transform=ccrs.PlateCarree(), alpha=0.8
        )
        
        # Overlay wind vectors if requested
        if include_wind or parameter == "wind_vector":
            u = ds['u10'][i, 0, :, :].values
            v = ds['v10'][i, 0, :, :].values
            u_skip = u[::step, ::step]
            v_skip = v[::step, ::step]
            
            ax.quiver(
                lon_skip, lat_skip, u_skip, v_skip,
                transform=ccrs.PlateCarree(), 
                color='black' if parameter != "wind_vector" else 'white',
                scale=700, regrid_shape=20, width=0.0025, alpha=0.7
            )
        
        # Add timestamp
        time_str = time_values[i] if i < len(time_values) else f"Frame {i+1}"
        param_title = parameter_labels.get(parameter, parameter.upper())
        ax.set_title(f"{param_title} - 04/03/2025 {time_str}")
        
        # Add watermark
        plt.figtext(0.01, 0.01, "WRF Indonesia Weather Visualization", fontsize=8)
        
        return [contour]

    # Create animation with all time steps
    ani = animation.FuncAnimation(fig, animate, frames=time_len, interval=300)
    
    # Save animation as GIF
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".gif")
    ani.save(tmp.name, writer='pillow', dpi=120)
    plt.close(fig)
    
    return FileResponse(tmp.name, media_type="image/gif", filename=f"{parameter}_animation.gif")

# Endpoint untuk membuat dan menyimpan peta statis untuk berbagi
@app.get("/create-shareable-map")
def create_shareable_map(parameter: str, time_index: int = 0, include_wind: bool = False):
    lon = ds['lon'].values
    lat = ds['lat'].values
    lon2d, lat2d = np.meshgrid(lon, lat)
    
    # Handle special case for wind vector
    if parameter == "wind_vector":
        u = ds['u10'][time_index, 0, :, :].values
        v = ds['v10'][time_index, 0, :, :].values
        data = np.sqrt(u**2 + v**2)  # Calculate wind speed
    else:
        data = ds[parameter][time_index, 0, :, :].values

    fig = plt.figure(figsize=(13, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())
    setup_base_map(ax, lon, lat)
    
    # Add data visualization
    cmap = 'Blues' if parameter == 'rain' else 'viridis'
    contour = ax.contourf(lon2d, lat2d, data, cmap=cmap, transform=ccrs.PlateCarree(), alpha=0.8)
    cbar = plt.colorbar(contour, ax=ax, orientation='vertical', pad=0.02)
    cbar.set_label(parameter_labels.get(parameter, parameter.upper()))
    
    # Overlay wind vectors if requested
    if include_wind and parameter != "wind_vector":
        step = 5  # Skip factor for quiver plot
        lon_skip = lon2d[::step, ::step]
        lat_skip = lat2d[::step, ::step]
        
        u = ds['u10'][time_index, 0, :, :].values
        v = ds['v10'][time_index, 0, :, :].values
        u_skip = u[::step, ::step]
        v_skip = v[::step, ::step]
        
        ax.quiver(
            lon_skip, lat_skip, u_skip, v_skip,
            transform=ccrs.PlateCarree(), color='black', scale=700,
            regrid_shape=20, width=0.0025, alpha=0.7
        )
    
    # Add timestamp and date
    time_str = time_values[time_index] if time_index < len(time_values) else f"Time {time_index}"
    param_title = parameter_labels.get(parameter, parameter.upper())
    ax.set_title(f"{param_title} - 04/03/2025 {time_str}")
    
    # Add watermark
    plt.figtext(0.01, 0.01, "WRF Indonesia Weather Visualization", fontsize=8)
    
    # Generate unique filename
    filename = f"{parameter}_{time_index}_{int(datetime.datetime.now().timestamp())}.png"
    filepath = STATIC_DIR / filename
    
    # Save the map
    fig.savefig(filepath, bbox_inches='tight', dpi=150)
    plt.close(fig)
    
    # Return the URL for sharing
    share_url = f"/static/{filename}"
    return {"success": True, "share_url": share_url}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

 
#uvicorn myweatherapp.src.main:app --reload
   