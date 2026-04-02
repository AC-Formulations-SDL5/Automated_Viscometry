from cnc_controller import CNC_Machine

cnc = CNC_Machine()
cnc.home()

# # Washing Station 1 Location
# x_pos = 387
# y_pos = 68
# z_pos = -67
# cnc.move_to_point(x_pos, y_pos, z_pos, speed=500)