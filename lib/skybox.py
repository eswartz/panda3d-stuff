from abc import ABCMeta, abstractmethod
import os.path

from panda3d.core import GeomVertexData, GeomVertexFormat,GeomVertexWriter, RenderState, GeomTriangles, Geom, GeomNode
from panda3d.core import Filename
from panda3d.core import TextureAttrib, Texture
from panda3d.core import getModelPath
from utils import filesystem


class Skybox(object):
    """
    Create customizable skybox geometry
    """
    __metaclass__ = ABCMeta

    normals = [
            (-1, 0, 0),
            (1, 0, 0),
            (0, -1, 0),
            (0, 1, 0),
            (0, 0, -1),
            (0, 0, 1),
            ]

    def __init__(self, base):
        self._base = base

    def create(self, parent=None):
        """
        Create the skybox
        :return:
        """

        box = self.createBox()

        if not parent:
            parent = self._base.render
        sky = parent.attachNewNode(box)

        self.setupRender(sky)

        return sky


    def setupRender(self, sky):
        """
        Create the skybox
        :return:
        """
        sky.setTwoSided(True)       # HACK
        sky.setLightOff()

        sky.setBin('background', 0)
        sky.setDepthWrite(False)
        sky.setDepthTest(False)
        sky.setCompass()

        return sky

    @abstractmethod
    def getFaceMapping(self, normal):
        """
        Get the mapping from normal -> UVs, for a quad that is
        constructed clockwise from LL, LR, TR, TL.
        :param normal: the face''s key
        :return: array of (u,v) for the vertices of the quads on the face
        """

    @abstractmethod
    def getFaceTexture(self, normal):
        """
        Get the texture that decorates the given face.
        :param normal: the face's key
        :return: Texture
        """

    vertMappings = {
        (1, 0, 0) : [
            (-1, 1, -1),
            (-1, -1, -1),
            (-1, -1, 1),
            (-1, 1, 1),
        ],

        (-1, 0, 0) : [
            (1, -1, -1),
            (1, 1, -1),
            (1, 1, 1),
            (1, -1, 1),
        ],

        (0, 1, 0) : [
            (1, -1, -1),
            (-1, -1, -1),
            (-1, -1, 1),
            (1, -1, 1),
        ],

        (0, -1, 0) : [
            (-1, 1, -1),
            (1, 1, -1),
            (1, 1, 1),
            (-1, 1, 1),
        ],

        (0, 0, 1) : [
            (1, -1, -1),
            (-1, -1, -1),
            (-1, 1, -1),
            (1, 1, -1),
        ],

        (0, 0, -1) : [
            (-1, -1, 1),
            (1, -1, 1),
            (1, 1, 1),
            (-1, 1, 1),
        ],

    }
    def createBox(self):
        """
        Create the skybox GeomNode
        :return:
        """

        obj = ''
        obj += "# Skybox\n"
        obj += 'mtllib skybox.mtl\n'


        mtl = '# material for skybox\n'

        fmt = GeomVertexFormat.getV3n3t2()
        vdata = GeomVertexData('skybox', fmt, Geom.UHStatic)
        vdata.setNumRows(24)

        vertex = GeomVertexWriter(vdata, 'vertex')
        normals = GeomVertexWriter(vdata, 'normal')
        texcoord = GeomVertexWriter(vdata, 'texcoord')

        node = GeomNode('skybox')

        for normal in self.normals:
            geom = Geom(vdata)
            prim = GeomTriangles(Geom.UHStatic)

            idx = vertex.getWriteRow()

            verts = self.vertMappings[normal]
            tcs = self.getFaceMapping(normal)

            for v, t in zip(verts, tcs):
                vertex.addData3f(v[0]*2, v[1]*2, v[2]*2)
                normals.addData3f(normal)
                texcoord.addData2f(t)

                obj += 'v {0} {1} {2}\n'.format(v[0]*2, v[1]*2, v[2]*2)
                obj += 'vn {0} {1} {2}\n'.format(*normal)
                obj += 'vt {0} {1}\n'.format(*t)


            tex = self.getFaceTexture(normal)

            prim.addVertices(idx, idx + 1, idx + 3)
            prim.closePrimitive()

            obj += "usemtl {0}\n".format(tex.getName())
            obj += 'f {0}/{0} {1}/{1} {2}/{2}\n'.format(1+idx, 1+idx+1, 1+idx+3)

            prim.addVertices(idx + 1, idx + 2, idx + 3)
            prim.closePrimitive()

            obj += "usemtl {0}\n".format(tex.getName())
            obj += 'f {0}/{0} {1}/{1} {2}/{2}\n'.format(1+idx+1, 1+idx+2, 1+idx+3)

            geom.addPrimitive(prim)

            tex.setWrapU(Texture.WMMirror)
            tex.setWrapV(Texture.WMMirror)

            node.addGeom(geom, RenderState.make(TextureAttrib.make(tex)))


            mtl += "newmtl {0}\n".format(tex.getName())
            mtl += "Ka 1 1 1\n"
            mtl += "Kd 1 1 1\n"
            mtl += "map_Kd {0}\n".format(tex.getFilename().toOsSpecific())

        return node

    def loadTexture(self, texpath, name, exts):
        tex = None
        if not texpath:
            texpath = '.'
        try:
            path = filesystem.toPanda(os.path.join(texpath, name + exts))
            fname = Filename(path)
            if fname.resolveFilename(getModelPath().getValue()):
                tex = self._base.loader.loadTexture(fname)
        except TypeError:       # exts is a list
            for e in exts:
                path = filesystem.toPanda(os.path.join(texpath, name + e))
                fname = Filename(path)
                if fname.resolveFilename(getModelPath().getValue()):
                    tex = self._base.loader.loadTexture(fname)
                    break
        if not tex:
            raise Exception("did not find any match for "+texpath+"/"+name+" with "+str(exts))
        return tex

class CubemapSkybox(Skybox):

    nameMappings = {
                (1, 0, 0): '1',
                (-1, 0, 0): '0',
                (0, 0, -1): '4',
                (0, 0, 1): '5',
                (0, -1, 0): '2',
                (0, 1, 0): '3',
                }
    texcoordMappings = {
            (-1, 0, 0): [
                (1, 1), (1, 0), (0,0), (0,1)
            ],
            (1, 0, 0): [
                (0, 0), (0,1), (1,1), (1,0)
            ],
            (0, -1, 0): [
                (0, 0), (1, 0), (1, 1), (0, 1)
            ],
            (0, 1, 0): [
                (1, 1), (0, 1), (0, 0), (1, 0)
            ],
            (0, 0, -1): [
                (0, 1), (1, 1), (1, 0), (0, 0)
            ],
            (0, 0, 1): [
                (0, 1), (1, 1), (1, 0), (0, 0)
            ],
        }
    def __init__(self, base, path, baseName, exts):
        Skybox.__init__(self, base)
        self._baseName = baseName
        self._path = path
        self._exts = exts

    def getFaceTexture(self, normal):
        suffix = self.nameMappings[normal]
        tex = self.loadTexture(self._path, self._baseName + suffix, self._exts)
        return tex

    def getFaceMapping(self, normal):
        return self.texcoordMappings[normal]


class NetmapSkybox(Skybox):
    AXES = {
            (-1, 0, 0): 'posx',
            (1, 0, 0): 'negx',
            (0, 0, -1): 'posy',
            (0, 0, 1): 'negy',
            # our Z = their Y
            (0, -1, 0): 'posz',
            (0, 1, 0): 'negz',
            }

    NUMBERS = {
            (-1, 0, 0): '2',
            (1, 0, 0): '0',
            (0, 0, -1): '4',
            (0, 0, 1): '3',
            # our Z = their Y
            (0, -1, 0): '1',
            (0, 1, 0): '5',
            }
    texcoordMappings = {
            (-1, 0, 0): [
                (1, 0), (0, 0), (0, 1), (1, 1)
            ],
            (1, 0, 0): [
                (1, 0), (0, 0), (0, 1), (1, 1)
            ],
            (0, -1, 0): [
                (0, 0), (1, 0), (1, 1), (0, 1)
            ],
            (0, 1, 0): [
                (0, 0), (1, 0), (1, 1), (0, 1)
            ],
            (0, 0, -1): [
                (0, 1), (1, 1), (1, 0), (0, 0)
            ],
            (0, 0, 1): [
                (1, 0), (0, 0), (0, 1), (1, 1)
            ],
        }

    def __init__(self, base, path, baseName, exts, naming=AXES):
        Skybox.__init__(self, base)
        self._baseName = baseName
        self._path = path
        self._exts = exts
        self._naming = naming

    def getFaceTexture(self, normal):
        suffix = self._naming[normal]
        tex = self.loadTexture(self._path, self._baseName + suffix, self._exts)
        return tex

    def getFaceMapping(self, normal):
        return self.texcoordMappings[normal]

