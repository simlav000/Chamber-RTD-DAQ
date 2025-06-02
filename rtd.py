# Author: Simon Lavoie (simon.lavoie@mail.mcgill.ca)
import sys
import os
import threading
import argparse
import pandas
import socket
import time
import rtd_config as rc
from modbus import ModbusClient
from datetime import datetime 

sys.path.append('Database')
from Database import bvl_pymongodb


# Session refers to current execution of this script
SESSION_TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H-%M-%S")


LOG_DIR = os.path.join(os.getcwd(), "log")
DATA_DIR = os.path.join(os.getcwd(), "data")

CLIENTS = []
SERVER_RUNNING = True

# TCP Server for instantaneous streaming of temperature data to LabView
def start_tcp_server(host='127.0.0.1', port=5050):
    global SERVER_RUNNING

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen()
    log(f"[TCP] Server started on {host}:{port}")

    def handle_clients():
        global SERVER_RUNNING
        while SERVER_RUNNING:
            conn, addr = server.accept()
            log(f"[TCP] Client connected: {addr}")
            CLIENTS.append((conn, addr))

    threading.Thread(target=handle_clients, daemon=True).start()


def broadcast_tcp_message(msg):
    for conn, addr in CLIENTS:
        try:
            conn.sendall((msg + "\n").encode())
        except:
            CLIENTS.remove((conn, addr))
            log(f"[TCP] Client disconnected: {addr}")
            log(f"[TCP] Shutting down...")
            stop_server()

def stop_server():
    global SERVER_RUNNING
    SERVER_RUNNING = False

    for conn, addr in CLIENTS:
        try:
            conn.close()
            log(f"[TCP] Closed connection to {addr}")
        except:
            pass
    CLIENTS.clear()

    log("[SYSTEM] Exiting program.")


def main():
    global SERVER_RUNNING

    # Make the data directory if it does not already exist
    if not(os.path.exists(bvl_pymongodb.cfg.DATA_FOLDER)):
        os.mkdir(bvl_pymongodb.cfg.DATA_FOLDER)

    # Path to csv file for db upload
    csv_path = os.path.join(
            bvl_pymongodb.cfg.DATA_FOLDER, bvl_pymongodb.cfg.CSV_FILE_NAME
    )

    # Build the header for the database
    dfheader = ["timestamp"]
    dfheader.extend("channel_" + str(i + 1) for i in range(rc.NUM_REGISTERS))

    df = pandas.DataFrame(columns = dfheader)

    modbus_client = ModbusClient(
        host=rc.BRAINBOX_IP,
        port=9002,
        slave=1,
        num_registers=rc.NUM_REGISTERS
    )

    # Begin DAQ loop
    count = 0
    thread = None
    while SERVER_RUNNING:
        try:
            registers = modbus_client.read_input_registers()

            row_dict = {
                "timestamp":
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            row_dict.update(
                {f"channel_{i+1}": val for i, val in
                enumerate(registers)}
            )

            df.loc[len(df)] = row_dict 

            # Send to LabVIEW via TCP
            csv_row = ",".join(str(row_dict[col]) for col in dfheader)
            broadcast_tcp_message(csv_row)

            count += 1

            time.sleep(rc.SAMPLE_RATE / 60)

            if count >= int(rc.SAMPLE_RATE * rc.DB_UPLOADINTERVAL):
                # Spawn thread to upload, and clear df immediately
                thread = threading.Thread(
                    target=upload_data,
                    # Send COPY of current df to thread, as df gets wiped in 
                    # the next pass.
                    args=(df.copy(), csv_path), 
                    # Want upload to complete even if program shuts down
                    daemon=False
                )
                thread.start()

                df = pandas.DataFrame(columns=dfheader)
                count = 0


        except KeyboardInterrupt:
            if thread and thread.is_alive():
                log("⌛ Waiting for upload to finish...")
                thread.join()

            SERVER_RUNNING = False
            for c in CLIENTS:
                try:
                    c.close()
                except:
                    pass

            log("Job's done")
            break



def upload_data(df_to_upload, csv_path):
    if args.db:
        df_to_upload.to_csv(csv_path, index=False)
        code = bvl_pymongodb.upload_from_csv(rc.DB_NAME, rc.COLLECTION)
        log(bvl_pymongodb.bvl_mongo_help(code))


def log(msg):
    if args.log:
        os.makedirs(LOG_DIR, exist_ok=True)
        log_path = os.path.join(LOG_DIR, SESSION_TIMESTAMP + "_log.txt")
        with open(log_path , "a") as log_file:
            log_file.write(f"{msg}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
            "--log",
            action="store_true",
            help="Enable logging to file"
    )
    parser.add_argument(
            "--db",
            action="store_true",
            help="Enable data upload to database"
    )

    args = parser.parse_args()

    start_tcp_server()
    main()
