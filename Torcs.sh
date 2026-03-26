#!/usr/bin/env bash
set -e

IMAGE_NAME="torcs-podman"
HASH_FILE=".torcs_build_hash"

# ------------------------------
# 1️⃣ Rebuild container if needed
# ------------------------------
if ! command -v podman &> /dev/null; then
    echo "Podman not found. Please install Podman first."
    exit 1
fi

CURRENT_HASH=$(find \
    requirements.txt \
    launch_menu \
    torcs \
    Scripts \
    launch.sh \
    containerrun.py \
    podman/Containerfile \
    -type f \
    -exec sha256sum {} + | sort -u | sha256sum | awk '{print $1}')

PREVIOUS_HASH=""
[ -f "$HASH_FILE" ] && PREVIOUS_HASH=$(cat "$HASH_FILE")

IMAGE_EXISTS=false
if podman image exists "$IMAGE_NAME"; then IMAGE_EXISTS=true; fi

if [ "$IMAGE_EXISTS" = false ] || [ "$CURRENT_HASH" != "$PREVIOUS_HASH" ]; then
    echo "Changes detected or image missing → rebuilding container..."
    podman build -t "$IMAGE_NAME" -f podman/Containerfile .
    echo "$CURRENT_HASH" > "$HASH_FILE"
else
    echo "Container is up to date."
fi

# ------------------------------
# 2️⃣ Wayland + GPU mounts
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
# 3️⃣ Launch the container
# ------------------------------
echo "Running torcs-podman container with Wayland..."

podman run --rm -it \
    --network=host \
    $GPU_OPTS \
    $DISPLAY_OPTS \
    torcs-podman
