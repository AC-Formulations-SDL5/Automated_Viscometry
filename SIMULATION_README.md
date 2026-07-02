# Viscometry Platform Web Interface - SIMULATION GUIDE

This simulation allows you to see the web interface in action without the actual experiment hardware.

## 🚀 Quick Start Options

### Option 1: Automatic (Recommended)
**For Windows users:**
```bash
# Just double-click this file:
START_SIMULATION.bat
```

**For all users:**
```bash
python run_simulation.py
```

### Option 2: Manual Setup
```bash
# 1. Install dependencies
pip install flask==2.3.3 flask-socketio==5.3.6 eventlet==0.33.3

# 2. Run simulation
python simulate_viscometry.py
```

### Option 3: Static Demo
If the simulation doesn't work, you can view a static version:
```bash
# Open in any web browser:
DEMO_INTERFACE.html
```

## 📋 What the Simulation Shows

The simulation demonstrates a complete viscometry experiment workflow:

### 🎯 **Experiment Flow**
1. **Initialization**: Viscometer homes to (0,0,0)
2. **Cell Testing**: Tests 3 sample cells (one from each row)
3. **Z-Series**: 8 height steps per cell with decreasing Z
4. **Multi-RPM Testing**: 5 different RPM values at each height
5. **Washing**: Complete wash sequence after each cell
6. **Real-time Data**: Live measurement points plotted

### 📊 **Web Interface Features**

#### **Header Banner**
- Laboratory branding: "Acceleration Consortium - Self-Driving Lab #5"
- Professional layout with logo

#### **Status Dashboard** 
- Current operation status
- Active cell number
- Current RPM
- Live X,Y,Z position
- Running/stopped indicator

#### **Platform Map (Left Panel)**
- 18 cells arranged in 3 rows (6 cells each)
- 2 washing stations
- Real-time viscometer position (red dot)
- Active cell highlighted in yellow
- Interactive hover tooltips

#### **Scatter Plot (Right Panel)**
- Real-time plotting of Rotational Drag vs Height
- Color-coded by cell number
- Interactive controls (show all/current only)
- Data export functionality
- Live statistics

## 🎮 Simulation Parameters

```python
# Speed Control
simulation_speed = 2.0  # 2x faster than real experiment

# Test Configuration
demo_cells = [1, 7, 13]  # One cell from each row
TEST_RPMS = [0.8, 1.0, 2.0, 5.0, 10.0]  # Five RPM values
z_steps = 8  # Height levels per cell

# Platform Layout (matches your hardware)
ROWS = [
    {'row_number': 1, 'base_x': 10},    # Cells 1-6
    {'row_number': 2, 'base_x': 85},    # Cells 7-12  
    {'row_number': 3, 'base_x': 309}    # Cells 13-18
]

WASH_STATIONS = [
    {'id': 1, 'x': 383, 'y': 68},     # Station 1
    {'id': 2, 'x': 383, 'y': 147}     # Station 2
]
```

## 📱 Access the Interface

Once running, open your web browser to:
```
http://localhost:5000
```

The interface is responsive and works on:
- Desktop computers
- Tablets  
- Mobile phones

## 🔧 Troubleshooting

### Port Already in Use
```bash
# If port 5000 is busy, kill the process:
# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -ti:5000 | xargs kill
```

### Missing Dependencies
```bash
# Install individually if batch install fails:
pip install flask
pip install flask-socketio  
pip install eventlet
```

### Import Errors
```bash
# Make sure you're in the correct directory:
cd /path/to/visc_automated_workflow_V3
python simulate_viscometry.py
```

## 📊 Understanding the Data

### **Rotational Drag Calculation**
```python
rotational_drag = abs(torque_percent) / rpm
```

### **Simulated Data Characteristics**
- **Base Torque**: Increases with RPM (realistic motor behavior)
- **Height Effect**: Higher torque at lower Z positions (sample contact)
- **Noise**: Random variations simulate real sensor noise
- **Trends**: Progressive data accumulation shows hit-point detection

### **Platform Coordinates**
- **X-axis**: 0 to 450 mm (machine width)
- **Y-axis**: 0 to 400 mm (machine depth)  
- **Z-axis**: 0 to -75 mm (vertical travel)
- **Cell Spacing**: 67 mm between cells in Y direction

## 🎬 Simulation Timeline

```
0:00 - Web interface starts
0:05 - Simulation begins
0:05 - Home position (0,0,0)
0:10 - Cell 1 testing starts
0:30 - Cell 1 wash sequence
0:45 - Cell 7 testing starts  
1:05 - Cell 7 wash sequence
1:20 - Cell 13 testing starts
1:40 - Cell 13 wash sequence
1:45 - Return home, experiment complete
```

Total simulation time: ~2 minutes (vs ~20 minutes real experiment)

## 🔄 Customizing the Simulation

Edit `simulate_viscometry.py` to modify:

```python
# Test different cells
demo_cells = [2, 8, 14]  # Different cells

# Adjust simulation speed  
simulator.simulation_speed = 1.0  # Real-time speed

# More/fewer RPM tests
TEST_RPMS = [0.5, 1.0, 5.0, 10.0, 20.0]  # Add more RPMs

# Different Z-step count
while current_z >= max_z_travel and z_step < 12:  # More steps
```

## 📝 Real vs Simulation

| Feature | Real Experiment | Simulation |
|---------|----------------|------------|
| Duration | 15-30 minutes | 2 minutes |
| Data Points | ~200 per cell | ~40 per cell |
| Hardware | CNC + Viscometer | Software only |
| Measurements | Actual torque | Calculated values |
| Movement | Physical motion | Animated transitions |
| Errors | Hardware issues | None |

## 🎓 Educational Use

This simulation is perfect for:
- **Training**: Learn the interface without hardware
- **Development**: Test new features safely  
- **Demos**: Show capabilities to stakeholders
- **Debugging**: Isolate software vs hardware issues
- **Documentation**: Generate screenshots and videos

## 📹 Making a Demo Video

1. Start the simulation: `python run_simulation.py`
2. Open browser to `http://localhost:5000`
3. Screen record the 2-minute simulation
4. Shows complete workflow from start to finish

Perfect for presentations and documentation!

---

## 💡 Next Steps

After viewing the simulation:
1. **Install hardware dependencies** for real experiment
2. **Modify configuration** in `src/viscometry/run/settings.py`
3. **Test with real hardware** using the integrated web interface
4. **Customize interface** by editing CSS/JS files

The simulation uses the exact same web interface as the real experiment!