# Interactive Albedo Analysis Dashboard

A web-based interactive dashboard for analyzing and comparing glacier albedo measurements from MODIS satellite sensors against ground-based AWS (Automatic Weather Station) data.

## Features

### 🗺️ Interactive Map
- Display glacier locations and boundaries
- Show MODIS pixel locations with click selection
- AWS station markers with metadata
- Multi-pixel selection support
- Real-time pixel information display

### 📊 Comprehensive Visualizations
- **Scatter Plots**: MODIS vs AWS albedo comparison with trend lines
- **Time Series**: Temporal analysis of albedo values
- **Box Plots**: Statistical distribution comparison across methods
- **Histograms**: Albedo value distributions
- **Correlation Matrix**: Method comparison heatmaps
- **Statistical Tables**: Real-time calculation of RMSE, bias, correlation

### 🔧 Interactive Controls
- Glacier selection with data availability indicators
- MODIS method selection (MOD09GA, MOD10A1, MCD43A3)
- Date range filtering with data availability
- Pixel selection modes (All, Selected, Best)
- AWS data inclusion toggle
- Real-time analysis updates

### 📈 Analysis Capabilities
- Compare multiple MODIS albedo products
- Validate satellite data against ground measurements
- Statistical analysis with correlation, RMSE, bias calculations
- Pixel-level analysis and selection
- Temporal trend analysis
- Export functionality for data and visualizations

## Data Sources

### Glaciers Included
- **Athabasca Glacier** (Canadian Rockies) - 2 pixels
- **Haig Glacier** (Canadian Rockies) - 13 pixels  
- **Coropuna Glacier** (Peruvian Andes) - 197 pixels

### MODIS Products
- **MOD09GA**: Daily surface reflectance from Terra
- **MOD10A1**: Daily snow albedo from Terra
- **MCD43A3**: Daily albedo from Terra/Aqua combined

### Ground Data
- AWS (Automatic Weather Station) albedo measurements
- Daily time series data with gap-filling
- Co-located with glacier study sites

## Installation and Setup

### Prerequisites
- Python 3.8+
- Required packages (see requirements_dashboard.txt)

### Installation
1. Clone or copy the project files
2. Install dependencies:
   ```bash
   pip install -r requirements_dashboard.txt
   ```
3. Ensure data files are in the correct locations:
   ```
   data/
   ├── modis/
   │   ├── athabasca/
   │   ├── haig/
   │   └── coropuna/
   ├── aws/
   └── glacier_masks/
   ```

### Running the Dashboard
```bash
python app.py
```

The dashboard will be available at: http://127.0.0.1:8050

## Usage Guide

### Getting Started
1. **Select a Glacier**: Choose from the dropdown (availability indicators show data status)
2. **Choose Methods**: Select which MODIS products to analyze
3. **Select Pixels**: 
   - All pixels: Use all available data
   - Selected pixels: Click on map to choose specific pixels
   - Best pixels: Automatically select optimal pixels
4. **Set Date Range**: Filter temporal data range
5. **Update Analysis**: Click to refresh visualizations

### Navigation
- **Map & Selection Tab**: Interactive map and pixel selection
- **Scatter Analysis Tab**: MODIS vs AWS comparison plots
- **Time Series Tab**: Temporal trend analysis
- **Distributions Tab**: Box plots and histograms
- **Statistics Tab**: Correlation matrices and summary tables

### Tips
- Click on map pixels to select them for focused analysis
- Use the "Best Pixels" mode to automatically select pixels closest to AWS stations
- Export options available for both data and visualizations
- Real-time updates as you change selections

## Technical Architecture

### Core Components
- **Data Manager**: Interfaces with existing albedo analysis framework
- **Map Component**: Interactive Leaflet map with pixel selection
- **Plot Components**: Plotly-based interactive visualizations
- **Control Components**: User interface controls and filters
- **Layout Manager**: Responsive dashboard layout

### Integration
- Built on top of existing albedo analysis framework
- Uses Plotly Dash for web interface
- Integrates with pandas/geopandas data processing
- Real-time statistical calculations
- Efficient data caching and filtering

### Performance
- Caching system for large datasets
- Optimized for responsive interactions
- Memory-efficient data handling
- Progressive loading of visualizations

## Configuration

### Dashboard Settings
Edit `config/dashboard_config.yaml` to customize:
- Server settings (host, port, debug mode)
- Visualization parameters (colors, plot sizes)
- Analysis parameters (quality thresholds)
- Performance settings (cache timeout, data limits)

### Glacier Configuration
Edit `config/glacier_sites.yaml` to:
- Add new glaciers
- Update data file paths
- Modify AWS station coordinates
- Adjust analysis parameters per glacier

## Data Format

### MODIS Data
- CSV format with columns: pixel_id, date, method, albedo, latitude, longitude, glacier_fraction
- Multiple methods in single file supported
- Quality flags and metadata included

### AWS Data
- CSV format with columns: Time, Albedo
- Daily measurements with timestamps
- Gap-filled and quality controlled

### Spatial Data
- Glacier boundaries as shapefiles
- AWS station locations as point shapefiles
- Coordinate reference systems handled automatically

## Troubleshooting

### Common Issues
1. **Data not loading**: Check file paths in glacier_sites.yaml
2. **Map not displaying**: Verify pixel coordinates in MODIS data
3. **Analysis errors**: Check for required columns in data files
4. **Performance issues**: Use pixel selection for large datasets

### Debug Mode
Run with debug=True in dashboard_config.yaml for detailed error messages.

### Logging
Check console output for detailed processing information and error diagnostics.

## Export Capabilities

### Data Export
- CSV format for filtered datasets
- Statistical summaries
- Pixel selection information

### Visualization Export
- PNG images for plots
- HTML format for interactive plots
- High-resolution options available

## Future Enhancements

- Additional glaciers and datasets
- More statistical analysis methods
- Advanced pixel selection algorithms
- Batch processing capabilities
- API endpoints for programmatic access
- Mobile-responsive improvements

## Support

For technical issues or questions about the dashboard functionality, check the logs for detailed error information and verify data file formats and configurations.

## License

This dashboard integrates with the existing albedo analysis framework and follows the same licensing terms.