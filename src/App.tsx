import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './presentation/components/layout/Navbar';
import DeviceList from './presentation/pages/DeviceList';
import DeviceManagement from './presentation/pages/DeviceManagement';
import DevicePassport from './presentation/pages/DevicePassport';

/**
 * App - Componente principal de la aplicación
 */
function App(): JSX.Element {
  return (
    <Router>
      <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
        <Navbar />
        <Routes>
          <Route path="/" element={<DeviceList />} />
          <Route path="/devices" element={<DeviceList />} />
          <Route path="/devices/:id" element={<DeviceManagement />} />
          <Route path="/devices/:id/passport" element={<DevicePassport />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;

