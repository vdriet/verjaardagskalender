""" Maken van een verjaardagskalender op basis van google contacten """
import os
from datetime import date, timedelta
from time import time

import requests
import waitress
from authlib.integrations.flask_client import OAuth
from flask import Flask, redirect, render_template, session, url_for, request
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config['FLASK_APP'] = 'verjaardagskalender'
app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)

app.config['PREFERRED_URL_SCHEME'] = 'https'
SHOWDAYS = 366
oauth = OAuth(app)

oauth.register(
  name='google',
  server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
  client_kwargs={
    'scope': 'openid email profile https://www.googleapis.com/auth/contacts'
  }
)


def lees_json(url, token):
  """ Lees json van een url met autorisatie """
  try:
    headers = {'Content-Type': 'application/json',
               'Authorization': f'Bearer {token}'}
    req = requests.get(url, headers=headers, verify=False, timeout=6, allow_redirects=False)
    return req.json()
  except requests.ConnectionError:
    return 'failed to connect'


def istokenvalid():
  """ Controleer geldigheid van het sessie-token """
  exp = session.get('exp')
  if exp is None or exp - time() < 0:
    return False
  return True


@app.route('/verjaardagskalender', methods=['GET'])
def hoofdpagina():
  """ Tonen van de hoofdpagina """
  user = session.get('user')
  token = session.get('access_token')
  valid = istokenvalid()
  if valid:
    return kalender()
  return render_template('index.html', user=user, token=token, valid=valid)


def kalender():
  """ Ophalen gegevens en maken verjaardagskalender """
  if not istokenvalid():
    redirect_uri = url_for('authorize', _external=True, _scheme='https')
    session['returnpath'] = '/verjaardagskalender'
    return oauth.google.authorize_redirect(redirect_uri)
  contacten = haalcontacten()
  data = verwerkcontacten(contacten)
  return render_template('kalender.html', data=data)


def haalcontacten():
  """ haal contacten """
  url = 'https://people.googleapis.com/v1/people/me/connections?personFields=names,birthdays,events'
  token = session.get('access_token')
  pageurl = url
  data = []
  while True:
    jsondata = lees_json(pageurl, token)
    data += jsondata['connections']
    pagetoken = jsondata.get('nextPageToken')
    if pagetoken is None:
      break
    pageurl = url + f'&pageToken={pagetoken}'
  return data


def toonleeftijdindagen(leeftijdindagen):
  """ Bepaal of de datum op basis van aantal dagen getoond moet worden """
  dagenvan1000tal = int(leeftijdindagen) % 1000
  if dagenvan1000tal == 0 or dagenvan1000tal > (1000 - SHOWDAYS):
    return True
  return False


def bepaalnaam(persoon):
  """ Bepaal de naam van het contact """
  names = persoon.get('names')
  if names is None:
    return 'No Name'
  return names[0].get('displayName', 'No Name')


def maaklegekalender():
  """ Maak een lege kalender """
  legekalender = {}
  for maandnr in range(1, 13):
    maandlengte = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    maand = {}
    for dagnr in range(1, maandlengte[maandnr] + 1):
      maand[dagnr] = {}
    legekalender[maandnr] = maand
  return legekalender


def voegdatumaanlijsttoe(contactenlijst, naam, datum):
  """ Voeg een datum aan de lijst toe """
  jaar = datum.get('year', '????')
  maand = datum.get('month')
  dag = datum.get('day')
  eventementenopdag = contactenlijst.get(maand).get(dag)
  eventementenopdag[naam] = f'({jaar})'


def voegfeestdagtoeaanlijst(contactenlijst, naam, datum):
  """ Voeg een 1000-dagen feestdag toe aan de lijst """
  jaar = datum.get('year')
  if jaar is None:
    return
  maand = datum.get('month')
  dag = datum.get('day')
  vandaag = date.today()
  leeftijdindagen = (vandaag - date(jaar, maand, dag)).days
  if toonleeftijdindagen(leeftijdindagen):
    if leeftijdindagen % 1000 == 0:
      feestdatum = vandaag
      aantaldagentevieren = leeftijdindagen
    else:
      feestdatum = vandaag + timedelta(1000 - leeftijdindagen % 1000)
      aantaldagentevieren = leeftijdindagen + 1000 - leeftijdindagen % 1000
    feestmaand = feestdatum.month
    feestdag = feestdatum.day
    eventementenopdag = contactenlijst.get(feestmaand).get(feestdag)
    eventementenopdag[naam] = f'{aantaldagentevieren} dagen'


def verwerkcontacten(contacten):
  """ Verwerk de contacten """
  feestdagenlijst = maaklegekalender()
  for persoon in contacten:
    naam = bepaalnaam(persoon)

    geboortedagen = persoon.get('birthdays')
    if not geboortedagen is None:
      geboortedatum = geboortedagen[0].get('date')
      if not geboortedatum is None:
        voegdatumaanlijsttoe(feestdagenlijst, naam, geboortedatum)
        voegfeestdagtoeaanlijst(feestdagenlijst, naam, geboortedatum)
    evenementen = persoon.get('events')
    if not evenementen is None:
      for evenement in evenementen:
        langenaam = naam + ' (' + evenement.get('type', '?') + ')'
        evenementdatum = evenement.get('date')
        if not evenementdatum is None:
          voegdatumaanlijsttoe(feestdagenlijst, langenaam, evenementdatum)
          voegfeestdagtoeaanlijst(feestdagenlijst, langenaam, evenementdatum)
  return feestdagenlijst


@app.route('/verjaardagskalender/login')
def login():
  """ login op basis van oauth """
  session['returnpath'] = '/verjaardagskalender'
  if 'localhost' in request.host:
    protocol = 'http'
  else:
    protocol = 'https'
  redirect_uri = url_for('authorize', _external=True, _scheme=protocol)
  return oauth.google.authorize_redirect(redirect_uri)


@app.route('/verjaardagskalender/logout')
def logout():
  """ uitloggen """
  session.pop('exp', None)
  session.pop('user', None)
  session.pop('access_token', None)
  return redirect('/verjaardagskalender')


@app.route('/verjaardagskalender/authorize')
def authorize():
  """ autoriseer de user """
  token = oauth.google.authorize_access_token()
  session['exp'] = token.get('expires_at')
  session['user'] = token['userinfo']
  session['access_token'] = token['access_token']
  returnpath = session.get('returnpath', '/verjaardagskalender')
  return redirect(returnpath)


if __name__ == '__main__':
  waitress.serve(app, host="0.0.0.0", port=8084)
