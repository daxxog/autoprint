# AutoPrint
# alpha 0.1
# by daXXog

import imaplib, email, string, base64, ConfigParser, httplib, json, logging, mimetypes, optparse, os, sys, time, urllib, urllib2, mimetools 

#google account login info
username = 'username'
password = 'password'

# from http://yuji.wordpress.com/2011/06/22/python-imaplib-imap-example-with-gmail/
# slightly modified by daXXog

#Code samples assume the following definitions:
CRLF = '\r\n'
BOUNDARY = mimetools.choose_boundary()

# The following are used for authentication functions.
FOLLOWUP_HOST = 'www.google.com/cloudprint'
FOLLOWUP_URI = 'select%2Fgaiaauth'
GAIA_HOST = 'www.google.com'
LOGIN_URI = '/accounts/ServiceLoginAuth'
LOGIN_URL = 'https://www.google.com/accounts/ClientLogin'
SERVICE = 'cloudprint'
logger = logging.getLogger('google.cloudprint')

# The following are used for general backend access.
CLOUDPRINT_URL = 'http://www.google.com/cloudprint'
# CLIENT_NAME should be some string identifier for the client you are writing.
CLIENT_NAME = 'Cloud Print API Client'
#_______________________________________________________________

# from http://yuji.wordpress.com/2011/06/22/python-imaplib-imap-example-with-gmail/
# slightly modified by daXXog
def get_first_text_block(email_message_instance):
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload()
            else:
                return 0 #stops "NoneType"
    elif maintype == 'text':
        return email_message_instance.get_payload()
    else:
        return 0 #stops "NoneType"
#_______________________________________________________________

# from https://developers.google.com/cloud-print/docs/pythonCode
# slightly modified by daXXog
def GetUrl(url, tokens, data=None, cookies=False, anonymous=False):
  """Get URL, with GET or POST depending data, adds Authorization header.

  Args:
    url: Url to access.
    tokens: dictionary of authentication tokens for specific user.
    data: If a POST request, data to be sent with the request.
    cookies: boolean, True = send authentication tokens in cookie headers.
    anonymous: boolean, True = do not send login credentials.
  Returns:
    String: response to the HTTP request.
  """
  request = urllib2.Request(url)
  if not anonymous:
    if cookies:
      logger.debug('Adding authentication credentials to cookie header')
      request.add_header('Cookie', 'SID=%s; HSID=%s; SSID=%s' % (
          tokens['SID'], tokens['HSID'], tokens['SSID']))
    else:  # Don't add Auth headers when using Cookie header with auth tokens.   
      request.add_header('Authorization', 'GoogleLogin auth=%s' % tokens['Auth'])
  request.add_header('X-CloudPrint-Proxy', 'api-prober')
  if data:
    request.add_data(data)
    request.add_header('Content-Length', str(len(data)))
    request.add_header('Content-Type', 'multipart/form-data;boundary=%s' % BOUNDARY)

  # In case the gateway is not responding, we'll retry.
  retry_count = 0
  while retry_count < 5:
    try:
      result = urllib2.urlopen(request).read()
      return result
    except urllib2.HTTPError, e:
      # We see this error if the site goes down. We need to pause and retry.
      err_msg = 'Error accessing %s\n%s' % (url, e)
      logger.error(err_msg)
      logger.info('Pausing %d seconds', 60)
      time.sleep(60)
      retry_count += 1
      if retry_count == 5:
        return err_msg
#_______________________________________________________________

# MultiPart Form Data
# from https://developers.google.com/cloud-print/docs/pythonCode
def EncodeMultiPart(fields, files, file_type='application/xml'):
    """Encodes list of parameters and files for HTTP multipart format.

    Args:
      fields: list of tuples containing name and value of parameters.
      files: list of tuples containing param name, filename, and file contents.
      file_type: string if file type different than application/xml.
    Returns:
      A string to be sent as data for the HTTP post request.
    """
    lines = []
    for (key, value) in fields:
      lines.append('--' + BOUNDARY)
      lines.append('Content-Disposition: form-data; name="%s"' % key)
      lines.append('')  # blank line
      lines.append(value)
    for (key, filename, value) in files:
      lines.append('--' + BOUNDARY)
      lines.append(
          'Content-Disposition: form-data; name="%s"; filename="%s"'
          % (key, filename))
      lines.append('Content-Type: %s' % file_type)
      lines.append('')  # blank line
      lines.append(value)
    lines.append('--' + BOUNDARY + '--')
    lines.append('')  # blank line
    return CRLF.join(lines)
#_______________________________________________________________

# from https://developers.google.com/cloud-print/docs/pythonCode
def GetCookie(cookie_key, cookie_string):
    """Extract the cookie value from a set-cookie string.

    Args:
      cookie_key: string, cookie identifier.
      cookie_string: string, from a set-cookie command.
    Returns:
      string, value of cookie.
    """
    logger.debug('Getting cookie from %s', cookie_string)
    id_string = cookie_key + '='
    cookie_crumbs = cookie_string.split(';')
    for c in cookie_crumbs:
      if id_string in c:
        cookie = c.split(id_string)
        return cookie[1]
    return None
#_______________________________________________________________

# from https://developers.google.com/cloud-print/docs/pythonCode
# slightly modified by daXXog
def SubmitJob(printerid, jobsrc):
  """Submit a job to printerid with content of dataUrl.

  Args:
    printerid: string, the printer id to submit the job to.
    jobtype: string, must match the dictionary keys in content and content_type.
    jobsrc: string, points to source for job. Could be a pathname or id string.
  Returns:
    boolean: True = submitted, False = errors."""
    
  jobname, jobtype = os.path.splitext(jobsrc)
  jobtype = jobtype[1:]
  fdata = ReadFile(jobsrc)
  
  # Make the title unique for each job, since the printer by default will name
  # the print job file the same as the title.
  
  datehour = time.strftime('%b%d%H%M', time.localtime())
  title = '%s%s' % (datehour, jobsrc)
  """The following dictionaries expect a certain kind of data in jobsrc, depending on jobtype:
  jobtype               jobsrc
  ======================================
  pdf                     pathname to the pdf file
  png                    pathname to the png file
  jpeg                   pathname to the jpeg file
  =======================================    
  """
  content = {'txt': jobsrc,
             'html': jobsrc,
            }
  content_type = {'txt': 'text/plain',
                  'html': 'text/html',
                 }
  headers = [('printerid', printerid),
             ('title', title),
             ('content', content[jobtype]),
             ('contentType', content_type[jobtype])]
  files = [('capabilities', 'capabilities', '{"capabilities":[]}')]
  if jobtype in ['txt', 'html']:
    files.append(('content', jobsrc, fdata))
    edata = EncodeMultiPart(headers, files, file_type=content_type[jobtype])
  else:
    edata = EncodeMultiPart(headers, files)

  response = GetUrl('%s/submit' % CLOUDPRINT_URL, tokens, data=edata)
  status = Validate(response)
  if not status:
    error_msg = GetMessage(response)
    print 'Print job %s failed with %s', jobtype, error_msg
    #logger.error('Print job %s failed with %s', jobtype, error_msg)

  return status
#_______________________________________________________________

# Utility Functions
# from https://developers.google.com/cloud-print/docs/pythonCode
def ConvertJson(json_str):    
  """Convert json string to a python object.

  Args:
    json_str: string, json response.
  Returns:
    dictionary of deserialized json string.
  """
  j = {}
  try:
    j = json.loads(json_str)
    j['json'] = True
  except ValueError, e:
    # This means the format from json_str is probably bad.
    logger.error('Error parsing json string %s\n%s', json_str, e)
    j['json'] = False
    j['error'] = e

  return j

def GetKeyValue(line, sep=':'):
    """Return value from a key value pair string.

    Args:
      line: string containing key value pair.
      sep: separator of key and value.
    Returns:
      string: value from key value string.
    """
    s = line.split(sep)
    return StripPunc(s[1])

def StripPunc(s):
  """Strip puncuation from string, except for - sign.

  Args:
    s: string.
  Returns:
    string with puncuation removed.
  """
  for c in string.punctuation:
    if c == '-':  # Could be negative number, so don't remove '-'.
      continue
    else:
      s = s.replace(c, '')
  return s.strip()

def Validate(response):
  """Determine if JSON response indicated success."""
  if response.find('"success": true') > 0:
    return True
  else:
    return False

def GetMessage(response):
  """Extract the API message from a Cloud Print API json response.

  Args:
    response: json response from API request.
  Returns:
    string: message content in json response.
  """
  lines = response.split('\n')
  for line in lines:
    if '"message":' in line:
      msg = line.split(':')
      return msg[1]

  return None

def ReadFile(pathname):
  """Read contents of a file and return content.

  Args:
    pathname: string, (path)name of file.
  Returns:
    string: contents of file.
  """
  try:
    f = open(pathname, 'rb')
    try:
      s = f.read()
    except IOError, e:
      logger('Error reading %s\n%s', pathname, e)
    finally:
      f.close()
      return s
  except IOError, e:
    logger.error('Error opening %s\n%s', pathname, e)
    return None

def WriteFile(file_name, data):
  """Write contents of data to a file_name.

  Args:
    file_name: string, (path)name of file.
    data: string, contents to write to file.
  Returns:
    boolean: True = success, False = errors.
  """
  status = True

  try:
    f = open(file_name, 'wb')
    try:
      f.write(data)
    except IOError, e:
      logger.error('Error writing %s\n%s', file_name, e)
      status = False
    finally:
      f.close()
  except IOError, e:
    logger.error('Error opening %s\n%s', file_name, e)
    status = False

  return status

def Base64Encode(pathname):
  """Convert a file to a base64 encoded file.

  Args:
    pathname: path name of file to base64 encode..
  Returns:
    string, name of base64 encoded file.
  For more info on data urls, see:
    http://en.wikipedia.org/wiki/Data_URI_scheme
  """
  b64_pathname = pathname + '.b64'
  file_type = mimetypes.guess_type(pathname)[0] or 'application/octet-stream'
  data = ReadFile(pathname)

  # Convert binary data to base64 encoded data.
  header = 'data:%s;base64,' % file_type
  b64data = header + base64.b64encode(data)

  if WriteFile(b64_pathname, b64data):
    return b64_pathname
  else:
    return None
#_______________________________________________________________

# from https://developers.google.com/cloud-print/docs/pythonCode
def GetPrinters(proxy=None):
  """Get a list of all printers, including name, id, and proxy.

  Args:
    proxy: name of proxy to filter by.
  Returns:
    dictionary, keys = printer id, values = printer name, and proxy.
  """
  printers = {}
  values = {}
  tokenss = ['"id"', '"name"', '"proxy"']
  for t in tokenss:
    values[t] = ''

  if proxy:
    response = GetUrl('%s/list?proxy=%s' % (CLOUDPRINT_URL, proxy), tokens)
  else:
    response = GetUrl('%s/search' % CLOUDPRINT_URL, tokens)

  printers = ConvertJson(response)['printers']

  return printers
#_______________________________________________________________

# from https://developers.google.com/cloud-print/docs/pythonCode
def GaiaLogin(email, password):
    """Login to gaia using HTTP post to the gaia login page.

    Args:
      email: string,
      password: string
    Returns:
      dictionary of authentication tokens.
    """
    tokens = {}
    cookie_keys = ['SID', 'LSID', 'HSID', 'SSID']
    email = email.replace('+', '%2B')
    # Needs to be some random string.
    galx_cookie = base64.b64encode('%s%s' % (email, time.time()))

    # Simulate submitting a gaia login form.
    form = ('ltmpl=login&fpui=1&rm=hide&hl=en-US&alwf=true'
            '&continue=https%%3A%%2F%%2F%s%%2F%s'
            '&followup=https%%3A%%2F%%2F%s%%2F%s'
            '&service=%s&Email=%s&Passwd=%s&GALX=%s' % (FOLLOWUP_HOST,
            FOLLOWUP_URI, FOLLOWUP_HOST, FOLLOWUP_URI, SERVICE, email,
            password, galx_cookie))
    login = httplib.HTTPS(GAIA_HOST, 443)
    login.putrequest('POST', LOGIN_URI)
    login.putheader('Host', GAIA_HOST)
    login.putheader('content-type', 'application/x-www-form-urlencoded')
    login.putheader('content-length', str(len(form)))
    login.putheader('Cookie', 'GALX=%s' % galx_cookie)
    logger.debug('Sent POST content: %s', form)
    login.endheaders()
    logger.info('HTTP POST to https://%s%s', GAIA_HOST, LOGIN_URI)
    login.send(form)

    (errcode, errmsg, headers) = login.getreply()
    login_output = login.getfile()
    login_output.close()
    login.close()
    logger.info('Login complete.')

    if errcode != 302:
      logger.error('Gaia HTTP post returned %d, expected 302', errcode)
      logger.error('Message: %s', errmsg)

    for line in str(headers).split('\r\n'):
      if not line: continue
      (name, content) = line.split(':', 1)
      if name.lower() == 'set-cookie':
        for k in cookie_keys:
          if content.strip().startswith(k):
            tokens[k] = GetCookie(k, content)

    if not tokens:
      logger.error('No cookies received, check post parameters.')
      return None
    else:
      logger.debug('Received the following authorization tokens.')
      for t in tokens:
        logger.debug(t)
      return tokens
#_______________________________________________________________

# from https://developers.google.com/cloud-print/docs/pythonCode
def GetAuthTokens(email, password):
    """Assign login credentials from GAIA accounts service.

    Args:
      email: Email address of the Google account to use.
      password: Cleartext password of the email account.
    Returns:
      dictionary containing Auth token.
    """
    # First get GAIA login credentials using our GaiaLogin method.
    tokens = GaiaLogin(email, password)

    # We still need to get the Auth token.    
    params = {'accountType': 'GOOGLE',
              'Email': email,
              'Passwd': password,
              'service': SERVICE,
              'source': CLIENT_NAME}
    stream = urllib.urlopen(LOGIN_URL, urllib.urlencode(params))

    for line in stream:
      if line.strip().startswith('Auth='):
        tokens['Auth'] = line.strip().replace('Auth=', '')
    return tokens
#_______________________________________________________________







# connect via IMAP
mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login(username, password)

# connect to google
tokens = GetAuthTokens(username, password);
printers = GetPrinters();
if printers[0]['name'] == 'Save to Google Docs':
  useprinter = 1
else:
  useprinter = 0
  
print 'Printing on ' + printers[useprinter]['name']

mail.list()
mail.select('inbox') # connect to inbox
    
result, data = mail.search(None, 'ALL')
    
ids = data[0] # data is a list
id_list = ids.split() # ids is a space separated string

numMessages = len(id_list) # find out how many messages we need to parse

for i in reversed(range(numMessages)):
    message = ""
    

    latest_email_id = id_list[i] # get the latest email
    
    result, data = mail.fetch(latest_email_id, '(RFC822)') # fetch the email body (RFC822) for the given ID
    
    raw_email = data[0][1] # here's the body, which is raw text of the whole email
    
    mailme = email.message_from_string(raw_email)
    
    # parse the plain text (if any)
    parser = email.parser.Parser()
    messagepareser = parser.parsestr(raw_email)
    plaintext = get_first_text_block(messagepareser)
    
    if plaintext == 0:
        breaker = '<br>'
        extension = 'html'
        fancyheader = '<b>'
        fancyfooter = '</b><hr>'
        plaintext = ''
    else:
        breaker = '\n'
        fancyheader = ''
        fancyfooter = '\n===================================================================='
        extension = 'txt'

    message += fancyheader + 'From: ' + mailme['From'] + breaker
    message += 'Subject: ' + mailme['Subject'] + breaker
    message += 'Date: ' + mailme['Date'] + fancyfooter + breaker + breaker
    message += plaintext + breaker

    # parse the html (if any)
    for part in mailme.walk():
        if part.is_multipart():
            continue
        if part.get_content_type() == 'text/html' or part.get_content_type() == 'text/plain':
            body = '\n' + part.get_payload() + '\n'
        dtypes = part.get_params(None, 'Content-Disposition')
        if not dtypes:
            if part.get_content_type() == 'text/plain':
                continue
            ctypes = part.get_params()
            if not ctypes:
                continue
            for key,val in ctypes:
                if key.lower() == 'name':
                    #message += 'Attachment: ' + val + '<br>'
                    break
            else:
                continue
        else:
            attachment,filename = None,None
            for key,val in dtypes:
                key = key.lower()
                if key == 'filename':
                    filename = val
                if key == 'attachment':
                    attachment = 1
            if not attachment:
                continue
            #message += 'Attachment: ' + filename + '<br>'
        if body:
            message += body + '\n'
    
    # save the text or html
    filename = str(i) + '.' + extension
    save = open(filename, 'w')
    save.write(message)
    save.close()

    #upload to cloud print
    SubmitJob(printers[useprinter]['id'], filename)
    
    print 'message #'+str(i)+' saved / printed'
