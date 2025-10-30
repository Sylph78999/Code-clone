// Automatic Feeder Schedule Functionality

document.addEventListener('DOMContentLoaded', function() {
    // Get all elements
    const gramsInput = document.getElementById('gramsInput');
    const decreaseGramsBtn = document.getElementById('decreaseGrams');
    const increaseGramsBtn = document.getElementById('increaseGrams');
    
    const timeInput = document.getElementById('timeInput');
    const timeUpBtn = document.getElementById('timeUpBtn');
    const timeDownBtn = document.getElementById('timeDownBtn');
    const timePeriod = document.getElementById('timePeriod');
    const periodUpBtn = document.getElementById('periodUpBtn');
    const periodDownBtn = document.getElementById('periodDownBtn');
    
    const dayButtons = document.querySelectorAll('.day-btn');
    const confirmBtn = document.getElementById('confirmBtn');
    const cancelBtn = document.getElementById('cancelBtn');

    // Initialize values
    let currentGrams = 50;
    let currentHour = 10;
    let currentMinute = 0;
    let currentPeriod = 'AM';
    let selectedDays = [];

    // Set default grams value
    gramsInput.value = currentGrams;
    updateTimeDisplay();

    // Grams control functions
    function updateGrams(change) {
        let newGrams = currentGrams + change;
        
        // Ensure grams stay within limits (50g - 500g)
        if (newGrams < 50) {
            newGrams = 50;
        } else if (newGrams > 500) {
            newGrams = 500;
        }
        
        currentGrams = newGrams;
        gramsInput.value = currentGrams;
    }

    decreaseGramsBtn.addEventListener('click', function() {
        updateGrams(-50);
    });

    increaseGramsBtn.addEventListener('click', function() {
        updateGrams(50);
    });

    // Also allow manual input with validation
    gramsInput.addEventListener('input', function() {
        let value = parseInt(this.value);
        
        if (isNaN(value)) {
            value = 50;
        } else if (value < 50) {
            value = 50;
        } else if (value > 500) {
            value = 500;
        }
        
        // Round to nearest 50
        value = Math.round(value / 50) * 50;
        
        currentGrams = value;
        this.value = value;
    });

    gramsInput.addEventListener('blur', function() {
        if (this.value === '' || parseInt(this.value) < 50) {
            currentGrams = 50;
            this.value = 50;
        }
    });

    // Time control functions
    function updateTimeDisplay() {
        const formattedHour = currentHour.toString().padStart(2, '0');
        const formattedMinute = currentMinute.toString().padStart(2, '0');
        timeInput.value = formattedHour + ':' + formattedMinute;
        timePeriod.textContent = currentPeriod;
    }

    function incrementTime() {
        currentMinute += 15;
        
        if (currentMinute >= 60) {
            currentMinute = 0;
            currentHour++;
            
            if (currentHour > 12) {
                currentHour = 1;
            }
        }
        
        updateTimeDisplay();
    }

    function decrementTime() {
        currentMinute -= 15;
        
        if (currentMinute < 0) {
            currentMinute = 45;
            currentHour--;
            
            if (currentHour < 1) {
                currentHour = 12;
            }
        }
        
        updateTimeDisplay();
    }

    timeUpBtn.addEventListener('click', incrementTime);
    timeDownBtn.addEventListener('click', decrementTime);

    // Period (AM/PM) control
    function togglePeriod() {
        currentPeriod = currentPeriod === 'AM' ? 'PM' : 'AM';
        updateTimeDisplay();
    }

    periodUpBtn.addEventListener('click', togglePeriod);
    periodDownBtn.addEventListener('click', togglePeriod);

    // Day selection
    dayButtons.forEach(function(btn, index) {
        btn.addEventListener('click', function() {
            this.classList.toggle('active');
            
            const dayIndex = index;
            const dayIndexInArray = selectedDays.indexOf(dayIndex);
            
            if (dayIndexInArray > -1) {
                selectedDays.splice(dayIndexInArray, 1);
            } else {
                selectedDays.push(dayIndex);
            }
        });
    });

    confirmBtn.addEventListener('click', function() {
    // Validate that at least one day is selected
    if (selectedDays.length === 0) {
        alert('Please select at least one day for the schedule.');
        return;
    }

    // Get day names
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const selectedDayNames = selectedDays.sort().map(function(index) {
        return dayNames[index];
    });

    // Create schedule object
    const schedule = {
        feeder_id: 1,
        grams: currentGrams,
        time: currentHour.toString().padStart(2, '0') + ':' + currentMinute.toString().padStart(2, '0') + ' ' + currentPeriod,
        days: selectedDays,
        timestamp: new Date().toISOString()
    };

    // Show confirmation message
    const confirmMsg = 'Schedule will be set:\n\nGrams: ' + currentGrams + 'g\nTime: ' + schedule.time + '\nDays: ' + selectedDayNames.join(', ') + '\n\nThis will be sent to ESP32 and will trigger automatically.';
    
    if (!confirm(confirmMsg)) {
        return;
    }

    // Send to backend
    fetch('/set_schedule', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(schedule)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('✓ Schedule set successfully!\n\n' + data.message + '\n\nIt will appear in logs when feeding actually happens.');
            window.location.href = '/logs';
        } else {
            alert('✗ Error: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('✗ Failed to set schedule: ' + error.message);
    });
});
        

    // Cancel button
    cancelBtn.addEventListener('click', function() {
        if (confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
            window.location.href = '/dashboard';
        }
    });

    // Mobile navigation toggle (if needed)
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');
    
    if (navToggle) {
        navToggle.addEventListener('click', function() {
            navLinks.classList.toggle('active');
        });
    }
});

