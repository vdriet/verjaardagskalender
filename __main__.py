""" maken van een verjaardagskalender op basis van google contacten """
from datetime import date, timedelta
import os
from time import time
from urllib.request import Request, urlopen

from authlib.integrations.flask_client import OAuth
from flask import Flask, json, redirect, render_template, session, url_for
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
  """ lees json van een url met autorisatie """
  req = Request(url)
  req.add_header('Content-Type', 'application/json')
  req.add_header('Authorization', f'Bearer {token}')
  with urlopen(req) as stream:
    response = stream.read()
    content_json = json.loads(response)
  return content_json

def istokenvalid():
  """ check geldigheid van het sessie-token """
  exp = session.get('exp')
  if exp is None:
    print('Geen token')
    return False
  now = time()
  if exp - now < 0:
    print(f'Verlopen {now - exp:.1f} seconden geleden')
    return False
  print(f'Nog geldig: {exp - now:.1f} seconden')
  return True

@app.route('/verjaardagskalender', methods=['GET'])
def index():
  """ tonen van hoofdpagina met informatie """
  user = session.get('user')
  token = session.get('access_token')
  valid = istokenvalid()
  return render_template('index.html', user=user, token=token, valid=valid)

@app.route('/verjaardagskalender/show', methods=['GET'])
def kalender():
  """ ophalen van de verjaardagskalender """
  if not istokenvalid():
    redirect_uri = url_for('authorize', _external=True, _scheme='https')
    session['returnpath'] = '/verjaardagskalender/show'
    return oauth.google.authorize_redirect(redirect_uri)
  connections = getconnections()
  data = processconnections(connections)
  newdata = sorted(data, key=lambda d: d['sortkey'])
  return render_template('kalender.html', data=newdata)

@app.route('/verjaardagskalender/show1', methods=['GET'])
def kalender1():
  """ ophalen van de verjaardagskalender """
  if not istokenvalid():
    redirect_uri = url_for('authorize', _external=True, _scheme='https')
    session['returnpath'] = '/verjaardagskalender/show1'
    return oauth.google.authorize_redirect(redirect_uri)
  connections = getconnections()
  data = processconnections(connections)
  newdata = {}
  for row in data:
    month = int(row['month'])
    day = int(row['day'])
    monthdata = newdata.get(month, {})
    daydata = monthdata.get(day, {})
    daydata[row['name']] = row['ageindays']
    monthdata[day] = daydata
    newdata[month] = monthdata
  return render_template('kalender1.html', data=newdata)

def getconnections():
  """ haal de contacten op """
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

def createrowdate(name, jsondate):
  """ maken een regel met gegevens van een verjaardag """
  outy = jsondate.get('year', '????')
  outm = jsondate.get('month')
  outd = jsondate.get('day')
  return createrow(name, outy, outm, outd)

def createrow(name, year, month, day):
  """ maken van een regel op basis van dag/maand/jaar """
  ret = []
  today = date.today()
  ageindays = '-' if year == '????' else (today - date(year, month, day)).days
  if showbirthday(month, day):
    sortyear = today.year
    if month < today.month:
      sortyear += 1
    ret.append(createrowdatekey(name, f'{year}-{month:02d}-{day:02d}',
                                sortyear, month, day, f'({year})'))
  if showdaysage(ageindays):
    celebrateday = today + timedelta(1000 - ageindays % 1000)
    daysyear = celebrateday.year
    daysmonth = celebrateday.month
    daysday = celebrateday.day
    celebrateagedays = ageindays + 1000 - ageindays % 1000
    ret.append(createrowdatekey(name, f'{year}-{month:02d}-{day:02d}',
                                daysyear, daysmonth, daysday, celebrateagedays))
  return ret

def createrowdatekey(name, datetext, daysyear, daysmonth, daysday, ageindays): # pylint: disable=too-many-arguments
  """ maken van een regel met een sorteersleutel er bij """
  row = {}
  sortkey = f'{daysyear}-{daysmonth:02d}-{daysday:02d}'
  row['name'] = name
  row['date'] = datetext
  row['month'] = daysmonth
  row['day'] = daysday
  row['sortkey'] = sortkey
  row['ageindays'] = ageindays
  return row

def nextbirthday(month, day):
  """ bepaal de volgende verjaardag """
  today = date.today()
  todaymonth = today.month
  todayday = today.day
  if todaymonth > month or (todaymonth == month and todayday > day):
    nextbirthdayyear = today.year + 1
  else:
    nextbirthdayyear = today.year
  return date(nextbirthdayyear, month, day)

def showbirthday(month, day):
  """ bepaal of de gegevens getoond moeten worden """
  daysfromnow = (nextbirthday(month, day) - date.today()).days
  return 0 <= daysfromnow < SHOWDAYS

def showdaysage(ageindays):
  """ bepaal of de datum op basis van aantal dagen getoond moet worden """
  if ageindays == '-':
    return False
  if int(ageindays) % 1000 => (1000 - SHOWDAYS):
    return True
  return False

def processconnections(connections):
  """ verwerk de contacten """
  connectionslist = []
  for person in connections:
    names = person.get('names')
    if names is None:
      name = 'No Name'
    else:
      name = names[0].get('displayName')

    birthdays = person.get('birthdays')
    if not birthdays is None:
      birthday = birthdays[0].get('date')
      if not birthday is None:
        connectionslist.extend(createrowdate(name, birthday))
    events = person.get('events')
    if not events is None:
      for event in events:
        longname = name + ' (' + event.get('type', '?') + ')'
        eventdate = event.get('date')
        if not eventdate is None:
          connectionslist.extend(createrowdate(longname, eventdate))
  return connectionslist

@app.route('/verjaardagskalender/login')
def login():
  """ login op basis van oauth """
  session['returnpath'] = '/verjaardagskalender'
  redirect_uri = url_for('authorize', _external=True, _scheme='https')
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
  app.run(host='0.0.0.0', port=8084, debug=False)
