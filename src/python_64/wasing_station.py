import time
from move_to_locations import PumpESP32

# Device settings (same as main.py)
ESP32_PORT = "COM11"  # Updated to match all_cells_with_wash.py
ESP32_BAUD = 115200   # Updated to match all_cells_with_wash.py
PUMP_VIRTUAL = False             # Set to False for actual hardware
# Updated timing for new washing sequence: 10s pump + 60s DC motor + 15s rinse = 85s total
WASH1_WAIT = 85  # Total time for new sequence
WASH2_WAIT = 85
WASH3_WAIT = 85

def wash1_pump_only(pump: PumpESP32):
    """
    Run washing station 1 pump sequence only (no CNC movement)
    """
    print("[WASH1] start")
    pump.send_tag(b"1")
    time.sleep(WASH1_WAIT)

def wash2_pump_only(pump: PumpESP32):
    """
    Run washing station 2 pump sequence only (no CNC movement)
    """
    print("[WASH2] start")
    pump.send_tag(b"2")
    time.sleep(WASH2_WAIT)

def wash3_pump_only(pump: PumpESP32):
    """
    Run washing station 3 pump sequence only (no CNC movement) 
    """
    print("[WASH3] start")
    pump.send_tag(b"3")
    time.sleep(WASH3_WAIT)

def run_wash_sequence():
    """
    Run the pump washing sequence (pump control only):
    - wash1 pump sequence
    - wash2 pump sequence  
    - wash3 pump sequence
    """
    
    # Initialize pump controller
    pump = PumpESP32(port=ESP32_PORT, baud=ESP32_BAUD, virtual=PUMP_VIRTUAL)
    
    try:
        pump.open()
        print("[WASHING] Starting pump wash sequence...")
        
        # Pump-only wash sequence
        wash1_pump_only(pump)
        wash2_pump_only(pump) 
        wash3_pump_only(pump)
        
        print("[WASHING] All wash stations completed")
        
    except Exception as e:
        print(f"[WASHING ERROR] {e}")
        # Emergency stop in case of error
        try:
            pump.send_tag(b"0")
        except:
            pass
        
    finally:
        # Clean up connections
        try:
            pump.close()
        except:
            pass
        print("[WASHING] Sequence completed")

def run_single_wash_station(station_num: int):
    """
    Run a single wash station pump sequence (1, 2, or 3)
    """
    if station_num not in [1, 2, 3]:
        print("Error: Station number must be 1, 2, or 3")
        return
        
    pump = PumpESP32(port=ESP32_PORT, baud=ESP32_BAUD, virtual=PUMP_VIRTUAL)
    
    try:
        pump.open()
        print(f"[WASHING] Starting wash station {station_num}...")
        
        if station_num == 1:
            wash1_pump_only(pump)
        elif station_num == 2:
            wash2_pump_only(pump)
        elif station_num == 3:
            wash3_pump_only(pump)
            
        print(f"[WASHING] Wash station {station_num} completed")
        
    except Exception as e:
        print(f"[WASHING ERROR] {e}")
        try:
            pump.send_tag(b"0")
        except:
            pass
        
    finally:
        try:
            pump.close()
        except:
            pass

def emergency_stop():
    """
    Emergency stop all pumps and motors
    """
    pump = PumpESP32(port=ESP32_PORT, baud=ESP32_BAUD, virtual=PUMP_VIRTUAL)
    
    try:
        pump.open()
        print("[EMERGENCY] Sending stop command...")
        pump.send_tag(b"0")
        time.sleep(1)
        print("[EMERGENCY] Stop command sent")
        
    except Exception as e:
        print(f"[EMERGENCY ERROR] {e}")
        
    finally:
        try:
            pump.close()
        except:
            pass

if __name__ == "__main__":
    print("=== Pump-Only Washing Station Controller ===")
    print("Available operations:")
    print("1. Run full pump wash sequence (wash1 -> wash2 -> wash3)")
    print("2. Run pump wash station 1") 
    print("3. Run pump wash station 2")
    print("4. Run pump wash station 3")
    print("9. Emergency stop all")
    print("0. Exit")
    
    while True:
        try:
            choice = input("\nEnter choice (1-4, 9 for stop, 0 to exit): ").strip()
            
            if choice == "1":
                run_wash_sequence()
            elif choice == "2":
                run_single_wash_station(1)
            elif choice == "3":
                run_single_wash_station(2)
            elif choice == "4":
                run_single_wash_station(3)
            elif choice == "9":
                emergency_stop()
            elif choice == "0":
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please enter 1-4, 9, or 0.")
                
        except KeyboardInterrupt:
            print("\n[INTERRUPT] Sending emergency stop...")
            emergency_stop()
            break
        except Exception as e:
            print(f"[ERROR] {e}")

# Simple function to run just washing station 1
def run_washing_station_1_only():
    """
    Direct execution of washing station 1 pump sequence only
    """
    pump = PumpESP32(port=ESP32_PORT, baud=ESP32_BAUD, virtual=PUMP_VIRTUAL)
    
    try:
        pump.open()
        print("[WASH1] Starting washing station 1...")
        wash1_pump_only(pump)
        print("[WASH1] Washing station 1 completed")
        
    except Exception as e:
        print(f"[WASH1 ERROR] {e}")
        try:
            pump.send_tag(b"0")
        except:
            pass
        
    finally:
        try:
            pump.close()
        except:
            pass

# Uncomment the line below to run washing station 1 directly
run_washing_station_1_only()
