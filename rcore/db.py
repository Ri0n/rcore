from sqlalchemy import select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FromClause, asc, desc
from sqlalchemy.sql import table, column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import query

from rcore.rpctools import Filter, Criteria, RichList
from rcore import getContext

Base = declarative_base()


class Values(FromClause):
    def __init__(self, *args):
        self.list = args
        assert len(self.list)

    def _populate_column_collection(self):
        self._columns.update([("column%d" % i, column("column%d" % i))
                              for i in xrange(1, len(self.list[0]) + 1)])


@compiles(Values)
def compile_values(element, compiler, asfrom=False, **kw):
    v = "VALUES %s" % ", ".join(
        "(%s)" % ", ".join(repr(elem) for elem in tup)
        for tup in element.list
    )
    if asfrom:
        v = "(%s)" % v
    return v


class SQLAFilter(Filter):
    def getQuery(self, classObj):
        return getContext().db.query(classObj).filer_by(**self)

    def addCTimeConstraints(self, query, classObj):
        if "period" in self:
            if "from" in self["period"]:
                query = query.filter(getattr(classObj, "ctime") >= self["period"]["from"])
            if "to" in self["period"]:
                query = query.filter(getattr(classObj, "ctime") <= self["period"]["to"])
        return query


class SQLACriteria(Criteria):
    defaultFilter = SQLAFilter

    def getList(self, classObj=None):
        cls = classObj or self._filter.defaultClass
        q = self._filter.getQuery(cls)
        cnt = self._needCount and q.count() or None
        if self._offset:
            q = q.offset(self._offset)
        if self._limit:
            q = q.limit(self._limit)
        if self._distinct:
            q = q.distinct()
        if len(self._sorting):
            q = q.order_by(*[(d == 'ASK' and asc or desc)(getattr(cls, k)) for k, d in self._sorting.iteritems()])
        return RichList(q.all(), cnt)


if __name__ == '__main__':
    t1 = table('t1', column('a'), column('b'))
    t2 = Values((1, 0.5), (2, -0.5)).alias('weights')
    print select([t1, t2]).select_from(t1.join(t2, t1.c.a == t2.c.column1))
