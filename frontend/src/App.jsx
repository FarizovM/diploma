
import './App.css'
import MapComponent from './MapComponent'

function App() {
  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Мапа моніторингу якості повітря</h1>
      </header>
      <main className="map-container">
        <MapComponent />
      </main>
    </div>
  )
}

export default App
