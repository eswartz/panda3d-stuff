'''
Allow simulating a typewriter using texture projection

Ed Swartz, Feb 2016
'''
import sys

USE_RP = True

from panda3d.core import loadPrcFileData, Vec4, TextNode  # @UnusedImport

from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from world import World

# loadPrcFileData("", "gl-debug #t ")
# loadPrcFileData("", "gl-check-errors #t ")

loadPrcFileData("", "win-size 1024 768")
loadPrcFileData('', 'model-path $MAIN_DIR/assets/models')
loadPrcFileData('', 'model-path $MAIN_DIR/assets/textures')
loadPrcFileData('', 'model-path $MAIN_DIR/assets/fonts')
loadPrcFileData('', 'model-path $MAIN_DIR/assets/sounds')


if USE_RP:
    # Insert the pipeline path to the system path, this is required to be
    # able to import the pipeline classes. In case you placed the render
    # pipeline in a subfolder of your project, you have to adjust this.
    sys.path.insert(0, "/home/ejs/devel/RenderPipeline")

    # Import render pipeline classes
    from rpcore import RenderPipeline, SpotLight

global globalClock

class MyApp(ShowBase):

    def __init__(self):
        if not USE_RP:
            ShowBase.__init__(self)
        else:
            # Construct and create the pipeline
            self.render_pipeline = RenderPipeline()
            self.render_pipeline.create(self)

        self.win.setClearColor(Vec4(0.5, 0.8, 0.8, 1))

        self.disableMouse()

        if not USE_RP:
            self.render.setShaderAuto()

        self.loadingMessage = self.showLoadingMessage()

        self.world = World(self, USE_RP)
        self.acceptOnce('createWorld', self.createWorld)
        self.world.start('--gogogo' in sys.argv)

    def createWorld(self, task=None):
        self.loadingMessage.removeNode()

        self.doMethodLater(0.1, self.world.createWorld, 'create world')

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


