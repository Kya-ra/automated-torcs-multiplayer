#!/usr/bin/env bash
set -e

IMAGE_NAME="torcs-podman"
HASH_FILE=".torcs_build_hash"

# ------------------------------
# 1️⃣ Rebuild container if needed
# ------------------------------
CURRENT_HASH=$(find . -type f \
    ! -path "./.git/*" \
    ! -path "./logs/*" \
    ! -path "./*.pyc" \
    ! -path "./__pycache__/*" \
    -exec sha256sum {} + | sort | sha256sum | awk '{print $1}')

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
WAYLAND_SOCKET="$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY"

if [ ! -S "$WAYLAND_SOCKET" ]; then
    echo "Error: Wayland socket not found at $WAYLAND_SOCKET"
    exit 1
fi

WAYLAND_OPTS="-e WAYLAND_DISPLAY=$WAYLAND_DISPLAY \
              -e XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR \
              -v $WAYLAND_SOCKET:$WAYLAND_SOCKET:rw \
              -v /tmp:/tmp:rw"

GPU_OPTS=""
[ -d /dev/dri ] && GPU_OPTS="--device /dev/dri:/dev/dri"

# ------------------------------
# 3️⃣ Launch the container
# ------------------------------
echo "Running torcs-podman container with Wayland..."

podman run --rm -it \
    --network=host \
    $GPU_OPTS \
    $WAYLAND_OPTS \
    torcs-podman