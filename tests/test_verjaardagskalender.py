from unittest import TestCase
from freezegun import freeze_time
from verjaardagskalender import app


class TestVerjaardagskalender(TestCase):
  def test_hoofdpagina(self):
    with app.test_client() as client:
      verwachting = 'Op deze pagina wordt een verjaardagskalender getoond wanneer je ' + \
                    'ingelogd bent met een google-account'

      resultaat = client.get('/verjaardagskalender').data.decode('utf-8')
      self.assertIn(verwachting, resultaat)

  def test_toonleeftijdindagen(self):
    import verjaardagskalender
    self.assertTrue(verjaardagskalender.toonleeftijdindagen(1999))
    self.assertFalse(verjaardagskalender.toonleeftijdindagen(2634))
    self.assertTrue(verjaardagskalender.toonleeftijdindagen(2635))
    self.assertFalse(verjaardagskalender.toonleeftijdindagen(3001))

  def test_bepaalnaam(self):
    import verjaardagskalender
    persoon = {
      'etag': 'etagvalue',
      'names': [
        {
          'displayName': 'Jan Voorbeeld',
          'displayNameLastFirst': 'Voorbeeld, Jan',
          'familyName': 'Voorbeeld',
          'givenName': 'Jan',
          'metadata': {
            'primary': True,
            'source': {
              'id': '12ab34cd56ef',
              'type': 'CONTACT'
            },
            'sourcePrimary': True
          },
          'unstructuredName': 'Jan Voorbeeld'
        }
      ],
      'resourceName': 'people/12ab34cd56ef'
    }
    naam = verjaardagskalender.bepaalnaam(persoon)
    self.assertEqual('Jan Voorbeeld', naam)

  def test_bepaalnaam_geendisplay(self):
    import verjaardagskalender
    persoon = {
      'etag': 'etagvalue',
      'names': [
        {
          'displayNameLastFirst': 'Voorbeeld, Jan',
          'familyName': 'Voorbeeld',
          'givenName': 'Jan',
          'metadata': {
            'primary': True,
            'source': {
              'id': '12ab34cd56ef',
              'type': 'CONTACT'
            },
            'sourcePrimary': True
          },
          'unstructuredName': 'Jan Voorbeeld'
        }
      ],
      'resourceName': 'people/12ab34cd56ef'
    }
    naam = verjaardagskalender.bepaalnaam(persoon)
    self.assertEqual('No Name', naam)

  def test_bepaalnaam_leeg(self):
    import verjaardagskalender
    persoon = {
      'etag': 'etagvalue',
      'resourceName': 'people/12ab34cd56ef'
    }
    naam = verjaardagskalender.bepaalnaam(persoon)
    self.assertEqual('No Name', naam)

  def test_maaklegekalender(self):
    import verjaardagskalender
    resultaat = verjaardagskalender.maaklegekalender()
    self.assertNotEqual(resultaat, None)
    self.assertEqual(len(resultaat), 12)
    self.assertEqual(len(resultaat[1]), 31)
    self.assertEqual(len(resultaat[2]), 29)
    self.assertEqual(resultaat[3][4], {})

  def test_voegdatumaanlijsttoe(self):
    import verjaardagskalender
    lijst = verjaardagskalender.maaklegekalender()
    verjaardagskalender.voegdatumaanlijsttoe(lijst, 'Jan Voorbeeld', {'year': 2001, 'month': 2, 'day': 3})
    verjaardagskalender.voegdatumaanlijsttoe(lijst, 'Piet Voorbeeld', {'month': 4, 'day': 5})
    verjaardagskalender.voegdatumaanlijsttoe(lijst, 'Jan Tweeling', {'year': 2006, 'month': 7, 'day': 8})
    verjaardagskalender.voegdatumaanlijsttoe(lijst, 'Piet Tweeling', {'year': 2006, 'month': 7, 'day': 8})
    resultaat1 = lijst[2][3]
    resultaat2 = lijst[4][5]
    resultaat3 = lijst[7][8]
    self.assertEqual(resultaat1, {'Jan Voorbeeld': '(2001)'})
    self.assertEqual(resultaat2, {'Piet Voorbeeld': '(????)'})
    self.assertEqual(resultaat3, {'Jan Tweeling': '(2006)', 'Piet Tweeling': '(2006)'})

  @freeze_time("2024-12-23 13:28:00")
  def test_voegfeestdagtoeaanlijst(self):
    import verjaardagskalender
    legelijst = verjaardagskalender.maaklegekalender()
    lijst = verjaardagskalender.maaklegekalender()
    verjaardagskalender.voegfeestdagtoeaanlijst(lijst, 'Geen Jaartal', {'month': 4, 'day': 3})
    verjaardagskalender.voegfeestdagtoeaanlijst(lijst, 'Klaas Voorbeeld', {'year': 2022, 'month': 3, 'day': 28})
    self.assertDictEqual(lijst, legelijst)
    verjaardagskalender.voegfeestdagtoeaanlijst(lijst, 'Jan Voorbeeld', {'year': 2022, 'month': 4, 'day': 3})
    verjaardagskalender.voegfeestdagtoeaanlijst(lijst, 'Piet Voorbeeld', {'year': 2022, 'month': 3, 'day': 29})
    resultaat1 = lijst[12][28]
    resultaat2 = lijst[12][23]
    self.assertEqual(resultaat1, {'Jan Voorbeeld': '1000 dagen'})
    self.assertEqual(resultaat2, {'Piet Voorbeeld': '1000 dagen'})
