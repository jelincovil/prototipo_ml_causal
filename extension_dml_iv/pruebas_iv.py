"""Pruebas mínimas de la extensión; no ejecutan ni alteran el prototipo original."""
import inspect
import math
import unittest

import numpy as np
import pandas as pd

from datos_iv import EsquemaIV, comprobar_pared, leer, verificar_splits
from estimacion_iv import estimar
from generar_datos_iv import generar_universo


class PruebasIV(unittest.TestCase):
    def test_generacion_y_esquema_son_reproducibles(self):
        datos_a, verdad_a = generar_universo(n=300)
        datos_b, verdad_b = generar_universo(n=300)
        pd.testing.assert_frame_equal(datos_a, datos_b)
        self.assertEqual(verdad_a, verdad_b)
        self.assertNotIn("U", datos_a.columns)
        self.assertFalse({"d0", "d1", "y0", "y1", "tau"} & set(datos_a.columns))
        EsquemaIV().validar(list(datos_a.columns), datos_a.to_dict("series"))

    def test_integridad_de_los_datos_incluidos(self):
        self.assertTrue(verificar_splits())
        comprobar_pared()

    def test_esquema_rechaza_roles_duplicados(self):
        observados = leer("train")
        with self.assertRaisesRegex(ValueError, "más de un rol"):
            EsquemaIV(tratamiento="y").validar(list(observados), observados)

    def test_estimacion_finita_acotada_y_reproducible(self):
        observados = leer("train")
        resultado_a = estimar(observados)
        resultado_b = estimar(observados)
        self.assertEqual(resultado_a, resultado_b)
        self.assertGreater(resultado_a["primera_etapa"]["diferencia"], 0)
        self.assertTrue(math.isfinite(resultado_a["coeficiente"]))
        self.assertLess(resultado_a["ic95"][0], resultado_a["ic95"][1])
        self.assertTrue(np.isfinite(resultado_a["error_estandar"]))

    def test_el_estimador_no_admite_verdad_como_entrada(self):
        parametros = set(inspect.signature(estimar).parameters)
        self.assertEqual(parametros, {"observados", "semilla", "esquema"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
