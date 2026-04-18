import cv2
import numpy as np
import json
import os
import copy

class MapArchitect:
    def __init__(self, video_path):
        self.video_path = video_path
        self.config_file = 'parking_config.json'
        self.cap = cv2.VideoCapture(video_path)
        
        if not self.cap.isOpened():
            print(f"Error: Cannot open {video_path}")
            return

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame_idx = 0
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        # --- Multi-Layer Data ---
        # 1. Spots Layer: { frame_idx: [ [pts], ... ] }
        self.keyframes = {} 
        # 2. Graph Layer (Static - doesn't change with frames usually)
        self.nodes = [] # List of { "id": int, "x": int, "y": int, "type": str }
        self.edges = [] # List of { "from": id, "to": id }
        
        self.load_config()

        # --- UI State ---
        self.mode = "SPOTS" # Modes: SPOTS, NODES, PATHS
        self.temp_points = [] 
        self.selected_node_idx = -1
        self.dragging_id = -1 # -1: none, >=0: node, -2: spot
        
        # For path creation
        self.active_node_id = None 

        cv2.namedWindow('SmartPark Map Architect', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('SmartPark Map Architect', 1280, 720)
        cv2.setMouseCallback('SmartPark Map Architect', self.mouse_callback)
        cv2.createTrackbar('Frame', 'SmartPark Map Architect', 0, max(1, self.total_frames-1), self.on_trackbar)

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                full_data = json.load(f)
                data = full_data.get(self.video_path, {})
                
                # Handle legacy (list) or new (dict) format
                if isinstance(data, list):
                    self.keyframes = {0: data}
                elif isinstance(data, dict):
                    # Check if it's the new Graph structure
                    if "keyframes" in data:
                        self.keyframes = {int(k): v for k, v in data["keyframes"].items()}
                        self.nodes = data.get("nodes", [])
                        self.edges = data.get("edges", [])
                    else:
                        self.keyframes = {int(k): v for k, v in data.items()}

    def save_config(self):
        full_data = {}
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                full_data = json.load(f)
        
        # Convert keyframes to string keys for JSON
        json_keyframes = {str(k): v for k, v in self.keyframes.items()}
        
        full_data[self.video_path] = {
            "keyframes": json_keyframes,
            "nodes": self.nodes,
            "edges": self.edges
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(full_data, f, indent=4)
        print(f"Saved Map Data (Graph + Spots) to {self.config_file}")

    def on_trackbar(self, val):
        self.current_frame_idx = val
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, val)

    def get_interpolated_spots(self, idx):
        if idx in self.keyframes: return copy.deepcopy(self.keyframes[idx])
        sorted_keys = sorted(self.keyframes.keys())
        if not sorted_keys: return []
        prev_k = None; next_k = None
        for k in sorted_keys:
            if k < idx: prev_k = k
            if k > idx: next_k = k; break
        if prev_k is None: return self.keyframes[sorted_keys[0]]
        if next_k is None: return self.keyframes[sorted_keys[-1]]
        
        s0 = self.keyframes[prev_k]; s1 = self.keyframes[next_k]
        if len(s0) != len(s1): return s0
        ratio = (idx - prev_k) / (next_k - prev_k)
        res = []
        for i in range(len(s0)):
            p0 = s0[i]; p1 = s1[i]
            if len(p0) != len(p1): res.append(p0); continue
            interp = [[int(p0[j][0] + (p1[j][0]-p0[j][0])*ratio), int(p0[j][1] + (p1[j][1]-p0[j][1])*ratio)] for j in range(len(p0))]
            res.append(interp)
        return res

    def mouse_callback(self, event, x, y, flags, param):
        spots = self.get_interpolated_spots(self.current_frame_idx)
        
        if event == cv2.EVENT_LBUTTONDOWN:
            if self.mode == "SPOTS":
                # Reshape/Move logic (Simplified for this script)
                self.temp_points.append([x,y])
                if len(self.temp_points) == 4:
                    self.keyframes[self.current_frame_idx] = spots + [self.temp_points]
                    self.temp_points = []
            
            elif self.mode == "NODES":
                # Check for Dragging node
                for i, n in enumerate(self.nodes):
                    if np.sqrt((n['x']-x)**2 + (n['y']-y)**2) < 15:
                        self.selected_node_idx = i
                        return
                # Create Node
                node_type = "junction"
                if flags & cv2.EVENT_FLAG_SHIFTKEY: node_type = "entrance"
                if flags & cv2.EVENT_FLAG_CTRLKEY: node_type = "spot"
                
                new_id = len(self.nodes)
                self.nodes.append({"id": new_id, "x": x, "y": y, "type": node_type})

            elif self.mode == "PATHS":
                # Path creation logic
                for n in self.nodes:
                    if np.sqrt((n['x']-x)**2 + (n['y']-y)**2) < 15:
                        if self.active_node_id is None:
                            self.active_node_id = n['id']
                        else:
                            if self.active_node_id != n['id']:
                                self.edges.append({"from": self.active_node_id, "to": n['id']})
                            self.active_node_id = None
                        return

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.mode == "NODES" and self.selected_node_idx != -1:
                self.nodes[self.selected_node_idx]['x'] = x
                self.nodes[self.selected_node_idx]['y'] = y

        elif event == cv2.EVENT_LBUTTONUP:
            self.selected_node_idx = -1

        elif event == cv2.EVENT_RBUTTONDOWN:
            # Delete logic
            if self.mode == "NODES":
                for i, n in enumerate(self.nodes):
                    if np.sqrt((n['x']-x)**2 + (n['y']-y)**2) < 15:
                        nid = self.nodes[i]['id']
                        self.nodes.pop(i)
                        self.edges = [e for e in self.edges if e['from'] != nid and e['to'] != nid]
                        break
            elif self.mode == "SPOTS":
                for i, s in enumerate(spots):
                    if cv2.pointPolygonTest(np.array(s), (x,y), False) >= 0:
                        spots.pop(i)
                        self.keyframes[self.current_frame_idx] = spots
                        break

    def run(self):
        while True:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)
            ret, frame = self.cap.read()
            if not ret: break
            
            spots = self.get_interpolated_spots(self.current_frame_idx)
            
            # --- Draw Graph Edges ---
            for e in self.edges:
                n1 = next(n for n in self.nodes if n['id'] == e['from'])
                n2 = next(n for n in self.nodes if n['id'] == e['to'])
                cv2.line(frame, (n1['x'], n1['y']), (n2['x'], n2['y']), (255, 100, 0), 2)

            # --- Draw Spots ---
            for s in spots:
                pts = np.array(s, np.int32).reshape((-1, 1, 2))
                cv2.polylines(frame, [pts], True, (0, 255, 0), 2)

            # --- Draw Nodes ---
            for n in self.nodes:
                color = (255, 255, 255) # Junction
                if n['type'] == "entrance": color = (0, 255, 255) # Yellow
                if n['type'] == "spot": color = (0, 0, 255) # Blue
                if n['id'] == self.active_node_id: color = (0, 165, 255) # Orange highlighting
                
                cv2.circle(frame, (n['x'], n['y']), 8, color, -1)
                cv2.putText(frame, str(n['id']), (n['x']+10, n['y']), cv2.FONT_HERSHEY_PLAIN, 1, (255,255,255), 1)

            # --- Drawing Temp Lines ---
            if self.mode == "PATHS" and self.active_node_id is not None:
                n_active = next(n for n in self.nodes if n['id'] == self.active_node_id)
                cv2.line(frame, (n_active['x'], n_active['y']), (500,500), (0, 165, 255), 1) # Just a placeholder

            # --- UI Overlay ---
            cv2.putText(frame, f"MODE: {self.mode}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
            cv2.putText(frame, "[1] Spots | [2] Nodes | [3] Paths | [S] Save | [ESC] Exit", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)
            cv2.putText(frame, "NODES: Shift+Click=Entrance, Ctrl+Click=SpotAnchor", (20, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150,150,150), 1)

            cv2.imshow('SmartPark Map Architect', frame)
            key = cv2.waitKey(20) & 0xFF
            if key == 27: break
            elif key == ord('1'): self.mode = "SPOTS"
            elif key == ord('2'): self.mode = "NODES"
            elif key == ord('3'): self.mode = "PATHS"
            elif key == ord('s'): self.save_config()

        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    VIDEO = r"C:\Users\yamin\CSProj12\test_video\video2.mp4"
    arch = MapArchitect(VIDEO)
    arch.run()
