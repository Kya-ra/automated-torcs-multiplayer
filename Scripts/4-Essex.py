# This code was written by University of Essex students participating in an IBM Hackathon
# It is available at https://github.com/Wahsitrek/a-race-car-/blob/main/torcs_jm_par.py and used with permission of Jonny at IBM
# Some minor changes have been made for compatability and formatting standards. These are documented in README.md

import socket
import sys
import getopt
import os
import time
import math

PI = 3.14159265359

data_size = 2**17

ophelp = "Options:\n"
ophelp += " --host, -H <host>    TORCS server host. [localhost]\n"
ophelp += " --port, -p <port>    TORCS port. [3001]\n"
ophelp += " --id, -i <id>        ID for server. [SCR]\n"
ophelp += " --steps, -m <#>      Maximum simulation steps. 1 sec ~ 50 steps. [100000]\n"
ophelp += " --episodes, -e <#>   Maximum learning episodes. [1]\n"
ophelp += (
    " --track, -t <track>  Your name for this track. Used for learning. [unknown]\n"
)
ophelp += " --stage, -s <#>      0=warm up, 1=qualifying, 2=race, 3=unknown. [3]\n"
ophelp += " --debug, -d          Output full telemetry.\n"
ophelp += " --help, -h           Show this help.\n"
ophelp += " --version, -v        Show current version."
usage = "Usage: %s [ophelp [optargs]] \n" % sys.argv[0]
usage = usage + ophelp
version = "20130505-2"


def clip(v, lo, hi):
    if v < lo:
        return lo
    elif v > hi:
        return hi
    else:
        return v


def bargraph(x, mn, mx, w, c="X"):
    """Draws a simple asciiart bar graph. Very handy for
    visualizing what's going on with the data.
    x= Value from sensor, mn= minimum plottable value,
    mx= maximum plottable value, w= width of plot in chars,
    c= the character to plot with."""
    if not w:
        return ""  # No width!
    if x < mn:
        x = mn  # Clip to bounds.
    if x > mx:
        x = mx  # Clip to bounds.
    tx = mx - mn  # Total real units possible to show on graph.
    if tx <= 0:
        return "backwards"  # Stupid bounds.
    upw = tx / float(w)  # X Units per output char width.
    if upw <= 0:
        return "what?"  # Don't let this happen.
    negpu, pospu, negnonpu, posnonpu = 0, 0, 0, 0
    if mn < 0:  # Then there is a negative part to graph.
        if x < 0:  # And the plot is on the negative side.
            negpu = -x + min(0, mx)
            negnonpu = -mn + x
        else:  # Plot is on pos. Neg side is empty.
            negnonpu = -mn + min(0, mx)  # But still show some empty neg.
    if mx > 0:  # There is a positive part to the graph
        if x > 0:  # And the plot is on the positive side.
            pospu = x - max(0, mn)
            posnonpu = mx - x
        else:  # Plot is on neg. Pos side is empty.
            posnonpu = mx - max(0, mn)  # But still show some empty pos.
    nnc = int(negnonpu / upw) * "-"
    npc = int(negpu / upw) * c
    ppc = int(pospu / upw) * c
    pnc = int(posnonpu / upw) * "_"
    return "[%s]" % (nnc + npc + ppc + pnc)


class Client:
    def __init__(
        self, H=None, p=None, i=None, e=None, t=None, s=None, d=None, vision=False
    ):
        self.vision = vision

        self.host = "localhost"
        self.port = 3004
        self.sid = "SCR-Essex"
        self.maxEpisodes = 1  # "Maximum number of learning episodes to perform"
        self.trackname = "unknown"
        self.stage = 3  # 0=Warm-up, 1=Qualifying 2=Race, 3=unknown <Default=3>
        self.debug = False
        self.maxSteps = 100000  # 50steps/second
        self.parse_the_command_line()
        if H:
            self.host = H
        if p:
            self.port = p
        if i:
            self.sid = i
        if e:
            self.maxEpisodes = e
        if t:
            self.trackname = t
        if s:
            self.stage = s
        if d:
            self.debug = d
        self.S = ServerState()
        self.R = DriverAction()
        self.setup_connection()

    def setup_connection(self):
        try:
            self.so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error:
            print("Error: Could not create socket...")
            sys.exit(-1)
        self.so.settimeout(1)

        n_fail = 5
        while True:
            a = "-45 -19 -12 -7 -4 -2.5 -1.7 -1 -.5 0 .5 1 1.7 2.5 4 7 12 19 45"

            initmsg = "%s(init %s)" % (self.sid, a)

            try:
                self.so.sendto(initmsg.encode(), (self.host, self.port))
            except socket.error:
                sys.exit(-1)
            sockdata = str()
            try:
                sockdata, addr = self.so.recvfrom(data_size)
                sockdata = sockdata.decode("utf-8")
            except socket.error:
                print("Waiting for server on %d............" % self.port)
                print("Count Down : " + str(n_fail))
                if n_fail < 0:
                    print("relaunch torcs")

                    time.sleep(1.0)
                    if self.vision is False:
                        os.system("torcs -nofuel -nodamage -nolaptime &")
                    else:
                        os.system("torcs -nofuel -nodamage -nolaptime -vision &")

                    time.sleep(1.0)
                    os.system("sh autostart.sh")
                    n_fail = 5
                n_fail -= 1

            identify = "***identified***"
            if identify in sockdata:
                print("Client connected on %d.............." % self.port)
                break

    def parse_the_command_line(self):
        try:
            (opts, args) = getopt.getopt(
                sys.argv[1:],
                "H:p:i:m:e:t:s:dhv",
                [
                    "host=",
                    "port=",
                    "id=",
                    "steps=",
                    "episodes=",
                    "track=",
                    "stage=",
                    "debug",
                    "help",
                    "version",
                ],
            )
        except getopt.error as why:
            print("getopt error: %s\n%s" % (why, usage))
            sys.exit(-1)
        try:
            for opt in opts:
                if opt[0] == "-h" or opt[0] == "--help":
                    print(usage)
                    sys.exit(0)
                if opt[0] == "-d" or opt[0] == "--debug":
                    self.debug = True
                if opt[0] == "-H" or opt[0] == "--host":
                    self.host = opt[1]
                if opt[0] == "-i" or opt[0] == "--id":
                    self.sid = opt[1]
                if opt[0] == "-t" or opt[0] == "--track":
                    self.trackname = opt[1]
                if opt[0] == "-s" or opt[0] == "--stage":
                    self.stage = int(opt[1])
                if opt[0] == "-p" or opt[0] == "--port":
                    self.port = int(opt[1])
                if opt[0] == "-e" or opt[0] == "--episodes":
                    self.maxEpisodes = int(opt[1])
                if opt[0] == "-m" or opt[0] == "--steps":
                    self.maxSteps = int(opt[1])
                if opt[0] == "-v" or opt[0] == "--version":
                    print("%s %s" % (sys.argv[0], version))
                    sys.exit(0)
        except ValueError as why:
            print(
                "Bad parameter '%s' for option %s: %s\n%s"
                % (opt[1], opt[0], why, usage)
            )
            sys.exit(-1)
        if len(args) > 0:
            print("Superflous input? %s\n%s" % (", ".join(args), usage))
            sys.exit(-1)

    def get_servers_input(self):
        """Server's input is stored in a ServerState object"""
        if not self.so:
            return
        sockdata = str()

        while True:
            try:
                sockdata, addr = self.so.recvfrom(data_size)
                sockdata = sockdata.decode("utf-8")
            except socket.error:
                print(".", end=" ")
            if "***identified***" in sockdata:
                print("Client connected on %d.............." % self.port)
                continue
            elif "***shutdown***" in sockdata:
                print(
                    (
                        (
                            "Server has stopped the race on %d. "
                            + "You were in %d place."
                        )
                        % (self.port, self.S.d["racePos"])
                    )
                )
                self.shutdown()
                return
            elif "***restart***" in sockdata:
                print("Server has restarted the race on %d." % self.port)
                self.shutdown()
                return
            elif not sockdata:  # Empty?
                continue  # Try again.
            else:
                self.S.parse_server_str(sockdata)
                if self.debug:
                    sys.stderr.write("\x1b[2J\x1b[H")  # Clear for steady output.
                    print(self.S)
                break  # Can now return from this function.

    def respond_to_server(self):
        if not self.so:
            return
        try:
            message = repr(self.R)
            self.so.sendto(message.encode(), (self.host, self.port))
        except socket.error as emsg:
            print("Error sending to server: %s Message %s" % (emsg[1], str(emsg[0])))
            sys.exit(-1)
        if self.debug:
            print(self.R.fancyout())

    def shutdown(self):
        if not self.so:
            return
        print(
            (
                "Race terminated or %d steps elapsed. Shutting down %d."
                % (self.maxSteps, self.port)
            )
        )
        self.so.close()
        self.so = None


class ServerState:
    """What the server is reporting right now."""

    def __init__(self):
        self.servstr = str()
        self.d = dict()

    def parse_server_str(self, server_string):
        """Parse the server string."""
        self.servstr = server_string.strip()[:-1]
        sslisted = self.servstr.strip().lstrip("(").rstrip(")").split(")(")
        for i in sslisted:
            w = i.split(" ")
            self.d[w[0]] = destringify(w[1:])

    def __repr__(self):
        return self.fancyout()
        out = str()
        for k in sorted(self.d):
            strout = str(self.d[k])
            if type(self.d[k]) is list:
                strlist = [str(i) for i in self.d[k]]
                strout = ", ".join(strlist)
            out += "%s: %s\n" % (k, strout)
        return out

    def fancyout(self):
        """Specialty output for useful ServerState monitoring."""
        out = str()
        sensors = [  # Select the ones you want in the order you want them.
            "stucktimer",
            "fuel",
            "distRaced",
            "distFromStart",
            "opponents",
            "wheelSpinVel",
            "z",
            "speedZ",
            "speedY",
            "speedX",
            "targetSpeed",
            "rpm",
            "skid",
            "slip",
            "track",
            "trackPos",
            "angle",
        ]

        for k in sensors:
            if k not in self.d:
                continue
            if type(self.d.get(k)) is list:  # Handle list type data.
                if k == "track":  # Nice display for track sensors.
                    strout = str()
                    raw_tsens = ["%.1f" % x for x in self.d["track"]]
                    strout += (
                        " ".join(raw_tsens[:9])
                        + "_"
                        + raw_tsens[9]
                        + "_"
                        + " ".join(raw_tsens[10:])
                    )
                elif k == "opponents":  # Nice display for opponent sensors.
                    strout = str()
                    for osensor in self.d["opponents"]:
                        if osensor > 190:
                            oc = "_"
                        elif osensor > 90:
                            oc = "."
                        elif osensor > 39:
                            oc = chr(int(osensor / 2) + 97 - 19)
                        elif osensor > 13:
                            oc = chr(int(osensor) + 65 - 13)
                        elif osensor > 3:
                            oc = chr(int(osensor) + 48 - 3)
                        else:
                            oc = "?"
                        strout += oc
                    strout = " -> " + strout[:18] + " " + strout[18:] + " <-"
                else:
                    strlist = [str(i) for i in self.d[k]]
                    strout = ", ".join(strlist)
            else:  # Not a list type of value.
                if k == "gear":  # This is redundant now since it's part of RPM.
                    gs = "_._._._._._._._._"
                    p = int(self.d["gear"]) * 2 + 2  # Position
                    label = "%d" % self.d["gear"]  # Label
                    if label == "-1":
                        label = "R"
                    if label == "0":
                        label = "N"
                    strout = gs[:p] + "(%s)" % label + gs[p + 3 :]
                elif k == "damage":
                    strout = "%6.0f %s" % (
                        self.d[k],
                        bargraph(self.d[k], 0, 10000, 50, "~"),
                    )
                elif k == "fuel":
                    strout = "%6.0f %s" % (
                        self.d[k],
                        bargraph(self.d[k], 0, 100, 50, "f"),
                    )
                elif k == "speedX":
                    cx = "X"
                    if self.d[k] < 0:
                        cx = "R"
                    strout = "%6.1f %s" % (
                        self.d[k],
                        bargraph(self.d[k], -30, 300, 50, cx),
                    )
                elif k == "speedY":  # This gets reversed for display to make sense.
                    strout = "%6.1f %s" % (
                        self.d[k],
                        bargraph(self.d[k] * -1, -25, 25, 50, "Y"),
                    )
                elif k == "speedZ":
                    strout = "%6.1f %s" % (
                        self.d[k],
                        bargraph(self.d[k], -13, 13, 50, "Z"),
                    )
                elif k == "z":
                    strout = "%6.3f %s" % (
                        self.d[k],
                        bargraph(self.d[k], 0.3, 0.5, 50, "z"),
                    )
                elif k == "trackPos":  # This gets reversed for display to make sense.
                    cx = "<"
                    if self.d[k] < 0:
                        cx = ">"
                    strout = "%6.3f %s" % (
                        self.d[k],
                        bargraph(self.d[k] * -1, -1, 1, 50, cx),
                    )
                elif k == "stucktimer":
                    if self.d.get(k):
                        strout = "%3d %s" % (
                            self.d[k],
                            bargraph(self.d[k], 0, 300, 50, "'"),
                        )
                    else:
                        strout = "Not stuck!"
                elif k == "rpm":
                    g = self.d["gear"]
                    if g < 0:
                        g = "R"
                    else:
                        g = "%1d" % g
                    strout = bargraph(self.d[k], 0, 10000, 50, g)
                elif k == "angle":
                    asyms = [
                        "  !  ",
                        ".|'  ",
                        "./'  ",
                        "_.-  ",
                        ".--  ",
                        "..-  ",
                        "---  ",
                        ".__  ",
                        "-._  ",
                        "'-.  ",
                        "'\.  ",
                        "'|.  ",
                        "  |  ",
                        "  .|'",
                        "  ./'",
                        "  .-'",
                        "  _.-",
                        "  __.",
                        "  ---",
                        "  --.",
                        "  -._",
                        "  -..",
                        "  '\.",
                        "  '|.",
                    ]
                    rad = self.d[k]
                    deg = int(rad * 180 / PI)
                    symno = int(0.5 + (rad + PI) / (PI / 12))
                    symno = symno % (len(asyms) - 1)
                    strout = "%5.2f %3d (%s)" % (rad, deg, asyms[symno])
                elif k == "skid":  # A sensible interpretation of wheel spin.
                    frontwheelradpersec = self.d["wheelSpinVel"][0]
                    skid = 0
                    if frontwheelradpersec:
                        skid = (
                            0.5555555555 * self.d["speedX"] / frontwheelradpersec
                            - 0.66124
                        )
                    strout = bargraph(skid, -0.05, 0.4, 50, "*")
                elif k == "slip":  # A sensible interpretation of wheel spin.
                    frontwheelradpersec = self.d["wheelSpinVel"][0]
                    slip = 0
                    if frontwheelradpersec:
                        slip = (
                            self.d["wheelSpinVel"][2] + self.d["wheelSpinVel"][3]
                        ) - (self.d["wheelSpinVel"][0] + self.d["wheelSpinVel"][1])
                    strout = bargraph(slip, -5, 150, 50, "@")
                else:
                    strout = str(self.d[k])
            out += "%s: %s\n" % (k, strout)
        return out


class DriverAction:
    """What the driver is intending to do (i.e. send to the server).
    Composes something like this for the server:
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus 0)(meta 0) or
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus -90 -45 0 45 90)(meta 0)"""

    def __init__(self):
        self.actionstr = str()
        self.d = {
            "accel": 0.2,
            "brake": 0,
            "clutch": 0,
            "gear": 1,
            "steer": 0,
            "focus": [-90, -45, 0, 45, 90],
            "meta": 0,
        }

    def clip_to_limits(self):
        """There pretty much is never a reason to send the server
        something like (steer 9483.323). This comes up all the time
        and it's probably just more sensible to always clip it than to
        worry about when to. The "clip" command is still a snakeoil
        utility function, but it should be used only for non standard
        things or non obvious limits (limit the steering to the left,
        for example). For normal limits, simply don't worry about it."""
        self.d["steer"] = clip(self.d["steer"], -1, 1)
        self.d["brake"] = clip(self.d["brake"], 0, 1)
        self.d["accel"] = clip(self.d["accel"], 0, 1)
        self.d["clutch"] = clip(self.d["clutch"], 0, 1)
        if self.d["gear"] not in [-1, 0, 1, 2, 3, 4, 5, 6]:
            self.d["gear"] = 0
        if self.d["meta"] not in [0, 1]:
            self.d["meta"] = 0
        if (
            type(self.d["focus"]) is not list
            or min(self.d["focus"]) < -180
            or max(self.d["focus"]) > 180
        ):
            self.d["focus"] = 0

    def __repr__(self):
        self.clip_to_limits()
        out = str()
        for k in self.d:
            out += "(" + k + " "
            v = self.d[k]
            if type(v) is not list:
                out += "%.3f" % v
            else:
                out += " ".join([str(x) for x in v])
            out += ")"
        return out
        return out + "\n"

    def fancyout(self):
        """Specialty output for useful monitoring of bot's effectors."""
        out = str()
        od = self.d.copy()
        od.pop("gear", "")  # Not interesting.
        od.pop("meta", "")  # Not interesting.
        od.pop("focus", "")  # Not interesting. Yet.
        for k in sorted(od):
            if k == "clutch" or k == "brake" or k == "accel":
                strout = ""
                strout = "%6.3f %s" % (od[k], bargraph(od[k], 0, 1, 50, k[0].upper()))
            elif k == "steer":  # Reverse the graph to make sense.
                strout = "%6.3f %s" % (od[k], bargraph(od[k] * -1, -1, 1, 50, "S"))
            else:
                strout = str(od[k])
            out += "%s: %s\n" % (k, strout)
        return out


def destringify(s):
    """makes a string into a value or a list of strings into a list of
    values (if possible)"""
    if not s:
        return s
    if type(s) is str:
        try:
            return float(s)
        except ValueError:
            print("Could not find a value in %s" % s)
            return s
    elif type(s) is list:
        if len(s) < 2:
            return destringify(s[0])
        else:
            return [destringify(i) for i in s]


# ===== OLD LEGACY FUNCTION (DISABLED - using drive_modular instead) =====
# def drive_example(c):
#     '''This is only an example. It will get around the track but the
#     correct thing to do is write your own `drive()` function.'''
#     S,R= c.S.d,c.R.d
#     target_speed=160
#
#     R['steer']= S['angle']*25 / PI
#     R['steer']-= S['trackPos']*.25
#
#     R['accel'] = max(0.0, min(1.0, R['accel']))
#
#
#     if S['speedX'] < target_speed - (R['steer']*2.5):
#         R['accel']+= .4
#     else:
#         R['accel']-= .2
#     if S['speedX']<10:
#        R['accel']+= 1/(S['speedX']+.1)
#
#     if ((S['wheelSpinVel'][2]+S['wheelSpinVel'][3]) -
#        (S['wheelSpinVel'][0]+S['wheelSpinVel'][1]) > 2):
#        R['accel']-= 0.1
#
#
#
#     R['gear']=1
#     if S['speedX']>60:
#         R['gear']=2
#     if S['speedX']>100:
#         R['gear']=3
#     if S['speedX']>140:
#         R['gear']=4
#     if S['speedX']>190:
#         R['gear']=5
#     if S['speedX']>220:
#         R['gear']=6
#     return

#############################################
# MODULAR DRIVE LOGIC WITH USER PARAMETERS  #
#############################################

# ================= USER CONFIGURABLE PARAMETERS =================
TARGET_SPEED = 120  # Base cap; dynamic target reduces in turns
STEER_GAIN = 32
CENTERING_GAIN = 0.95
BRAKE_THRESHOLD = 0.06  # Brake earlier
GEAR_SPEEDS = [0, 40, 70, 100, 125, 150]
ENABLE_TRACTION_CONTROL = True
STEER_SMOOTH = 0.85
MAX_STEER_DELTA = 0.08
MAX_ACCEL_DELTA = 0.08
MAX_BRAKE_DELTA = 0.08
ACCEL_BRAKE_DEADZONE = 0.02
STRAIGHT_SENSOR_MIN = 90.0
STRAIGHT_ANGLE_DZ = 0.012
STRAIGHT_POS_DZ = 0.02


# ================= HELPER FUNCTIONS =================
def calculate_steering(S):
    # Base human-like steering: align + center
    steer = (S["angle"] * STEER_GAIN / math.pi) - (S["trackPos"] * CENTERING_GAIN)

    # Look-ahead (gentle): start turning before the car's angle changes
    aL = max(1.0, S["track"][8])  # slight left-forward
    aR = max(1.0, S["track"][10])  # slight right-forward
    fwd = max(1.0, S["track"][9])  # forward

    # Predict curve direction: + = turn right, - = turn left
    curve = (aR - aL) / max(aL, aR)

    # Weight it only when a corner is actually coming (forward distance shrinking)
    # Start earlier so turn-in is smoother instead of last-moment.
    look_w = max(
        0.0, min(1.0, (60.0 - fwd) / 35.0)
    )  # 0 on straights, 1 on tight corners
    steer += curve * 0.70 * look_w

    # Your original speed scaling (natural feel)
    if S["speedX"] < 80:
        steer *= 1.35
    if S["speedX"] > 110:
        steer *= 0.85
    if S["speedX"] > 150:
        steer *= 0.70

    return max(-1, min(1, steer))


def calculate_target_speed(S, R):
    steer_mag = abs(R["steer"])
    angle_mag = abs(S["angle"])

    # Use forward track sensor (index 9) to anticipate turns/walls.
    # Shorter distance ahead means tighter corner: lower target speed.
    forward_min = max(1.0, min(S["track"][8], S["track"][9], S["track"][10]))
    left = max(1.0, S["track"][6])
    right = max(1.0, S["track"][12])
    curvature = abs(left - right) / max(left, right)
    nearL = max(1.0, S["track"][8])
    nearR = max(1.0, S["track"][10])
    farL = max(1.0, S["track"][6])
    farR = max(1.0, S["track"][12])

    dir_near = (nearR - nearL) / max(nearL, nearR)
    dir_far = (farR - farL) / max(farL, farR)

    # Chicane: direction flips between near and far
    s_turn = (
        (forward_min < 55.0)
        and (abs(dir_near) > 0.12)
        and (abs(dir_far) > 0.12)
        and (dir_near * dir_far < 0)
    )

    # Base target from forward clearance
    sensor_target = 60.0 + 4.5 * forward_min

    # If forward view is short, slow down (hairpin / 90-degree)
    if forward_min < 35.0:
        sensor_target -= (35.0 - forward_min) * 1.6

    # --- HARD CAP for very tight corners (prevents wide sand exit) ---
    if forward_min < 22.0:
        sensor_target = min(sensor_target, 65.0)
    elif forward_min < 28.0:
        sensor_target = min(sensor_target, 80.0)

    # Curvature proxy: big imbalance => sharp turn ahead
    if curvature > 0.25:
        sensor_target -= (curvature - 0.25) * 80.0

    # Extra: if forward is short AND curvature high, cap speed softly
    if forward_min < 28.0 and curvature > 0.30:
        sensor_target = min(sensor_target, 90.0)

    if s_turn:
        sensor_target -= 12.0  # 5–15 km/h slower is perfect for chicanes

    target = min(TARGET_SPEED, sensor_target)
    target -= steer_mag * 45
    target -= angle_mag * 70
    target -= max(0.0, abs(S["trackPos"]) - 0.25) * 40

    if s_turn:
        target -= 15.0  # stronger, noticeable slowdown

    # Keep a higher floor so hairpins/90° corners don't become crawling
    return max(65.0, target)


def calculate_throttle(S, R):
    s = S["speedX"]
    target = calculate_target_speed(S, R)

    if s < target:
        accel = min(1.0, R["accel"] + 0.18)
    else:
        accel = max(0.0, R["accel"] - 0.35)

    if s < 10:
        accel = 1.0

    accel *= 1.0 - min(0.6, abs(R["steer"]) * 0.9)
    # If we're off-center, don't accelerate hard (prevents sliding onto sand)
    if abs(S["trackPos"]) > 0.45:
        accel = min(accel, 0.45)
    return max(0.0, min(1.0, accel))


def apply_brakes(S, R):
    s = S["speedX"]
    target = calculate_target_speed(S, R)
    brake = 0.0

    # Brake when overshooting the dynamic target speed.
    if s > target + 12:
        brake = min(1.0, (s - target) / 70.0 + 0.05)

    forward_min = max(1.0, min(S["track"][8], S["track"][9], S["track"][10]))
    curvature = abs(max(1.0, S["track"][6]) - max(1.0, S["track"][12])) / max(
        max(1.0, S["track"][6]), max(1.0, S["track"][12])
    )

    # Pre-emptive brake for sharp corner ahead (ramped, not a hard hit).
    if forward_min < 28.0 and curvature > 0.28 and s > 70:
        severity = max(0.0, (28.0 - forward_min) / 10.0) + max(
            0.0, (curvature - 0.28) / 0.12
        )
        brake = max(brake, min(0.6, 0.3 + 0.15 * severity))

    # If we're already slow, don't keep braking (prevents crawling in corners)
    if s < 75:
        brake = min(brake, 0.15)

    if abs(S["angle"]) > BRAKE_THRESHOLD and s > 80:
        brake = max(brake, 0.55)
    if abs(S["angle"]) > BRAKE_THRESHOLD + 0.05 and s > 90:
        brake = max(brake, 0.75)

    # Early sharp-turn protection
    if abs(R["steer"]) > 0.35 and s > 95:
        brake = max(brake, 0.6)
    if abs(R["steer"]) > 0.50 and s > 110:
        brake = max(brake, 0.85)

    # Smooth brake changes to avoid harsh spikes.
    prev_brake = R.get("brake", 0.0)
    brake = min(brake, prev_brake + 0.15)
    return min(1.0, brake)


def shift_gears(S):
    gear = 1
    for i, speed in enumerate(GEAR_SPEEDS):
        if S["speedX"] > speed:
            gear = i + 1
    return min(gear, 6)


def traction_control(S, accel):
    if ENABLE_TRACTION_CONTROL:
        if (
            (S["wheelSpinVel"][2] + S["wheelSpinVel"][3])
            - (S["wheelSpinVel"][0] + S["wheelSpinVel"][1])
        ) > 2:
            accel -= 0.1
    return max(0.0, accel)


# ================= MAIN DRIVE FUNCTION =================
def drive_modular(c):
    try:
        S, R = c.S.d, c.R.d

        # Initialize steer first (before calculate_throttle uses it)
        desired = calculate_steering(S)
        # On clear straights, kill tiny oscillations to prevent shaking
        forward_min = max(1.0, min(S["track"][8], S["track"][9], S["track"][10]))
        if (
            forward_min > STRAIGHT_SENSOR_MIN
            and abs(S["angle"]) < STRAIGHT_ANGLE_DZ
            and abs(S["trackPos"]) < STRAIGHT_POS_DZ
        ):
            desired = 0.0
        prev_steer = R.get("_prev_steer", desired)
        # Blend + rate limit for smoother turn-in
        blended = STEER_SMOOTH * prev_steer + (1.0 - STEER_SMOOTH) * desired
        delta = blended - prev_steer
        if delta > MAX_STEER_DELTA:
            blended = prev_steer + MAX_STEER_DELTA
        elif delta < -MAX_STEER_DELTA:
            blended = prev_steer - MAX_STEER_DELTA
        R["steer"] = clip(blended, -1.0, 1.0)
        R["_prev_steer"] = R["steer"]

        # Now calculate throttle (uses R['steer'])
        R["accel"] = calculate_throttle(S, R)

        # Apply brakes
        R["brake"] = apply_brakes(S, R)

        # Traction control
        R["accel"] = traction_control(S, R["accel"])

        # Gear shifting
        R["gear"] = shift_gears(S)

        recovery = (abs(S["trackPos"]) > 0.95) or (abs(S["angle"]) > 0.75)

        # --- SAFETY SLOWDOWN (prevents first-corner wall) ---
        # Tight-corner aware: only slow hard when the forward sensor is short.
        if not recovery:
            forward = max(1.0, S["track"][9])
            tight = forward < 28.0
            if tight and (abs(S["angle"]) > 0.12 or abs(S["trackPos"]) > 0.60):
                # If we're still FAST, scrub speed hard (prevents wall crash)
                if S["speedX"] > 55:
                    R["accel"] = min(R["accel"], 0.35)
                    R["brake"] = max(R["brake"], 0.45)
                else:
                    # If we're already slow, DO NOT keep braking (prevents stopping)
                    R["brake"] = min(R["brake"], 0.12)
                    R["accel"] = max(R["accel"], 0.55)
                    # Nudge back toward center so it recovers cleanly
                    R["steer"] += -S["trackPos"] * 0.25
            elif abs(S["trackPos"]) > 0.75 and S["speedX"] > 80:
                # Off-center at speed: scrub a little without killing momentum.
                R["accel"] = min(R["accel"], 0.45)
                R["brake"] = max(R["brake"], 0.30)

        # --- OFF-TRACK RECOVERY ---
        # Stronger rejoin while still moving.
        if abs(S["trackPos"]) > 0.85:
            R["steer"] += -S["trackPos"] * 0.25
            R["accel"] = max(R["accel"], 0.55)
            R["brake"] = min(R["brake"], 0.10)

        # --- SLIGHT OFF-TRACK CORRECTION (NO SPEED KILL) ---
        if 0.55 < abs(S["trackPos"]) < 0.90:
            R["steer"] += -S["trackPos"] * 0.35
            R["brake"] = min(R["brake"], 0.20)

        # --- ANTI-SPIN / OFF-TRACK RECOVERY (sand/gravel) ---
        # Rare trigger only when truly spinning.
        if (abs(S["trackPos"]) > 0.90) or (abs(S["angle"]) > 0.75 and S["speedX"] > 60):
            R["accel"] = min(R["accel"], 0.25)
            R["brake"] = max(R["brake"], 0.30)

        # --- UNSTUCK / KEEP MOVING ---
        # If speed is near zero, force gentle recovery forward.
        if S["speedX"] < 5:
            forward = max(1.0, S["track"][9])
            if forward > 20.0:
                R["accel"] = 1.0
                R["brake"] = 0.0
                if abs(S["trackPos"]) > 0.4:
                    R["steer"] = -S["trackPos"] * 0.8
        elif S["speedX"] < 15 and abs(S["trackPos"]) < 0.30:
            # On track but slowing too much: keep rolling.
            R["brake"] = min(R["brake"], 0.05)
            R["accel"] = max(R["accel"], 0.5)
        elif S["speedX"] < 25 and abs(S["trackPos"]) < 0.30 and abs(S["angle"]) < 0.10:
            # On track and aligned: don't allow a full stop.
            R["brake"] = 0.0
            R["accel"] = max(R["accel"], 0.4)
        # --- NO FULL STOP AFTER CORNER ---
        # If we're moving slowly, never keep braking hard (prevents freezing).
        if S["speedX"] < 25:
            R["brake"] = min(R["brake"], 0.10)
            R["accel"] = max(R["accel"], 0.45)
        # --- NEVER DROP TO ZERO SPEED UNLESS TRULY STUCK ---
        # If we're moving and only slightly off-track, keep momentum.
        if S["speedX"] > 25:
            R["accel"] = max(R["accel"], 0.35)
            R["brake"] = min(R["brake"], 0.25)
        # --- FINAL-TURN / VERY-TIGHT-CORNER PROTECTION ---
        # If the forward sensors show extremely low clearance (e.g., corkscrew
        # final hairpin), enforce stronger braking, cap steering and reduce
        # acceleration to avoid going off into sand.
        try:
            forward_min = max(1.0, min(S["track"][8], S["track"][9], S["track"][10]))
        except Exception:
            forward_min = 9999.0
        if forward_min < 35.0:
            # Aggressive measures when approaching a very tight last turn
            if S["speedX"] > 55:
                R["brake"] = max(R.get("brake", 0.0), 0.45)
                R["accel"] = max(R.get("accel", 0.0), 0.10)
                # Cap steering to avoid over-rotation/spin
                R["steer"] = clip(R.get("steer", 0.0), -0.55, 0.55)
                # Encourage engine braking by lowering gear when needed
                if S["speedX"] < 70:
                    R["gear"] = max(1, R.get("gear", 1))
                else:
                    R["gear"] = min(R.get("gear", 4), 4)
            else:
                # If already slow, avoid continued heavy braking that can lock
                R["brake"] = min(R.get("brake", 0.0), 0.20)
                R["accel"] = max(R.get("accel", 0.0), 0.35)
        # --- SMOOTHING: low-pass accel/brake to avoid start-stop jitter ---
        # Capture previous values (from previous timestep) and rate-limit changes
        prev_accel = R.get("_prev_accel", R.get("accel", 0.0))
        prev_brake = R.get("_prev_brake", R.get("brake", 0.0))
        desired_accel = R.get("accel", 0.0)
        desired_brake = R.get("brake", 0.0)

        # Accel smoothing
        diff_a = desired_accel - prev_accel
        if abs(diff_a) < ACCEL_BRAKE_DEADZONE:
            new_accel = prev_accel
        else:
            new_accel = prev_accel + max(-MAX_ACCEL_DELTA, min(MAX_ACCEL_DELTA, diff_a))

        # Brake smoothing
        diff_b = desired_brake - prev_brake
        if abs(diff_b) < ACCEL_BRAKE_DEADZONE:
            new_brake = prev_brake
        else:
            new_brake = prev_brake + max(-MAX_BRAKE_DELTA, min(MAX_BRAKE_DELTA, diff_b))

        # If braking is significant, reduce accel to avoid fighting controls
        if new_brake > 0.15:
            new_accel = min(new_accel, 0.3)

        R["accel"] = clip(new_accel, 0.0, 1.0)
        R["brake"] = clip(new_brake, 0.0, 1.0)
        R["_prev_accel"] = R["accel"]
        R["_prev_brake"] = R["brake"]
    except Exception as e:
        print(f"Error in drive_modular: {e}", flush=True)
        import traceback

        traceback.print_exc()
        # Safe defaults on error
        R["accel"] = 0.0
        R["brake"] = 1.0
        R["steer"] = 0.0
        R["gear"] = 1

    return


# ================= MAIN LOOP =================
if __name__ == "__main__":
    try:
        C = Client()
        print("Client connected, starting loop...")
        for step in range(C.maxSteps, 0, -1):
            try:
                C.get_servers_input()
                drive_modular(C)
                C.respond_to_server()
            except socket.error as e:
                print(f"Socket error at step {step}: {e}")
                break
            except Exception as e:
                print(f"Error at step {step}: {e}")
                import traceback

                traceback.print_exc()
                break
        C.shutdown()
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback

        traceback.print_exc()
