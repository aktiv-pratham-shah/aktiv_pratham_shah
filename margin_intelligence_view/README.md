# 📔 Margin Intelligence View - Project Documentation

**Module Name**: `margin_intelligence_view`  
**Version**: 1.0.0 (Odoo 18)  
**Objective**: Transform Odoo from a revenue-tracking system into a profit-maximizing engine.

---

## 🚀 1. Core Dashboard Features
The **Margin Intelligence Dashboard** is the central hub for analyzing profitability. It can be accessed via `Sales ➔ Reporting ➔ Margin Intelligence` or `Purchase ➔ Reporting ➔ Margin Intelligence`.

### 📊 KPI Cards (High-Level Summary)
Instantly see your financial health across 5 key metrics:
*   **Avg Margin %**: The overall percentage of profit across all selected orders.
*   **Health Counts (Good/Warning/Critical)**: A count of items that are healthy (>=30%), in the warning zone (10-30%), or bleeding profit (<10%).
*   **Total Margin Amount**: The actual dollar value of profit earned.

### 🏆 Top/Bottom 5 Performers (New!)
A dedicated section that identifies:
*   **Top 5 Products**: Your most profitable items (high-margin "Winners").
*   **Bottom 5 Products**: Your least profitable items (loss-making "Losers").

### 📅 Margin Trends (New!)
Every line in the data table now features a **Historical Trend Icon**:
*   **⬆️ Green Arrow**: Current margin is **higher** than the product's last 30-day average.
*   **⬇️ Red Arrow**: Current margin has **declined** compared to history.

### 🗂️ Analysis Tools
*   **Group by Category**: A purple toggle that instantly organizes the entire table by "Product Category" with category-specific averages.
*   **Excel Export**: A green button to download the current view as a ready-to-use CSV file for management reporting.
*   **Sorting & Filtering**: Click any table header to sort by price, cost, or margin.

---

## 🛡️ 2. The Profit Guard (Margin Protection)
*   **Setup**: Navigate to `Sales ➔ Configuration ➔ Settings` and set your **Minimum Margin (%)**.
*   **Enforcement**: If a salesperson attempts to **Confirm** a Sale Order where any line item falls below that percentage, Odoo will **block the transaction**.

---

## 🏅 3. Profit-Based Commission Engine
*   **Formula**: `Total Margin (Profit) * Commission Rate (%)`.
*   **User Setup**: Assign a unique **Commission Rate** under `Settings ➔ Users ➔ Mitchell Admin ➔ Margin & Commissions`.
*   **Invisible Tracking**: "Projected Commission" is visible on every Quotation form.

---

## 🖥️ 4. Technical Architecture
*   **Component**: `MarginDashboard` (OWL action client).
*   **Data Engine**: Optimized `margin.intelligence` (Abstract Model) with batch trend analysis.
*   **Dependencies**: `sale_management`, `purchase`, `stock`.

---
*Created by **Pratham Shah** for Odoo 18.*
