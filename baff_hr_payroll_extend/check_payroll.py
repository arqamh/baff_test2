#!/usr/bin/env python3
"""
check_payroll.py  —  Ocean Voyager Payroll: Sample Data Builder + Validator
baff_hr_payroll_extend

Creates a complete tagged test dataset, runs the full payroll pipeline on it,
then validates every layer with precise formula checks.

Coverage
--------
  Phase 1  Module & data integrity  (structures, rules, input types, wizard ACL)
  Phase 2  Employee & contract setup  (categories, OT rates, fixed allowances)
  Phase 3  Attendance & leave records  (OT hours, holiday hours, no-pay leaves)
  Phase 4  Payslip computation  (inputs, rule lines, NOPAY_DED, OT amounts, net)
  Phase 5  Salary sheet wizard  (model, action, menu, fields, smoke test)

Sample data — all records tagged "[TEST_PAYROLL]", period: March 2026
  Staff     Alice Staff    wage=50,000   NormOT=10h  HolHrs=4  NoPay=2d
  Non-Staff Bob NonStaff  wage=35,000   NormOT=8h DblOT=6h TrplOT=2h HolHrs=8 NoPay=1d

Key formula facts encoded as precise checks
  Staff  NORM_OT_AMT = 10  * (50000/240 * 1.5) = 3125.00
  NS     NORM_OT_AMT =  8  * (35000/200 * 1.5) = 2100.00
  NS     DBL_OT_AMT  =  6  * (35000/200 * 2.0) = 2100.00
  NS     TRPL_OT_AMT =  2  * (35000/200 * 3.0) = 1050.00
  Staff  NOPAY_DED   =  2  * (50000/30)         = 3333.33
  NS     NOPAY_DED   =  1  * (35000/26)         = 1346.15

  HOL_AMT uses wage/30 * 1.5 (daily rate, not the contract OT rate field).
  The check only verifies it is non-zero when HOL_HRS > 0.

  NOPAY_DED salary rule reads inputs.NOPAY_DED, which comes from a fixed
  deduction on the contract (amount = days).  The NOPAY input created by
  _get_no_pay_count (from validated leaves) is informational only.

Usage
-----
    python check_payroll.py                          # build sample + run checks
    python check_payroll.py --skip-sample            # check existing data only
    python check_payroll.py --cleanup                # delete tagged records after checks
    python check_payroll.py --cleanup-only           # delete tagged records and exit
    python check_payroll.py --url http://host:8069 --db mydb --user admin --password s3cr3t
    python check_payroll.py --no-color
"""

import argparse
import sys
import xmlrpc.client
from datetime import date, datetime

# =============================================================================
# Connection defaults  (change to match your environment)
# =============================================================================
DEFAULT_URL      = 'http://localhost:8000'
DEFAULT_DB       = 'baff_stag_03302026'
DEFAULT_USER     = 'admin'
DEFAULT_PASSWORD = 'admin'

# =============================================================================
# Sample-data parameters
# =============================================================================
TAG          = '[TEST_PAYROLL]'
SAMPLE_YEAR  = 2026
SAMPLE_MONTH = 3                          # March
DATE_FROM    = date(SAMPLE_YEAR, SAMPLE_MONTH, 1)
DATE_TO      = date(SAMPLE_YEAR, SAMPLE_MONTH, 31)

WAGE_STAFF = 50_000.0
WAGE_NS    = 35_000.0

# Computed OT rates
RATE_STAFF_N = round(WAGE_STAFF / 240.0 * 1.5, 6)   # 312.5
RATE_STAFF_D = round(WAGE_STAFF / 240.0 * 2.0, 6)
RATE_STAFF_T = round(WAGE_STAFF / 240.0 * 3.0, 6)
RATE_NS_N    = round(WAGE_NS   / 200.0 * 1.5, 6)    # 262.5
RATE_NS_D    = round(WAGE_NS   / 200.0 * 2.0, 6)    # 350.0
RATE_NS_T    = round(WAGE_NS   / 200.0 * 3.0, 6)    # 525.0

# Attendance — Staff (1 record, March 10)
OT_STAFF_NORM  = 10.0
OT_STAFF_HOL   =  4.0

# Attendance — Non-Staff (2 records: March 10 + March 17)
OT_NS_NORM_1, OT_NS_DBL_1, OT_NS_TRPL_1, OT_NS_HOL_1 = 8.0, 4.0, 2.0, 6.0
OT_NS_NORM_2, OT_NS_DBL_2, OT_NS_TRPL_2, OT_NS_HOL_2 = 0.0, 2.0, 0.0, 2.0
OT_NS_NORM  = OT_NS_NORM_1 + OT_NS_NORM_2    # 8.0
OT_NS_DBL   = OT_NS_DBL_1  + OT_NS_DBL_2    # 6.0
OT_NS_TRPL  = OT_NS_TRPL_1 + OT_NS_TRPL_2   # 2.0
OT_NS_HOL   = OT_NS_HOL_1  + OT_NS_HOL_2    # 8.0

# No-pay days — stored as fixed deduction (NOPAY_DED) on contract
NOPAY_STAFF = 2.0
NOPAY_NS    = 1.0

# Fixed allowances
FA_SPEC_INCNTV = 5_000.0
FA_LDR_ALLW    = 3_000.0
FA_ATTND_ALLW  = 2_000.0

# Expected salary rule absolute values
EXP_STAFF_NORM_OT = round(OT_STAFF_NORM * RATE_STAFF_N, 2)        # 3125.00
EXP_NS_NORM_OT    = round(OT_NS_NORM    * RATE_NS_N,    2)        # 2100.00
EXP_NS_DBL_OT     = round(OT_NS_DBL     * RATE_NS_D,    2)        # 2100.00
EXP_NS_TRPL_OT    = round(OT_NS_TRPL    * RATE_NS_T,    2)        # 1050.00
EXP_STAFF_NOPAY   = round(NOPAY_STAFF   * (WAGE_STAFF / 30), 2)   # 3333.33
EXP_NS_NOPAY      = round(NOPAY_NS      * (WAGE_NS    / 26), 2)   # 1346.15

# =============================================================================
# Terminal colours
# =============================================================================
USE_COLOR = True

def _c(code, t):    return f'\033[{code}m{t}\033[0m' if USE_COLOR else t
def _ok(m):         print(_c('92', '[PASS]'), m)
def _fail(m):       print(_c('91', '[FAIL]'), m)
def _warn(m):       print(_c('93', '[WARN]'), m)
def _info(m):       print(_c('94', '[INFO]'), m)
def _step(m):       print(_c('96', '[STEP]'), m)
def _head(title):
    bar = _c('1;96', '─' * 64)
    print(f'\n{bar}\n  {_c("1;96", title)}\n{bar}')

# =============================================================================
# Odoo XML-RPC wrapper
# =============================================================================
class Odoo:
    def __init__(self, url, db, user, password):
        self.db = db
        self.pw = password
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
        try:
            self.uid = common.authenticate(db, user, password, {})
        except Exception as exc:
            sys.exit(f'Cannot reach Odoo at {url}: {exc}')
        if not self.uid:
            sys.exit(f'Authentication failed (db={db}, user={user})')
        self._m = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
        ver = common.version().get('server_version', '?')
        _info(f'Connected — Odoo {ver}  db={db}  uid={self.uid}')

    def call(self, model, method, *args, **kw):
        return self._m.execute_kw(self.db, self.uid, self.pw,
                                  model, method, list(args), kw)

    def create(self, model, vals):
        return self.call(model, 'create', vals)

    def write(self, model, ids, vals):
        return self.call(model, 'write', ids, vals)

    def search(self, model, domain, fields=None, limit=None, order=None):
        kw = {}
        if fields: kw['fields'] = fields
        if limit:  kw['limit']  = limit
        if order:  kw['order']  = order
        return self.call(model, 'search_read', domain, **kw)

    def count(self, model, domain):
        return self.call(model, 'search_count', domain)

    def field_exists(self, model, fname):
        try:
            return fname in self.call(model, 'fields_get', [fname])
        except Exception:
            return False

    def get_relation(self, model, fname):
        try:
            info = self.call(model, 'fields_get', [fname])
            return info.get(fname, {}).get('relation')
        except Exception:
            return None

    @staticmethod
    def fmt_date(d):
        return d.strftime('%Y-%m-%d')

    @staticmethod
    def fmt_dt(d, h=8, m=0):
        return datetime(d.year, d.month, d.day, h, m).strftime('%Y-%m-%d %H:%M:%S')


# =============================================================================
# Sample Data Creator
# =============================================================================
class SampleDataCreator:
    """
    Builds a complete tagged payroll test dataset. Idempotent — re-running
    reuses existing tagged records instead of creating duplicates.
    """

    def __init__(self, odoo):
        self.o      = odoo
        self._stack = []           # (model, id) in creation order

        # Public refs populated during build()
        self.company_id    = None
        self.job_staff_id  = None
        self.job_ns_id     = None
        self.emp_staff_id  = None
        self.emp_ns_id     = None
        self.ct_staff_id   = None
        self.ct_ns_id      = None
        self.batch_id      = None
        self.slip_staff_id = None
        self.slip_ns_id    = None

    # ── helpers ───────────────────────────────────────────────────────────────

    def _create(self, model, vals):
        rid = self.o.create(model, vals)
        self._stack.append((model, rid))
        _step(f'  Created  {model:48s} id={rid}')
        return rid

    def _reuse_or_create(self, model, id_domain, create_vals):
        rows = self.o.search(model, id_domain, fields=['id'], limit=1)
        if rows:
            _step(f'  Reusing  {model:48s} id={rows[0]["id"]}')
            return rows[0]['id'], False
        return self._create(model, create_vals), True

    # ── steps ─────────────────────────────────────────────────────────────────

    def _setup_company(self):
        rows = self.o.search('res.company', [], fields=['id', 'name'], limit=1)
        if rows:
            self.company_id = rows[0]['id']
            _info(f'  Company: {rows[0]["name"]} (id={self.company_id})')

    def _setup_jobs(self):
        for attr, title in [('job_staff_id', f'{TAG} Staff Officer'),
                             ('job_ns_id',   f'{TAG} Non-Staff Worker')]:
            rid, _ = self._reuse_or_create('hr.job', [('name', '=', title)],
                                            {'name': title})
            setattr(self, attr, rid)

    def _setup_employees(self):
        cat_ok       = self.o.field_exists('hr.employee', 'ocean_voyager_emp_category')
        epf_ok       = self.o.field_exists('hr.employee', 'epf_number')
        initials_ok  = self.o.field_exists('hr.employee', 'name_initials')
        lastname_ok  = self.o.field_exists('hr.employee', 'last_name')
        if not cat_ok:
            _warn('  ocean_voyager_emp_category not on hr.employee — is baff_hr_extend installed?')

        for attr, name, cat, epf, initials, last_name, job in [
            ('emp_staff_id', f'{TAG} Alice Staff',  'staff',     'TEST-S01', 'T.A.', 'Staff',    self.job_staff_id),
            ('emp_ns_id',    f'{TAG} Bob NonStaff', 'non_staff', 'TEST-N01', 'T.B.', 'NonStaff', self.job_ns_id),
        ]:
            rows = self.o.search('hr.employee', [('name', '=', name)],
                                 fields=['id'], limit=1)
            if rows:
                _step(f'  Reusing  hr.employee                                  id={rows[0]["id"]}')
                setattr(self, attr, rows[0]['id'])
                continue
            vals = {'name': name, 'job_id': job}
            if cat_ok:          vals['ocean_voyager_emp_category'] = cat
            if epf_ok:          vals['epf_number'] = epf
            if initials_ok:     vals['name_initials'] = initials
            if lastname_ok:     vals['last_name'] = last_name
            if self.company_id: vals['company_id'] = self.company_id
            setattr(self, attr, self._create('hr.employee', vals))

    def _setup_contracts(self):
        st = self.o.search('hr.payroll.structure.type',
                           [('default_struct_id', '!=', False)],
                           fields=['id'], limit=1)
        struct_type_id = st[0]['id'] if st else None

        for attr, emp_id, name, wage in [
            ('ct_staff_id', self.emp_staff_id, f'{TAG} Contract Alice Staff',  WAGE_STAFF),
            ('ct_ns_id',    self.emp_ns_id,    f'{TAG} Contract Bob NonStaff', WAGE_NS),
        ]:
            rows = self.o.search('hr.contract', [('name', '=', name)],
                                 fields=['id'], limit=1)
            if rows:
                ct_id = rows[0]['id']
                _step(f'  Reusing  hr.contract                                  id={ct_id}')
                setattr(self, attr, ct_id)
                try: self.o.write('hr.contract', [ct_id], {'state': 'open'})
                except Exception: pass
                continue

            vals = {
                'name': name, 'employee_id': emp_id, 'wage': wage,
                'date_start': Odoo.fmt_date(date(SAMPLE_YEAR, 1, 1)),
                'state': 'open',
            }
            if struct_type_id:
                vals['structure_type_id'] = struct_type_id
            ct_id = self._create('hr.contract', vals)
            setattr(self, attr, ct_id)
            try: self.o.write('hr.contract', [ct_id], {'state': 'open'})
            except Exception: pass

    def _setup_attendance(self):
        if not self.o.field_exists('hr.attendance', 'eligible_for_overtime'):
            _warn('  OT fields missing on hr.attendance — skipping attendance creation')
            return

        have = {f: self.o.field_exists('hr.attendance', f)
                for f in ('normal_overtime', 'double_overtime',
                          'triple_overtime', 'holiday_hours')}

        # (emp_id, day, ci_h, co_h, norm, dbl, trpl, hol)
        specs = [
            (self.emp_staff_id, 10,  8, 20, OT_STAFF_NORM, 0.0,         0.0,          OT_STAFF_HOL),
            (self.emp_ns_id,    10,  8, 22, OT_NS_NORM_1,  OT_NS_DBL_1, OT_NS_TRPL_1, OT_NS_HOL_1),
            (self.emp_ns_id,    17,  8, 16, OT_NS_NORM_2,  OT_NS_DBL_2, OT_NS_TRPL_2, OT_NS_HOL_2),
        ]
        for emp_id, day, h_in, h_out, norm, dbl, trpl, hol in specs:
            att_date = date(SAMPLE_YEAR, SAMPLE_MONTH, day)
            existing = self.o.search(
                'hr.attendance',
                [('employee_id', '=', emp_id),
                 ('check_in_date', '=', Odoo.fmt_date(att_date))],
                fields=['id'], limit=1)
            if existing:
                _step(f'  Reusing  hr.attendance                               id={existing[0]["id"]}')
                continue

            vals = {
                'employee_id': emp_id,
                'check_in':    Odoo.fmt_dt(att_date, h_in),
                'check_out':   Odoo.fmt_dt(att_date, h_out),
                'eligible_for_overtime':    True,
                'overtime_approval_status': 'approved',
            }
            ot_map = {'normal_overtime': norm, 'double_overtime': dbl,
                      'triple_overtime': trpl, 'holiday_hours': hol}
            for f, v in ot_map.items():
                if have[f]:
                    vals[f] = v
            self._create('hr.attendance', vals)

    def _setup_leaves(self):
        """Create validated no-pay leaves — populates informational NOPAY input."""
        et = self.o.search('hr.work.entry.type', [('code', '=', 'NOPAY')],
                           fields=['id'], limit=1)
        if not et:
            _warn('  NOPAY work entry type not found — skipping leave creation'); return

        lt = self.o.search('hr.leave.type',
                           [('work_entry_type_id', '=', et[0]['id'])],
                           fields=['id', 'name'], limit=1)
        if not lt:
            _warn('  No leave type mapped to NOPAY — skipping leave creation'); return
        lt_id = lt[0]['id']

        for emp_id, d_from, d_to in [
            (self.emp_staff_id, date(SAMPLE_YEAR, SAMPLE_MONTH, 5),
                                date(SAMPLE_YEAR, SAMPLE_MONTH, 6)),
            (self.emp_ns_id,    date(SAMPLE_YEAR, SAMPLE_MONTH, 7),
                                date(SAMPLE_YEAR, SAMPLE_MONTH, 7)),
        ]:
            existing = self.o.search(
                'hr.leave',
                [('employee_id', '=', emp_id),
                 ('holiday_status_id', '=', lt_id),
                 ('request_date_from', '=', Odoo.fmt_date(d_from)),
                 ('state', '!=', 'refuse')],
                fields=['id'], limit=1)
            if existing:
                _step(f'  Reusing  hr.leave                                    id={existing[0]["id"]}')
                continue

            days = (d_to - d_from).days + 1
            leave_id = self._create('hr.leave', {
                'employee_id':       emp_id,
                'holiday_status_id': lt_id,
                'request_date_from': Odoo.fmt_date(d_from),
                'request_date_to':   Odoo.fmt_date(d_to),
                'number_of_days':    days,
            })
            final = 'draft'
            for action in ('action_confirm', 'action_approve', 'action_validate'):
                try:
                    self.o.call('hr.leave', action, [[leave_id]])
                    row = self.o.search('hr.leave', [('id', '=', leave_id)],
                                        fields=['state'], limit=1)
                    final = row[0]['state'] if row else '?'
                    if final == 'validate': break
                except Exception:
                    pass
            if final == 'validate':
                _step(f'  Leave id={leave_id} validated ({days} day(s))')
            else:
                _warn(f'  Leave id={leave_id} state={final} — '
                      f'NOPAY informational input may be 0')

    def _setup_fixed_allowances(self):
        """Add allowances + NOPAY_DED deduction to contracts."""
        allw_model = self.o.get_relation('hr.contract', 'fixed_allowance_ids')
        ded_model  = self.o.get_relation('hr.contract', 'fixed_deduction_ids')
        if not allw_model:
            _warn('  fixed_allowance_ids not found on hr.contract — skipping'); return

        def _fad(code, fallback_name):
            rows = self.o.search('fixed.allowance.deduction',
                                 [('input_type_id.code', '=', code)],
                                 fields=['id'], limit=1)
            if rows:
                return rows[0]['id']
            it = self.o.search('hr.payslip.input.type', [('code', '=', code)],
                               fields=['id'], limit=1)
            if not it:
                _warn(f'  Input type [{code}] not found — skipping fad'); return None
            try:
                fid = self.o.create('fixed.allowance.deduction',
                                    {'name': fallback_name,
                                     'input_type_id': it[0]['id']})
                self._stack.append(('fixed.allowance.deduction', fid))
                _step(f'  Created  fixed.allowance.deduction                   id={fid} [{code}]')
                return fid
            except Exception as e:
                _warn(f'  Could not create fad for [{code}]: {e}'); return None

        fad_spec  = _fad('SPEC_INCNTV', 'Special Incentive')
        fad_ldr   = _fad('LDR_ALLW',   'Leader Allowance')
        fad_attnd = _fad('ATTND_ALLW',  'Attendance Allowance')
        fad_nopay = _fad('NOPAY_DED',   'No Pay Days')

        def _already(ct_id, model, fad_id):
            if not fad_id: return True
            try:
                return bool(self.o.search(model,
                                          [('contract_id', '=', ct_id),
                                           ('type_id', '=', fad_id)],
                                          fields=['id'], limit=1))
            except Exception:
                return False

        def _add(ct_id, o2m_field, fad_id, amount, desc):
            if not fad_id: return
            m = allw_model if o2m_field == 'fixed_allowance_ids' else (ded_model or allw_model)
            if _already(ct_id, m, fad_id):
                _step(f'  Reusing  fixed item on contract {ct_id}: {desc}'); return
            try:
                self.o.write('hr.contract', [ct_id], {
                    o2m_field: [(0, 0, {'type_id': fad_id, 'amount': amount,
                                        'description': f'{TAG} {desc}'})]
                })
                _step(f'  Added    {o2m_field} ct={ct_id}: {desc} = {amount}')
            except Exception as e:
                _warn(f'  Could not add {desc} to contract {ct_id}: {e}')

        ded_field = 'fixed_deduction_ids' if ded_model else 'fixed_allowance_ids'

        # Staff
        _add(self.ct_staff_id, 'fixed_allowance_ids', fad_spec,  FA_SPEC_INCNTV, 'Special Incentive')
        _add(self.ct_staff_id, 'fixed_allowance_ids', fad_attnd, FA_ATTND_ALLW,  'Attendance Allowance')
        _add(self.ct_staff_id, ded_field,             fad_nopay, NOPAY_STAFF,    'No Pay Days')
        # Non-Staff
        _add(self.ct_ns_id, 'fixed_allowance_ids', fad_ldr,   FA_LDR_ALLW,    'Leader Allowance')
        _add(self.ct_ns_id, 'fixed_allowance_ids', fad_attnd, FA_ATTND_ALLW,  'Attendance Allowance')
        _add(self.ct_ns_id, ded_field,             fad_nopay, NOPAY_NS,       'No Pay Days')

    def _setup_payslips(self):
        batch_name = f'{TAG} Payroll March {SAMPLE_YEAR}'
        b = self.o.search('hr.payslip.run', [('name', '=', batch_name)],
                          fields=['id'], limit=1)
        if b:
            self.batch_id = b[0]['id']
            _step(f'  Reusing  hr.payslip.run                               id={self.batch_id}')
        else:
            self.batch_id = self._create('hr.payslip.run', {
                'name':       batch_name,
                'date_start': Odoo.fmt_date(DATE_FROM),
                'date_end':   Odoo.fmt_date(DATE_TO),
            })

        struct_map = {}
        for code in ('OCEAN_VOYAGER_STAFF', 'OCEAN_VOYAGER_NON_STAFF'):
            r = self.o.search('hr.payroll.structure', [('code', '=', code)],
                              fields=['id'], limit=1)
            if r: struct_map[code] = r[0]['id']

        for attr, emp_id, ct_id, sname, scode in [
            ('slip_staff_id', self.emp_staff_id, self.ct_staff_id,
             f'{TAG} Payslip March {SAMPLE_YEAR} - Alice Staff',
             'OCEAN_VOYAGER_STAFF'),
            ('slip_ns_id',    self.emp_ns_id,    self.ct_ns_id,
             f'{TAG} Payslip March {SAMPLE_YEAR} - Bob NonStaff',
             'OCEAN_VOYAGER_NON_STAFF'),
        ]:
            s = self.o.search('hr.payslip', [('name', '=', sname)],
                              fields=['id', 'state'], limit=1)
            if s:
                slip_id = s[0]['id']
                _step(f'  Reusing  hr.payslip                                  id={slip_id}')
            else:
                vals = {
                    'name':           sname,
                    'employee_id':    emp_id,
                    'payslip_run_id': self.batch_id,
                    'date_from':      Odoo.fmt_date(DATE_FROM),
                    'date_to':        Odoo.fmt_date(DATE_TO),
                    'contract_id':    ct_id,
                }
                if scode in struct_map:
                    vals['struct_id'] = struct_map[scode]
                slip_id = self._create('hr.payslip', vals)
            setattr(self, attr, slip_id)

            # Re-trigger input computation
            try:
                self.o.call('hr.payslip',
                            'action_recall_payslip_input_lines_calculation',
                            [[slip_id]])
                _step(f'  Inputs recomputed  slip id={slip_id}')
            except Exception as e:
                _warn(f'  action_recall_payslip_input_lines_calculation: {e}')

            # Compute salary rule lines
            try:
                self.o.call('hr.payslip', 'compute_sheet', [[slip_id]])
                _step(f'  compute_sheet() done  slip id={slip_id}')
            except Exception as e:
                _warn(f'  compute_sheet() failed: {e}')

            # Confirm payslip
            cur = (self.o.search('hr.payslip', [('id', '=', slip_id)],
                                 fields=['state'], limit=1) or [{}])[0].get('state')
            if cur != 'done':
                try:
                    self.o.call('hr.payslip', 'action_payslip_done', [[slip_id]])
                    _step(f'  Payslip id={slip_id} confirmed -> done')
                except Exception as e:
                    _warn(f'  action_payslip_done() failed: {e} — slip stays {cur}')

    # ── public ────────────────────────────────────────────────────────────────

    def build(self):
        _head('Building Sample Data')
        self._setup_company()
        self._setup_jobs()
        self._setup_employees()
        self._setup_contracts()
        self._setup_attendance()
        self._setup_leaves()
        self._setup_fixed_allowances()
        self._setup_payslips()
        _info(f'\nSample data ready — batch={self.batch_id}'
              f'  slip_staff={self.slip_staff_id}  slip_ns={self.slip_ns_id}')
        return self

    def cleanup(self):
        _head('Cleanup — Removing Sample Data')
        for sid in (self.slip_staff_id, self.slip_ns_id):
            if sid:
                for action in ('action_payslip_cancel', 'action_draft'):
                    try: self.o.call('hr.payslip', action, [[sid]])
                    except Exception: pass
        for model, rid in reversed(self._stack):
            try:
                self.o.call(model, 'unlink', [rid])
                _ok(f'  Deleted {model} id={rid}')
            except Exception as e:
                _warn(f'  Could not delete {model} id={rid}: {e}')

    @staticmethod
    def cleanup_by_tag(odoo):
        """Stateless — searches and removes all records whose name contains TAG."""
        _head(f'Cleanup — Removing All Records Tagged {TAG!r}')
        for model in ('hr.payslip', 'hr.payslip.run', 'hr.leave',
                      'hr.attendance', 'hr.contract', 'hr.employee', 'hr.job'):
            try:
                rows = odoo.search(model, [('name', 'like', TAG)],
                                   fields=['id'], limit=0)
                ids = [r['id'] for r in rows]
                if not ids:
                    _info(f'  No tagged records in {model}'); continue
                if model == 'hr.payslip':
                    for action in ('action_payslip_cancel', 'action_draft'):
                        try: odoo.call(model, action, [ids])
                        except Exception: pass
                odoo.call(model, 'unlink', ids)
                _ok(f'  Deleted {len(ids)} record(s) from {model}')
            except Exception as e:
                _warn(f'  {model}: {e}')


# =============================================================================
# Payroll Checker
# =============================================================================
class PayrollChecker:

    def __init__(self, odoo, sample=None):
        self.o      = odoo
        self.sample = sample
        self.passed = 0
        self.failed = 0
        self.warned = 0

    def ok(self, m):    _ok(m);   self.passed += 1
    def fail(self, m):  _fail(m); self.failed += 1
    def warn(self, m):  _warn(m); self.warned += 1

    def check(self, cond, ok_msg, fail_msg, *, soft=False):
        if cond:
            self.ok(ok_msg)
        elif soft:
            self.warn(fail_msg)
        else:
            self.fail(fail_msg)

    def near(self, actual, expected, label, tol=0.5):
        diff = abs(actual - expected)
        self.check(diff <= tol,
                   f'{label}: {expected:,.2f} (actual={actual:,.2f}) OK',
                   f'{label}: expected={expected:,.2f} actual={actual:,.2f} diff={diff:,.2f}')

    # ── payslip data helpers ──────────────────────────────────────────────────

    def _get_inputs(self, slip_id):
        """Return {input_type_code: amount} for a payslip."""
        rows = self.o.search(
            'hr.payslip.input',
            [('payslip_id', '=', slip_id)],
            fields=['name', 'amount', 'input_type_id'],
        )
        result = {}
        for r in rows:
            it = r.get('input_type_id')
            if it:
                it_id = it[0] if isinstance(it, (list, tuple)) else it
                it_r  = self.o.search('hr.payslip.input.type', [('id', '=', it_id)],
                                       fields=['code'], limit=1)
                code = it_r[0]['code'] if it_r else r.get('name', '?')
            else:
                code = r.get('name', '?')
            result[code] = r.get('amount', 0.0)
        return result

    def _get_lines(self, slip_id):
        """Return {rule_code: total} for a payslip."""
        rows = self.o.search('hr.payslip.line', [('slip_id', '=', slip_id)],
                             fields=['code', 'name', 'total'], limit=0)
        return {r['code']: r['total'] for r in rows}

    def _chk_inp(self, inputs, code, expected, label):
        v = inputs.get(code)
        if v is None: self.fail(f'{label}: input [{code}] not found in payslip')
        else:         self.near(abs(v), abs(expected), label)

    def _chk_line(self, lines, code, expected, label):
        v = lines.get(code)
        if v is None: self.fail(f'{label}: rule [{code}] not in payslip lines')
        else:         self.near(abs(v), abs(expected), label)

    def _chk_nonzero(self, lines, code, label):
        v = lines.get(code)
        if v is None:
            self.fail(f'{label}: rule [{code}] not found')
        else:
            self.check(abs(v) > 0, f'{label}: [{code}] = {v:,.2f} (non-zero)',
                       f'{label}: [{code}] = 0  (expected non-zero)')

    def _net_sanity(self, lines, label):
        g, d, n = lines.get('BAFF_GROSS'), lines.get('TOT_DED'), lines.get('BAFF_NET')
        if None in (g, d, n):
            self.warn(f'{label} net sanity: BAFF_GROSS/TOT_DED/BAFF_NET not all present')
            return
        self.near(n, g + d,
                  f'{label} NET sanity  GROSS={g:,.2f} TOT_DED={d:,.2f} NET={n:,.2f}')

    # =========================================================================
    # Phase 1 — Module & Data Integrity
    # =========================================================================
    def phase1_data_integrity(self):
        _head('Phase 1 — Module & Data Integrity')

        mods = self.o.search('ir.module.module',
                             [('name', '=', 'baff_hr_payroll_extend')],
                             fields=['state', 'installed_version'])
        if not mods:
            self.fail("Module 'baff_hr_payroll_extend' not found"); return False
        m = mods[0]
        self.check(m['state'] == 'installed',
                   f"Module installed (v{m['installed_version']})",
                   f"Module state='{m['state']}' — expected 'installed'")

        _info('Salary structures …')
        for code in ('OCEAN_VOYAGER', 'OCEAN_VOYAGER_STAFF', 'OCEAN_VOYAGER_NON_STAFF'):
            r = self.o.search('hr.payroll.structure', [('code', '=', code)], fields=['name'])
            self.check(bool(r), f'Structure [{code}]', f'Structure [{code}] missing')

        _info('Input types …')
        existing = {r['code'] for r in
                    self.o.search('hr.payslip.input.type', [], fields=['code'], limit=0)}
        for code in ('NORM_OT_HRS', 'DBL_OT_HRS', 'TRPL_OT_HRS', 'HOL_HRS',
                     'ATTND_ALLW', 'SPEC_ALLW', 'SAL_ADV', 'TEAM_HELP',
                     'NOPAY_DED', 'REl_ALW', 'NO_EXP', 'NOPAY',
                     'LEAVE_ALLW', 'SPEC_INCNTV', 'LDR_ALLW'):
            self.check(code in existing,
                       f'Input type [{code}]', f'Input type [{code}] missing')

        for struct_code, rule_codes, ot_codes, lbl in [
            ('OCEAN_VOYAGER_STAFF',
             ('BAFF_BASIC', 'NORM_OT_AMT', 'HOL_AMT', 'SPEC_INCNTV', 'ATTND_ALLW',
              'BAFF_GROSS', 'SAL_ADV', 'NOPAY_DED', 'EPF_EE_8', 'PAYE_TAX',
              'TEAM_HELP', 'TOT_DED', 'BAFF_NET', 'EPF_ER_3', 'EPF_ER_12'),
             ('NORM_OT_AMT',), 'Staff'),
            ('OCEAN_VOYAGER_NON_STAFF',
             ('BAFF_BASIC', 'NORM_OT_AMT', 'DBL_OT_AMT', 'TRPL_OT_AMT', 'HOL_AMT',
              'LDR_ALLW', 'ATTND_ALLW', 'REL_ALLW', 'BAFF_GROSS', 'SAL_ADV',
              'NOPAY_DED', 'EPF_EE_8', 'PAYE_TAX', 'TEAM_HELP', 'TOT_DED',
              'BAFF_NET', 'EPF_ER_3', 'EPF_ER_12'),
             ('NORM_OT_AMT', 'DBL_OT_AMT', 'TRPL_OT_AMT'), 'Non-Staff'),
        ]:
            _info(f'{lbl} rules …')
            struct = self.o.search('hr.payroll.structure', [('code', '=', struct_code)],
                                   fields=['id'])
            if not struct:
                self.fail(f'  Structure [{struct_code}] not found'); continue
            present = {r['code']: r.get('amount_python_compute', '')
                       for r in self.o.search(
                           'hr.salary.rule', [('struct_id', '=', struct[0]['id'])],
                           fields=['code', 'amount_python_compute'], limit=0)}
            for code in rule_codes:
                self.check(code in present,
                           f'  [{lbl}] rule [{code}]',
                           f'  [{lbl}] rule [{code}] missing')
            for code in ot_codes:
                if code not in present: continue
                f = present[code]
                has_rate = 'baff_ot_rate_' in f
                hardcoded = any(kw in f for kw in
                                ('wage/240', 'wage/200', 'wage / 240', 'wage / 200'))
                if has_rate and not hardcoded:
                    self.ok(f'  [{lbl}] [{code}] uses computed rate field')
                elif hardcoded:
                    self.fail(f'  [{lbl}] [{code}] hardcoded wage divisor — update to baff_ot_rate_*')
                else:
                    self.warn(f'  [{lbl}] [{code}] formula unrecognised: {f[:55]}')

        _info('Wizard …')
        wiz = self.o.search('ir.model', [('model', '=', 'hr.salary.sheet.wizard')],
                            fields=['id', 'name'])
        self.check(bool(wiz), 'Wizard model registered',
                   "Wizard model 'hr.salary.sheet.wizard' not found")
        if wiz:
            n = self.o.count('ir.model.access', [('model_id', '=', wiz[0]['id'])])
            self.check(n >= 2, f'Wizard ACL: {n} record(s) (User + Manager)',
                       f'Wizard ACL: {n} record(s) — menu may be hidden for non-admin')

        for code, name in (('SPEC_INCNTV', 'Special Incentive'),
                            ('LDR_ALLW', 'Leader Allowance')):
            it = self.o.search('hr.payslip.input.type', [('code', '=', code)], fields=['id'])
            if it:
                fn = self.o.count('fixed.allowance.deduction',
                                  [('input_type_id', '=', it[0]['id'])])
                self.check(fn > 0,
                           f'fixed.allowance.deduction for [{code}] ({name}) exists',
                           f'fixed.allowance.deduction for [{code}] missing — '
                           f"type won't appear in contract config")
        return True

    # =========================================================================
    # Phase 2 — Employee & Contract Configuration
    # =========================================================================
    def phase2_employees_contracts(self):
        _head('Phase 2 — Employee & Contract Configuration')

        if not self.o.field_exists('hr.employee', 'ocean_voyager_emp_category'):
            self.fail("'ocean_voyager_emp_category' not on hr.employee"); return

        ns = self.o.count('hr.employee', [('ocean_voyager_emp_category', '=', 'staff')])
        nn = self.o.count('hr.employee', [('ocean_voyager_emp_category', '=', 'non_staff')])
        nu = self.o.count('hr.employee',
                          [('ocean_voyager_emp_category', 'not in', ['staff', 'non_staff']),
                           ('active', '=', True)])
        self.check(ns > 0, f'Staff employees: {ns}',    'No staff employees',    soft=True)
        self.check(nn > 0, f'Non-Staff employees: {nn}', 'No non-staff employees', soft=True)
        if nu: self.warn(f'{nu} active employee(s) have no category set')

        if not self.o.field_exists('hr.contract', 'baff_ot_rate_normal'):
            self.fail("baff_ot_rate_* not on hr.contract"); return

        cts = self.o.search('hr.contract', [('state', '=', 'open')],
                            fields=['name', 'wage', 'baff_ot_rate_normal',
                                    'baff_ot_rate_double', 'baff_ot_rate_triple'],
                            limit=0)
        self.check(bool(cts), f'Running contracts: {len(cts)}',
                   'No running contracts', soft=True)

        bad = [c['name'] for c in cts
               if c['wage'] and (not c['baff_ot_rate_normal']
                                 or not c['baff_ot_rate_double']
                                 or not c['baff_ot_rate_triple'])]
        if bad:
            self.fail(f'{len(bad)} contract(s) with wage>0 but zero OT rate: '
                      f'{", ".join(bad[:4])}' + (' ...' if len(bad) > 4 else ''))
        else:
            self.ok(f'All {len(cts)} running contracts have OT rates > 0')

        # Precise formula checks for sample contracts
        if self.sample:
            for ct_id, lbl, wage, cat in [
                (self.sample.ct_staff_id, 'Staff (Alice)',   WAGE_STAFF, 'staff'),
                (self.sample.ct_ns_id,    'NS (Bob)',        WAGE_NS,    'non_staff'),
            ]:
                if not ct_id: continue
                rows = self.o.search('hr.contract', [('id', '=', ct_id)],
                                     fields=['baff_ot_rate_normal',
                                             'baff_ot_rate_double',
                                             'baff_ot_rate_triple'])
                if not rows: continue
                c, div = rows[0], 240.0 if cat == 'staff' else 200.0
                for field, mult in (('baff_ot_rate_normal', 1.5),
                                    ('baff_ot_rate_double', 2.0),
                                    ('baff_ot_rate_triple', 3.0)):
                    self.near(round(c[field], 4), round(wage / div * mult, 4),
                              f'{lbl} {field} (wage/{int(div)} x{mult})')

    # =========================================================================
    # Phase 3 — Attendance & Leave Records
    # =========================================================================
    def phase3_attendance_leaves(self):
        _head('Phase 3 — Attendance & Leave Records')

        n_ot = self.o.count('hr.attendance',
                            [('eligible_for_overtime', '=', True),
                             ('overtime_approval_status', '=', 'approved')])
        self.check(n_ot > 0, f'Approved OT attendance records: {n_ot}',
                   'No approved OT attendance — OT hours will be 0', soft=True)

        if not self.o.field_exists('hr.attendance', 'holiday_hours'):
            self.fail("'holiday_hours' missing on hr.attendance"); return

        n_hol = self.o.count('hr.attendance',
                             [('eligible_for_overtime', '=', True),
                              ('overtime_approval_status', '=', 'approved'),
                              ('holiday_hours', '>', 0)])
        self.check(n_hol > 0, f'Records with holiday_hours > 0: {n_hol}',
                   'No holiday_hours records — Holiday OT will be 0', soft=True)

        if self.sample:
            for emp_id, lbl, en, ed, et, eh in [
                (self.sample.emp_staff_id, 'Alice Staff',
                 OT_STAFF_NORM, 0.0, 0.0, OT_STAFF_HOL),
                (self.sample.emp_ns_id, 'Bob NonStaff',
                 OT_NS_NORM, OT_NS_DBL, OT_NS_TRPL, OT_NS_HOL),
            ]:
                if not emp_id: continue
                recs = self.o.search(
                    'hr.attendance',
                    [('employee_id', '=', emp_id),
                     ('eligible_for_overtime', '=', True),
                     ('overtime_approval_status', '=', 'approved'),
                     ('check_in_date', '>=', Odoo.fmt_date(DATE_FROM)),
                     ('check_in_date', '<=', Odoo.fmt_date(DATE_TO))],
                    fields=['normal_overtime', 'double_overtime',
                            'triple_overtime', 'holiday_hours'], limit=0)
                if not recs:
                    self.fail(f'{lbl}: no approved OT attendance in sample period'); continue
                an = sum(r.get('normal_overtime', 0) or 0 for r in recs)
                ad = sum(r.get('double_overtime', 0) or 0 for r in recs)
                at = sum(r.get('triple_overtime', 0) or 0 for r in recs)
                ah = sum(r.get('holiday_hours',   0) or 0 for r in recs)
                self.near(an, en, f'{lbl} attendance: normal_overtime total')
                if ed: self.near(ad, ed, f'{lbl} attendance: double_overtime total')
                if et: self.near(at, et, f'{lbl} attendance: triple_overtime total')
                self.near(ah, eh, f'{lbl} attendance: holiday_hours total')

        et = self.o.search('hr.work.entry.type', [('code', '=', 'NOPAY')],
                           fields=['id', 'name'])
        self.check(bool(et), f'Work entry type [NOPAY]: {et[0]["name"] if et else ""}',
                   'Work entry type [NOPAY] not found')
        if et:
            lt = self.o.search('hr.leave.type',
                               [('work_entry_type_id', '=', et[0]['id'])],
                               fields=['name'])
            self.check(bool(lt),
                       f'Leave types mapped to NOPAY: {[t["name"] for t in lt]}',
                       'No leave type mapped to NOPAY work entry type')

        if self.sample:
            for emp_id, lbl in [(self.sample.emp_staff_id, 'Alice Staff'),
                                 (self.sample.emp_ns_id,    'Bob NonStaff')]:
                if not emp_id: continue
                validated = self.o.search(
                    'hr.leave',
                    [('employee_id', '=', emp_id),
                     ('state', '=', 'validate'),
                     ('request_date_from', '<=', Odoo.fmt_date(DATE_TO)),
                     ('request_date_to',   '>=', Odoo.fmt_date(DATE_FROM))],
                    fields=['number_of_days'], limit=0)
                days = sum(r['number_of_days'] for r in validated)
                self.check(days > 0,
                           f'{lbl}: validated no-pay leaves = {days} day(s)',
                           f'{lbl}: no validated no-pay leaves (NOPAY info input = 0)',
                           soft=True)

    # =========================================================================
    # Phase 4 — Payslip Computation
    # =========================================================================
    def phase4_payslip_computation(self):
        _head('Phase 4 — Payslip Computation')

        if self.sample:
            self._check_slip(
                slip_id=self.sample.slip_staff_id, label='STAFF (Alice)',
                wage=WAGE_STAFF,
                exp_norm=EXP_STAFF_NORM_OT, exp_dbl=None, exp_trpl=None,
                exp_nopay=EXP_STAFF_NOPAY,
                exp_spec=FA_SPEC_INCNTV, exp_ldr=None, exp_attnd=FA_ATTND_ALLW,
                in_norm=OT_STAFF_NORM, in_dbl=None, in_trpl=None,
                in_hol=OT_STAFF_HOL, nopay_days=NOPAY_STAFF,
            )
            self._check_slip(
                slip_id=self.sample.slip_ns_id, label='NON-STAFF (Bob)',
                wage=WAGE_NS,
                exp_norm=EXP_NS_NORM_OT, exp_dbl=EXP_NS_DBL_OT, exp_trpl=EXP_NS_TRPL_OT,
                exp_nopay=EXP_NS_NOPAY,
                exp_spec=None, exp_ldr=FA_LDR_ALLW, exp_attnd=FA_ATTND_ALLW,
                in_norm=OT_NS_NORM, in_dbl=OT_NS_DBL, in_trpl=OT_NS_TRPL,
                in_hol=OT_NS_HOL, nopay_days=NOPAY_NS,
            )
        else:
            self._check_generic_batch()

    def _check_slip(self, *, slip_id, label, wage,
                    exp_norm, exp_dbl, exp_trpl, exp_nopay,
                    exp_spec, exp_ldr, exp_attnd,
                    in_norm, in_dbl, in_trpl, in_hol, nopay_days):
        if not slip_id:
            self.warn(f'{label}: payslip not created — skipping'); return

        _info(f'\n  -- {label}  slip id={slip_id} --')
        state = (self.o.search('hr.payslip', [('id', '=', slip_id)],
                               fields=['state'], limit=1) or [{}])[0].get('state', '?')
        self.check(state in ('done', 'draft'),
                   f'{label}: state = {state}',
                   f'{label}: state = {state} (expected done/draft)')

        inputs = self._get_inputs(slip_id)
        lines  = self._get_lines(slip_id)

        if not lines:
            self.fail(f'{label}: no salary lines — run compute_sheet() first'); return

        # Inputs
        _info('  Inputs:')
        for code in sorted(inputs):
            _info(f'    [{code:16s}]  {inputs[code]:>13,.3f}')

        self._chk_inp(inputs, 'NORM_OT_HRS', in_norm, f'{label} NORM_OT_HRS')
        if in_dbl  is not None: self._chk_inp(inputs, 'DBL_OT_HRS',  in_dbl,  f'{label} DBL_OT_HRS')
        if in_trpl is not None: self._chk_inp(inputs, 'TRPL_OT_HRS', in_trpl, f'{label} TRPL_OT_HRS')
        self._chk_inp(inputs, 'HOL_HRS', in_hol, f'{label} HOL_HRS')

        # NOPAY — informational (from validated leaves via _get_no_pay_count)
        nopay_info = inputs.get('NOPAY')
        if nopay_info is not None:
            _info(f'  {label}: NOPAY (info) = {nopay_info} day(s) [from validated leaves]')
        else:
            self.warn(f'{label}: NOPAY input not found — no validated no-pay leaves?')

        # NOPAY_DED — from contract fixed deduction, feeds the salary rule formula
        nd = inputs.get('NOPAY_DED')
        if nd is not None:
            self.near(abs(nd), nopay_days,
                      f'{label} NOPAY_DED input (days from fixed deduction)')
        else:
            self.fail(
                f'{label}: NOPAY_DED input not found. '
                f'Add a fixed deduction (type=NOPAY_DED, amount={nopay_days} days) '
                f'to the contract so the salary rule can compute.'
            )

        # Salary lines
        _info('  Rule lines:')
        for code in sorted(lines):
            _info(f'    [{code:16s}]  {lines[code]:>14,.2f}')

        self._chk_line(lines, 'BAFF_BASIC', wage, f'{label} BAFF_BASIC')
        self._chk_line(lines, 'NORM_OT_AMT', exp_norm, f'{label} NORM_OT_AMT')
        if exp_dbl  is not None: self._chk_line(lines, 'DBL_OT_AMT',  exp_dbl,  f'{label} DBL_OT_AMT')
        if exp_trpl is not None: self._chk_line(lines, 'TRPL_OT_AMT', exp_trpl, f'{label} TRPL_OT_AMT')
        self._chk_nonzero(lines, 'HOL_AMT', f'{label} HOL_AMT')    # daily formula; just check non-zero

        if exp_spec is not None: self._chk_line(lines, 'SPEC_INCNTV', exp_spec, f'{label} SPEC_INCNTV')
        if exp_ldr  is not None: self._chk_line(lines, 'LDR_ALLW',    exp_ldr,  f'{label} LDR_ALLW')
        self._chk_line(lines, 'ATTND_ALLW', exp_attnd, f'{label} ATTND_ALLW')

        div = '30' if exp_spec else '26'
        self._chk_line(lines, 'NOPAY_DED', exp_nopay, f'{label} NOPAY_DED (days x wage/{div})')

        epf = lines.get('EPF_EE_8')
        if epf is not None:
            self.check(epf < 0,
                       f'{label} EPF_EE_8 is negative (deduction): {epf:,.2f}',
                       f'{label} EPF_EE_8 is not negative — check formula')

        g = lines.get('BAFF_GROSS', 0)
        b = lines.get('BAFF_BASIC', 0)
        self.check(g >= b,
                   f'{label} BAFF_GROSS ({g:,.2f}) >= BAFF_BASIC ({b:,.2f})',
                   f'{label} BAFF_GROSS ({g:,.2f}) < BAFF_BASIC ({b:,.2f})')
        self._net_sanity(lines, label)

    def _check_generic_batch(self):
        batches = self.o.search('hr.payslip.run', [],
                                fields=['name', 'date_start', 'state'],
                                limit=1, order='date_start desc')
        if not batches:
            self.warn('No payroll batches found'); return
        batch = batches[0]
        _info(f'Most recent batch: {batch["name"]}  state={batch["state"]}')
        slips = self.o.search(
            'hr.payslip',
            [('payslip_run_id', '=', batch['id']), ('state', '=', 'done')],
            fields=['name'], limit=1)
        if not slips:
            self.warn('No confirmed payslips in batch — confirm first'); return
        _info(f'Sample payslip: {slips[0]["name"]}')
        lines = self._get_lines(slips[0]['id'])
        for code in ('BAFF_BASIC', 'BAFF_GROSS', 'NOPAY_DED',
                     'EPF_EE_8', 'TOT_DED', 'BAFF_NET'):
            v = lines.get(code)
            if v is not None:
                self.ok(f'Line [{code}] = {v:,.2f}')
            else:
                self.warn(f'Line [{code}] not found in payslip')
        self._net_sanity(lines, slips[0]['name'])

    # =========================================================================
    # Phase 5 — Salary Sheet Wizard
    # =========================================================================
    def phase5_wizard(self):
        _head('Phase 5 — Salary Sheet Wizard')

        wiz = self.o.search('ir.model', [('model', '=', 'hr.salary.sheet.wizard')],
                            fields=['id', 'name'])
        if not wiz:
            self.fail("Wizard model not found"); return
        self.ok(f'Wizard model: {wiz[0]["name"]}')

        actions = self.o.search('ir.actions.act_window',
                                [('res_model', '=', 'hr.salary.sheet.wizard')],
                                fields=['name', 'target'])
        self.check(bool(actions),
                   f'Wizard act_window: {actions[0]["name"] if actions else ""}',
                   'No ir.actions.act_window for wizard')
        if actions:
            self.check(actions[0].get('target') == 'new',
                       "Wizard target='new' (dialog)",
                       f"Wizard target='{actions[0].get('target')}' — expected 'new'")

        for name, hint in (('Custom Reports', 'Payroll > Reporting'),
                            ('Salary Sheet',   'Custom Reports')):
            rows = self.o.search('ir.ui.menu', [('name', '=', name)],
                                 fields=['complete_name'])
            self.check(bool(rows),
                       f'Menu "{name}": {rows[0]["complete_name"] if rows else ""}',
                       f'Menu "{name}" not found (expected under {hint})')

        try:
            wf = self.o.call('hr.salary.sheet.wizard', 'fields_get',
                             ['payslip_run_id', 'employee_category'])
            self.check('payslip_run_id' in wf,
                       'Wizard.payslip_run_id accessible',
                       'Wizard.payslip_run_id not found')
            self.check('employee_category' in wf,
                       'Wizard.employee_category accessible',
                       'Wizard.employee_category not found')
            if 'employee_category' in wf:
                choices = {k for k, _ in (wf['employee_category'].get('selection') or [])}
                self.check({'staff', 'non_staff'} <= choices,
                           f'Wizard category choices: {sorted(choices)}',
                           f'Wizard category missing staff/non_staff: {choices}')
        except Exception as exc:
            self.fail(f'Cannot read wizard fields: {exc}')

        if self.sample and self.sample.batch_id:
            for cat, lbl in (('staff', 'Staff'), ('non_staff', 'Non-Staff')):
                try:
                    wid = self.o.create('hr.salary.sheet.wizard', {
                        'payslip_run_id':    self.sample.batch_id,
                        'employee_category': cat,
                    })
                    self.ok(f'Wizard record created for {lbl} category (id={wid})')
                    try: self.o.call('hr.salary.sheet.wizard', 'unlink', [[wid]])
                    except Exception: pass
                except Exception as exc:
                    self.fail(f'Could not create wizard record for {lbl}: {exc}')

    # =========================================================================
    # Summary + runner
    # =========================================================================
    def summary(self):
        _head('Summary')
        total = self.passed + self.failed + self.warned
        print(
            _c('92', f'  PASS : {self.passed:3d}') + '  ' +
            _c('91', f'FAIL : {self.failed:3d}') + '  ' +
            _c('93', f'WARN : {self.warned:3d}') + '  ' +
            f'TOTAL: {total}'
        )
        if self.failed:
            print(_c('91', '\n  One or more checks FAILED — review the output above.'))
        elif self.warned:
            print(_c('93', '\n  All checks passed with warnings.'))
        else:
            print(_c('92', '\n  All checks PASSED.'))
        return self.failed

    def run(self):
        self.phase1_data_integrity()
        self.phase2_employees_contracts()
        self.phase3_attendance_leaves()
        self.phase4_payslip_computation()
        self.phase5_wizard()
        return self.summary()


# =============================================================================
# CLI
# =============================================================================
def _parse_args():
    p = argparse.ArgumentParser(
        description='Ocean Voyager payroll validator with sample data builder.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument('--url',          default=DEFAULT_URL)
    p.add_argument('--db',           default=DEFAULT_DB)
    p.add_argument('--user',         default=DEFAULT_USER)
    p.add_argument('--password',     default=DEFAULT_PASSWORD)
    p.add_argument('--skip-sample',  action='store_true',
                   help='Skip sample data creation — check existing data only')
    p.add_argument('--cleanup',      action='store_true',
                   help='Delete tagged sample records after checks complete')
    p.add_argument('--cleanup-only', action='store_true',
                   help='Delete all tagged records and exit (no checks run)')
    p.add_argument('--no-color',     action='store_true')
    return p.parse_args()


def main():
    global USE_COLOR
    args = _parse_args()
    if args.no_color:
        USE_COLOR = False

    odoo = Odoo(args.url, args.db, args.user, args.password)

    if args.cleanup_only:
        SampleDataCreator.cleanup_by_tag(odoo)
        sys.exit(0)

    sample = None
    if not args.skip_sample:
        sample = SampleDataCreator(odoo).build()

    checker  = PayrollChecker(odoo, sample=sample)
    failures = checker.run()

    if args.cleanup and sample:
        sample.cleanup()

    sys.exit(failures)


if __name__ == '__main__':
    main()
