
import './App.css'
import MapComponent from './MapComponent'

function App() {
  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Air Quality Monitoring Map</h1>
      </header>
      <main className="map-container">
        <MapComponent />
      </main>
    </div>
  )
}

export default App
