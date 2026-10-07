import struct
import unittest
from tools.bfme_host.maps import refpack,unpack,metadata,extend_camera
from tools.bfme_host.build import command_limits
from tools.bfme_host.camera import install,FAR_CONSTANT,FAR_MULTIPLY


def map_fixture():
    names=['WorldInfo','cameraMaxHeight','cameraGroundMaxHeight','cameraPitchAngle']
    data=b'CkMp'+struct.pack('<I',len(names))
    for i in range(len(names),0,-1):
        text=names[i-1].encode();data+=bytes([len(text)])+text+struct.pack('<I',i)
    properties=struct.pack('<H',3)
    for index,value in [(2,300),(3,380),(4,37.5)]:
        properties+=bytes([2])+index.to_bytes(3,'little')+struct.pack('<f',value)
    data+=struct.pack('<IHI',1,1,len(properties))+properties
    data+=struct.pack('<IHI',1,1,8)+b'UNCHANGED'
    return data


class BFMEHost(unittest.TestCase):
    def test_camera_extension_is_local_and_preserves_shared_constant(self):
        class Memory:
            base=0x400000
            hproc=1
            res={}
            class k:
                @staticmethod
                def VirtualAllocEx(*args):return 0x20000000
            memory={base+FAR_MULTIPLY:b'\xd8\x0d'+struct.pack('<I',base+FAR_CONSTANT),
                    base+FAR_CONSTANT:struct.pack('<f',1800)}
            def read(self,address,count):return self.memory.get(address)
            def write(self,address,value,code=False):self.memory[address]=value;return True
        game=Memory()
        install(game,8)
        self.assertEqual(game.read(0x20000000,4),struct.pack('<f',14400))
        self.assertEqual(game.read(game.base+FAR_CONSTANT,4),struct.pack('<f',1800))
        self.assertEqual(game.read(game.base+FAR_MULTIPLY+2,4),struct.pack('<I',0x20000000))
        self.assertTrue(game.res['bfmexbar_camera']['nearPlaneUnchanged'])

    def test_camera_extension_rejects_unrecognized_instruction(self):
        class Unexpected:
            base=0x400000
            def read(self,address,count):return b'\0'*count
        with self.assertRaises(RuntimeError):install(Unexpected(),8)

    def test_camera_only_patch_preserves_every_other_byte(self):
        original=map_fixture();result,changes=extend_camera(original,8)
        self.assertEqual(len(changes),1)
        offset=changes[0]['offset']
        self.assertEqual(original[:offset],result[:offset])
        self.assertEqual(original[offset+4:],result[offset+4:])
        fields=metadata(result)
        self.assertEqual(fields['cameraMaxHeight']['value'],2400)
        self.assertEqual(fields['cameraGroundMaxHeight']['value'],380)
        self.assertEqual(fields['cameraPitchAngle']['value'],37.5)

    def test_refpack_literal_and_overlap(self):
        # Literal ABCD, then copy six bytes at distance four: ABCDABCDAB.
        data=b'\x10\xfb\x00\x00\x0a\xe0ABCD\x0c\x03\xfc'
        self.assertEqual(refpack(data),b'ABCDABCDAB')

    def test_refpack_rejects_invalid_reference(self):
        with self.assertRaises(ValueError):refpack(b'\x10\xfb\0\0\x03\0\0\xfc')

    def test_ear_mismatched_size(self):
        with self.assertRaises(ValueError):unpack(b'EAR\0'+struct.pack('<I',99)+b'\x10\xfb\0\0\x04\xe0CkMp\xfc')

    def test_caps_preserve_starting_values(self):
        text='\n'.join(f'{f}CommandPointsMP{n} = 100 1000 ; comment' for f in ['Good','Evil'] for n in range(2,9))
        limits=command_limits(text,4)
        self.assertEqual(len(limits),14)
        self.assertTrue(all(value==(100,4000) for value in limits.values()))


if __name__=='__main__':unittest.main()
