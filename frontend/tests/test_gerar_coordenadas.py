import runpy
import struct
import tempfile
import unittest
from pathlib import Path

gerador = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/gerar-coordenadas-municipios.py"))


def geometria(latitude, longitude, epsg=4674, ordem="<"):
    flag = int(ordem == "<")
    return struct.pack(ordem + "2sBBiBIdd", b"GP", 0, flag, epsg, flag, 1, longitude, latitude)


class TestGerador(unittest.TestCase):
    def test_eixos_e_endian(self):
        for ordem in ("<", ">"):
            self.assertEqual(gerador["ponto"](geometria(12.3, -45.6, ordem=ordem)), (12.3, -45.6))

    def test_duplicatas_equivalentes(self):
        registro = ("0123456", geometria(1, 2))
        self.assertEqual(gerador["consolidar"]([registro, registro]),
                         ({"0123456": (1, 2)}, {"0123456"}, 2))

    def test_conflito_antes_de_arredondar(self):
        with self.assertRaisesRegex(ValueError, "conflitantes"):
            gerador["consolidar"]([("0123456", geometria(1, 2)), ("0123456", geometria(1, 2.0000001))])

    def test_codigo_invalido(self):
        for codigo in (1234567, "123456", "123456x"):
            with self.subTest(codigo=codigo), self.assertRaisesRegex(ValueError, "Código municipal"):
                gerador["consolidar"]([(codigo, geometria(1, 2))])

    def test_referencial_invalido(self):
        with self.assertRaisesRegex(ValueError, "EPSG:4674"):
            gerador["ponto"](geometria(1, 2, epsg=4326))

    def test_coordenadas_invalidas(self):
        for par in ((91, 0), (0, -181), (0, float("inf")), (float("nan"), 0)):
            with self.subTest(par=par), self.assertRaisesRegex(ValueError, "coordenadas inválidos"):
                gerador["ponto"](geometria(*par))

    def test_integridade_invalida(self):
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "entrada.zip"
            arquivo.write_bytes(b"arquivo sintetico")
            with self.assertRaisesRegex(ValueError, "SHA-256 do ZIP"):
                gerador["extrair"](arquivo)


if __name__ == "__main__":
    unittest.main()
