import cv2
import numpy as np
from ultralytics import YOLO
from shapely.geometry import Polygon, Point
from typing import List, Dict, Any

class ParkingDetector:
    def __init__(self, model_path: str = "yolov8n-visdrone.pt"):
        """
        Initializes the YOLO model for vehicle detection.
        Args:
            model_path (str): Path to the YOLO weight file.
        """
        self.model = YOLO(model_path)
        print(f"ParkingDetector initialized with model: {model_path}")
        
        # Combined classes for robustness:
        # COCO: 2=Car, 3=Motorcycle, 5=Bus, 7=Truck
        # VisDrone: 3=Car, 4=Van, 5=Truck, 6=Tricycle, 9=Motorcycle
        # Union: [2, 3, 4, 5, 6, 7, 8, 9]
        self.vehicle_classes = [2, 3, 4, 5, 6, 7, 8, 9] 

    def process_frame(self, frame: np.ndarray, parking_spots: List[List[tuple]], conf: float = 0.15) -> Dict[str, Any]:
        """
        Processes a single video frame to detect vehicles and determine parking spot occupancy.
        
        Args:
            frame (np.ndarray): The input image frame.
            parking_spots (List[List[tuple]]): A list where each element is a list of (x, y) tuples defining a spot polygon.
            conf (float): The confidence threshold for detection.
            
        Returns:
            Dict[str, Any]: A dictionary containing detection results and spot occupancy status.
        """
        # Lower confidence to catch more vehicles
        results = self.model(frame, classes=self.vehicle_classes, conf=conf, verbose=False)
        detections = results[0].boxes.data.cpu().numpy() # [x1, y1, x2, y2, conf, class_id]
        
        # Debug: un-comment if needed
        # print(f"Detected {len(detections)} vehicles.")

        spot_status = []
        
        for i, spot_coords in enumerate(parking_spots):
            spot_poly = Polygon(spot_coords)
            is_occupied = False
            overlap_area = 0.0

            if not spot_poly.is_valid:
                # Handle invalid polygons (self-intersecting) by fixing buffer(0)
                spot_poly = spot_poly.buffer(0)

            for det in detections:
                x1, y1, x2, y2, conf, cls = det
                # Create a polygon for the detected vehicle (using bounding box)
                vehicle_box = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
                
                # Check for intersection
                if spot_poly.intersects(vehicle_box):
                    intersection = spot_poly.intersection(vehicle_box).area
                    spot_area = spot_poly.area
                    # Heuristic: If significant overlap (e.g., > 15% of spot area)
                    # Lower threshold to ensure even partial overlaps trigger "Occupied"
                    if intersection / spot_area > 0.15:
                         is_occupied = True
                         overlap_area = intersection
                         break # Occupied by at least one vehicle
            
            spot_status.append({
                "spot_id": i + 1,
                "occupied": is_occupied,
                "coordinates": spot_coords # Return the coordinates to visualize
            })

        return {
            "vehicle_count": len(detections),
            "spots": spot_status,
            "raw_detections": detections.tolist()
        }

if __name__ == "__main__":
    # Example usage for testing
    detector = ParkingDetector()
    
    # Mock parking spots (simple rectangles for demo)
    # In a real scenario, these would come from the Admin UI setup.
    mock_spots = [
        [(100, 100), (200, 100), (200, 200), (100, 200)], # Spot 1
        [(250, 100), (350, 100), (350, 200), (250, 200)], # Spot 2
    ]
    
    # Create a dummy image (black frame)
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Run detection
    result = detector.process_frame(dummy_frame, mock_spots)
    print("Detection Result:", result)
