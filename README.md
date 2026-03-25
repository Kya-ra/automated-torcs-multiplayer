# Automated TORCS Multiplayer

## Steps to run:

Prerequisites: Podman

1. Place Scripts in /Scripts
2. Run with `./Torcs.sh`
3. Follow on-screen instructions
4. Launch, and when Torcs opens select default option 3 times to start

## Changes made to gym_torcs files

This project uses files provided by IBM UK, and modified by students at Bath Spa University, the Universities of Essex and of Exeter, and of UCL.
Files provided were bought in line with ruff standards for Python, given unique IDs, and the constructor override for the port number was removed.

The only nessecary change if testing your own torcs_jm_par files is to change C = Client(p=3001) to C = Client()