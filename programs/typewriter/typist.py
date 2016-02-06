"""
Support "typing" onto an object.

This method creates a Texture and PNMImage, makes that texture a second
TextureStage on the original object, and copies changes when a character is struck.
"""
import random

from panda3d.core import Vec3, Point3, Texture, PNMImage, TextureStage, PNMTextMaker, Vec4

from panda3d.core import Geom
from panda3d.core import GeomNode
from panda3d.core import GeomPoints
from panda3d.core import GeomVertexArrayFormat
from panda3d.core import GeomVertexData
from panda3d.core import GeomVertexFormat
from panda3d.core import GeomVertexWriter
from panda3d.core import RenderAttrib
from panda3d.core import Shader
from panda3d.core import TexGenAttrib
from panda3d.core import TextureStage
from panda3d.core import Vec3, NodePath, Texture, Vec4
from panda3d.core import loadPrcFileData

from direct.interval.LerpInterval import LerpPosInterval
from scheduler import Scheduler
from utils import fonts

global globalClock

class Typist(object):

    TARGETS = { 'paper': {
            'model': 'paper',
            'textureRoot': 'Front',
            'scale': Point3(0.85, 0.85, 1),
            'hpr' : Point3(0, 0, 0),
        }
    }

    def __init__(self, base, typewriterNP, underDeskClip, sounds):
        self.base = base
        self.sounds = sounds
        self.underDeskClip = underDeskClip
        self.typeIndex = 0

        self.typewriterNP = typewriterNP
        self.rollerAssemblyNP = typewriterNP.find("**/roller assembly")
        assert self.rollerAssemblyNP
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
        self.targetRoot = None
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

    def setupTexture(self):
        """
        This is the overlay/decal/etc. which contains the typed characters.

        The texture size and the font size are currently tied together.
        :return:
        """
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

        # ensure we can quickly update subimages
        self.tex.setKeepRamImage(True)

        # temp for drawing chars
        self.chImage = PNMImage(*self.fontCharSize)


    def drawCharacter(self, ch, px, py):
        """
        Draw a character onto the texture
        :param ch:
        :param px: paperX
        :param py: paperY
        :return: the paper-relative size of the character
        """

        h = self.fontCharSize[1]

        if ch != ' ':

            # position -> pixel, applying margins
            x = int(self.tex.getXSize() * (px * 0.8 + 0.1))
            y = int(self.tex.getYSize() * (py * 0.8 + 0.1))

            # always draw onto the paper, to capture
            # incremental character overstrikes
            self.pnmFont.generateInto(ch, self.texImage, x, y)

            if False:
                #print ch,"to",x,y,"w=",g.getWidth()
                self.tex.load(self.texImage)

            else:
                # copy an area (presumably) encompassing the character
                g = self.pnmFont.getGlyph(ord(ch))
                cx, cy = self.fontCharSize

                # a glyph is minimally sized and "moves around" in its text box
                # (think ' vs. ,), so it has been drawn somewhere relative to
                # the 'x' and 'y' we wanted.
                x += g.getLeft()
                y -= g.getTop()

                self.chImage.copySubImage(
                        self.texImage,
                        0, 0,  # from
                        x, y,  # to
                        cx,  cy  # size
                )

                self.tex.loadSubImage(self.chImage, x, y)

            # toggle for a typewriter that uses non-proportional spacing
            #w = self.paperCharWidth(g.getWidth())
            w = self.paperCharWidth()

        else:

            w = self.paperCharWidth()

        return w, h

    def start(self):
        self.target = None
        self.setTarget('paper')

        self.hookKeyboard()


    def createRollerBase(self):
        """ The paper moves such that it is tangent to the roller.

        This nodepath keeps a coordinate space relative to that, so that
        the paper can be positioned from (0,0,0) to (0,0,1) to "roll" it
        along the roller.
        """
        bb = self.rollerNP.getTightBounds()

        #self.rollerNP.showTightBounds()
        self.paperRollerBase = self.rollerAssemblyNP.attachNewNode('rollerBase')
        self.paperRollerBase.setHpr(0, -20, 0)

        print "roller:",bb
        rad = abs(bb[0].y - bb[1].y) / 2
        center = Vec3(-(bb[0].x+bb[1].x)/2 - 0.03,
                      (bb[0].y-bb[1].y)/2,
                      (bb[0].z+bb[1].z)/2)
        self.paperRollerBase.setPos(center)

    def setTarget(self, name):
        if self.target:
            self.target.removeNode()

        # load and transform the model
        target = self.TARGETS[name]
        self.target = self.base.loader.loadModel(target['model'])
        #self.target.setScale(target['scale'])
        self.target.setHpr(target['hpr'])

        # put it in the world
        self.target.reparentTo(self.paperRollerBase)

        rbb = self.rollerNP.getTightBounds()
        tbb = self.target.getTightBounds()

        rs = (rbb[1] - rbb[0])
        ts = (tbb[1] - tbb[0])

        self.target.setScale(rs.x / ts.x, 1, 1)

        # apply the texture
        self.targetRoot = self.target
        if 'textureRoot' in target:
            self.targetRoot = self.target.find("**/" + target['textureRoot'])
            assert self.targetRoot

        self.targetRoot.setTexture(self.typingStage, self.tex)

        #self.setupTargetClip()

        # reset
        self.paperX = self.paperY = 0.
        newPos = self.calcPaperPos(self.paperY)
        self.target.setPos(newPos)

        self.moveCarriage()

    def setupTargetClip(self):
        """
        The target is fed in to the typewriter but until we invent "geom curling",
        it shouldn't be visible under the typewriter under the desk.

        The @underDeskClip node has a world-relative bounding box, which
        we can convert to the target-relative bounding box, and pass to a
        shader that can clip the nodes.

        """
        shader = Shader.make(
                Shader.SLGLSL,
            """
#version 120

attribute vec4 p3d_MultiTexCoord0;
attribute vec4 p3d_MultiTexCoord1;

void main() {
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
    gl_TexCoord[0] = p3d_MultiTexCoord0;
    gl_TexCoord[1] = p3d_MultiTexCoord1;
}

            """,

                """
#version 120

uniform sampler2D baseTex;
uniform sampler2D charTex;
const vec4 zero = vec4(0, 0, 0, 0);
const vec4 one = vec4(1, 1, 1, 1);
const vec4 half = vec4(0.5, 0.5, 0.5, 0);

void main() {
    vec4 baseColor = texture2D(baseTex, gl_TexCoord[0].st);
    vec4 typeColor = texture2D(charTex, gl_TexCoord[1].st);
    gl_FragColor = baseColor * typeColor;

}"""
        )

        self.target.setShader(shader)

        baseTex = self.targetRoot.getTexture()
        print "Base Texture:",baseTex
        self.target.setShaderInput("baseTex", baseTex)

        self.target.setShaderInput("charTex", self.tex)

    def hookKeyboard(self):
        """
        Hook events so we can respond to keypresses.
        """
        self.base.buttonThrowers[0].node().setKeystrokeEvent('keystroke')
        self.base.accept('keystroke', self.schedTypeCharacter)
        self.base.accept('backspace', self.schedBackspace)

        self.base.accept('arrow_up', lambda: self.schedAdjustPaper(-5))
        self.base.accept('arrow_up-repeat', lambda: self.schedAdjustPaper(-1))
        self.base.accept('arrow_down', lambda:self.schedAdjustPaper(5))
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
        return float(self.fontCharSize[1] * 1.2) / self.tex.getYSize()

    def schedScroll(self):
        if self.scheduler.isQueueEmpty():
            self.schedRollPaper(1)
            self.schedResetCarriage()

    def schedBackspace(self):
        if self.scheduler.isQueueEmpty():
            def doit():
                if self.paperX > 0:
                    self.schedAdjustCarriage(-1)

            self.scheduler.schedule(0.01, doit)


    def createMoveCarriageInterval(self, newX, curX=None):
        if curX is None:
            curX = self.paperX
        here = self.calcCarriage(curX)
        there = self.calcCarriage(newX)

        posInterval = LerpPosInterval(
                self.carriageNP, abs(newX - curX),
                there,
                startPos = here,
                blendType='easeIn')

        posInterval.setDoneEvent('carriageReset')

        def isReset():
            self.paperX = newX

        self.base.acceptOnce('carriageReset', isReset)
        return posInterval

    def schedResetCarriage(self):
        if self.paperX > 0.1:
            self.sounds['pullback'].play()

        invl = self.createMoveCarriageInterval(0)

        self.scheduler.scheduleInterval(0, invl)

    def calcCarriage(self, paperX):
        """
        Calculate where the carriage should be offset based
        on the position on the paper
        :param paperX: 0...1
        :return: pos for self.carriageNP
        """
        x = (0.5 - paperX) * 0.69 * 0.8 + 0.01

        bb = self.carriageBounds
        return self.baseCarriagePos + Point3(x * (bb[1].x-bb[0].x), 0, 0)

    def moveCarriage(self):
        pos = self.calcCarriage(self.paperX)
        self.carriageNP.setPos(pos)


    def schedMoveCarriage(self, curX, newX):
        if self.scheduler.isQueueEmpty():
            #self.scheduler.schedule(0.1, self.moveCarriage)
            invl = self.createMoveCarriageInterval(newX, curX=curX)
            invl.start()

    def schedAdjustCarriage(self, bx):
        if self.scheduler.isQueueEmpty():
            def doit():
                self.paperX = max(0.0, min(1.0, self.paperX + bx * self.paperCharWidth()))
                self.moveCarriage()

            self.scheduler.schedule(0.1, doit)


    def calcPaperPos(self, paperY):
        # center over roller, peek out a little
        z = paperY * 0.8 - 0.5 + 0.175

        bb = self.target.getTightBounds()

        return Point3(-0.5, 0, z * (bb[1].z-bb[0].z))

    def createMovePaperInterval(self, newY):
        here = self.calcPaperPos(self.paperY)
        there = self.calcPaperPos(newY)

        posInterval = LerpPosInterval(
                self.target, abs(newY - self.paperY),
                there,
                startPos = here,
                blendType='easeInOut')

        posInterval.setDoneEvent('scrollDone')

        def isDone():
            self.paperY = newY

        self.base.acceptOnce('scrollDone', isDone)
        return posInterval

    def schedAdjustPaper(self, by):
        if self.scheduler.isQueueEmpty():
            def doit():
                self.schedRollPaper(by)

            self.scheduler.schedule(0.1, doit)

    def schedRollPaper(self, by):
        """
        Position the paper such that @percent of it is rolled over roller
        :param percent:
        :return:
        """

        def doit():
            self.sounds['scroll'].play()

            newY = min(1.0, max(0.0, self.paperY + self.paperLineHeight() * by))

            invl = self.createMovePaperInterval(newY)
            invl.start()

        self.scheduler.schedule(0.1, doit)

    def schedTypeCharacter(self, keyname):
        # filter for visibility
        if ord(keyname) == 13:
            self.schedScroll()

        elif ord(keyname) >= 32 and ord(keyname) != 127:
            if self.scheduler.isQueueEmpty():
                curX, curY = self.paperX, self.paperY
                self.typeCharacter(keyname, curX, curY)

    def typeCharacter(self, ch, curX, curY):

        newX = curX

        w, h = self.drawCharacter(ch, curX, curY)

        newX += w


        if ch != ' ':
            # alternate typing sound
            #self.typeIndex = (self.typeIndex+1) % 3
            self.typeIndex = random.randint(0, 2)
            self.sounds['type' + str(self.typeIndex+1)].play()

        else:
            self.sounds['advance'].play()


        if newX >= 1:
            self.sounds['bell'].play()
            newX = 1


        self.schedMoveCarriage(self.paperX, newX)

        # move first, to avoid overtype
        self.paperX = newX

