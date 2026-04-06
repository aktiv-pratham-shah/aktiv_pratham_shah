/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

/**
 * MarginDashboard Component
 * Provides a clean and stable visualization of profit margins.
 * Matches original functionality before filtration updates.
 */
export class MarginDashboard extends Component {
    static template = "margin_intelligence_view.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            activeTab: 'sale',
            filter: 'all',  // Simple health filter
            lines: [],
            loading: true,
            kpis: {
                avgMargin: 0,
                goodCount: 0,
                warningCount: 0,
                criticalCount: 0,
                totalMargin: 0,
                top5: [],
                bottom5: []
            },
            sortField: 'margin_pct',
            sortOrder: 'desc',
            groupByCategory: false
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    /**
     * Data Retrieval logic
     */
    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "margin.intelligence",
                "get_dashboard_data",
                [this.state.activeTab]
            );
            this.state.lines = data || [];
            this.updateKPIs();
        } catch (error) {
            console.error("Dashboard data load failed:", error);
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Metric Calculations
     */
    updateKPIs() {
        const lines = this.state.lines;
        if (!lines || !lines.length) {
            this.state.kpis = { avgMargin: 0, goodCount: 0, warningCount: 0, criticalCount: 0, totalMargin: 0, top5: [], bottom5: [] };
            return;
        }

        const totalMarginPct = lines.reduce((sum, line) => sum + line.margin_pct, 0);
        this.state.kpis.avgMargin = (totalMarginPct / lines.length).toFixed(2);
        this.state.kpis.goodCount = lines.filter(l => l.health === 'good').length;
        this.state.kpis.warningCount = lines.filter(l => l.health === 'warning').length;
        this.state.kpis.criticalCount = lines.filter(l => l.health === 'critical').length;
        this.state.kpis.totalMargin = lines.reduce((sum, line) => sum + line.margin_amt, 0).toLocaleString(undefined, { minimumFractionDigits: 2 });

        const productMap = new Map();
        lines.forEach(line => {
            const current = productMap.get(line.product_name) || line.margin_pct;
            productMap.set(line.product_name, (current + line.margin_pct) / 2);
        });

        const sortedProducts = Array.from(productMap.entries())
            .map(([name, pct]) => ({ name, pct: pct.toFixed(2) }))
            .sort((a, b) => b.pct - a.pct);

        this.state.kpis.top5 = sortedProducts.slice(0, 5);
        this.state.kpis.bottom5 = sortedProducts.reverse().slice(0, 5);
    }

    /**
     * UI Action Handlers
     */
    async switchTab(tab) {
        if (this.state.activeTab !== tab) {
            this.state.activeTab = tab;
            await this.loadData();
        }
    }

    toggleGrouping() {
        this.state.groupByCategory = !this.state.groupByCategory;
    }

    sort(field) {
        if (this.state.sortField === field) {
            this.state.sortOrder = this.state.sortOrder === 'asc' ? 'desc' : 'asc';
        } else {
            this.state.sortField = field;
            this.state.sortOrder = 'desc';
        }
    }

    /**
     * Computed Getters for UI Loops
     */
    get filteredLines() {
        let lines = [...this.state.lines]; // Work on a copy
        if (this.state.filter !== 'all') {
            lines = lines.filter(l => l.health === this.state.filter);
        }

        return lines.sort((a, b) => {
            let v1 = a[this.state.sortField];
            let v2 = b[this.state.sortField];
            if (typeof v1 === 'string') {
                v1 = v1.toLowerCase();
                v2 = v2.toLowerCase();
            }
            if (this.state.sortOrder === 'asc') return v1 > v2 ? 1 : -1;
            return v1 < v2 ? 1 : -1;
        });
    }

    get groupedData() {
        const lines = this.filteredLines;
        if (!this.state.groupByCategory) {
            return [{ isGroup: false, lines: lines, name: 'default' }];
        }

        const groups = {};
        lines.forEach(line => {
            const cat = line.category_name || 'Uncategorized';
            if (!groups[cat]) groups[cat] = [];
            groups[cat].push(line);
        });

        return Object.entries(groups).map(([name, items]) => ({
            isGroup: true,
            name: name,
            lines: items,
            count: items.length,
            avg: (items.reduce((s, l) => s + l.margin_pct, 0) / items.length).toFixed(2)
        })).sort((a, b) => b.avg - a.avg);
    }

    /**
     * Export feature
     */
    exportToExcel() {
        const rows = this.filteredLines;
        if (!rows.length) return;
        const header = ["Order", "Product", "Price", "Cost/Ref", "Margin Amt", "Margin %", "Health"];
        const csvContent = [
            header.join(","),
            ...rows.map(r => [
                `"${r.order_name}"`, `"${r.product_name}"`, r.price.toFixed(2), 
                r.cost_or_ref.toFixed(2), r.margin_amt.toFixed(2), `${r.margin_pct.toFixed(2)}%`, r.health
            ].join(","))
        ].join("\n");
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        link.setAttribute("href", URL.createObjectURL(blob));
        link.setAttribute("download", `margin_intel_${new Date().toISOString().slice(0,10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

registry.category("actions").add("margin_intelligence_view.dashboard", MarginDashboard);
