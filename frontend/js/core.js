/**
 * SMART LOT CORE ENGINE
 * Shared API & HTTP Polling Logic
 */

const API_BASE_URL = "";

function getHeaders() {
    const token = localStorage.getItem('admin_token');
    return {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
}

const API = {
    async getLots() {
        const r = await fetch(`${API_BASE_URL}/api/lots`);
        return await r.json();
    },
    async getLotStatus(lot_id) {
        const r = await fetch(`${API_BASE_URL}/api/lot/${lot_id}/status`);
        return await r.json();
    },
    async getLotRecommendation(lot_id) {
        const r = await fetch(`${API_BASE_URL}/api/lot/${lot_id}/recommendation`);
        return await r.json();
    },
    async fetchSpots() {
        const r = await fetch(`${API_BASE_URL}/api/spots`);
        return await r.json();
    },
    async listVideos() {
        const r = await fetch(`${API_BASE_URL}/api/list_videos`);
        return await r.json();
    },
    async switchVideo(filename) {
        return fetch(`${API_BASE_URL}/api/switch_video`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ filename })
        }).then(r => r.json());
    },
    async deselectVideo() {
        const token = localStorage.getItem('admin_token');
        const r = await fetch(`${API_BASE_URL}/api/deselect_video`, { 
            method: 'POST',
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
         });
        return await r.json();
    },
    async addUrl(url) {
        const r = await fetch(`${API_BASE_URL}/api/add_url`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ url })
        });
        return await r.json();
    },
    async getLots() {
        const r = await fetch(`${API_BASE_URL}/api/admin/lots`, { headers: getHeaders() });
        return await r.json();
    },
    async createLot(name, zone_type) {
        const r = await fetch(`${API_BASE_URL}/api/admin/create_lot`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ name, zone_type })
        });
        return await r.json();
    },
    async deleteLot(lot_id) {
        const r = await fetch(`${API_BASE_URL}/api/admin/lot/${lot_id}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        return await r.json();
    },
    async resetLot(lot_id) {
        const r = await fetch(`${API_BASE_URL}/api/admin/lot/${lot_id}/reset`, {
            method: 'POST',
            headers: getHeaders()
        });
        return await r.json();
    },
    async addZoneToLot(lot_id, video_source) {
        const r = await fetch(`${API_BASE_URL}/api/admin/lot/${lot_id}/zone`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ video_source })
        });
        return await r.json();
    },
    async updateLotType(lot_id, type) {
        const r = await fetch(`${API_BASE_URL}/api/admin/lot/${lot_id}/type`, {
            method: 'PUT',
            headers: getHeaders(),
            body: JSON.stringify({ type })
        });
        return await r.json();
    },
    async getZonesForLot(lot_id) {
        const r = await fetch(`${API_BASE_URL}/api/admin/lot/${lot_id}/zones`, {
            headers: getHeaders()
        });
        return await r.json();
    },
    async saveZoneMap(zone_id, mapData) {
        const r = await fetch(`${API_BASE_URL}/api/admin/zone/${zone_id}/map`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(mapData)
        });
        return await r.json();
    },
    async getZoneMap(zone_id) {
        const r = await fetch(`${API_BASE_URL}/api/admin/zone/${zone_id}/map`, {
            headers: getHeaders()
        });
        return await r.json();
    },
    async getLotMap(lot_id) {
        const r = await fetch(`${API_BASE_URL}/api/admin/lot/${lot_id}/map`, { headers: getHeaders() });
        return await r.json();
    },
    async updateZoneOffset(zone_id, offset_x, offset_y) {
        const r = await fetch(`${API_BASE_URL}/api/admin/zone/${zone_id}/offset`, {
            method: 'PUT',
            headers: getHeaders(),
            body: JSON.stringify({ offset_x, offset_y })
        });
        return await r.json();
    },
    async addGlobalEdge(lot_id, node_a_id, node_b_id, manual_weight=null) {
        const r = await fetch(`${API_BASE_URL}/api/admin/lot/${lot_id}/edge`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ node_a_id, node_b_id, manual_weight })
        });
        return await r.json();
    },
    async deleteEdge(edge_id) {
        const r = await fetch(`${API_BASE_URL}/api/admin/edge/${edge_id}`, {
            method: 'DELETE',
            headers: getHeaders()
        });
        return await r.json();
    },
    async wipeStitch(lot_id) {
        const r = await fetch(`${API_BASE_URL}/api/admin/lot/${lot_id}/stitch/wipe`, {
            method: 'POST',
            headers: getHeaders()
        });
        return await r.json();
    },
    async uploadVideo(formData) {
        const token = localStorage.getItem('admin_token');
        const r = await fetch(`${API_BASE_URL}/api/upload_video`, {
            method: 'POST',
            headers: token ? { 'Authorization': `Bearer ${token}` } : {},
            body: formData
        });
        return await r.json();
    },
    async clearLibrary() {
        const token = localStorage.getItem('admin_token');
        const r = await fetch(`${API_BASE_URL}/api/clear_library`, { 
            method: 'POST',
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
         });
        return await r.json();
    },
    async saveConfig(config) {
        const r = await fetch(`${API_BASE_URL}/api/save_config`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(config)
        });
        return await r.json();
    },
    async fetchRecommendation() {
        const r = await fetch(`${API_BASE_URL}/api/recommendation`);
        return await r.json();
    }
};

function runHeartbeat(callback) {
    setInterval(async () => {
        try {
            const data = await API.fetchSpots();
            if (data) callback(data);
        } catch(e) { console.error("Heartbeat error", e); }
    }, 500);
}
