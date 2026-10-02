import pathlib,struct,tempfile,unittest,zipfile,zlib
from map_pipeline.assets import decode_bc1_tga,extract_assets,script_texts
from map_pipeline.parser import MapError


class AssetTests(unittest.TestCase):
    def test_bc1_red_block(self):
        header=bytearray(28);header[:4]=b'IWi\x06';header[4]=11;header[5]=2;struct.pack_into('<HHH',header,6,4,4,1)
        tga=decode_bc1_tga(bytes(header)+struct.pack('<HHI',0xf800,0,0))
        self.assertEqual(tga[18:],bytes((0,0,255,255))*16)
    def test_bc1_transparent_index(self):
        header=bytearray(28);header[:4]=b'IWi\x06';header[4]=11;header[5]=2;struct.pack_into('<HHH',header,6,4,4,1)
        tga=decode_bc1_tga(bytes(header)+struct.pack('<HHI',0,0xffff,0xffffffff))
        self.assertEqual(tga[18:],bytes(64))
    def test_mipmap_images_are_rejected(self):
        with self.assertRaises(MapError):decode_bc1_tga(b'IWi\x06'+bytes(32))
    def test_safe_archive_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp);archive=p/'unsafe.iwd'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape.gsc','main() {}')
            with self.assertRaises(MapError):extract_assets(archive,p/'out')
            self.assertFalse((p/'escape.gsc').exists())
    def test_source_fastfile_extraction(self):
        payload=b'maps/mp/example.gsc\0main()\n{\n return;\n}\0'
        found=script_texts(b'IWffu100'+struct.pack('<I',5)+zlib.compress(payload))
        self.assertIn('maps/mp/example.gsc',found)


if __name__=='__main__':unittest.main()
