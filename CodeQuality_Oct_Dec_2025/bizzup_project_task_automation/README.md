# Bizzup Project Task Automation

## Overview

This module automatically updates project task planned dates based on related **Purchase Orders (PO)**, **Manufacturing Orders (MO)**, and **Delivery Orders (DO)** linked via the project's analytic account.

## Purpose

Eliminate manual task date updates by automatically synchronizing task timelines with actual order dates from purchasing, production, and delivery operations.

---

## Features

### **Automatic Date Synchronization**

Three types of tasks can auto-update their planned dates:

| Task Type | Source | Date Field Used | Trigger Events |
|-----------|--------|-----------------|----------------|
| **Purchasing** | Purchase Orders | `date_order` (Order Date) | PO create, confirm, modify |
| **Production** | Manufacturing Orders | `create_date` (Creation Date) | MO create, plan, modify |
| **Delivery** | Delivery Orders | `scheduled_date` (Scheduled Date) | DO create, validate, modify |

### **Date Calculation Logic**

- **Start Date**: Earliest date from all related orders
- **End Date**: Latest date from all related orders
- **Updates**: Real-time when orders are created/confirmed/modified

---

## Configuration

### **Step 1: Enable Task Automation**

1. Open a **Project Task**
2. Go to **Automation** tab
3. Enable one or more flags:
   - ☑ **Auto-Update Purchasing Dates**
   - ☑ **Auto-Update Production Dates**
   - ☑ **Auto-Update Delivery Dates**

### **Step 2: Link Orders to Project**

All orders must be linked to the project's **Analytic Account**:

#### **For Purchase Orders:**
1. Open Purchase Order
2. Set **Project Analytic Account** field
3. Confirm PO → Purchasing task dates update automatically

#### **For Manufacturing Orders:**
1. Open Manufacturing Order
2. Set **Analytic Account** field (standard Odoo field)
3. Plan/Confirm MO → Production task dates update automatically

#### **For Delivery Orders:**
1. Open Delivery Order (outgoing only)
2. Set **Project Analytic Account** field
3. Validate DO → Delivery task dates update automatically

---

## Usage Example

### **Scenario: Full Project Workflow**

**Initial Setup:**
```
Project: "Product Launch 2025"
Analytic Account: "PROJ-2025-001"
Tasks:
  - Purchasing (Auto-Update Purchasing Dates: ✓)
  - Production (Auto-Update Production Dates: ✓)
  - Delivery (Auto-Update Delivery Dates: ✓)
```

**Step 1: Create Purchase Orders**
```
PO-001: Order Date = 2025-01-10, Analytic Account = PROJ-2025-001
PO-002: Order Date = 2025-01-15, Analytic Account = PROJ-2025-001
PO-003: Order Date = 2025-01-20, Analytic Account = PROJ-2025-001

→ Purchasing Task Updates:
  Start Date: 2025-01-10 (earliest PO)
  End Date: 2025-01-20 (latest PO)
```

**Step 2: Create Manufacturing Orders**
```
MO-001: Created = 2025-01-25, Analytic Account = PROJ-2025-001
MO-002: Created = 2025-02-05, Analytic Account = PROJ-2025-001

→ Production Task Updates:
  Start Date: 2025-01-25 (earliest MO)
  End Date: 2025-02-05 (latest MO)
```

**Step 3: Create Delivery Orders**
```
DO-001: Scheduled = 2025-02-15, Analytic Account = PROJ-2025-001
DO-002: Scheduled = 2025-02-20, Analytic Account = PROJ-2025-001

→ Delivery Task Updates:
  Start Date: 2025-02-15 (earliest DO)
  End Date: 2025-02-20 (latest DO)
```

---

## 🔍 Technical Details

### **Models Extended**

| Model | New Fields | Methods Overridden |
|-------|------------|-------------------|
| `project.task` | `is_auto_purchasing_task`<br>`is_auto_production_task`<br>`is_auto_delivery_task` | `_update_task_dates_from_orders()` |
| `purchase.order` | `account_id` | `create()`, `write()`, `button_confirm()` |
| `mrp.production` | *(uses existing `analytic_account_id`)* | `create()`, `write()`, `button_plan()` |
| `stock.picking` | `analytic_account_id` | `create()`, `write()`, `button_validate()` |

### **Update Flow**

```
Order Created/Modified
    ↓
Check if analytic_account_id exists
    ↓
Find project(s) with same analytic account
    ↓
Find tasks with automation flag enabled
    ↓
Calculate min/max dates from all related orders
    ↓
Update task.date_start and task.date_end
```

### **Important Notes**

- Only **confirmed** Purchase Orders (`state` in `['purchase', 'done']`) are considered
- Only **outgoing** deliveries (`picking_type_code = 'outgoing'`) update Delivery tasks
- Manufacturing Orders use **creation date**, not planned/scheduled dates
- Tasks can have multiple automation flags enabled simultaneously
- Updates are **real-time** (not scheduled/batch)

---

## UI Enhancements

### **Task Form View**
- New **Automation** tab with:
  - Toggle switches for each automation type
  - Helpful information panel explaining how it works

### **Task List View**
- Optional columns for automation flags
- Boolean toggle widgets for quick enable/disable

### **Task Search/Filters**
- Filter by "Auto Purchasing Tasks"
- Filter by "Auto Production Tasks"
- Filter by "Auto Delivery Tasks"

### **Purchase Order Views**
- Analytic Account field visible in form and list
- Filter: "With Project Link"

### **Delivery Order Views**
- Analytic Account field (only for outgoing deliveries)
- Filter: "With Project Link"

---
##  License

**Other proprietary**

Copyright © 2025 Gilliam Management Services and Information Systems, Ltd.  
All Rights Reserved

Unauthorized copying, editing, or printing of this software is strictly prohibited.

---

### **Version 18.0.1.0.0**
- Initial release
- Auto-update Purchasing task dates from POs
- Auto-update Production task dates from MOs
- Auto-update Delivery task dates from DOs
- Real-time synchronization
- Comprehensive UI enhancements
