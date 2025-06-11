from sqlalchemy import Column, String, Float, Integer, Date, ForeignKey, UniqueConstraint, Index, Numeric, Text
from sqlalchemy.orm import relationship
from database import Base

class Station(Base):
    __tablename__ = "stations"
    
    id = Column(Text, primary_key=True)
    name = Column(Text)
    latitude = Column(Numeric(10, 5))
    longitude = Column(Numeric(10, 5))
    elevation = Column(Numeric(10, 2))
    elevation_unit = Column(Text)
    mindate = Column(Date)  # Note: column name is mindate, not min_date
    maxdate = Column(Date)  # Note: column name is maxdate, not max_date
    datacoverage = Column(Numeric(5, 4))  # Note: column name is datacoverage, not data_coverage
    
    # Relationships
    monthly_normals = relationship("MonthlyNormal", back_populates="station", cascade="all, delete-orphan")
    cloud_cover = relationship("CloudCover", back_populates="station", cascade="all, delete-orphan")
    heat_index = relationship("HeatIndex", back_populates="station", cascade="all, delete-orphan")
    
    # Properties to maintain backward compatibility with the API
    @property
    def min_date(self):
        return self.mindate
    
    @property
    def max_date(self):
        return self.maxdate
    
    @property
    def data_coverage(self):
        return self.datacoverage

class MonthlyNormal(Base):
    __tablename__ = "monthly_normals"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Text, ForeignKey("stations.id"))
    month = Column(Integer)
    temp_max = Column(Numeric(6, 1))  # Changed from temp_high
    temp_min = Column(Numeric(6, 1))  # Changed from temp_low
    precipitation = Column(Numeric(6, 2))
    
    # Relationships
    station = relationship("Station", back_populates="monthly_normals")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('station_id', 'month', name='monthly_normals_station_id_month_key'),
        Index('idx_monthly_normals_station_id', 'station_id'),
        Index('idx_monthly_normals_month', 'month'),
    )
    
    # Properties for backward compatibility
    @property
    def temp_high(self):
        return self.temp_max
    
    @property
    def temp_low(self):
        return self.temp_min

class CloudCover(Base):
    __tablename__ = "cloud_cover"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Text, ForeignKey("stations.id"))
    station_name = Column(Text)
    month = Column(Integer)
    day = Column(Integer)
    clr = Column(Numeric(6, 1))  # Clear
    few = Column(Numeric(6, 1))  # Few clouds
    sct = Column(Numeric(6, 1))  # Scattered clouds
    bkn = Column(Numeric(6, 1))  # Broken clouds
    ovc = Column(Numeric(6, 1))  # Overcast
    
    # Relationships
    station = relationship("Station", back_populates="cloud_cover")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('station_id', 'month', 'day', name='cloud_cover_station_id_month_day_key'),
        Index('idx_cloud_cover_station_id', 'station_id'),
        Index('idx_cloud_cover_month_day', 'month', 'day'),
    )

class HeatIndex(Base):
    __tablename__ = "heat_index"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Text, ForeignKey("stations.id"))
    station_name = Column(Text)
    month = Column(Integer)
    day = Column(Integer)
    min_heat_index = Column(Numeric(6, 1))
    max_heat_index = Column(Numeric(6, 1))
    
    # Relationships
    station = relationship("Station", back_populates="heat_index")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('station_id', 'month', 'day', name='heat_index_station_id_month_day_key'),
        Index('idx_heat_index_station_id', 'station_id'),
        Index('idx_heat_index_month_day', 'month', 'day'),
    )