'''
Allow simulating a typewriter using texture projection

Ed Swartz, Feb 2016
'''

from panda3d.core import DirectionalLight, AmbientLight, PointLight, ScissorEffect, ColorWriteAttrib, CullBinManager
from panda3d.core import Point3, Mat4, TransparencyAttrib # @UnusedImport

from direct.interval.LerpInterval import LerpHprInterval, LerpPosInterval, LerpFunc
from direct.interval.MetaInterval import Parallel, Sequence
import skybox

from typist import Typist

global globalClock

class World(object):

    def __init__(self, base):
        self.base = base
        """ direct.showbase.ShowBase """

        alight = AmbientLight('alight')
        alnp = self.base.render.attachNewNode(alight)
        alight.setColor((0.2, 0.2, 0.2, 1))
        self.base.render.setLight(alnp)

        # Put lighting on the main scene

        dlight = DirectionalLight('dlight')
        dlnp = self.base.render.attachNewNode(dlight)
        dlnp.setPos(0, 5, 5)
        dlight.setColor((0.8, 0.8, 0.5, 1))
        dlnp.setHpr(0, 60, 0)
        self.base.render.setLight(dlnp)

        plight = PointLight('plight')
        plnp = self.base.render.attachNewNode(plight)
        plnp.setPos(0, -50, 50)
        plnp.setHpr(0, 60, 0)
        self.base.render.setLight(plnp)

        self.sounds = {}

    def start(self, skipIntro):
        self.skipIntro = skipIntro

        self.base.skybox = None
        self.typewriterNP = None
        self.deskNP = None
        self.base.taskMgr.doMethodLater(0.2, self.loadup, 'loadup')

    def loadup(self, task):
        # get in front
        self.base.camera.setPos(0, 0, 0)

        # trusty typewriter
        self.typewriterNP = self.base.loader.loadModel('typewriter')

        # the desk
        self.deskNP = self.base.loader.loadModel('desk')

        # skybox
        skyb = skybox.NetmapSkybox(self.base, 'iceRiver', '', '.jpg')
        self.sky = skyb.create(self.base.cam)

        # sounds
        self.sounds['bell'] = self.base.loader.loadSfx('bell.wav')
        self.sounds['advance'] = self.base.loader.loadSfx('advance.wav')
        self.sounds['pullback'] = self.base.loader.loadSfx('pullback.wav')
        self.sounds['scroll'] = self.base.loader.loadSfx('scroll.wav')
        self.sounds['type1'] = self.base.loader.loadSfx('type1.wav')
        self.sounds['type2'] = self.base.loader.loadSfx('type2.wav')
        self.sounds['type3'] = self.base.loader.loadSfx('type3.wav')

        if not self.skipIntro:
            self.sky.setAttrib(TransparencyAttrib.make(TransparencyAttrib.M_alpha))
            self.sky.setAlphaScale(0, 1)

            alphaInterval = LerpFunc(lambda a: self.sky.setAlphaScale(a, 1),
                                     duration=1,
                                     fromData=0,
                                     toData=1,
                                     blendType='easeIn')

            seq = Sequence(alphaInterval)
            seq.setDoneEvent('createWorld')

            seq.start()

        else:
            self.base.messenger.send('createWorld')

    def createWorld(self, task=None):
        self.sky.clearAttrib(TransparencyAttrib)

        self.deskNP.reparentTo(self.base.render)
        self.deskNP.setScale(7.5)
        self.deskNP.setPos(0, -5, -6.5)

        # make a box that clips content under the desk (e.g. the paper)
        bb = self.deskNP.getTightBounds()
        sz = (bb[1]-bb[0]) * 0.8

        self.underDeskClip = self.base.loader.loadModel('box')
        self.underDeskClip.setScale(sz)
        self.underDeskClip.reparentTo(self.base.render)
        self.underDeskClip.setPos(-sz.x/2, -sz.y*1.1, -sz.z*0.73)

        if False:
            # --> nope, this actually hides everything the camera might see

            self.newBin = CullBinManager.getGlobalPtr().addBin('foo', CullBinManager.BT_state_sorted, -50)
            # make the box obscure geometry "inside" it
            self.underDeskClip.setAttrib(ColorWriteAttrib.make(False))
            self.underDeskClip.setDepthWrite(True)
            self.underDeskClip.setBin('foo', -50)

        else:
            bb = self.underDeskClip.getTightBounds()
            self.underDeskClip.removeNode()


        self.typewriterNP.reparentTo(self.base.render)

        self.typewriterNP.setHpr(0, 0, 0)
        self.typewriterNP.setScale(5)

        self.base.camera.setPos(0, -25, 5)
        self.cameraTarget = Point3(0, -9.5, 7.5)
        #self.cameraTarget = Point3(0, -25, 2.5)
        self.cameraHprTarget = Point3(0, -19.5, 0)
        self.typewriterTarget = Point3(0, -2.5, 2.666)
        self.typewriterStart = Point3(0, -5, 10)

        if not self.skipIntro:
            self.animateArrival()
        else:
            self.activateTypewriter()

    def animateArrival(self):
        """
        Cheesy animation introducing viewer to the DESK and TYPEWRITER
        :return:
        """
        camMoveInterval = LerpPosInterval(self.base.camera,  2, self.cameraTarget)
        camHprInterval = LerpHprInterval(self.base.camera,  2, self.cameraHprTarget)

        dropKeyboardInterval = LerpPosInterval(self.typewriterNP, 2,
                                               self.typewriterTarget,
                                               startPos=self.typewriterStart,
                                               blendType='easeOut')

        sequence = Parallel(camMoveInterval, camHprInterval, dropKeyboardInterval)

        sequence.setDoneEvent('arrivalFinished')

        def arrivalFinished():
            self.activateTypewriter()
            self.base.ignore('enter')
            self.base.ignore('esc')

        self.base.accept('arrivalFinished', arrivalFinished)

        sequence.start()

        # for the impatient...
        def cancelStartupSequence():
            sequence.finish()

        self.base.acceptOnce('enter', cancelStartupSequence)
        self.base.acceptOnce('esc', cancelStartupSequence)


    def activateTypewriter(self):
        """
        Once the intro is complete, enable interactivity
        """

        self.placeItems()

        # re-enable mouse
        mat=Mat4(self.base.camera.getMat())
        mat.invertInPlace()
        self.base.mouseInterfaceNode.setMat(mat)
        self.base.enableMouse()

        self.typist = Typist(self.base, self.typewriterNP, self.underDeskClip, self.sounds)
        self.typist.start()

    def placeItems(self):
        """
        Place items in world after intro animation (should be a no-op, but to be sure...)
        """
        self.base.camera.setHpr(self.cameraHprTarget)
        self.base.camera.setPos(self.cameraTarget)
        self.typewriterNP.setPos(self.typewriterTarget)



