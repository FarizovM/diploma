import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, Marker, Popup, Tooltip, useMapEvents, ImageOverlay } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default Leaflet markers missing icons in React
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

const getWindDirectionText = (degrees) => {
  if (degrees === null || degrees === undefined) return '';
  if (degrees >= 12 && degrees <= 34) return 'ПнПнСх';
  if (degrees >= 34 && degrees <= 57) return 'ПнСх';
  if (degrees >= 57 && degrees <= 79) return 'СхПнСх';
  if (degrees >= 79 && degrees <= 102) return 'Сх';
  if (degrees >= 102 && degrees <= 124) return 'СхПдСх';
  if (degrees >= 124 && degrees <= 147) return 'ПдСх';
  if (degrees >= 147 && degrees <= 169) return 'ПдПдСх';
  if (degrees >= 169 && degrees <= 192) return 'Пд';
  if (degrees >= 192 && degrees <= 214) return 'ПдПдЗх';
  if (degrees >= 214 && degrees <= 237) return 'ПдЗх';
  if (degrees >= 237 && degrees <= 259) return 'ЗхПдЗх';
  if (degrees >= 259 && degrees <= 282) return 'Зх';
  if (degrees >= 282 && degrees <= 304) return 'ЗхПнЗх';
  if (degrees >= 304 && degrees <= 327) return 'ПнЗх';
  if (degrees >= 327 && degrees <= 349) return 'ПнПнЗх';
  if ((degrees >= 349 && degrees <= 360) || (degrees >= 0 && degrees <= 12)) return 'Пн';
  return '';
};

const MapComponent = () => {
  const [geoData, setGeoData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [contextMenuPos, setContextMenuPos] = useState(null);
  const [highlightedStationId, setHighlightedStationId] = useState(null);
  const [pointBuffer, setPointBuffer] = useState(null);
  const [lineData, setLineData] = useState(null);
  const [lineDistance, setLineDistance] = useState(null);
  const [plumeData, setPlumeData] = useState(null);
  const [isPlumeLoading, setIsPlumeLoading] = useState(false);

  const findInfluenceStation = (lat, lng) => {
    fetch(`http://localhost:8000/api/neares-post?x=${lng}&y=${lat}`)
      .then((response) => response.json())
      .then((data) => {
        if (data.status === 200) {
          if (data.result?.influenceStation?.id) {
            setHighlightedStationId(data.result.influenceStation.id);
            setLineDistance(data.result.influenceStation.dist_m);
          } else {
            alert('Станцію впливу не знайдено.');
            setLineDistance(null);
          }
          if (data.result?.pointBuffer) {
            setPointBuffer(data.result.pointBuffer);
          } else {
            setPointBuffer(null);
          }
          if (data.result?.line) {
            setLineData(data.result.line);
          } else {
            setLineData(null);
          }
          setContextMenuPos(null);
        } else {
          alert('Помилка від сервера при пошуку станції.');
        }
      })
      .catch((err) => {
        console.error(err);
        alert('Помилка при пошуку станції впливу.');
      });
  };

  const [clickedPos, setClickedPos] = useState(null);
  const [mouseCoords, setMouseCoords] = useState(null);

  const MapEvents = () => {
    useMapEvents({
      contextmenu: (e) => {
        setContextMenuPos(e.latlng);
        setClickedPos(e.latlng);
      },
      mousemove: (e) => {
        setMouseCoords(e.latlng);
      }
    });
    return null;
  };
  
  const fetchWindPlume = (lat, lng, windDir, windSpeed) => {
    setIsPlumeLoading(true);
    // Робимо запит до нового ендпоінта
    fetch(`http://localhost:8000/api/plume?lat=${lat}&lng=${lng}&wind_dir=${windDir}&wind_speed=${windSpeed}`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 200) {
          setPlumeData(data.result);
        } else {
          alert('Помилка розрахунку фізики');
        }
      })
      .catch(err => console.error(err))
      .finally(() => setIsPlumeLoading(false));
  };

  useEffect(() => {
    // Fetch nearest post data from your API
    // Adjust x, y if you want to test finding nearest stations based on a user location
    // Currently fetching without params
    fetch('http://localhost:8000/api/neares-post')
      .then((response) => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then((data) => {
        if (data.status === 200 && data.result?.geojson) {
          setGeoData(data.result.geojson);
        } else {
          setError('Failed to load GeoJSON data from API response.');
        }
      })
      .catch((err) => {
        setError(err.toString());
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="loading">Loading Map Data...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div className="map-wrapper" style={{ position: 'relative', height: '100%' }}>
      <MapContainer center={[47.9103, 33.3917]} zoom={11} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapEvents />
        {contextMenuPos && (
          <Popup position={contextMenuPos} onClose={() => setContextMenuPos(null)}>
            <div style={{minWidth: '150px'}}>
              <p style={{margin: '0 0 10px 0'}}>
                <b>Координати:</b><br/>
                X (Довг): {contextMenuPos.lng.toFixed(5)}<br/>
                Y (Шир): {contextMenuPos.lat.toFixed(5)}
              </p>
              <button 
                onClick={() => navigator.clipboard.writeText(`${contextMenuPos.lat.toFixed(5)}, ${contextMenuPos.lng.toFixed(5)}`)}
                style={{width: '100%', marginBottom: '5px', padding: '5px', fontSize: '12px'}}
              >
                📋 Скопіювати координати
              </button>
              <button 
                onClick={() => findInfluenceStation(contextMenuPos.lat, contextMenuPos.lng)}
                style={{width: '100%', padding: '5px', fontSize: '12px', backgroundColor: '#3498db', color: 'white', border: 'none'}}
              >
                🔍 Знайти станцію впливу
              </button>
            </div>
          </Popup>
        )}
        {geoData && geoData.features && (
          <GeoJSON 
            key={highlightedStationId || 'default'}
            data={geoData} 
            pointToLayer={(feature, latlng) => {
              const windDir = feature.properties.wind_direction;
              const rotation = windDir !== null && windDir !== undefined ? windDir + 180 : 0;
              const hasWindData = windDir !== null && windDir !== undefined;
              const isHighlighted = feature.properties.air_station_id === highlightedStationId;
              const borderColor = isHighlighted ? '#e74c3c' : '#3388ff';
              const borderWidth = isHighlighted ? '4px' : '2px';
              
              const iconHtml = `
                <div style="
                  width: 30px;
                  height: 30px;
                  background-color: white;
                  border: ${borderWidth} solid ${borderColor};
                  border-radius: 50%;
                  display: flex;
                  align-items: center;
                  justify-content: center;
                  box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                  position: relative;
                ">
                  ${hasWindData ? `
                    <div style="
                      transform: rotate(${rotation}deg);
                      width: 100%;
                      height: 100%;
                      display: flex;
                      align-items: center;
                      justify-content: center;
                    ">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="${borderColor}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="transform: translateY(-4px);">
                        <line x1="12" y1="19" x2="12" y2="5"></line>
                        <polyline points="5 12 12 5 19 12"></polyline>
                      </svg>
                    </div>
                  ` : `
                    <div style="width: 8px; height: 8px; background-color: ${borderColor}; border-radius: 50%;"></div>
                  `}
                </div>
              `;

              const customIcon = L.divIcon({
                html: iconHtml,
                className: 'custom-wind-marker',
                iconSize: [30, 30],
                iconAnchor: [15, 15],
                popupAnchor: [0, -15]
              });

              return L.marker(latlng, { icon: customIcon });
            }}
            onEachFeature={(feature, layer) => {
              if (feature.properties && feature.properties.name) {
                const props = feature.properties;
                const windDirVal = props.wind_direction;
                const windDirText = windDirVal !== null ? `${windDirVal}° (${getWindDirectionText(windDirVal)})` : 'Немає даних';
                const windSpeedText = props.wind_speed !== null ? `${props.wind_speed} м/с` : 'Немає даних';
                
                // Створюємо базовий контент
                layer.bindPopup(`
                  <b>Станція:</b> ${props.name}<br/>
                  <b>Напрямок вітру:</b> ${windDirText}<br/>
                  <b>Швидкість вітру:</b> ${windSpeedText}
                `);

                // Додаємо кнопку через подію popupopen, щоб прикріпити onClick (оскільки в bindPopup чистий HTML)
                layer.on('popupopen', (e) => {
                  const popupNode = e.popup._contentNode;
                  // Перевіряємо, чи є дані про вітер, щоб малювати шлейф
                  if (props.wind_direction !== null && props.wind_speed !== null && !popupNode.querySelector('.plume-btn')) {
                     const btn = document.createElement('button');
                     btn.className = 'plume-btn';
                     btn.innerHTML = '💨 Побудувати фізичну модель шлейфу';
                     btn.style.cssText = 'margin-top: 10px; width: 100%; padding: 5px; background: #9b59b6; color: white; border: none; border-radius: 4px; cursor: pointer;';
                     
                     btn.onclick = () => {
                        // Викликаємо функцію, передаючи координати і вітер станції
                        fetchWindPlume(
                          feature.geometry.coordinates[1], // lat (Y)
                          feature.geometry.coordinates[0], // lng (X)
                          props.wind_direction,
                          props.wind_speed
                        );
                     };
                     popupNode.appendChild(btn);
                  }
                });
                
                if (feature.properties.air_station_id === highlightedStationId) {
                  layer.openPopup();
                }
              }
            }}
          />
        )}
        {pointBuffer && (
          <GeoJSON 
            key={JSON.stringify(pointBuffer)} 
            data={pointBuffer}
            style={{
              color: '#3498db',
              weight: 2,
              opacity: 0.8,
              fillColor: '#3498db',
              fillOpacity: 0.15
            }}
          />
        )}
        {lineData && (
          <GeoJSON
            key={JSON.stringify(lineData)}
            data={lineData}
            style={{
              color: '#e74c3c',
              weight: 3,
              dashArray: '5, 10'
            }}
          >
            {lineDistance !== null && (
              <Tooltip sticky direction="center" className="line-tooltip">
                <span style={{ fontWeight: 'bold', fontSize: '13px', backgroundColor: 'rgba(255, 255, 255, 0.8)', padding: '2px 5px', borderRadius: '4px' }}>
                  {Math.round(lineDistance)} м
                </span>
              </Tooltip>
            )}
          </GeoJSON>
        )}
        {clickedPos && (
          <Marker position={clickedPos}>
            <Popup>
              <b>Обрана точка</b><br/>
              X: {clickedPos.lng.toFixed(5)}<br/>
              Y: {clickedPos.lat.toFixed(5)}
            </Popup>
          </Marker>
        )}
        {plumeData && plumeData.image && (
          <ImageOverlay
            key={plumeData.bounds.join(',')} // Додаємо ключ!
            url={plumeData.image}
            bounds={plumeData.bounds}
            opacity={1.0}
            zIndex={1000} // Підняли zIndex, щоб точно було поверх інших шарів
          />
        )}
      </MapContainer>
      
      {mouseCoords && (
        <div style={{
          position: 'absolute',
          bottom: '20px',
          left: '50%',
          transform: 'translateX(-50%)',
          backgroundColor: 'rgba(255, 255, 255, 0.9)',
          padding: '8px 15px',
          borderRadius: '20px',
          boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '14px',
          fontWeight: '500',
          pointerEvents: 'none',
          color: '#333'
        }}>
          <span>📍</span>
          <span>X: {mouseCoords.lng.toFixed(5)}, Y: {mouseCoords.lat.toFixed(5)}</span>
        </div>
      )}
    </div>
  );
};

export default MapComponent;
