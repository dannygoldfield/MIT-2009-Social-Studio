from pathlib import Path
import json
import tempfile
import unittest
import uuid
import wave
import numpy as np
from PIL import Image
from mit2009_studio import media, render, server

class StudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.before_formats = media.FORMATS.copy()
        media.FORMATS['vertical'] = (270, 480)
        media.FORMATS['square'] = (270, 270)
        media.FORMATS['landscape'] = (480, 270)
        cls.rows = {}
        cls.photo = cls.root / 'photo.jpg'
        image = Image.new('RGB', (720, 480), '#a72d35')
        image.paste(Image.new('RGB', (240, 480), '#eee6d3'), (240, 0))
        image.save(cls.photo)
        cls.add('photo', cls.photo)
        for name, duration in [('sound', 4), ('accent', .15)]:
            t=np.arange(round(duration*48000))/48000
            samples=(np.sin(2*np.pi*220*t)*4000).astype('<i2')
            with wave.open(str(cls.root / f'{name}.wav'),'wb') as out:
                out.setnchannels(2);out.setsampwidth(2);out.setframerate(48000)
                out.writeframes(np.column_stack((samples,samples)).tobytes())
            cls.add(name, cls.root / f'{name}.wav')

    @classmethod
    def add(cls, name, path, role='source'):
        cls.rows[name] = dict(id=name,name=path.name,path=path,role=role,**media.inspect(path))

    @classmethod
    def tearDownClass(cls):
        media.FORMATS.clear();media.FORMATS.update(cls.before_formats)
        cls.temp.cleanup()

    def export(self, tool, config):
        folder=self.root/uuid.uuid4().hex;folder.mkdir()
        path,role=render.RENDERERS[tool](config,self.rows.__getitem__,folder,lambda _:None)
        self.assertTrue(path.is_file());self.assertGreater(path.stat().st_size,100)
        return path,role,media.probe(path)

    def test_01_audio_native_duration_optional_layers_and_repeatability(self):
        config=dict(main='sound',accent='accent',music='sound',duration=2.3,seed=5)
        first,_,info=self.export('audio',config)
        second,_,_=self.export('audio',config)
        self.assertEqual(media.digest(first),media.digest(second))
        self.assertAlmostEqual(float(info['format']['duration']),2.3,places=3)
        self.assertEqual(info['streams'][0]['sample_rate'],'48000')
        self.assertEqual(info['streams'][0]['channels'],2)
        solo,_,_=self.export('audio',dict(main='sound',duration=2,seed=5))
        self.assertTrue(solo.exists())

    def test_02_video_photo_order_timing_and_silence(self):
        path,_,info=self.export('video',dict(sequence=[dict(id='photo',duration=.8),dict(id='photo',duration=1.2,focus_x=.2)],dissolve=.08,motion='pan'))
        self.assertEqual(info['streams'][0]['width'],270)
        self.assertEqual(info['streams'][0]['height'],480)
        self.assertEqual(info['streams'][0]['nb_frames'],'60')
        self.assertEqual(len(info['streams']),1)
        self.add('video',path)

    def test_03_full_frame_crops_do_not_create_borders(self):
        source=Image.new('RGB',(900,600),'#ffffff')
        for motion in ['still','pan','push']:
            for focus in [0,.5,1]:
                for t in [0,.5,1]:
                    frame=render.crop_frame(source,(270,480),t,motion,focus,focus)
                    self.assertEqual(frame.getextrema(),((255,255),(255,255),(255,255)))

    def test_04_clip_trim_and_bad_duration(self):
        path,_,info=self.export('video',dict(sequence=[dict(id='video',duration=.6,start=.2)],fit='contain'))
        self.assertEqual(info['streams'][0]['nb_frames'],'18')
        with self.assertRaisesRegex(ValueError,'shorter'):
            self.export('video',dict(sequence=[dict(id='video',duration=10)]))

    def test_05_all_text_styles_export_and_animate(self):
        for style in ['fade','rise','words','type']:
            path,_,info=self.export('text',dict(text='BUILD.\nTEST.\nREPEAT.',duration=1,hold=1,style=style))
            self.assertEqual(info['streams'][0]['nb_frames'],'30')
            empty=render.text_layer('BUILD.',(270,480),-.1,1,style)
            shown=render.text_layer('BUILD.',(270,480),.7,1,style)
            self.assertIsNone(empty.getbbox());self.assertIsNotNone(shown.getbbox())

    def test_06_transparent_overlay_has_alpha(self):
        path,role,info=self.export('text',dict(text='2.009',duration=1,hold=1,transparent=True))
        self.assertEqual(role,'text-overlay')
        self.assertTrue(info['streams'][0]['pix_fmt'].startswith('yuva'))
        self.assertTrue((path.parent/'overlay-preview.mp4').is_file())
        self.add('overlay',path,role)

    def test_07_assembler_preserves_video_and_adds_sound(self):
        path,_,info=self.export('assemble',dict(video='video',audio='sound',fade=0))
        self.assertEqual({s['codec_type'] for s in info['streams']},{'video','audio'})
        self.assertAlmostEqual(float(info['format']['duration']),2,places=2)
        def video_hash(p):
            return media.run([media.ffmpeg(),'-v','error','-i',str(p),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-'])
        self.assertEqual(video_hash(path),video_hash(self.rows['video']['path']))
        self.add('with-audio',path)

    def test_08_assembler_composites_transparent_text(self):
        path,_,info=self.export('assemble',dict(video='video',audio='sound',overlay='overlay'))
        self.assertEqual(len(info['streams']),2)
        self.assertEqual(info['streams'][0]['width'],270)

    def test_09_short_audio_requires_explicit_loop(self):
        with self.assertRaisesRegex(ValueError,'shorter'):
            self.export('assemble',dict(video='video',audio='accent'))
        _,_,info=self.export('assemble',dict(video='video',audio='accent',loop_audio=True))
        self.assertAlmostEqual(float(info['format']['duration']),2,places=2)

    def test_10_text_over_video_preserves_audio(self):
        _,_,info=self.export('text',dict(text='Ready to build',duration=1.5,hold=1.5,base='with-audio'))
        self.assertEqual({s['codec_type'] for s in info['streams']},{'video','audio'})

    def test_11_library_rejects_files_outside_its_data_folder(self):
        previous=server.DATA;server.DATA=self.root/'data';server.initialize()
        try:
            identity=uuid.uuid4().hex
            server.add_entry(dict(id=identity,file='../photo.jpg'))
            with self.assertRaisesRegex(ValueError,'unavailable'):
                server.lookup(identity)
            for wrong in ['../../HPR-Umbrella','/Users/dannygoldfield/Projects/HPR-Audio-Generator',None]:
                with self.assertRaises(ValueError):server.lookup(wrong)
        finally:server.DATA=previous

    def test_12_invalid_render_inputs_fail_clearly(self):
        for config in [dict(text=''),dict(text='x'*301),dict(text='test',duration=1,start=2)]:
            with self.assertRaises(ValueError):self.export('text',config)
        with self.assertRaises(ValueError):self.export('video',dict(sequence=[]))
        with self.assertRaises(ValueError):media.number(float('nan'),1,0,5)

if __name__=='__main__':unittest.main(verbosity=2)
