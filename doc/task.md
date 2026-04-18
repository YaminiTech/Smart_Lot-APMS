# SMART LOT: ADAPTIVE PARKING MANAGEMENT SYSTEM - Task History

### Phase 1: Core Database & Architecture Migration
- [x] Implement SQLAlchemy ORM and configure SQLite engine
- [x] Define relational entities (`ParkingLot`, `Zone`, `ParkingSpot`, `GraphNode`, `GraphEdge`)
- [x] Refactor FastAPI to read/write state natively from the database instead of `config.json`

### Phase 2: Role-Based Entry & Admin Security
- [x] Build landing screen with `[Continue as Admin]` vs `[Find Parking]` roles
- [x] Implement PyJWT Authentication for Admin logins and secure `/api/admin` routes
- [x] Build Admin Dashboard "Create/Edit Parking Lot" selection modal

### Phase 3: Multi-Zone Mapping & Camera Stitching
- [x] Implement Single-Zone mapping logic (1 camera, 1 graph)
- [x] Implement Multi-Zone workspace allowing Admins to upload multiple videos to one lot
- [x] Allow Admins to define `offset_x`/`offset_y` coordinate offsets for connecting individual zones
- [x] Build Python Backend engine logic to stitch isolated zone graphs into one massive Global Graph

### Phase 3.5: Stitcher Accessibility & Portals
- [x] Add explicit SQL columns for Node Labels and Manual Path Weights.
- [x] Update `architect.html` to allow Admins to name nodes ("Portals" / Entrances/Exits).
- [x] Update `stitcher.html` to visually render spots and named Portals.
- [x] Render a new button to Wipe Stitching (Reset offsets to 0,0 and destroy global edges).

### Phase 4: User Parking Lot Selection Flow
- [x] Build dynamic UI fetching all available Parking Lots and rendering their total capacity
- [x] Load the unified stitched 2D Map for the selected lot on the UI canvas
- [x] Refactor Dijkstra routing algorithm to traverse the unified Global Graph across disjoint zones

### Phase 5: Driver Experience Enhancements (UX)
- [x] Integrate Audio / Haptic Feedback when navigated spots become occupied
- [x] Implement Admin-controlled Gold 'Reserved' spots that the Dijkstra router dynamically avoids
- [x] Implement sleek multi-camera dropdown HUD for the driver to manually switch zone streams

### Phase 6: Vehicle Tracking ("Find My Car")
- [x] Build a robust UI switch allowing drivers to save their exact parked location
- [x] Write logic to invert the shortest-path algorithm, routing drivers back from the Spot to the Main Entrance

### Phase 7: Cloud-Ready Database & Revert Logic
- [x] Refactor `database.py` to support dynamic `DATABASE_URL` (SQLite Default)
- [x] Create `migrate_to_postgres.py` data migration utility
- [x] Document the "Safe Revert" process in README for emergency rollbacks
