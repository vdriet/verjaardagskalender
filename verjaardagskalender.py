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


def lees_json(url: str, token: str) -> dict:
  """
  Fetches and returns JSON data from a given URL using an HTTP GET request. The request includes
  custom headers for content type and authorization. Handles connection errors gracefully by
  returning an error dictionary.

  Parameters:
      url (str): The URL to which the GET request will be sent.
      token (str): The authorization token to include in the request headers.

  Returns:
      dict: A dictionary containing either the JSON response data or an error message if
            the connection fails.

  Raises:
      requests.ConnectionError: If there is a problem with the network connection during
                                the request process.
  """
  try:
    headers = {'Content-Type': 'application/json',
               'Authorization': f'Bearer {token}'}
    req = requests.get(url, headers=headers, verify=False, timeout=6, allow_redirects=False)
    return req.json()
  except requests.ConnectionError:
    return {'error': 'failed to connect'}


def istokenvalid() -> bool:
  """
  Determines the validity of a token based on its expiration time.

  This function checks whether a token's expiration time, stored in the current
  session, has passed. If the expiration time is missing or the time has already
  expired, the token is deemed invalid.

  Returns:
      bool: True if the token is valid, False otherwise.
  """
  exp = session.get('exp')
  if exp is None or exp - time() < 0:
    return False
  return True


@app.route('/verjaardagskalender', methods=['GET'])
def hoofdpagina() -> str:
  """
  Handles the route for the birthday calendar homepage. Verifies if the access token is
  valid and either displays the calendar page or redirects to the index page.


  Returns
  -------
  Response
      The rendered 'kalender' page if the access token is valid; otherwise, the
      rendered 'index.html' page with user and token information from the session.
  """
  user = session.get('user')
  token = session.get('access_token')
  valid = istokenvalid()
  if valid:
    return kalender()
  return render_template('index.html', user=user, token=token, valid=valid)


def kalender() -> str:
  """
  Retrieves contact data and generates a birthday calendar.

  This function checks for a valid authentication token. If the token is invalid,
  it redirects to the authorization page. Otherwise, it fetches contacts data,
  processes it to extract birthday and event information, and renders the calendar
  template with the processed data.

  Returns
  -------
  Response
      Either a redirect to the authorization page if the token is invalid,
      or the rendered calendar template with the processed contact data.
  """
  if not istokenvalid():
    redirect_uri = url_for('authorize', _external=True, _scheme='https')
    session['returnpath'] = '/verjaardagskalender'
    return oauth.google.authorize_redirect(redirect_uri)
  contacten = haalcontacten()
  data = verwerkcontacten(contacten)
  return render_template('kalender.html', data=data)


def haalcontacten() -> list:
  """
  Fetches the list of contacts for the user from the Google People API.

  This function retrieves a list of user connections, including details
  such as names, birthdays, and events. It fetches all pages of contact
  data using the `nextPageToken` provided by the API. Access to the API
  is authenticated using an access token stored in the session. The
  retrieved data is consolidated into a single list and returned.

  Returns
  -------
  list
      A list of contacts retrieved from the Google People API. Each contact
      is represented as a dictionary containing details such as names,
      birthdays, and events.
  """
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


def toonleeftijdindagen(leeftijdindagen: int) -> bool:
  """
  Check if the given age in days falls within a certain threshold condition.

  The function evaluates if the number of days, when taken as a modulus of
  1000, is equal to zero or if it falls within the last part of a 1000-day
  cycle defined by the SHOWDAYS constant. If so, it returns True, otherwise
  it returns False.

  Parameters:
      leeftijdindagen (int): The age in days to be evaluated.

  Returns:
      bool: True if the conditions are met, False otherwise.
  """
  dagenvan1000tal = int(leeftijdindagen) % 1000
  if dagenvan1000tal == 0 or dagenvan1000tal > (1000 - SHOWDAYS):
    return True
  return False


def bepaalnaam(persoon: dict) -> str:
  """
  Determines the display name of a person based on the provided person data.
  The function checks if the 'names' key exists in the given dictionary. If it
  does not exist, it will return 'No Name'. If it exists, it attempts to retrieve
  the first name's display name, defaulting to 'No Name' if it is not present.

  Arguments:
      persoon (dict): A dictionary containing person information. Expected to
      have a key 'names', which is a list of dictionaries, each containing a
      key 'displayName'.

  Returns:
      str: The display name of the person, or 'No Name' if unavailable.
  """
  names = persoon.get('names')
  if names is None:
    return 'No Name'
  return names[0].get('displayName', 'No Name')


def maaklegekalender() -> dict:
  """
  Creates an empty calendar structure for a year.

  This function generates a dictionary structure representing an empty
  calendar for a year. Each key in the outer dictionary corresponds to a month
  number (1 through 12). Each month contains another dictionary where the keys
  correspond to day numbers and the values are initialized to empty dictionaries.

  Returns:
      dict: A dictionary representing an empty calendar where each month contains
      a dictionary of days initialized to empty dictionaries.
  """
  legekalender = {}
  for maandnr in range(1, 13):
    maandlengte = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    maand = {}
    for dagnr in range(1, maandlengte[maandnr] + 1):
      maand[dagnr] = {}
    legekalender[maandnr] = maand
  return legekalender


def voegdatumaanlijsttoe(contactenlijst: dict, naam: str, datum: dict) -> None:
  """
  Adds a date to a list of contacts, associating it with the specified name.

  This function processes the given date to extract the year, month, and day.
  It then uses the month and day to locate an entry in the provided contact
  list and associates the supplied name with the formatted year. If the year
  is not provided, a default placeholder is used.

  Parameters:
      contactenlijst (dict): A dictionary representing a calendar-like structure
          where months are keys pointing to nested dictionaries containing days
          and their associated events.
      naam (str): The name to associate with the event on the specified date.
      datum (dict): A dictionary containing the date components with potential
          keys 'year', 'month', and 'day'. 'year' is optional.

  Returns:
      None
  """
  jaar = datum.get('year', '????')
  maand = datum.get('month')
  dag = datum.get('day')
  eventementenopdag = contactenlijst.get(maand).get(dag)
  eventementenopdag[naam] = f'({jaar})'


def voegfeestdagtoeaanlijst(contactenlijst: dict, naam: str, datum: dict) -> None:
  """
  Adds a celebration day to a given contact list if specific conditions are met.

  This function computes how many days have passed since the provided date and determines
  if a particular milestone in days (like every 1000 days) should be celebrated. If the
  function calculates that a celebration is due or upcoming, it adds an entry in the
  contact list for the relevant day. The contact list structure assumes storage organized
  by month and day.

  Parameters:
      contactenlijst (dict): A dictionary representing the contact list organized by months
          (as keys) containing sub-dictionaries of days (as keys).
      naam (str): The name or identifier of the individual or event to associate with the
          celebration.
      datum (dict): A dictionary containing the keys 'year', 'month', and 'day' which specify
          the date of an event or someone’s birthdate.
  """
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


def verwerkcontacten(contacten: list) -> list:
  """
  Processes a list of contacts to generate a list of calendar events and holidays.

  For each contact, their birthdays and events are analyzed. Dates are added to the
  list of calendar holidays along with corresponding labels consisting of the contact
  name and event type where appropriate. The function ensures that both the calendar
  list and the holiday-specific list are updated with the relevant information.

  Args:
      contacten (list): A list of dictionaries representing contacts. Each contact
          dictionary may contain 'birthdays' (list of dictionaries with 'date') and
          'events' (list of dictionaries with 'type' and 'date').

  Returns:
      list: A list of calendar events and holidays with corresponding labels and dates.
  """
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
def login() -> str:
  """
  Handles user login by redirecting them to an OAuth provider for authentication.
  The function determines the appropriate protocol (HTTP or HTTPS) based on the
  host environment and constructs the redirect URI.

  Returns:
      Response: A Flask response redirecting the user to the OAuth provider's
      authorization URL.
  """
  session['returnpath'] = '/verjaardagskalender'
  if 'localhost' in request.host:
    protocol = 'http'
  else:
    protocol = 'https'
  redirect_uri = url_for('authorize', _external=True, _scheme=protocol)
  return oauth.google.authorize_redirect(redirect_uri)


@app.route('/verjaardagskalender/logout')
def logout() -> str:
  """
  Logs out the current user by clearing specific session data and redirects to
  the main verjaardagskalender page.

  Removes the expiration time, user information, and access token from the session
  to effectively log out the current user.

  Returns:
      Response: A redirect response to the verjaardagskalender main page.
  """
  session.pop('exp', None)
  session.pop('user', None)
  session.pop('access_token', None)
  return redirect('/verjaardagskalender')


@app.route('/verjaardagskalender/authorize')
def authorize() -> str:
  """
  Authorize the user by handling OAuth2 authorization using Google's services.
  Stores user session information upon successful authorization and redirects
  to the specified return path.

  Returns
  -------
  Response
      A redirect response object to the URL specified in the user's session
      return path or defaults to '/verjaardagskalender'.

  Raises
  ------
  None
  """
  token = oauth.google.authorize_access_token()
  session['exp'] = token.get('expires_at')
  session['user'] = token['userinfo']
  session['access_token'] = token['access_token']
  returnpath = session.get('returnpath', '/verjaardagskalender')
  return redirect(returnpath)


if __name__ == '__main__':
  waitress.serve(app, host="0.0.0.0", port=8084)
