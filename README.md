
# Apache-MINA-GUI

A simple Python-based GUI demonstration for interacting with Apache MINA servers. This project aims to provide an easy way to test and visualize network communication using Apache MINA through various client and server interfaces.

## Overview

This repository includes several Python scripts that implement different versions of client-side and server-side GUI applications. These GUIs can be used to establish network connections, send messages, and receive responses from an Apache MINA-based server.

## Features

- Multiple client GUI implementations (`client_gui_1.py`, `client_gui_2.py`, `client_gui_3.py`)
- A server-side GUI (`server_gui.py`)
- Simple user-friendly interfaces for testing Apache MINA network functionality
- Easy to run and modify for educational or demonstration purposes

## Prerequisites

- Python 3.x
- Tkinter (usually included with standard Python installations)

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/ruoqilee2003/Apache-MINA-GUI.git
   cd Apache-MINA-GUI
   ```

2. (Optional) Create and activate a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate   # On Linux/Mac
   venv\Scripts\activate      # On Windows
   ```

3. Install any dependencies (if required).

## Usage

Run any of the provided Python GUI scripts:

```bash
python client_gui_1.py
```

Or try other GUIs:

```bash
python client_gui_2.py
python client_gui_3.py
python server_gui.py
```

Use the GUI to connect to your Apache MINA server, send messages, and view responses.

## Notes
- This project is intended for educational and demonstration purposes.
