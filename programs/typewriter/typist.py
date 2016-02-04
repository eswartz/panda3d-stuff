import random

from panda3d.core import Vec3, Point3, CompassEffect, Texture, PNMImage, TextureStage, PNMPainter, PNMBrush, \
    PNMTextMaker

from direct.interval.LerpInterval import LerpFunc, LerpPosInterval
from lib.scheduler import Scheduler
from lib.utils import fonts

global globalClock

class Typist(object):

    TARGETS = { 'paper': {
            'model': 'paper',
            'textureRoot': 'Front',
            'scale': Point3(0.85, 0.85, 1),
            'hpr' : Point3(0, 0, 0),
        }
    }

    def __init__(self, base, typewriterNP, sounds):
        self.base = base
        self.sounds = sounds
        self.typeIndex = 0

        self.typewriterNP = typewriterNP
        self.rollerNP = typewriterNP.find("**/roller")
        assert self.rollerNP
        self.carriageNP = typewriterNP.find("**/carriage")
        assert self.carriageNP
        self.baseCarriagePos = self.carriageNP.getPos()
        self.carriageBounds = self.carriageNP.getTightBounds()


        self.font = base.loader.loadFont('Harting.ttf', pointSize=32)
        self.pnmFont = PNMTextMaker(self.font)
        self.fontCharSize, _, _ = fonts.measureFont(self.pnmFont, 32)
        print "font char size: ",self.fontCharSize

        self.pixelsPerLine = int(round(self.pnmFont.getLineHeight()))

        self.target = None
        """ panda3d.core.NodePath """
        self.paperY = 0.0
        """ range from 0 to 1 """
        self.paperX = 0.0
        """ range from 0 to 1 """

        self.createRollerBase()

        self.tex = None
        self.texImage = None
        self.setupTexture()

        self.scheduler = Scheduler()
        task = self.base.taskMgr.add(self.tick, 'timerTask')
        task.setDelay(0.01)

    def tick(self, task):
        self.scheduler.tick(globalClock.getRealTime())
        return task.cont

    def createRollerBase(self):
        """ The paper moves such that it is tangent to the roller.

        This nodepath keeps a coordinate space relative to that, so that
        the paper can be positioned from (0,0,0) to (0,0,1) to "roll" it
        along the roller.
        """
        self.paperRollerBase = self.rollerNP.attachNewNode('rollerBase')
        self.paperRollerBase.setHpr(0, -20, 0)

        bb = self.rollerNP.getTightBounds()
        rad = abs(bb[0].y - bb[1].y) / 2
        center = Vec3((bb[0].x+bb[1].x)/2, (bb[0].y+bb[1].y)/2-rad*0.3, (bb[0].z+bb[1].z)/2)
        self.paperRollerBase.setPos(center)

        # don't let the typewriter scale the target in a funny way
        #self.compass = CompassEffect.make(self.base.render, CompassEffect.P_scale)
        #self.paperRollerBase.setEffect(self.compass)

    def setupTexture(self):
        self.texImage = PNMImage(1024, 1024)
        self.texImage.addAlpha()
        self.texImage.fillVal(255)
        self.texImage.alphaFillVal(0)

        self.tex = Texture('typing')
        self.tex.setMagfilter(Texture.FTLinear)
        self.tex.setMinfilter(Texture.FTLinear)

        self.typingStage = TextureStage('typing')
        self.typingStage.setMode(TextureStage.MModulate)

        self.tex.load(self.texImage)


    def start(self):
        self.target = None
        self.loadTarget('paper')

        self.hookKeyboard()

    def loadTarget(self, name):
        if self.target:
            self.target.removeNode()

        # load and transform the model
        target = self.TARGETS[name]
        self.target = self.base.loader.loadModel(target['model'])
        self.target.setScale(target['scale'])
        self.target.setHpr(target['hpr'])

        # put it in the world
        self.target.reparentTo(self.paperRollerBase)

        # apply the texture
        root = self.target
        if 'textureRoot' in target:
            root = self.target.find("**/" + target['textureRoot'])
            assert root

        root.setTexture(self.typingStage, self.tex)

        # reset
        self.paperX = self.paperY = 0.0
        self.schedRollPaper()
        self.moveCarriage()

    def hookKeyboard(self):
        """
        Hook events so we can respond to keypresses.
        """
        self.base.buttonThrowers[0].node().setKeystrokeEvent('keystroke')
        self.base.accept('keystroke', self.schedTypeCharacter)
        self.base.accept('enter', self.schedScroll)
        self.base.accept('backspace', self.schedBackspace)

        self.base.accept('arrow_up', lambda: self.schedAdjustPaper(-3))
        self.base.accept('arrow_up-repeat', lambda: self.schedAdjustPaper(-1))
        self.base.accept('arrow_down', lambda:self.schedAdjustPaper(3))
        self.base.accept('arrow_down-repeat', lambda:self.schedAdjustPaper(1))

        self.base.accept('arrow_left', lambda: self.schedAdjustCarriage(-1))
        self.base.accept('arrow_left-repeat', lambda: self.schedAdjustCarriage(-1))
        self.base.accept('arrow_right', lambda:self.schedAdjustCarriage(1))
        self.base.accept('arrow_right-repeat', lambda:self.schedAdjustCarriage(1))

    def paperCharWidth(self, pixels=None):
        if not pixels:
            pixels = self.fontCharSize[0]
        return float(pixels) / self.tex.getXSize()

    def paperLineHeight(self):
        return float(self.fontCharSize[1]) / self.tex.getYSize()

    def schedScroll(self):
        self.paperY += self.paperLineHeight()

        self.sounds['scroll'].play()

        self.schedRollPaper()
        self.schedResetCarriage()

    def schedBackspace(self):
        if self.scheduler.isQueueEmpty():
            def doit():
                if self.paperX > 0:
                    self.schedAdjustCarriage(-1)

            self.scheduler.schedule(0.01, doit)

    def schedResetCarriage(self):
        if self.paperX > 0.1:
            self.sounds['pullback'].play()

        here = self.calcCarriage(self.paperX)
        there = self.calcCarriage(0)

        posInterval = LerpPosInterval(
                self.carriageNP, self.paperX,
                there,
                startPos = here,
                blendType='easeIn')

        posInterval.setDoneEvent('carriageReset')

        def isReset():
            self.paperX = 0

        self.base.acceptOnce('carriageReset', isReset)

        posInterval.start()

    def calcCarriage(self, paperX):
        x = (0.5 - paperX) * 0.5 - 0.15

        bb = self.carriageBounds
        return self.baseCarriagePos + Point3(x * (bb[1].x-bb[0].x), 0, 0)

    def moveCarriage(self):
        pos = self.calcCarriage(self.paperX)
        self.carriageNP.setPos(pos)


    def schedMoveCarriage(self):
        self.scheduler.schedule(0.1, self.moveCarriage)

    def schedAdjustCarriage(self, by):
        def doit():
            self.paperX = max(0.0, min(1.0, self.paperX + by * self.paperCharWidth()))
            self.moveCarriage()

        self.scheduler.schedule(0.1, doit)


    def schedAdjustPaper(self, by):
        def doit():
            self.paperY = min(1.0, max(0.0, self.paperY + self.paperLineHeight() * by))
            self.schedRollPaper()

        self.scheduler.schedule(0.1, doit)

    def schedRollPaper(self):
        """
        Position the paper such that @percent of it is rolled over self.rollerNP.
        :param percent:
        :return:
        """

        def doit():
            # center over roller, peek out a little
            z = self.paperY * 0.8 - 0.5 + 0.175

            bb = self.target.getTightBounds()

            self.target.setPos(0, 0, z * (bb[1].z-bb[0].z))

        self.scheduler.schedule(0.1, doit)

    def schedTypeCharacter(self, keyname):
        # filter
        if ord(keyname) >= 32 and ord(keyname) != 127:
            if self.scheduler.isQueueEmpty():
                self.scheduler.schedule(0.001, lambda: self.typeCharacter(keyname))

    def typeCharacter(self, ch):

        # position -> pixel, applying margins
        x = int(self.tex.getXSize() * (self.paperX * 0.8 + 0.1))
        y = int(self.tex.getYSize() * (self.paperY * 0.8 + 0.1))

        if ch != ' ':
            #g = self.pnmFont.getGlyph(ord(ch))

            #print ch,"to",x,y,"w=",g.getWidth()
            self.pnmFont.generateInto(ch, self.texImage, x, y)

            #self.paperX += self.paperCharWidth(g.getWidth())
            self.paperX += self.paperCharWidth()

            # alternate typing sound
            #self.typeIndex = (self.typeIndex+1) % 3
            self.typeIndex = random.randint(0, 2)
            self.sounds['type' + str(self.typeIndex+1)].play()

        else:
            self.paperX += self.paperCharWidth()
            self.sounds['advance'].play()


        if self.paperX >= 1:
            self.sounds['bell'].play()
            self.paperX = 1

        self.schedMoveCarriage()

        self.tex.load(self.texImage)
