document.addEventListener("DOMContentLoaded", loadAdminData);
document.addEventListener("DOMContentLoaded", function () {
    loadAdminData();
});

let adminChartInstance = null;
let riskPieInstance = null;
let revenueChartInstance = null;
let nextMonthChartInstance = null;

// ============================
// LOAD DASHBOARD DATA
// ============================

async function loadAdminData() {

    try {

        const res = await fetch("/admin-data");
        const data = await res.json();

        document.getElementById("totalUsers").innerText =
            data.total_users;

        document.getElementById("totalPredictions").innerText =
            data.total_predictions;

        document.getElementById("usersCount").innerText =
            data.last_30_days_users_count;

        document.getElementById("overall").innerText =
            Math.round(data.overall * 100) + "%";

        // ============================
        // REVENUE ESTIMATION
        // ============================

        if (data.revenue) {

            document.getElementById("totalRevenue").innerText =
                data.revenue.total_revenue.toLocaleString();

            document.getElementById("revenueLoss").innerText =
                data.revenue.revenue_loss.toLocaleString();

            renderRevenueChart(data.revenue);
        }

        // ============================
        // HISTORY TABLE
        // ============================

        const tbody = document.getElementById("adminHistory");
        tbody.innerHTML = "";

        data.history.forEach(r => {
            const row = `
                <tr>
                    <td>${r.user}</td>
                    <td>${r.created_at ? new Date(r.created_at).toLocaleString() : "-"}</td>
                    <td>${Math.round(r.probability * 100)}%</td>
                    <td><span class="badge ${r.risk.toLowerCase()}">${r.risk}</span></td>
                    <td>${r.suggestion || "-"}</td>
                </tr>
            `;
            tbody.innerHTML += row;
        });


        if (data.risk_distribution) {
            renderRiskPieChart(data.risk_distribution);
        }

        // ============================
        // MONTHLY RANKING TABLE
        // ============================

        const rankingTable = document.getElementById("monthlyRankingTable");

        if (rankingTable) {

            if (data.monthly_ranking && data.monthly_ranking.length > 0) {

                rankingTable.innerHTML = "";

                data.monthly_ranking.forEach((item, index) => {
                    rankingTable.innerHTML += `
                        <tr>
                            <td>${index + 1}</td>
                            <td>${item.month}</td>
                            <td>${item.avg}%</td>
                        </tr>
                    `;
                });

            } else {
                rankingTable.innerHTML = `
                    <tr>
                        <td colspan="3">No Data</td>
                    </tr>
                `;
            }
        }

        // ============================
        // TREND CHART
        // ============================

        if (data.monthly_ranking && data.monthly_ranking.length > 0) {
            renderTrendChart(data.monthly_ranking);
        }

    } catch (error) {
        console.error("Dashboard load error:", error);
    }
}


// ============================
// REVENUE ACCORDION TOGGLE
// ============================

function toggleRevenue() {

    const content = document.getElementById("revenueContent");
    const arrow = document.getElementById("revenueArrow");

    content.classList.toggle("open");

    arrow.innerText = content.classList.contains("open") ? "▲" : "▼";
}

// ============================
// DATE RANGE ACCORDION TOGGLE
// ============================

function toggleDateRange() {

    const content = document.getElementById("dateRangeContent");
    const arrow = document.getElementById("dateArrow");

    if (!content) return;

    if (content.classList.contains("open")) {
        content.classList.remove("open");
        arrow.innerText = "▼";
    } else {
        content.classList.add("open");
        arrow.innerText = "▲";
    }
}

function toggleRisk() {

    const content = document.getElementById("riskContent");
    const arrow = document.getElementById("riskArrow");

    if (!content) return;

    content.classList.toggle("open");

    arrow.innerText = content.classList.contains("open") ? "▲" : "▼";
}

function toggleMonthly() {

    const content = document.getElementById("monthlyContent");
    const arrow = document.getElementById("monthlyArrow");

    if (!content) return;

    content.classList.toggle("open");

    arrow.innerText = content.classList.contains("open") ? "▲" : "▼";
}

function toggleHistory() {

    const content = document.getElementById("historyContent");
    const arrow = document.getElementById("historyArrow");

    if (!content) return;

    content.classList.toggle("open");

    arrow.innerText = content.classList.contains("open") ? "▲" : "▼";
}

function toggleTrend() {

    const content = document.getElementById("trendContent");
    const arrow = document.getElementById("trendArrow");

    if (!content) return;

    content.classList.toggle("open");
    arrow.innerText = content.classList.contains("open") ? "▲" : "▼";
}

function toggleNextMonth() {

    const content = document.getElementById("nextMonthContent");
    const arrow = document.getElementById("nextMonthArrow");

    if (!content) return;

    content.classList.toggle("open");
    arrow.innerText = content.classList.contains("open") ? "▲" : "▼";

    if (content.classList.contains("open")) {
        loadNextMonthPrediction();
    }
}

// ============================
// REVENUE CHART
// ============================

function renderRevenueChart(revenueData) {

    const ctx = document.getElementById("revenueChart");
    if (!ctx) return;

    if (revenueChartInstance) {
        revenueChartInstance.destroy();
    }

    revenueChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Total Revenue", "Revenue Loss"],
            datasets: [{
                label: "INR",
                data: [
                    revenueData.total_revenue,
                    revenueData.revenue_loss
                ],
                backgroundColor: [
                    "#22c55e",
                    "#ef4444"
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

let trendChartInstance = null;


// TREND CHART //
function renderTrendChart(monthlyData) {

    const ctx = document.getElementById("trendChart");
    if (!ctx) return;

    if (trendChartInstance) {
        trendChartInstance.destroy();
    }

    trendChartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels: monthlyData.map(item => item.month),
            datasets: [{
                label: "Average Churn %",
                data: monthlyData.map(item => item.avg),
                borderColor: "#22c55e",
                backgroundColor: "rgba(34,197,94,0.2)",
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

// ============================
// RISK PIE CHART
// ============================

function renderRiskPieChart(distribution) {

    const ctx = document.getElementById("riskPieChart");
    if (!ctx) return;

    if (riskPieInstance) {
        riskPieInstance.destroy();
    }

    riskPieInstance = new Chart(ctx, {
        type: "pie",
        data: {
            labels: ["Low", "Medium", "High"],
            datasets: [{
                data: [
                    distribution.Low || 0,
                    distribution.Medium || 0,
                    distribution.High || 0
                ],
                backgroundColor: [
                    "#22c55e",
                    "#facc15",
                    "#ef4444"
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

function renderNextMonthChart(data) {

    const ctx = document.getElementById("nextMonthChart");
    if (!ctx) return;

    if (nextMonthChartInstance) {
        nextMonthChartInstance.destroy();
    }

    nextMonthChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Expected Churn", "Retained Users"],
            datasets: [{
                label: "Users",
                data: [
                    data.expected_churn,
                    data.total_users - data.expected_churn
                ],
                backgroundColor: ["#ef4444", "#22c55e"]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

// ============================
// DATE RANGE FETCH
// ============================

async function fetchDateRangeData() {

    const start = document.getElementById("startDate").value;
    const end = document.getElementById("endDate").value;

    if (!start || !end) {
        alert("Please select both dates");
        return;
    }

    try {

        const response = await fetch("/admin/date-range", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                start_date: start,
                end_date: end
            })
        });

        const data = await response.json();

        if (!response.ok) {
            alert("Server error");
            return;
        }

        // ========================
        // UPDATE SUMMARY
        // ========================

        document.getElementById("dateResults").innerHTML = `
            <p><strong>Total Predictions:</strong> ${data.total_predictions}</p>
            <p><strong>Average Probability:</strong> ${data.average_probability}</p>
            <p><strong>High Risk Rate:</strong> ${data.high_risk_rate}%</p>
        `;

        // ========================
        // UPDATE MONTHLY TABLE
        // ========================

        const table = document.getElementById("dateMonthlyTable");

        if (!data.monthly_ranking || data.monthly_ranking.length === 0) {
            table.innerHTML = `
                <tr>
                    <td colspan="2">No Data Found</td>
                </tr>
            `;
            return;
        }

        table.innerHTML = "";

        data.monthly_ranking.forEach(item => {
            table.innerHTML += `
                <tr>
                    <td>${item.month}</td>
                    <td>${item.avg}%</td>
                </tr>
            `;
        });

    } catch (error) {
        console.error("Date range error:", error);
        alert("Failed to fetch date range analytics");
    }
}

// ============================
// LOGOUT
// ============================

function logout() {
    localStorage.clear();
    window.location.href = "/";
}

// ============================
// EXPORT CSV
// ============================

function exportCSV() {
    window.location.href = "/export-last-30-days";
}

// ============================
// BULK PREDICTION
// ============================

async function uploadBulkFile() {

    const fileInput = document.getElementById("bulkFile");
    const file = fileInput.files[0];

    if (!file) {
        alert("Please select a CSV file");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("/bulk-predict", {
        method: "POST",
        body: formData
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.error);
        return;
    }

    const tbody = document.getElementById("bulkResults");
    tbody.innerHTML = "";

    data.results.forEach(r => {
        tbody.innerHTML += `
            <tr>
                <td>${r.user}</td>
                <td>${Math.round(r.probability * 100)}%</td>
                <td><span class="badge ${r.risk.toLowerCase()}">${r.risk}</span></td>
            </tr>
        `;
    });

    document.getElementById("bulkSummary").innerHTML = `
        <h4>Overall Average Churn Probability:
        <span style="color:#38bdf8;">
        ${Math.round(data.overall_probability * 100)}%
        </span></h4>
    `;
}

async function loadNextMonthPrediction() {

    try {

        const res = await fetch("/predict-next-month");
        const data = await res.json();

        if (!res.ok) {
            console.error("Next month error");
            return;
        }

        document.getElementById("nmTotalUsers").innerText =
            data.total_users;

        document.getElementById("nmExpectedChurn").innerText =
            data.expected_churn;

        document.getElementById("nmChurnRate").innerText =
            data.churn_rate + "%";

        document.getElementById("nmRevenueLoss").innerText =
            data.expected_revenue_loss.toLocaleString();

        document.getElementById("nmRevenue").innerText =
            data.expected_revenue.toLocaleString();

        renderNextMonthChart(data);

    } catch (err) {
        console.error("Next month fetch failed", err);
    }
}