# To change this template, choose Tools | Templates
# and open the template in the editor.

from rcore.error import InvalidFilterParametersError
import collections
import datetime


class RichList(object):
    def __init__(self, items=[], cnt=None): # maybe 0 is better for cnt ?
        self.items = items[:]
        self.count = cnt

    def __iter__(self):
        return self.items.__iter__()

    def __len__(self):
        return len(self.items)

    def __getitem__(self, item):
        return self.items[item]

    def sort(self, field, reverse=False):
        self.items.sort(
            cmp=lambda x, y: cmp(getattr(x, field), getattr(y, field)),
            reverse=reverse
        )

    def map(self, func):
        return RichList(map(func, self.items), self.count)


class Condition(object):
    signs = {
        "!": dict(text="!=", singleTest=lambda var, val: var != val),
        "<": dict(text="<", singleTest=lambda var, val: var < val),
        ">": dict(text=">", singleTest=lambda var, val: var > val),
        "=": dict(text="=", singleTest=lambda var, val: var == val),
        ">=": dict(text=">=", singleTest=lambda var, val: var >= val),
        "<=": dict(text="<=", singleTest=lambda var, val: var <= val),
    }

    def __init__(self, condType, value, valueType=None):
        self.setType(condType)
        self.setValue(value, valueType)

    def __str__(self):
        return self.signs[self.type]["text"] + " " + str(self.value)

    def setType(self, t):
        t = str(t)
        if t not in self.signs.keys():
            raise InvalidFilterParametersError("Unknown comparing type")
        self.type = t

    def setValue(self, v, valType=None):
        if hasattr(v, '__iter__') and not isinstance(v, basestring):
            v = set(v)
            v = set(self.validateType(i, valType) for i in v)
        else:
            v = self.validateType(v, valType)

        self.value = v

    def validateType(self, v, valType):
        if valType and type(v) != valType: # what about parent classes?
            try:
                v = valType(v)
            except Exception, e:
                raise InvalidFilterParametersError("Type mismatch: " + repr(e))
        return v

    def test(self, var):
        return self.signs[self.type]["singleTest"](var, self.value)

    @classmethod
    def fromMixed(cls, v, valueType=None):
        if type(v) == list and len(v) and v[0] in cls.signs:
            condType = v[0]
            value = v[1]
        else:
            condType = '='
            value = v
        return cls(condType, value, valueType)

    @staticmethod
    def typed(type):
        '''
        Returns constructor for Conditions with predefined type
        '''
        return TypedCondition(type)


class TypedCondition(Condition):
    def __init__(self, type):
        self.type = type

    def __call__(self, condType, value):
        return Condition(condType, value, self.type)


class Filter(dict):
    defaultClass = None

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        if "fields" in self.__class__.__dict__:
            wrongKeys = set(self.keys()) - set(self.fields)
            for k in wrongKeys:
                del self[k]

    def setParam(self, name, value):
        self[name] = value

    def convertCTime(self):
        if "createdFrom" in self or "createdTo" in self:
            self["period"] = {}
        if "createdFrom" in self:
            self["period"]["from"] = self["createdFrom"]
            del self["createdFrom"]
        if "createdTo" in self:
            self["period"]["to"] = self["createdTo"]
            del self["createdTo"]
        if "period" in self:
            if ("from" in self["period"] and not isinstance(self["period"]["from"], datetime.datetime)) \
                or ("to" in self["period"] and not isinstance(self["period"]["to"], datetime.datetime)):
                raise InvalidFilterParametersError("Invalid period")


class Criteria(object):
    defaultFilter = Filter

    def __init__(self):
        self._filter = self.defaultFilter()
        self._offset = None
        self._limit = None
        self._sorting = dict()
        self._needCount = False
        self._distinct = False

    @classmethod
    def fromDict(cls, d, filterClass=None, renameKeys=None):
        filterClass = filterClass or cls.defaultFilter
        c = cls()
        c._initFromDict(d, filterClass, renameKeys)
        return c

    def _initFromDict(self, d, filterClass=Filter, renameKeys=None):
        if d:
            offset = d.get("offset", None)
            if offset:
                self.setOffset(offset[0])
                self.setLimit(offset[1] if len(offset) > 1 else None)

            sort = d.get("sort", None)
            if sort:
                for field, direction in sort:
                    self.addSorting(field.lower(), direction.upper())

            self._needCount = bool(d.get("needcount", False))

            if "filter" in d and isinstance(d["filter"], dict):
                self._filter = filterClass(
                    dict(
                        (renameKeys.get(k, k), v) for k, v in d["filter"].iteritems()
                    ) if renameKeys else d["filter"].copy()
                )
            else:
                self._filter = filterClass()
        else:
            self._filter = filterClass()


    def setParams(self, params):
        if hasattr(self._filter, "setParams") and isinstance(self._filter, collections.Callable):
            self._filter.setParams(params)
        else:
            self._filter = Filter(params)

    def setOffset(self, value=None):
        self._offset = int(value) if value else None

    def offset(self):
        return self._offset

    def setLimit(self, value=None):
        self._limit = int(value) if value else None

    def limit(self):
        return self._limit

    def setDistinct(self, distinct):
        self._distinct = bool(int(distinct))

    def isDistinct(self):
        return self._distinct

    def addSorting(self, field, direction="ASC"):
        direction = direction.upper()
        self._sorting[field] = direction if direction == "ASC" else "DESC"

    def sorting(self):
        return self._sorting

    def needCount(self):
        return self._needCount

    def getList(self, classObj=None):
        return self._filter.getList(classObj)

    def __setitem__(self, name, value):
        self._filter.setParam(name, value)


# Base class for all RPC services
class RPCService(object):
    pass
    