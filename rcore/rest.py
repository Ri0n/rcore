# Copyright (c) 2013, Il'inykh Sergey
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the <organization> nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL IL'INYKH SERGEY BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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

