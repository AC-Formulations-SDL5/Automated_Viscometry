# Viscometry Platform Web Interface

This web interface provides real-time monitoring and visualization for the automated viscometry platform.

## Features

- **Real-time Platform Map**: Visual representation of the 18-cell layout with live viscometer position tracking
- **Interactive Scatter Plot**: Real-time plotting of rotational drag vs height measurements
- **Status Dashboard**: Live monitoring of system status, current cell, RPM, and position
- **Data Export**: Export measurement data to CSV format
- **Responsive Design**: Works on desktop and mobile devices

## Setup

1. Install web interface dependencies:
```bash
pip install -r requirements_web.txt
```

2. Run the main analysis script:
```bash
python all_cells_with_rotational_drag_feedback.py
```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

## Interface Layout

### Header Banner
- **Left**: "Acceleration Consortium - Self-Driving Lab #5 - Formulation" and "Automated Viscometry Platform"
- **Right**: Laboratory logo

### Status Bar
- Real-time status message
- Current cell being tested
- Current RPM
- Viscometer position (X, Y, Z)
- Running/Stopped indicator

### Left Panel - Platform Map
- Visual representation of the 450mm x 400mm platform
- 18 sample cells arranged in 3 rows (6 cells each)
- 2 washing stations 
- Real-time viscometer position indicator
- Color-coded legend:
  - **Green circles**: Sample cells
  - **Blue circles**: Wash stations  
  - **Red circle**: Viscometer position
  - **Yellow circle**: Currently active cell

### Right Panel - Scatter Plot
- X-axis: Height (mm)
- Y-axis: Rotational Drag (Nm)
- Real-time data points colored by cell
- Interactive controls:
  - Show all cells / Current cell only
  - Clear data
  - Export data to CSV
- Data summary statistics

## Platform Configuration

### Cell Layout
- **Row 1**: Cells 1-6 (BASE_X = 10mm)
- **Row 2**: Cells 7-12 (BASE_X = 85mm) 
- **Row 3**: Cells 13-18 (BASE_X = 309mm)
- **Y-spacing**: 67mm between cells (BASE_Y = 62mm)

### Wash Stations
- **Station 1**: X=383mm, Y=68mm
- **Station 2**: X=383mm, Y=147mm

### Platform Boundaries
- **X-axis**: 0 to 450mm
- **Y-axis**: 0 to 400mm
- **Z-axis**: -75mm to 0mm

## Real-time Updates

The interface uses WebSockets for real-time communication:
- Position updates when CNC machine moves
- Measurement data as it's collected
- Status updates throughout the experiment
- RPM changes during measurements

## Data Export

Click "Export Data" to download a CSV file containing:
- Timestamp
- Cell ID
- Height (mm)
- Rotational Drag (Nm)
- RPM

## Troubleshooting

1. **Web interface doesn't load**: Check that port 5000 is available
2. **No real-time updates**: Verify WebSocket connection in browser console
3. **Plot not showing**: Check browser JavaScript console for errors
4. **Logo not displaying**: Place logo file at `static/images/logo.png`

## Browser Compatibility

Tested with:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+