/**
 * SMART LOT CORE ENGINE
 * Shared API & Real-time Sync Logic
 */

const API = {
    async fetchSpots() {
        const r = await fetch('/api/spots');
        return await r.json();
    },
    async listVideos() {
        const r = await fetch('/api/list_videos');
        return await r.json();
    },
    async switchVideo(filename) {
        return fetch('/api/switch_video', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        }).then(r => r.json());
    },
    async deselectVideo() {
        const r = await fetch('/api/deselect_video', { method: 'POST' });
        return await r.json();
    },
    async addUrl(url) {
        const r = await fetch('/api/add_url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        return await r.json();
    },
    async uploadVideo(formData) {
        const r = await fetch('/api/upload_video', {
            method: 'POST',
            body: formData
        });
        return await r.json();
    },
    async clearLibrary() {
        const r = await fetch('/api/clear_library', { method: 'POST' });
        return await r.json();
    },
    async saveConfig(config) {
        const r = await fetch('/api/save_config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        return await r.json();
    },
    async fetchRecommendation() {
        const r = await fetch('/api/recommendation');
        return await r.json();
    }
};

function runHeartbeat(callback) {
    setInterval(async () => {
        try {
            const data = await API.fetchSpots();
            if (data) callback(data);
        } catch (e) { }
    }, 500);
}
