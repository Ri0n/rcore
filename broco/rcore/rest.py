import urllib
import json

from twisted.web.client import getPage
from twisted.python import log

class Request(object):
    def __init__(self, baseUrl):
        self.baseUrl = str(baseUrl)
        self.baseUrl = self.baseUrl + ("/" if self.baseUrl[-1] != '/' else '')
        self.vars = {}

    def addVar(self, name, value):
        self.vars[name] = json.dumps(value)
        return self

    def send(self):
        payload = urllib.urlencode(self.vars)
        #log.msg("transmitted post data: " + str(payload))
        d = getPage(self.baseUrl, method='POST', postdata=payload, 
                    headers={"Content-type": "application/x-www-form-urlencoded; "
                             "charset=utf-8"})
        d.addCallback(self._parseResponse)
        return d

    def _parseResponse(self, content):
        result = dict(failed=False, success=True)
        if content in result.keys():
            return result[content]
        log.msg("REST service returned buggy response:" + str(content))
        return False

