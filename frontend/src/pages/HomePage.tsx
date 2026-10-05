import { Hero } from '@/components/home/Hero';
import { TrustBar } from '@/components/home/TrustBar';
import { Services } from '@/components/home/Services';
import { HowItWorks, Tracking } from '@/components/home/Process';
import { DashboardPreview, Evidence, FinancialControl } from '@/components/home/Product';
import { Maintenance } from '@/components/home/Maintenance';
import { Catalog, Companies, Opportunities } from '@/components/home/Ecosystem';
import { Faq, Testimonials } from '@/components/home/Proof';
import { FinalCta } from '@/components/home/Cta';
import { Seo } from '@/components/Seo';
import { ORGANIZATION_SCHEMA } from '@/lib/seo';

/** Page d'accueil : le parcours de compréhension complet, du besoin à la preuve. */
export default function HomePage() {
  return (
    <>
      <Seo
        title="KEMTA — Suivi de chantier, construction et gestion immobilière au Cameroun"
        description="Confiez votre projet à KEMTA : suivi de chantier à distance, contrôle du budget, preuves photo horodatées, entreprises BTP vérifiées et entretien de propriété au Cameroun."
        path="/"
        jsonLd={ORGANIZATION_SCHEMA}
      />
      <Hero />
      <TrustBar />
      <Services />
      <HowItWorks />
      <Tracking />
      <DashboardPreview />
      <FinancialControl />
      <Evidence />
      <Maintenance />
      <Companies />
      <Catalog />
      <Opportunities />
      <Testimonials />
      <Faq />
      <FinalCta />
    </>
  );
}
