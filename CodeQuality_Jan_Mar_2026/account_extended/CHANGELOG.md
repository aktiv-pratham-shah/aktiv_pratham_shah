# Changelog

## [19.0.1.0.0] - 2026-04-03

### Added
- **Follow-up Report Enhancement**:
    -   Dynamic injection of unpaid invoices summary table into follow-up emails and PDFs.
    -   Automatic "Grand Total" calculation with intelligent currency symbol detection.
    -   Smart placement of the summary table before closing signatures.
- **Weekly Due Invoices Automation**:
    -   New cron job `_cron_send_weekly_due_invoices` for automated weekly reporting.
    -   Individualized emails for each salesperson containing their customers' unpaid invoices.
    -   Master summary email for directors containing all overdue invoices globally.
    -   Automatic conversion of multi-currency amounts to INR for standardized reporting.

### Changed
- **Account Follow-up Logic**:
    -   Forced explicit currency symbols (e.g., €, $) to appear on report lines even for the company's base currency.
    -   Improved column mapping for follow-up report lines to ensure consistency with PDF outputs.
