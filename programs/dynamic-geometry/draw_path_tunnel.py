
'''

Draw a tunnel with mouse movement, create it and its collision geometry, and walk through it.

Created on Feb 27, 2015
Released Feb 4, 2016

@author: ejs
'''
from panda3d.core import loadPrcFileData  # @UnusedImport
#loadPrcFile("./myconfig.prc")
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


class MyApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.seeNode = self.render.attachNewNode('see')
         
        self.cam.reparentTo(self.seeNode)
        self.cam.setPos(0, 0, 5)
        
        self.fpscamera = fpscontroller.FpsController(self, self.seeNode)
        self.fpscamera.setFlyMode(True)
        self.fpscamera.setMouseLook(True)
        
        self.prevPos = self.fpscamera.getPos()
        self.prevInto = None
        
        self.makeInstructions()
        self.info = self.genLabelText("Position: <unknown>", 2)

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
        
        # Initialize the Pusher collision handler.
        self.pusher = CollisionHandlerFloor()
                
        ### player
        
        # Create a collsion node for this object.
        playerNode = CollisionNode('player')
        playerNode.addSolid(CollisionSphere(0, 0, 0, 1))
        
        # Attach the collision node to the object's model.
        self.playerC = self.fpscamera.player.attachNewNode(playerNode)
        # Set the object's collision node to render as visible.
        self.playerC.show()
         

    def toggleDrawing(self):
        self.isDrawing = not self.isDrawing
        
        if self.isDrawing:
            self.instructionText.setText('Enter: Generate Tunnel from Movement')

            self.fpscamera.setFlyMode(True)
            self.prevPos = None

            # self.cTrav.remosveCollider(self.playerC)
            
            self.removeTask('updatePhysics')
            self.addTask(self.drawHere, 'drawHere')
            
            self.geomNode = GeomNode('geomNode')
            self.geomNodePath = self.render.attachNewNode(self.geomNode)
            
            self.geomNodePath.setTwoSided(True)
            
            
            # apparently p3tinydisplay needs this
            self.geomNodePath.setColorOff()

            # Create a collision node for this object.
            self.floorCollNode = CollisionNode('geom')

            # Attach the collision node to the object's model.
            floorC = self.geomNodePath.attachNewNode(self.floorCollNode)
            # Set the object's collision node to render as visible.
            floorC.show()

            self.newVertexData()
            
            self.newGeom()

        else:
            self.instructionText.setText('Enter: Record Movement for Tunnel')

            self.removeTask('drawHere')
            if self.prevPos:
                #self.completePath()
                self.completeTunnelPath()
            
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
        OnscreenText(text="Draw Path by Walking (WSAD/space/mouselook)",
                          style=1, fg=(1,1,0,1),
                          pos=(0.5,-0.95), scale = .07)
        self.genLabelText("ESC: Quit", 0)
        self.instructionText = self.genLabelText("", 1)
        
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
            
        elif (pos - prevPos).length() >= 1:
#             self.extendPathQuad(prevPos, pos, 2)
            self.extendPathTunnel(prevPos, pos, 3)
                    
            self.leftColor[1] += 63
            self.rightColor[2] += 37
            
            self.prevPos = pos
        
        return task.cont

    def extendPathQuad(self, prevPos, pos, width):
        self.drawQuadTo(prevPos, pos, width)

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
                
            self.completeQuadPath()

            if newGeom:                
                self.newVertexData()
                                
            self.newGeom()
            if newGeom:
                self.drawQuadTo(prevPos, pos, width)
            else:
                self.triStrips.addConsecutiveVertices(row - 2, 2)
            
        
    def extendPathTunnel(self, prevPos, pos, width):
        self.drawTunnelTo(prevPos, pos, width)

    def drawLineTo(self, pos, color):
        self.vertexWriter.addData3f(pos.x, pos.y, pos.z)
#         self.normalWriter.addData3f(0, 0, 1)
        self.colorWriter.addData4i(color)
        
        self.triStrips.addNextVertices(1)
        
        return 1
            
    def drawQuadTo(self, a, b, width):
        """ a (to) b are vectors defining a line bisecting a new quad. """
        into = (b - a)
        if abs(into.x) + abs(into.y) < 1:
            # ensure that if we jump in place, we don't get a thin segment
            if not self.prevInto:
                return
            into = self.prevInto
        else:
            into.normalize()
        
        # the perpendicular of (a,b) is (-b,a); we want the path to be "flat" in Z=space
        
        if self.vertexWriter.getWriteRow() == 0:
            self.drawQuadRow(a, into, width)        
        
        verts = self.drawQuadRow(b, into, width)

        self.prevInto = into
        
        return verts

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

        return 2
            
    def drawTunnelTo(self, a, b, width):
        """ a (to) b are vectors defining a line bisecting a new tunnel segment. """
        into = (b - a)
        if abs(into.x) + abs(into.y) < 1:
            # ensure that if we jump in place, we don't get a thin segment
            if not self.prevInto:
                return
            into = self.prevInto
        else:
            into.normalize()
        
        # the perpendicular of (a,b) is (-b,a); we want the path to be "flat" in Z=space
        
        if self.vertexWriter.getWriteRow() == 0:
            self.drawTunnelBoundary(a, into, width)        
            
        row = self.vertexWriter.getWriteRow()
        verts = self.drawTunnelBoundary(b, into, width)        
        totalVerts = self.drawTunnelRow(row, verts)        
        
        self.prevInto = into
        
        return totalVerts

    def drawTunnelBoundary(self, a, into, width):
        """ a defines a point, with 'into' being the normalized direction. """
        
        aLowLeft = Vec3(a.x - into.y * width, a.y + into.x * width, a.z)
        aLowRight = Vec3(a.x + into.y * width, a.y - into.x * width, a.z)
        aHighRight = Vec3(a.x + into.y * width, a.y - into.x * width, a.z + width * 3)
        aHighLeft = Vec3(a.x - into.y * width, a.y + into.x * width, a.z + width * 3)
        
        self.vertexWriter.addData3f(aLowLeft)
        self.vertexWriter.addData3f(aLowRight)
        self.vertexWriter.addData3f(aHighRight)
        self.vertexWriter.addData3f(aHighLeft)
        
        self.colorWriter.addData4i(self.leftColor)
        self.colorWriter.addData4i(self.rightColor)
        self.colorWriter.addData4i(self.leftColor)
        self.colorWriter.addData4i(self.rightColor)
        
        return 4
    
    def drawTunnelRowX(self, row, verts):
        # BOTTOM: bottom-left, new-bottom-left, bottom-right, new-bottom-right
        self.triStrips.addConsecutiveVertices(row - verts + 0, 1)
        self.triStrips.addConsecutiveVertices(row + 0, 1)
        self.triStrips.addConsecutiveVertices(row - verts + 1, 1)
        self.triStrips.addConsecutiveVertices(row + 1, 1)
        self.triStrips.closePrimitive()
        # RIGHT: (new-bottom-right) bottom-right, new-top-right, top-right
        self.triStrips.addConsecutiveVertices(row + 1, 1)
        self.triStrips.addConsecutiveVertices(row - verts + 1, 1)
        self.triStrips.addConsecutiveVertices(row + 2, 1)
        self.triStrips.addConsecutiveVertices(row - verts + 2, 1)
        self.triStrips.closePrimitive()
        # TOP: top-left, new top-right, new top-left
        self.triStrips.addConsecutiveVertices(row - verts + 2, 1)
        self.triStrips.addConsecutiveVertices(row - verts + 3, 1)
        self.triStrips.addConsecutiveVertices(row + 2, 1)
        self.triStrips.addConsecutiveVertices(row + 3, 1)
        self.triStrips.closePrimitive()
        # LEFT: (new top-left) new bottom-left, top-left, bottom-left, new-bottom-left
        self.triStrips.addConsecutiveVertices(row + 3, 1)
        self.triStrips.addConsecutiveVertices(row + 0, 1)
        self.triStrips.addConsecutiveVertices(row - verts + 3, 1)
        self.triStrips.addConsecutiveVertices(row - verts + 0, 1)
        self.triStrips.closePrimitive()
        
        return verts * 4
    
    def drawTunnelRow(self, row, verts):
#         # clockwise for the inside of the tunnel
#         # TOP: new-top-left, top-left, new-top-right, top-right
#         self.triStrips.addConsecutiveVertices(row + 3, 1)
#         self.triStrips.addConsecutiveVertices(row - verts + 3, 1)
#         self.triStrips.addConsecutiveVertices(row + 2, 1)
#         self.triStrips.addConsecutiveVertices(row - verts + 2, 1)
#         # RIGHT: new-bottom-right, bottom-right
#         self.triStrips.addConsecutiveVertices(row + 1, 1)
#         self.triStrips.addConsecutiveVertices(row - verts + 1, 1)
#         # BOTTOM: new-bottom-left, bottom-left
#         self.triStrips.addConsecutiveVertices(row, 1)
#         self.triStrips.addConsecutiveVertices(row - verts, 1)
#         # LEFT: new top-left, top-left
#         self.triStrips.addConsecutiveVertices(row + 3, 1)
#         self.triStrips.addConsecutiveVertices(row - verts + 3, 1)
        
        # TOP: new-top-left, top-left, new-top-right, top-right
        self.triStrips.addConsecutiveVertices(row - verts + 3, 1)
        self.triStrips.addConsecutiveVertices(row + 3, 1)
        self.triStrips.addConsecutiveVertices(row - verts + 2, 1)
        self.triStrips.addConsecutiveVertices(row + 2, 1)
        # RIGHT: new-bottom-right, bottom-right
        self.triStrips.addConsecutiveVertices(row - verts + 1, 1)
        self.triStrips.addConsecutiveVertices(row + 1, 1)
        # BOTTOM: new-bottom-left, bottom-left
        self.triStrips.addConsecutiveVertices(row - verts, 1)
        self.triStrips.addConsecutiveVertices(row, 1)
        # LEFT: new top-left, top-left
        self.triStrips.addConsecutiveVertices(row - verts + 3, 1)
        self.triStrips.addConsecutiveVertices(row + 3, 1)

        self.triStrips.closePrimitive()
        
        return verts * 4
        
    def completeQuadPath(self):
        self.geomNode.addGeom(self.geom)
        
        if self.triStrips.getNumPrimitives() == 0:
            return
        
        floorMesh = CollisionFloorMesh()
        vertexReader = GeomVertexReader(self.vertexData, 'vertex') 
        tris = self.triStrips.decompose()
        print "Decomposed prims:",tris.getNumPrimitives()
        p = 0
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
        

    def completeTunnelPath(self):
        self.geomNode.addGeom(self.geom)
        
        if self.triStrips.getNumPrimitives() == 0:
            return
        
        floorMesh = CollisionFloorMesh()
        vertexReader = GeomVertexReader(self.vertexData, 'vertex') 
        
        print "Original prims:",self.triStrips.getNumPrimitives()
        
        p = 0
        for i in range(self.triStrips.getNumPrimitives()):
            v0 = self.triStrips.getPrimitiveStart(i)
            ve = self.triStrips.getPrimitiveEnd(i)
            j = v0 + 4
            
            # add the bottom triangles
            vertexReader.setRow(self.triStrips.getVertex(j))
            floorMesh.addVertex(Point3(vertexReader.getData3f()))
            vertexReader.setRow(self.triStrips.getVertex(j+1))
            floorMesh.addVertex(Point3(vertexReader.getData3f()))
            vertexReader.setRow(self.triStrips.getVertex(j+2))
            floorMesh.addVertex(Point3(vertexReader.getData3f()))
            floorMesh.addTriangle(p, p+1, p+2)
            
            vertexReader.setRow(self.triStrips.getVertex(j+3))
            floorMesh.addVertex(Point3(vertexReader.getData3f()))
            floorMesh.addTriangle(p+1, p+3, p+2)

            p += 4
        
        # this adds every triangle, but is not appropriate for a closed path
#         tris = self.triStrips.decompose()
#         print "Decomposed prims:",tris.getNumPrimitives()
#         p = 0
#         for i in range(tris.getNumPrimitives()):
#             v0 = tris.getPrimitiveStart(i)
#             ve = tris.getPrimitiveEnd(i)
#             if v0 < ve:
#                 vertexReader.setRow(tris.getVertex(v0))
#                 floorMesh.addVertex(Point3(vertexReader.getData3f()))
#                 vertexReader.setRow(tris.getVertex(v0+1))
#                 floorMesh.addVertex(Point3(vertexReader.getData3f()))
#                 vertexReader.setRow(tris.getVertex(v0+2))
#                 floorMesh.addVertex(Point3(vertexReader.getData3f()))
#                 floorMesh.addTriangle(p, p+1, p+2)
#                 p += 3
        
        self.floorCollNode.addSolid(floorMesh)
        
    
          
    def updatePhysics(self, task):
        pos = self.fpscamera.getPos()

        self.info.setText("Position: {0}, {1}, {2}".format(int(pos.x*100)/100., int(pos.y*100)/100., int(pos.z)/100.))

        return task.cont
                          

        
app = MyApp()
app.run()
