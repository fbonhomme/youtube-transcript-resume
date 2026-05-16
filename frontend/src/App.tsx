import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import LibraryPage from "./pages/LibraryPage";
import NewSummaryPage from "./pages/NewSummaryPage";
import SummaryDetailPage from "./pages/SummaryDetailPage";
import ThemeManagerPage from "./pages/ThemeManagerPage";
import PromptsPage from "./pages/PromptsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/library" replace />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/library/:id" element={<SummaryDetailPage />} />
        <Route path="/new" element={<NewSummaryPage />} />
        <Route path="/themes" element={<ThemeManagerPage />} />
        <Route path="/prompts" element={<PromptsPage />} />
      </Route>
    </Routes>
  );
}
