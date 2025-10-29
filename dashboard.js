// Dashboard JavaScript Functions
class DashboardManager {
    constructor() {
        this.allLogs = []; // Store all logs from database
        this.displayedLogs = []; // Logs currently displayed
        this.currentFilter = 'today';
        this.pieChart = null;
        this.showingMore = false;
        this.maxVisibleLogs = 5; // Show only 5 logs initially
        this.currentDispenseAmount = 50; // Default amount starts at 50g
        this.init();
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.setupEventListeners();
                this.loadInitialData();
                this.initializePieChart();
                this.loadDispenseAmount();
            });
        } else {
            this.setupEventListeners();
            this.loadInitialData();
            this.initializePieChart();
            this.loadDispenseAmount();
        }
    }

    setupEventListeners() {
        // Filter buttons
        const filterButtons = document.querySelectorAll('.time-btn');
        filterButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                filterButtons.forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                const filter = e.target.getAttribute('data-filter');
                this.filterLogs(filter);
            });
        });

        // Feed Me button
        const feedMeButton = document.getElementById('feed-me-button-big');
        if (feedMeButton) {
            feedMeButton.addEventListener('click', () => {
                this.feedMe();
            });
        }

        // More button
        const moreButton = document.getElementById('more-button');
        if (moreButton) {
            moreButton.addEventListener('click', () => {
                this.toggleMoreLogs();
            });
        }

        // Delete All button
        const deleteAllButton = document.getElementById('delete-all-button');
        if (deleteAllButton) {
            deleteAllButton.addEventListener('click', () => {
                this.deleteAllLogs();
            });
        }
    }

    // NEW: Increase amount by 50g
    increaseAmount() {
        if (this.currentDispenseAmount < 500) {
            this.currentDispenseAmount += 50;
            this.updateAmountDisplay();
            this.syncAmountToServer();
            this.syncAmountToESP32(); // NEW: Sync with ESP32
        }
    }

    // NEW: Decrease amount by 50g (minimum 50g)
    decreaseAmount() {
        if (this.currentDispenseAmount > 50) {
            this.currentDispenseAmount -= 50;
            this.updateAmountDisplay();
            this.syncAmountToServer();
            this.syncAmountToESP32(); // NEW: Sync with ESP32
        }
    }

    // NEW: Update the display
    updateAmountDisplay() {
        const amountValueEl = document.getElementById('current-amount-value');
        if (amountValueEl) {
            amountValueEl.textContent = this.currentDispenseAmount;
        }
    }

    // NEW: Sync to Flask server
    async syncAmountToServer() {
        try {
            await fetch(`/set_dispense_amount?amount=${this.currentDispenseAmount}`, {
                method: 'POST'
            });
            console.log(`Dispense amount set to: ${this.currentDispenseAmount}g`);
        } catch (error) {
            console.error('Error syncing dispense amount:', error);
        }
    }

    // NEW: Sync amount with ESP32
    async syncAmountToESP32() {
        try {
            const response = await fetch(`http://192.168.254.4/set_target_weight?target_weight=${this.currentDispenseAmount}`, {
                method: 'POST'
            });
            console.log(`ESP32 target weight synced to: ${this.currentDispenseAmount}g`);
        } catch (error) {
            console.error('Error syncing with ESP32:', error);
        }
    }

    async loadInitialData() {
        try {
            // Load ESP32 status
            await this.loadESP32Status();
            // Load feeding logs from database
            await this.loadFeedingLogs();
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    async loadDispenseAmount() {
        try {
            const response = await fetch('/get_dispense_amount');
            if (response.ok) {
                const data = await response.json();
                this.currentDispenseAmount = data.amount;
                this.updateAmountDisplay();
                // Also sync with ESP32
                await this.syncAmountToESP32();
            }
        } catch (error) {
            console.error('Error loading dispense amount:', error);
        }
    }

    async loadESP32Status() {
        try {
            const response = await fetch('/get_esp32_status');
            if (response.ok) {
                const data = await response.json();
                if (!data.error) {
                    this.updateLiveData(data);
                }
            }
        } catch (error) {
            console.error('Error loading ESP32 status:', error);
        }
    }

    async loadFeedingLogs() {
    try {
        const response = await fetch('/get_feeding_logs');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const logs = await response.json();
        
        // Convert database logs to dashboard format
        this.allLogs = logs.map(log => {
            const dateTime = new Date(log.timestamp);
            
            // Determine feed type
            let feedType = log.feed_type || 'Manual';
            
            return {
                id: log.id,
                date: dateTime.toISOString().split('T')[0],
                time: dateTime.toTimeString().slice(0, 5),
                amount: `${log.amount || log.weight}g`,
                status: this.getStatusFromEvent(log.event_type),
                source: log.source,
                feed_type: feedType,
                image_path: log.image_path,
                feeding_id: log.feeding_id,
                timestamp: log.timestamp,
                originalData: log
            };
        });
            console.log(`Loaded ${this.allLogs.length} logs from database`);
            this.applyCurrentFilter();
        } catch (error) {
            console.error('Error loading feeding logs:', error);
            // Fallback to empty array
            this.allLogs = [];
            this.applyCurrentFilter();
        }
    }

   getStatusFromEvent(eventType) {
    if (!eventType) return 'Completed';
    switch(eventType.toUpperCase()) {
        case 'MANUAL_FEED':
        case 'AUTOMATIC_FEED':
        case 'SCHEDULED_FEED':
        case 'FEEDING_START':
        case 'FEEDING_COMPLETED':
        case 'COMPLETED':
        case 'DISPENSING_COMPLETED':
            return 'Completed';
        }
    }

    applyCurrentFilter() {
        const today = new Date().toISOString().split('T')[0];
        if (this.currentFilter === 'today') {
            this.displayedLogs = this.allLogs.filter(log => log.date === today);
        } else {
            // For week filter, show logs from last 7 days
            const oneWeekAgo = new Date();
            oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
            this.displayedLogs = this.allLogs.filter(log => {
                const logDate = new Date(log.date);
                return logDate >= oneWeekAgo;
            });
        }
        
        // Sort by timestamp descending (newest first)
        this.displayedLogs.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        this.populateLogsTable();
        this.updateStats();
        this.updateMoreButton();
    }

    populateLogsTable() {
        const tbody = document.getElementById('logsTableBody');
        if (!tbody) return;
        
        // Determine which logs to display
        let logsToDisplay;
        if (this.showingMore) {
            logsToDisplay = this.displayedLogs;
        } else {
            logsToDisplay = this.displayedLogs.slice(0, this.maxVisibleLogs);
        }
        
        if (logsToDisplay.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-gray); font-style: italic;">
                        No feeding logs found for selected period.
                    </td>
                </tr>
            `;
            return;
        }
        
       tbody.innerHTML = logsToDisplay.map(log => {
    const statusClass = log.status.toLowerCase().replace(' ', '-');
    
    // Determine source icon and text based on feed_type
    const sourceIcon = log.feed_type === 'Automatic' ? 
        '<i class="fas fa-clock" style="color: #4CAF50; margin-right: 5px;"></i>' : 
        '<i class="fas fa-hand-pointer" style="color: #2196F3; margin-right: 5px;"></i>';
    const sourceText = log.feed_type === 'Automatic' ? 'Automatic' : 'Manual';
    
    // Check if image exists and create appropriate icon
    const imageIcon = log.image_path ? 
        `<i class="fas fa-image" style="color: #ff6b35; cursor: pointer;" 
            onclick="viewImage('${log.image_path}')" 
            title="View Photo"></i>` : 
        '<i class="fas fa-camera" style="color: #6b7280;" title="No photo"></i>';
    
    return `
        <tr>
            <td>Module 1</td>
            <td>${log.date}</td>
            <td>${log.time}</td>
            <td>${log.amount}</td>
            <td><span class="status-badge ${statusClass}">${log.status}</span></td>
            <td>${sourceIcon}${sourceText}</td>
            <td>${imageIcon}</td>
            <td>
                <i class="fas fa-trash delete-icon"
                   onclick="window.dashboardManager.deleteLogEntry(${log.id})"
                   title="Delete">
                </i>
            </td>
        </tr>
    `;
}).join('');

}

    updateMoreButton() {
        const moreBtn = document.getElementById('more-button');
        if (!moreBtn) return;
        
        if (this.displayedLogs.length > this.maxVisibleLogs) {
            moreBtn.style.display = 'flex';
            if (this.showingMore) {
                moreBtn.innerHTML = '<i class="fas fa-chevron-up"></i> Show Less';
            } else {
                moreBtn.innerHTML = '<i class="fas fa-chevron-down"></i> Show More';
            }
        } else {
            moreBtn.style.display = 'none';
        }
    }

    toggleMoreLogs() {
        this.showingMore = !this.showingMore;
        this.populateLogsTable();
        this.updateMoreButton();
        
        // Scroll to the table after toggling
        if (this.showingMore) {
            const tableContainer = document.querySelector('.table-container');
            if (tableContainer) {
                tableContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
    }

    filterLogs(filter) {
        this.currentFilter = filter;
        this.showingMore = false;
        this.applyCurrentFilter();
    }

    async deleteLogEntry(logId) {
        if (!confirm('Are you sure you want to delete this feeding log?')) {
            return;
        }
        
        try {
            const response = await fetch(`/delete_log/${logId}, { method: 'DELETE' }`);
            if (response.ok) {
                // Remove from local arrays
                this.allLogs = this.allLogs.filter(log => log.id !== logId);
                this.displayedLogs = this.displayedLogs.filter(log => log.id !== logId);
                // Update the display
                this.applyCurrentFilter();
                console.log(`Log ${logId} deleted successfully`);
            } else {
                throw new Error('Failed to delete log from server');
            }
        } catch (error) {
            console.error('Error deleting log:', error);
            alert('Error deleting log. Please try again.');
        }
    }

    async deleteAllLogs() {
        const confirmed = confirm('Are you sure you want to delete ALL feeding logs? This action cannot be undone.');
        if (!confirmed) return;
        
        const deleteAllBtn = document.getElementById('delete-all-button');
        const originalHTML = deleteAllBtn.innerHTML;
        deleteAllBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deleting...';
        deleteAllBtn.disabled = true;
        
        try {
            const response = await fetch('/delete_all_logs', { method: 'DELETE' });
            if (response.ok) {
                // Clear all logs
                this.allLogs = [];
                this.displayedLogs = [];
                this.showingMore = false;
                // Update the UI
                this.applyCurrentFilter();
                console.log('All logs deleted successfully');
                alert('All feeding logs have been deleted successfully!');
            } else {
                throw new Error('Failed to delete all logs from server');
            }
        } catch (error) {
            console.error('Error deleting all logs:', error);
            alert('Error clearing logs. Please try again.');
        } finally {
            deleteAllBtn.innerHTML = originalHTML;
            deleteAllBtn.disabled = false;
        }
    }

    updateLiveData(statusData) {
        // Update current weight display if needed
        const currentWeightEl = document.getElementById('current-weight');
        if (currentWeightEl && statusData.weight !== undefined) {
            currentWeightEl.textContent = `${statusData.weight}g`;
        }
    }

    initializePieChart() {
        const ctx = document.getElementById('pieChart');
        if (!ctx) return;
        
        if (this.pieChart) {
            this.pieChart.destroy();
        }
        
        this.pieChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [0, 100],
                    backgroundColor: ['#ff6b35', '#e5e7eb'],
                    borderWidth: 0,
                }]
            },
            options: {
                cutout: '70%',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
    }

    updateStats() {
        let logsToCalculate = this.displayedLogs;
        
        // For "today" filter, make sure we're only counting today's logs
        if (this.currentFilter === 'today') {
            const today = new Date().toISOString().split('T')[0];
            logsToCalculate = this.displayedLogs.filter(log => log.date === today);
        }
        
        const completedFeedings = logsToCalculate.filter(log => 
            log.status === 'Completed' || log.status === 'In Progress'
        ).length;
        
        // Update total feedings
        const totalFeedingsEl = document.getElementById('total-feedings');
        if (totalFeedingsEl) {
            totalFeedingsEl.textContent = completedFeedings;
        }
        
        // Calculate total food dispensed
        let totalDispensed = 0;
        logsToCalculate.forEach(log => {
            if (log.status === 'Completed') {
                // Extract numeric value from amount string (e.g., "200g" -> 200)
                const amount = parseInt(log.amount) || 0;
                totalDispensed += amount;
            }
        });

// Global function to view images
function viewImage(imagePath) {
    if (!imagePath) {
        alert('No image available');
        return;
    }
    // Open image in new window
    const imageWindow = window.open('', '_blank');
    imageWindow.document.write(`
        <html>
            <head>
                <title>Feeding Photo</title>
                <style>
                    body { margin: 0; background: #000; display: flex; justify-content: center; align-items: center; height: 100vh; }
                    img { max-width: 90%; max-height: 90vh; box-shadow: 0 0 20px rgba(255,255,255,0.3); }
                </style>
            </head>
            <body>
                <img src="${imagePath}" alt="Feeding Photo" onclick="window.close()">
            </body>
        </html>
    `);
}
        
        const totalDispensedKg = (totalDispensed / 1000).toFixed(1);
        const foodDispensedEl = document.getElementById('food-dispensed');
        if (foodDispensedEl) {
            foodDispensedEl.textContent = totalDispensedKg;
        }
        
        // Update pie chart details
        this.updatePieChart(totalDispensedKg);
    }

    updatePieChart(totalDispensedKg) {
        const foodDispensedDetailEl = document.getElementById('food-dispensed-detail');
        const foodRemainingDetailEl = document.getElementById('food-remaining-detail');
        const piePercentageEl = document.getElementById('pie-percentage');
        
        const totalCapacity = 10.0; // 10kg total capacity
        const remaining = Math.max(0, (totalCapacity - parseFloat(totalDispensedKg))).toFixed(1);
        const percentage = totalDispensedKg > 0 ? 
            Math.round((parseFloat(totalDispensedKg) / totalCapacity) * 100) : 0;
        
        if (foodDispensedDetailEl) {
            foodDispensedDetailEl.textContent = `Food Dispensed: ${totalDispensedKg}kg`;
        }
        if (foodRemainingDetailEl) {
            foodRemainingDetailEl.textContent = `Remaining: ${remaining}kg`;
        }
        if (piePercentageEl) {
            piePercentageEl.textContent = `${percentage}%`;
        }
        
        // Update pie chart
        if (this.pieChart) {
            this.pieChart.data.datasets[0].data = [percentage, 100 - percentage];
            this.pieChart.update();
        }
    }

    async feedMe() {
        console.log('Instant feeding triggered');
        
        // Immediate visual feedback
        const feedButton = document.getElementById('feed-me-button-big');
        const feedText = feedButton.querySelector('.feed-text');
        const originalText = feedText.textContent;
        feedText.textContent = 'Sending...';
        feedButton.style.opacity = '0.7';
        
        try {
            // Sync amount with ESP32 first
            await this.syncAmountToESP32();
            
            // Trigger feeding on ESP32
            const espResponse = await fetch('http://192.168.254.4/trigger_dispensing', {
                method: 'POST',
                body: `amount=${this.currentDispenseAmount}`
            });
            
            if (espResponse.ok) {
                feedText.textContent = 'Sent!';
                console.log('Feeding command sent to ESP32');
                
                // Also log to Flask server
                await fetch('/trigger_feeding', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body:  `source=Dashboard&amount=${this.currentDispenseAmount}`
                });
                
                // Reset to default amount
                this.currentDispenseAmount = 50;
                this.updateAmountDisplay();
                this.syncAmountToServer();
                this.syncAmountToESP32();
                
                // Immediate status refresh
                setTimeout(() => {
                    if (window.liveDataComponent) {
                        window.liveDataComponent.fetchESP32Status();
                    }
                    // Reload logs to show new feeding entry
                    this.loadFeedingLogs();
                }, 100);
            } else {
                feedText.textContent = 'Failed!';
            }
        } catch (error) {
            feedText.textContent = 'Error!';
            console.error('Feeding error:', error);
        }
        
        // Quick reset
        setTimeout(() => {
            feedText.textContent = originalText;
            feedButton.style.opacity = '1';
        }, 800);
    }
}

// Initialize Dashboard Manager
window.dashboardManager = new DashboardManager();

// Global Functions
function feedMe() {
    if (window.dashboardManager) {
        window.dashboardManager.feedMe();
    }
}

function deleteLog(logId) {
    if (window.dashboardManager) {
        window.dashboardManager.deleteLogEntry(logId);
    }
}

function loadMoreLogs() {
    if (window.dashboardManager) {
        window.dashboardManager.toggleMoreLogs();
    }
}

function filterLogs(filter) {
    if (window.dashboardManager) {
        window.dashboardManager.filterLogs(filter);
    }
}

function scrollToActivity() {
    const liveDataSection = document.querySelector('.live-data-section');
    if (liveDataSection) {
        liveDataSection.scrollIntoView({ behavior: 'smooth' });
    }
}