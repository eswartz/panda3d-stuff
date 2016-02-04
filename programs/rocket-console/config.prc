#notify-level debug
#default-directnotify-level warning

#notify-level-express debug
#notify-level-rocket debug


# These specify where model files may be loaded from.  You probably
# want to set this to a sensible path for yourself.  $THIS_PRC_DIR is
# a special variable that indicates the same directory as this
# particular Config.prc file.

model-path    $MAIN_DIR
model-path    $MAIN_DIR/assets

# Enable/disable performance profiling tool and frame-rate meter

want-pstats            #t
show-frame-rate-meter  #t

# Enable audio using the OpenAL audio library by default:

#audio-library-name p3openal_audio

# Enable the use of the new movietexture class.

use-movietexture #t

# The new version of panda supports hardware vertex animation, but it's not quite ready

hardware-animated-vertices #t

# Enable the model-cache, but only for models, not textures.

model-cache-dir $HOME/.panda3d/cache
model-cache-textures #f

# This option specifies the default profiles for Cg shaders.
# Setting it to #t makes them arbvp1 and arbfp1, since these
# seem to be most reliable. Setting it to #f makes Panda use
# the latest profile available.

basic-shaders-only #f
sync-video #t

#yield-timeslice #t
#support-threads #t
#threading-model Cull/Draw


