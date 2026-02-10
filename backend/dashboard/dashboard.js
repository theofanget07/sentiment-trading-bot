// CryptoSentinel AI Analytics Dashboard + Admin Panel

const API_BASE = '/analytics';
let userGrowthChart = null;
let revenueChart = null;
let adminToken = null;

// ==================== TAB NAVIGATION ====================

function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.getAttribute('data-tab');
            
            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Add active class to clicked button and corresponding content
            button.classList.add('active');
            document.getElementById(`${targetTab}Tab`).classList.add('active');
        });
    });
}

// ==================== ANALYTICS FUNCTIONS ====================

// Fetch and update all metrics
async function updateDashboard() {
    try {
        // Fetch overview data
        const overview = await fetchJSON(`${API_BASE}/overview`);
        
        if (overview) {
            updateOverviewMetrics(overview);
        }
        
        // Fetch user metrics
        const userMetrics = await fetchJSON(`${API_BASE}/users?days=7`);
        
        if (userMetrics) {
            updateUserGrowthChart(userMetrics);
        }
        
        // Fetch revenue metrics
        const revenueMetrics = await fetchJSON(`${API_BASE}/revenue`);
        
        if (revenueMetrics) {
            updateRevenueChart(revenueMetrics);
        }
        
        // Fetch cost metrics
        const costMetrics = await fetchJSON(`${API_BASE}/costs?days=7`);
        
        if (costMetrics) {
            updateCostMetrics(costMetrics);
        }
        
        // Fetch alerts
        const alerts = await fetchJSON(`${API_BASE}/alerts`);
        
        if (alerts) {
            updateAlerts(alerts);
        }
        
        // Update last refresh time
        document.getElementById('lastUpdate').textContent = new Date().toLocaleString();
        
    } catch (error) {
        console.error('Error updating dashboard:', error);
    }
}

// Update overview metrics cards
function updateOverviewMetrics(data) {
    const { users, revenue, engagement, health } = data;
    
    // Users
    document.getElementById('totalUsers').textContent = users.total.toLocaleString();
    document.getElementById('premiumUsers').textContent = `${users.premium} Premium`;
    
    // Revenue
    document.getElementById('mrr').textContent = `€${revenue.mrr_eur.toFixed(0)}`;
    document.getElementById('conversionRate').textContent = `${revenue.conversion_rate_pct.toFixed(1)}% Conversion`;
    
    // Engagement
    document.getElementById('dau').textContent = users.dau.toLocaleString();
    document.getElementById('wau').textContent = `${users.wau} WAU`;
    
    // Commands
    document.getElementById('commandsToday').textContent = engagement.commands_today.toLocaleString();
    document.getElementById('errorRate').textContent = `${engagement.error_rate_pct.toFixed(2)}% Errors`;
    
    // Health status
    const healthCard = document.getElementById('healthStatus');
    const healthText = document.getElementById('healthText');
    
    healthCard.className = 'health-card';
    
    if (health.status === 'healthy') {
        healthText.textContent = 'All Systems Operational';
    } else if (health.status === 'warning') {
        healthCard.classList.add('warning');
        healthText.textContent = 'Warning: Check Alerts';
    } else {
        healthCard.classList.add('error');
        healthText.textContent = 'Error: Action Required';
    }
}

// Update user growth chart
function updateUserGrowthChart(data) {
    const ctx = document.getElementById('userGrowthChart');
    
    // Reverse data to show chronological order
    const dailyData = data.daily_data.reverse();
    
    const labels = dailyData.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    const dauData = dailyData.map(d => d.dau);
    const newUsersData = dailyData.map(d => d.new_users);
    
    if (userGrowthChart) {
        userGrowthChart.destroy();
    }
    
    userGrowthChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'DAU',
                    data: dauData,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                },
                {
                    label: 'New Users',
                    data: newUsersData,
                    borderColor: '#764ba2',
                    backgroundColor: 'rgba(118, 75, 162, 0.1)',
                    tension: 0.4,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Update revenue chart
function updateRevenueChart(data) {
    const ctx = document.getElementById('revenueChart');
    
    if (revenueChart) {
        revenueChart.destroy();
    }
    
    revenueChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Premium Users', 'Free Users'],
            datasets: [{
                data: [data.premium_users, data.free_users],
                backgroundColor: [
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(200, 200, 200, 0.8)'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// Update cost metrics
function updateCostMetrics(data) {
    document.getElementById('apiCostsToday').textContent = `$${data.api_costs_usd.toFixed(2)}`;
    document.getElementById('totalCostsWeek').textContent = `€${data.total_costs_eur.toFixed(2)}`;
    document.getElementById('costPerUser').textContent = `€${data.cost_per_user_eur.toFixed(2)}`;
}

// Update alerts
function updateAlerts(data) {
    const alertsList = document.getElementById('alertsList');
    
    if (data.alert_count === 0) {
        alertsList.innerHTML = '<p class="loading">✅ No active alerts</p>';
        return;
    }
    
    alertsList.innerHTML = '';
    
    data.alerts.forEach(alert => {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert-item alert-${alert.severity}`;
        
        const messageParts = alert.message.split('\n');
        const title = messageParts[0];
        const details = messageParts.slice(1).join('<br>');
        
        alertDiv.innerHTML = `
            <strong>${title}</strong>
            <div class="alert-message">${details}</div>
        `;
        
        alertsList.appendChild(alertDiv);
    });
}

// ==================== ADMIN FUNCTIONS ====================

// Admin login
function initAdmin() {
    const loginBtn = document.getElementById('adminLoginBtn');
    const tokenInput = document.getElementById('adminTokenInput');
    
    loginBtn.addEventListener('click', async () => {
        const token = tokenInput.value.trim();
        
        if (!token) {
            showAuthError('Please enter an admin token');
            return;
        }
        
        // Try to fetch admin users with this token
        try {
            const response = await fetch(`${API_BASE}/admin/users?token=${encodeURIComponent(token)}`);
            
            if (response.status === 401) {
                showAuthError('❌ Invalid token');
                return;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Token is valid!
            adminToken = token;
            document.getElementById('adminAuth').style.display = 'none';
            document.getElementById('adminPanel').style.display = 'block';
            
            // Load admin data
            await loadAdminUsers();
            
        } catch (error) {
            console.error('Admin login error:', error);
            showAuthError('❌ Authentication failed');
        }
    });
    
    // Allow Enter key to submit
    tokenInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            loginBtn.click();
        }
    });
    
    // Search functionality
    const searchInput = document.getElementById('userSearch');
    searchInput.addEventListener('input', async (e) => {
        const searchTerm = e.target.value.trim();
        await loadAdminUsers(searchTerm);
    });
    
    // Refresh button
    const refreshBtn = document.getElementById('refreshUsersBtn');
    refreshBtn.addEventListener('click', async () => {
        const searchTerm = document.getElementById('userSearch').value.trim();
        await loadAdminUsers(searchTerm);
    });
}

function showAuthError(message) {
    const errorElement = document.getElementById('authError');
    errorElement.textContent = message;
    setTimeout(() => {
        errorElement.textContent = '';
    }, 3000);
}

// Load admin users
async function loadAdminUsers(search = '') {
    if (!adminToken) return;
    
    try {
        let url = `${API_BASE}/admin/users?token=${encodeURIComponent(adminToken)}`;
        
        if (search) {
            url += `&search=${encodeURIComponent(search)}`;
        }
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Update admin stats
        document.getElementById('adminTotalUsers').textContent = data.total_users.toLocaleString();
        document.getElementById('adminPremiumUsers').textContent = data.premium_users.toLocaleString();
        document.getElementById('adminFreeUsers').textContent = data.free_users.toLocaleString();
        document.getElementById('adminMRR').textContent = `€${data.mrr_eur.toFixed(0)}`;
        
        // Update users table
        updateUsersTable(data.users);
        
    } catch (error) {
        console.error('Error loading admin users:', error);
    }
}

// Update users table
function updateUsersTable(users) {
    const tbody = document.getElementById('usersTableBody');
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="loading">No users found</td></tr>';
        return;
    }
    
    tbody.innerHTML = '';
    
    users.forEach(user => {
        const row = document.createElement('tr');
        
        // Status badge
        const statusBadge = user.is_premium 
            ? '<span class="badge badge-premium">💎 Premium</span>' 
            : '<span class="badge badge-free">🆓 Free</span>';
        
        // Stripe indicator
        const stripeIndicator = user.has_stripe_subscription
            ? '<span class="stripe-indicator active" title="Active Stripe subscription">🟢</span>'
            : '<span class="stripe-indicator" title="No Stripe subscription">⚫</span>';
        
        // Action button
        const actionBtn = user.is_premium
            ? `<button class="btn-action btn-downgrade" onclick="toggleUserTier(${user.user_id})">↓ Set FREE</button>`
            : `<button class="btn-action btn-upgrade" onclick="toggleUserTier(${user.user_id})">↑ Set PREMIUM</button>`;
        
        row.innerHTML = `
            <td>${user.user_id}</td>
            <td>@${user.username}</td>
            <td>${statusBadge}</td>
            <td>${stripeIndicator}</td>
            <td>${actionBtn}</td>
        `;
        
        tbody.appendChild(row);
    });
}

// Toggle user tier (Premium <-> Free)
async function toggleUserTier(userId) {
    if (!adminToken) return;
    
    if (!confirm(`Toggle Premium/Free status for user ${userId}?`)) {
        return;
    }
    
    try {
        const response = await fetch(
            `${API_BASE}/admin/user/${userId}/toggle?token=${encodeURIComponent(adminToken)}`,
            { method: 'POST' }
        );
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        alert(`✅ ${result.message}`);
        
        // Reload users
        const searchTerm = document.getElementById('userSearch').value.trim();
        await loadAdminUsers(searchTerm);
        
    } catch (error) {
        console.error('Error toggling user tier:', error);
        alert('❌ Failed to toggle user tier');
    }
}

// Make toggleUserTier globally accessible
window.toggleUserTier = toggleUserTier;

// ==================== FETCH HELPER ====================

// Fetch JSON helper
async function fetchJSON(url) {
    try {
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`Error fetching ${url}:`, error);
        return null;
    }
}

// ==================== INITIALIZATION ====================

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    // Init tabs
    initTabs();
    
    // Init admin
    initAdmin();
    
    // Load analytics
    updateDashboard();
    
    // Auto-refresh analytics every 60 seconds
    setInterval(updateDashboard, 60000);
});
