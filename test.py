import xml.etree.ElementTree as ET
from subprocess import call

xml_path = "torcs/config/raceman/quickrace.xml"

player_count = int(input("Enter player count: "))

tree = ET.parse(xml_path)
root = tree.getroot()

drivers_section = None
for section in root.findall("section"):
    if section.get("name") == "Drivers":
        drivers_section = section
        break

if drivers_section is None:
    raise ValueError("Drivers section not found")

to_remove = []
for child in drivers_section.findall("section"):
    if child.get("name", "").isdigit():
        to_remove.append(child)

for child in to_remove:
    drivers_section.remove(child)

for i in range(player_count):
    sec = ET.Element("section", {"name": str(i + 1)})

    attnum = ET.SubElement(sec, "attnum", {
        "name": "idx",
        "val": str(i)
    })

    attstr = ET.SubElement(sec, "attstr", {
        "name": "module",
        "val": "scr_server"
    })

    drivers_section.append(sec)

tree.write(xml_path, encoding="UTF-8", xml_declaration=True)
call(["./launch.sh", str(player_count)])