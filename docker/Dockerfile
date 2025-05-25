FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements files first to leverage Docker cache
COPY requirements.txt ./
COPY simulators/CraneIoT/requirements.txt ./craneiot_requirements.txt

# Install Python dependencies for the gateway and the simulator
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r craneiot_requirements.txt

# This includes the gateway code AND the (pre-patched) simulators/CraneIoT submodule
COPY . .

CMD ["/bin/sh", "-c", "python ./simulators/CraneIoT/src/crane_simulation/crane_simulation.py & \
    echo 'Container: Simulator started in background. Waiting a few seconds...' && \
    sleep 3 && \
    echo 'Container: Starting Maritime IoT Gateway in foreground...' && \
    exec python -m src.main"]