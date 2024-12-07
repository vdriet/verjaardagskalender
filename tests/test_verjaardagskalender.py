from unittest import TestCase

from verjaardagskalender import app


class TestVerjaardagskalender(TestCase):
  def test_hoofdpagina(self):
    with app.test_client() as client:
      verwachting = 'Op deze pagina wordt een verjaardagskalender getoond wanneer je ' + \
                    'ingelogd bent met een google-account'

      resultaat = client.get('/verjaardagskalender').data.decode('utf-8')
      self.assertIn(verwachting, resultaat)
