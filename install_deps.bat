@echo off
echo Installing Interactive Albedo Dashboard Dependencies...
echo ============================================================

echo Activating glacier_dashboard environment...
call conda activate glacier_dashboard

echo.
echo Installing core packages via conda...
conda install -y plotly
conda install -y -c conda-forge pandas numpy scipy

echo.
echo Installing Dash packages via pip...
pip install dash==2.14.2
pip install dash-bootstrap-components==1.5.0
pip install dash-leaflet==0.1.23

echo.
echo Testing installation...
python -c "import dash, plotly, dash_bootstrap_components, dash_leaflet; print('All packages installed successfully!')"

echo.
echo ============================================================
echo Installation complete! You can now run:
echo python app.py
echo.
echo Or use the launcher:
echo python run_dashboard.py
echo ============================================================

pause