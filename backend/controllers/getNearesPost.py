from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from fastapi import HTTPException

"""
Методика вирахування: Модель спрямованого впливу
Замість того, щоб спиратися на складні фізичні моделі розсіювання (як Гауссова модель плюму, яка занадто важка для реал-тайм SQL-запитів), ми можемо використати модифікований метод зворотних зважених відстаней (IDW) із накладанням "вектора вітру".

Нам потрібно вирахувати Коефіцієнт впливу (Influence Score) для кожного поста за такою логікою:
1. Відстань ($d$): Чим далі пост, тим менший вплив (базова дифузія).
2. Азимут ($\alpha$): Кут від поста до твого місцезнаходження.
3. Напрямок вітру ($\omega$): Куди дме вітер. Важливо: метеорологи часто вказують, звідки дме вітер, тому переконайся, що твій кут вказує вектор руху маси повітря.
4. Різниця кутів ($\theta$): $\theta = |\alpha - \omega|$. Якщо $\theta \approx 0^\circ$, вітер несе повітря прямо від поста до тебе. Якщо $\theta \approx 180^\circ$, вітер відносить повітря геть.
5. Швидкість вітру ($v$): Чим сильніший вітер, тим більшу вагу має напрямок (витягує "шлейф" забруднення), і тим меншу вагу має базова дифузія в усі боки.

Формула розрахунку коефіцієнта впливу:
$$Influence = \frac{1}{d^p} \times \left( k_{base} + k_{wind} \cdot v \cdot \left( \frac{1 + \cos(\theta)}{2} \right)^n \right)$$
"""
def find_nearest_post(x: float, y: float, db: Session, result_payload: dict):
    query = text("""
    WITH target_location AS (
        -- Задаємо координати користувача (x - довгота, y - широта)
        SELECT ST_SetSRID(ST_MakePoint(:x, :y), 4326)::geography AS geom
    ),
    nearest_candidates AS (
        -- ЕТАП 1: Використовуємо R-дерево (GiST індекс) для пошуку 10 найближчих постів.
        -- Оператор <-> працює по bounding box і є надзвичайно швидким завдяки індексу GiST (R-дерево).
        SELECT 
            p.air_station_id as id,
            p.geom,
            b.wind_direction, -- кут, КУДИ дме вітер (в градусах)
            b.wind_speed,     -- швидкість вітру (м/с)
            p.geom <-> t.geom AS distance_meters
        FROM 
            data_air_monitoring.air_station p
            LEFT JOIN LATERAL (
                SELECT wind_direction, wind_speed
                FROM data_air_monitoring.air_station_data q 
                WHERE q.air_station_id=p.air_station_id
                ORDER BY cdate DESC 
                LIMIT 1
            ) b ON true, 
            target_location t
        where wind_direction is not null
        and (p.geom <-> t.geom) <= 3000
        ORDER BY 
            p.geom <-> t.geom ASC
        LIMIT 10
    )
    -- ЕТАП 2: Рахуємо коефіцієнт впливу (Influence Score)
    SELECT 
        id,
        distance_meters AS dist_m,
        wind_direction,
        wind_speed,
        -- Рахуємо азимут від поста до користувача (переводимо радіани в градуси)
        DEGREES(ST_Azimuth(geom::geometry, (SELECT geom::geometry FROM target_location))) AS az_post_to_person,
        
        -- Реалізація формули впливу
        (1 / NULLIF(POWER(distance_meters, 1.2), 0)) * (
            0.2 + -- k_base (базова константа дифузії)
            0.5 * --k_wind (множник сили впливу вітру) 
            wind_speed * POWER(
                (COS(RADIANS(
                    (wind_direction+180) - DEGREES(ST_Azimuth(geom::geometry, (SELECT geom::geometry FROM target_location)))
                )) + 1) / 2, 
                2 -- ступінь вузькості шлейфу (n)
            )
        ) AS influence

    FROM nearest_candidates
    ORDER BY influence DESC
    LIMIT 1
    """)

    influence = db.execute(query, {"x": x, "y": y}).fetchone()

    if influence:
        inf_dict = dict(influence._mapping)
        inf_dict["influence_station"] = True
        result_payload["influenceStation"] = inf_dict
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

        # Отримання всіх станцій у форматі GeoJSON
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
