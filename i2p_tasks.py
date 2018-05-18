"""i2p_tasks -- Luigi CDM task support.
"""
from typing import cast, List, Type

import luigi
from sqlalchemy.engine import RowProxy
from sqlalchemy.exc import DatabaseError

from csv_load import LoadCSV
from etl_tasks import CDMStatusTask, SqlScriptTask
from param_val import IntParam
from script_lib import Script
from sql_syntax import Environment, Params

import csv
import subprocess
import urllib.request
import zipfile

class CDMScriptTask(SqlScriptTask):

    @property
    def variables(self) -> Environment:
        return dict(datamart_id='C4UK', datamart_name='University of Kansas', i2b2_data_schema='BLUEHERONDATA',
                    min_pat_list_date_dd_mon_rrrr='01-Jan-2010', min_visit_date_dd_mon_rrrr='01-Jan-2010',
                    i2b2_meta_schema='BLUEHERONMETADATA', enrollment_months_back='42', network_id='C4',
                    network_name='GPC', i2b2_etl_schema='HERON_ETL_3')


class condition(CDMScriptTask):
    script = Script.condition

    def requires(self) -> List[luigi.Task]:
        return [encounter()]


class death(CDMScriptTask):
    script = Script.death

    def requires(self) -> List[luigi.Task]:
        return [demographic()]


class death_cause(CDMScriptTask):
    script = Script.death_cause

    def requires(self) -> List[luigi.Task]:
        return [pcornet_init()]


class demographic(CDMScriptTask):
    script = Script.demographic

    def requires(self) -> List[luigi.Task]:
        return [loadLanguage(), pcornet_init()]


class diagnosis(CDMScriptTask):
    script = Script.diagnosis

    def requires(self) -> List[luigi.Task]:
        return [encounter()]


class dispensing(CDMScriptTask):
    script = Script.dispensing

    def requires(self) -> List[luigi.Task]:
        return [encounter()]


class encounter(CDMScriptTask):
    script = Script.encounter

    def requires(self) -> List[luigi.Task]:
        return [demographic()]


class enrollment(CDMScriptTask):
    script = Script.enrollment

    def requires(self) -> List[luigi.Task]:
        return [pcornet_init()]


class harvest(CDMScriptTask):
    script = Script.harvest

    def requires(self) -> List[luigi.Task]:
        return [condition(), death(), death_cause(), diagnosis(), dispensing(), enrollment(),
                lab_result_cm(), loadHarvestLocal(), med_admin(), obs_clin(), obs_gen(), pcornet_trial(),
                prescribing(), pro_cm(), procedures(), provider(), vital()]


class lab_result_cm(CDMScriptTask):
    script = Script.lab_result_cm

    def requires(self) -> List[luigi.Task]:
        return [encounter(), loadLabNormal()]


class med_admin(CDMScriptTask):
    script = Script.med_admin

    def requires(self) -> List[luigi.Task]:
        return [pcornet_init()]


class obs_clin(CDMScriptTask):
    script = Script.obs_clin

    def requires(self):
        return [pcornet_init()]


class obs_gen(CDMScriptTask):
    script = Script.obs_gen

    def requires(self):
        return [pcornet_init()]


class CDMPatientGroupTask(CDMScriptTask):
    patient_num_first = IntParam()
    patient_num_last = IntParam()
    patient_num_qty = IntParam(significant=False, default=-1)
    group_num = IntParam(significant=False, default=-1)
    group_qty = IntParam(significant=False, default=-1)

    def run(self) -> None:
        SqlScriptTask.run_bound(self, script_params=dict(
            patient_num_first=self.patient_num_first, patient_num_last=self.patient_num_last))


class _PatientNumGrouped(luigi.WrapperTask):
    group_tasks = cast(List[Type[CDMPatientGroupTask]], [])  # abstract

    def requires(self) -> List[luigi.Task]:
        deps = []  # type: List[luigi.Task]
        for group_task in self.group_tasks:
            survey = patient_chunks_survey()
            deps += [survey]
            results = survey.results()
            if results:
                deps += [
                    group_task(
                        group_num=ntile.chunk_num,
                        group_qty=len(results),
                        patient_num_qty=ntile.patient_num_qty,
                        patient_num_first=ntile.patient_num_first,
                        patient_num_last=ntile.patient_num_last)
                    for ntile in results
                ]
        return deps


class patient_chunks_survey(SqlScriptTask):
    script = Script.patient_chunks_survey
    patient_chunks = IntParam(default=20)
    patient_chunk_max = IntParam(default=None)

    @property
    def variables(self) -> Environment:
        return dict(chunk_qty=str(self.patient_chunks))

    def run(self) -> None:
        SqlScriptTask.run_bound(self, script_params=dict(chunk_qty=str(self.patient_chunks)))

    def results(self) -> List[RowProxy]:
        with self.connection(event='survey results') as lc:
            q = '''
               select patient_num
                 , patient_num_qty
                 , patient_num_first
                 , patient_num_last
               from patient_chunks
               where chunk_qty = :chunk_qty
                 and (:chunk_max is null or
                      chunk_num <= :chunk_max)
               order by chunk_num
             '''
            Params
            params = dict(chunk_max=self.patient_chunk_max, chunk_qty=self.patient_chunks)  # type: Params

            try:
                return lc.execute(q, params=params).fetchall()
            except DatabaseError:
                return []


class pcornet_init(CDMScriptTask):
    script = Script.pcornet_init

    def requires(self) -> List[luigi.Task]:
        return []


class pcornet_loader(CDMScriptTask):
    script = Script.pcornet_loader

    def requires(self) -> List[luigi.Task]:
        return [harvest()]


class pcornet_trial(CDMScriptTask):
    script = Script.pcornet_trial

    def requires(self) -> List[luigi.Task]:
        return [pcornet_init()]


class prescribing(CDMScriptTask):
    script = Script.prescribing

    def requires(self) -> List[luigi.Task]:
        return [encounter()]


class pro_cm(CDMScriptTask):
    script = Script.pro_cm

    def requires(self) -> List[luigi.Task]:
        return [pcornet_init()]


class procedures(CDMScriptTask):
    script = Script.procedures

    def requires(self) -> List[luigi.Task]:
        return [encounter()]


class provider(CDMScriptTask):
    script = Script.provider

    def requires(self):
        return [loadSpecialtyMap(), loadSpecialtyCode(), encounter()]


class vital(CDMScriptTask):
    script = Script.vital

    def requires(self) -> List[luigi.Task]:
        return [encounter()]


class loadLabNormal(LoadCSV):
    taskName = 'LABNORMAL'
    csvname = 'curated_data/labnormal.csv'

    def requires(self):
        return [pcornet_init()]


class loadHarvestLocal(LoadCSV):
    taskName = 'HARVEST_LOCAL'
    csvname = 'curated_data/harvest_local.csv'

    def requires(self):
        return [pcornet_init()]


class loadLanguage(LoadCSV):
    taskName = 'LANGUAGE_CODE'
    # language.csv is a copy of the CDM spec's patient_pref_language_spoke spreadsheet.
    csvname = 'curated_data/language.csv'

    def requires(self):
        return [pcornet_init()]


class loadSpecialtyMap(LoadCSV):
    taskName = 'PROVIDER_SPECIALTY_MAP'
    # provider_specialty_map.csv is created on demand by the downloadNPI method.
    csvname = 'curated_data/provider_specialty_map.csv'

    def requires(self):
        return [pcornet_init(), downloadNPI()]


class loadSpecialtyCode(LoadCSV):
    taskName = 'PROVIDER_SPECIALTY_CODE'
    # provider_specialty_code.csv is a copy of the CDM spec's provider_primary_specialty spreadsheet.
    csvname = 'curated_data/provider_specialty_code.csv'


class downloadNPI(CDMStatusTask):
    taskName = 'NPI_DOWNLOAD'
    npi_url = 'http://download.cms.gov/nppes/'
    dl_path = 'curated_data/'
    load_path = 'curated_data/'
    npi_zip = 'NPPES_Data_Dissemination_April_2018.zip'
    npi_csv = 'npidata_pfile_20050523-20180408.csv'
    specialty_csv = 'provider_specialty_map.csv'

    taxonomy_col = 'Healthcare Provider Taxonomy Code_'
    switch_col = 'Healthcare Provider Primary Taxonomy Switch_'
    npi_col = 'NPI'
    taxonomy_ct = 15

    def run(self):
        self.setTaskStart()
        self.fetch()
        self.extract()
        self.setTaskEnd(self.expectedRecords)

    def fetch(self):
        r = urllib.request.urlopen(self.npi_url + self.npi_zip)

        with open(self.dl_path + self.npi_zip, 'wb') as fout:
            fout.write(r.read())

        subprocess.call(['unzip', '-o', self.dl_path + self.npi_zip, '-d', self.dl_path])

    def extract(self):
        self.expectedRecords = 0
        with open(self.dl_path + self.npi_csv, 'r') as fin:
            with open(self.load_path + self.specialty_csv, 'w', newline='') as fout:
                reader = csv.DictReader(fin)
                writer = csv.writer(fout)
                writer.writerow(['NPI', 'SPECIALTY'])
                for row in reader:
                    self.expectedRecords = self.expectedRecords + 1
                    useDefault = True
                    for i in range(1, self.taxonomy_ct + 1):
                        if row[self.switch_col + str(i)] == 'Y':
                            useDefault = False
                            writer.writerow([row[self.npi_col], row[self.taxonomy_col + str(i)]])
                            continue

                    if (useDefault):
                        writer.writerow([row[self.npi_col], row[self.taxonomy_col + str(1)]])

