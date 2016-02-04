import random

from panda3d.core import Vec3, Point3, CompassEffect, Texture, PNMImage, TextureStage, PNMPainter, PNMBrush, \
    PNMTextMaker

from lib.utils import fonts


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
        self.rollPaper()
        self.moveCarriage()

    def hookKeyboard(self):
        """
        Hook events so we can respond to keypresses.
        """
        def userCharacter(keyname):
            # filter
            if ord(keyname) >= 32 and ord(keyname) != 127:
                self.typeCharacter(keyname)

        self.base.buttonThrowers[0].node().setKeystrokeEvent('keystroke')
        self.base.accept('keystroke', userCharacter)
        self.base.accept('enter', self.scroll)
        self.base.accept('backspace', self.bksp)

        self.base.accept('arrow_up', lambda: self.adjustPaper(3))
        self.base.accept('arrow_up-repeat', lambda: self.adjustPaper(1))
        self.base.accept('arrow_down', lambda:self.adjustPaper(-3))
        self.base.accept('arrow_down-repeat', lambda:self.adjustPaper(-1))

        self.base.accept('arrow_left', lambda: self.adjustCarriage(-1))
        self.base.accept('arrow_left-repeat', lambda: self.adjustCarriage(-1))
        self.base.accept('arrow_right', lambda:self.adjustCarriage(1))
        self.base.accept('arrow_right-repeat', lambda:self.adjustCarriage(1))

    def paperCharWidth(self, pixels=None):
        if not pixels:
            pixels = self.fontCharSize[0]
        return float(pixels) / self.tex.getXSize()

    def paperLineHeight(self):
        return float(self.fontCharSize[1]) / self.tex.getYSize()

    def scroll(self):
        self.paperX = 0
        self.paperY += self.paperLineHeight()

        self.sounds['scroll'].play()

        self.rollPaper()
        self.resetCarriage()

    def bksp(self):
        if self.paperX > 0:
            self.adjustCarriage(-1)

    def resetCarriage(self):
        self.paperX = 0
        self.sounds['pullback'].play()

    def moveCarriage(self):
        x = (0.5 - self.paperX) * 0.5 - 0.15

        bb = self.carriageBounds
        self.carriageNP.setPos(self.baseCarriagePos + Point3(x * (bb[1].x-bb[0].x), 0, 0))

    def adjustCarriage(self, by):
        self.paperX = max(0.0, min(1.0, self.paperX + by * self.paperCharWidth()))
        self.moveCarriage()


    def adjustPaper(self, by):
        self.paperY = min(1.0, max(0.0, self.paperY + self.paperLineHeight() * by))
        self.rollPaper()

    def rollPaper(self):
        """
        Position the paper such that @percent of it is rolled over self.rollerNP.
        :param percent:
        :return:
        """
        # center over roller, peek out a little
        z = self.paperY * 0.8 - 0.5 + 0.175

        bb = self.target.getTightBounds()

        self.target.setPos(0, 0, z * (bb[1].z-bb[0].z))

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

            self.sounds[random.choice(['type1', 'type2'])].play()

        else:
            self.paperX += self.paperCharWidth()
            self.sounds['advance'].play()


        if self.paperX >= 1:
            self.sounds['bell'].play()
            self.paperX = 1

        self.moveCarriage()

        self.tex.load(self.texImage)