from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from fastapi import HTTPException

def find_nearest_post(x: float, y: float, db: Session, result_payload: dict):
    query = text("""
    WITH person AS (
        SELECT ST_SetSRID(ST_MakePoint(:x, :y), 4326) AS geom
    ),
    pas AS (
        SELECT
            id,
            dist_m,
            wind_direction,
            az_post_to_person,
            CASE 
                WHEN abs(abs(wind_direction+180)-az_post_to_person) > 180 
                    THEN abs(360-(abs(abs(wind_direction+180)-az_post_to_person)))
                ELSE abs(abs(wind_direction+180)-az_post_to_person)
            END as corner,
            1/dist_m as weight/*,
            geom*/
        FROM (
            SELECT ap.id,
                ap.wind_direction,
                ST_Distance(ap.geom::geography, p.geom::geography) AS dist_m,
                DEGREES(ST_Azimuth(ap.geom, p.geom)) AS az_post_to_person,
                ap.geom
            FROM (
                SELECT 
                    air_station_id as id, 
                    geom, 
                    wind_direction 
                FROM data_air_monitoring.air_station a
                LEFT JOIN LATERAL (
                    SELECT wind_direction 
                    FROM data_air_monitoring.air_station_data q 
                    WHERE q.air_station_id=a.air_station_id
                    ORDER BY cdate DESC 
                    LIMIT 1
                ) b ON true
                WHERE wind_direction IS NOT NULL
            ) ap
            JOIN person p ON true
            WHERE ST_DWithin(ap.geom::geography, p.geom::geography, 3000)  /*3 км*/
        ) q
    )
    SELECT weight/b.sum_weight as influence, q.id, q.dist_m, q.wind_direction, q.az_post_to_person, q.corner, q.weight
    FROM pas q
    JOIN LATERAL (
        SELECT SUM(weight) AS sum_weight FROM pas
    ) b ON true
    where corner between 0 and 45
    order by corner ASC,(weight/b.sum_weight) desc, dist_m ASC
    limit 1
    """)
    
    influence = db.execute(query, {"x": x, "y": y}).fetchone()

    if influence:
        inf_dict = dict(influence._mapping)
        inf_dict["influence_station"] = True
        result_payload["influenceStation"] = inf_dict
    else:
        nearestStationSQL = text("""
            WITH person AS (
            SELECT ST_SetSRID(ST_MakePoint(:x, :y), 4326) AS geom
        ),
        pas AS (
            SELECT
                id,
                dist_m,
                wind_direction,
                az_post_to_person,
                CASE 
                    WHEN abs(abs(wind_direction+180)-az_post_to_person) > 180 
                        THEN abs(360-(abs(abs(wind_direction+180)-az_post_to_person)))
                    ELSE abs(abs(wind_direction+180)-az_post_to_person)
                END as corner,
                1/dist_m as weight/*,
                geom*/
            FROM (
                SELECT ap.id,
                    ap.wind_direction,
                    ST_Distance(ap.geom::geography, p.geom::geography) AS dist_m,
                    DEGREES(ST_Azimuth(ap.geom, p.geom)) AS az_post_to_person,
                    ap.geom
                FROM (
                    SELECT 
                        air_station_id as id, 
                        geom, 
                        wind_direction 
                    FROM data_air_monitoring.air_station a
                    LEFT JOIN LATERAL (
                        SELECT wind_direction 
                        FROM data_air_monitoring.air_station_data q 
                        WHERE q.air_station_id=a.air_station_id
                        ORDER BY cdate DESC 
                        LIMIT 1
                    ) b ON true
                    WHERE wind_direction IS NOT NULL
                ) ap
                JOIN person p ON true
                WHERE ST_DWithin(ap.geom::geography, p.geom::geography, 3000)  /*3 км*/
            ) q
        )
        SELECT weight/b.sum_weight as influence, q.id, q.dist_m, q.wind_direction, q.az_post_to_person, q.corner, q.weight
        FROM pas q
        JOIN LATERAL (
            SELECT SUM(weight) AS sum_weight FROM pas
        ) b ON true
        order by corner ASC,(weight/b.sum_weight) desc, dist_m ASC
        limit 1 
        """)
        
        nearest = db.execute(nearestStationSQL, {"x": x, "y": y}).fetchone()
        
        if nearest:
            near_dict = dict(nearest._mapping)
            near_dict["nearest_station"] = True
            result_payload["influenceStation"] = near_dict
        else:
            result_payload["influenceStation"] = {}

    # Побудова буфера навколо точки
    buffer_query = text("""
        SELECT st_asgeojson(ST_Buffer(ST_SetSRID(ST_MakePoint(:x, :y), 4326)::geography, 3000)::geometry, 6, 0)::json as buffer_geom
    """)
    buffer_result = db.execute(buffer_query, {"x": x, "y": y}).fetchone()
    if buffer_result:
        result_payload["pointBuffer"] = buffer_result[0]

    # Побудова лінії від точки до найближчої станції
    inf_station = result_payload.get("influenceStation", {})
    if inf_station and "id" in inf_station:
        lineSql = text("""
            SELECT ST_AsGeoJSON(ST_MakeLine(
                ST_SetSRID(ST_MakePoint(:x, :y), 4326),
                a.geom
            )::geometry, 6, 0)::json as line_geom
            FROM data_air_monitoring.air_station a
            WHERE a.air_station_id = :id
        """)
        line_result = db.execute(lineSql, {"x": x, "y": y, "id": inf_station["id"]}).fetchone()
        if line_result and line_result[0]:
            result_payload["line"] = line_result[0]


def getNearesPost(x: Optional[float], y: Optional[float], db: Session):
    try:
        if x is not None:
            x = float(x)
        if y is not None:
            y = float(y)

        geojsonSql = text("""
            SELECT 
                'FeatureCollection' As type, 
                json_agg(f) As features 
            FROM 
            (
                SELECT 
                    'Feature' As type, 
                    row_number() over() as id, 
                    st_asgeojson(st_force2d(geom), 6, 0)::json as geometry, 
                    (
                        select row_to_json(tc) 
                        from (
                            SELECT  q.*
                        ) tc
                    ) as properties 
                FROM (
                    select * from data_air_monitoring.air_station t 
                    left join lateral (
                        select * from data_air_monitoring.air_station_data
                        where air_station_id = t.air_station_id
                        order by cdate desc limit 1
                    ) b on true
                ) q
            ) f;
        """)

        geojson_result = db.execute(geojsonSql).fetchone()
        
        result_payload = {
            "influenceStation": {},
            "geojson": dict(geojson_result._mapping) if geojson_result else {}
        }


        if x is not None and y is not None:
            find_nearest_post(x, y, db, result_payload)

        return {"result": result_payload, "status": 200}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
