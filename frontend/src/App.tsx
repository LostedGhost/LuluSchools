import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import { RedirectIfAuthenticated } from "./auth/RedirectIfAuthenticated";
import { AppLayout, ThemeProvider } from "./layout/AppLayout";
import { EleveProfileProvider } from "./eleve/EleveProfileContext";
import { AdminEtabProvider } from "./admin/AdminEtabContext";

import { LandingPage } from "./pages/LandingPage";
import { EtablissementsAnnuairePage } from "./pages/EtablissementsAnnuairePage";
// Chargée à la demande : Leaflet + react-leaflet ne doivent jamais alourdir le
// bundle des autres pages (même principe que StarfieldScene, voir LandingPage.tsx).
const CartesPage = lazy(() => import("./pages/CartesPage").then((m) => ({ default: m.CartesPage })));
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { ChangePasswordPage } from "./pages/ChangePasswordPage";
import { DashboardRedirect } from "./pages/DashboardRedirect";

import { TuteurDashboard } from "./pages/tuteur/TuteurDashboard";
import { NouvelleInscriptionPage } from "./pages/tuteur/NouvelleInscriptionPage";
import { ServicesScolairesPage as TuteurServicesScolairesPage } from "./pages/tuteur/ServicesScolairesPage";

import { EleveDashboard } from "./pages/eleve/EleveDashboard";
import { CoursListPage } from "./pages/eleve/CoursListPage";
import { QuizPage } from "./pages/eleve/QuizPage";
import { DevoirsListPage } from "./pages/eleve/DevoirsListPage";
import { DevoirDetailPage } from "./pages/eleve/DevoirDetailPage";
import { BulletinPage } from "./pages/eleve/BulletinPage";
import { ActesPage } from "./pages/eleve/ActesPage";
import { CoursDirectPage } from "./pages/eleve/CoursDirectPage";
import { ServicesScolairesPage as EleveServicesScolairesPage } from "./pages/eleve/ServicesScolairesPage";

import { EnseignantDashboard } from "./pages/enseignant/EnseignantDashboard";
import { PostesListPage } from "./pages/enseignant/PostesListPage";
import { PostulerPage } from "./pages/enseignant/PostulerPage";
import { MesCandidaturesPage } from "./pages/enseignant/MesCandidaturesPage";
import { MesContratsPage } from "./pages/enseignant/MesContratsPage";
import { MesCoursPage } from "./pages/enseignant/MesCoursPage";
import { MesDevoirsPage } from "./pages/enseignant/MesDevoirsPage";
import { SessionsLivePage } from "./pages/enseignant/SessionsLivePage";

import { AdminEtabDashboard } from "./pages/admin_etablissement/AdminEtabDashboard";
import { ClassesPage } from "./pages/admin_etablissement/ClassesPage";
import { InscriptionsAValiderPage } from "./pages/admin_etablissement/InscriptionsAValiderPage";
import { RecrutementPage } from "./pages/admin_etablissement/RecrutementPage";
import { ContestationsPage } from "./pages/admin_etablissement/ContestationsPage";
import { ActesAdminPage } from "./pages/admin_etablissement/ActesAdminPage";
import { ReferentielsEtabPage } from "./pages/admin_etablissement/ReferentielsEtabPage";
import { ServicesScolairesAdminPage } from "./pages/admin_etablissement/ServicesScolairesAdminPage";
import { EvenementsAdminPage } from "./pages/admin_etablissement/EvenementsAdminPage";

import { AdminMinisterielDashboard } from "./pages/admin_ministeriel/AdminMinisterielDashboard";
import { EtablissementsPage } from "./pages/admin_ministeriel/EtablissementsPage";
import { ReferentielsPage } from "./pages/admin_ministeriel/ReferentielsPage";

import { MessagerieListPage } from "./pages/messagerie/MessagerieListPage";
import { ConversationPage } from "./pages/messagerie/ConversationPage";
import { SignalementsPage } from "./pages/admin_etablissement/SignalementsPage";
import { BilletteriePage } from "./pages/billetterie/BilletteriePage";
import { ValiderAccesPage } from "./pages/controle_acces/ValiderAccesPage";
import { MicroJobsPage } from "./pages/micro_jobs/MicroJobsPage";
import { MicroJobsArbitragePage } from "./pages/admin_ministeriel/MicroJobsArbitragePage";

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
      <AuthProvider>
        <AppLayout>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/etablissements" element={<EtablissementsAnnuairePage />} />
            <Route
              path="/cartes"
              element={
                <Suspense fallback={<div className="page-content" />}>
                  <CartesPage />
                </Suspense>
              }
            />
            <Route
              path="/connexion"
              element={
                <RedirectIfAuthenticated>
                  <LoginPage />
                </RedirectIfAuthenticated>
              }
            />
            <Route
              path="/inscription-tuteur"
              element={
                <RedirectIfAuthenticated>
                  <SignupPage role="tuteur" />
                </RedirectIfAuthenticated>
              }
            />
            <Route
              path="/inscription-enseignant"
              element={
                <RedirectIfAuthenticated>
                  <SignupPage role="enseignant" />
                </RedirectIfAuthenticated>
              }
            />
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
            <Route
              path="/tuteur/services"
              element={
                <RequireAuth roles={["tuteur"]}>
                  <TuteurServicesScolairesPage />
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
            <Route
              path="/eleve/cours-direct"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <CoursDirectPage />
                  </EleveProfileProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/eleve/services"
              element={
                <RequireAuth roles={["eleve"]}>
                  <EleveProfileProvider>
                    <EleveServicesScolairesPage />
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
            <Route
              path="/enseignant/cours-direct"
              element={
                <RequireAuth roles={["enseignant"]}>
                  <SessionsLivePage />
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
            <Route
              path="/admin-etablissement/referentiels"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <ReferentielsEtabPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/services"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <ServicesScolairesAdminPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />
            <Route
              path="/admin-etablissement/evenements"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <EvenementsAdminPage />
                  </AdminEtabProvider>
                </RequireAuth>
              }
            />

            {/* Messagerie (tuteur, eleve, enseignant) */}
            <Route
              path="/messagerie"
              element={
                <RequireAuth roles={["tuteur", "eleve", "enseignant"]}>
                  <MessagerieListPage />
                </RequireAuth>
              }
            />
            <Route
              path="/messagerie/:conversationId"
              element={
                <RequireAuth roles={["tuteur", "eleve", "enseignant"]}>
                  <ConversationPage />
                </RequireAuth>
              }
            />

            {/* Billetterie (achat, tous roles consommateurs) */}
            <Route
              path="/billetterie"
              element={
                <RequireAuth roles={["tuteur", "eleve", "enseignant", "admin_etablissement"]}>
                  <BilletteriePage />
                </RequireAuth>
              }
            />

            {/* Controle d'acces (contrôleurs designes : enseignant ou admin etablissement) */}
            <Route
              path="/valider-acces"
              element={
                <RequireAuth roles={["enseignant", "admin_etablissement"]}>
                  <ValiderAccesPage />
                </RequireAuth>
              }
            />

            {/* Micro-jobs : publier/payer ouvert a tous les roles, accepter reserve aux non-eleves (verifie cote backend) */}
            <Route
              path="/micro-jobs"
              element={
                <RequireAuth roles={["enseignant", "tuteur", "admin_etablissement", "admin_ministeriel", "eleve"]}>
                  <MicroJobsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/admin-ministeriel/micro-jobs-arbitrage"
              element={
                <RequireAuth roles={["admin_ministeriel"]}>
                  <MicroJobsArbitragePage />
                </RequireAuth>
              }
            />

            {/* Admin etablissement (A+) — signalements messagerie */}
            <Route
              path="/admin-etablissement/signalements"
              element={
                <RequireAuth roles={["admin_etablissement"]}>
                  <AdminEtabProvider>
                    <SignalementsPage />
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
