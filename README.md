# 🌡️ Temperature Readout

This repository contains Python scripts and a LabVIEW Virtual Instrument (VI) for reading and streaming temperature data.

## 📜 Contents

- Python scripts:
  - `rtd.py`
  - `modbus.py`
  - `rtd_config.py`
  - `client.py`
- LabVIEW Virtual Instrument:
  - `rtd.vi` (Which I've compiled into LiveTemperaturePlot.exe)

## ⚠️ TL;DR

To ensure full functionality,  `rtd.vi` or `LiveTemperaturePlot.exe` (whichever you choose to execute)
**must reside in the same directory** as `rtd.py`, `modbus.py` and `rtd_config.py`.
---

## ⚙️ Dependency Chain

### 1. `modbus.py` – The Device Manager 

This script manages communication with the **Brainboxes ES-357** Ethernet-to-Serial device, which relays temperature readings from the **Sequent Microsystems DAQ HAT** over RS485.

- A TCP port is opened between `modbus.py` and the ES-357.
- Managed by the `ModbusClient` class.
- `read_input_registers()` sends a request and returns an array of temperature values.
- The number of values is controlled by the `ModbusClient` constructor.

> 💡 You may increase this number if more thermocouples/HATs are added.

---

### 2. `rtd_config.py` - The Settings File

This script contains three key tunable global parameters:

1. `SAMPLE_RATE` – How often (per minute) read requests are sent.
2. `NUM_REGISTERS` – Number of thermocouple readings to extract.
3. `DB_UPLOADINTERVAL` – Interval (in minutes) before uploading to the database at [BvL-MongoDB](https://github.com/Brunner-neutrino-lab/BvL-MongoDB) *(access required)*.

Other parameters:

- `DB_NAME` and `COLLECTION` – MongoDB names (changeable if desired).
- `BRAINBOXES_IP` - Kept seperate from the source code for privacy reasons.

---

### 3. `rtd.py` – The Script That Gathers and Streams

`rtd.py` behavior:

- Instantiates a `ModbusClient`
- Reads temperatures in a loop
- Uploads to MongoDB periodically (if `--db` flag is passed)
- Opens a TCP server on port `5050` to stream readings to clients (e.g., LabVIEW, `client.py`)

Optional command-line flags:

- `--db` – Enable database upload
- `--log` – Enable debug logging to `log/` directory

---

### 4. `client.py` – The TCP Tester

This script helps test `rtd.py`’s TCP server.

Steps:

1. Run `rtd.py` in one terminal
2. Run `client.py` in another
3. Watch temperature data and debug messages stream in

> ⚠️ Note: `rtd.py` is designed to **exit if a client disconnects**, a workaround for safe shutdown within LabVIEW.
