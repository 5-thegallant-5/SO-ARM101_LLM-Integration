import serial
import struct
import argparse
import sys

class BusServoController:
    """Controller for Waveshare/Feetech serial bus servos (ST/SC/STS series). Handles low-level packet send/receive."""
    def __init__(self, port: str, baud: int = 1000000, timeout: float = 0.1):
        """Open serial port to the bus servo adapter."""
        self.ser = serial.Serial(port, baudrate=baud, timeout=timeout)
    
    def _checksum(self, data_bytes: bytes) -> int:
        """Calculate checksum: ~((sum of data_bytes) & 0xFF)."""
        total = sum(data_bytes) & 0xFF
        return (~total) & 0xFF
    
    def send_packet(self, servo_id: int, instruction: int, params: bytes = b''):
        """Build and send a command packet to the servo bus."""
        # Packet format: 0xFF 0xFF [ID] [LENGTH] [INSTRUCTION] [...PARAMS...] [CHECKSUM]
        length = len(params) + 2  # includes instruction and checksum
        packet = bytes([servo_id, length, instruction]) + params
        checksum = self._checksum(packet)
        # Prepend header and append checksum
        full_packet = b'\xFF\xFF' + packet + bytes([checksum])
        self.ser.write(full_packet)
    
    def read_packet(self, expected_length: int) -> bytes:
        """Read a response packet from the serial. expected_length is the number of bytes to read."""
        data = self.ser.read(expected_length)
        return data
    
    def ping(self, servo_id: int) -> bool:
        """Ping a servo ID. Returns True if the servo responds (i.e., is present)."""
        self.send_packet(servo_id, 0x01)  # 0x01 = PING instruction
        response = self.read_packet(6)    # Expect 6 bytes: 0xFF 0xFF ID 0x02 ERROR CHECKSUM
        if response and len(response) >= 6:
            if response[0] == 0xFF and response[1] == 0xFF and response[2] == servo_id:
                # Verify checksum of ID, LENGTH, ERROR
                resp_id, length, error, checksum = response[2], response[3], response[4], response[5]
                calc = self._checksum(bytes([resp_id, length, error]))
                return calc == checksum
        return False
    
    def scan_servos(self, max_id: int = 253) -> list:
        """Scan the bus for all servos from ID 1 up to max_id. Returns list of IDs found."""
        found = []
        for sid in range(1, max_id+1):
            if self.ping(sid):
                found.append(sid)
        return found
    
    def set_position(self, servo_id: int, angle_deg: float, time_ms: int = 0, speed: int = 0, acceleration: int = None):
        """Move servo to the specified angle (0–360°). Optionally specify time (ms), speed, and acceleration."""
        # Clamp and convert angle to 0–4095 position units
        if angle_deg < 0: angle_deg = 0
        if angle_deg > 360: angle_deg = 360
        pos_val = int(angle_deg / 360.0 * 4096) & 0xFFF  # 12-bit position
        if pos_val > 4095: pos_val = 4095  # just in case angle=360 gives 4096, wrap to 4095
        
        # Prepare motion parameters
        time_val = 0 if time_ms is None else int(time_ms)
        if time_val < 0: time_val = 0
        if time_val > 65535: time_val = 65535  # 16-bit limit
        
        speed_val = 0 if speed is None else int(speed)
        if speed_val < 0: speed_val = 0
        if speed_val > 1023: speed_val = 1023  # 10-bit limit (0–1023)
        
        # Pack parameters into little-endian bytes
        if acceleration is not None:
            acc_val = int(acceleration) & 0xFF  # 8-bit
            params = struct.pack('<H H H B', pos_val, time_val, speed_val, acc_val)
        else:
            params = struct.pack('<H H H', pos_val, time_val, speed_val)
        # 0x03 = WRITE instruction
        self.send_packet(servo_id, 0x03, params)
        # (No status response expected for a normal write when error = 0)
    
    def _read_bytes(self, servo_id: int, start_addr: int, length: int) -> bytes:
        """Helper to read `length` bytes from servo's memory starting at `start_addr`."""
        params = bytes([start_addr, length])
        self.send_packet(servo_id, 0x02, params)  # 0x02 = READ
        # Response length = 6 (header+id+len+error+cksum) + data length
        resp = self.read_packet(6 + length)
        if not resp or len(resp) < 6+length:
            return b''
        # Basic validation: header and id
        if resp[0] == 0xFF and resp[1] == 0xFF and resp[2] == servo_id:
            # Verify checksum over ID, Length, Error, Data...
            data_section = resp[2: (2+ (resp[3]))]  # resp[3] is length (error+data bytes)
            # Note: resp[3] = length = error(1) + data(length) + checksum(1). So data bytes = resp[3] - 2.
            checksum = resp[ (2 + resp[3]) ]  # last byte
            calc = self._checksum(data_section)
            if calc == checksum:
                # Data bytes are resp[5] up to resp[... second last]
                return resp[5: 5+length]
        return b''
    
    def read_position(self, servo_id: int) -> float:
        """Read current position (angle in degrees) from servo."""
        data = self._read_bytes(servo_id, start_addr=0x38, length=2)
        if data:
            pos_val = data[0] | (data[1] << 8)  # little-endian
            # Convert to degrees (0-360)
            return (pos_val * 360.0 / 4096.0)
        return None
    
    def read_speed(self, servo_id: int) -> int:
        """Read current speed of servo (raw units)."""
        data = self._read_bytes(servo_id, start_addr=0x3A, length=2)
        if data:
            speed_val = data[0] | (data[1] << 8)
            # Mask to 10 bits (0–1023). Bit 10 might indicate direction (if protocol uses it).
            return speed_val & 0x3FF
        return None
    
    def read_load(self, servo_id: int) -> float:
        """Read current load of servo (percentage of max torque)."""
        data = self._read_bytes(servo_id, start_addr=0x3C, length=2)
        if data:
            load_val = data[0] | (data[1] << 8)
            load_val = load_val & 0x3FF  # 10-bit magnitude
            return load_val / 10.23  # scale to 0–100%
        return None
    
    def read_voltage(self, servo_id: int) -> float:
        """Read current supply voltage of servo (Volts)."""
        data = self._read_bytes(servo_id, start_addr=0x3E, length=1)
        if data:
            volt_val = data[0]
            return volt_val / 10.0  # e.g. 75 -> 7.5 V
        return None
    
    def read_temperature(self, servo_id: int) -> int:
        """Read current temperature of servo (°C)."""
        data = self._read_bytes(servo_id, start_addr=0x3F, length=1)
        if data:
            return data[0]  # temperature in Celsius
        return None
    
    def close(self):
        """Close the serial port."""
        self.ser.close()

# --- Command-line interface ---

parser = argparse.ArgumentParser(description="Control and monitor SO-ARM100/101 bus servos via Waveshare adapter")
parser.add_argument('-p', '--port', required=True, help="Serial port device (e.g. /dev/ttyACM0 or /dev/ttyUSB0)")
subparsers = parser.add_subparsers(dest="command", required=True)

# 'scan' command
subparsers.add_parser('scan', help="Scan the bus and list connected servos")

# 'move' command
move_parser = subparsers.add_parser('move', help="Move a servo to a given angle")
move_parser.add_argument('-i', '--id', type=int, required=True, help="Target servo ID")
move_parser.add_argument('-a', '--angle', type=float, required=True, help="Target angle in degrees (0-360)")
move_parser.add_argument('-t', '--time', type=int, default=0, help="Move duration in milliseconds (0 for immediate)")
move_parser.add_argument('-s', '--speed', type=int, default=0, help="Speed limit (0 for max speed)")
move_parser.add_argument('--acc', type=int, default=None, help="Acceleration value 0-255 (optional, STS servos only)")

# 'read' command
read_parser = subparsers.add_parser('read', help="Read real-time status from a servo")
read_parser.add_argument('-i', '--id', type=int, required=True, help="Target servo ID")

args = parser.parse_args()

# Instantiate controller
try:
    controller = BusServoController(args.port)
except Exception as e:
    print(f"Error: Could not open port {args.port} - {e}")
    sys.exit(1)

if args.command == 'scan':
    ids = controller.scan_servos()
    if ids:
        print("Servos detected on bus IDs:", ids)
    else:
        print("No servos found.")
elif args.command == 'move':
    controller.set_position(args.id, args.angle, time_ms=args.time, speed=args.speed, acceleration=args.acc)
    print(f"Commanded servo {args.id} to {args.angle} degrees.")
elif args.command == 'read':
    pos = controller.read_position(args.id)
    spd = controller.read_speed(args.id)
    load = controller.read_load(args.id)
    volt = controller.read_voltage(args.id)
    temp = controller.read_temperature(args.id)
    if pos is None:
        print(f"Servo {args.id} did not respond.")
    else:
        print(f"Servo {args.id} Angle: {pos:.1f} deg")
        if spd is not None:
            print(f"Servo {args.id} Speed: {spd} (raw)")
        if load is not None:
            print(f"Servo {args.id} Load: {load:.1f}%")
        if volt is not None:
            print(f"Servo {args.id} Voltage: {volt:.1f} V")
        if temp is not None:
            print(f"Servo {args.id} Temperature: {temp} °C")

controller.close()
