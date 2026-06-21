/** @odoo-module **/

import { onMounted } from "@odoo/owl";

function updateClock() {
    const el = document.getElementById("odoo_digital_clock");

    if (!el) return;

    const now = new Date();

    const h = String(now.getHours()).padStart(2, "0");
    const m = String(now.getMinutes()).padStart(2, "0");
    const s = String(now.getSeconds()).padStart(2, "0");

    el.innerHTML = `${h}:${m}:${s}`;
}

setInterval(updateClock, 1000);

// أول تشغيل
setTimeout(updateClock, 500);
