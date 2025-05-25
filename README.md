# Maritime IoT Gateway Application
The gateway app relies on the `CraneIoT` simulator for Modbus TCP and NMEA WebSocket data. `CraneIoT` has been added as a submodule to `simulators/CraneIoT`

1.  **Clone the repo with submodules:**
    ```bash
    git clone --recurse-submodules https://github.com/cnrabdullah/maritime-iot-gateway.git
    cd maritime-iot-gateway
    ```

2.  **Patch the simulator script:**
    - The NMEA simulator claims to send new line and carriage return but is not actually sending them. Apply this patch to fix it:
    ```bash
    git -C simulators/CraneIoT/ apply ../../patches/01_nmea_crlf.patch
    ```

3.  **(Optional) Review and change the default app settings**
    - If needed, change the default app settings through `config/gateway_config.default.yml` or create a local config file out of it at `config/gateway_config.yml`
    ```bash
    cp config/gateway_config.default.yml config/gateway_config.yml
    ```

3.  **Use any MQTT client tool to monitor the gateway data:**
    - host: `wss://mqtt-dashboard.com:8884`
    - sub: `ows-challenge/mv-sinking-boat/main-crane/#`

## Option 1: Running with Docker (Recommended)

This method runs both the simulator and the gateway application inside a single Docker container.

1.  **Prerequisites:**
    *   Docker installed and running.
    *   The initial setup steps (cloning and patching) above must be completed.

2.  **Build the Docker Image:**
    From the root directory of the `maritime-iot-gateway` project:
    ```bash
    docker build -t maritime-gateway-app -f docker/Dockerfile .
    ```

3.  **Run the Docker Container:**
    ```bash
    docker run -it --rm --name maritime-gateway maritime-gateway-app
    ```
    *   This will start both the `CraneIoT` simulator and the gateway application. You'll see logs from both.

4.  **Monitor MQTT Data:**
    - Monitor the data flow on MQTT client

5.  **Stop the Container:**
    Press `Ctrl+C` in the terminal where `docker run` is executing.

## Option 2: Running Locally

### Running the Simulators (CraneIoT)

1.  **Create a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    pip install -r simulators/CraneIoT/requirements.txt
    ```

3.  **Run the simulator:**
    ```bash
    python ./simulators/CraneIoT/src/crane_simulation/crane_simulation.py
    ```
    Keep the simulator script running while you test the gateway.

### Running the Gateway

1.  **Open a new terminal and activate the venv again:**
    ```bash
    source .venv/bin/activate
    ```

2.  **Run the gateway app:**
    ```bash
    python -m src.main
    ```

4.  **Monitor MQTT Data:**
    - Monitor the data flow on MQTT client

5.  **Stop the Application:**
    Press `Ctrl+C` in the terminal where app is executing.


## Potential Improvements
- Implement unit and integration tests
- Implement CI/CD flow
- Implement packaging
- Implement static analyzing
- Define code formatter
- Secret management
- Add githooks to auto-run static analyzing, code formatting and version increase pre-push