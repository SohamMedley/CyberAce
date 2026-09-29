/* CyberAce — Global Interactions */

// Nav scroll state
const nav = document.querySelector('.nav');
if (nav) window.addEventListener('scroll', () => nav.classList.toggle('scrolled', window.scrollY > 20));

// API base: /api proxies to backend on Render; localhost for dev
window.API = (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
    ? 'http://localhost:8000/api'
    : '/api';

// File helpers
window.readText = file => new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(r.result);
    r.onerror = rej;
    r.readAsText(file);
});
window.readDataURL = file => new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(r.result);
    r.onerror = rej;
    r.readAsDataURL(file);
});
window.loadPDF = () => {
    if (window.pdfjsLib) return Promise.resolve();
    return new Promise((res, rej) => {
        const s = document.createElement('script');
        s.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
        s.onload = () => { window.pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'; res(); };
        s.onerror = rej;
        document.head.appendChild(s);
    });
};
window.pdfText = async file => {
    await window.loadPDF();
    const buf = await file.arrayBuffer();
    const pdf = await window.pdfjsLib.getDocument({data: buf}).promise;
    let t = '';
    for (let i=1; i<=Math.min(pdf.numPages, 10); i++) {
        const p = await pdf.getPage(i);
        const c = await p.getTextContent();
        t += c.items.map(x => x.str).join(' ') + '\n';
    }
    return t;
};

// Health check + log AI status
(async () => {
    try {
        const h = await fetch(window.API + '/health');
        const d = await h.json();
        console.log(`CyberAce online · AI: ${d.ai ? 'enabled ✓' : 'disabled (add GROQ_API_KEY)'}`);
    } catch(e) {}
})();
