#!/usr/bin/env bash
set -e

# Default player count
PLAYER_COUNT=${1:-1}

# ------------------------------
# 1️⃣ Ensure Podman exists
# ------------------------------
if ! command -v podman &> /dev/null; then
    echo "Podman not found. Please install Podman first."
    exit 1
fi

# ------------------------------
# 2️⃣ Build container if missing
# ------------------------------
if ! podman image exists torcs-podman; then
    echo "Building torcs-podman container..."
    podman build -t torcs-podman -f podman/Containerfile .
fi

# ------------------------------
# 3️⃣ Detect host environment
# ------------------------------
DISPLAY_OPTS=""
GPU_OPTS=""

# Wayland first
if [ -n "$WAYLAND_DISPLAY" ] && [ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]; then
    echo "Wayland detected"

    DISPLAY_OPTS="-e WAYLAND_DISPLAY=$WAYLAND_DISPLAY \
                   -e XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR \
                   -v $XDG_RUNTIME_DIR/$WAYLAND_DISPLAY:$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY:rw \
                   -v /tmp:/tmp:rw \
                   -e QT_QPA_PLATFORM=wayland \
                   -e LIBGL_ALWAYS_INDIRECT=0"

    # WSLg mounts if needed
    if grep -q Microsoft /proc/version; then
        DISPLAY_OPTS="$DISPLAY_OPTS -v /mnt/wslg:/mnt/wslg:rw"
    fi

# Fallback to X11
else
    echo "Falling back to X11"
    DISPLAY_OPTS="-e DISPLAY=$DISPLAY \
                   -v /tmp/.X11-unix:/tmp/.X11-unix:rw"
    xhost +local:root &> /dev/null
fi

# Mount GPU devices if available
if [ -d /dev/dri ]; then
    echo "GPU devices detected, mounting /dev/dri"
    GPU_OPTS="--device /dev/dri:/dev/dri"
fi

# Mount PulseAudio socket
if [ -S "$XDG_RUNTIME_DIR/pulse/native" ]; then
    DISPLAY_OPTS="$DISPLAY_OPTS -e PULSE_SERVER=unix:$XDG_RUNTIME_DIR/pulse/native \
                               -v $XDG_RUNTIME_DIR/pulse:$XDG_RUNTIME_DIR/pulse:rw"
fi

# ------------------------------
# 4️⃣ Run the container
# ------------------------------
echo "Running torcs-podman container..."
podman run --rm -it --network=host -e PLAYER_COUNT="$PLAYER_COUNT" $GPU_OPTS $DISPLAY_OPTS torcs-podman