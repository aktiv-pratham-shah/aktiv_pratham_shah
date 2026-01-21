# Biuld ASCII Report for Vendo bill

### Technical Name: vander_bill_ascii_report

### ['18.0.1.0.1'] - 2024-12-03 | US-02

- Ticket HT01194.
- changed the report to generate vendor payments.

### ['18.0.1.0.2'] - 2024-12-03 | US-02

- Ticket HT01194.
- New CR.
- Changed the report to print from start date and end date.
- Removed minus(-) sign before the amount.

### ['18.0.1.1.0] - 2025-01-17 | US - 04

- Ticket HT01194 | Fourth Stage
- New CR
- Changed the domain in the search of account.payment.
- Added new One2Many field in res.company.
- Added View for the new field.
- Added new Many2one in wizard to select the Masav No.
- Made changes to code of report vals.


### ['18.0.1.7.1'] - 2025-07-30 | HT01922

- Masav report for one currency.

### ['18.0.2.6.1'] - 2025-07-31 | HT01851

- The MASV report will be grouped first by Payment Date, then by Vendor.
- Added a new Many2many field added in report wizard to allow vendor selection.
- When the user selects a date range, the system will show only the vendors with payments in that range.
- The user can then choose from these vendors, and the report will include only the payments for the selected vendors within the specified dates.
