from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, JSON
from sqlalchemy.orm import relationship
try:
    from .database import Base
except ImportError:
    from database import Base

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)

class ParkingLot(Base):
    __tablename__ = "parking_lots"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True) # Will lock to Admin later
    zone_type = Column(String, default="single") # "single" or "multi"
    
    zones = relationship("Zone", back_populates="lot", cascade="all, delete")
    spots = relationship("ParkingSpot", back_populates="lot", cascade="all, delete")

class Zone(Base):
    __tablename__ = "zones"
    id = Column(Integer, primary_key=True, index=True)
    lot_id = Column(Integer, ForeignKey("parking_lots.id"))
    video_source = Column(String)
    offset_x = Column(Float, default=0.0)
    offset_y = Column(Float, default=0.0)
    
    lot = relationship("ParkingLot", back_populates="zones")
    nodes = relationship("GraphNode", back_populates="zone", cascade="all, delete")
    spots = relationship("ParkingSpot", back_populates="zone", cascade="all, delete")

class ParkingSpot(Base):
    __tablename__ = "parking_spots"
    id = Column(Integer, primary_key=True, index=True)
    lot_id = Column(Integer, ForeignKey("parking_lots.id"))
    zone_id = Column(Integer, ForeignKey("zones.id"))
    polygon_data = Column(JSON) # Store array of [x,y] coordinates
    status = Column(String, default="vacant") # vacant, occupied, reserved
    spot_index = Column(Integer) # Display ID
    
    lot = relationship("ParkingLot", back_populates="spots")
    zone = relationship("Zone", back_populates="spots")

class GraphNode(Base):
    __tablename__ = "graph_nodes"
    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"))
    x = Column(Float)
    y = Column(Float)
    label = Column(String, default="")
    
    zone = relationship("Zone", back_populates="nodes")

class GraphEdge(Base):
    __tablename__ = "graph_edges"
    id = Column(Integer, primary_key=True, index=True)
    node_a_id = Column(Integer, ForeignKey("graph_nodes.id", ondelete="CASCADE"))
    node_b_id = Column(Integer, ForeignKey("graph_nodes.id", ondelete="CASCADE"))
    weight = Column(Float)
    manual_weight = Column(Float, nullable=True)
