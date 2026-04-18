# SMART LOT: ADAPTIVE PARKING MANAGEMENT SYSTEM

This document outlines the massive architectural expansion of the SmartPark system into a multi-lot, multi-zone platform backed by a robust database.

## Phase 1: Core Database & Architecture Migration
*The foundational step. Before we can stitch cameras or build lots, we need a real database to hold the relational data.*
**Goal:** Replace the flat `config.json` file with a relational SQL Database.

- **Entity Creation (`models.py`):**
  - `Admin`: `admin_id`, `username`, `password_hash`
  - `ParkingLot`: `lot_id`, `name`, `admin_id`, `zone_type` (single/multi)
  - `Zone`: `zone_id`, `lot_id`, `video_source`, `offset_x`, `offset_y`
  - `ParkingSpot`: `spot_id`, `lot_id`, `zone_id`, `polygon_data`, `status`
  - `GraphNode`: `node_id`, `zone_id`, `x`, `y`, `label`
  - `GraphEdge`: `id`, `node_a`, `node_b`, `weight`, `manual_weight`
- **Engine Refactor:** Update FastAPI AI engine to read/write state to the DB instead of JSON natively.

> [!NOTE] 
> **PostgreSQL vs SQLite:** PostgreSQL is extremely powerful and fully suitable for our application. The only downside is it requires you to install a PostgreSQL server on your Windows machine, whereas SQLite is completely built-in to Python instantly. **Recommendation:** We will build the system using **SQLAlchemy**, a library that lets us write universal database code. We can start with SQLite for instant testing today, and seamlessly swap a single line of code to use PostgreSQL tomorrow if you decide to install it!

## Phase 2: Role-Based Entry & Admin Security
*Locking the gates and establishing the two user flows.*
**Goal:** Implement JWT Authentication and split the user flows.

- **App Entry:** [DONE]
- **JWT Locking:** [DONE]
- **Admin Dashboard:** [DONE]

## Phase 3: Multi-Zone Mapping & Camera Stitching
*The most complex upgrade—enabling massive lots.*
**Goal:** Allow Admins to map multiple zones and stitch them into one Global Graph.

- **Single Zone Flow:** [DONE]
- **Multi-Zone Flow:** [DONE]
- **Workspace Canvas:** [DONE]
- **Graph Stitching:** [DONE]

## Phase 4: User Parking Lot Selection Flow
*Giving the driver choices.*
**Goal:** Allow drivers to see available capacity before routing.

- **Selection Screen:** [DONE]
- **Load Global Graph:** [DONE]
- **Dynamic Routing:** [DONE]

## Phase 5: Driver Experience Enhancements (UX)
*Polishing the interface.*
**Goal:** Introduce Haptics and Reserved Spots.

- **Haptics/Audio:** [DONE]
- **Reserved Status:** [DONE]
- **Zone Swapping:** [DONE]

## Phase 6: Vehicle Tracking ("Find My Car")
*The final cherry on top.*
**Goal:** Reverse the Dijkstra routing.

- **Save Spot:** [DONE]
- **Reverse Route:** [DONE]

## Phase 7: Cloud-Ready Database Migration (PostgreSQL)
*Preparing for the next-level scale.*
**Goal:** Enable a seamless, toggleable switch to PostgreSQL with a 100% safe revert to SQLite.

- **Environment-DRY Architecture**: Refactor `database.py` to prioritize `DATABASE_URL` environment variables but default to `sqlite:///./smartpark.db`.
- **Dependency Isolation**: Add `psycopg2-binary` as an optional dependency for enterprise deployment.
- **Seamless Migration Tool**: Create a standalone script to clone the local SQLite state into a remote PostgreSQL instance without data loss.
- **Fail-Safe**: System must automatically stay on SQLite if no Postgres configuration is detected, ensuring "It Just Works" locally.

