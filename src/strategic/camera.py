"""Version-guarded, process-local BFME2 world-camera draw-distance extension.

openbfme2 reverse/symbols.csv identifies W3DView::setCameraTransform at
RVA 0x8BE6B. Its far distance is GlobalData[0x950] * 1800, independent of
map cameraMaxHeight. Only this instruction's constant operand is redirected;
the shared constant, near plane, cursor camera and executable file stay intact.
"""

from common.paths import ROOT
import ctypes
import struct

CAMERA_TRANSFORM = 0x8BE6B
FAR_MULTIPLY = 0x8BED6
FAR_CONSTANT = 0x7C7808


def install(game, factor):
    address = game.base + FAR_MULTIPLY
    expected = b'\xd8\x0d' + struct.pack('<I', game.base + FAR_CONSTANT)
    if game.read(address, 6) != expected:
        raise RuntimeError('World-camera far-plane instruction does not match BFME2 1.06')
    original = game.read(game.base + FAR_CONSTANT, 4)
    if original != struct.pack('<f', 1800.0):
        raise RuntimeError('Unexpected BFME2 world-camera far-distance constant')
    memory = game.k.VirtualAllocEx(ctypes.c_void_p(game.hproc), None, 4, 0x3000, 0x04)
    if not memory:
        raise ctypes.WinError(ctypes.get_last_error())
    value = struct.pack('<f', 1800.0 * factor)
    operand = struct.pack('<I', memory)
    if not game.write(memory, value) or not game.write(address + 2, operand, code=True):
        raise RuntimeError('Cannot install the world-camera draw-distance extension')
    if game.read(memory, 4) != value or game.read(address + 2, 4) != operand:
        raise RuntimeError('Camera draw-distance extension failed read-back verification')
    game.res['bfmexbar_camera'] = {'farMultiplierBefore': 1800, 'farMultiplierAfter': 1800 * factor,
                                 'nearPlaneUnchanged': True, 'diskBinaryUnchanged': True}


def register(smoke, factor):
    original = smoke.Game
    smoke.RVA['bmfe-workshopCameraInit'] = CAMERA_TRANSFORM

    class ExtendedCameraGame(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.on('bmfe-workshopCameraInit', self.extend_camera)

        @staticmethod
        def extend_camera(game, tid, ctx):
            install(game, factor)
            return False

    smoke.Game = ExtendedCameraGame
