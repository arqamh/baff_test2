# Test Cases: Same-Day Overtime Calculation with Non-Working Day Start Time

**Module**: `baff_hr_overtime_extend`
**Feature**: Non-Working Day Start Time Configuration
**Test Type**: Functional Testing
**Test Focus**: Same-Day Overtime Calculation
**Version**: 16.0.1.0.0
**Date**: 2025-11-18

---

## Overview

This document contains test cases to verify that overtime calculations for non-working days (public holidays, mercantile holidays, and weekends) correctly apply the configured start time when calculating worked hours.

### Key Business Rule

When an employee checks in **before** the configured "Non Working Day Start Time":
- Overtime calculation should start from the **configured start time**, not the actual check-in time

When an employee checks in **on or after** the configured start time:
- Overtime calculation should start from the **actual check-in time**

---

## Prerequisites

Before starting the tests, ensure the following configuration is in place:

1. **Company Setup**
   - Company created with overtime configuration enabled
   - Roundup overtime interval configured (e.g., 0.25 for 15 minutes)

2. **Work Entry Types**
   - Public Holiday work entry type with `holiday_mapping = 'public'`
   - Mercantile Holiday work entry type with `holiday_mapping = 'mercantile'`

3. **Resource Calendar**
   - Standard working week configured (e.g., Monday to Friday, 9:00 AM - 5:00 PM)
   - Weekends (Saturday and Sunday) not scheduled

4. **Overtime Template**
   - Template created with:
     - **Non Working Day Start Time** = `8:00 AM` (8.0)
     - Rules configured for:
       - Public Holidays → Holiday Hours
       - Mercantile Holidays → Double Overtime
       - Weekends → Triple Overtime

5. **Employee Setup**
   - Employee with active contract
   - Contract linked to the overtime template
   - Employee assigned to the resource calendar

---

## Test Cases

### Test Case 1: Public Holiday - Check-in Before Start Time

**Test ID**: TC_OT_PH_001
**Priority**: High
**Type**: Positive Test

#### Test Data
- **Date**: Select a date configured as a Public Holiday (Monday-Friday)
- **Configured Start Time**: 8:00 AM
- **Check-in Time**: 7:00 AM
- **Check-out Time**: 5:00 PM (17:00)

#### Test Steps
1. Navigate to **Attendances** module
2. Create new attendance record:
   - Select the test employee
   - Set check-in date/time to a public holiday at **7:00 AM**
   - Set check-out date/time to the same day at **5:00 PM**
3. Save the attendance record
4. Verify the computed overtime fields

#### Expected Results
- **Holiday Hours**: `9.0` hours (calculated from 8:00 AM to 5:00 PM)
- **Normal Overtime**: `0.0`
- **Double Overtime**: `0.0`
- **Triple Overtime**: `0.0`
- **Calculation Logic**: System should ignore the 7:00 AM check-in and calculate from 8:00 AM

#### Actual Results
| Field | Expected | Actual | Pass/Fail |
|-------|----------|--------|-----------|
| Holiday Hours | 9.0 | | |
| Normal Overtime | 0.0 | | |
| Double Overtime | 0.0 | | |
| Triple Overtime | 0.0 | | |

**Remarks**:
_[QA to fill in any observations or issues]_

---

### Test Case 2: Public Holiday - Check-in After Start Time

**Test ID**: TC_OT_PH_002
**Priority**: High
**Type**: Positive Test

#### Test Data
- **Date**: Select a date configured as a Public Holiday (Monday-Friday)
- **Configured Start Time**: 8:00 AM
- **Check-in Time**: 9:00 AM
- **Check-out Time**: 5:00 PM (17:00)

#### Test Steps
1. Navigate to **Attendances** module
2. Create new attendance record:
   - Select the test employee
   - Set check-in date/time to a public holiday at **9:00 AM**
   - Set check-out date/time to the same day at **5:00 PM**
3. Save the attendance record
4. Verify the computed overtime fields

#### Expected Results
- **Holiday Hours**: `8.0` hours (calculated from 9:00 AM to 5:00 PM)
- **Normal Overtime**: `0.0`
- **Double Overtime**: `0.0`
- **Triple Overtime**: `0.0`
- **Calculation Logic**: System should use the actual check-in time of 9:00 AM

#### Actual Results
| Field | Expected | Actual | Pass/Fail |
|-------|----------|--------|-----------|
| Holiday Hours | 8.0 | | |
| Normal Overtime | 0.0 | | |
| Double Overtime | 0.0 | | |
| Triple Overtime | 0.0 | | |

**Remarks**:
_[QA to fill in any observations or issues]_

---

### Test Case 3: Mercantile Holiday - Check-in Before Start Time

**Test ID**: TC_OT_MH_001
**Priority**: High
**Type**: Positive Test

#### Test Data
- **Date**: Select a date configured as a Mercantile Holiday
- **Configured Start Time**: 8:00 AM
- **Check-in Time**: 6:30 AM
- **Check-out Time**: 4:00 PM (16:00)

#### Test Steps
1. Navigate to **Attendances** module
2. Create new attendance record:
   - Select the test employee
   - Set check-in date/time to a mercantile holiday at **6:30 AM**
   - Set check-out date/time to the same day at **4:00 PM**
3. Save the attendance record
4. Verify the computed overtime fields

#### Expected Results
- **Holiday Hours**: `0.0`
- **Normal Overtime**: `0.0`
- **Double Overtime**: `8.0` hours (calculated from 8:00 AM to 4:00 PM)
- **Triple Overtime**: `0.0`
- **Calculation Logic**: System should ignore the 6:30 AM check-in and calculate from 8:00 AM

#### Actual Results
| Field | Expected | Actual | Pass/Fail |
|-------|----------|--------|-----------|
| Holiday Hours | 0.0 | | |
| Normal Overtime | 0.0 | | |
| Double Overtime | 8.0 | | |
| Triple Overtime | 0.0 | | |

**Remarks**:
_[QA to fill in any observations or issues]_

---

### Test Case 4: Mercantile Holiday - Check-in After Start Time

**Test ID**: TC_OT_MH_002
**Priority**: High
**Type**: Positive Test

#### Test Data
- **Date**: Select a date configured as a Mercantile Holiday
- **Configured Start Time**: 8:00 AM
- **Check-in Time**: 10:00 AM
- **Check-out Time**: 6:00 PM (18:00)

#### Test Steps
1. Navigate to **Attendances** module
2. Create new attendance record:
   - Select the test employee
   - Set check-in date/time to a mercantile holiday at **10:00 AM**
   - Set check-out date/time to the same day at **6:00 PM**
3. Save the attendance record
4. Verify the computed overtime fields

#### Expected Results
- **Holiday Hours**: `0.0`
- **Normal Overtime**: `0.0`
- **Double Overtime**: `8.0` hours (calculated from 10:00 AM to 6:00 PM)
- **Triple Overtime**: `0.0`
- **Calculation Logic**: System should use the actual check-in time of 10:00 AM

#### Actual Results
| Field | Expected | Actual | Pass/Fail |
|-------|----------|--------|-----------|
| Holiday Hours | 0.0 | | |
| Normal Overtime | 0.0 | | |
| Double Overtime | 8.0 | | |
| Triple Overtime | 0.0 | | |

**Remarks**:
_[QA to fill in any observations or issues]_

---

### Test Case 5: Weekend (Saturday) - Check-in Before Start Time

**Test ID**: TC_OT_WE_001
**Priority**: High
**Type**: Positive Test

#### Test Data
- **Date**: Select a Saturday (non-scheduled day)
- **Configured Start Time**: 8:00 AM
- **Check-in Time**: 7:30 AM
- **Check-out Time**: 3:30 PM (15:30)

#### Test Steps
1. Navigate to **Attendances** module
2. Create new attendance record:
   - Select the test employee
   - Set check-in date/time to a Saturday at **7:30 AM**
   - Set check-out date/time to the same day at **3:30 PM**
3. Save the attendance record
4. Verify the computed overtime fields

#### Expected Results
- **Holiday Hours**: `0.0`
- **Normal Overtime**: `0.0`
- **Double Overtime**: `0.0`
- **Triple Overtime**: `7.5` hours (calculated from 8:00 AM to 3:30 PM)
- **Calculation Logic**: System should ignore the 7:30 AM check-in and calculate from 8:00 AM

#### Actual Results
| Field | Expected | Actual | Pass/Fail |
|-------|----------|--------|-----------|
| Holiday Hours | 0.0 | | |
| Normal Overtime | 0.0 | | |
| Double Overtime | 0.0 | | |
| Triple Overtime | 7.5 | | |

**Remarks**:
_[QA to fill in any observations or issues]_

---

### Test Case 6: Weekend (Sunday) - Check-in After Start Time

**Test ID**: TC_OT_WE_002
**Priority**: High
**Type**: Positive Test

#### Test Data
- **Date**: Select a Sunday (non-scheduled day)
- **Configured Start Time**: 8:00 AM
- **Check-in Time**: 11:00 AM
- **Check-out Time**: 7:00 PM (19:00)

#### Test Steps
1. Navigate to **Attendances** module
2. Create new attendance record:
   - Select the test employee
   - Set check-in date/time to a Sunday at **11:00 AM**
   - Set check-out date/time to the same day at **7:00 PM**
3. Save the attendance record
4. Verify the computed overtime fields

#### Expected Results
- **Holiday Hours**: `0.0`
- **Normal Overtime**: `0.0`
- **Double Overtime**: `0.0`
- **Triple Overtime**: `8.0` hours (calculated from 11:00 AM to 7:00 PM)
- **Calculation Logic**: System should use the actual check-in time of 11:00 AM

#### Actual Results
| Field | Expected | Actual | Pass/Fail |
|-------|----------|--------|-----------|
| Holiday Hours | 0.0 | | |
| Normal Overtime | 0.0 | | |
| Double Overtime | 0.0 | | |
| Triple Overtime | 8.0 | | |

**Remarks**:
_[QA to fill in any observations or issues]_

---

### Test Case 7: Check-in Exactly at Start Time

**Test ID**: TC_OT_EDGE_001
**Priority**: Medium
**Type**: Boundary Test

#### Test Data
- **Date**: Select a Saturday (non-scheduled day)
- **Configured Start Time**: 8:00 AM
- **Check-in Time**: 8:00 AM (exactly)
- **Check-out Time**: 4:00 PM (16:00)

#### Test Steps
1. Navigate to **Attendances** module
2. Create new attendance record:
   - Select the test employee
   - Set check-in date/time to a Saturday at **8:00 AM** (exactly)
   - Set check-out date/time to the same day at **4:00 PM**
3. Save the attendance record
4. Verify the computed overtime fields

#### Expected Results
- **Holiday Hours**: `0.0`
- **Normal Overtime**: `0.0`
- **Double Overtime**: `0.0`
- **Triple Overtime**: `8.0` hours (calculated from 8:00 AM to 4:00 PM)
- **Calculation Logic**: System should use the check-in time as it matches the configured start time

#### Actual Results
| Field | Expected | Actual | Pass/Fail |
|-------|----------|--------|-----------|
| Holiday Hours | 0.0 | | |
| Normal Overtime | 0.0 | | |
| Double Overtime | 0.0 | | |
| Triple Overtime | 8.0 | | |

**Remarks**:
_[QA to fill in any observations or issues]_

---

### Test Case 8: No Configured Start Time (Default Behavior)

**Test ID**: TC_OT_EDGE_002
**Priority**: Medium
**Type**: Negative Test

#### Test Data
- **Date**: Select a Saturday (non-scheduled day)
- **Configured Start Time**: Not set / 0:00 AM (0.0)
- **Check-in Time**: 7:00 AM
- **Check-out Time**: 5:00 PM (17:00)

#### Test Steps
1. Navigate to **HR > Configuration > Overtime Templates**
2. Edit the overtime template
3. Clear/set the **Non Working Day Start Time** field to `0:00` or leave blank
4. Save the template
5. Navigate to **Attendances** module
6. Create new attendance record:
   - Select the test employee
   - Set check-in date/time to a Saturday at **7:00 AM**
   - Set check-out date/time to the same day at **5:00 PM**
7. Save the attendance record
8. Verify the computed overtime fields

#### Expected Results
- **Holiday Hours**: `0.0`
- **Normal Overtime**: `0.0`
- **Double Overtime**: `0.0`
- **Triple Overtime**: `10.0` hours (calculated from actual check-in 7:00 AM to 5:00 PM)
- **Calculation Logic**: When no start time is configured, system should use actual check-in time

#### Actual Results
| Field | Expected | Actual | Pass/Fail |
|-------|----------|--------|-----------|
| Holiday Hours | 0.0 | | |
| Normal Overtime | 0.0 | | |
| Double Overtime | 0.0 | | |
| Triple Overtime | 10.0 | | |

**Remarks**:
_[QA to fill in any observations or issues]_

---

### Test Case 9: Multiple Attendance Records Same Day

**Test ID**: TC_OT_EDGE_003
**Priority**: Low
**Type**: Positive Test

#### Test Data
- **Date**: Select a public holiday
- **Configured Start Time**: 8:00 AM
- **First Check-in**: 7:00 AM, **First Check-out**: 12:00 PM
- **Second Check-in**: 1:00 PM, **Second Check-out**: 6:00 PM

#### Test Steps
1. Navigate to **Attendances** module
2. Create first attendance record:
   - Check-in: Public holiday at **7:00 AM**
   - Check-out: Same day at **12:00 PM**
3. Create second attendance record:
   - Check-in: Same public holiday at **1:00 PM**
   - Check-out: Same day at **6:00 PM**
4. Verify both computed overtime fields

#### Expected Results
- **First Attendance Holiday Hours**: `4.0` hours (from 8:00 AM to 12:00 PM)
- **Second Attendance Holiday Hours**: `5.0` hours (from 1:00 PM to 6:00 PM)
- **Total for Day**: `9.0` hours
- **Calculation Logic**: Each attendance is calculated independently

#### Actual Results
| Attendance | Field | Expected | Actual | Pass/Fail |
|------------|-------|----------|--------|-----------|
| First | Holiday Hours | 4.0 | | |
| Second | Holiday Hours | 5.0 | | |

**Remarks**:
_[QA to fill in any observations or issues]_

---

## Test Execution Summary

**Total Test Cases**: 9
**Passed**: ___
**Failed**: ___
**Blocked**: ___
**Not Executed**: ___

### Critical Issues Found
_[QA to document any critical issues]_

### Observations
_[QA to document general observations]_

---

## Sign-off

**Tested By**: ________________________
**Date**: ________________________
**Approved By**: ________________________
**Date**: ________________________

---

## Appendix: Configuration Screenshots

### A. Overtime Template Configuration
_[QA to attach screenshot showing Non Working Day Start Time field set to 8:00]_

### B. Resource Calendar Configuration
_[QA to attach screenshot showing work schedule (Mon-Fri)]_

### C. Holiday Configuration
_[QA to attach screenshot showing public/mercantile holiday setup]_

### D. Sample Attendance Record
_[QA to attach screenshot of a sample attendance with overtime calculations]_
