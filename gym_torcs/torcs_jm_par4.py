import socket
import sys
import getopt
import os
import time
import math
#import subprocess

#from logs import race_logger

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
    if not w:
        return ""
    if x < mn:
        x = mn
    if x > mx:
        x = mx
    tx = mx - mn
    if tx <= 0:
        return "backwards"
    upw = tx / float(w)
    if upw <= 0:
        return "what?"
    negpu, pospu, negnonpu, posnonpu = 0, 0, 0, 0
    if mn < 0:
        if x < 0:
            negpu = -x + min(0, mx)
            negnonpu = -mn + x
        else:
            negnonpu = -mn + min(0, mx)
    if mx > 0:
        if x > 0:
            pospu = x - max(0, mn)
            posnonpu = mx - x
        else:
            posnonpu = mx - max(0, mn)
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
        self.sid = "SCR4"
        self.maxEpisodes = 1
        self.trackname = "unknown"
        self.stage = 3
        self.debug = False
        self.maxSteps = 100000  # 50 steps/second

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

        # For steering smoothing
        self.prev_steer = 0.0

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
            # 19 track angles
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
                    os.system("pkill torcs")
                    time.sleep(1.0)
                    if self.vision is False:
                        os.system("torcs -nofuel -nodamage -nolaptime &")
                    else:
                        os.system("torcs -nofuel -nodamage -nolaptime -vision &")

                    time.sleep(1.0)
                    os.system("sh autostart.sh")
                    n_fail = 5
                n_fail -= 1

            if "***identified***" in sockdata:
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
                if opt[0] in ("-h", "--help"):
                    print(usage)
                    sys.exit(0)
                if opt[0] in ("-d", "--debug"):
                    self.debug = True
                if opt[0] in ("-H", "--host"):
                    self.host = opt[1]
                if opt[0] in ("-i", "--id"):
                    self.sid = opt[1]
                if opt[0] in ("-t", "--track"):
                    self.trackname = opt[1]
                if opt[0] in ("-s", "--stage"):
                    self.stage = int(opt[1])
                if opt[0] in ("-p", "--port"):
                    self.port = int(opt[1])
                if opt[0] in ("-e", "--episodes"):
                    self.maxEpisodes = int(opt[1])
                if opt[0] in ("-m", "--steps"):
                    self.maxSteps = int(opt[1])
                if opt[0] in ("-v", "--version"):
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
                        % (self.port, self.S.d.get("racePos", -1))
                    )
                )
                self.shutdown()
                return
            elif "***restart***" in sockdata:
                print("Server has restarted the race on %d." % self.port)
                self.shutdown()
                return
            elif not sockdata:
                continue
            else:
                self.S.parse_server_str(sockdata)
                if self.debug:
                    sys.stderr.write("\x1b[2J\x1b[H")
                    print(self.S)
                break

    def respond_to_server(self):
        if not self.so:
            return
        try:
            message = repr(self.R)
            self.so.sendto(message.encode(), (self.host, self.port))
        except socket.error as emsg:
            print("Error sending to server:", emsg)
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
    def __init__(self):
        self.servstr = str()
        self.d = dict()

    def parse_server_str(self, server_string):
        self.servstr = server_string.strip()[:-1]
        sslisted = self.servstr.strip().lstrip("(").rstrip(")").split(")(")
        for i in sslisted:
            w = i.split(" ")
            self.d[w[0]] = destringify(w[1:])

    def __repr__(self):
        return self.fancyout()

    def fancyout(self):
        out = str()
        sensors = [
            "speedX",
            "speedY",
            "speedZ",
            "trackPos",
            "angle",
            "rpm",
            "track",
            "wheelSpinVel",
        ]
        for k in sensors:
            out += f"{k}: {self.d.get(k)}\n"
        return out


class DriverAction:
    def __init__(self):
        self.actionstr = str()
        self.d = {
            "accel": 0.85,
            "brake": 0.0,
            "clutch": 0.0,
            "gear": 1,
            "steer": 0.0,
            "focus": [-90, -45, 0, 45, 90],
            "meta": 0,
        }

    def clip_to_limits(self):
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
            if not isinstance(v, list):
                out += "%.3f" % v
            else:
                out += " ".join([str(x) for x in v])
            out += ")"
        return out

    def fancyout(self):
        out = str()
        od = self.d.copy()
        od.pop("gear", "")
        od.pop("meta", "")
        od.pop("focus", "")
        for k in sorted(od):
            if k in ("clutch", "brake", "accel"):
                out += "%s: %6.3f %s\n" % (
                    k,
                    od[k],
                    bargraph(od[k], 0, 1, 50, k[0].upper()),
                )
            elif k == "steer":
                out += "%s: %6.3f %s\n" % (k, od[k], bargraph(-od[k], -1, 1, 50, "S"))
            else:
                out += "%s: %s\n" % (k, str(od[k]))
        return out


def destringify(s):
    if not s:
        return s
    if isinstance(s, str):
        try:
            return float(s)
        except ValueError:
            return s
    elif isinstance(s, list):
        if len(s) < 2:
            return destringify(s[0])
        else:
            return [destringify(i) for i in s]


# ==========================
#  Improved Modular Driving
# ==========================
# ==========================
#  Improved Modular Driving
# ==========================

# --------------------------
# Speed plan (tune these)
# --------------------------
BASE_SPEED = 185.0  # straight-line target speed (km/h)
MIN_SPEED = 50.0  # minimum target speed in sharp turns
MAX_SPEED = 250.0  # cap speed (for safety / stability)
K_CURVE = 58  # how strongly curves reduce target speed (bigger = slower in turns)

# --------------------------
# Steering plan (tune these)
# --------------------------
STEER_GAIN = 11.5  # angle -> steer sensitivity
CENTER_GAIN = 0.24  # trackPos -> centering strength
STEER_SMOOTH_ALPHA = 0.82  # 0.10~0.35, bigger = more responsive, smaller = smoother

# --------------------------
# Braking plan (tune these)
# --------------------------
BRAKE_ANGLE_TH = 0.12  # radians. bigger = brake later, smaller = brake earlier
BRAKE_MAX = 1.0  # max brake intensity

# --------------------------
# Traction control
# --------------------------
ENABLE_TC = True
TC_SLIP_TH = 0.7
TC_ACCEL_CUT = 0.02


def estimate_curve_from_track(track19):
    """
    track19: list of 19 distances.
    Estimate curve severity.

    Fix: avoid slowing down too much on small curves by:
      - adding a dead-zone for center distance
      - reducing the weight of center penalty
    """
    if not isinstance(track19, list) or len(track19) < 19:
        return 0.0

    center = float(track19[9])
    left = sum(track19[0:9]) / 9.0
    right = sum(track19[10:19]) / 9.0
    lr_diff = abs(left - right)

    # Dead-zone: only penalize center when it's clearly short
    center_penalty = 0.0
    if center < 60.0:  # dead-zone threshold (tune: 50~80)
        center_penalty = (60.0 - center) / 60.0  # 0..1-ish

    # Combine
    curve = lr_diff * 0.6 + center_penalty * 10.0  # was 25.0 -> too aggressive
    return max(0.0, curve)


def compute_target_speed(S):
    """
    Dynamic target speed: high on straights, reduced in turns.
    Fix: cap the curve value to prevent extreme slowdowns due to noise.
    """
    curve = estimate_curve_from_track(S.get("track", []))
    curve = min(curve, 30.0)  # safety cap (tune: 20~40)
    tgt = BASE_SPEED - K_CURVE * curve
    return clip(tgt, MIN_SPEED, MAX_SPEED)


def compute_steer(S):
    """
    Basic steering based on:
      - heading error: angle
      - lateral error: trackPos
    """
    angle = float(S.get("angle", 0.0))
    trackPos = float(S.get("trackPos", 0.0))
    steer = (angle * STEER_GAIN / math.pi) - (trackPos * CENTER_GAIN)
    return clip(steer, -1.0, 1.0)


def compute_accel_brake(S, current_accel, target_speed):
    """
    Longitudinal control:
      - throttle to chase target speed
      - brake when angle is large
      - enforce brake/accel mutual exclusion for stability
    """
    speedX = float(S.get("speedX", 0.0))
    angle = float(S.get("angle", 0.0))

    # Brake if heading angle is large (turning / off-line)
    brake = 0.0
    if abs(angle) > BRAKE_ANGLE_TH:
        brake = clip((abs(angle) - BRAKE_ANGLE_TH) * 1.8, 0.0, BRAKE_MAX)

    # Throttle control
    accel = float(current_accel)

    if speedX < target_speed:
        accel += 0.04
    else:
        accel -= 0.06

    # Help launch from near stop
    if speedX < 10.0:
        accel += 0.5 / (speedX + 1.0)

    accel = clip(accel, 0.0, 1.0)

    # Mutual exclusion: if braking, suppress throttle
    if brake > 0.0:
        accel = min(accel, 0.05)

    return accel, brake


def traction_control(S, accel):
    """
    Reduce throttle if rear wheels spin significantly more than front wheels.
    """
    if not ENABLE_TC:
        return accel

    w = S.get("wheelSpinVel", [0, 0, 0, 0])
    if isinstance(w, list) and len(w) >= 4:
        slip = (w[2] + w[3]) - (w[0] + w[1])
        if slip > TC_SLIP_TH:
            accel -= TC_ACCEL_CUT

    return clip(accel, 0.0, 1.0)


def shift_gear(S, current_gear):
    """
    Simple gear logic with downshift and upshift.
    Uses speed thresholds + low rpm downshift.
    """
    speedX = float(S.get("speedX", 0.0))
    rpm = float(S.get("rpm", 0.0))

    up = [0, 55, 95, 135, 175, 215]  # shift up when speed above
    down = [0, 25, 50, 85, 120, 160]  # shift down when speed below

    g = int(current_gear)
    g = clip(g, 1, 6)

    # Downshift if too slow for current gear
    if g > 1 and speedX < down[g - 1]:
        g -= 1

    # Upshift if fast enough
    if g < 6 and speedX > up[g - 1]:
        g += 1

    # Encourage downshift if rpm very low
    if g > 1 and rpm > 0 and rpm < 2500:
        g -= 1

    return clip(g, 1, 6)


def drive(c: Client):
    S = c.S.d
    R = c.R.d

    # 1) Dynamic target speed (slow down in turns)
    target_speed = compute_target_speed(S)

    # 2) Steering + smoothing (EMA)
    raw_steer = compute_steer(S)
    steer = STEER_SMOOTH_ALPHA * raw_steer + (1.0 - STEER_SMOOTH_ALPHA) * c.prev_steer
    c.prev_steer = steer
    R["steer"] = clip(steer, -1.0, 1.0)

    # 3) Throttle/Brake
    accel, brake = compute_accel_brake(S, R.get("accel", 0.2), target_speed)
    accel = traction_control(S, accel)
    R["accel"] = accel
    R["brake"] = brake

    # 4) Gear
    R["gear"] = shift_gear(S, R.get("gear", 1))

    # (optional)
    R["clutch"] = 0.0


if __name__ == "__main__":
    """
    race_logger.add_car_stats(BASE_SPEED, MIN_SPEED, MAX_SPEED, K_CURVE, STEER_GAIN, CENTER_GAIN, STEER_SMOOTH_ALPHA, BRAKE_ANGLE_TH, BRAKE_MAX, ENABLE_TC, TC_SLIP_TH, TC_ACCEL_CUT)
    
    results_filepath = "../torcs/results/quickrace/"
    xml_files = [
        os.path.join(results_filepath, f)
        for f in os.listdir(results_filepath)
        if f.lower().endswith(".xml")
    ]
    file_amount = len(xml_files)
    """

    print("Player 4 is running.")

    C4 = Client(p=3004)
    for step in range(C4.maxSteps, 0, -1):
        C4.get_servers_input()
        drive(C4)
        C4.respond_to_server()
    
    #race_logger.check_for_new_file(file_amount)
    #race_logger.add_race_stats()

    # subprocess.run(["bash", "./terminateProcesses.sh"], check=False)

    C4.shutdown()