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
        