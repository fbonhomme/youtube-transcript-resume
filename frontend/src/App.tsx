import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import { ConfirmProvider } from "./components/ConfirmDialog";
import LibraryPage from "./pages/LibraryPage";
import NewSummaryPage from "./pages/NewSummaryPage";
import ImportPage from "./pages/ImportPage";
import SummaryDetailPage from "./pages/SummaryDetailPage";
import ThemeManagerPage from "./pages/ThemeManagerPage";
import PromptsPage from "./pages/PromptsPage";

export default function App() {
  return (
    <ConfirmProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/library" replace />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/library/:id" element={<SummaryDetailPage />} />
          <Route path="/new" element={<NewSummaryPage />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/themes" element={<ThemeManagerPage />} />
          <Route path="/prompts" element={<PromptsPage />} />
        </Route>
      </Routes>
    </ConfirmProvider>
  );
}
