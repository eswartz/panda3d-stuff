__author__ = 'ejs'

import errno
import glob
import logging

import inspect
import os
import sys
import platform

def mkdirP(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def get_actual_filename(name):
    if not '\\' in name:
        return name
    dirs = name.split('\\')
    # disk letter
    test_name = [dirs[0].upper()]
    for d in dirs[1:]:
        test_name += ["%s[%s]" % (d[:-1], d[-1])]
    res = glob.glob('\\'.join(test_name))
    if not res:
        #File not found
        return None
    return res[0]

_mainScriptDir = None

def getScriptDir(module=None, toParent=None):
    """
    Find the directory where the main script is running
    From http://stackoverflow.com/questions/3718657/how-to-properly-determine-current-script-directory-in-python/22881871#22881871

    :param follow_symlinks:
    :return:
    """
    global _mainScriptDir
    if module and not _mainScriptDir:
        if getattr(sys, 'frozen', False): # py2exe, PyInstaller, cx_Freeze
            path = os.path.abspath(sys.executable)
        else:
            path = inspect.getabsfile(module)
            if not toParent:
                toParent = "../.."
            path = os.path.join(path, toParent)       # remove our package and module

            path = os.path.realpath(path)

        # Windows needs real case for e.g. model path lookups
        path = get_actual_filename(path)

        _mainScriptDir = os.path.dirname(path)        # our package

    return _mainScriptDir

_libScriptDir = None

def getLibScriptDir():
    """
     Find the directory where the main script is running
    From http://stackoverflow.com/questions/3718657/how-to-properly-determine-current-script-directory-in-python/22881871#22881871

    :param follow_symlinks:
    :return:
    """
    global _libScriptDir
    if not _libScriptDir:
        if getattr(sys, 'frozen', False): # py2exe, PyInstaller, cx_Freeze
            path = os.path.abspath(sys.executable)
        else:
            path = inspect.getabsfile(sys.modules['utils.filesystem'])
            path = os.path.join(path, "../..")       # remove our package and module

            path = os.path.realpath(path)

        # Windows needs real case for e.g. model path lookups
        path = get_actual_filename(path)

        #print "getLibScriptDir:",path

        _libScriptDir = os.path.dirname(path)        # our package

    return _libScriptDir

def getUserDataDir():
    """
    Get real user data folder under which the game data can be stored.
    :return:
    """

    if platform.system() == 'Windows':
        # HOME is not trustworthy
        userhome = os.environ.get('USERPROFILE')
        if not userhome:
            userhome = os.path.expanduser('~')

        data_dir = os.path.join(userhome, "AppData", "Roaming")
        if not os.path.exists(data_dir):
            data_dir = os.path.join(userhome, "Documents")

    elif platform.system() == 'Linux':
        data_dir = os.path.expanduser("~/.config")

    elif platform.system() == 'Darwin':
        data_dir = os.path.expanduser("~/Library")
    else:
        data_dir = os.path.expanduser("~")

    return data_dir

_tempDir = None

def findDataFilename(name, extract=False, executable=False):
    """
    Resolve a filename along Panda's model-path.
    :param name:
    :return: filename or None
    """
    from panda3d.core import Filename, getModelPath
    from panda3d.core import VirtualFileSystem

    logging.debug("findDataFilename: "+ name +" on: \n" + str(getModelPath().getValue()))

    vfs = VirtualFileSystem.getGlobalPtr()
    fileName = Filename(name)
    vfile = vfs.findFile(fileName, getModelPath().getValue())
    if not vfile:
        if extract and name.endswith(".exe"):
            fileName = Filename(name[:-4])
            vfile = vfs.findFile(fileName, getModelPath().getValue())
        if not vfile:
            return None

    fileName = vfile.getFilename()
    if extract:
        # see if the file is embedded in some virtual place OR has the wrong perms
        from panda3d.core import SubfileInfo

        info = SubfileInfo()

        needsCopy = not vfile.getSystemInfo(info) or info.getFilename() != fileName
        if not needsCopy:
            if executable:
                # see if on Linux or OSX and not executable
                try:
                    stat = os.stat(fileName.toOsSpecific())
                    if (stat.st_mode & 0111) == 0:
                        logging.error("Found %s locally, but not marked executable!", fileName)
                        needsCopy = True
                except:
                    needsCopy = True

        if needsCopy:
            # virtual file needs to be copied out
            global _tempDir
            if not _tempDir:
                import tempfile
                _tempDir = os.path.realpath(tempfile.mkdtemp())
                #print "Temp dir:",_tempDir

            xpath = _tempDir + '/' + fileName.getBasename()
            xTarg = Filename.fromOsSpecific(xpath)

            # on Windows, case-sensitivity must be honored for the following to work
            xTarg.makeCanonical()

            print "extracting",fileName,"to",xTarg

            if not xTarg.exists():
                if not vfs.copyFile(fileName, xTarg):
                    raise IOError("extraction failed when copying " + str(fileName) + " to " + str(xTarg))

            fileName = xTarg
            os.chmod(fileName.toOsSpecific(), 0777)

    return fileName


def findDataFile(name, extract=False, executable=False):
    """
    Resolve a filename along Panda's model-path.
    :param name:
    :return: path or None
    """
    fileName = findDataFilename(name, extract, executable)
    if not fileName:
        return None
    return fileName.toOsSpecific()


def toPanda(path):
    path = path.replace('\\', '/')
    # make Windows path look Unix-y for the VFS
    if len(path) > 3 and path[1] == ':' and path[2] == '/':
        path = '/' + path[0].lower() + path[2:]
    return path
