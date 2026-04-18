import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from . import models, database

def migrate():
    source_url = "sqlite:///./smart_lot.db"
    dest_url = os.getenv("DATABASE_URL")
    
    if not dest_url or dest_url.startswith("sqlite"):
        print("ERROR: Please set DATABASE_URL environment variable to a PostgreSQL target.")
        return

    print(f"MIGRATION: [Local SQLite] -> [PostgreSQL]")
    
    # Engines
    src_engine = create_engine(source_url)
    dst_engine = create_engine(dest_url)
    
    # Create tables in destination
    models.Base.metadata.create_all(bind=dst_engine)
    
    with src_engine.connect() as src_conn, dst_engine.connect() as dst_conn:
        src_session = Session(bind=src_engine)
        dst_session = Session(bind=dst_engine)
        
        # Order matters for foreign keys
        classes = [
            models.Admin,
            models.ParkingLot,
            models.Zone,
            models.ParkingSpot,
            models.GraphNode,
            models.GraphEdge
        ]
        
        for cls in classes:
            print(f"  Cloning {cls.__name__}...")
            items = src_session.query(cls).all()
            for item in items:
                # Merge into destination
                src_session.expunge(item)
                dst_session.merge(item)
            dst_session.commit()
            
    print("MIGRATION COMPLETE: All data cloned successfully.")

if __name__ == "__main__":
    migrate()
