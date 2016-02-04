'''
Allow simulating a typewriter using texture projection

Ed Swartz, Feb 2016
'''
import sys
import random

from direct.gui.OnscreenText import OnscreenText
from direct.interval.MetaInterval import Parallel, Sequence
from panda3d.core import loadPrcFile, loadPrcFileData, Point3,Vec4, Mat4, LoaderOptions, TextNode, \
    TransparencyAttrib, Vec3  # @UnusedImport
from panda3d.core import DirectionalLight, AmbientLight, PointLight
from panda3d.core import Texture, PNMImage
from panda3d.core import PandaSystem
from direct.interval.LerpInterval import LerpHprInterval, LerpPosInterval, LerpFunc
from direct.showbase.ShowBase import ShowBase

from lib import skybox
from world import World

loadPrcFileData('', 'model-path $MAIN_DIR/assets/models')
loadPrcFileData('', 'model-path $MAIN_DIR/assets/textures')
loadPrcFileData('', 'model-path $MAIN_DIR/assets/fonts')
loadPrcFileData('', 'model-path $MAIN_DIR/assets/sounds')

global globalClock

class MyApp(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)

        self.win.setClearColor(Vec4(0.5, 0.8, 0.8, 1))

        self.disableMouse()

        self.render.setShaderAuto()

        self.loadingMessage = self.showLoadingMessage()

        self.world = World(self)
        self.acceptOnce('createWorld', self.createWorld)
        self.world.start('--gogogo' in sys.argv)

    def createWorld(self):
        self.loadingMessage.removeNode()
        self.world.createWorld()

    def showLoadingMessage(self):

        bigFont = self.loader.loadFont('Harting.ttf', pointSize=32).makeCopy()

        bigFont.setOutline(Vec4(0,0,0,1), 1, 0)
        loadingMessage = self.render2d.attachNewNode('loading')
        OnscreenText('Loading...', fg=Vec4(0,0,0,.75), pos=(.01,-.01),
                                 font=bigFont, align=TextNode.A_center, parent=loadingMessage)
        OnscreenText('Loading...', fg=Vec4(1,1,1,1),
                                font=bigFont, align=TextNode.A_center, parent=loadingMessage)

        return loadingMessage


app = MyApp()
app.run()


