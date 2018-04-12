from collections import defaultdict
from csv import DictReader
from datetime import datetime
from etl_tasks import DBAccessTask
from param_val import StrParam, IntParam
from sqlalchemy import func, MetaData, Table, Column
from sqlalchemy.types import String

import logging
import sqlalchemy as sqla

log = logging.getLogger(__name__)

class LoadCSV(DBAccessTask):
    tablename = StrParam()
    csvname = StrParam()
    rowcount = IntParam(default=1)

    def complete(self) -> bool:
        #return False
        db = self._dbtarget().engine
        table = Table(self.tablename, sqla.MetaData())
        if not table.exists(bind=db):
            log.info('no such table: %s', self.tablename)
            return False
        with self.connection() as q:
            actual = q.scalar('select records from cdm_status where status = \'%s\'' % self.tablename)
            actual = 0 if actual == None else actual
            log.info('table %s has %d rows', self.tablename, actual)
            return actual >= self.rowcount  # type: ignore  # sqla

    def run(self) -> None:
        self.load()
        self.setStatus()

    def load(self) -> None:
        def sz(l, chunk=16):
            return max(chunk, chunk * ((l + chunk - 1) // chunk))

        db = self._dbtarget().engine
        schema = MetaData()
        l = list()

        with open(self.csvname) as fin:
            dr = DictReader(fin)

            mcl = defaultdict(int)
            for row in dr:
                l.append(row)
                for col in dr.fieldnames:
                    mcl[col] = sz(max(mcl[col], len(row[col])))

            columns = ([Column(n, String(mcl[n])) for n in dr.fieldnames])
            table = Table(self.tablename, schema, *columns)
            if table.exists(bind=db):
                table.drop(db)
            table.create(db)

            db.execute(table.insert(), l)

    def setStatus(self) -> None:
        statusTable = Table("cdm_status", MetaData(), Column('STATUS'), Column('LAST_UPDATE'), Column('RECORDS'))

        db = self._dbtarget().engine

        with self.connection() as q:
            actual = q.scalar(sqla.select([func.count()]).select_from(self.tablename))

        db.execute(statusTable.insert(), [{'STATUS':self.tablename, 'LAST_UPDATE':datetime.now(), 'RECORDS':actual}])