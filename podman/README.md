# How to Build and Run the Container

<p>
To build the container, first make sure that you're in the root folder of this project (which is torcs-car), then run this command in the terminal

<p>
<code>
podman build -t torcs-podman -f podman/Containerfile .
</code>

<p>
This will start building the container file. The container file will first download the necessary packages and libraries to run torcs and the python file for the car.

### It will install the following:
- <b>Wine</b>, as our containerization is based on Linux
- <b>Tmux</b>, to horiztonally split the terminal window to automatically ope both the python file and Torcs.exe at the same time in a single terminal window.
- Some OpenGL libraries for Torcs to run
- Pip packages mentioned in the requirements.txt file

---
Afterwards it will copy over the folders gym_torcs and torcs to the container as well as the launch.sh file

The launch.sh file handles the tmux sessions and the initializations of the python controller file and Torcs.

## Running the container
To run the container you can use this command below:

<p>
<code>
podman run --rm -it --network=host torcs-podman
</code>

<p>
If you're using WSL, running the command above will probably not work as intended. You will see tmux, python and wine launching but not the actual torcs program as running the podman container regularly like above does not route the gui to wslg by default which allows for gui apps to run as a window on Windows.

For WSL, you can run this command instead which worked in my case:

<p>
<code>
podman run --rm -it --network=host -e DISPLAY="$DISPLAY" -e WAYLAND_DISPLAY="$WAYLAND_DISPLAY" -e XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" -v /mnt/wslg:/mnt/wslg -v /tmp/.X11-unix:/tmp/.X11-unix -v "$XDG_RUNTIME_DIR":"$XDG_RUNTIME_DIR" torcs-podman
</code>

This one will properly route the display settings so that the Torcs screen will properly show up.

<p>
There is also a Torcs.sh file in the root of this project, it currently has the WSL version of the command in it, you can modify that to the regular command. I'm going to add Torcs.sh to .gitignore so that it does not mess up others changes for this file.

On a Linux native machine, a user can also run this Torcs.sh file just like running a program through a GUI file explorer, so it is also user friendly in that terms. 
This will probably be similar on macos as well although I haven't tested it yet.

For Windows, we don't really have a quick launch file for the command right now, but we can probably build one easily using a powershell script. It would behave similarly.

Also a quick note if Torcs.sh refuses to run because of permissions, run this command below:

<code>
chmod +x Torcs.sh
</code>