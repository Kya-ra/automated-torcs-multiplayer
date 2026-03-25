#This code was written by Bath Spa University students participating in an IBM Hackathon
#It is available at https://github.com/samctl/spa-racing-ibm-granite/blob/main/gym_torcs/torcs_jm_par.py and used with permission of Jonny at IBM

"""
Advanced Driving Control Algorithm for Car Racing Game/Simulation

This script implements an advanced driving control algorithm designed to provide realistic and adaptive vehicle dynamics
for a car racing game or simulation. The algorithm takes into account various parameters such as lateral position error,
yaw angle, longitudinal speed, target speed, minimum and maximum speeds, stability, cornering demands, and gear shifts.

The main components of the script include:
- Steering Control: Uses proportional control with kp_pos and kp_ang gains to calculate the steering angle based on
  the lateral position error and yaw angle. The raw steering value is then reduced based on the car's speed.
- Throttle/Brake Control: Determines throttle and brake values based on whether the current speed of the car is above or below
  the target speed. Additional logic is applied to adjust the throttle and brake values based on cornering, stability,
  and gear constraints.
- Gearbox Logic: Implements an advanced gearbox control system that considers slip proxy, stability, straightness,
  lateral acceleration, and other factors to determine optimal gear shift behavior.
- Launch Control: Includes a launch control feature for standstill or low-speed gear transitions (1 to 2, 2 to 3) to
  limit throttle based on the current speed of the car, preventing wheel spin and damage.
- Traction Control: Applies traction control by reducing throttle when excessive slip is detected.

The script calculates various parameters such as target_speed, MIN_SPEED, MAX_SPEED, accel, brake, steer, and gear,
and sends them back to the server for application to the car's behavior in the game or simulation.

This algorithm has been enhanced using IBM Granite, a state-of-the-art language model developed by IBM. The integration
of IBM Granite's advanced natural language processing capabilities has helped improve code readability, maintainability,
and overall functionality of this driving control algorithm.

By leveraging IBM Granite, we aim to provide a more immersive and realistic driving experience by adapting vehicle dynamics
based on different racing situations like cornering, straight-line acceleration, and gear shifts. The use of IBM Granite
has contributed to the development of a sophisticated and efficient algorithm that enhances the realism and responsiveness
of the car's behavior in the game or simulation.
"""


import socket
import sys
import getopt
import os
import time
import math
import random
import numpy as np
from collections import deque

PI= 3.14159265359

data_size = 2**17

# ---------------------------------------------------------
# Hyper‑parameters you can tune later
# ---------------------------------------------------------
BUFFER_SIZE   = int(1e5)          # max number of experiences stored
BATCH_SIZE    = 64                # size of each training batch
GAMMA         = 0.99              # discount factor for future rewards
EPS_START     = 1.0               # epsilon for ε‑greedy (decrease later)
EPS_END       = 0.01              # final epsilon
EPS_DECAY     = 200000            # decay steps for ε
LR_ALPHA      = 0.001             # learning rate
steerGain = 30

# Discretized action space: { 'accel', 'brake' }
ACTIONS = ['accel','brake']

ophelp=  'Options:\n'
ophelp+= ' --host, -H <host>    TORCS server host. [localhost]\n'
ophelp+= ' --port, -p <port>    TORCS port. [3001]\n'
ophelp+= ' --id, -i <id>        ID for server. [SCR]\n'
ophelp+= ' --steps, -m <#>      Maximum simulation steps. 1 sec ~ 50 steps. [100000]\n'
ophelp+= ' --episodes, -e <#>   Maximum learning episodes. [1]\n'
ophelp+= ' --track, -t <track>  Your name for this track. Used for learning. [unknown]\n'
ophelp+= ' --stage, -s <#>      0=warm up, 1=qualifying, 2=race, 3=unknown. [3]\n'
ophelp+= ' --debug, -d          Output full telemetry.\n'
ophelp+= ' --help, -h           Show this help.\n'
ophelp+= ' --version, -v        Show current version.'
usage= 'Usage: %s [ophelp [optargs]] \n' % sys.argv[0]
usage= usage + ophelp
version= "20130505-2"

def clip(v,lo,hi):
    if v<lo: return lo
    elif v>hi: return hi
    else: return v

def bargraph(x,mn,mx,w,c='X'):
    '''Draws a simple asciiart bar graph. Very handy for
    visualizing what's going on with the data.
    x= Value from sensor, mn= minimum plottable value,
    mx= maximum plottable value, w= width of plot in chars,
    c= the character to plot with.'''
    if not w: return '' # No width!
    if x<mn: x= mn      # Clip to bounds.
    if x>mx: x= mx      # Clip to bounds.
    tx= mx-mn # Total real units possible to show on graph.
    if tx<=0: return 'backwards' # Stupid bounds.
    upw= tx/float(w) # X Units per output char width.
    if upw<=0: return 'what?' # Don't let this happen.
    negpu, pospu, negnonpu, posnonpu= 0,0,0,0
    if mn < 0: # Then there is a negative part to graph.
        if x < 0: # And the plot is on the negative side.
            negpu= -x + min(0,mx)
            negnonpu= -mn + x
        else: # Plot is on pos. Neg side is empty.
            negnonpu= -mn + min(0,mx) # But still show some empty neg.
    if mx > 0: # There is a positive part to the graph
        if x > 0: # And the plot is on the positive side.
            pospu= x - max(0,mn)
            posnonpu= mx - x
        else: # Plot is on neg. Pos side is empty.
            posnonpu= mx - max(0,mn) # But still show some empty pos.
    nnc= int(negnonpu/upw)*'-'
    npc= int(negpu/upw)*c
    ppc= int(pospu/upw)*c
    pnc= int(posnonpu/upw)*'_'
    return '[%s]' % (nnc+npc+ppc+pnc)

class Client():
    def __init__(self,H=None,p=None,i=None,e=None,t=None,s=None,d=None,vision=False):
        self.vision = vision

        self.host= 'localhost'
        self.port= 3001
        self.sid= 'SCR-BathSpa'
        self.maxEpisodes=1 # "Maximum number of learning episodes to perform"
        self.trackname= 'unknown'
        self.stage= 3 # 0=Warm-up, 1=Qualifying 2=Race, 3=unknown <Default=3>
        self.debug= False
        self.maxSteps= 100000  # 50steps/second
        self.parse_the_command_line()
        if H: self.host= H
        if p: self.port= p
        if i: self.sid= i
        if e: self.maxEpisodes= e
        if t: self.trackname= t
        if s: self.stage= s
        if d: self.debug= d
        self.S= ServerState()
        self.R= DriverAction()
        self.setup_connection()

    def setup_connection(self):
        try:
            self.so= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error as emsg:
            print('Error: Could not create socket...')
            sys.exit(-1)
        self.so.settimeout(1)

        n_fail = 5
        while True:
            a= "-45 -19 -12 -7 -4 -2.5 -1.7 -1 -.5 0 .5 1 1.7 2.5 4 7 12 19 45"

            initmsg='%s(init %s)' % (self.sid,a)

            try:
                self.so.sendto(initmsg.encode(), (self.host, self.port))
            except socket.error as emsg:
                sys.exit(-1)
            sockdata= str()
            try:
                sockdata,addr= self.so.recvfrom(data_size)
                sockdata = sockdata.decode('utf-8')
            except socket.error as emsg:
                print("Waiting for server on %d............" % self.port)
                print("Count Down : " + str(n_fail))
                if n_fail < 0:
                    print("relaunch torcs")
                    
                    time.sleep(1.0)
                    if self.vision is False:
                        os.system('torcs -nofuel -nodamage -nolaptime &')
                    else:
                        os.system('torcs -nofuel -nodamage -nolaptime -vision &')

                    time.sleep(1.0)
                    os.system('sh autostart.sh')
                    n_fail = 5
                n_fail -= 1

            identify = '***identified***'
            if identify in sockdata:
                print("Client connected on %d.............." % self.port)
                break

    def parse_the_command_line(self):
        try:
            (opts, args) = getopt.getopt(sys.argv[1:], 'H:p:i:m:e:t:s:dhv',
                       ['host=','port=','id=','steps=',
                        'episodes=','track=','stage=',
                        'debug','help','version'])
        except getopt.error as why:
            print('getopt error: %s\n%s' % (why, usage))
            sys.exit(-1)
        try:
            for opt in opts:
                if opt[0] == '-h' or opt[0] == '--help':
                    print(usage)
                    sys.exit(0)
                if opt[0] == '-d' or opt[0] == '--debug':
                    self.debug= True
                if opt[0] == '-H' or opt[0] == '--host':
                    self.host= opt[1]
                if opt[0] == '-i' or opt[0] == '--id':
                    self.sid= opt[1]
                if opt[0] == '-t' or opt[0] == '--track':
                    self.trackname= opt[1]
                if opt[0] == '-s' or opt[0] == '--stage':
                    self.stage= int(opt[1])
                if opt[0] == '-p' or opt[0] == '--port':
                    self.port= int(opt[1])
                if opt[0] == '-e' or opt[0] == '--episodes':
                    self.maxEpisodes= int(opt[1])
                if opt[0] == '-m' or opt[0] == '--steps':
                    self.maxSteps= int(opt[1])
                if opt[0] == '-v' or opt[0] == '--version':
                    print('%s %s' % (sys.argv[0], version))
                    sys.exit(0)
        except ValueError as why:
            print('Bad parameter \'%s\' for option %s: %s\n%s' % (
                                       opt[1], opt[0], why, usage))
            sys.exit(-1)
        if len(args) > 0:
            print('Superflous input? %s\n%s' % (', '.join(args), usage))
            sys.exit(-1)

    def get_servers_input(self):
        '''Server's input is stored in a ServerState object'''
        if not self.so: return
        sockdata= str()

        while True:
            try:
                sockdata,addr= self.so.recvfrom(data_size)
                sockdata = sockdata.decode('utf-8')
            except socket.error as emsg:
                print('.', end=' ')
            if '***identified***' in sockdata:
                print("Client connected on %d.............." % self.port)
                continue
            elif '***shutdown***' in sockdata:
                print((("Server has stopped the race on %d. "+
                        "You were in %d place.") %
                        (self.port,self.S.d['racePos'])))
                self.shutdown()
                return
            elif '***restart***' in sockdata:
                print("Server has restarted the race on %d." % self.port)
                self.shutdown()
                return
            elif not sockdata: # Empty?
                continue       # Try again.
            else:
                self.S.parse_server_str(sockdata)
                if self.debug:
                    sys.stderr.write("\x1b[2J\x1b[H") # Clear for steady output.
                    print(self.S)
                break # Can now return from this function.

    def respond_to_server(self):
        if not self.so: return
        try:
            message = repr(self.R)
            self.so.sendto(message.encode(), (self.host, self.port))
        except socket.error as emsg:
            print("Error sending to server: %s Message %s" % (emsg[1],str(emsg[0])))
            sys.exit(-1)
        if self.debug: print(self.R.fancyout())

    def shutdown(self):
        if not self.so: return
        print(("Race terminated or %d steps elapsed. Shutting down %d."
               % (self.maxSteps,self.port)))
        self.so.close()
        self.so = None

class ExperienceReplay:
    def __init__(self, capacity: int):
        self.buffer = deque(maxlen=capacity)   # stores tuples (s,a,r,s')
        self.capacity = capacity

    def add(self, state, action, reward, next_state):
        self.buffer.append((state, action, reward, next_state))

    def sample(self, batch_size: int):
        if len(self.buffer) < batch_size:
            raise ValueError("Not enough samples in buffer")
        # Randomly choose a batch
        idxs = random.sample(range(len(self.buffer)), batch_size)
        batch = [self.buffer[i] for i in idxs]

        # Unpack into separate lists (order matters!)
        states, actions, rewards, next_states = zip(*batch)

        return list(states), list(actions), list(rewards), list(next_states)

    def __len__(self):
        return len(self.buffer)

class ServerState():
    '''What the server is reporting right now.'''
    def __init__(self):
        self.servstr= str()
        self.d= dict()

    def parse_server_str(self, server_string):
        '''Parse the server string.'''
        self.servstr= server_string.strip()[:-1]
        sslisted= self.servstr.strip().lstrip('(').rstrip(')').split(')(')
        for i in sslisted:
            w= i.split(' ')
            self.d[w[0]]= destringify(w[1:])

    def __repr__(self):
        return self.fancyout()
        out= str()
        for k in sorted(self.d):
            strout= str(self.d[k])
            if type(self.d[k]) is list:
                strlist= [str(i) for i in self.d[k]]
                strout= ', '.join(strlist)
            out+= "%s: %s\n" % (k,strout)
        return out

    def fancyout(self):
        '''Specialty output for useful ServerState monitoring.'''
        out= str()
        sensors= [ # Select the ones you want in the order you want them.
        'stucktimer',
        'fuel',
        'distRaced',
        'distFromStart',
        'opponents',
        'wheelSpinVel',
        'z',
        'speedZ',
        'speedY',
        'speedX',
        'targetSpeed',
        'rpm',
        'skid',
        'slip',
        'track',
        'trackPos',
        'angle',
        ]

        for k in sensors:
            if type(self.d.get(k)) is list: # Handle list type data.
                if k == 'track': # Nice display for track sensors.
                    strout= str()
                    raw_tsens= ['%.1f'%x for x in self.d['track']]
                    strout+= ' '.join(raw_tsens[:9])+'_'+raw_tsens[9]+'_'+' '.join(raw_tsens[10:])
                elif k == 'opponents': # Nice display for opponent sensors.
                    strout= str()
                    for osensor in self.d['opponents']:
                        if   osensor >190: oc= '_'
                        elif osensor > 90: oc= '.'
                        elif osensor > 39: oc= chr(int(osensor/2)+97-19)
                        elif osensor > 13: oc= chr(int(osensor)+65-13)
                        elif osensor >  3: oc= chr(int(osensor)+48-3)
                        else: oc= '?'
                        strout+= oc
                    strout= ' -> '+strout[:18] + ' ' + strout[18:]+' <-'
                else:
                    strlist= [str(i) for i in self.d[k]]
                    strout= ', '.join(strlist)
            else: # Not a list type of value.
                if k == 'gear': # This is redundant now since it's part of RPM.
                    gs= '_._._._._._._._._'
                    p= int(self.d['gear']) * 2 + 2  # Position
                    l= '%d'%self.d['gear'] # Label
                    if l=='-1': l= 'R'
                    if l=='0':  l= 'N'
                    strout= gs[:p]+ '(%s)'%l + gs[p+3:]
                elif k == 'damage':
                    strout= '%6.0f %s' % (self.d[k], bargraph(self.d[k],0,10000,50,'~'))
                elif k == 'fuel':
                    strout= '%6.0f %s' % (self.d[k], bargraph(self.d[k],0,100,50,'f'))
                elif k == 'speedX':
                    cx= 'X'
                    if self.d[k]<0: cx= 'R'
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k],-30,300,50,cx))
                elif k == 'speedY': # This gets reversed for display to make sense.
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k]*-1,-25,25,50,'Y'))
                elif k == 'speedZ':
                    strout= '%6.1f %s' % (self.d[k], bargraph(self.d[k],-13,13,50,'Z'))
                elif k == 'z':
                    strout= '%6.3f %s' % (self.d[k], bargraph(self.d[k],.3,.5,50,'z'))
                elif k == 'trackPos': # This gets reversed for display to make sense.
                    cx='<'
                    if self.d[k]<0: cx= '>'
                    strout= '%6.3f %s' % (self.d[k], bargraph(self.d[k]*-1,-1,1,50,cx))
                elif k == 'stucktimer':
                    if self.d[k]:
                        strout= '%3d %s' % (self.d[k], bargraph(self.d[k],0,300,50,"'"))
                    else: strout= 'Not stuck!'
                elif k == 'rpm':
                    g= self.d['gear']
                    if g < 0:
                        g= 'R'
                    else:
                        g= '%1d'% g
                    strout= bargraph(self.d[k],0,10000,50,g)
                elif k == 'angle':
                    asyms= [
                          "  !  ", ".|'  ", "./'  ", "_.-  ", ".--  ", "..-  ",
                          "---  ", ".__  ", "-._  ", "'-.  ", "'\.  ", "'|.  ",
                          "  |  ", "  .|'", "  ./'", "  .-'", "  _.-", "  __.",
                          "  ---", "  --.", "  -._", "  -..", "  '\.", "  '|."  ]
                    rad= self.d[k]
                    deg= int(rad*180/PI)
                    symno= int(.5+ (rad+PI) / (PI/12) )
                    symno= symno % (len(asyms)-1)
                    strout= '%5.2f %3d (%s)' % (rad,deg,asyms[symno])
                elif k == 'skid': # A sensible interpretation of wheel spin.
                    frontwheelradpersec= self.d['wheelSpinVel'][0]
                    skid= 0
                    if frontwheelradpersec:
                        skid= .5555555555*self.d['speedX']/frontwheelradpersec - .66124
                    strout= bargraph(skid,-.05,.4,50,'*')
                elif k == 'slip': # A sensible interpretation of wheel spin.
                    frontwheelradpersec= self.d['wheelSpinVel'][0]
                    slip= 0
                    if frontwheelradpersec:
                        slip= ((self.d['wheelSpinVel'][2]+self.d['wheelSpinVel'][3]) -
                              (self.d['wheelSpinVel'][0]+self.d['wheelSpinVel'][1]))
                    strout= bargraph(slip,-5,150,50,'@')
                else:
                    strout= str(self.d[k])
            out+= "%s: %s\n" % (k,strout)
        return out

class DriverAction():
    '''What the driver is intending to do (i.e. send to the server).
    Composes something like this for the server:
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus 0)(meta 0) or
    (accel 1)(brake 0)(gear 1)(steer 0)(clutch 0)(focus -90 -45 0 45 90)(meta 0)'''
    def __init__(self):
       self.actionstr= str()
       self.d= { 'accel':0.2,
                   'brake':0,
                  'clutch':0,
                    'gear':1,
                   'steer':0,
                   'focus':[-90,-45,0,45,90],
                    'meta':0
                    }

    def clip_to_limits(self):
        """There pretty much is never a reason to send the server
        something like (steer 9483.323). This comes up all the time
        and it's probably just more sensible to always clip it than to
        worry about when to. The "clip" command is still a snakeoil
        utility function, but it should be used only for non standard
        things or non obvious limits (limit the steering to the left,
        for example). For normal limits, simply don't worry about it."""
        self.d['steer']= clip(self.d['steer'], -1, 1)
        self.d['brake']= clip(self.d['brake'], 0, 1)
        self.d['accel']= clip(self.d['accel'], 0, 1)
        self.d['clutch']= clip(self.d['clutch'], 0, 1)
        if self.d['gear'] not in [-1, 0, 1, 2, 3, 4, 5, 6]:
            self.d['gear']= 0
        if self.d['meta'] not in [0,1]:
            self.d['meta']= 0
        if type(self.d['focus']) is not list or min(self.d['focus'])<-180 or max(self.d['focus'])>180:
            self.d['focus']= 0

    def __repr__(self):
        self.clip_to_limits()
        out= str()
        for k in self.d:
            out+= '('+k+' '
            v= self.d[k]
            if not type(v) is list:
                out+= '%.3f' % v
            else:
                out+= ' '.join([str(x) for x in v])
            out+= ')'
        return out
        return out+'\n'

    def fancyout(self):
        '''Specialty output for useful monitoring of bot's effectors.'''
        out= str()
        od= self.d.copy()
        od.pop('gear','') # Not interesting.
        od.pop('meta','') # Not interesting.
        od.pop('focus','') # Not interesting. Yet.
        for k in sorted(od):
            if k == 'clutch' or k == 'brake' or k == 'accel':
                strout=''
                strout= '%6.3f %s' % (od[k], bargraph(od[k],0,1,50,k[0].upper()))
            elif k == 'steer': # Reverse the graph to make sense.
                strout= '%6.3f %s' % (od[k], bargraph(od[k]*-1,-1,1,50,'S'))
            else:
                strout= str(od[k])
            out+= "%s: %s\n" % (k,strout)
        return out

def destringify(s):
    '''makes a string into a value or a list of strings into a list of
    values (if possible)'''
    if not s: return s
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
        
        
        
def drive(c):
    S, R = c.S.d, c.R.d

    # ---------- helpers ----------
    def smoothstep(x, e0, e1):
        x = clip((x - e0) / float(e1 - e0), 0.0, 1.0)
        return x * x * (3.0 - 2.0 * x)

    def lerp(a, b, t):
        return a + (b - a) * t

    # ---------- sensors ----------
    speed_x   = float(S.get('speedX', 0.0))
    angle     = float(S.get('angle', 0.0))
    track_pos = float(S.get('trackPos', 0.0))
    track     = S.get('track', [200.0] * 19)
    wheel     = S.get('wheelSpinVel', [0.0, 0.0, 0.0, 0.0])
    dist_from_start = float(S.get('distFromStart', 0.0))

    # ---------- lap timing and risk mode ----------
    # Track lap timing: aggressive mode from 101-113 seconds (1:41-1:53)
    prev_dist = float(getattr(drive, "_prev_dist", 0.0))
    lap_start_time = float(getattr(drive, "_lap_start_time", time.time()))
    
    # Detect new lap (distance resets or goes backwards significantly)
    if dist_from_start < prev_dist - 100.0:  # New lap started
        lap_start_time = time.time()
        drive._lap_start_time = lap_start_time
    
    drive._prev_dist = dist_from_start
    lap_elapsed = time.time() - lap_start_time
    # Aggressive mode: after 1:41 but before 1:53
    aggressive_mode = 101.0 < lap_elapsed <= 113.0

    if not isinstance(track, list) or len(track) < 19:
        track = [200.0] * 19
    if not isinstance(wheel, list) or len(wheel) < 4:
        wheel = [0.0, 0.0, 0.0, 0.0]

    # Forward sensors
    fwd7, fwd8, fwd9, fwd10, fwd11 = track[7], track[8], track[9], track[10], track[11]
    fwd_min = max(min(fwd7, fwd8, fwd9, fwd10, fwd11), 1.0)
    lr_diff = abs(fwd11 - fwd7)

    # ---------- straight / corner ----------
    wide = clip((fwd_min - 65.0) / 110.0, 0.0, 1.0)
    bal  = 1.0 - clip(lr_diff / 55.0, 0.0, 1.0)
    ang  = 1.0 - clip(abs(angle) / 0.12, 0.0, 1.0)
    straightness = wide * bal * (0.6 + 0.4 * ang)
    corner_strength = clip(1.0 - straightness, 0.0, 1.0)

    # ---------- apex targeting ----------
    turn_dir = -1.0 if fwd11 < fwd7 else 1.0
    APEX = 0.62
    desired_line = lerp(0.0, (-turn_dir) * APEX, corner_strength)

    prev_line = float(getattr(drive, "_prev_line", 0.0))
    line = 0.90 * prev_line + 0.10 * desired_line
    drive._prev_line = line

    # ---------- steering ----------
    kp_pos = 0.70
    kp_ang = 10.0
    pos_err = track_pos - line

    steer_raw = -(kp_pos * pos_err) + (kp_ang * angle)
    steer_raw /= (1.0 + speed_x / 105.0)
    steer_raw = clip(steer_raw, -1.0, 1.0)

    prev_steer = float(getattr(drive, "_prev_steer", 0.0))
    alpha = 0.18 + 0.22 * corner_strength
    steer = (1.0 - alpha) * prev_steer + alpha * steer_raw
    steer = clip(steer, -1.0, 1.0)
    drive._prev_steer = steer
    R['steer'] = steer

    # ---------- target speed ----------
    # Adjust danger based on lap timing - aggressive mode only 1:41-1:53
    if aggressive_mode:
        # Aggressive: lower danger = faster on straights
        danger = (10.0 / fwd_min) + (0.008 * lr_diff) + (0.30 * corner_strength)
        MAX_SPEED = 245.0 + 120.0 * straightness
    else:
        # Cautious (default): more conservative
        danger = (18.0 / fwd_min) + (0.010 * lr_diff) + (0.35 * corner_strength)
        MAX_SPEED = 220.0 + 95.0 * straightness
    
    MIN_SPEED = 45.0
    target_speed = clip(MAX_SPEED / (1.0 + danger), MIN_SPEED, MAX_SPEED)

    # ---------- throttle / brake ----------
    if speed_x > target_speed:
        brake = clip((speed_x - target_speed) / (25.0 + 10.0 * corner_strength), 0.0, 0.9)
        accel = 0.0
    else:
        accel = clip((target_speed - speed_x) / 15.0, 0.25, 1.0)
        brake = 0.0

    if straightness > 0.82 and abs(steer) < 0.05 and abs(angle) < 0.03 and abs(track_pos) < 0.35:
        accel = 1.0
        brake = 0.0

    accel *= (1.0 - (0.20 + 0.50 * corner_strength) * abs(steer))

    # =========================================================
    # Gearbox with STRONG 3<->4 suppression
    # =========================================================
    tick = int(getattr(drive, "_tick", 0)) + 1
    drive._tick = tick

    gear = int(getattr(drive, "_gear", R.get('gear', 1)))
    gear_enter_tick = int(getattr(drive, "_gear_enter_tick", 0))

    # Slip proxy
    rear = float(wheel[2] + wheel[3])
    front = float(wheel[0] + wheel[1])
    slip = rear - front

    # Only shift when stable (prevents twitch)
    SHIFT_BLOCK_STEER = 0.12     # relaxed for more shifting opportunities
    SHIFT_BLOCK_SLIP  = 1.6      # relaxed for more shifting opportunities
    stable_for_shift = (abs(steer) < SHIFT_BLOCK_STEER and abs(angle) < 0.07 and slip < SHIFT_BLOCK_SLIP)

    # Longer holds specifically for 3 and 4 (kills residual oscillation)
    HOLD = {1: 10, 2: 12, 3: 20, 4: 20, 5: 16, 6: 16}
    can_shift = (tick - gear_enter_tick) >= HOLD.get(gear, 12)

    # Gear caps
    if corner_strength > 0.85:
        gear_cap = 3
    elif corner_strength > 0.65:
        gear_cap = 4
    elif corner_strength > 0.45:
        gear_cap = 5
    else:
        gear_cap = 6

    if not (straightness > 0.75 and speed_x > 135.0):
        gear_cap = min(gear_cap, 5)
    if not (straightness > 0.60 or speed_x > 125.0):
        gear_cap = min(gear_cap, 4)

    # Min allowed gear by speed (prevents downshift shock)
    MIN_GEAR_BY_SPEED = [
        (150.0, 5),
        (120.0, 4),
        (90.0,  3),
        (55.0,  2),
        (0.0,   1),
    ]
    min_allowed_gear = 1
    for spd, gmin in MIN_GEAR_BY_SPEED:
        if speed_x >= spd:
            min_allowed_gear = gmin
            break

    gear_cap = max(gear_cap, min_allowed_gear)
    gear = max(gear, min_allowed_gear)
    gear = min(gear, gear_cap)

    # ---- EVEN STRONGER 3<->4 anti-hunt ----
    # Larger hysteresis + longer lock + more stability required.
    UP_34   = 110.0   # raised for more stable 3->4 shifts
    DOWN_43 = 71.0    # lowered for more aggressive downshifting
    LOCK34_TICKS = 32 # reduced for less hunting behavior

    lock34_until = int(getattr(drive, "_lock34_until", 0))
    stable_cnt = int(getattr(drive, "_stable_cnt", 0))
    stable_now = (straightness > 0.68 and abs(steer) < 0.08 and abs(angle) < 0.055 and slip < 1.3)
    if stable_now:
        stable_cnt = min(stable_cnt + 1, 60)
    else:
        stable_cnt = max(stable_cnt - 3, 0)
    drive._stable_cnt = stable_cnt

    if can_shift and stable_for_shift:
        if gear == 3:
            # 3->4 only if REALLY stable for a while
            if tick >= lock34_until and stable_cnt >= 16 and speed_x >= UP_34 and gear_cap >= 4:
                gear = 4
                gear_enter_tick = tick
                lock34_until = tick + LOCK34_TICKS
        elif gear == 4:
            # 4->3 only if clearly slow OR corner demand is high and you're over-speeding
            need_down = (speed_x <= DOWN_43) or (corner_strength > 0.75 and target_speed < 0.90 * speed_x)
            if tick >= lock34_until and need_down and min_allowed_gear <= 3:
                gear = 3
                gear_enter_tick = tick
                lock34_until = tick + LOCK34_TICKS
        else:
            # Other gears: conservative, one-step shifts
            UP   = {1: 18.0, 2: 42.0, 4: 130.0, 5: 180.0}
            DOWN = {2: 13.0, 3: 30.0, 5: 110.0, 6: 165.0}

            if gear < gear_cap and speed_x >= UP.get(gear, 999.0):
                gear += 1
                gear_enter_tick = tick
            elif gear > min_allowed_gear and speed_x <= DOWN.get(gear, -1.0):
                if target_speed < (0.90 * speed_x) or corner_strength > 0.75:
                    gear -= 1
                    gear_enter_tick = tick

    # Enforce caps after decisions
    gear = max(gear, min_allowed_gear)
    gear = min(gear, gear_cap)

    # Save
    gear = int(clip(gear, 1, 6))
    R['gear'] = gear
    drive._gear = gear
    drive._gear_enter_tick = gear_enter_tick
    drive._lock34_until = lock34_until

    # ---------- launch control ----------
    if gear == 1:
        accel = min(accel, 0.80 + 0.20 * smoothstep(speed_x, 4.0, 20.0))
    elif gear == 2:
        accel = min(accel, 0.85 + 0.15 * smoothstep(speed_x, 10.0, 40.0))

    # ---------- traction control ----------
    if slip > 1.4:
        accel *= (1.0 - 0.8 * clip((slip - 1.4) / 5.0, 0.0, 1.0))

    # ---------- output ----------
    R['accel'] = clip(accel, 0.0, 1.0)
    R['brake'] = clip(brake, 0.0, 0.9)
    return

if __name__ == "__main__":
    C=Client()
    for step in range(C.maxSteps,0,-1):
        C.get_servers_input()
        drive(C)
        # , "brake:", C.R.d['brake'], "steer:", C.R.d['steer'], "accel:", C.R.d['accel']
        # print ("Track: ", C.S.d['track'])
        C.respond_to_server()
    C.shutdown()
