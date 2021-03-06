/** prescribing - create and populate the prescribing table.
*/
insert into cdm_status (task, start_time) select 'prescribing', sysdate from dual
/
BEGIN
PMN_DROPSQL('DROP TABLE prescribing');
END;
/
BEGIN
PMN_DROPSQL('drop table prescribing_key');
END;
/
BEGIN
PMN_DROPSQL('drop table prescribing_w_cui');
END;
/
BEGIN
PMN_DROPSQL('drop table prescribing_w_refills');
END;
/
BEGIN
PMN_DROPSQL('drop table prescribing_w_freq');
END;
/
BEGIN
PMN_DROPSQL('drop table prescribing_w_quantity');
END;
/
BEGIN
PMN_DROPSQL('drop table prescribing_w_supply');
END;
/
BEGIN
PMN_DROPSQL('drop table prescribing_w_basis');
END;
/
BEGIN
PMN_DROPSQL('drop table prescribing_w_prn');
END;
/
BEGIN
PMN_DROPSQL('drop table prescribing_w_route');
END;
/
BEGIN
PMN_DROPSQL('drop table prescribing_w_daw');
END;
/
BEGIN
PMN_DROPSQL('DROP sequence  prescribing_seq');
END;
/

create sequence  prescribing_seq cache 2000
/

/** prescribing_key -- one row per order (inpatient or outpatient)

Design note on modifiers:
create or replace view rx_mod_design as
  select c_basecode
  from blueheronmetadata.pcornet_med
  -- TODO: fix pcornet_mapping.csv
  where c_fullname like '\PCORI_MOD\RX_BASIS\PR\_%'
  and c_basecode not in ('MedObs:PRN',   -- that's a supplementary flag, not a basis
                         'MedObs:Other'  -- that's as opposed to Historical; not same category as Inpatient, Outpatient
                         )
  and c_basecode not like 'RX_BASIS:%'
;

select case when (
  select listagg(c_basecode, ',') within group (order by c_basecode) modifiers
  from rx_mod_design
  ) = 'MedObs:Inpatient,MedObs:Outpatient'
then 1 -- pass
else 1/0 -- fail
end modifiers_as_expected
from dual
;
*/
create table prescribing_key as
select cast(prescribing_seq.nextval as varchar(19)) prescribingid
, instance_num
, cast(patient_num as varchar(50)) patid
, cast(encounter_num as varchar(50)) encounterid
, provider_id rx_providerid
, start_date
, end_date
, concept_cd
, modifier_cd
, case when trim(translate(tval_char, '0123456789.', ' ')) is null then tval_char else null end rx_dose_ordered
, case when trim(translate(tval_char, '0123456789.', ' ')) is null then um.code else null end rx_dose_ordered_unit
, tval_char raw_rx_dose_ordered
, units_cd raw_rx_dose_ordered_unit
from &&i2b2_data_schema.observation_fact rx
join encounter en on rx.encounter_num = en.encounterid
left join unit_map um on rx.units_cd = um.unit_name
where rx.modifier_cd in ('MedObs:Inpatient', 'MedObs:Outpatient')
/

alter table prescribing_key modify (rx_providerid null)
/

/** prescribing_w_cui

take care with cardinalities...

select count(distinct c_name), c_basecode
from pcornet_med
group by c_basecode, c_name
having count(distinct c_name) > 1
order by c_basecode
;
*/
create table prescribing_w_cui as
select rx.*
, mo.pcori_cui rxnorm_cui
, substr(mo.c_basecode, 1, 50) raw_rxnorm_cui
, substr(mo.c_name, 1, 50) raw_rx_med_name
from prescribing_key rx
left join
  (select distinct c_basecode
  , c_name
  , pcori_cui
  from pcornet_med
  ) mo
on rx.concept_cd = mo.c_basecode
/

/** prescribing_w_refills
This join isn't guaranteed not to introduce more rows,
but at least one measurement showed it does not.
 */
create table prescribing_w_refills as
select rx.*
, refills.nval_num rx_refills
from prescribing_w_cui rx
left join
  (select instance_num
  , concept_cd
  , nval_num
  from &&i2b2_data_schema.observation_fact
  where modifier_cd = 'RX_REFILLS'
    /* aka:
    select c_basecode from pcornet_med refillscode
    where refillscode.c_fullname like '\PCORI_MOD\RX_REFILLS\' */
  ) refills on refills.instance_num = rx.instance_num and refills.concept_cd = rx.concept_cd
/

create table prescribing_w_freq as
select rx.*
-- '09' as PRN has been eliminated from the list of valid frequencies and replaced with a PRN flag.
-- For backward compatibility and simplified mapping, '09' has been retained in frequency mapping
-- (see heron:med_freq_mod_map.csv) and overridden here.
, case
    when substr(freq.pcori_basecode, instr(freq.pcori_basecode, ':') + 1, 2) = '09' then 'OT'
    else substr(freq.pcori_basecode, instr(freq.pcori_basecode, ':') + 1, 2)
  end rx_frequency
from prescribing_w_refills rx
left join
  (select instance_num
  , concept_cd
  , pcori_basecode
  from &&i2b2_data_schema.observation_fact
  join pcornet_med on modifier_cd = c_basecode
  and c_fullname like '\PCORI_MOD\RX_FREQUENCY\%'
  ) freq on freq.instance_num = rx.instance_num and freq.concept_cd = rx.concept_cd
/

create table prescribing_w_quantity as
select rx.*
, quantity.nval_num rx_quantity
from prescribing_w_freq rx
left join
  (select instance_num
  , concept_cd
  , nval_num
  from &&i2b2_data_schema.observation_fact
  where modifier_cd = 'RX_QUANTITY'
    /* aka:
    select c_basecode from pcornet_med refillscode
    where refillscode.c_fullname like '\PCORI_MOD\RX_QUANTITY\' */
  ) quantity on quantity.instance_num = rx.instance_num and quantity.concept_cd = rx.concept_cd
/

create table prescribing_w_supply as
select rx.*
, supply.nval_num rx_days_supply
from prescribing_w_quantity rx
left join
  (select instance_num
  , concept_cd
  , nval_num
  from &&i2b2_data_schema.observation_fact
  where modifier_cd = 'RX_DAYS_SUPPLY'
    /* aka:
    select c_basecode from pcornet_med refillscode
    where refillscode.c_fullname like '\PCORI_MOD\RX_DAYS_SUPPLY\' */
  ) supply on supply.instance_num = rx.instance_num and supply.concept_cd = rx.concept_cd
/

create table prescribing_w_basis as
select rx.*
, substr(basis.pcori_basecode, instr(basis.pcori_basecode, ':') + 1, 2) rx_basis
from prescribing_w_supply rx
left join
  (select instance_num
  , concept_cd
  , pcori_basecode
  from &&i2b2_data_schema.observation_fact
  join pcornet_med on modifier_cd = c_basecode
  and c_fullname like '\PCORI_MOD\RX_BASIS\%'
  and modifier_cd in ('MedObs:Inpatient', 'MedObs:Outpatient')
  ) basis on basis.instance_num = rx.instance_num and basis.concept_cd = rx.concept_cd
/

create table prescribing_w_prn as
select rx.*
-- PRN is determined by a specific source system fact or a frequency of '09'.
-- Note that '09' is now mapped to a frequency of other.  See comments in
-- 'create table prescribing_w_freq as' for related logic.
, case
    when prn.tval_char = 'Y' or rx.rx_frequency = '09' then 'Y'
    else 'N'
  end rx_prn_flag
from prescribing_w_basis rx
left join
  (select instance_num
  , concept_cd
  , 'Y' as tval_char
  from &&i2b2_data_schema.observation_fact
  where modifier_cd = 'MedObs:PRN'
    /* aka:
    select c_basecode from pcornet_med code
    where code.c_fullname like '\PCORI_MOD\RX_BASIS\PR\02\MedObs:PRN\' */
  ) prn on prn.instance_num = rx.instance_num and prn.concept_cd = rx.concept_cd
/

create table prescribing_w_route as
select rx.*
, nvl(rm.code, 'NI') rx_route
, rt.tval_char raw_rx_route
from prescribing_w_prn rx
left join
  (select instance_num
  , tval_char
  from &&i2b2_data_schema.supplemental_fact
  where source_column = 'PRESCRIBING_ROUTE'
  ) rt on rt.instance_num = rx.instance_num
left join route_map rm on lower(rt.tval_char) = lower(rm.route_name)
/

create table prescribing_w_daw as
select rx.*
, cast(nvl(tval_char, 'NI') as varchar(2)) rx_dispense_as_written
from prescribing_w_route rx
left join
  (select instance_num
  , tval_char
  from &&i2b2_data_schema.supplemental_fact
  where source_column = 'DISPENSE_AS_WRITTEN'
  ) daw on daw.instance_num = rx.instance_num
/

create table prescribing as
select rx.prescribingid
, rx.patid
, rx.encounterid
, rx.rx_providerid
, trunc(rx.start_date) rx_order_date
, to_char(rx.start_date, 'HH24:MI') rx_order_time
, trunc(rx.start_date) rx_start_date
, trunc(rx.end_date) rx_end_date
, to_number(rx.rx_dose_ordered) rx_dose_ordered
, rx.rx_dose_ordered_unit
, rx.rx_quantity
, 'NI' rx_dose_form
, rx.rx_refills
, rx.rx_days_supply
, rx.rx_frequency
, rx.rx_prn_flag
, rx.rx_route
, decode(rx.modifier_cd, 'MedObs:Inpatient', '01', 'MedObs:Outpatient', '02') rx_basis
, rx.rxnorm_cui
, 'OD' rx_source
, rx.rx_dispense_as_written
, rx.raw_rx_med_name
, cast(null as varchar(50)) raw_rx_frequency
, rx.raw_rxnorm_cui
, cast(null as varchar(50)) raw_rx_quantity
, cast(null as varchar(50)) raw_rx_ndc
, rx.raw_rx_dose_ordered
, rx.raw_rx_dose_ordered_unit
, rx.raw_rx_route
, cast(null as varchar(50)) raw_rx_refills

/* ISSUE: HERON should have an actual order time.
   idea: store real difference between order date start data, possibly using the update date */
from prescribing_w_daw rx
/

create index prescribing_idx on prescribing (PATID, ENCOUNTERID)
/
BEGIN
GATHER_TABLE_STATS('PRESCRIBING');
END;
/

update cdm_status
set end_time = sysdate, records = (select count(*) from prescribing)
where task = 'prescribing'
/

select records from cdm_status where task = 'prescribing'
