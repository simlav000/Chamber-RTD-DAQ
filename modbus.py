# modbus.py
import socket
import struct
import rtd_config


# This function computes the Modbus CRC16 checksum for a given sequence of
# bytes. CRC stands for cyclic redundancy check, 16 is the number of bits used
# in the verification. CRC16 is a way to detect errors in data transmission.
# The Modbus protocol appends this two-byte checksum to each message. This
# particular CRC16 uses a specific polynomial and bitwise operations. It
# ensures that the receiver can verify the integrity of the data received. The
# polynomial is a fixed magic number (0xA001) used in the bitwise math to
# generate a checksum. More info can be found at:
# https://www.sunshine2k.de/articles/coding/crc/understanding_crc.html
def crc16(data: bytes) -> bytes:
    crc = 0xFFFF
    # The following is the usual long division algorithm.
    for pos in data:
        crc ^= pos
        for _ in range(8):
            if (crc & 1):
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1

    # Pack the 16-bit CRC into two bytes, little-endian order (LSB first).
    return struct.pack('<H', crc)

# This function reads data from a TCP socket until a full Modbus response is
# received. Modbus responses vary in length, but we can use the byte count
# field to know the expected size. The function loops reading data chunks until
# the complete message is assembled or a timeout occurs.
def recv_full_response(sock, min_bytes=5, timeout=3) -> bytes:
    sock.settimeout(timeout)  # Set how long to wait before giving up
    data = bytearray()  # Initialize an empty buffer to store incoming bytes.
    while True:
        try:
            chunk = sock.recv(1024)  # Read up to 1024 bytes from the socket.
            if not chunk:
                break  # If no data received, end the loop (connection closed).
            data.extend(chunk)
            if len(data) >= min_bytes:
                # Byte count is the 3rd byte in Modbus response.
                byte_count = data[2] 
                # Total expected length = header + data + CRC.
                expected_len = 3 + byte_count + 2
                if len(data) >= expected_len:
                    break
        except socket.timeout:
            break  # Timeout reached without complete data; stop reading.
    return data  # Return all collected bytes.

class ModbusClient:
    def __init__(self, host, port, slave, num_registers):
        self.host = host
        self.port = port
        self.slave = slave
        self.num_registers = num_registers

    # This is the main function to perform the Modbus "Read Input Registers"
    # operation. It builds the Modbus request, sends it via a TCP socket to a
    # serial tunnel device, waits for the response, verifies correctness, and
    # then extracts the register values.
    def read_input_registers(self, start_addr=0, num_registers=8):
        # The Modbus function code 4 means "Read input registers".
        function_code = 4

        # Pack the request frame without CRC:
        # > means big-endian (network order)
        # B is an unsigned byte, H is unsigned short (2 bytes)
        # Fields: slave address, function code, starting address, no. registers
        request_wo_crc = struct.pack(
            '>B B H H',
            self.slave,
            function_code,
            start_addr,
            num_registers
        )

        # Calculate the CRC16 checksum of the request frame.
        crc = crc16(request_wo_crc)

        # Append the CRC to the request frame, form the complete Modbus RTU frame.
        frame = request_wo_crc + crc

        #print(f"Connecting to {host}:{port}...")

        # Open a TCP connection to the serial tunnel device.
        with socket.create_connection((self.host, self.port), timeout=5) as sock:
            #print("Connected. Sending Modbus RTU frame to read input registers...")

            # Send the complete Modbus request frame over the socket.
            sock.sendall(frame)

            # Receive the full Modbus response frame.
            response = recv_full_response(sock)

            # Print the raw response in hexadecimal format for debugging.
            #print(f"Received response: {response.hex()}")

            # Check that the response length is at least 5 bytes (minimum valid
            # Modbus frame size).
            if len(response) < 5:
                raise ValueError("Response too short")

            # Check against CRC
            if response[-2:] != crc16(response[:-2]):
                raise ValueError("CRC check failed")

            # Confirm the response is from the correct slave and function code
            # matches
            if response[0] != self.slave or response[1] != function_code:
                raise ValueError("Unexpected slave or function code")

            # Extract the byte count from the third byte of the response.
            byte_count = response[2]

            # The byte count should equal number of registers requested times 2
            # (each register is 2 bytes).
            if byte_count != num_registers * 2:
                raise ValueError(f"Unexpected byte count {byte_count}")

            # Initialize an empty list to hold the register values.
            registers = []

            # Loop over each register; extract and unpack 2 bytes per register.
            for i in range(num_registers):
                reg_bytes = response[3 + i*2 : 5 + i*2]
                # Convert bytes to integer (big-endian), divide by 10 for degrees.
                reg_val = struct.unpack('>H', reg_bytes)[0] * 0.1
                registers.append(reg_val)  # Add the value to the list.

            return registers
