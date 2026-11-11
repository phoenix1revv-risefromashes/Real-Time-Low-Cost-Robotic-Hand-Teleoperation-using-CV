import pyfirmata
import time

signal_pin = [9,10,11,12,13]

board = pyfirmata.Arduino("/dev/cu.usbmodem101") #selecting board

for i in signal_pin:
    board.digital[i].mode = pyfirmata.SERVO
    
def rotateServo(pin, angle):
    board.digital[pin].write(angle)
    return

# def rotateFinger():
#     status = 'r'
#     while(True):
                
#         if status == 'r':
#             for degree in range(0,90):
#                 rotateServo(9, degree)
#             status = input("at 90: type anykey for reverse: ")
#         else:
#             for degree in range(0,90, -1):
#                 rotateServo(9, degree)
#             status = input("at 0: type r for 90 rotation: ")
            

        
for degree in range(0,90):
    rotateServo(9, degree)
    
# time.sleep(1)

# degree = 90
# while(degree > 0):
#     rotateServo(9, degree)
#     degree = degree - 1
