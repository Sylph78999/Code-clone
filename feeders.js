// feeders.js

// Load all feeders on page load
async function loadFeeders() {
    try {
        const response = await fetch('/get_feeders');
        const feeders = await response.json();
        
        const feedersList = document.getElementById('feedersList');
        const emptyState = document.getElementById('emptyState');
        
        if (feeders.length === 0) {
            feedersList.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }
        
        feedersList.style.display = 'grid';
        emptyState.style.display = 'none';
        
        feedersList.innerHTML = feeders.map(feeder => `
            <div class="feeder-card">
                <div class="feeder-header">
                    <div class="feeder-name">
                        <i class="fas fa-microchip"></i>
                        <span>${feeder.name}</span>
                    </div>
                    <span class="feeder-status ${feeder.is_online ? 'online' : 'offline'}">
                        ${feeder.is_online ? 'Online' : 'Offline'}
                    </span>
                </div>
                
                <div class="feeder-info">
                    <div class="info-item">
                        <i class="fas fa-network-wired"></i>
                        <span>${feeder.ip_address}</span>
                    </div>
                    
                    <div class="info-item">
                        <i class="fas fa-weight"></i>
                        <span>Capacity: ${feeder.max_capacity_g |5000}g</span>
                    </div>
                </div>
                
               
                    </button>
                    <button class="btn-delete" onclick="deleteFeeder(${feeder.id}, '${feeder.name}')">
                        <i class="fas fa-trash"></i>
                        <span>Delete</span>
                    </button>
                </div>
            </div>
        `).join('');
        
        console.log('Loaded ' + feeders.length + ' feeder(s)');
    } catch (error) {
        console.error('Error loading feeders:', error);
        alert('Failed to load feeders. Please refresh the page.');
    }
}

// Show add feeder form
function showAddForm() {
    const form = document.getElementById('addFeederForm');
    form.style.display = 'block';
    document.getElementById('feederName').focus();
}

// Hide add feeder form
function hideAddForm() {
    const form = document.getElementById('addFeederForm');
    form.style.display = 'none';
    document.getElementById('feederName').value = '';
    document.getElementById('feederIP').value = '';
}

// Add new feeder
async function addFeeder() {
    const name = document.getElementById('feederName').value.trim();
    const ip = document.getElementById('feederIP').value.trim();
    
    // Validation
    if (!name) {
        alert('Please enter a feeder name');
        return;
    }
    
    if (!ip) {
        alert('Please enter an IP address');
        return;
    }
    
    // Basic IP validation
    const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (!ipPattern.test(ip)) {
        alert('Please enter a valid IP address (e.g., 192.168.254.4)');
        return;
    }
    
    try {
        const response = await fetch('/add_feeder', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                name: name, 
                ip_address: ip 
            })
        });
        
        if (response.ok) {
            console.log('Feeder added successfully');
            hideAddForm();
            loadFeeders();
            
            // Show success message
            alert('Feeder "' + name + '" added successfully!');
        } else {
            throw new Error('Failed to add feeder');
        }
    } catch (error) {
        console.error('Error adding feeder:', error);
        alert('Failed to add feeder. Please try again.');
    }
}

// Delete feeder
async function deleteFeeder(id, name) {
    const confirmed = confirm('Are you sure you want to delete "' + name + '"?\n\nThis action cannot be undone.');
    
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch('/delete_feeder/' + id, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            console.log('Feeder ' + id + ' deleted successfully');
            loadFeeders();
            alert('Feeder "' + name + '" has been deleted.');
        } else {
            throw new Error('Failed to delete feeder');
        }
    } catch (error) {
        console.error('Error deleting feeder:', error);
        alert('Failed to delete feeder. Please try again.');
    }
}

// Trigger feeding for a specific feeder
async function triggerFeed(id) {
    try {
        const response = await fetch('/trigger_feeding/' + id, {
            method: 'POST'
        });
        
        if (response.ok) {
            console.log('Feeding triggered for feeder ' + id);
            alert('Feeding has been triggered!');
        } else {
            throw new Error('Failed to trigger feeding');
        }
    } catch (error) {
        console.error('Error triggering feeding:', error);
        alert('Failed to trigger feeding. Please try again.');
    }
}

// Setup event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Load feeders
    loadFeeders();
    
    // Add feeder button
    const showAddFormBtn = document.getElementById('showAddFormBtn');
    if (showAddFormBtn) {
        showAddFormBtn.addEventListener('click', showAddForm);
    }
    
    // Enter key on inputs
    const feederNameInput = document.getElementById('feederName');
    const feederIPInput = document.getElementById('feederIP');
    
    if (feederNameInput && feederIPInput) {
        feederNameInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                feederIPInput.focus();
            }
        });
        
        feederIPInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addFeeder();
            }
        });
    }
    
    // Mobile navigation toggle
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });
    }
});

// Auto-refresh feeders every 30 seconds
setInterval(loadFeeders, 30000);