import cv2
import numpy as np
import threading
import time
import json
import os
import sys
import asyncio
from fastapi import FastAPI, Response, Request, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import jwt
import datetime
import bcrypt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

try:
    from . import database, models
except ImportError:
    import database, models

# Initialize SQLite Database Tables
models.Base.metadata.create_all(bind=database.engine)

# --- CORE CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_DIR = os.path.join(BASE_DIR, "test_video")
CONFIG_FILE = os.path.join(BASE_DIR, "parking_config.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Ensure dirs exist
for d in [VIDEO_DIR, FRONTEND_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# --- AI LOADER ---
sys.path.append(os.path.join(BASE_DIR, "ml", "scripts"))
try:
    from detector import ParkingDetector
except ImportError:
    # Fallback for different pathing
    from ml.scripts.detector import ParkingDetector

# --- STATE MANAGEMENT ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

class AppState:
    def __init__(self):
        settings = load_settings()
        self.active_video_path = settings.get("active_video_path")
        self.is_live = settings.get("is_live", False)
        self.output_frame_raw = cv2.imencode(".jpg", np.zeros((720, 1280, 3), np.uint8))[1].tobytes()
        self.output_frame_ai = cv2.imencode(".jpg", np.zeros((720, 1280, 3), np.uint8))[1].tobytes()
        self.parking_status = []
        self.update_counter = 0  # High-performance sync/async bridge
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.detector = ParkingDetector(os.path.join(BASE_DIR, "yolov8n-visdrone.pt"))
        self.user_session = "admin" # Default keep-alive for now to prevent auto-logout

state = AppState()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def get_interpolated_spots(config, path, frame_idx):
    filename = os.path.basename(path)
    data = config.get(path) or config.get(filename)
    if data:
        keyframes = data.get("keyframes", {})
        if "0" in keyframes: return keyframes["0"]
        # Backup if saved under 'spots' key directly
        if "spots" in data: return data["spots"]
    return []

# --- BACKGROUND AI ENGINE ---
def video_processing_loop():
    while not state.stop_event.is_set():
        current_source = state.active_video_path
        
        if not current_source:
            # High-Tech Standby Frame
            standby = np.zeros((720, 1280, 3), np.uint8)
            # Add some cyber grid lines
            for i in range(0, 1280, 40): cv2.line(standby, (i, 0), (i, 720), (20, 20, 20), 1)
            for i in range(0, 720, 40): cv2.line(standby, (0, i), (1280, i), (20, 20, 20), 1)
            
            cv2.putText(standby, "SYSTEM STANDBY", (480, 340), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 243, 0), 2)
            cv2.putText(standby, "Awaiting Source Authorization...", (460, 380), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 1)
            
            _, encoded = cv2.imencode(".jpg", standby)
            with state.lock:
                state.output_frame_raw = encoded.tobytes()
                state.output_frame_ai = encoded.tobytes()
                state.parking_status = []
                state.update_counter += 1
            time.sleep(1.0)
            continue

        cap = cv2.VideoCapture(current_source)
        config = load_config()
        
        while cap.isOpened() and state.active_video_path == current_source:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Loop
                continue

            h, w, _ = frame.shape
            # Get spots for this source
            raw_spots = get_interpolated_spots(config, current_source, 0) # Simplification
            
            # RAW FEED SYNC
            _, encoded_raw = cv2.imencode(".jpg", frame)
            
            # AI FEED SYNC
            viz_frame = frame.copy()
            detection_data = []
            
            if not raw_spots:
                cv2.putText(viz_frame, "UNMAPPED SOURCE", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                # Run AI Detector
                current_spots = [[(int(p[0]*w), int(p[1]*h)) for p in rs] for rs in raw_spots]
                results = state.detector.process_frame(frame, current_spots)
                
                for i, det in enumerate(results['spots']):
                    occupied = det['occupied']
                    pts = np.array(current_spots[i], np.int32).reshape((-1,1,2))
                    color = (0,0,255) if occupied else (0,255,0)
                    cv2.polylines(viz_frame, [pts], True, color, 2)
                    detection_data.append({
                        "spot_id": det['spot_id'], 
                        "occupied": occupied, 
                        "coords_ratio": raw_spots[i]
                    })

            _, encoded_ai = cv2.imencode(".jpg", viz_frame)

            with state.lock:
                state.output_frame_raw = encoded_raw.tobytes()
                state.output_frame_ai = encoded_ai.tobytes()
                state.parking_status = detection_data
                state.update_counter += 1
            
            time.sleep(0.01) # High performance loop
        cap.release()

# Start AI thread
threading.Thread(target=video_processing_loop, daemon=True).start()

# --- API ENDPOINTS ---

@app.get("/")
def get_home(): return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/login")
def get_login(): return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, "SMART LOT_cyber_key_2026", algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/auth")
async def handle_auth(request: Request, db: Session = Depends(database.get_db)):
    data = await request.json()
    username = data.get("username")
    password = data.get("password")
    is_login = data.get("isLogin", True)
    
    if not password:
        raise HTTPException(status_code=400, detail="Missing secure password")

    admin = db.query(models.Admin).filter(models.Admin.username == username).first()
    
    if not is_login:
        # Registration Flow
        if admin:
            raise HTTPException(status_code=400, detail="Username already exists")
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin = models.Admin(username=username, password_hash=hashed)
        db.add(admin)
        db.commit()
        db.refresh(admin)
    else:
        # Login Flow
        if not admin or not bcrypt.checkpw(password.encode('utf-8'), admin.password_hash.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
    expiration = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    token = jwt.encode({"sub": str(admin.id), "username": admin.username, "exp": int(expiration.timestamp())}, "SMART LOT_cyber_key_2026", algorithm="HS256")
    return {"status": "success", "session": token, "admin_id": admin.id}

@app.get("/api/spots")
def get_spots():
    with state.lock:
        active_name = os.path.basename(state.active_video_path) if state.active_video_path else None
        mapping = None
        if active_name:
            config = load_config()
            for k, v in config.items():
                if active_name in k:
                    mapping = v
                    break
        
        return {
            "spots": state.parking_status, 
            "active": active_name,
            "is_live": getattr(state, 'is_live', False),
            "mapping": mapping # Dialogue 1: The 'Digital Twin' data
        }

@app.post("/api/deselect_video", dependencies=[Depends(verify_token)])
def deselect_video():
    state.active_video_path = None
    return {"status": "success"}

@app.get("/raw_feed")
def raw_feed():
    def generate():
        while True:
            with state.lock:
                frame = state.output_frame_raw
            if frame: yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05)
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/ai_feed")
def ai_feed():
    def generate():
        while True:
            with state.lock:
                frame = state.output_frame_ai
            if frame: yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.05)
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/viewer")
def get_viewer(): return FileResponse(os.path.join(FRONTEND_DIR, "viewer.html"))

@app.get("/api/list_videos")
def list_videos():
    vids = []
    if os.path.exists(VIDEO_DIR):
        vids = [f for f in os.listdir(VIDEO_DIR) if f.endswith(('.mp4', '.avi', '.mkv'))]
    
    # Check config for mapping status
    config = load_config()
    video_details = []
    for v in vids:
        path = os.path.normpath(os.path.join(VIDEO_DIR, v))
        # Robust check: if path or filename is in config, it has been mapped
        has_config = (path in config) or (v in config)
        video_details.append({"filename": v, "has_config": has_config})
        
    return {"videos": video_details, "active": os.path.basename(state.active_video_path) if state.active_video_path else None}

@app.post("/api/switch_video", dependencies=[Depends(verify_token)])
async def switch_video(request: Request):
    data = await request.json()
    filename = data.get("filename")
    
    # Check if it's a file in VIDEO_DIR or a URL
    file_path = os.path.join(VIDEO_DIR, filename)
    if os.path.exists(file_path):
        state.active_video_path = file_path
        state.is_live = False
    else:
        state.active_video_path = filename
        state.is_live = True
    
    save_settings({
        "active_video_path": state.active_video_path,
        "is_live": state.is_live
    })
        
    return {"status": "success", "is_live": state.is_live}

@app.post("/api/add_url", dependencies=[Depends(verify_token)])
async def add_url(request: Request):
    data = await request.json()
    url = data.get("url")
    if not url: return {"status": "error"}
    # We treat URL as a filename for the library registry
    return {"status": "success", "url": url}

@app.get("/api/lots")
def public_get_lots(db: Session = Depends(database.get_db)):
    lots = db.query(models.ParkingLot).all()
    results = []
    for l in lots:
        total = db.query(models.ParkingSpot).filter(models.ParkingSpot.lot_id == l.id).count()
        # For simulation, some spots are occupied
        occupied = db.query(models.ParkingSpot).filter(models.ParkingSpot.lot_id == l.id, models.ParkingSpot.status == 'occupied').count()
        results.append({
            "id": l.id,
            "name": l.name,
            "total_slots": total,
            "free_slots": total - occupied
        })
    return {"status": "success", "lots": results}

@app.get("/api/lot/{lot_id}/status")
def get_lot_status(lot_id: int, db: Session = Depends(database.get_db)):
    lot = db.query(models.ParkingLot).filter(models.ParkingLot.id == lot_id).first()
    if not lot: return {"status": "error"}
    
    # Mapping Data (Nodes, Edges, Spots Geometry)
    zones = db.query(models.Zone).filter(models.Zone.lot_id == lot_id).all()
    zone_ids = [z.id for z in zones]
    
    nodes = db.query(models.GraphNode).filter(models.GraphNode.zone_id.in_(zone_ids)).all()
    node_id_to_idx = {n.id: i for i, n in enumerate(nodes)}
    
    # Global Edges
    edges = db.query(models.GraphEdge).filter(models.GraphEdge.node_a_id.in_(node_id_to_idx.keys())).all()
    
    # Spots Geometry and Status
    spots = db.query(models.ParkingSpot).filter(models.ParkingSpot.lot_id == lot_id).all()
    
    res_nodes = [{"id": n.id, "x": n.x, "y": n.y, "label": n.label, "zone_id": n.zone_id} for n in nodes]
    # Adjust coordinates by zone offsets for the global map
    for n in res_nodes:
        zone = next(z for z in zones if z.id == n['zone_id'])
        n['x'] += zone.offset_x / 1000 # Normalizing back or keep as is? Let's use absolute px for now?
        # Wait, Architect saves normalized 0-1. Stitcher uses px. 
        # For driver, let's use absolute space.
        # Use a scaling factor for the global canvas.
        
    res_edges = []
    for e in edges:
        if e.node_a_id in node_id_to_idx and e.node_b_id in node_id_to_idx:
            res_edges.append([node_id_to_idx[e.node_a_id], node_id_to_idx[e.node_b_id], e.manual_weight or e.weight])

    res_spots = []
    for s in spots:
        zone = next(z for z in zones if z.id == s.zone_id)
        # Offset polygon points
        poly = s.polygon_data # stored as [[x,y], [x,y]] normalized
        res_spots.append({
            "spot_id": s.id,
            "spot_index": s.spot_index,
            "status": s.status,
            "occupied": s.status == 'occupied',
            "poly": poly,
            "zone_id": s.zone_id,
            "zone_offset": {"x": zone.offset_x, "y": zone.offset_y}
        })

    return {
        "status": "success",
        "lot_name": lot.name,
        "nodes": res_nodes,
        "edges": res_edges,
        "spots": res_spots
    }

@app.get("/api/lot/{lot_id}/recommendation")
def get_lot_recommendation(lot_id: int, db: Session = Depends(database.get_db)):
    # Find nearest vacant spot to node 0
    lot = db.query(models.ParkingLot).filter(models.ParkingLot.id == lot_id).first()
    if not lot: return {"status": "error"}
    
    zones = db.query(models.Zone).filter(models.Zone.lot_id == lot_id).all()
    zone_ids = [z.id for z in zones]
    
    # Get all nodes to find node 0 (Entrance)
    nodes = db.query(models.GraphNode).filter(models.GraphNode.zone_id.in_(zone_ids)).order_by(models.GraphNode.id).all()
    if not nodes: return {"status": "full"}
    entrance = nodes[0]
    
    available_spots = db.query(models.ParkingSpot).filter(
        models.ParkingSpot.lot_id == lot_id, 
        models.ParkingSpot.status == 'vacant' # Skip occupied AND reserved
    ).all()
    if not available_spots: return {"status": "full"}
    
    best_spot_id = None
    min_dist = float('inf')
    
    # Pre-fetch entrance zone offset to avoid N+1 queries in loop
    entrance_zone = db.query(models.Zone).filter(models.Zone.id == entrance.zone_id).first()
    ex = entrance.x + (entrance_zone.offset_x / 1000 if entrance_zone else 0)
    ey = entrance.y + (entrance_zone.offset_y / 1000 if entrance_zone else 0)

    for s in available_spots:
        # Euclidean in global coordinates:
        zone = next(z for z in zones if z.id == s.zone_id)
        poly = s.polygon_data
        cx = (sum(p[0] for p in poly) / 4) + zone.offset_x / 1000
        cy = (sum(p[1] for p in poly) / 4) + zone.offset_y / 1000
        
        dist = ((cx - ex)**2 + (cy - ey)**2)**0.5
        if dist < min_dist:
            min_dist = dist
            best_spot_id = s.id
            
    return {"status": "success", "recommended_spot_id": best_spot_id}

@app.post("/api/upload_video", dependencies=[Depends(verify_token)])
async def upload_video(file: UploadFile = File(...)):
    if not os.path.exists(VIDEO_DIR): os.makedirs(VIDEO_DIR)
    
    file_path = os.path.join(VIDEO_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    return {"status": "success", "filename": file.filename}

@app.post("/api/clear_library", dependencies=[Depends(verify_token)])
def clear_library():
    import shutil
    if os.path.exists(VIDEO_DIR):
        shutil.rmtree(VIDEO_DIR)
        os.makedirs(VIDEO_DIR)
    state.active_video_path = None
    # Also wipe config if starting fresh
    if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
    return {"status": "success"}

@app.get("/admin")
def get_admin(): return FileResponse(os.path.join(FRONTEND_DIR, "admin.html"))

@app.get("/driver")
def get_driver(): return FileResponse(os.path.join(FRONTEND_DIR, "driver.html"))

@app.get("/architect")
def get_architect(): return FileResponse(os.path.join(FRONTEND_DIR, "architect.html"))

@app.get("/stitcher")
def get_stitcher(): return FileResponse(os.path.join(FRONTEND_DIR, "stitcher.html"))

@app.get("/api/get_frame")
def get_frame(filename: str):
    path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(path): return {"status": "error"}
    cap = cv2.VideoCapture(path)
    ret, frame = cap.read()
    cap.release()
    if ret:
        _, encoded = cv2.imencode(".jpg", frame)
        return Response(content=encoded.tobytes(), media_type="image/jpeg")
    return {"status": "error"}

@app.post("/api/save_config", dependencies=[Depends(verify_token)])
async def save_config(request: Request):
    data = await request.json()
    # Merge with existing
    config = load_config()
    config.update(data)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
    return {"status": "success"}

@app.post("/api/admin/lot/{lot_id}/zone", dependencies=[Depends(verify_token)])
async def add_zone_to_lot(lot_id: int, request: Request, db: Session = Depends(database.get_db)):
    data = await request.json()
    video_source = data.get("video_source")
    zone = db.query(models.Zone).filter(models.Zone.lot_id==lot_id, models.Zone.video_source==video_source).first()
    if not zone:
        zone = models.Zone(lot_id=lot_id, video_source=video_source)
        db.add(zone)
        db.commit()
    return {"status": "success"}

@app.get("/api/admin/lot/{lot_id}/zones", dependencies=[Depends(verify_token)])
def get_zones_for_lot(lot_id: int, db: Session = Depends(database.get_db)):
    zones = db.query(models.Zone).filter(models.Zone.lot_id == lot_id).all()
    res = []
    for z in zones:
        has_config = db.query(models.ParkingSpot).filter(models.ParkingSpot.zone_id == z.id).count() > 0
        res.append({"zone_id": z.id, "filename": z.video_source, "has_config": has_config, "offset_x": z.offset_x, "offset_y": z.offset_y})
    return {"status": "success", "zones": res}

@app.post("/api/admin/zone/{zone_id}/map", dependencies=[Depends(verify_token)])
async def save_zone_map(zone_id: int, request: Request, db: Session = Depends(database.get_db)):
    data = await request.json()
    zone = db.query(models.Zone).filter(models.Zone.id == zone_id).first()
    if not zone: return {"status": "error"}
    
    # 1. Update Nodes (Non-destructive)
    incoming_nodes = data.get("nodes", [])
    existing_nodes = db.query(models.GraphNode).filter(models.GraphNode.zone_id == zone_id).all()
    node_map = {n.id: n for n in existing_nodes}
    
    updated_node_ids = []
    
    for n_data in incoming_nodes:
        nid = n_data.get("id")
        if nid and nid in node_map:
            # Update existing
            node = node_map[nid]
            node.x = n_data["x"]
            node.y = n_data["y"]
            node.label = n_data.get("label", "")
            updated_node_ids.append(node.id)
        else:
            # Create new
            new_node = models.GraphNode(
                zone_id=zone_id, 
                x=n_data["x"], 
                y=n_data["y"], 
                label=n_data.get("label", "")
            )
            db.add(new_node)
            db.flush() # Assign ID without full commit
            updated_node_ids.append(new_node.id)

    # Delete nodes that are gone
    for n in existing_nodes:
        if n.id not in updated_node_ids:
            # Check if this node has global edges before deleting? 
            # Usually better to let user delete carefully.
            db.delete(n)
            
    # 2. Update Edges (Local only)
    # We clear local edges and rebuild from the indices provided
    # Global edges (Cross-zone) are preserved because they use IDs and we didn't delete those nodes!
    db.query(models.GraphEdge).filter(
        models.GraphEdge.node_a_id.in_(updated_node_ids),
        models.GraphEdge.node_b_id.in_(updated_node_ids)
    ).delete(synchronize_session=False)

    for e in data.get("edges", []):
        if e[0] < len(updated_node_ids) and e[1] < len(updated_node_ids):
            edge = models.GraphEdge(
                node_a_id=updated_node_ids[e[0]], 
                node_b_id=updated_node_ids[e[1]],
                weight=0 # Recalculate if needed, or let stitcher handle it
            )
            # Calc weight
            n1 = incoming_nodes[e[0]]
            n2 = incoming_nodes[e[1]]
            edge.weight = ((n1['x']-n2['x'])**2 + (n1['y']-n2['y'])**2)**0.5
            db.add(edge)

    # 3. Update Spots
    # For spots, we currently wipe and recreate but we should preserve status if indices match
    existing_spots = db.query(models.ParkingSpot).filter(models.ParkingSpot.zone_id == zone_id).order_by(models.ParkingSpot.spot_index).all()
    status_map = {s.spot_index: s.status for s in existing_spots}
    
    db.query(models.ParkingSpot).filter(models.ParkingSpot.zone_id == zone_id).delete()
    
    for i, s_data in enumerate(data.get("spots", [])):
        # If s_data is an object with status, use it. Otherwise use saved status.
        status = "vacant"
        poly = s_data
        if isinstance(s_data, dict):
            status = s_data.get("status", status_map.get(i, "vacant"))
            poly = s_data.get("poly")
            
        spot = models.ParkingSpot(
            lot_id=zone.lot_id, 
            zone_id=zone_id, 
            polygon_data=poly, 
            spot_index=i, 
            status=status
        )
        db.add(spot)
        
    db.commit()
    return {"status": "success"}

@app.get("/api/admin/zone/{zone_id}/map", dependencies=[Depends(verify_token)])
def get_zone_map(zone_id: int, db: Session = Depends(database.get_db)):
    zone = db.query(models.Zone).filter(models.Zone.id == zone_id).first()
    if not zone: return {"status": "error"}

    nodes = db.query(models.GraphNode).filter(models.GraphNode.zone_id == zone_id).order_by(models.GraphNode.id).all()
    spots = db.query(models.ParkingSpot).filter(models.ParkingSpot.zone_id == zone_id).order_by(models.ParkingSpot.spot_index).all()
    
    node_id_to_idx = {n.id: i for i, n in enumerate(nodes)}
    res_nodes = [{"id": n.id, "x": n.x, "y": n.y, "label": n.label} for n in nodes]
    res_edges = []
    if nodes:
        node_ids = [n.id for n in nodes]
        edges = db.query(models.GraphEdge).filter(
            models.GraphEdge.node_a_id.in_(node_ids),
            models.GraphEdge.node_b_id.in_(node_ids)
        ).all()
        for e in edges:
            if e.node_a_id in node_id_to_idx and e.node_b_id in node_id_to_idx:
                res_edges.append([node_id_to_idx[e.node_a_id], node_id_to_idx[e.node_b_id]])
                
    res_spots = [{"poly": s.polygon_data, "status": s.status} for s in spots]
    return {"status": "success", "filename": zone.video_source, "map": {"nodes": res_nodes, "edges": res_edges, "spots": res_spots}}

@app.get("/api/admin/lot/{lot_id}/map", dependencies=[Depends(verify_token)])
def get_lot_map(lot_id: int, db: Session = Depends(database.get_db)):
    zones = db.query(models.Zone).filter(models.Zone.lot_id == lot_id).all()
    zone_data = []
    zone_ids = [z.id for z in zones]
    all_nodes = db.query(models.GraphNode).filter(models.GraphNode.zone_id.in_(zone_ids)).all()
    
    # Global edges: where both nodes belong to this lot's zones, but optionally different zones
    node_ids = [n.id for n in all_nodes]
    edges = db.query(models.GraphEdge).filter(models.GraphEdge.node_a_id.in_(node_ids)).all()
    
    for z in zones:
        z_nodes = [{"id": n.id, "x": n.x, "y": n.y} for n in all_nodes if n.zone_id == z.id]
        z_spots = [{"id": s.id, "poly": s.polygon_data} for s in db.query(models.ParkingSpot).filter(models.ParkingSpot.zone_id == z.id).all()]
        zone_data.append({
            "id": z.id,
            "filename": z.video_source,
            "offset_x": z.offset_x,
            "offset_y": z.offset_y,
            "nodes": z_nodes,
            "spots": z_spots
        })
        
    global_edges = [{"id": e.id, "node_a": e.node_a_id, "node_b": e.node_b_id} for e in edges]
    return {"status": "success", "zones": zone_data, "edges": global_edges}

@app.put("/api/admin/zone/{zone_id}/offset", dependencies=[Depends(verify_token)])
async def update_zone_offset(zone_id: int, request: Request, db: Session = Depends(database.get_db)):
    data = await request.json()
    zone = db.query(models.Zone).filter(models.Zone.id == zone_id).first()
    if not zone: return {"status": "error"}
    zone.offset_x = data.get("offset_x", 0)
    zone.offset_y = data.get("offset_y", 0)
    db.commit()
    return {"status": "success"}

@app.post("/api/admin/lot/{lot_id}/edge", dependencies=[Depends(verify_token)])
async def add_global_edge(lot_id: int, request: Request, db: Session = Depends(database.get_db)):
    data = await request.json()
    n_a = db.query(models.GraphNode).filter(models.GraphNode.id == data.get("node_a_id")).first()
    n_b = db.query(models.GraphNode).filter(models.GraphNode.id == data.get("node_b_id")).first()
    if n_a and n_b:
        z_a = db.query(models.Zone).filter(models.Zone.id == n_a.zone_id).first()
        z_b = db.query(models.Zone).filter(models.Zone.id == n_b.zone_id).first()
        gx1 = n_a.x + z_a.offset_x
        gy1 = n_a.y + z_a.offset_y
        gx2 = n_b.x + z_b.offset_x
        gy2 = n_b.y + z_b.offset_y
        w = ((gx1 - gx2)**2 + (gy1 - gy2)**2)**0.5
        edge = models.GraphEdge(node_a_id=n_a.id, node_b_id=n_b.id, weight=w, manual_weight=data.get("manual_weight"))
        db.add(edge)
        db.commit()
        return {"status": "success", "edge_id": edge.id}
    return {"status": "error"}

@app.delete("/api/admin/edge/{edge_id}", dependencies=[Depends(verify_token)])
async def delete_edge(edge_id: int, db: Session = Depends(database.get_db)):
    edge = db.query(models.GraphEdge).filter(models.GraphEdge.id == edge_id).first()
    if edge:
        db.delete(edge)
        db.commit()
        return {"status": "success"}
    return {"status": "error"}

@app.post("/api/admin/lot/{lot_id}/stitch/wipe", dependencies=[Depends(verify_token)])
async def wipe_stitch(lot_id: int, db: Session = Depends(database.get_db)):
    zones = db.query(models.Zone).filter(models.Zone.lot_id == lot_id).all()
    zone_ids = [z.id for z in zones]
    for z in zones:
        z.offset_x = 0.0
        z.offset_y = 0.0
    nodes = db.query(models.GraphNode).filter(models.GraphNode.zone_id.in_(zone_ids)).all()
    node_map = {n.id: n.zone_id for n in nodes}
    edges = db.query(models.GraphEdge).filter(models.GraphEdge.node_a_id.in_(node_map.keys())).all()
    for e in edges:
        z_a = node_map.get(e.node_a_id)
        z_b = node_map.get(e.node_b_id)
        if z_a != z_b:
            db.delete(e)
    db.commit()
    return {"status": "success"}

@app.get("/api/admin/lots", dependencies=[Depends(verify_token)])
def get_lots(db: Session = Depends(database.get_db)):
    lots = db.query(models.ParkingLot).all()
    return {"status": "success", "lots": [{"id": l.id, "name": l.name, "zone_type": l.zone_type} for l in lots]}

@app.delete("/api/admin/lot/{lot_id}", dependencies=[Depends(verify_token)])
async def delete_lot(lot_id: int, db: Session = Depends(database.get_db)):
    lot = db.query(models.ParkingLot).filter(models.ParkingLot.id == lot_id).first()
    if not lot: return {"status": "error"}
    db.delete(lot)
    db.commit()
    return {"status": "success"}

@app.put("/api/admin/lot/{lot_id}/type", dependencies=[Depends(verify_token)])
async def update_lot_type(lot_id: int, request: Request, db: Session = Depends(database.get_db)):
    data = await request.json()
    lot = db.query(models.ParkingLot).filter(models.ParkingLot.id == lot_id).first()
    if not lot: return {"status": "error"}
    lot.zone_type = data.get("type", "multi")
    db.commit()
    return {"status": "success"}

@app.post("/api/admin/lot/{lot_id}/reset", dependencies=[Depends(verify_token)])
async def reset_lot(lot_id: int, db: Session = Depends(database.get_db)):
    lot = db.query(models.ParkingLot).filter(models.ParkingLot.id == lot_id).first()
    if not lot: return {"status": "error"}
    db.query(models.Zone).filter(models.Zone.lot_id == lot.id).delete()
    db.query(models.ParkingSpot).filter(models.ParkingSpot.lot_id == lot.id).delete()
    db.query(models.GraphNode).filter(models.GraphNode.zone_id.in_(
        db.query(models.Zone.id).filter(models.Zone.lot_id == lot.id)
    )).delete(synchronize_session=False)
    db.commit()
    return {"status": "success"}

@app.post("/api/admin/create_lot", dependencies=[Depends(verify_token)])
async def create_lot(request: Request, db: Session = Depends(database.get_db)):
    data = await request.json()
    new_lot = models.ParkingLot(name=data.get("name", "Unnamed Lot"), zone_type=data.get("zone_type", "single"))
    db.add(new_lot)
    db.commit()
    db.refresh(new_lot)
    return {"status": "success", "lot_id": new_lot.id, "name": new_lot.name, "zone_type": new_lot.zone_type}

# Static folders for styles/scripts
app.mount("/mobile", StaticFiles(directory=os.path.join(FRONTEND_DIR, "mobile")), name="mobile")
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
