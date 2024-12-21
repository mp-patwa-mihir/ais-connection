import random
import socket
import time
import math
import threading

# Liste pour stocker les connexions clients
clients = []
clients_lock = threading.Lock()

def calculate_checksum(nmea_str):
    checksum = 0
    for char in nmea_str:
        checksum ^= ord(char)
    return format(checksum, '02X')

def encode_sixbit(binary_data):
    charset = "0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXabcdefghijklmnopqrstuvwxyz"
    encoded = ''
    padding_length = (6 - len(binary_data) % 6) % 6
    binary_data += '0' * padding_length
    for i in range(0, len(binary_data), 6):
        sixbit_segment = binary_data[i:i+6]
        value = int(sixbit_segment, 2)
        encoded += charset[value]
    return encoded

def twos_complement(value, bit_width):
    if value < 0:
        value = (1 << bit_width) + value
    return format(value, f'0{bit_width}b')

def broadcast_message(message):
    with clients_lock:
        disconnected_clients = []
        for client in clients:
            try:
                client.sendall((message + "\r\n").encode('utf-8'))
            except socket.error:
                disconnected_clients.append(client)
        # Retirer les clients déconnectés
        for client in disconnected_clients:
            clients.remove(client)
            client.close()

def generate_type1_message(vessel):
    mmsi_bin = format(vessel.mmsi, '030b')
    lat_bin = twos_complement(int(vessel.lat * 600000), 27)
    lon_bin = twos_complement(int(vessel.lon * 600000), 28)
    sog_bin = format(int(vessel.sog * 10), '010b')
    cog_bin = format(int(vessel.cog * 10), '012b')
    hdg_bin = format(int(vessel.cog), '009b')
    nav_status_bin = format(vessel.nav_status, '004b')
    rot_bin = twos_complement(0, 8)
    raim_bin = format(vessel.raim_flag, '01b')
    timestamp_bin = format(vessel.timestamp, '06b')

    binary_message = (
        "000001" + "00" + mmsi_bin + nav_status_bin + rot_bin + sog_bin + "0" +
        lon_bin + lat_bin + cog_bin + hdg_bin + timestamp_bin + "00" + raim_bin + "0000000000"
    )

    encoded_message = encode_sixbit(binary_message)
    fill_bits = (6 - len(binary_message) % 6) % 6
    nmea_message = f"!AIVDM,1,1,,A,{encoded_message},{fill_bits}"
    checksum = calculate_checksum(nmea_message[1:])
    return f"{nmea_message}*{checksum}"

def generate_type5_message(vessel):
    mmsi_bin = format(vessel.mmsi, '030b')
    imo_bin = format(random.randint(1000000, 9999999), '030b')
    callsign = str(vessel.mmsi)
    callsign_bin = ''.join(format(ord(c), '06b') for c in callsign.ljust(7))
    name_bin = ''.join(format(ord(c), '06b') for c in str(vessel.mmsi).ljust(20)[:20])
    ship_type_bin = format(random.randint(0, 99), '08b')
    dim_a_bin = format(random.randint(0, 511), '09b')
    dim_b_bin = format(random.randint(0, 511), '09b')
    dim_c_bin = format(random.randint(0, 63), '06b')
    dim_d_bin = format(random.randint(0, 63), '06b')
    fix_type_bin = format(random.randint(0, 7), '04b')
    eta_month_bin = format(random.randint(1, 12), '04b')
    eta_day_bin = format(random.randint(1, 31), '05b')
    eta_hour_bin = format(random.randint(0, 23), '05b')
    eta_minute_bin = format(random.randint(0, 59), '06b')
    draught_bin = format(int(random.uniform(0, 25.5) * 10), '08b')
    destination_bin = ''.join(format(ord(c), '06b') for c in "DESTINATION".ljust(20))

    binary_message = (
        "000101" + mmsi_bin + "00" + imo_bin + callsign_bin + name_bin +
        ship_type_bin + dim_a_bin + dim_b_bin + dim_c_bin + dim_d_bin +
        fix_type_bin + eta_month_bin + eta_day_bin + eta_hour_bin + eta_minute_bin +
        draught_bin + destination_bin + "0"
    )

    encoded_message = encode_sixbit(binary_message)
    fill_bits = (6 - len(binary_message) % 6) % 6
    nmea_message = f"!AIVDM,1,1,,A,{encoded_message},{fill_bits}"
    checksum = calculate_checksum(nmea_message[1:])
    return f"{nmea_message}*{checksum}"

class Vessel:
    def __init__(self, mmsi, lat, lon, sog, cog, nav_status):
        self.mmsi = mmsi
        self.initial_lat = lat
        self.initial_lon = lon
        self.lat = lat
        self.lon = lon
        self.sog = sog
        self.cog = cog
        self.nav_status = nav_status
        self.timestamp = 0
        self.raim_flag = random.randint(0, 1)
        self.last_transmission = 0
        self.last_static_transmission = 0

    def update_position(self):
        distance_nm = self.sog / 3600  # Distance parcourue en 1 seconde
        delta_lat = distance_nm * math.cos(math.radians(self.cog)) * 0.01667
        delta_lon = distance_nm * math.sin(math.radians(self.cog)) * 0.01667
        self.lat = max(46.0, min(self.lat + delta_lat, 47.0))
        self.lon = max(-2.0, min(self.lon + delta_lon, -1.0))
        self.timestamp = (self.timestamp + 1) % 60

    def reset_position(self):
        self.lat = self.initial_lat
        self.lon = self.initial_lon

def generate_vessels(num_vessels=2000):
    vessels = []
    for i in range(num_vessels):
        mmsi = random.randint(200000000, 799999999)
        coast_lat = 46.15
        coast_lon = -1.15
        coast_point = random.random()
        lat = coast_lat + coast_point * 0.7
        lon = coast_lon - coast_point * 0.8
        sea_offset = random.uniform(0.05, 0.2)
        lon -= sea_offset
        sog = random.uniform(0.0, 30.0)
        cog = random.uniform(0.0, 360.0)
        nav_status = random.randint(0, 15)
        vessels.append(Vessel(mmsi, lat, lon, sog, cog, nav_status))
    return vessels

server_running = True

def generate_ais_message(vessel, current_time):
    if current_time - vessel.last_static_transmission >= 360:
        vessel.last_static_transmission = current_time
        return generate_type5_message(vessel)
    else:
        return generate_type1_message(vessel)

def handle_client(client_socket, addr, vessels):
    print(f"Connected by {addr}")
    with clients_lock:
        clients.append(client_socket)

    start_time = time.time()
    vessel_index = 0
    messages_per_second = 200
    message_interval = 1 / messages_per_second  # Time interval between messages (5 milliseconds)
    last_reset_time = start_time

    try:
        while server_running:
            current_time = time.time()

            # Reset positions every hour
            if current_time - last_reset_time >= 3600:  # 3600 seconds = 1 hour
                for vessel in vessels:
                    vessel.reset_position()
                last_reset_time = current_time

            cycle_start = time.time()
            for _ in range(messages_per_second):
                vessel = vessels[vessel_index]
                vessel.update_position()
                ais_message = generate_ais_message(vessel, time.time() - start_time)
                broadcast_message(ais_message)
                vessel_index = (vessel_index + 1) % len(vessels)

                # Wait for the correct interval to maintain 200 messages per second
                elapsed_time = time.time() - cycle_start
                remaining_time = (message_interval * (_ + 1)) - elapsed_time
                if remaining_time > 0:
                    time.sleep(remaining_time)

            # Wait until the next second to align with the start of the next cycle
            time.sleep(max(0, 1 - (time.time() - cycle_start)))

    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        with clients_lock:
            if client_socket in clients:
                clients.remove(client_socket)
        client_socket.close()
        print(f"Connection closed for {addr}")


def ais_simulation_server(host='127.0.0.1', port=2400):
    global server_running
    vessels = generate_vessels(2000)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            # Set socket options to prevent address in use error (optional)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            server_socket.bind((host, port))
            server_socket.listen()
            server_socket.settimeout(1.0)
            print(f"Server listening on {host}:{port}")

            while server_running:
                try:
                    client_socket, addr = server_socket.accept()
                    client_thread = threading.Thread(target=handle_client, args=(client_socket, addr, vessels))
                    client_thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Error accepting connection: {e}")
                    continue  # Continue accepting new clients

            print("Server shutting down...")

    except OSError as e:
        print(f"Error binding to {host}:{port} - {e}")
        return  # Return early if we can't bind to the port

    # Cleanup client sockets
    with clients_lock:
        for client in clients:
            client.close()

    # Wait for all threads to finish
    for thread in threading.enumerate():
        if thread != threading.current_thread():
            thread.join(timeout=5)  # Optionally increase timeout

    print("All client connections closed, server shutdown complete.")

if __name__ == "__main__":
    try:
        server_thread = threading.Thread(target=ais_simulation_server)
        server_thread.start()

        while server_running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down server...")
        server_running = False
        server_thread.join(timeout=10)
        print("Server stopped.")