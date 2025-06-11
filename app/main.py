from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
import math
import datetime
from datetime import date as Date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import logging

# Import database components
from database import get_db
from models import Station, MonthlyNormal, CloudCover, HeatIndex

# Import sun calculator module
from sun_calculator import get_sun_data_for_date_range

app = FastAPI(title="Climate Data API")

# Enable CORS for Vue frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Vue app's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/")
def read_root():
    return {"message": "Climate Data API is running with PostgreSQL"}

@app.get("/api/stations/search")
def search_stations(
    query: str = Query("", min_length=0),
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Return station suggestions based on user input.
    Filters stations where the name contains the query string (case-insensitive).
    """
    if not query:
        return []
    
    # Search in both name and ID fields
    stations = db.query(Station).filter(
        or_(
            func.lower(Station.name).contains(query.lower()),
            func.lower(Station.id).contains(query.lower())
        )
    ).limit(limit).all()
    
    # Convert to dict format matching original API
    results = []
    for station in stations:
        results.append({
            "id": station.id,
            "name": station.name,
            "latitude": float(station.latitude) if station.latitude else None,
            "longitude": float(station.longitude) if station.longitude else None,
            "elevation": float(station.elevation) if station.elevation else None,
            "elevationUnit": station.elevation_unit,
            "mindate": station.mindate.isoformat() if station.mindate else None,
            "maxdate": station.maxdate.isoformat() if station.maxdate else None,
            "datacoverage": float(station.datacoverage) if station.datacoverage else None
        })
    
    return results

@app.get("/api/stations/search-full")
def search_stations_full(
    query: str = Query("", min_length=0),
    offset: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Return full search results with pagination support.
    Filters stations where the name or ID contains the query string (case-insensitive).
    """
    if not query:
        return {
            "results": [],
            "totalCount": 0,
            "offset": offset,
            "limit": limit
        }
    
    # Build query
    base_query = db.query(Station).filter(
        or_(
            func.lower(Station.name).contains(query.lower()),
            func.lower(Station.id).contains(query.lower())
        )
    )
    
    # Get total count
    total_count = base_query.count()
    
    # Get paginated results
    stations = base_query.offset(offset).limit(limit).all()
    
    # Convert to dict format
    results = []
    for station in stations:
        results.append({
            "id": station.id,
            "name": station.name,
            "latitude": float(station.latitude) if station.latitude else None,
            "longitude": float(station.longitude) if station.longitude else None,
            "elevation": float(station.elevation) if station.elevation else None,
            "elevationUnit": station.elevation_unit,
            "mindate": station.mindate.isoformat() if station.mindate else None,
            "maxdate": station.maxdate.isoformat() if station.maxdate else None,
            "datacoverage": float(station.datacoverage) if station.datacoverage else None
        })
    
    return {
        "results": results,
        "totalCount": total_count,
        "offset": offset,
        "limit": limit,
        "totalPages": math.ceil(total_count / limit) if limit > 0 else 0
    }

@app.get("/api/stations")
def get_all_stations(db: Session = Depends(get_db)):
    """Return all stations for client-side filtering"""
    stations = db.query(Station).all()
    
    results = []
    for station in stations:
        results.append({
            "id": station.id,
            "name": station.name,
            "latitude": float(station.latitude) if station.latitude else None,
            "longitude": float(station.longitude) if station.longitude else None,
            "elevation": float(station.elevation) if station.elevation else None,
            "elevationUnit": station.elevation_unit,
            "mindate": station.mindate.isoformat() if station.mindate else None,
            "maxdate": station.maxdate.isoformat() if station.maxdate else None,
            "datacoverage": float(station.datacoverage) if station.datacoverage else None
        })
    
    return results

@app.get("/api/stations/{station_id}")
def get_station(station_id: str, db: Session = Depends(get_db)):
    """Return detailed information for a specific station"""
    # Handle GHCND prefix
    clean_id = station_id.replace('GHCND:', '')
    
    # Try both with and without prefix
    station = db.query(Station).filter(
        or_(
            Station.id == station_id,
            Station.id == f'GHCND:{clean_id}'
        )
    ).first()
    
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    return {
        "id": station.id,
        "name": station.name,
        "latitude": float(station.latitude) if station.latitude else None,
        "longitude": float(station.longitude) if station.longitude else None,
        "elevation": float(station.elevation) if station.elevation else None,
        "elevationUnit": station.elevation_unit,
        "mindate": station.mindate.isoformat() if station.mindate else None,
        "maxdate": station.maxdate.isoformat() if station.maxdate else None,
        "datacoverage": float(station.datacoverage) if station.datacoverage else None
    }

@app.get("/api/normals/{station_id}")
def get_normals(station_id: str, db: Session = Depends(get_db)):
    """Return climate normals data for a specific station"""
    # Handle GHCND prefix
    clean_id = station_id.replace('GHCND:', '')
    
    # Get station
    station = db.query(Station).filter(
        or_(
            Station.id == station_id,
            Station.id == f'GHCND:{clean_id}'
        )
    ).first()
    
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    
    # Get normals data from monthly_normals table
    normals = db.query(MonthlyNormal).filter(
        MonthlyNormal.station_id == station.id
    ).order_by(MonthlyNormal.month).all()
    
    if not normals:
        raise HTTPException(status_code=404, detail=f"Climate data not found for station {station_id}")
    
    # Format data to match original API
    months = ['January', 'February', 'March', 'April', 
             'May', 'June', 'July', 'August', 
             'September', 'October', 'November', 'December']
    
    data = []
    for normal in normals:
        row = {
            "STATION": station.id,
            "LATITUDE": float(station.latitude) if station.latitude else None,
            "LONGITUDE": float(station.longitude) if station.longitude else None,
            "ELEVATION": float(station.elevation) if station.elevation else None,
            "month": normal.month,
            "monthName": months[normal.month - 1] if 1 <= normal.month <= 12 else None,
        }
        
        # Add climate data fields with original API field names
        if normal.precipitation is not None:
            row["MLY-PRCP-NORMAL"] = float(normal.precipitation)
        if normal.temp_max is not None:
            row["MLY-TMAX-NORMAL"] = float(normal.temp_max)
        if normal.temp_min is not None:
            row["MLY-TMIN-NORMAL"] = float(normal.temp_min)
        
        data.append(row)
    
    return {"station_id": station_id, "data": data}

@app.get("/api/sun-data/{station_id}")
async def get_sun_data(station_id: str, db: Session = Depends(get_db)):
    """
    Get sunrise, sunset, and daylight hours for a station for the current year.
    
    Times are returned in the station's local timezone in 24-hour format (HH:MM).
    """
    # Handle GHCND prefix
    clean_id = station_id.replace('GHCND:', '')
    
    # Get station
    station = db.query(Station).filter(
        or_(
            Station.id == station_id,
            Station.id == f'GHCND:{clean_id}'
        )
    ).first()
    
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Always use current year
    current_year = datetime.date.today().year
    start_date = datetime.date(current_year, 1, 1)
    end_date = datetime.date(current_year, 12, 31)
    
    # Since sun_data table doesn't exist in new database, always calculate on the fly
    try:
        result = get_sun_data_for_date_range(
            float(station.latitude), 
            float(station.longitude), 
            start_date, 
            end_date,
            format_times_simple=True
        )
        
        # Add station info
        result["station"] = {
            "id": station.id,
            "name": station.name,
            "elevation": float(station.elevation) if station.elevation else None
        }
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating sun data: {str(e)}")

@app.get("/api/cloud-cover/{station_id}")
def get_cloud_cover(
    station_id: str,
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db)
):
    """
    Get cloud cover data for a specific station.
    Optionally filter by month.
    """
    # Handle GHCND prefix
    clean_id = station_id.replace('GHCND:', '')
    
    # Get station
    station = db.query(Station).filter(
        or_(
            Station.id == station_id,
            Station.id == f'GHCND:{clean_id}'
        )
    ).first()
    
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    
    # Build query
    query = db.query(CloudCover).filter(CloudCover.station_id == station.id)
    
    if month:
        query = query.filter(CloudCover.month == month)
    
    # Order by month and day
    cloud_data = query.order_by(CloudCover.month, CloudCover.day).all()
    
    if not cloud_data:
        raise HTTPException(status_code=404, detail=f"Cloud cover data not found for station {station_id}")
    
    # Format data
    months = ['January', 'February', 'March', 'April', 
             'May', 'June', 'July', 'August', 
             'September', 'October', 'November', 'December']
    
    data = []
    for record in cloud_data:
        data.append({
            "station_id": record.station_id,
            "station_name": record.station_name,
            "month": record.month,
            "monthName": months[record.month - 1] if 1 <= record.month <= 12 else None,
            "day": record.day,
            "clr": float(record.clr) if record.clr is not None else None,
            "few": float(record.few) if record.few is not None else None,
            "sct": float(record.sct) if record.sct is not None else None,
            "bkn": float(record.bkn) if record.bkn is not None else None,
            "ovc": float(record.ovc) if record.ovc is not None else None
        })
    
    return {
        "station_id": station_id,
        "station": {
            "id": station.id,
            "name": station.name,
            "latitude": float(station.latitude) if station.latitude else None,
            "longitude": float(station.longitude) if station.longitude else None
        },
        "data": data
    }

@app.get("/api/heat-index/{station_id}")
def get_heat_index(
    station_id: str,
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db)
):
    """
    Get heat index data for a specific station.
    Optionally filter by month.
    """
    # Handle GHCND prefix
    clean_id = station_id.replace('GHCND:', '')
    
    # Get station
    station = db.query(Station).filter(
        or_(
            Station.id == station_id,
            Station.id == f'GHCND:{clean_id}'
        )
    ).first()
    
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found")
    
    # Build query
    query = db.query(HeatIndex).filter(HeatIndex.station_id == station.id)
    
    if month:
        query = query.filter(HeatIndex.month == month)
    
    # Order by month and day
    heat_data = query.order_by(HeatIndex.month, HeatIndex.day).all()
    
    if not heat_data:
        raise HTTPException(status_code=404, detail=f"Heat index data not found for station {station_id}")
    
    # Format data
    months = ['January', 'February', 'March', 'April', 
             'May', 'June', 'July', 'August', 
             'September', 'October', 'November', 'December']
    
    data = []
    for record in heat_data:
        data.append({
            "station_id": record.station_id,
            "station_name": record.station_name,
            "month": record.month,
            "monthName": months[record.month - 1] if 1 <= record.month <= 12 else None,
            "day": record.day,
            "min_heat_index": float(record.min_heat_index) if record.min_heat_index is not None else None,
            "max_heat_index": float(record.max_heat_index) if record.max_heat_index is not None else None
        })
    
    return {
        "station_id": station_id,
        "station": {
            "id": station.id,
            "name": station.name,
            "latitude": float(station.latitude) if station.latitude else None,
            "longitude": float(station.longitude) if station.longitude else None
        },
        "data": data
    }