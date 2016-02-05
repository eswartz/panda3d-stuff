'''
Class for controlling the camera like an FPS.

The W/S/A/D keys move & strafe.
Up/down also do W/S.
Left/right arrow turn.
Backspace turns around.

PgUp/PgDown adjust the view angle up/down. 

Created on Feb 25, 2015

@author: ejs
'''
from math import pi, sin, cos

from panda3d.core import loadPrcFile, Vec3, Vec3F, PandaNode,\
    KeyboardButton, WindowProperties, Camera
from direct.task.TaskManagerGlobal import taskMgr
import math
loadPrcFile("./myconfig.prc")
 
from direct.task import Task

if False:
    globalClock = 0
    
DEG_TO_RAD = pi/180 #translates degrees to radians for sin and cos

# movement
ACCELERATION = 25 

JUMP_GRAV = 9.8

JUMP_HEIGHT = 4
JUMP_TIME = 0.5
# height - scale*(time)^2 = 0
# height = scale*(time)^2
# height/(time)^2 = scale
JUMP_SCALE = JUMP_HEIGHT / JUMP_TIME ** 2

# number of steps before new velocity takes over
STEPS = 8

class TurnSmoother(object):
    def __init__(self, minRate, maxRate, targetLag, rangeX):
        """
        @param minRate: minimum turn rate (degrees per second)
        @param maxRate: minimum turn rate (degrees per second)
        @param targetLag: how long it takes to retarget (2=fastest)
        @param rangeX: if not None, the min and max angles allowed
        """
        self.turnTime = 0
        self.turnAccelTime = 1.0 / 30
        self.minRate = minRate
        self.maxRate = maxRate
        self.targetLag = targetLag
        self.range = rangeX
        
        self.turnTick = self.turnAccelTime / 5
        self.turnIncrMax = 1 << 5
        self.turnRate = 0

        self.heading = 0        
        self.debug = False
        self.reset()
        
    def setDebug(self, debug):
        self.debug = debug
        
    def setHeading(self, heading):
        self.heading = heading
        if self.debug:
            print "setHeading:",self.heading

    def getHeading(self):
        return self.heading
    
    def setTurnRate(self, turnRate):
        self.turnRate = turnRate   
    def getTurnRate(self):
        return self.turnRate
        
    def reset(self):
        if self.debug:
            print "reset"
        self.turnRate = 0
        self.turnTime = 0
        self.turnIncr = 0
        self.turnDirec = 0
        self.targeting = False
        self.curMaxRate = self.maxRate

    def updateTurn(self, direc, dt):
        self.targeting = False
        self.curMaxRate = self.maxRate
        
        if (direc > 0 and self.turnIncr <= 0) or (direc < 0 and self.turnIncr >= 0):
            # switching direction, restart
            self.turnDirec = direc
            self.turnIncr = direc * self.minRate
        else:
            self.updateTowards(dt)
            
            if abs(self.turnRate) >= self.maxRate:
                if self.debug:
                    print "updateTurn, reduce rate"
                self.turnIncr = self.turnDirec * self.turnIncrMax
                self.turnRate = self.turnDirec * self.maxRate
            
    def updateTowards(self, dt):
        """ Update the rate for this segment of time.  Does not limit! """
        self.turnIncr <<= 1
        self.turnRate += self.turnIncr
        
        
    def unTurn(self, dt):
        if self.turnDirec != 0:
            if not self.turnIncr:
                self.turnIncr = self.turnDirec * self.minRate   # shouldn't happen
                
        if self.turnRate != 0:
            self.turnRate /= 2.0
        
            if abs(self.turnRate) < 1:
                self.turnRate = 0
                self.turnIncr = 0

            if self.debug:                
                print "unturn:",self.turnIncr, self.turnRate

    def setTarget(self, angle):
        if not self.targeting and angle != int(self.heading) % 360:
            if self.debug:
                print "setTarget:",angle
            self.targeting = True
            self.target = angle
            
            if abs(self.heading - angle) <= 180: 
                self.turnDirec = 1
            elif abs(self.heading - 360 - angle) <= 180: 
                self.turnDirec = 1
                self.target += 360
            else:
                self.turnDirec = -1

            self.turnIncr = self.turnDirec * self.maxRate
            self.turnRate = self.turnDirec * self.maxRate

    def updateTarget(self, dt):
        if self.debug:
            print "targeting", self.target, "from", self.heading, "at", self.turnDirec, "=", self.turnIncr
#         self.updateTowards(dt)
#         
#         if abs(self.turnRate) >= self.maxRate * self.targetLag:
#             self.turnIncr = self.turnDirec * self.turnIncrMax
#             self.turnRate = self.turnDirec * self.maxRate * self.targetLag
#         
#         # not clamped
#         self.heading = (self.heading + self.turnRate * dt)
# 
#         if (self.turnDirec > 0 and self.heading >= self.target) or (self.turnDirec < 0 and self.heading <= self.target):
#             self.heading = self.target
#             self.turnIncr = self.turnDirec
#             self.turnRate = self.turnDirec * self.minRate 
#             self.targeting = False

        self.heading = (self.heading * (self.targetLag - 1) + self.target) / float(self.targetLag)

        self.turnRate = 1
        
        if abs(self.heading - self.target) < 1:
            self.heading = self.target % 360
            self.targeting = False
            
    def update(self, dt):
        if self.targeting:
            self.updateTarget(dt)
        else:
            if self.turnRate:
                if self.debug:
                    print "update for turnRate=",self.turnRate,"from",self.heading
                self.heading = (self.heading + self.turnRate * dt)
                
                if self.range:
                    if self.turnRate < 0 and self.heading < self.range[0]:
                        if self.debug:
                            print "clamp",self.heading,"to",self.range[0]
                        self.heading = self.range[0]
                    elif self.turnRate > 0 and self.heading > self.range[1]:
                        if self.debug:
                            print "clamp",self.heading,"to",self.range[1]
                        self.heading = self.range[1]
                else:
                    self.heading %= 360.0
                
            else:
                self.heading = int(self.heading)

        return self.heading

class FpsController(object):
    def __init__(self, base, player=None):
        
        self.base = base
        
        if not player:
            player = self.base.cam
            
        self.player = player
        self.lastSetPos = None

        # Disable the camera trackball controls.
        self.base.disableMouse()

        self.mouseLook = False
        
        self.setupKeys()
        
        self.headingTurner = TurnSmoother(8, 180, 16, None)
        
        self.lookTurner = TurnSmoother(8, 90, 4, (-90, 90))

        self.tickTime = 0.0
        self.tickQuantum = 1 / 60.0
        
        self.reset()

        self.setupGameLoop()
        
    def isMouseLook(self):
        return self.mouseLook
    
    def setMouseLook(self, mouseLook):
        self.mouseLook = mouseLook
        self.mouseGrabbed = mouseLook   # for now

        wp = WindowProperties()
        wp.setMouseMode(mouseLook and WindowProperties.MConfined or WindowProperties.MAbsolute)
        wp.setCursorHidden(mouseLook)
        self.base.win.requestProperties(wp)
       
        self.base.taskMgr.doMethodLater(0, self.resolveMouse, "resolve mouse")

    def resolveMouse(self, t):
        wp = self.base.win.getProperties()
        self.mouseGrabbed = wp.getMouseMode() == WindowProperties.MConfined
        print "ACTUAL GRAB MODE:", self.mouseGrabbed
        
        # re-center mouse, or else we get no good delta
        if not wp.getFullscreen():
            ret = self.base.win.movePointer(0, self.base.win.getXSize() / 2, self.base.win.getYSize() / 2)
            print "movePointer:", ret
        
    def reset(self):
        self.truePos = self.player.getPos()
        
        self.headingTurner.reset()
        self.reversing = False
        
        self.jumping = False
        self.jumpTime = 0
        self.jumpZ = 0

        self.lookTurner.reset()
        self.lookSticky = False
        
        self.bob = Vec3(0, 0, 0)
                
        self.setVelocity(self.player, Vec3(0, 0, 0))
        self.walkCycle = 0
        
        self.flyMode = False
        
        self.lastMouseX, self.lastMouseY = None, None
        
        
    def getPos(self):
        return self.player.getPos()
    
        
    def setPos(self, pos):
        self.player.setFluidPos(pos)
        self.truePos = pos
        self.lastSetPos = pos

    def setHpr(self, hpr):
        self.lookSticky = True
        self.player.setHpr(hpr)
        self.headingTurner.setHeading(self.player.getH())
        self.lookTurner.setHeading(self.player.getP())

    def getHeading(self):
        return self.player.getH()
    def getLookAngle(self):
        return self.player.getP()
    
    def getHpr(self):
        return Vec3(self.getHeading(), self.getLookAngle(), 0)
    
    def setFlyMode(self, on):
        self.flyMode = on
    
    def setupKeys(self):
        #A dictionary of what keys are currently being pressed
        #The key events update this list, and our task will query it as input
        self.keys = {"turnLeft" : 0, "turnRight": 0,
                     "front": 0, "back": 0,
                     "strafeLeft": 0, "strafeRight": 0,
                     "reverse" : 0,
                     "up": 0 , "down": 0,
                     "lookUp" : 0, "lookDown" : 0, "lookReset": 0,
                     "jump": 0 }
    
        self.lastKeys = []
        # Other keys events set the appropriate value in our key dictionary
        self.mapOnOffKey("arrow_left", "turnLeft")
        self.mapOnOffKey("arrow_right", "turnRight")
        self.mapOnOffKey("w", "front")
        self.mapOnOffKey("s", "back")
        self.mapOnOffKey("arrow_up", "front")
        self.mapOnOffKey("arrow_down", "back")
        self.mapOnOffKey("a", "strafeLeft")
        self.mapOnOffKey("d", "strafeRight")
        self.mapOnOffKey("[", "up")
        self.mapOnOffKey("]", "down")
        self.mapOnOffKey("backspace", "reverse")
        
        self.mapOnOffKey("page_up", "lookUp")
        self.mapOnOffKey("page_down", "lookDown")
        self.mapOnOffKey("home", "lookReset")
        
        self.mapOnOffKey("space", "jump")

    def mapOnOffKey(self, name, token):
        self.base.accept(name, self.setKey, [token, 1])
        self.base.accept(name + "-up",  self.setKey, [token, 0])
        
    #As described earlier, this simply sets a key in the self.keys dictionary to
    #the given value
    def setKey(self, key, val): 
        self.keys[key] = val

    def setupGameLoop(self):
        self.fpsCameraTask = taskMgr.add(self.fpsCameraHandler, "fpsCameraHandler")
        
    def fpsCameraHandler(self, task):
        self.tickTime += globalClock.getDt() # @UndefinedVariable
        while self.tickTime >= self.tickQuantum:
            self.movePlayer(self.player, self.tickTime)  
            self.tickTime -= self.tickQuantum

        return Task.cont

    def movePlayer(self, player, dt):
        mw = self.base.mouseWatcherNode

        heading = self.headingTurner.getHeading()  # Heading is the roll value for this model
        lookAngle = player.getP()

        # y is forward/back, x is left/right, z is up/down 
        
        curVel = self.getVelocity(player)
        
        # Accelerate in the direction the player is currently facing
        y = 0
        if self.keys["front"]:
            y = 1
        elif self.keys["back"]:
            y = -1
        x = 0
        if self.keys["strafeLeft"]:
            x = -1
        elif self.keys["strafeRight"]:
            x = 1
        
        z = 0
        if self.keys["up"]:
            z = 1
        elif self.keys["down"]:
            z = -1
        
        if mw.isButtonDown(KeyboardButton.shift()):
            x *= 2
            y *= 2
            
        if self.keys["jump"]:
            if not self.jumping:
                self.jumpTime = 0
                self.jumping = True
                self.jumpZ = 0

        now = globalClock.getFrameTime() 
        if x or y:
            if not self.walkCycle:
                self.walkCycle = now
            
        heading_rad = DEG_TO_RAD * (360 - heading)
        
        newFwdBack = Vec3(sin(heading_rad)*y, cos(heading_rad) * y, 0)
        
        if self.flyMode:
            newFwdBack.z = sin(DEG_TO_RAD * lookAngle) * y
         
        newStrafe = Vec3(-sin(heading_rad-pi/2) * x, -cos(heading_rad-pi/2)*x, 0)
        
        newUpDown = Vec3(0, 0, z)
        
        newVel = (newFwdBack + newStrafe + newUpDown) * ACCELERATION
        playerVel = (curVel * (STEPS-1) + newVel) / STEPS
        
        self.setVelocity(player, playerVel)
        
        if self.mouseLook and mw.hasMouse():
            x, y = mw.getMouseX(), mw.getMouseY()
            
            dx, dy = x, y
            
            self.headingTurner.setTurnRate(math.sin(dx) * -1440)
            #self.headingTurner.setTarget(dx / pi)
            self.lookTurner.setTurnRate(math.sin(dy) * 1440)
            #self.lookTurner.setTarget(y * 90)
            
            self.lastMouseX, self.lastMouseY = x, y
            
            if self.mouseGrabbed:
                self.base.win.movePointer(0, 
                                      int(self.base.win.getProperties().getXSize() / 2),
                                      int(self.base.win.getProperties().getYSize() / 2))

                
            
        # Change heading if left or right is being pressed
        now = globalClock.getFrameTime()
        if self.keys["turnRight"]:
            self.headingTurner.updateTurn(-1, dt)

        elif self.keys["turnLeft"]:
            self.headingTurner.updateTurn(1, dt)

        elif self.keys["reverse"]:
            self.headingTurner.setTarget(heading + 180)
            
        elif not self.mouseLook:
            self.headingTurner.unTurn(dt)
                
        heading = self.headingTurner.update(dt)
            
        # Adjust view angle
        
        if self.keys["lookDown"]:
            self.lookTurner.updateTurn(-1, dt)
            self.lookSticky = True
        elif self.keys["lookUp"]:
            self.lookTurner.updateTurn(1, dt)
            self.lookSticky = True
        elif self.keys["lookReset"]:
            self.lookTurner.setTarget(0)
            self.lookSticky = False
        elif not self.mouseLook:
            self.lookTurner.unTurn(dt)
    
            if self.lookTurner.getTurnRate() == 0:            
                if (x or y or self.jumpZ) and not self.mouseLook:
                    self.lookSticky = False

            if not self.lookSticky:
                self.lookTurner.setTarget(0)                    
            
        lookAngle = self.lookTurner.update(dt)
            

        player.setH(heading)
        
        player.setP(lookAngle)
        
        
        # Finally, update the position as with any other object
        self.updatePos(player, now, dt)

    def forward(self, units, forceLook=False):
        heading_rad = DEG_TO_RAD * (360 - self.getHeading())
        newFwdBack = Vec3(sin(heading_rad)*units, cos(heading_rad) * units, 0)
        if self.flyMode or forceLook:
            newFwdBack.z = sin(DEG_TO_RAD * self.getLookAngle()) * units
        return newFwdBack
        
    def step(self, t, dt, maxT):
        """ Calculate the increment in the fraction per second, given 
        t = now - startTime, maxT = max time, and dt = delta between last and current.
        
        Follow integral(1,N) 1/(2^t) dt = 1/(2^t * ln 2)
        """
         
        print "from",t,"plus",dt
        lo = 1.0 / (maxT * math.pow(2, maxT - t))
        hi = 1.0 / (maxT * math.pow(2, maxT - t - dt))
        return (hi - lo) / math.log(2)

    def getBob(self):
        """ Get the head-bob vector. """
        return self.bob
    
    def updatePos(self, obj, now, dt):
        vel = self.getVelocity(obj)
        
        if self.lastSetPos:
            self.truePos += obj.getPos() - self.lastSetPos
            
        newPos = self.truePos + (vel*dt)
        
        self.truePos = newPos

        pos = Vec3F(newPos)
        if not self.jumping:
            if self.keys["front"] or self.keys["back"] or self.keys["strafeLeft"] or self.keys["strafeRight"]:
                walkZ = sin((now - self.walkCycle) * 1.5 * 2 * pi) * 0.25
                self.bob.z = walkZ 
                #pos.z = self.truePos.z + walkZ
            else:
                self.bob.z = self.bob.z * (STEPS-1) / STEPS
                #pos.z = (obj.getZ() * (STEPS-1) / STEPS)
                
        else:
            if False:
                if self.jumpTime >= JUMP_TIME*2:
                    self.jumping = False
                elif self.jumpTime <= JUMP_TIME:
                    self.jumpZ += JUMP_SCALE*dt
                self.jumpZ -= JUMP_GRAV * dt
                
                self.jumpTime += dt

            else:
                self.jumpTime += dt
                if self.jumpTime >= JUMP_TIME*2:
                    self.jumping = False
                    self.jumpZ = 0
                else:
                    self.jumpZ = JUMP_HEIGHT - JUMP_SCALE*((self.jumpTime - JUMP_TIME) ** 2)

            pos.z += self.jumpZ

        
#         print self.truePos,vel,pos
        self.lastSetPos = pos
        obj.setPos(pos)
        
    def setVelocity(self, obj, val):
        obj.setPythonTag("velocity", val)
    
    def getVelocity(self, obj):
        return obj.getPythonTag("velocity")

    
    def setDebugHeading(self, debug):
        self.headingTurner.setDebug(debug)

    
    
    
    
    

    
    
    
    

