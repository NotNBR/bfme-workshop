"""Small real FFmpeg round trip, without proprietary game assets."""
from pathlib import Path
import tempfile
import unittest
from video.encoding import encode, export_profile


class VideoExportTests(unittest.TestCase):
    def test_profile_preserves_all_frames_and_protects_existing_files(self):
        with tempfile.TemporaryDirectory(prefix='workshop video test ') as folder:
            folder=Path(folder);source=folder/'source.mp4';target=folder/'small.mp4'
            encode(['-f','lavfi','-i','testsrc2=size=160x90:rate=30:duration=1',
                    '-f','lavfi','-i','sine=frequency=440:duration=1',
                    '-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',source],folder/'source.log')
            profiles=folder/'profiles.toml'
            profiles.write_text('[profiles.small]\nvideo_kbps=250\naudio_kbps=64\nmax_bytes=100000\npreset="fast"\n')
            result=export_profile(source,target,profiles,'small')
            self.assertEqual(result['frames'],30)
            self.assertLess(result['bytes'],100000)
            self.assertEqual(result['size'],(160,90))
            before=target.read_bytes()
            with self.assertRaises(FileExistsError):export_profile(source,target,profiles,'small')
            self.assertEqual(target.read_bytes(),before)


if __name__=='__main__':unittest.main()
