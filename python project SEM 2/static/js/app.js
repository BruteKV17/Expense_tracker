document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".password-toggle").forEach(btn => {
        btn.addEventListener("click", function () {
            const target = document.getElementById(this.dataset.target);
            const icon = this.querySelector("i");
            if (target.type === "password") {
                target.type = "text";
                icon.className = "bi bi-eye-slash-fill";
            } else {
                target.type = "password";
                icon.className = "bi bi-eye-fill";
            }
        });
    });

    const charts = window.chartPayload || {};
    const chartTextColor = "#cbd5e1";
    const chartGridColor = "rgba(148,163,184,0.12)";

    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: chartTextColor,
                    boxWidth: 12,
                    usePointStyle: true
                }
            },
            tooltip: {
                backgroundColor: "rgba(15, 23, 42, 0.92)",
                titleColor: "#fff",
                bodyColor: "#cbd5e1",
                borderColor: "rgba(79, 70, 229, 0.35)",
                borderWidth: 1,
                padding: 12
            }
        },
        scales: {
            x: {
                ticks: { color: chartTextColor },
                grid: { color: chartGridColor, drawBorder: false }
            },
            y: {
                ticks: { color: chartTextColor },
                grid: { color: chartGridColor, drawBorder: false }
            }
        }
    };

    function createChart(id, config) {
        const ctx = document.getElementById(id);
        if (ctx) new Chart(ctx, config);
    }

    createChart("expensePieChart", {
        type: "pie",
        data: {
            labels: charts.pie_labels || [],
            datasets: [{
                data: charts.pie_values || [],
                backgroundColor: ["#4F46E5", "#38BDF8", "#22C55E", "#EF4444", "#F59E0B", "#A855F7", "#14B8A6", "#F43F5E"],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: commonOptions.plugins
        }
    });

    createChart("monthlyBarChart", {
        type: "bar",
        data: {
            labels: charts.bar_labels || [],
            datasets: [{
                label: "Expense",
                data: charts.bar_values || [],
                backgroundColor: "rgba(79, 70, 229, 0.85)",
                borderRadius: 12,
                borderSkipped: false
            }]
        },
        options: commonOptions
    });

    createChart("trendLineChart", {
        type: "line",
        data: {
            labels: charts.line_labels || [],
            datasets: [{
                label: "Trend",
                data: charts.line_values || [],
                borderColor: "#38BDF8",
                backgroundColor: "rgba(56, 189, 248, 0.15)",
                fill: true,
                tension: 0.35,
                pointRadius: 3,
                pointBackgroundColor: "#38BDF8"
            }]
        },
        options: commonOptions
    });

    createChart("budgetDoughnutChart", {
        type: "doughnut",
        data: {
            labels: charts.budget_labels || [],
            datasets: [{
                data: charts.budget_values || [],
                backgroundColor: ["#22C55E", "rgba(148, 163, 184, 0.25)"],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "72%",
            plugins: commonOptions.plugins
        }
    });

    createChart("weeklyExpenseChart", {
        type: "line",
        data: {
            labels: charts.weekly_labels || [],
            datasets: [{
                label: "Weekly Expense",
                data: charts.weekly_values || [],
                borderColor: "#F59E0B",
                backgroundColor: "rgba(245, 158, 11, 0.12)",
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointBackgroundColor: "#F59E0B"
            }]
        },
        options: commonOptions
    });
});