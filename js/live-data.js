// Optimized Live Data Component
class LiveDataComponent {
    constructor() {
        this.currentData = null;
        this.isOnline = false;
        this.lastUpdate = Date.now();
        this.interval = null;
        this.failCount = 0;
        this.maxCapacity = this.loadMaxCapacity(); // Load saved capacity
        this.init();
    }

    init() {
        this.render();
        this.startPolling();
        // Immediate first fetch
        this.fetchESP32Status();
    }

    render() {
        const container = document.getElementById('live-data-container');
        if (!container) return;

        const weight = this.currentData?.weight || 0;
        const isOnline = this.currentData?.online || false;
       
        container.innerHTML = `
            <div class="live-data-container">
                <div class="live-data-header">
                    <h3 class="live-data-title">Live Data</h3>
                    <div class="live-indicator">
                        <div class="live-dot ${isOnline ? 'online' : 'offline'}"></div>
                        <span class="live-text">${isOnline ? 'Live' : 'Offline'}</span>
                    </div>
                </div>
               
                <div class="live-data-content">
                    <div class="data-item">
                        <span class="data-label">Current Weight</span>
                        <div class="data-value ${isOnline ? 'weight-normal' : 'weight-offline'}">
                            ${weight}g
                        </div>
                    </div>

                    <div class="data-item">
                        <span class="data-label">System Status</span>
                        <span class="status-badge ${isOnline ? 'status-online' : 'status-offline'}">
                            ${isOnline ? 'Online' : 'Offline'}
                        </span>
                    </div>

                    ${this.currentData?.servo_open ? `
                    <div class="data-item">
                        <span class="data-label">Servo Status</span>
                        <span class="status-badge status-warning">OPEN</span>
                    </div>
                    ` : ''}

                    ${this.currentData?.feeding_active ? `
                    <div class="data-item">
                        <span class="data-label">Feeding Status</span>
                        <span class="status-badge status-warning">ACTIVE</span>
                    </div>
                    ` : ''}

                    ${this.currentData?.buzzer_active ? `
                    <div class="data-item">
                        <span class="data-label">Buzzer</span>
                        <span class="status-badge status-offline">LOW FOOD</span>
                    </div>
                    ` : ''}

                    <div class="progress-section">
                        <div class="progress-label">
                            <span>Food Level</span>
                            <span>${Math.round((weight / 10000) * 100)}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${Math.round((weight / 10000) * 100)}%"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Update system status card
        this.updateSystemStatusCard(isOnline);
    }

    startPolling() {
        // Poll every 3 seconds instead of 1 second to reduce load
        this.interval = setInterval(() => {
            this.fetchESP32Status();
        }, 3000);
    }

    async fetchESP32Status() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000);
           
            const response = await fetch('/get_esp32_status', {
                signal: controller.signal
            });
           
            clearTimeout(timeoutId);
           
            if (response.ok) {
                const data = await response.json();
                this.currentData = data;
                this.isOnline = data.online;
                this.lastUpdate = Date.now();
                this.failCount = 0; // Reset fail count on success
                this.render();
            } else {
                this.handleFetchError();
            }
        } catch (error) {
            this.handleFetchError();
        }
    }

    handleFetchError() {
        this.failCount++;
        // Only mark offline after 3 consecutive failures
        if (this.failCount >= 3) {
            this.isOnline = false;
            this.currentData = null;
            this.render();
        }
    }

    updateSystemStatusCard(isOnline) {
        const systemStatusCard = document.querySelector('.stat-card.success');
        if (!systemStatusCard) return;

        const statusValue = systemStatusCard.querySelector('.stat-value');
        if (!statusValue) return;

        if (isOnline) {
            statusValue.textContent = 'Online';
            statusValue.className = 'stat-value status-online';
            systemStatusCard.style.background = 'linear-gradient(135deg, #34d399 0%, #10b981 100%)';
        } else {
            statusValue.textContent = 'Offline';
            statusValue.className = 'stat-value status-offline';
            systemStatusCard.style.background = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
        }

        // Update remaining and capacity display
        this.updateFoodDistribution();
    }

    loadMaxCapacity() {
        // Try to load from localStorage
        const saved = localStorage.getItem('maxFoodCapacity');
        return saved ? parseInt(saved) : 0;
    }

    saveMaxCapacity(weight) {
        localStorage.setItem('maxFoodCapacity', weight.toString());
        this.maxCapacity = weight;
    }

    updateFoodDistribution() {
        const currentWeight = this.currentData?.weight || 0;
       
        // Auto-detect refill: if current weight is significantly higher than before, it's a refill
        if (currentWeight > this.maxCapacity * 0.9) {
            // This looks like a refill - save as new max capacity
            this.saveMaxCapacity(currentWeight);
        }
       
        // Reset capacity to 0 if food is nearly empty (below 50g)
        if (currentWeight < 30 && this.maxCapacity > 0) {
            this.saveMaxCapacity(0);
        }

        // Update Current Weight Capacity (shows the reference/max)
        const capacityEl = document.getElementById('current-weight-capacity');
        if (capacityEl) {
            capacityEl.textContent = `Current Weight Capacity: ${this.maxCapacity}g`;
        }

        // Update Remaining (shows current weight from live data)
        const remainingEl = document.getElementById('food-remaining-detail');
        if (remainingEl) {
            remainingEl.textContent = `Remaining: ${currentWeight}g`;
        }
    }

    destroy() {
        if (this.interval) {
            clearInterval(this.interval);
        }
    }
}

// Initialize immediately
window.liveDataComponent = new LiveDataComponent();



