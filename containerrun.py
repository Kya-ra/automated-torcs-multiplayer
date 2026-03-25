import xml.etree.ElementTree as ET
from subprocess import call
import os
from pathlib import Path

player_count = int(os.getenv("PLAYER_COUNT", 1))
scripts_env = os.getenv("SCRIPTS", "")
script_list = scripts_env.split()

xml_path = Path("/torcs/torcs/config/raceman/quickrace.xml")  # container path

tree = ET.parse(xml_path)
root = tree.getroot()

drivers_section = None
for section in root.findall("section"):
    if section.get("name") == "Drivers":
        drivers_section = section
        break

if drivers_section is None:
    raise ValueError("Drivers section not found")

# Remove existing numeric driver sections
to_remove = [
    child
    for child in drivers_section.findall("section")
    if child.get("name", "").isdigit()
]
for child in to_remove:
    drivers_section.remove(child)

# Add new players
for i in range(player_count):
    sec = ET.Element("section", {"name": str(i + 1)})
    ET.SubElement(sec, "attnum", {"name": "idx", "val": str(i)})
    ET.SubElement(sec, "attstr", {"name": "module", "val": "scr_server"})
    drivers_section.append(sec)

tree.write(xml_path, encoding="UTF-8", xml_declaration=True)

# Now call launch.sh inside container
launch_sh = Path("/torcs/launch.sh")
call([str(launch_sh)], cwd="/torcs")
