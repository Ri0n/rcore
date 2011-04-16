from rcore.context import getContext
from rcore.error import AccessDenied
from rcore import getCore

GUEST   = 1
STATISTICIAN = 2
OPERATOR  = 4
MANAGER = GUEST | STATISTICIAN | OPERATOR

roles = dict((globals()[t], t) for t in ["GUEST", "STATISTICIAN", "OPERATOR", "MANAGER"])

def role(roleType):
    def roleCheckerDecorator(rpc_method):
        def roleChecker(*args, **kwargs):
            if not getCore().getUser(getContext().initiator).hasRole(roleType):
                raise AccessDenied("User '%s' does not have %s access" % (str(getContext().initiator), roles[roleType]))
            return rpc_method(*args, **kwargs)
        return roleChecker
    return roleCheckerDecorator
