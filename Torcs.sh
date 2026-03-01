dpkg -s podman &> /dev/null  

if [ $? -ne 0 ]

	then
        	echo "not installed"  
            	sudo apt-get update
            	sudo apt-get install podman
				podman build -t torcs-podman -f podman/Containerfile .

	else
            	echo    "Podman is installed, running container"
fi

podman run --rm -it --network=host -e DISPLAY=$DISPLAY -e XAUTHORITY=$XAUTHORITY -v /tmp/.X11-unix:/tmp/.X11-unix:ro -v $XAUTHORITY:$XAUTHORITY:ro --device /dev/dri torcs-podman
