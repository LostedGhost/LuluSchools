import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { AppLayout, ThemeProvider } from "./layout/AppLayout";
import { EleveProfileProvider } from "./eleve/EleveProfileContext";
import { AdminEtabProvider } from "./admin/AdminEtabContext";

import { LandingPage } from "./pages/LandingPage";
import { EtablissementsAnnuairePage } from "./pages/EtablissementsAnnuairePage";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { ChangePasswordPage } from "./pages/ChangePasswordPage";
import { DashboardRedirect } from "./pages/DashboardRedirect";

import { TuteurDashboard } from "./pages/tuteur/TuteurDashboard";
import { NouvelleInscriptionPage } from "./pages/tuteur/NouvelleInscriptionPage";

import { EleveDashboard } from "./pages/eleve/EleveDashboard";
import { CoursListPage } from "./pages/eleve/CoursListPage";
import { QuizPage } from "./pages/eleve/QuizPage";
import { DevoirsListPage } from "./pages/eleve/DevoirsListPage";
import { DevoirDetailPage } from "./pages/eleve/DevoirDetailPage";
import { BulletinPage } from "./pages/eleve/BulletinPage";
import { ActesPage } from "./pages/eleve/ActesPage";

import { EnseignantDashboard } from "./pages/enseignant/EnseignantDashboard";
import { PostesListPage } from "./pages/enseignant/PostesListPage";
import { PostulerPage } from "./pages/enseignant/PostulerPage";
import { MesCandidaturesPage } from "./pages/enseignant/MesCandidaturesPage";
import { MesContratsPage } from "./pages/enseignant/MesContratsPage";
import { MesCoursPage } from "./pages/enseignant/MesCoursPage";
import { MesDevoirsPage } from "./pages/enseignant/MesDevoirsPage";

import { AdminEtabDashboard } from "./pages/admin_etablissement/AdminEtabDashboard";
import { ClassesPage } from "./pages/admin_etablissement/ClassesPage";
import { InscriptionsAValiderPage } from "./pages/admin_etablissement/InscriptionsAValiderPage";
import { RecrutementPage } from "./pages/admin_etablissement/RecrutementPage";
import { ContestationsPage } from "./pages/admin_etablissement/ContestationsPage";
import { ActesAdminPage } from "./pages/admin_etablissement/ActesAdminPage";

import { AdminMinisterielDashboard } from "./pages/admin_ministeriel/AdminMinisterielDashboard";
import { EtablissementsPage } from "./pages/admin_ministeriel/EtablissementsPage";
import { ReferentielsPage } from "./pages/admin_ministeriel/ReferentielsPage";

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
      <AuthProvider>
        <AppLayout>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/etablissements" element={<EtablissementsAnnuairePage />} />
            <Route path="/connexion" element={<LoginPage />} />
            <Route path="/inscription-tuteur" element={<SignupPage role="tuteur" />} />
            <Route path="/inscription-enseignant" element={<SignupPage role="enseignant" />} />
            <Route
              path="/changer-mot-de-passe"
              element={
                <RequireAuth>
                  <ChangePasswordPage />
                </RequireAuth>
              }
            />
            <Route path="/dashboard" element={<DashboardRedirect />} />

            {/* Tuteur */}
            <Route
              path="/tuteur"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <TuteurDashboard />
                </RequireAuth>
              }
            />
            <Route
              path="/tuteur/nouvelle-inscription"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <NouvelleInscriptionPage />
                </RequireAuth>
              }
            />

            {/* Eleve */}
            <Route
              path="/eleve"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <EleveDashboard />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/cours"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <CoursListPage />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/quiz/:quizId"
              element={
                <RequireAuth roles={["eleve"]}>
                  <QuizPage />
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/devoirs"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <DevoirsListPage />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/devoirs/:devoirId"
              element={
                <RequireAuth roles={["eleve"]}>
                  <DevoirDetailPage />
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/bulletin"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <BulletinPage />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/actes"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <ActesPage />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />

            {/* Enseignant */}
            <Route
              path="/enseignant"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <EnseignantDashboard />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/postes"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <PostesListPage />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/postes/:posteId/postuler"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <PostulerPage />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/candidatures"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <MesCandidaturesPage />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/contrats"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <MesContratsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/cours"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <MesCoursPage />
                </RequireAuth>
              }
            />
            <Route
              path="/enseignant/devoirs"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <MesDevoirsPage />
                </RequireAuth>
              }
            />

            {/* Admin etablissement (A+) */}
            <Route
              path="/admin-etablissement"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <AdminEtabDashboard />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/classes"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <ClassesPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/inscriptions"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <InscriptionsAValiderPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/postes"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <RecrutementPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/contestations"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <ContestationsPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/actes"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <ActesAdminPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />

            {/* Admin ministeriel (A++) */}
            <Route
              path="/admin-ministeriel"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <AdminMinisterielDashboard />
                </RequireAuth>
              }
            />
            <Route
              path="/admin-ministeriel/etablissements"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <EtablissementsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/admin-ministeriel/referentiels"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <ReferentielsPage />
                </RequireAuth>
              }
            />
          </Routes>
        </AppLayout>
      </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
