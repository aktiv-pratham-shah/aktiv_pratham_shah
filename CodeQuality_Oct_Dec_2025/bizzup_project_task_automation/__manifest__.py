# Copyright (C) Gilliam Management Services and Information Systems, Ltd. (the owner of Bizzup), 2021, 2022, 2023, 2024, 2025
# All Rights Reserved to Gilliam Management Services and Information Systems, Ltd.
# Unauthorized copying, editing or printing of this file, in any way is strictly prohibited
# Proprietary and confidential for more information, please contact
# lg@bizzup.app

{
    "name": "Bizzup Project Task Automation",
    "summary": "Automatic Task Date Updates from PO, MO, and Delivery Orders",
    "description": """
    Automatic Project Task Date Tracking
    =====================================
    
    This module automatically updates project task planned dates based on related:
    - Purchase Orders (PO)
    - Manufacturing Orders (MO)
    - Delivery Orders (DO)
    
    Features:
    ---------
    * Auto-update Purchasing task dates from Purchase Orders
    * Auto-update Production task dates from Manufacturing Orders
    * Auto-update Delivery task dates from Delivery Orders
    * Real-time synchronization when orders are created/confirmed
    * Link orders to projects via Analytic Account
    
    Configuration:
    --------------
    1. Enable automation flags on tasks (Purchasing/Production/Delivery)
    2. Link PO/MO/DO to project's analytic account
    3. Dates update automatically when orders are created/confirmed
    
    Date Logic:
    -----------
    - Start Date: Earliest order date from all related orders
    - End Date: Latest order date from all related orders
    - Updates in real-time when orders change
    """,
    "version": "18.0.1.0.0",
    "category": "Project",
    "license": "Other proprietary",
    "author": "Gilliam Management Services and Information Systems, Ltd.",
    "website": "www.bizzup.app",
    "depends": [
        'project',
        'purchase',
        'mrp',
        'stock',
    ],
    "data": [
        "views/project_task_views.xml",
        "views/stock_picking_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
