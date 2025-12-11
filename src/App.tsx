import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './presentation/components/layout/Navbar';
import DeviceList from './presentation/pages/DeviceList';
import DeviceManagement from './presentation/pages/DeviceManagement';
import DevicePassport from './presentation/pages/DevicePassport';
import CreatePolicyPage from './presentation/pages/CreatePolicyPage';

/**
 * App - Componente principal de la aplicación
 */
function App(): JSX.Element {
  return (
    <Router>
      <div style={{ minHeight: '100vh', backgroundColor: '#f5f5f5' }}>
        <Navbar />
        <Routes>
          <Route path="/devices" element={<DeviceList />} />
          <Route path="/devices/:id" element={<DeviceManagement />} />
          <Route path="/devices/:id/passport" element={<DevicePassport />} />
          <Route path="/devices/:id/policies/create" element={<CreatePolicyPage />} />
          <Route path="*" element={<Navigate to="/devices" replace />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;

