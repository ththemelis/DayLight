let monitorChart;

// 1. Αρχικοποίηση Γραφήματος
function initChart() {
    const canvas = document.getElementById('tempChart');
    if (!canvas) return; // Αν δεν υπάρχει το canvas, σταμάτα

    const ctx = canvas.getContext('2d');
    monitorChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'Θερμοκρασία °C',
                    data: [],
                    borderColor: '#ff9800',
                    yAxisID: 'y',
                    tension: 0.4
                },
                {
                    label: 'Υγρασία %',
                    data: [],
                    borderColor: '#00e5ff',
                    yAxisID: 'y1',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { display: false },
                y: { type: 'linear', position: 'left', min: 10, max: 50, ticks: {color: '#ff9800'} },
                y1: { type: 'linear', position: 'right', min: 0, max: 100, ticks: {color: '#00e5ff'} }
            }
        }
    });
}

// 2. Ενημέρωση Δεδομένων
async function updateData() {
    try {
        const resState = await fetch("/api/state");
        const state = await resState.json();

        // Χρησιμοποιούμε προαιρετική αλυσίδα (optional chaining) για να μην κρασάρει αν λείπει ένα ID
        if(document.getElementById("temp")) document.getElementById("temp").innerText = state.temperature.toFixed(1);
        if(document.getElementById("hum")) document.getElementById("hum").innerText = state.humidity.toFixed(1);
        
        // Έλεγχος για το ID του mode (δοκιμάζει και τα δύο πιθανά IDs)
        const modeEl = document.getElementById("mode") || document.getElementById("mode-text");
        if(modeEl) modeEl.innerText = state.auto ? "AUTO" : "MANUAL";

        const controls = document.getElementById("manual-controls");
        if(controls) {
            controls.style.opacity = state.auto ? "0.3" : "1";
            controls.style.pointerEvents = state.auto ? "none" : "all";
        }

        // Ενημέρωση Γραφήματος
const resLogs = await fetch("/api/logs");
        if (!resLogs.ok) throw new Error("Logs not found"); // Έλεγχος αν η απάντηση είναι οκ
        
        const logs = await resLogs.json();
if (logs && logs.length > 0) {
    const lastLogs = logs.slice(-30);
    
    // Ενημέρωση Labels
    monitorChart.data.labels = lastLogs.map(() => ""); 
    
    // ΕΔΩ ΕΙΝΑΙ ΤΟ ΚΡΙΣΙΜΟ ΣΗΜΕΙΟ:
    // Πρέπει το l.temp να αντιστοιχεί στο "temp" του main.py
    monitorChart.data.datasets[0].data = lastLogs.map(l => parseFloat(l.temp));
    monitorChart.data.datasets[1].data = lastLogs.map(l => parseFloat(l.hum));
    
    monitorChart.update('none');
}
    } catch (e) {
        console.error("Update error:", e);
    }
}

// 3. Event Listeners (με έλεγχο ύπαρξης)
function setupEvents() {
    const btnToggle = document.getElementById("toggle");
    if(btnToggle) btnToggle.onclick = () => fetch("/api/toggle").then(updateData);

    const btnAuto = document.getElementById("auto");
    if(btnAuto) btnAuto.onclick = () => fetch("/api/auto").then(updateData);

    const slider = document.getElementById("brightness");
    if(slider) slider.oninput = (e) => fetch(`/api/brightness?value=${e.target.value}`);

    const picker = document.getElementById("color-picker") || document.getElementById("color");
    if(picker) {
        picker.oninput = (e) => {
            const hex = e.target.value;
            const r = parseInt(hex.substr(1, 2), 16);
            const g = parseInt(hex.substr(3, 2), 16);
            const b = parseInt(hex.substr(5, 2), 16);
            fetch(`/api/set_color?r=${r}&g=${g}&b=${b}`);
        };
    }
}

// 4. Εκκίνηση
window.onload = () => {
    initChart();
    setupEvents();
    updateData();
    setInterval(updateData, 5000);
};