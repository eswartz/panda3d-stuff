
'''
Draw a tunnel with keyboard movement, create it and its collision geometry, and walk through it.

Created on Feb 25, 2015
Released Feb 4, 2016

@author: ejs
'''
from panda3d.core import loadPrcFile, loadPrcFileData  # @UnusedImport
loadPrcFile("./myconfig.prc")
# loadPrcFileData("", "load-display p3tinydisplay\nbasic-shaders-only #t\nhardware-animated-vertices #f") 
# loadPrcFileData("", "notify-level-collide debug") 
loadPrcFileData("", "sync-video 1") 

from direct.gui.OnscreenText import OnscreenText
from direct.showbase.ShowBase import ShowBase
from panda3d.core import TextNode, GeomNode, LVecBase4i, GeomVertexFormat, Geom,\
    GeomVertexWriter, GeomTristrips, GeomVertexData, Vec3, CollisionNode, \
    CollisionTraverser, CollisionSphere,\
    CollisionFloorMesh, GeomVertexReader, Point3, CollisionHandlerFloor
import sys

import fpscontroller
from direct.directnotify import DirectNotifyGlobal

class MyApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.seeNode = self.render.attachNewNode('see')
         
        self.cam.reparentTo(self.seeNode)
        self.cam.setPos(0, 0, 5)
        
        self.fpscamera = fpscontroller.FpsController(self, self.seeNode)
        self.fpscamera.setFlyMode(True)
        
        self.prevPos = self.fpscamera.getPos()
        self.prevInto = None
        self.info = self.genLabelText("Position: <unknown>", 4)

        self.makeInstructions()
        self.initCollisions()

        self.leftColor = LVecBase4i(224, 224, 64, 255)
        self.rightColor = LVecBase4i(64, 224, 224, 255)
        
        self.isDrawing = False
        self.toggleDrawing()
        
        self.accept("escape", sys.exit)            #Escape quits
        self.accept("enter", self.toggleDrawing)

    def initCollisions(self):
        # Initialize the collision traverser.
        self.cTrav = CollisionTraverser()
        
        self.cTrav.showCollisions(self.render)
        
#         self.cQueue = CollisionHandlerQueue()
         
        # Initialize the Pusher collision handler.
        #self.pusher = CollisionHandlerPusher()
        self.pusher = CollisionHandlerFloor()
                
        ### player
        
        print DirectNotifyGlobal.directNotify.getCategories()
        # Create a collsion node for this object.
        playerNode = CollisionNode('player')
        playerNode.addSolid(CollisionSphere(0, 0, 0, 1))
        
#         playerNode.setFromCollideMask(BitMask32.bit(0))
#         playerNode.setIntoCollideMask(BitMask32.allOn())
            
        # Attach the collision node to the object's model.
        self.playerC = self.fpscamera.player.attachNewNode(playerNode)
        # Set the object's collision node to render as visible.
        self.playerC.show()
         
        # Add the 'player' collision node to the Pusher collision handler.
        #self.pusher.addCollider(self.playerC, self.fpscamera.player)
        #self.pusher.addCollider(playerC, self.fpscamera.player)

#         self.cTrav.addCollider(self.playerC, self.cQueue)
        

    def toggleDrawing(self):
        self.isDrawing = not self.isDrawing
        
        if self.isDrawing:
            self.drawText.setText("Enter: Turn off drawing")
            self.fpscamera.setFlyMode(True)
            self.prevPos = None

            self.cTrav.removeCollider(self.playerC)
            self.pusher.removeCollider(self.playerC)
            
            self.removeTask('updatePhysics')
            self.addTask(self.drawHere, 'drawHere')
            
            self.geomNode = GeomNode('geomNode')
            self.geomNodePath = self.render.attachNewNode(self.geomNode)
            
            self.geomNodePath.setTwoSided(True)
            
            # apparently p3tinydisplay needs this
            self.geomNodePath.setColorOff()
    
    
            # Create a collision node for this object.
            self.floorCollNode = CollisionNode('geom')
            
#             self.floorCollNode.setFromCollideMask(BitMask32.bit(0))
#             self.floorCollNode.setIntoCollideMask(BitMask32.allOn())
        
            # Attach the collision node to the object's model.
            floorC = self.geomNodePath.attachNewNode(self.floorCollNode)
            # Set the object's collision node to render as visible.
            floorC.show()
            
            #self.pusher.addCollider(floorC, self.geomNodePath)

            self.newVertexData()
            
            self.newGeom()

        else:
            self.drawText.setText("Enter: Turn on drawing")
            self.removeTask('drawHere')
            if self.prevPos:
                self.completePath()
            
            self.fpscamera.setFlyMode(True)
            
            self.drive.setPos(self.fpscamera.getPos())
            
            self.cTrav.addCollider(self.playerC, self.pusher)
            self.pusher.addCollider(self.playerC, self.fpscamera.player)
            
            self.taskMgr.add(self.updatePhysics, 'updatePhysics')

    def newVertexData(self):
        fmt = GeomVertexFormat.getV3c4()
#         fmt = GeomVertexFormat.getV3n3c4()
        self.vertexData = GeomVertexData("path", fmt, Geom.UHStatic)
        self.vertexWriter = GeomVertexWriter(self.vertexData, 'vertex')
#         self.normalWriter = GeomVertexWriter(self.vertexData, 'normal')
        self.colorWriter = GeomVertexWriter(self.vertexData, 'color')

    def newGeom(self):
        self.triStrips = GeomTristrips(Geom.UHDynamic)
        self.geom = Geom(self.vertexData)
        self.geom.addPrimitive(self.triStrips)
        
        
    def makeInstructions(self):
        OnscreenText(text="Draw Path by Walking",
                          style=1, fg=(1,1,0,1),
                          pos=(0.5,-0.95), scale = .07)

        self.drawText = self.genLabelText("", 0)
        self.genLabelText("Walk (W/S/A/D), Jump=Space, Look=PgUp/PgDn", 1)
        self.genLabelText("  (hint, go backwards with S to see your path immediately)", 2)
        self.genLabelText("ESC: Quit", 3)
        
    def genLabelText(self, text, i):
        return OnscreenText(text = text, pos = (-1.3, .95-.05*i), fg=(1,1,0,1),
                      align = TextNode.ALeft, scale = .05)

    def drawHere(self, task):
        pos = self.fpscamera.getPos()
        self.info.setText("Position: {0}, {1}, {2} at {3} by {4}".format(int(pos.x*100)/100., int(pos.y*100)/100., int(pos.z)/100., 
                                                                  self.fpscamera.getHeading(), self.fpscamera.getLookAngle()))
        
        prevPos = self.prevPos
        
        if not prevPos:
            self.prevPos = pos
            
        elif (pos - prevPos).length() > 1:
            self.drawQuadTo(prevPos, pos, 2)
            
            row = self.vertexWriter.getWriteRow()
            numPrims = self.triStrips.getNumPrimitives()
            if numPrims == 0:
                primVerts = row
            else:
                primVerts = row - self.triStrips.getPrimitiveEnd(numPrims-1)

            if primVerts >= 4:
                self.triStrips.closePrimitive()
                
                if row >= 256:
                    print "Packing and starting anew"
                    newGeom = True
                    self.geom.unifyInPlace(row, False)
                else:
                    newGeom = False
                    
                self.completePath()

                if newGeom:                
                    self.newVertexData()
                                    
                self.newGeom()
                if not newGeom:
                    self.triStrips.addConsecutiveVertices(row - 2, 2)
                else:
                    self.drawQuadTo(prevPos, pos, 2)
                    
            self.leftColor[1] += 63
            self.rightColor[2] += 37
            
            self.prevPos = pos
        
        return task.cont

    def drawLineTo(self, pos, color):
        self.vertexWriter.addData3f(pos.x, pos.y, pos.z)
#         self.normalWriter.addData3f(0, 0, 1)
        self.colorWriter.addData4i(color)
        
        self.triStrips.addNextVertices(1)
            
    def drawQuadTo(self, a, b, width):
        """ a (to) b are vectors defining a line bisecting a new quad. """
        into = (b - a)
        if abs(into.x) + abs(into.y) < 1:
            if not self.prevInto:
                return
            into = self.prevInto
            print into
        else:
            into.normalize()
        
        # the perpendicular of (a,b) is (-b,a); we want the path to be "flat" in Z=space
        
        if self.vertexWriter.getWriteRow() == 0:
            self.drawQuadRow(a, into, width)        
            
        self.drawQuadRow(b, into, width)        
        
        self.prevInto = into

    def drawQuadRow(self, a, into, width):
        """ a defines a point, with 'into' being the normalized direction. """
        
        # the perpendicular of (a,b) is (-b,a); we want the path to be "flat" in Z=space
        
        aLeft = Vec3(a.x - into.y * width, a.y + into.x * width, a.z)
        aRight = Vec3(a.x + into.y * width, a.y - into.x * width, a.z)
        
        row = self.vertexWriter.getWriteRow()
        
        self.vertexWriter.addData3f(aLeft)
        self.vertexWriter.addData3f(aRight)

#         self.normalWriter.addData3f(Vec3(0, 0, 1))
#         self.normalWriter.addData3f(Vec3(0, 0, 1))

        self.colorWriter.addData4i(self.leftColor)
        self.colorWriter.addData4i(self.rightColor)
        
        self.triStrips.addConsecutiveVertices(row, 2)

    def completePath(self):
        self.geomNode.addGeom(self.geom)
        
        if self.triStrips.getNumPrimitives() == 0:
            return
        
        floorMesh = CollisionFloorMesh()
        
        tris = self.triStrips.decompose()
        p = 0
        vertexReader = GeomVertexReader(self.vertexData, 'vertex') 
        for i in range(tris.getNumPrimitives()):
            v0 = tris.getPrimitiveStart(i)
            ve = tris.getPrimitiveEnd(i)
            if v0 < ve:
                vertexReader.setRow(tris.getVertex(v0))
                floorMesh.addVertex(Point3(vertexReader.getData3f()))
                vertexReader.setRow(tris.getVertex(v0+1))
                floorMesh.addVertex(Point3(vertexReader.getData3f()))
                vertexReader.setRow(tris.getVertex(v0+2))
                floorMesh.addVertex(Point3(vertexReader.getData3f()))
                floorMesh.addTriangle(p, p+1, p+2)
                p += 3
        
        self.floorCollNode.addSolid(floorMesh)
        
        
          
    def updatePhysics(self, task):
        pos = self.fpscamera.getPos()
        self.info.setText("Position: {0}, {1}, {2}".format(int(pos.x*100)/100., int(pos.y*100)/100., int(pos.z)/100.))
        return task.cont
                          

        
app = MyApp()
app.run()
