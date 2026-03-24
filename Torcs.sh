#!/usr/bin/env bash
set -e

# Default player count
PLAYER_COUNT=${1:-1}
SCRIPTS=$(printf "%s\n" "${@:2}")

# ------------------------------
# 1️⃣ Ensure Podman exists
# ------------------------------
if ! command -v podman &> /dev/null; then
    echo "Podman not found. Please install Podman first."
    exit 1
fi

# ------------------------------
# 2️⃣ Build container if missing or outdated
# ------------------------------

IMAGE_NAME="torcs-podman"
HASH_FILE=".torcs_build_hash"

# Compute hash of relevant files (exclude stuff like .git, logs, etc.)
CURRENT_HASH=$(find . \
    -type f \
    ! -path "./.git/*" \
    ! -path "./logs/*" \
    ! -path "./*.pyc" \
    ! -path "./__pycache__/*" \
    -exec sha256sum {} + | sort | sha256sum | awk '{print $1}')

PREVIOUS_HASH=""
if [ -f "$HASH_FILE" ]; then
    PREVIOUS_HASH=$(cat "$HASH_FILE")
fi

# Check if image exists
IMAGE_EXISTS=false
if podman image exists "$IMAGE_NAME"; then
    IMAGE_EXISTS=true
fi

# Decide whether to rebuild
if [ "$IMAGE_EXISTS" = false ] || [ "$CURRENT_HASH" != "$PREVIOUS_HASH" ]; then
    echo "Changes detected or image missing → rebuilding container..."

    podman build -t "$IMAGE_NAME" -f podman/Containerfile .

    # Save new hash
    echo "$CURRENT_HASH" > "$HASH_FILE"
else
    echo "Container is up to date."
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

podman run --rm -it \
    --network=host \
    -e PLAYER_COUNT="$PLAYER_COUNT" \
    -e SCRIPTS="$SCRIPTS" \
    $GPU_OPTS \
    $DISPLAY_OPTS \
    torcs-podman