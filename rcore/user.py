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

'''
Created on 18.10.2010

@author: rion
'''
from rcore.error import InvalidParametersError

class User(object):
    '''
    just a user
    '''

    def __init__(self, login, password, name):
        self.login = login
        self.password = password
        self.name = name
        self.role = 0
        
    def addRole(self, roleType):
        from rcore import role
        if isinstance(roleType, basestring):
            roleType = getattr(role, roleType)
        if roleType not in role.roles.keys():
            raise InvalidParametersError("Invalid role: " + str(roleType))
        self.role |= roleType
        
    def hasRole(self, roleType):
        return self.role & roleType
        
    def auth(self, password, user = None):
        return password == self.password and (True if user == None else user == self.login)
        
    @classmethod
    def fromConfig(cls, conf):
        u = cls(conf.user, conf.password, conf.name)
        roles = conf._get("role", "").split("|")
        for r in roles:
            if r:
                u.addRole(r)
        return u
