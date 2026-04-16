# 🧪 Viscometry Platform Web Interface - Complete Simulation

Perfect! I've created a complete simulation of your viscometry platform web interface. Here's everything you need to run it:

## 🎯 What You'll See

The simulation demonstrates your complete viscometry workflow:
- **Real-time viscometer movement** across the 18-cell platform
- **Live data plotting** of rotational drag vs height
- **Interactive platform map** showing current position and active cells
- **Complete washing sequences** at both wash stations
- **Professional lab interface** with your exact branding

## 🚀 Quick Start (3 Ways)

### 🔥 **Option 1: Super Easy (Windows)**
```bash
# Just double-click this file:
START_SIMULATION.bat
```

### 🎮 **Option 2: One Command**
```bash
python run_simulation.py
```

### 🌐 **Option 3: Auto-Open Browser**
```bash
python start_with_browser.py
```

## 📱 Access the Interface

Once running, the interface will be available at:
```
🌐 http://localhost:5000
```

## 🎬 What Happens During Simulation

### **Timeline (2 minutes total)**
```
0:00 ► Web interface starts
0:05 ► Simulation begins - Home to (0,0,0)
0:10 ► Cell 1 testing (Row 1) - 8 Z-levels × 5 RPMs
0:30 ► Wash sequence at both stations  
0:45 ► Cell 7 testing (Row 2) - 8 Z-levels × 5 RPMs
1:05 ► Wash sequence at both stations
1:20 ► Cell 13 testing (Row 3) - 8 Z-levels × 5 RPMs  
1:40 ► Final wash sequence
1:45 ► Return home - Complete! ✅
```

### **Live Updates You'll See**
- ✅ Viscometer position tracking (red dot moving on map)
- ✅ Active cell highlighting (yellow circle)  
- ✅ Real-time status updates
- ✅ Current RPM display
- ✅ Live data points appearing on scatter plot
- ✅ Position coordinates updating (X, Y, Z)

## 🗺️ Platform Layout (Exactly Your Setup)

```
Wash Station 1 (383, 68) ●
                          │
Row 3: ● ● ● ● ● ●       │  Wash Station 2 (383, 147) ●
       13 14 15 16 17 18  │
                          │
Row 2: ● ● ● ● ● ●       │  
       7  8  9 10 11 12   │
                          │
Row 1: ● ● ● ● ● ●       │
       1  2  3  4  5  6    │

Platform: 450mm × 400mm
Z-range: 0mm to -75mm
```

## 📊 Data Generated

The simulation creates realistic measurement data:
- **Rotational Drag**: Calculated from simulated torque/RPM
- **Height Steps**: Progressive Z-movements with -0.02mm increments  
- **Multiple RPMs**: 0.8, 1.0, 2.0, 5.0, 10.0 RPM per height
- **Noise**: Random variations simulate real sensor behavior
- **Export**: Download data as CSV with timestamp

## 🛠️ Troubleshooting

### **Port 5000 Already in Use**
```powershell
# Find and kill the process
netstat -ano | findstr :5000
taskkill /PID [PID_NUMBER] /F
```

### **Missing Dependencies**  
```bash
# Auto-install (already handled by run_simulation.py)
pip install flask flask-socketio eventlet
```

### **Can't See Interface**
- ✅ Check console shows "Web interface started successfully!"
- ✅ Manually open: http://localhost:5000
- ✅ Try different browser (Chrome, Firefox, Edge)
- ✅ Check Windows Firewall isn't blocking port 5000

## 📖 Static Demo Alternative

If the simulation doesn't work, view the static demo:
```bash
# Open this file in any web browser:
DEMO_INTERFACE.html
```

## 🎨 Interface Features

### **Header Banner**
- "Acceleration Consortium - Self-Driving Lab #5 - Formulation"
- "Automated Viscometry Platform"
- Custom laboratory logo

### **Status Dashboard**
- Current operation status
- Active cell number (1-18)  
- Current RPM (0-10)
- Live position (X, Y, Z coordinates)
- Running/Stopped indicator

### **Platform Map (Left Panel)**
- All 18 cells in correct positions
- 2 wash stations at your coordinates
- Real-time viscometer position (red circle)
- Active cell highlighted (yellow circle)
- Interactive hover tooltips

### **Scatter Plot (Right Panel)**  
- X-axis: Height (mm)
- Y-axis: Rotational Drag (Nm)
- Color-coded by cell number
- Real-time data streaming
- Export to CSV functionality
- Show all cells vs current only

## 🔧 Customization

Edit `simulate_viscometry.py` to modify:
```python
# Test different cells
demo_cells = [2, 5, 8, 11, 16]  # Any combination

# Adjust speed  
simulation_speed = 1.0  # Real-time
simulation_speed = 4.0  # 4x faster

# More RPM values
TEST_RPMS = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
```

## 🎓 Perfect For

- ✅ **Training** - Learn interface without hardware
- ✅ **Demos** - Show capabilities to colleagues  
- ✅ **Development** - Test interface changes safely
- ✅ **Documentation** - Generate screenshots/videos
- ✅ **Debugging** - Isolate software vs hardware issues

## 🎥 Recording a Demo

1. Start: `python run_simulation.py`
2. Open: http://localhost:5000  
3. Screen record the 2-minute simulation
4. Perfect demo video for presentations! 🎬

---

## 🚀 Ready? Let's Go!

**Start the simulation:**
```bash
python run_simulation.py
```

**Then open your browser to:**
```
http://localhost:5000
```

**You'll see your complete viscometry platform web interface in action!** 🧪✨

---

### 💡 Next Steps After Simulation

1. **Customize** the interface colors/layout in `static/css/style.css`
2. **Add features** by modifying `static/js/app.js`  
3. **Integrate** with real hardware by running `all_cells_with_rotational_drag_feedback.py`
4. **Deploy** to lab computer for production use

The simulation uses the **exact same interface** as your real experiment! 🎯