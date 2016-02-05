
"""
Panda3D Debug Utilities
"""
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode, WindowProperties, SceneGraphAnalyzerMeter
from panda3d.bullet import BulletDebugNode

class DebugHelper(object):
    def __init__(self, base, render, world):
        self.base = base
        self.render = render
        self.world = world
        
        self.helps = []
        self.helpStrs = []
        
        if self.world:
            self.debugNP = self.render.attachNewNode(BulletDebugNode('Debug'))
            self.world.setDebugNode(self.debugNP.node())
        else:
            self.debugNP = None
        
        base.accept("f1", self.toggleHelp)
        self.helpStrs.append("F1: Help")
        
        base.accept("f2", self.toggleWireframe)
        self.helpStrs.append("F2: Toggle Wireframe")
        base.accept("f3", self.toggleDebugNode)
        self.helpStrs.append("F3: Toggle Debug Node")
        
        self.meter = None
        base.accept("f4", self.showRenderInfo)
        self.helpStrs.append("F4: Analyze Scene")
        base.accept("f5", self.showRenderMeter)
        self.helpStrs.append("F5: Show Render Meter")
        
        self.audioVolume = None
        base.accept("f8", self.toggleAudio)
        self.helpStrs.append("F8: Toggle Audio Mute")
        
        self.hasMouse = True
        base.accept("f10", self.toggleMouseFocus)
        self.helpStrs.append("F10: Toggle Mouse")

        base.accept("f12", self.debugMouse)
        self.helpStrs.append("F12: Debug Mouse")
        
        ####
        
        self.base.accept("v", self.base.bufferViewer.toggleEnable)
        self.base.accept("V", self.base.bufferViewer.toggleEnable)
        self.helpStrs.append("v/V: Toggle Buffer Viewer")
        
        self.base.bufferViewer.setPosition("llcorner")
        self.base.bufferViewer.setCardSize(1.0, 0.0)

        self.fpscamera = None
        self.bulletPlayerNode = None
        
    def addBulletPlayer(self, bulletNP, bulletNode):
        self.bulletPlayerNP = bulletNP
        self.bulletPlayerNode = bulletNode
        self.isPlayerSolid = True
        
        self.base.accept("f11", self.togglePlayerSolid)
        self.helpStrs.append("F11: Toggle Player Solidity")
        
    def addFpsCamera(self, fpscamera):
        self.fpscamera = fpscamera
        
        self.isOOBCamera = False
        self.base.accept("f9", self.toggleOutOfBodyCamera)
        self.helpStrs.append("F9: Toggle Out-of-body Camera")

    def toggleMouseFocus(self):
        self.hasMouse = not self.hasMouse
        wp = WindowProperties()
        if self.hasMouse:
            wp.setMouseMode(WindowProperties.MAbsolute)
            if self.fpscamera:
                self.fpscamera.setEnabled(False)
        else:
            wp.setMouseMode(WindowProperties.MRelative)
            if self.fpscamera:
                self.fpscamera.setEnabled(True)
        wp.setCursorHidden(self.hasMouse)
        self.base.win.requestProperties(wp)
        
    def toggleHelp(self):
        if self.helps:
            for helpNP in self.helps:
                helpNP.removeNode()
            self.helps = []
        else:
            line = 0
            self.helps.append(self.genLabelText("Help", line))
            for h in self.helpStrs:
                line += 1
                self.helps.append(self.genLabelText("  " + h, line))
        
    def genLabelText(self, text, i):
        text = OnscreenText(text = text, pos = (-1.3, .5-.05*i), fg=(0,1,0,1),
                      align = TextNode.ALeft, scale = .05)
        return text

    def toggleWireframe(self):
        if self.render.hasRenderMode():
            self.render.clearRenderMode()
        else:
            self.render.setRenderModeWireframe()
            
    def toggleDebugNode(self):
        print "toggle debug node",self.debugNP
        if self.debugNP:
            if self.debugNP.isHidden():
                self.debugNP.show()
            else:
                self.debugNP.hide()

    def showRenderInfo(self):
        self.render.analyze()
        
    def showRenderMeter(self):
        if not self.meter:
            self.meter = SceneGraphAnalyzerMeter('meter', self.render.node())
            self.meter.setupWindow(self.base.win)
        else:
            self.meter.clearWindow()
            self.meter = None
            
    def toggleAudio(self):
        sfxMgr = self.base.sfxManagerList[0]
        if self.audioVolume is None:
            self.audioVolume = sfxMgr.getVolume()
            
            sfxMgr.setVolume(0)
        else:
            sfxMgr.setVolume(self.audioVolume)
            self.audioVolume = None
            
    def togglePlayerSolid(self):
        if self.isPlayerSolid:
            print "Player not solid"
            self.bulletPlayerGravity = self.bulletPlayerNode.getGravity()
            self.bulletPlayerNode.setGravity((0, 0, 0))
            self.bulletPlayerNode.notifyCollisions(False)
            self.bulletPlayerNode.setCollisionResponse(False)
            self.bulletPlayerCollideMask = self.bulletPlayerNP.getCollideMask()
            print "mask was:",self.bulletPlayerCollideMask
            self.bulletPlayerNP.setCollideMask(0)
            self.bulletPlayerShapes = list(self.bulletPlayerNode.getShapes())
            #for s in self.bulletPlayerShapes:
            #    self.bulletPlayerNode.removeShape(s)
        else:
            print "Player solid"
            self.bulletPlayerNode.setGravity(self.bulletPlayerGravity)
            self.bulletPlayerNode.notifyCollisions(True)
            self.bulletPlayerNode.setCollisionResponse(True)
            self.bulletPlayerNP.setCollideMask(self.bulletPlayerCollideMask)
            #for s in self.bulletPlayerShapes:
            #    self.bulletPlayerNode.addShape(s)
            
        self.isPlayerSolid = not self.isPlayerSolid
            
    def toggleOutOfBodyCamera(self):
        if not self.isOOBCamera:
            self.cameraPos = self.fpscamera.getTrueCamera()
            print "pos was",self.cameraPos
            self.fpscamera.setTrueCamera((0, -10, 5))
        else:
            self.fpscamera.setTrueCamera(self.cameraPos)
            
        self.isOOBCamera = not self.isOOBCamera

    def debugMouse(self):
        for mouse in self.base.pointerWatcherNodes:
            if mouse.hasMouse:
              print "NAME=", mouse.getName()
              print "X=", mouse.getMouseX()
              print "Y=", mouse.getMouseY()
              

def mapDebugKeys(app, render, world):
    return DebugHelper(app, render, world)
