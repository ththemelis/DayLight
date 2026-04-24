// Ενημέρωση Δεδομένων
async function updateData() {
    try {
        const resState = await fetch("/api/state");
        const state = await resState.json();

        if(document.getElementById("temp")) document.getElementById("temp").innerText = state.temperature.toFixed(1);
        if(document.getElementById("hum")) document.getElementById("hum").innerText = state.humidity.toFixed(1);
        
        const modeEl = document.getElementById("mode") || document.getElementById("mode-text");
        if(modeEl) modeEl.innerText = state.auto ? "AUTO" : "MANUAL";

        const controls = document.getElementById("manual-controls");
        if(controls) {
            controls.style.opacity = state.auto ? "0.3" : "1";
            controls.style.pointerEvents = state.auto ? "none" : "all";
        }
    } catch (e) {
        console.error("Update error:", e);
    }
}

// Event Listeners (με έλεγχο ύπαρξης)
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

// Εκκίνηση
window.onload = () => {
    setupEvents();
    updateData();
    setInterval(updateData, 5000);
};
